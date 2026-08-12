"""Character-maintenance services used by heartbeat coordination."""

from __future__ import annotations

import json
import logging
from datetime import timedelta

from sqlmodel import Session, select

from src.chitrika.engines.emotion_engine import EmotionEngine
from src.chitrika.engines.settings_engine import SettingsEngine
from src.chitrika.models.base import (
    HeartbeatTaskType,
    ProactiveTrigger,
    ScheduledMessageStatus,
    TaskStatus,
)
from src.chitrika.models.character import Character
from src.chitrika.models.conversation import Conversation
from src.chitrika.models.emotion import EmotionState
from src.chitrika.models.heartbeat import HeartbeatTask, ScheduledMessage
from src.chitrika.models.message import Message
from src.chitrika.repositories.memory_repository import MemoryRepository
from src.chitrika.services.embedding_service import EmbeddingService
from src.chitrika.services.memory_lifecycle_service import MemoryLifecycleService
from src.chitrika.utils.datetime_helpers import hours_between, utcnow
from src.chitrika.utils.emotion_algorithms import compute_loneliness

logger = logging.getLogger("chitrika.heartbeat")


def log_heartbeat_task(
    session: Session,
    character_id: str,
    task_type: str | HeartbeatTaskType,
    status: str | TaskStatus,
    result: dict | None = None,
) -> None:
    session.add(HeartbeatTask(
        character_id=character_id,
        task_type=HeartbeatTaskType(task_type).value,
        status=TaskStatus(status).value,
        scheduled_at=utcnow(),
        executed_at=utcnow(),
        result_json=json.dumps(result, ensure_ascii=False) if result else None,
    ))


class EpisodicMemoryService:
    BATCH_SIZE = 30
    LINE_LIMIT = 160

    def __init__(self, session: Session, lifecycle: MemoryLifecycleService) -> None:
        self.session = session
        self.lifecycle = lifecycle
        self.repository = lifecycle.repository

    def summarize_recent(self, character: Character) -> None:
        """Best-effort summarization without weakening the outer transaction."""
        try:
            if not SettingsEngine(self.session).get("memory_episodic_summary", False):
                return
            batch = self.repository.list_short_term(character.id, limit=self.BATCH_SIZE)
            if len(batch) < self.BATCH_SIZE:
                return
            from src.chitrika.services.provider_service import (
                create_llm_client,
                resolve_provider_for_character,
            )

            provider = resolve_provider_for_character(
                self.session,
                provider_id=character.provider_id,
                provider_name=character.provider.name if character.provider else None,
            )
            if provider is None:
                return
            client = create_llm_client(self.session, provider)
            if client is None:
                return
            summary = self._summarize(character, client, provider, batch)
            if not summary:
                return
            self.lifecycle.store(
                character.id,
                "episodic",
                summary,
                importance=0.75,
                source_message_id=batch[-1].source_message_id,
            )
            self.lifecycle.archive([memory.id for memory in batch])
            log_heartbeat_task(
                self.session,
                character.id,
                "episodic_summary",
                "completed",
                {"batch_size": len(batch), "summary_len": len(summary)},
            )
        except Exception:
            logger.exception("Episodic summarization failed for %s", character.id)

    @classmethod
    def _summarize(cls, character, client, provider, batch: list) -> str:
        from src.llmproviders.LLMProvider import Message as LLMMessage
        from src.llmproviders.LLMProvider import Model as LLMModel

        snippets = "\n".join(
            f"- {memory.content[:cls.LINE_LIMIT]}" for memory in reversed(batch)
        )
        system = (
            f"You are the long-term memory of {character.display_name}, an AI companion. "
            "Write ONE concise narrative memory (1-3 sentences) in first person from "
            "the snippets. Keep stable, important details and output only the narrative."
        )
        response = client.send(
            LLMModel(name=provider.default_model or "deepseek-chat"),
            [LLMMessage(role="system", content=system), LLMMessage(role="user", content=snippets)],
        )
        return (response.content or "").strip()[:500]


