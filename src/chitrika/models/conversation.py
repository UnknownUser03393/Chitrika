"""Conversation model — a chat thread bound to a character."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlmodel import Field, SQLModel

from src.chitrika.utils.datetime_helpers import utcnow


class Conversation(SQLModel, table=True):
    """A conversation thread between the user and a specific character."""

    __tablename__ = "conversations"

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
    )
    character_id: str = Field(
        foreign_key="characters.id",
        index=True,
        description="The character participating in this conversation",
    )
    title: str | None = Field(
        default=None,
        description="Optional human-readable title (auto-generated or set by user)",
    )
    summary: str | None = Field(
        default=None,
        description="LLM-generated episodic summary of the conversation",
    )
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
    last_message_at: datetime | None = Field(
        default=None,
        description="Timestamp of the most recent message (for sorting)",
    )
