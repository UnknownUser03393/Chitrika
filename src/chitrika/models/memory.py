"""Memory model: facts, events, and conversation history."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlmodel import Field, Relationship, SQLModel

from src.chitrika.models.base import MemoryType, new_id
from src.chitrika.utils.datetime_helpers import utcnow

if TYPE_CHECKING:
    from src.chitrika.models.character import Character
    from src.chitrika.models.message import Message


class Memory(SQLModel, table=True):
    """A stored memory — short-term, long-term fact, or episodic summary.

    Memories belong to a character and decay in importance over time unless
    accessed or explicitly pinned.
    """

    __tablename__ = "memories"

    id: str = Field(default_factory=new_id, primary_key=True)
    character_id: str = Field(
        foreign_key="characters.id",
        index=True,
        description="The character this memory belongs to",
    )
    memory_type: str = Field(
        default=MemoryType.SHORT_TERM.value,
        index=True,
        description="One of: 'short_term', 'long_term', 'episodic'",
    )
    content: str = Field(
        description="The memory text",
    )
    source_message_id: Optional[str] = Field(
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
    emotional_valence: Optional[float] = Field(
        default=None,
        ge=-1.0,
        le=1.0,
        description="Emotional charge of the memory, -1.0 (negative) to 1.0 (positive)",
    )
    embedding: Optional[bytes] = Field(
        default=None,
        description=(
            "Local sentence-embedding of `content` (float32 bytes) for semantic "
            "recall. None when no embedding model is configured or not yet computed."
        ),
    )
    created_at: datetime = Field(default_factory=utcnow, index=True)
    updated_at: datetime = Field(default_factory=utcnow, index=True)
    last_accessed: datetime = Field(
        default_factory=utcnow,
        index=True,
        description="Last time this memory was retrieved or used in a prompt",
    )
    access_count: int = Field(
        default=0,
        description="How many times this memory has been retrieved",
    )
    is_pinned: bool = Field(
        default=False,
        index=True,
        description="User-explicit pin — pinned memories never decay",
    )
    is_forgotten: bool = Field(
        default=False,
        index=True,
        description="Soft-delete flag — forgotten memories are hidden but kept for audit",
    )

    character: "Character" = Relationship(back_populates="memories")
    source_message: Optional["Message"] = Relationship(back_populates="memories")
