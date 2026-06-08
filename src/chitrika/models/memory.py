"""Memory model — facts, events, and conversation history."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlmodel import Field, SQLModel

from src.chitrika.utils.datetime_helpers import utcnow


class Memory(SQLModel, table=True):
    """A stored memory — short-term, long-term fact, or episodic summary.

    Memories belong to a character and decay in importance over time unless
    accessed or explicitly pinned.
    """

    __tablename__ = "memories"

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
    )
    character_id: str = Field(
        foreign_key="characters.id",
        index=True,
        description="The character this memory belongs to",
    )
    memory_type: str = Field(
        description="One of: 'short_term', 'long_term', 'episodic'",
    )
    content: str = Field(
        description="The memory text",
    )
    source_message_id: str | None = Field(
        default=None,
        foreign_key="messages.id",
        description="The message that produced this memory, for traceability",
    )
    importance: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Importance score 0.0–1.0; low-importance memories are pruned",
    )
    emotional_valence: float | None = Field(
        default=None,
        ge=-1.0,
        le=1.0,
        description="Emotional charge of the memory, -1.0 (negative) to 1.0 (positive)",
    )
    created_at: datetime = Field(default_factory=utcnow)
    last_accessed: datetime = Field(
        default_factory=utcnow,
        description="Last time this memory was retrieved or used in a prompt",
    )
    access_count: int = Field(
        default=0,
        description="How many times this memory has been retrieved",
    )
    is_pinned: bool = Field(
        default=False,
        description="User-explicit pin — pinned memories never decay",
    )
    is_forgotten: bool = Field(
        default=False,
        description="Soft-delete flag — forgotten memories are hidden but kept for audit",
    )
