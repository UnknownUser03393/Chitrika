"""Message model — a single user or assistant message in a conversation."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlmodel import Field, SQLModel

from src.chitrika.utils.datetime_helpers import utcnow


class Message(SQLModel, table=True):
    """A single message within a conversation. Supports soft-delete and edit."""

    __tablename__ = "messages"

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
    )
    conversation_id: str = Field(
        foreign_key="conversations.id",
        index=True,
        description="The conversation this message belongs to",
    )
    role: str = Field(
        description="Either 'user' or 'assistant'",
    )
    content: str = Field(
        description="Message body (markdown)",
    )
    created_at: datetime = Field(default_factory=utcnow)
    edited_at: datetime | None = Field(
        default=None,
        description="When the message was last edited, if at all",
    )
    is_deleted: bool = Field(
        default=False,
        description="Soft-delete flag — deleted messages are hidden from UI",
    )
