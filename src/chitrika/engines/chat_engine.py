"""Chat Engine — conversation management, message handling, and LLM streaming.

Orchestrates the full send-message flow:
1. Persist user message
2. Load character + emotion + memories + history
3. Build enriched system prompt
4. Stream from LLM → SSE chunks
5. Save assistant response
6. Post-process: update emotions, extract memories
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Generator
from datetime import datetime

from sqlalchemy import and_, func
from sqlmodel import Session, col, select

from src.chitrika.engines.emotion_engine import EmotionEngine
from src.chitrika.engines.memory_engine import MemoryEngine
from src.chitrika.engines.plugin_engine import PluginEngine
from src.chitrika.engines.relationship_engine import RelationshipEngine
from src.chitrika.models.character import Character
from src.chitrika.models.conversation import Conversation
from src.chitrika.models.heartbeat import ScheduledMessage
from src.chitrika.models.memory import Memory
from src.chitrika.models.message import Message
from src.chitrika.services.prompt_service import PromptService
from src.chitrika.plugins.api import PromptContext
from src.chitrika.utils import sse
from src.chitrika.utils.datetime_helpers import utcnow

logger = logging.getLogger("chitrika.chat")


class ChatEngine:
    """High-level chat operations with LLM integration."""

    def __init__(self, session: Session, llm_provider=None, model_name: str = ""):
        self._session = session
        self._llm = llm_provider  # OpenAIProvider-compatible, injected
        self._model_name = model_name
        self._emotion = EmotionEngine(session)
        self._memory = MemoryEngine(session)
        self._relationship = RelationshipEngine(session)
        self._prompt = PromptService()

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
        self._session.commit()
        self._session.refresh(conv)
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

        self._session.commit()
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

        self._session.commit()
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
            self._session.commit()

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
        self._session.commit()
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
        self._session.commit()
        self._session.refresh(msg)
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

            self._session.commit()
            self._session.refresh(msg)

        return msg

    def delete_message(self, message_id: str) -> None:
        """Soft-delete a message."""
        msg = self._session.exec(
            select(Message).where(Message.id == message_id)
        ).first()
        if msg is None:
            raise ValueError(f"Message '{message_id}' not found")

        msg.is_deleted = True
        self._session.commit()

    # ------------------------------------------------------------------
    # Send message (streaming — generator-based)
    # ------------------------------------------------------------------

    def stream_response(
        self,
        conversation_id: str,
        user_content: str,
    ) -> Generator[str, None, None]:
        """Send a user message and yield SSE events for the LLM response.

        Yields strings like:
            event: message
            data: {"type":"start","message_id":"..."}

        Usage in FastAPI::

            StreamingResponse(
                engine.stream_response(conv_id, content),
                media_type="text/event-stream",
            )

        Cleaning up (saving assistant message) happens *after* the generator
        exhausts. If the client disconnects mid-stream, the last yield is
        a 'done' event that triggers finalization.
        """
        # 1. Load and validate conversation
        conv = self.get_conversation(conversation_id)
        if conv is None:
            yield sse.sse_error(f"Conversation '{conversation_id}' not found")
            return

        # 2. Load character
        character = self._session.exec(
            select(Character).where(Character.id == conv.character_id)
        ).first()
        if character is None:
            yield sse.sse_error("Character not found for conversation")
            return

        # 3. Save user message
        user_msg = Message(
            conversation_id=conversation_id,
            role="user",
            content=user_content,
        )
        self._session.add(user_msg)
        conv.last_message_at = utcnow()
        conv.updated_at = utcnow()
        self._session.commit()

        # 4. Load context
        try:
            emotion_state = self._emotion.get_or_create_state(character.id)
            # Apply decay before generating
            self._emotion.apply_decay(character.id)

            memories = self._memory.get_relevant(
                character.id, limit=10, track_access=True
            )
            relationship_state = self._relationship.get_or_create(character.id)
            history = self.get_messages(conversation_id, limit=30)

            # 5. Build prompt
            system_prompt = self._prompt.build_system_prompt(
                character=character,
                emotion_state=emotion_state,
                memories=memories,
                relationship_state=relationship_state,
            )
            system_prompt = PluginEngine(self._session).apply_system_prompt(
                PromptContext(
                    character_id=character.id,
                    conversation_id=conversation_id,
                    user_content=user_content,
                    system_prompt=system_prompt,
                )
            )
            llm_messages = self._prompt.build_messages(
                character=character,
                emotion_state=emotion_state,
                memories=memories,
                recent_messages=history,
                system_prompt_override=system_prompt,
                relationship_state=relationship_state,
            )
        except Exception:
            logger.exception("Failed to build prompt")
            yield sse.sse_error("Failed to build prompt context")
            return

        # 6. Stream from LLM — one response = one message bubble.
        # Newlines inside the response are preserved as line breaks
        # within the bubble (via CSS whitespace-pre-wrap), not split
        # into separate messages.
        assistant_msg_id = str(uuid.uuid4())
        full_response: list[str] = []
        error_occurred = False

        try:
            yield sse.sse_start(assistant_msg_id, user_message_id=user_msg.id)

            if self._llm is None:
                # --- No LLM provider: return echo for testing ---
                echo = f"[echo] {user_content}"
                full_response.append(echo)
                yield sse.sse_content(echo)
            else:
                try:
                    from src.llmproviders.LLMProvider import Model as LLMModel

                    model_obj = LLMModel(name=self._model_name or "deepseek-chat")
                    for chunk in self._llm.stream(model_obj, llm_messages):
                        if chunk.content:
                            full_response.append(chunk.content)
                            yield sse.sse_content(chunk.content)
                except Exception as exc:
                    logger.exception("LLM streaming failed")
                    error_occurred = True
                    yield sse.sse_error(str(exc))
                    return

            # 7. Save assistant message
            content = "".join(full_response)
            if not error_occurred:
                assistant_msg = Message(
                    id=assistant_msg_id,
                    conversation_id=conversation_id,
                    role="assistant",
                    content=content,
                )
                self._session.add(assistant_msg)
                conv.last_message_at = utcnow()
                conv.updated_at = utcnow()
                self._session.commit()

            yield sse.sse_done(assistant_msg_id, {})

        except GeneratorExit:
            # Client disconnected — save whatever we have so far
            partial = "".join(full_response).strip()
            if partial:
                assistant_msg = Message(
                    id=assistant_msg_id,
                    conversation_id=conversation_id,
                    role="assistant",
                    content=partial,
                )
                self._session.add(assistant_msg)
                conv.last_message_at = utcnow()
                conv.updated_at = utcnow()
                self._session.commit()
            return

        # 8. Post-processing: update emotions
        try:
            self._post_process_emotions(character.id, user_content, "".join(full_response))
        except Exception:
            logger.exception("Post-process emotion update failed")

        # 9. Post-processing: extract memories
        try:
            self._post_process_memories(character.id, user_content, "".join(full_response), user_msg.id)
        except Exception:
            logger.exception("Post-process memory extraction failed")

        # 10. Post-processing: advance the long-lived relationship state
        try:
            self._relationship.record_interaction(character.id, user_content)
        except Exception:
            logger.exception("Post-process relationship update failed")

    # ------------------------------------------------------------------
    # Post-processing helpers
    # ------------------------------------------------------------------

    def _post_process_emotions(
        self,
        character_id: str,
        user_text: str,
        assistant_text: str,
    ) -> None:
        """Apply ONNX emotion deltas, falling back to the lightweight local classifier."""
        from src.chitrika.utils.emotion_nlp import classify_emotion_delta
        from src.chitrika.utils.emotion_onnx import classify_with_onnx_if_available

        deltas = classify_with_onnx_if_available(user_text, assistant_text)
        if deltas is None:
            deltas = classify_emotion_delta(user_text, assistant_text)

        if deltas:
            self._emotion.update_emotion(character_id, deltas)

    def _post_process_memories(
        self,
        character_id: str,
        user_text: str,
        assistant_text: str,
        source_message_id: str,
    ) -> None:
        """Extract short-term context and durable user facts.

        This deliberately uses conservative patterns: a missed fact is less
        damaging than confidently remembering something the user never said.
        Repeated durable facts are reinforced by ``MemoryEngine.store``.
        """
        # Store user message as short-term memory
        if len(user_text) > 5:
            emotional_valence = 0.0
            positive_indicators = [
                "喜欢", "爱", "好", "开心", "棒", "厉害",
                "love", "good", "great", "happy",
            ]
            negative_indicators = [
                "讨厌", "烦", "难过", "伤心", "生气",
                "hate", "bad", "sad", "angry",
            ]

            for word in positive_indicators:
                if word in user_text:
                    emotional_valence += 0.2
            for word in negative_indicators:
                if word in user_text:
                    emotional_valence -= 0.2

            importance = abs(emotional_valence) if emotional_valence != 0 else 0.25

            self._memory.store(
                character_id=character_id,
                memory_type="short_term",
                content=user_text,
                importance=min(1.0, importance),
                emotional_valence=max(-1.0, min(1.0, emotional_valence)),
                source_message_id=source_message_id,
            )

        # Promote explicit self-disclosures into durable, compact facts.  Keep
        # this local and deterministic so memory still works without an LLM.
        import re

        fact_patterns = [
            (r"(?:我叫|我的名字是)\s*([^，。！？,.!?\n]{1,30})", "用户的名字是{0}"),
            (r"我(?:很|最|也)?喜欢\s*([^，。！？,.!?\n]{1,50})", "用户喜欢{0}"),
            (r"我(?:不喜欢|讨厌)\s*([^，。！？,.!?\n]{1,50})", "用户不喜欢{0}"),
            (r"我住在\s*([^，。！？,.!?\n]{1,50})", "用户住在{0}"),
            (r"我的生日是\s*([^，。！？,.!?\n]{1,30})", "用户的生日是{0}"),
            (r"我在\s*([^，。！？,.!?\n]{1,40})\s*(?:工作|上班)", "用户在{0}工作"),
            (r"\bmy name is\s+([^,.!?\n]{1,30})", "The user's name is {0}"),
            (r"\bi (?:really )?(?:like|love)\s+([^,.!?\n]{1,50})", "The user likes {0}"),
            (r"\bi (?:dislike|hate)\s+([^,.!?\n]{1,50})", "The user dislikes {0}"),
            (r"\bi live in\s+([^,.!?\n]{1,50})", "The user lives in {0}"),
        ]
        for pattern, template in fact_patterns:
            for match in re.finditer(pattern, user_text, flags=re.IGNORECASE):
                value = match.group(1).strip(" 的了呢啊呀 ")
                if not value:
                    continue
                self._memory.store(
                    character_id=character_id,
                    memory_type="long_term",
                    content=template.format(value),
                    importance=0.65,
                    emotional_valence=None,
                    source_message_id=source_message_id,
                )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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
