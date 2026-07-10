"""Heartbeat models: task log and scheduled proactive messages."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlmodel import Field, Relationship

from src.chitrika.models.base import (
    HeartbeatTaskType,
    ProactiveTrigger,
    ScheduledMessageStatus,
    TaskStatus,
    UUIDPrimaryKeyMixin,
)
from src.chitrika.utils.datetime_helpers import utcnow

if TYPE_CHECKING:
    from src.chitrika.models.character import Character
    from src.chitrika.models.conversation import Conversation


class HeartbeatTask(UUIDPrimaryKeyMixin, table=True):
    """Audit log of every heartbeat tick for every character."""

    __tablename__ = "heartbeat_tasks"

    character_id: str = Field(
        foreign_key="characters.id",
        index=True,
        description="The character processed during this heartbeat tick",
    )
    task_type: str = Field(
        default=HeartbeatTaskType.EMOTION_DECAY.value,
        index=True,
        description="One of: 'emotion_decay', 'memory_review', 'proactive_message'",
    )
    status: str = Field(
        default=TaskStatus.PENDING.value,
        index=True,
        description="pending | running | completed | failed",
    )
    scheduled_at: datetime = Field(
        default_factory=utcnow,
    )
    executed_at: Optional[datetime] = Field(default=None)
    result_json: Optional[str] = Field(
        default=None,
        description="Optional JSON payload with task result details",
    )
    created_at: datetime = Field(
        default_factory=utcnow,
        index=True,
    )

    character: "Character" = Relationship(back_populates="heartbeat_tasks")


class ScheduledMessage(UUIDPrimaryKeyMixin, table=True):
    """A proactive message queued by the heartbeat engine.

    The message may be sent immediately, delayed, or cancelled based on
    the LLM's re-evaluation at send time.
    """

    __tablename__ = "scheduled_messages"

    character_id: str = Field(
        foreign_key="characters.id",
        index=True,
    )
    conversation_id: str = Field(
        foreign_key="conversations.id",
        index=True,
    )
    content: Optional[str] = Field(
        default=None,
        description="Pre-generated message content; if None, LLM generates at send time",
    )
    status: str = Field(
        default=ScheduledMessageStatus.PENDING.value,
        index=True,
        description="pending | approved | sent | cancelled | expired",
    )
    trigger_reason: str = Field(
        default=ProactiveTrigger.LONELINESS.value,
        index=True,
        description="Why this message was scheduled: 'loneliness', 'schedule', 'reminder'",
    )
    scheduled_at: datetime = Field(
        default_factory=utcnow,
        index=True,
        description="When the message should be delivered",
    )
    evaluated_at: Optional[datetime] = Field(
        default=None,
        description="When the LLM made its decision",
    )
    cancelled_at: Optional[datetime] = Field(default=None)
    llm_decision_json: Optional[str] = Field(
        default=None,
        description="Raw LLM decision payload as JSON",
    )
    created_at: datetime = Field(
        default_factory=utcnow,
        index=True,
    )

    character: "Character" = Relationship(back_populates="scheduled_messages")
    conversation: "Conversation" = Relationship(back_populates="scheduled_messages")
