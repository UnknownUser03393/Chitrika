"""Shared ORM primitives for Chitrika models."""

import uuid
from enum import Enum

from sqlmodel import Field, SQLModel


def new_id() -> str:
    """Return a stable string UUID for SQLite-friendly primary keys."""
    return str(uuid.uuid4())


class UUIDPrimaryKeyMixin(SQLModel):
    """String UUID primary key used by all first-class tables."""

    id: str = Field(default_factory=new_id, primary_key=True)


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class MemoryType(str, Enum):
    SHORT_TERM = "short_term"
    LONG_TERM = "long_term"
    EPISODIC = "episodic"


class HeartbeatTaskType(str, Enum):
    EMOTION_DECAY = "emotion_decay"
    MEMORY_REVIEW = "memory_review"
    PROACTIVE_MESSAGE = "proactive_message"


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ScheduledMessageStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    SENT = "sent"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class ProactiveTrigger(str, Enum):
    LONELINESS = "loneliness"
    SCHEDULE = "schedule"
    REMINDER = "reminder"
