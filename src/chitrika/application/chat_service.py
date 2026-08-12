"""Conversation and message application commands plus stable DTO mapping."""

from __future__ import annotations

from sqlmodel import Session

from src.chitrika.repositories.chat_repository import ChatRepository, _relative_time
from src.chitrika.schemas.chat_schemas import (
    ChatResponse,
    ConversationBatchResponse,
    ConversationDetail,
    MessageListResponse,
    MessageResponse,
)


def message_to_response(message) -> MessageResponse:
    return MessageResponse(
        id=message.id,
        role=message.role.value if hasattr(message.role, "value") else message.role,
        content=message.content,
        time=_relative_time(message.created_at),
        created_at=message.created_at,
        edited_at=message.edited_at,
        is_deleted=message.is_deleted,
        generation_status=message.generation_status,
        error_detail=message.error_detail,
    )


class ConversationApplicationService:
    def __init__(self, session: Session) -> None:
        self.gateway = ChatRepository(session)

    def list(self, character_id: str | None = None) -> list[ChatResponse]:
        return [
            ChatResponse(**value)
            for value in self.gateway.list_conversations(character_id=character_id)
        ]

    def create(self, character_id: str, title: str | None) -> ConversationDetail:
        return ConversationDetail.model_validate(
            self.gateway.create_conversation(character_id, title=title)
        )

    def get(self, conversation_id: str) -> ConversationDetail | None:
        value = self.gateway.get_conversation(conversation_id)
        return ConversationDetail.model_validate(value) if value is not None else None

    def delete(self, conversation_id: str) -> None:
        self.gateway.delete_conversation(conversation_id)

    def delete_batch(self, ids: list[str]) -> ConversationBatchResponse:
        affected, missing = self.gateway.delete_conversations(ids)
        return ConversationBatchResponse(
            requested=len(ids), affected=affected, missing_ids=missing
        )

    def clear(self, conversation_id: str) -> None:
        self.gateway.clear_conversation_messages(conversation_id)

    def clear_batch(self, ids: list[str]) -> ConversationBatchResponse:
        affected, missing = self.gateway.clear_conversations_messages(ids)
        return ConversationBatchResponse(
            requested=len(ids), affected=affected, missing_ids=missing
        )

    def mark_read(self, conversation_id: str) -> int:
        return self.gateway.mark_conversation_read(conversation_id)


class MessageApplicationService:
    def __init__(self, session: Session) -> None:
        self.gateway = ChatRepository(session)

    def list(
        self, conversation_id: str, *, limit: int, before_id: str | None
    ) -> MessageListResponse:
        messages = self.gateway.get_messages(
            conversation_id, limit=limit, before_id=before_id
        )
        return MessageListResponse(messages=[message_to_response(item) for item in messages])

    def edit(self, message_id: str, content: str) -> MessageResponse:
        return message_to_response(self.gateway.edit_message(message_id, content))

    def recall(self, message_id: str) -> MessageResponse:
        return message_to_response(self.gateway.recall_message(message_id))

    def delete(self, message_id: str) -> None:
        self.gateway.delete_message(message_id)
