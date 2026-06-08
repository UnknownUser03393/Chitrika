"""Heartbeat models — task log and scheduled proactive messages."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlmodel import Field, SQLModel

from src.chitrika.utils.datetime_helpers import utcnow


class HeartbeatTask(SQLModel, table=True):
    """Audit log of every heartbeat tick for every character."""

    __tablename__ = "heartbeat_tasks"

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
    )
    character_id: str = Field(
        foreign_key="characters.id",
        index=True,
        description="The character processed during this heartbeat tick",
    )
    task_type: str = Field(
        description="One of: 'emotion_decay', 'memory_review', 'proactive_message'",
    )
    status: str = Field(
        default="pending",
        description="pending | running | completed | failed",
    )
    scheduled_at: datetime = Field(
        default_factory=utcnow,
    )
    executed_at: datetime | None = Field(default=None)
    result_json: str | None = Field(
        default=None,
        description="Optional JSON payload with task result details",
    )
    created_at: datetime = Field(
        default_factory=utcnow,
    )


class ScheduledMessage(SQLModel, table=True):
    """A proactive message queued by the heartbeat engine.

    The message may be sent immediately, delayed, or cancelled based on
    the LLM's re-evaluation at send time.
    """

    __tablename__ = "scheduled_messages"

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
    )
    character_id: str = Field(
        foreign_key="characters.id",
        index=True,
    )
    conversation_id: str = Field(
        foreign_key="conversations.id",
    )
    content: str | None = Field(
        default=None,
        description="Pre-generated message content; if None, LLM generates at send time",
    )
    status: str = Field(
        default="pending",
        description="pending | approved | sent | cancelled | expired",
    )
    trigger_reason: str = Field(
        default="loneliness",
        description="Why this message was scheduled: 'loneliness', 'schedule', 'reminder'",
    )
    scheduled_at: datetime = Field(
        default_factory=utcnow,
        description="When the message should be delivered",
    )
    evaluated_at: datetime | None = Field(
        default=None,
        description="When the LLM made its decision",
    )
    cancelled_at: datetime | None = Field(default=None)
    llm_decision_json: str | None = Field(
        default=None,
        description="Raw LLM decision payload as JSON",
    )
    created_at: datetime = Field(
        default_factory=utcnow,
    )
