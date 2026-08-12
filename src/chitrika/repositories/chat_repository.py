"""Conversation and message persistence/query repository."""

from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy import and_, func
from sqlmodel import Session, col, select

from src.chitrika.models.character import Character
from src.chitrika.models.conversation import Conversation
from src.chitrika.models.heartbeat import ScheduledMessage
from src.chitrika.models.memory import Memory
from src.chitrika.models.message import Message
from src.chitrika.utils.datetime_helpers import utcnow

logger = logging.getLogger("chitrika.chat")


class ChatRepository:
    """Manage conversations and persisted messages for one DB session."""

    def __init__(self, session: Session):
        self._session = session

    # ------------------------------------------------------------------
    # Conversation CRUD
    # ------------------------------------------------------------------

    def create_conversation(
        self,
        character_id: str,
        title: str | None = None,
    ) -> Conversation:
        """Create a new conversation with *character_id*."""
        character = self._session.exec(
            select(Character).where(
                Character.id == character_id,
                Character.enabled.is_(True),
            )
        ).first()
        if character is None:
            raise ValueError(f"Character '{character_id}' not found or disabled")

        conv = Conversation(
            character_id=character_id,
            title=title,
        )
        self._session.add(conv)
        self._session.flush()
        return conv

    def get_conversation(self, conversation_id: str) -> Conversation | None:
        """Fetch a single conversation."""
        return self._session.exec(
            select(Conversation).where(Conversation.id == conversation_id)
        ).first()

    def list_conversations(
        self,
        character_id: str | None = None,
    ) -> list[dict]:
        """Return conversations as ChatResponse-compatible dicts.

        Each conversation is enriched with character info, last message
        preview, and relative time string.
        """
        stmt = select(Conversation).order_by(
            col(Conversation.last_message_at).desc().nulls_last(),
            col(Conversation.updated_at).desc(),
        )
        if character_id is not None:
            stmt = stmt.where(Conversation.character_id == character_id)

        conversations = list(self._session.exec(stmt).all())
        if not conversations:
            return []

        conversation_ids = [conv.id for conv in conversations]
        character_ids = {conv.character_id for conv in conversations}

        characters = self._session.exec(
            select(Character).where(Character.id.in_(character_ids))
        ).all()
        characters_by_id = {char.id: char for char in characters}

        last_message_at = (
            select(
                Message.conversation_id,
                func.max(Message.created_at).label("created_at"),
            )
            .where(
                Message.conversation_id.in_(conversation_ids),
                Message.is_deleted.is_(False),
            )
            .group_by(Message.conversation_id)
            .subquery()
        )
        latest_messages = self._session.exec(
            select(Message).join(
                last_message_at,
                and_(
                    Message.conversation_id == last_message_at.c.conversation_id,
                    Message.created_at == last_message_at.c.created_at,
                ),
            )
        ).all()
        messages_by_conversation_id = {
            msg.conversation_id: msg for msg in latest_messages
        }

        # Count unread assistant messages per conversation
        unread_stmt = (
            select(
                Message.conversation_id,
                func.count(Message.id).label("unread"),
            )
            .where(
                Message.conversation_id.in_(conversation_ids),
                Message.role == "assistant",
                Message.is_deleted.is_(False),
                Message.read_at.is_(None),
            )
            .group_by(Message.conversation_id)
        )
        unread_rows = self._session.exec(unread_stmt).all()
        unread_by_conv: dict[str, int] = {row[0]: row[1] for row in unread_rows}

        result: list[dict] = []

        for conv in conversations:
            char = characters_by_id.get(conv.character_id)
            last_msg = messages_by_conversation_id.get(conv.id)

            result.append({
                "id": conv.id,
                "name": char.display_name if char else "Unknown",
                "initials": char.initials if char else "?",
                "color": char.color if char else "#4FA3E3",
                "lastMessage": last_msg.content[:100] if last_msg else "",
                "time": _relative_time(last_msg.created_at) if last_msg else "",
                "unread": unread_by_conv.get(conv.id, 0),
                "pinned": False,
                "character_id": conv.character_id,
            })

        return result

    def delete_conversation(self, conversation_id: str) -> None:
        """Delete a conversation and all its messages."""
        affected, missing_ids = self.delete_conversations([conversation_id])
        if affected == 0:
            raise ValueError(f"Conversation '{missing_ids[0]}' not found")

    def delete_conversations(self, conversation_ids: list[str]) -> tuple[int, list[str]]:
        """Delete multiple conversations and all dependent rows."""
        unique_ids = list(dict.fromkeys(conversation_ids))
        if not unique_ids:
            return 0, []

        conversations = self._session.exec(
            select(Conversation).where(Conversation.id.in_(unique_ids))
        ).all()
        found_ids = {conv.id for conv in conversations}
        missing_ids = [conversation_id for conversation_id in unique_ids if conversation_id not in found_ids]

        messages = self._session.exec(
            select(Message).where(Message.conversation_id.in_(found_ids))
        ).all()
        message_ids = [msg.id for msg in messages]
        if message_ids:
            memories = self._session.exec(
                select(Memory).where(Memory.source_message_id.in_(message_ids))
            ).all()
            for memory in memories:
                memory.source_message_id = None

        for msg in messages:
            self._session.delete(msg)

        scheduled_messages = self._session.exec(
            select(ScheduledMessage).where(ScheduledMessage.conversation_id.in_(found_ids))
        ).all()
        for scheduled_msg in scheduled_messages:
            self._session.delete(scheduled_msg)

        for conv in conversations:
            self._session.delete(conv)

        self._session.flush()
        return len(conversations), missing_ids

    def clear_conversation_messages(self, conversation_id: str) -> None:
        """Soft-delete all messages in a conversation without deleting it."""
        affected, missing_ids = self.clear_conversations_messages([conversation_id])
        if affected == 0:
            raise ValueError(f"Conversation '{missing_ids[0]}' not found")

    def clear_conversations_messages(self, conversation_ids: list[str]) -> tuple[int, list[str]]:
        """Soft-delete all messages in multiple conversations without deleting them."""
        unique_ids = list(dict.fromkeys(conversation_ids))
        if not unique_ids:
            return 0, []

        conversations = self._session.exec(
            select(Conversation).where(Conversation.id.in_(unique_ids))
        ).all()
        found_ids = {conv.id for conv in conversations}
        missing_ids = [conversation_id for conversation_id in unique_ids if conversation_id not in found_ids]

        messages = self._session.exec(
            select(Message).where(
                Message.conversation_id.in_(found_ids),
                Message.is_deleted.is_(False),
            )
        ).all()
        for msg in messages:
            msg.is_deleted = True

        now = utcnow()
        for conv in conversations:
            conv.last_message_at = None
            conv.updated_at = now

        self._session.flush()
        return len(conversations), missing_ids

    def mark_conversation_read(self, conversation_id: str) -> int:
        """Mark all unread assistant messages in a conversation as read.

        Returns the number of messages that were marked read.
        """
        now = utcnow()
        unread = self._session.exec(
            select(Message).where(
                Message.conversation_id == conversation_id,
                Message.role == "assistant",
                Message.is_deleted.is_(False),
                Message.read_at.is_(None),
            )
        ).all()

        for msg in unread:
            msg.read_at = now

        if unread:
            self._session.flush()

        return len(unread)

    def get_pending_desktop_notifications(
        self, character_id: str | None = None
    ) -> list[dict]:
        """Return assistant messages that haven't had a desktop notification yet.

        These are messages where desktop_notified_at is NULL, role is
        assistant, and is_deleted is False. Optionally filtered by character.
        """
        stmt = select(Message).where(
            Message.role == "assistant",
            Message.is_deleted.is_(False),
            Message.desktop_notified_at.is_(None),
        )

        if character_id is not None:
            stmt = stmt.join(Conversation).where(
                Conversation.character_id == character_id,
            )

        messages = self._session.exec(stmt.order_by(Message.created_at.desc())).all()

        result: list[dict] = []
        for msg in messages:
            conv = self.get_conversation(msg.conversation_id)
            result.append({
                "message_id": msg.id,
                "conversation_id": msg.conversation_id,
                "character_id": conv.character_id if conv else None,
                "content_preview": msg.content[:120],
                "is_proactive": msg.scheduled_message_id is not None,
                "created_at": msg.created_at.isoformat() if msg.created_at else None,
            })

        return result

    def acknowledge_desktop_notification(self, message_id: str) -> bool:
        """Mark a message as having had its desktop notification shown.

        Returns True if the message was found and updated.
        """
        msg = self._session.exec(
            select(Message).where(Message.id == message_id)
        ).first()
        if msg is None:
            return False

        msg.desktop_notified_at = utcnow()
        self._session.flush()
        return True

    # ------------------------------------------------------------------
    # Messages
    # ------------------------------------------------------------------

    def get_messages(
        self,
        conversation_id: str,
        *,
        limit: int = 50,
        before_id: str | None = None,
        include_deleted: bool = False,
    ) -> list[Message]:
        """Return messages for a conversation, newest last.

        Supports cursor-based pagination via *before_id*.
        """
        stmt = select(Message).where(Message.conversation_id == conversation_id)

        if not include_deleted:
            stmt = stmt.where(Message.is_deleted.is_(False))
        if before_id is not None:
            before_msg = self._session.exec(
                select(Message).where(Message.id == before_id)
            ).first()
            if before_msg is not None:
                stmt = stmt.where(Message.created_at < before_msg.created_at)

        stmt = stmt.order_by(col(Message.created_at).desc()).limit(limit)
        messages = list(self._session.exec(stmt).all())
        messages.reverse()  # chronological order
        return messages

    def edit_message(self, message_id: str, new_content: str) -> Message:
        """Edit a message's content."""
        msg = self._session.exec(
            select(Message).where(Message.id == message_id)
        ).first()
        if msg is None:
            raise ValueError(f"Message '{message_id}' not found")

        msg.content = new_content
        msg.edited_at = utcnow()
        self._session.flush()
        return msg

    def recall_message(self, message_id: str) -> Message:
        """Mark a message as recalled while preserving its original text."""
        msg = self._session.exec(
            select(Message).where(Message.id == message_id)
        ).first()
        if msg is None:
            raise ValueError(f"Message '{message_id}' not found")
        if msg.is_deleted:
            raise ValueError(f"Message '{message_id}' is deleted")
        if msg.role != "user":
            raise PermissionError("Only user messages can be recalled")

        if not msg.content.startswith("(recalled) "):
            escaped = msg.content.replace('"', r'\"')
            msg.content = f'(recalled) "{escaped}"'
            msg.edited_at = utcnow()

            conv = self.get_conversation(msg.conversation_id)
            if conv is not None:
                conv.updated_at = utcnow()

            self._session.flush()

        return msg

    def delete_message(self, message_id: str) -> None:
        """Soft-delete a message."""
        msg = self._session.exec(
            select(Message).where(Message.id == message_id)
        ).first()
        if msg is None:
            raise ValueError(f"Message '{message_id}' not found")

        msg.is_deleted = True
        self._session.flush()

def _relative_time(dt: datetime) -> str:
    """Convert a datetime to a human-readable relative time string.

    Examples: "刚刚", "5分钟前", "2小时前", "3天前"
    """
    if dt is None:
        return ""
    from src.chitrika.utils.datetime_helpers import ensure_naive

    now = utcnow()
    db_dt = ensure_naive(dt)
    diff = now - db_dt

    seconds = diff.total_seconds()
    if seconds < 60:
        return "刚刚"
    minutes = int(seconds / 60)
    if minutes < 60:
        return f"{minutes}分钟前"
    hours = int(minutes / 60)
    if hours < 24:
        return f"{hours}小时前"
    days = diff.days
    if days < 30:
        return f"{days}天前"
    months = int(days / 30)
    return f"{months}个月前"
