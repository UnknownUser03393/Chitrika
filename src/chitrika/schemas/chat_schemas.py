"""Pydantic schemas for chat / conversation API."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class ConversationCreate(BaseModel):
    """Request body for creating a new conversation."""

    character_id: str = Field(..., description="Which character to talk to")
    title: str | None = None


class SendMessage(BaseModel):
    """Request body for sending a message."""

    content: str = Field(..., min_length=1, description="Message text")


class MessageEdit(BaseModel):
    """Request body for editing a message."""

    content: str = Field(..., min_length=1)


# ---------------------------------------------------------------------------
# Response schemas (matching frontend data models)
# ---------------------------------------------------------------------------


class MessageResponse(BaseModel):
    """A single message as returned to the frontend."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    role: str
    content: str
    time: str
    created_at: datetime
    edited_at: datetime | None = None
    is_deleted: bool = False


class ChatResponse(BaseModel):
    """A conversation enriched for the frontend ChatListView."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    initials: str
    color: str
    lastMessage: str
    time: str
    unread: int = 0
    pinned: bool = False
    character_id: str | None = None


class ConversationDetail(BaseModel):
    """Full conversation details."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    character_id: str
    title: str | None
    summary: str | None
    created_at: datetime
    updated_at: datetime
    last_message_at: datetime | None


class MessageListResponse(BaseModel):
    """Paginated message list."""

    messages: list[MessageResponse]