class ProactiveMessagingService:
    COOLDOWN_HOURS = 12

    def __init__(self, session: Session, loneliness_threshold: float) -> None:
        self.session = session
        self.loneliness_threshold = loneliness_threshold

    def consider(
        self,
        character: Character,
        emotion_state: EmotionState,
        loneliness: float,
    ) -> None:
        pending = self.session.exec(select(ScheduledMessage).where(
            ScheduledMessage.character_id == character.id,
            ScheduledMessage.status == ScheduledMessageStatus.PENDING.value,
        )).first()
        if pending is not None:
            return
        recent_sent = self.session.exec(select(ScheduledMessage).where(
            ScheduledMessage.character_id == character.id,
            ScheduledMessage.status == ScheduledMessageStatus.SENT.value,
            ScheduledMessage.scheduled_at >= utcnow() - timedelta(hours=self.COOLDOWN_HOURS),
        )).first()
        if recent_sent is not None:
            return
        conversation = self.session.exec(
            select(Conversation)
            .where(Conversation.character_id == character.id)
            .order_by(Conversation.last_message_at.desc())
        ).first()
        if conversation is None:
            conversation = Conversation(character_id=character.id)
            self.session.add(conversation)
            self.session.flush()
        last_message = self.session.exec(
            select(Message)
            .join(Conversation)
            .where(
                Conversation.character_id == character.id,
                Message.role == "user",
                Message.is_deleted.is_(False),
            )
            .order_by(Message.created_at.desc())
        ).first()
        last_at = last_message.created_at if last_message else character.created_at
        hours_since_last = hours_between(utcnow(), last_at)
        if loneliness >= 0.8 or (loneliness >= self.loneliness_threshold and hours_since_last > 24):
            decision: dict = {"action": "now", "wait_minutes": 0}
        elif loneliness >= self.loneliness_threshold:
            decision = {"action": "wait", "wait_minutes": 60}
        else:
            decision = {"action": "cancel"}
        llm_decision = self._ask_llm(character, emotion_state, hours_since_last)
        if llm_decision is not None:
            decision = llm_decision
        if decision.get("action") not in {"now", "wait", "cancel"}:
            decision = {"action": "cancel"}
        if decision["action"] == "cancel":
            log_heartbeat_task(
                self.session, character.id, "proactive_message", "completed", {"decision": "cancel"}
            )
            return
        try:
            wait_minutes = int(decision.get("wait_minutes", 0))
        except (TypeError, ValueError):
            wait_minutes = 0
        wait_minutes = max(0, min(wait_minutes, 24 * 60))
        content = str(decision.get("message_content") or "").strip()
        if not content:
            content = self.fallback_message(character, emotion_state, hours_since_last)
        decision.update(wait_minutes=wait_minutes, message_content=content)
        scheduled = ScheduledMessage(
            character_id=character.id,
            conversation_id=conversation.id,
            content=content,
            status=ScheduledMessageStatus.PENDING.value,
            trigger_reason=ProactiveTrigger.LONELINESS.value,
            scheduled_at=utcnow() + timedelta(minutes=wait_minutes),
            evaluated_at=utcnow(),
            llm_decision_json=json.dumps(decision, ensure_ascii=False),
        )
        self.session.add(scheduled)
        log_heartbeat_task(
            self.session,
            character.id,
            "proactive_message",
            "completed",
            {
                "decision": decision["action"],
                "scheduled_for": scheduled.scheduled_at.isoformat(),
                "loneliness": loneliness,
            },
        )

    @staticmethod
    def fallback_message(
        character: Character,
        emotion_state: EmotionState,
        hours_since_last: float,
    ) -> str:
        del character
        emotions = emotion_state.to_dict()
        if emotions.get("sadness", 0.0) >= 0.45:
            return "在吗。。。有点想你"
        if emotions.get("anticipation", 0.0) >= 0.45:
            return "喂"
        if hours_since_last >= 24:
            return "还活着吗"
        return "嗯？"

    def _ask_llm(
        self, character: Character, emotion_state: EmotionState, hours_since_last: float
    ) -> dict | None:
        from src.chitrika.services.provider_service import (
            create_llm_client,
            resolve_provider_for_character,
        )

        provider = resolve_provider_for_character(
            self.session,
            provider_id=character.provider_id,
            provider_name=character.provider.name if character.provider else None,
        )
        if provider is None:
            return None
        client = create_llm_client(self.session, provider)
        if client is None:
            return None
        try:
            from src.chitrika.services.prompt_service import PromptService
            from src.llmproviders.LLMProvider import Message as LLMMessage
            from src.llmproviders.LLMProvider import Model as LLMModel

            recent = self.session.exec(
                select(Message)
                .join(Conversation)
                .where(
                    Conversation.character_id == character.id,
                    Message.is_deleted.is_(False),
                )
                .order_by(Message.created_at.desc())
                .limit(6)
            ).all()
            lines = [
                f"{'用户' if message.role == 'user' else character.display_name}: {message.content}"
                for message in reversed(recent)
            ]
            prompt = PromptService().build_proactive_prompt(
                character,
                emotion_state,
                hours_since_last,
                recent_messages=lines or None,
            )
            response = client.send(
                LLMModel(name=provider.default_model or "deepseek-chat"),
                [LLMMessage(role="user", content=prompt)],
            )
            content = response.content.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[1]
                if content.endswith("```"):
                    content = content[:-3]
            value = json.loads(content)
            return value if isinstance(value, dict) else None
        except Exception:
            logger.exception("Failed to get LLM proactive decision")
            return None


