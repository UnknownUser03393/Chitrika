"""Short-transaction runtime for one SSE chat generation."""

from __future__ import annotations

import logging
import re
import threading
from typing import Generator

from sqlmodel import Session

from src.chitrika.database import session_scope
from src.chitrika.models.conversation import Conversation
from src.chitrika.models.message import Message
from src.chitrika.services.chat_generation_service import (
    ChatGenerationService,
    PreparedGeneration,
)
from src.chitrika.services.chat_post_processor import ChatPostProcessor
from src.chitrika.utils import sse
from src.chitrika.utils.datetime_helpers import utcnow
from src.chitrika.uow import UnitOfWork

logger = logging.getLogger("chitrika.chat.stream")

_ACTIVE_CONVERSATIONS: set[str] = set()
_ACTIVE_LOCK = threading.Lock()
_SECRET_PATTERN = re.compile(
    r"(?i)(bearer\s+)[^\s,;]+|((?:api[_-]?key|token|secret)\s*[=:]\s*)[^\s,;]+"
)


def try_reserve_conversation(conversation_id: str) -> bool:
    """Atomically reserve a conversation for one in-process generation."""
    with _ACTIVE_LOCK:
        if conversation_id in _ACTIVE_CONVERSATIONS:
            return False
        _ACTIVE_CONVERSATIONS.add(conversation_id)
        return True


def release_conversation(conversation_id: str) -> None:
    with _ACTIVE_LOCK:
        _ACTIVE_CONVERSATIONS.discard(conversation_id)


def sanitize_error_detail(exc: BaseException) -> str:
    """Return bounded diagnostics with common credentials redacted."""
    raw = f"{type(exc).__name__}: {exc}".strip()
    redacted = _SECRET_PATTERN.sub(
        lambda match: f"{match.group(1) or match.group(2)}[REDACTED]", raw
    )
    return redacted[:1000]


def prepare_chat_stream(
    session: Session,
    conversation_id: str,
    user_content: str,
) -> PreparedGeneration:
    """Persist the user turn and copy everything needed by the network stream."""
    return ChatGenerationService(session).prepare(conversation_id, user_content)


def _persist_assistant(
    prepared: PreparedGeneration,
    content: str,
    status: str,
    error_detail: str | None = None,
) -> None:
    with UnitOfWork(session_factory=session_scope) as uow:
        session = uow.session
        conversation = session.get(Conversation, prepared.conversation_id)
        if conversation is None:
            raise RuntimeError("Conversation disappeared while generating")
        message = Message(
            id=prepared.assistant_message_id,
            conversation_id=prepared.conversation_id,
            role="assistant",
            content=content,
            generation_status=status,
            error_detail=error_detail,
        )
        session.add(message)
        conversation.last_message_at = utcnow()
        conversation.updated_at = utcnow()


def _post_process(prepared: PreparedGeneration, assistant_text: str) -> None:
    """Run all state mutation after persistence in a separate transaction scope."""
    with UnitOfWork(session_factory=session_scope) as uow:
        session = uow.session
        processor = ChatPostProcessor(
            session,
            llm=prepared.llm,
            model_name=prepared.model_name,
        )
        processor.process(
            prepared.character_id,
            prepared.user_content,
            assistant_text,
            prepared.user_message_id,
        )


def stream_prepared_response(prepared: PreparedGeneration) -> Generator[str, None, None]:
    """Stream without a DB session, then persist in fresh short transactions."""
    chunks: list[str] = []
    try:
        yield sse.sse_start(
            prepared.assistant_message_id,
            user_message_id=prepared.user_message_id,
        )
        try:
            if prepared.llm is None:
                chunk = f"[echo] {prepared.user_content}"
                chunks.append(chunk)
                yield sse.sse_content(chunk)
            else:
                from src.llmproviders.LLMProvider import Model as LLMModel

                model = LLMModel(name=prepared.model_name or "deepseek-chat")
                for response_chunk in prepared.llm.stream(model, prepared.llm_messages):
                    if response_chunk.content:
                        chunks.append(response_chunk.content)
                        yield sse.sse_content(response_chunk.content)
        except GeneratorExit:
            partial = "".join(chunks)
            if partial:
                detail = "The client disconnected before the response completed."
                _persist_assistant(prepared, partial, "interrupted", detail)
            raise
        except Exception as exc:
            logger.exception("LLM streaming failed")
            content = "".join(chunks)
            detail = sanitize_error_detail(exc)
            _persist_assistant(prepared, content, "error", detail)
            yield sse.sse_error(
                "The upstream model failed while responding.",
                code="upstream_error",
                details=detail,
                message_id=prepared.assistant_message_id,
            )
            return

        content = "".join(chunks)
        _persist_assistant(prepared, content, "complete")
        yield sse.sse_done(prepared.assistant_message_id, {})
        try:
            _post_process(prepared, content)
        except Exception:
            logger.exception("Chat post-processing failed")
    finally:
        release_conversation(prepared.conversation_id)
