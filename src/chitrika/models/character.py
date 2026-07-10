"""Character model: persona identity, prompt, and provider binding."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlmodel import Field, Relationship, SQLModel

from src.chitrika.models.base import new_id
from src.chitrika.utils.datetime_helpers import utcnow

if TYPE_CHECKING:
    from src.chitrika.models.conversation import Conversation
    from src.chitrika.models.emotion import EmotionState
    from src.chitrika.models.heartbeat import HeartbeatTask, ScheduledMessage
    from src.chitrika.models.memory import Memory
    from src.chitrika.models.provider import LLMProvider


class Character(SQLModel, table=True):
    """A digital persona with its own identity, prompt, and emotional state."""

    __tablename__ = "characters"

    id: str = Field(default_factory=new_id, primary_key=True)
    name: str = Field(
        unique=True,
        index=True,
        description="Internal slug / short name, e.g. 'alvia'",
    )
    display_name: str = Field(
        description="Human-readable name, e.g. '徐悦婷'",
    )
    avatar_url: Optional[str] = Field(default=None)
    description: Optional[str] = Field(
        default=None,
        description="Short biographical description",
    )
    provider_id: Optional[str] = Field(
        default=None,
        foreign_key="llm_providers.id",
        index=True,
        description="Configured LLM provider used by this character",
    )
    personality_prompt: str = Field(
        default="",
        description="Full system prompt injected into every LLM call",
    )
    initials: str = Field(
        default="",
        description="Fallback avatar initials, 1-2 chars",
    )
    color: str = Field(
        default="#4FA3E3",
        description="Hex colour used for avatar background",
    )
    enabled: bool = Field(
        default=True,
        index=True,
        description="Whether this character is active",
    )
    created_at: datetime = Field(default_factory=utcnow, index=True)
    updated_at: datetime = Field(default_factory=utcnow, index=True)

    provider: Optional["LLMProvider"] = Relationship(back_populates="characters")
    conversations: list["Conversation"] = Relationship(back_populates="character")
    emotion_state: Optional["EmotionState"] = Relationship(back_populates="character")
    memories: list["Memory"] = Relationship(back_populates="character")
    heartbeat_tasks: list["HeartbeatTask"] = Relationship(back_populates="character")
    scheduled_messages: list["ScheduledMessage"] = Relationship(back_populates="character")