class ScheduledMessageDeliveryService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def deliver_due(self) -> int:
        now = utcnow()
        due = self.session.exec(select(ScheduledMessage).where(
            ScheduledMessage.status == ScheduledMessageStatus.PENDING.value,
            ScheduledMessage.scheduled_at <= now,
        )).all()
        delivered = 0
        for scheduled in due:
            if not scheduled.content:
                scheduled.status = ScheduledMessageStatus.CANCELLED.value
                scheduled.cancelled_at = now
                continue
            message = Message(
                conversation_id=scheduled.conversation_id,
                role="assistant",
                content=scheduled.content,
                scheduled_message_id=scheduled.id,
            )
            self.session.add(message)
            conversation = self.session.get(Conversation, scheduled.conversation_id)
            if conversation is not None:
                conversation.last_message_at = message.created_at
                conversation.updated_at = now
            scheduled.status = ScheduledMessageStatus.SENT.value
            delivered += 1
        return delivered


class CharacterMaintenanceService:
    PROACTIVE_COOLDOWN_MINUTES = 30

    def __init__(
        self,
        session: Session,
        *,
        decay_rate: float,
        loneliness_threshold: float,
    ) -> None:
        self.session = session
        self.decay_rate = decay_rate
        self.loneliness_threshold = loneliness_threshold

    def maintain(self, character: Character) -> None:
        state = EmotionEngine(self.session).apply_decay(character.id, self.decay_rate)
        log_heartbeat_task(self.session, character.id, "emotion_decay", "completed")
        repository = MemoryRepository(self.session)
        lifecycle = MemoryLifecycleService(repository)
        forgotten = lifecycle.decay(character.id)
        log_heartbeat_task(
            self.session,
            character.id,
            "memory_review",
            "completed",
            {"forgotten": forgotten} if forgotten else None,
        )
        EmbeddingService(repository).backfill(character.id)
        EpisodicMemoryService(self.session, lifecycle).summarize_recent(character)
        last_user_message = self.session.exec(
            select(Message)
            .join(Conversation)
            .where(
                Conversation.character_id == character.id,
                Message.role == "user",
                Message.is_deleted.is_(False),
            )
            .order_by(Message.created_at.desc())
        ).first()
        last_at = last_user_message.created_at if last_user_message else character.created_at
        idle_hours = max(0.0, hours_between(utcnow(), last_at))
        loneliness = compute_loneliness(state.to_dict(), idle_hours)
        if (
            loneliness >= self.loneliness_threshold
            and idle_hours * 60 >= self.PROACTIVE_COOLDOWN_MINUTES
        ):
            ProactiveMessagingService(
                self.session, self.loneliness_threshold
            ).consider(character, state, loneliness)
