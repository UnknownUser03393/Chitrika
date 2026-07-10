"""Chat API routes — conversations, messages, and SSE streaming."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlmodel import Session, select

from src.chitrika.database import get_session
from src.chitrika.engines.chat_engine import _relative_time
from src.chitrika.schemas.chat_schemas import (
    ChatResponse,
    ConversationCreate,
    ConversationDetail,
    MessageEdit,
    MessageListResponse,
    MessageResponse,
    SendMessage,
)

logger = logging.getLogger("chitrika.routes.chat")

router = APIRouter(tags=["chat"])


# ---------------------------------------------------------------------------
# Dependency: resolve LLM provider from character's configured provider
# ---------------------------------------------------------------------------

def _get_llm(
    session: Session,
    *,
    provider_id: str | None = None,
    provider_name: str | None = None,
):
    """Create an LLM client for a provider id or fallback provider name.

    Returns (client, model_name) tuple, or (None, "") if no provider is found.
    """
    from src.chitrika.services.provider_service import (
        resolve_provider_for_character,
        create_llm_client,
    )

    provider = resolve_provider_for_character(
        session,
        provider_name=provider_name,
        provider_id=provider_id,
    )
    if provider is None:
        logger.warning("No provider found for character")
        return None, ""

    client = create_llm_client(provider.api_key, provider.base_url)
    model_name = provider.default_model or ""
    return client, model_name


# ---------------------------------------------------------------------------
# Conversation list — GET /api/conversations  (also /api/chats for compat)
# ---------------------------------------------------------------------------


@router.get("/conversations")
def list_conversations(
    character_id: str | None = Query(default=None),
    session: Session = Depends(get_session),
) -> list[ChatResponse]:
    """List all conversations, enriched for the frontend ChatListView."""
    from src.chitrika.engines.chat_engine import ChatEngine

    engine = ChatEngine(session)
    chats = engine.list_conversations(character_id=character_id)
    return [ChatResponse(**c) for c in chats]


# Frontend compatibility alias
@router.get("/chats")
def list_chats(
    character_id: str | None = Query(default=None),
    session: Session = Depends(get_session),
) -> list[ChatResponse]:
    """Alias for GET /api/conversations (frontend compat)."""
    return list_conversations(character_id=character_id, session=session)


# ---------------------------------------------------------------------------
# Create conversation — POST /api/conversations
# ---------------------------------------------------------------------------


@router.post("/conversations", status_code=201)
def create_conversation(
    body: ConversationCreate,
    session: Session = Depends(get_session),
) -> ConversationDetail:
    """Create a new conversation with a character."""
    from src.chitrika.engines.chat_engine import ChatEngine

    engine = ChatEngine(session)
    try:
        conv = engine.create_conversation(body.character_id, title=body.title)
        return ConversationDetail.model_validate(conv)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Get conversation — GET /api/conversations/{conversation_id}
# ---------------------------------------------------------------------------


@router.get("/conversations/{conversation_id}")
def get_conversation(
    conversation_id: str,
    session: Session = Depends(get_session),
) -> ConversationDetail:
    """Get a single conversation by ID."""
    from src.chitrika.engines.chat_engine import ChatEngine

    engine = ChatEngine(session)
    conv = engine.get_conversation(conversation_id)
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return ConversationDetail.model_validate(conv)


# ---------------------------------------------------------------------------
# Delete conversation — DELETE /api/conversations/{conversation_id}
# ---------------------------------------------------------------------------


@router.delete("/conversations/{conversation_id}", status_code=204)
def delete_conversation(
    conversation_id: str,
    session: Session = Depends(get_session),
) -> None:
    """Delete a conversation and all its messages."""
    from src.chitrika.engines.chat_engine import ChatEngine

    engine = ChatEngine(session)
    try:
        engine.delete_conversation(conversation_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Mark conversation read — POST /api/conversations/{conversation_id}/read
# ---------------------------------------------------------------------------


@router.post("/conversations/{conversation_id}/read")
def mark_conversation_read(
    conversation_id: str,
    session: Session = Depends(get_session),
) -> dict:
    """Mark all unread assistant messages in a conversation as read."""
    from src.chitrika.engines.chat_engine import ChatEngine

    engine = ChatEngine(session)
    count = engine.mark_conversation_read(conversation_id)
    return {"marked_read": count}


# ---------------------------------------------------------------------------
# Get messages — GET /api/conversations/{conversation_id}/messages
# ---------------------------------------------------------------------------


@router.get("/conversations/{conversation_id}/messages")
def get_messages(
    conversation_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    before: str | None = Query(default=None, alias="before"),
    session: Session = Depends(get_session),
) -> MessageListResponse:
    """Get messages for a conversation, newest last."""
    from src.chitrika.engines.chat_engine import ChatEngine

    engine = ChatEngine(session)
    messages = engine.get_messages(conversation_id, limit=limit, before_id=before)

    return MessageListResponse(
        messages=[
            MessageResponse(
                id=m.id,
                role=m.role.value if hasattr(m.role, "value") else m.role,
                content=m.content,
                time=_relative_time(m.created_at),
                created_at=m.created_at,
                edited_at=m.edited_at,
                is_deleted=m.is_deleted,
            )
            for m in messages
        ]
    )


# ---------------------------------------------------------------------------
# Send message — POST /api/conversations/{conversation_id}/messages  (SSE)
# ---------------------------------------------------------------------------


@router.delete("/conversations/{conversation_id}/messages", status_code=204)
def clear_conversation_messages(
    conversation_id: str,
    session: Session = Depends(get_session),
) -> None:
    """Clear all chat messages while keeping the conversation."""
    from src.chitrika.engines.chat_engine import ChatEngine

    engine = ChatEngine(session)
    try:
        engine.clear_conversation_messages(conversation_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/conversations/{conversation_id}/messages")
def send_message(
    conversation_id: str,
    body: SendMessage,
    session: Session = Depends(get_session),
) -> StreamingResponse:
    """Send a message and stream the AI response via SSE.

    Returns ``text/event-stream`` with these event types:
        - start   — streaming begins (contains message_id)
        - content — a chunk of the response
        - done    — streaming complete
        - error   — an error occurred
    """
    from src.chitrika.engines.chat_engine import ChatEngine
    from src.chitrika.models.character import Character

    # Validate conversation exists first
    engine = ChatEngine(session)
    conv = engine.get_conversation(conversation_id)
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Load character to determine provider
    character = session.exec(
        select(Character).where(Character.id == conv.character_id)
    ).first()
    if character is None:
        raise HTTPException(status_code=404, detail="Character not found")

    # Create LLM client from character's provider
    llm, model_name = _get_llm(
        session,
        provider_id=character.provider_id,
        provider_name=character.provider.name if character.provider else "deepseek",
    )

    # Re-create engine with provider for streaming
    engine = ChatEngine(session, llm_provider=llm, model_name=model_name)

    return StreamingResponse(
        engine.stream_response(conversation_id, body.content),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


# ---------------------------------------------------------------------------
# Edit message — PATCH /api/messages/{message_id}
# ---------------------------------------------------------------------------


@router.patch("/messages/{message_id}")
def edit_message(
    message_id: str,
    body: MessageEdit,
    session: Session = Depends(get_session),
) -> MessageResponse:
    """Edit a message's content."""
    from src.chitrika.engines.chat_engine import ChatEngine

    engine = ChatEngine(session)
    try:
        msg = engine.edit_message(message_id, body.content)
        return MessageResponse(
            id=msg.id,
            role=msg.role.value if hasattr(msg.role, "value") else msg.role,
            content=msg.content,
            time=_relative_time(msg.created_at),
            created_at=msg.created_at,
            edited_at=msg.edited_at,
            is_deleted=msg.is_deleted,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Delete message — DELETE /api/messages/{message_id}
# ---------------------------------------------------------------------------


@router.post("/messages/{message_id}/recall")
def recall_message(
    message_id: str,
    session: Session = Depends(get_session),
) -> MessageResponse:
    """Mark a message as recalled."""
    from src.chitrika.engines.chat_engine import ChatEngine

    engine = ChatEngine(session)
    try:
        msg = engine.recall_message(message_id)
        return MessageResponse(
            id=msg.id,
            role=msg.role.value if hasattr(msg.role, "value") else msg.role,
            content=msg.content,
            time=_relative_time(msg.created_at),
            created_at=msg.created_at,
            edited_at=msg.edited_at,
            is_deleted=msg.is_deleted,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/messages/{message_id}", status_code=204)
def delete_message(
    message_id: str,
    session: Session = Depends(get_session),
) -> None:
    """Soft-delete a message."""
    from src.chitrika.engines.chat_engine import ChatEngine

    engine = ChatEngine(session)
    try:
        engine.delete_message(message_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
