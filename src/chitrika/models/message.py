"""Message model: a single user or assistant utterance."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlmodel import Field, Relationship

from src.chitrika.models.base import MessageRole, UUIDPrimaryKeyMixin
from src.chitrika.utils.datetime_helpers import utcnow

if TYPE_CHECKING:
    from src.chitrika.models.conversation import Conversation
    from src.chitrika.models.memory import Memory


class Message(UUIDPrimaryKeyMixin, table=True):
    """A single message within a conversation. Supports soft-delete and edit."""

    __tablename__ = "messages"

    conversation_id: str = Field(
        foreign_key="conversations.id",
        index=True,
        description="The conversation this message belongs to",
    )
    role: str = Field(
        default=MessageRole.USER.value,
        description="Either 'user' or 'assistant'",
    )
    content: str = Field(
        description="Message body (markdown)",
    )
    created_at: datetime = Field(default_factory=utcnow, index=True)
    edited_at: Optional[datetime] = Field(
        default=None,
        description="When the message was last edited, if at all",
    )
    is_deleted: bool = Field(
        default=False,
        index=True,
        description="Soft-delete flag — deleted messages are hidden from UI",
    )
    read_at: Optional[datetime] = Field(
        default=None,
        description="When the user read this message (null = unread)",
    )
    desktop_notified_at: Optional[datetime] = Field(
        default=None,
        description="When a desktop notification was shown for this message",
    )
    scheduled_message_id: Optional[str] = Field(
        default=None,
        foreign_key="scheduled_messages.id",
        index=True,
        description="If this message was delivered from a scheduled proactive message",
    )

    conversation: "Conversation" = Relationship(back_populates="messages")
    memories: list["Memory"] = Relationship(back_populates="source_message")
