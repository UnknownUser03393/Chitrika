"""Conversation model: a chat thread bound to a character."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlmodel import Field, Relationship, SQLModel

from src.chitrika.models.base import new_id
from src.chitrika.utils.datetime_helpers import utcnow

if TYPE_CHECKING:
    from src.chitrika.models.character import Character
    from src.chitrika.models.heartbeat import ScheduledMessage
    from src.chitrika.models.message import Message


class Conversation(SQLModel, table=True):
    """A conversation thread between the user and a specific character."""

    __tablename__ = "conversations"

    id: str = Field(default_factory=new_id, primary_key=True)
    character_id: str = Field(
        foreign_key="characters.id",
        index=True,
        description="The character participating in this conversation",
    )
    title: Optional[str] = Field(
        default=None,
        description="Optional human-readable title (auto-generated or set by user)",
    )
    summary: Optional[str] = Field(
        default=None,
        description="LLM-generated episodic summary of the conversation",
    )
    created_at: datetime = Field(default_factory=utcnow, index=True)
    updated_at: datetime = Field(default_factory=utcnow, index=True)
    last_message_at: Optional[datetime] = Field(
        default=None,
        index=True,
        description="Timestamp of the most recent message (for sorting)",
    )

    character: "Character" = Relationship(back_populates="conversations")
    messages: list["Message"] = Relationship(back_populates="conversation")
    scheduled_messages: list["ScheduledMessage"] = Relationship(back_populates="conversation")
