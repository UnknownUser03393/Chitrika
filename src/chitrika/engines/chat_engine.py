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

from sqlmodel import Session, col, select

from src.chitrika.engines.emotion_engine import EmotionEngine
from src.chitrika.engines.memory_engine import MemoryEngine
from src.chitrika.models.character import Character
from src.chitrika.models.conversation import Conversation
from src.chitrika.models.message import Message
from src.chitrika.services.prompt_service import PromptService
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
        result: list[dict] = []

        for conv in conversations:
            char = self._session.exec(
                select(Character).where(Character.id == conv.character_id)
            ).first()

            last_msg = self._session.exec(
                select(Message)
                .where(
                    Message.conversation_id == conv.id,
                    Message.is_deleted.is_(False),
                )
                .order_by(col(Message.created_at).desc())
            ).first()

            result.append({
                "id": conv.id,
                "name": char.display_name if char else "Unknown",
                "initials": char.initials if char else "?",
                "color": char.color if char else "#4FA3E3",
                "lastMessage": last_msg.content[:100] if last_msg else "",
                "time": _relative_time(last_msg.created_at) if last_msg else "",
                "unread": 0,  # TODO: track read status
                "pinned": False,
                "character_id": conv.character_id,
            })

        return result

    def delete_conversation(self, conversation_id: str) -> None:
        """Delete a conversation and all its messages."""
        conv = self.get_conversation(conversation_id)
        if conv is None:
            raise ValueError(f"Conversation '{conversation_id}' not found")

        # Delete all messages
        messages = self._session.exec(
            select(Message).where(Message.conversation_id == conversation_id)
        ).all()
        for msg in messages:
            self._session.delete(msg)

        self._session.delete(conv)
        self._session.commit()

    def clear_conversation_messages(self, conversation_id: str) -> None:
        """Soft-delete all messages in a conversation without deleting it."""
        conv = self.get_conversation(conversation_id)
        if conv is None:
            raise ValueError(f"Conversation '{conversation_id}' not found")

        messages = self._session.exec(
            select(Message).where(
                Message.conversation_id == conversation_id,
                Message.is_deleted.is_(False),
            )
        ).all()
        for msg in messages:
            msg.is_deleted = True

        conv.last_message_at = None
        conv.updated_at = utcnow()
        self._session.commit()

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
            yield sse.sse_error(f"Character not found for conversation")
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

            memories = self._memory.get_relevant(character.id, limit=10)
            history = self.get_messages(conversation_id, limit=30)

            # 5. Build prompt
            llm_messages = self._prompt.build_messages(
                character=character,
                emotion_state=emotion_state,
                memories=memories,
                recent_messages=history,
            )
        except Exception:
            logger.exception("Failed to build prompt")
            yield sse.sse_error("Failed to build prompt context")
            return

        # 6. Stream from LLM
        assistant_msg_id = str(uuid.uuid4())
        full_response: list[str] = []
        error_occurred = False

        try:
            yield sse.sse_start(assistant_msg_id)

            # Create temporary assistant message placeholder
            assistant_msg = Message(
                id=assistant_msg_id,
                conversation_id=conversation_id,
                role="assistant",
                content="",  # fill as we stream
            )

            if self._llm is None:
                # --- No LLM provider: return echo for testing ---
                echo = f"[echo] {user_content}"
                full_response.append(echo)
                yield sse.sse_content(echo)
            else:
                model = self._llm.__class__.__module__  # use first available model
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

            # 7. Save assistant message
            assistant_msg.content = "".join(full_response)
            if not error_occurred:
                self._session.add(assistant_msg)
                conv.last_message_at = utcnow()
                conv.updated_at = utcnow()
                self._session.commit()

            usage = {}
            yield sse.sse_done(assistant_msg_id, usage)

        except GeneratorExit:
            # Client disconnected — save whatever we have so far
            assistant_msg.content = "".join(full_response)
            if assistant_msg.content:
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

    # ------------------------------------------------------------------
    # Post-processing helpers
    # ------------------------------------------------------------------

    def _post_process_emotions(
        self,
        character_id: str,
        user_text: str,
        assistant_text: str,
    ) -> None:
        """Apply emotion deltas based on the interaction content.

        Simple keyword-based heuristics for MVP.
        Future: use a lightweight classifier or LLM call.
        """
        deltas: dict[str, float] = {}

        # Positive keywords
        positive = ["谢谢", "爱你", "喜欢", "哈哈", "hhh", "好", "棒", "厉害",
                     "thank", "love", "good", "great", "nice"]
        for word in positive:
            if word.lower() in user_text.lower():
                deltas["joy"] = deltas.get("joy", 0.0) + 0.05
                deltas["trust"] = deltas.get("trust", 0.0) + 0.03

        # Negative keywords
        negative = ["讨厌", "滚", "傻逼", "烦", "生气", "bad", "hate", "stupid"]
        for word in negative:
            if word.lower() in user_text.lower():
                deltas["anger"] = deltas.get("anger", 0.0) + 0.1
                deltas["trust"] = deltas.get("trust", 0.0) - 0.05

        # Sadness keywords
        sad = ["难过", "伤心", "哭", "sad", "cry", "lonely", "孤独"]
        for word in sad:
            if word.lower() in user_text.lower():
                deltas["sadness"] = deltas.get("sadness", 0.0) + 0.08

        # Surprise keywords
        surprise_words = ["我靠", "我艹", "天哪", "wow", "omg", "卧槽"]
        for word in surprise_words:
            if word.lower() in user_text.lower():
                deltas["surprise"] = deltas.get("surprise", 0.0) + 0.1

        # Long user message → anticipation (user is engaged)
        if len(user_text) > 100:
            deltas["joy"] = deltas.get("joy", 0.0) + 0.03
            deltas["anticipation"] = deltas.get("anticipation", 0.0) + 0.05
        # Very short user message (e.g. "嗯") → slight dip
        elif len(user_text) < 5:
            deltas["anticipation"] = deltas.get("anticipation", 0.0) - 0.02

        if deltas:
            self._emotion.update_emotion(character_id, deltas)

    def _post_process_memories(
        self,
        character_id: str,
        user_text: str,
        assistant_text: str,
        source_message_id: str,
    ) -> None:
        """Extract potential memories from the interaction.

        Simple heuristics for MVP:
        - User messages with declarative patterns ("我喜欢...", "我有...", etc.)
        - Store as short-term memory with moderate importance.
        """
        # Store user message as short-term memory
        if len(user_text) > 5:
            emotional_valence = 0.0
            positive_indicators = ["喜欢", "爱", "好", "开心", "棒", "厉害",
                                   "love", "good", "great", "happy"]
            negative_indicators = ["讨厌", "烦", "难过", "伤心", "生气",
                                   "hate", "bad", "sad", "angry"]

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
