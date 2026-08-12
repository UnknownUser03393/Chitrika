"""SSE launch boundary with a short preparation transaction."""

from __future__ import annotations

from src.chitrika.database import session_scope
from src.chitrika.application.chat_stream_runtime import (
    prepare_chat_stream,
    release_conversation,
    stream_prepared_response,
    try_reserve_conversation,
)
from src.chitrika.uow import UnitOfWork


class ChatStreamApplicationService:
    def reserve_and_prepare(self, conversation_id: str, content: str):
        if not try_reserve_conversation(conversation_id):
            return None
        try:
            with UnitOfWork(session_factory=session_scope) as uow:
                return prepare_chat_stream(uow.session, conversation_id, content)
        except Exception:
            release_conversation(conversation_id)
            raise

    @staticmethod
    def stream(prepared):
        return stream_prepared_response(prepared)
