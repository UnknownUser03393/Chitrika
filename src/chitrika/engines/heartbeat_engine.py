"""Heartbeat Engine — background scheduler for periodic companion maintenance.

Runs every 5 minutes (configurable) and performs:
1. Emotion decay on all characters
2. Memory importance review
3. Loneliness assessment
4. Proactive messaging initiation when loneliness exceeds threshold
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from contextlib import AbstractContextManager
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from sqlmodel import Session, select

from src.chitrika.config import config
from src.chitrika.database import session_scope
from src.chitrika.engines.emotion_engine import EmotionEngine
from src.chitrika.engines.memory_engine import MemoryEngine
from src.chitrika.models.character import Character
from src.chitrika.models.conversation import Conversation
from src.chitrika.models.emotion import EmotionState
from src.chitrika.models.heartbeat import HeartbeatTask, ScheduledMessage
from src.chitrika.models.base import (
    HeartbeatTaskType,
    ProactiveTrigger,
    ScheduledMessageStatus,
    TaskStatus,
)
from src.chitrika.models.message import Message
from src.chitrika.utils.datetime_helpers import hours_between, utcnow

logger = logging.getLogger("chitrika.heartbeat")


class HeartbeatEngine:
    """Periodic background engine that keeps the companion 'alive'.

    Usage::

        engine = HeartbeatEngine()
        engine.start()
        # ... app runs ...
        engine.stop()
    """

    TICK_INTERVAL_MINUTES: int = 5
    LONELINESS_THRESHOLD: float = 0.6

    def __init__(
        self,
        session_factory: Callable[[], AbstractContextManager[Session]] | None = None,
    ):
        self._scheduler = BackgroundScheduler()
        self._session_factory = session_factory or session_scope
        self._running = False
        self._tick_count = 0
        self._last_tick: datetime | None = None

        # Populate from config
        self.TICK_INTERVAL_MINUTES = config.heartbeat_interval_minutes
        self.LONELINESS_THRESHOLD = config.loneliness_threshold

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start the background scheduler."""
        if self._running:
            return

        self._scheduler.add_job(
            self.tick,
            "interval",
            minutes=self.TICK_INTERVAL_MINUTES,
            id="heartbeat_tick",
            replace_existing=True,
            next_run_time=datetime.now(timezone.utc)
            + timedelta(seconds=10),  # first tick after 10s
        )
        self._scheduler.start()
        self._running = True
        logger.info(
            "Heartbeat started — tick every %d min, loneliness threshold %.2f",
            self.TICK_INTERVAL_MINUTES,
            self.LONELINESS_THRESHOLD,
        )

    def stop(self) -> None:
        """Gracefully shut down the scheduler."""
        if not self._running:
            return
        self._scheduler.shutdown(wait=False)
        self._running = False
        logger.info("Heartbeat stopped after %d ticks", self._tick_count)

    @property
    def status(self) -> dict:
        """Return current engine status for the API."""
        return {
            "running": self._running,
            "tick_interval_minutes": self.TICK_INTERVAL_MINUTES,
            "loneliness_threshold": self.LONELINESS_THRESHOLD,
            "tick_count": self._tick_count,
            "last_tick": self._last_tick.isoformat() if self._last_tick else None,
        }

    # ------------------------------------------------------------------
    # Main tick
    # ------------------------------------------------------------------

    def tick(self) -> None:
        """Execute one heartbeat cycle for all enabled characters."""
        self._tick_count += 1
        self._last_tick = utcnow()
        logger.debug("Heartbeat tick #%d", self._tick_count)

        with self._session_factory() as session:
            try:
                characters = session.exec(
                    select(Character).where(Character.enabled.is_(True))
                ).all()

                for character in characters:
                    try:
                        self._process_character(session, character)
                    except Exception:
                        logger.exception(
                            "Heartbeat failed for character %s", character.id
                        )

                # Deliver due scheduled messages (independent of per-character loop)
                self._deliver_due_messages(session)

                session.commit()
            except Exception:
                session.rollback()
                logger.exception("Heartbeat tick #%d failed", self._tick_count)

    def _process_character(self, session: Session, character: Character) -> None:
        """Run the full heartbeat pipeline for a single character."""
        emotion = EmotionEngine(session)
        memory = MemoryEngine(session)

        # 1. Emotion decay
        state = emotion.apply_decay(character.id, config.emotion_decay_rate)
        self._log_task(session, character.id, "emotion_decay", "completed")

        # 2. Memory review
        forgotten_count = memory.decay_importance(character.id)
        if forgotten_count > 0:
            self._log_task(
                session,
                character.id,
                "memory_review",
                "completed",
                result={"forgotten": forgotten_count},
            )
        else:
            self._log_task(session, character.id, "memory_review", "completed")

        # 3. Loneliness check
        from src.chitrika.utils.emotion_algorithms import compute_loneliness

        emotions = state.to_dict()
        loneliness = compute_loneliness(emotions)

        # 4. Proactive messaging
        if loneliness >= self.LONELINESS_THRESHOLD:
            self._initiate_proactive(session, character, state, loneliness)

    # ------------------------------------------------------------------
    # Proactive messaging
    # ------------------------------------------------------------------

    def _initiate_proactive(
        self,
        session: Session,
        character: Character,
        emotion_state: EmotionState,
        loneliness: float,
    ) -> None:
        """Decide whether to schedule a proactive message.

        In MVP mode, if no LLM provider is configured, we use a simple
        heuristic: schedule a message for 15 minutes later if loneliness
        is very high (>0.8), otherwise wait an hour.
        """
        # Check if there's already a pending scheduled message
        pending = session.exec(
            select(ScheduledMessage).where(
                ScheduledMessage.character_id == character.id,
                ScheduledMessage.status == ScheduledMessageStatus.PENDING.value,
            )
        ).first()

        if pending is not None:
            logger.debug("Character %s already has a pending scheduled message", character.id)
            return

        # Find or create a conversation for this character
        conv = session.exec(
            select(Conversation).where(
                Conversation.character_id == character.id,
            ).order_by(Conversation.last_message_at.desc())
        ).first()

        if conv is None:
            # Create a default conversation
            conv = Conversation(character_id=character.id)
            session.add(conv)
            session.flush()

        # Calculate hours since last interaction
        last_msg = session.exec(
            select(Message)
            .where(
                Message.conversation_id == conv.id,
                Message.is_deleted.is_(False),
            )
            .order_by(Message.created_at.desc())
        ).first()

        hours_since_last = 0.0
        if last_msg is not None:
            hours_since_last = hours_between(utcnow(), last_msg.created_at)

        # Decision logic
        if loneliness >= 0.8:
            decision = {"action": "now", "wait_minutes": 0}
        elif loneliness >= self.LONELINESS_THRESHOLD:
            if hours_since_last > 24:
                decision = {"action": "now", "wait_minutes": 0}
            else:
                decision = {"action": "wait", "wait_minutes": 60}
        else:
            decision = {"action": "cancel"}

        # If we have an LLM provider, ask it for a richer decision
        llm_decision = self._ask_llm_for_decision(
            session, character, emotion_state, hours_since_last
        )
        if llm_decision is not None:
            decision = llm_decision

        logger.info(
            "Proactive decision for %s: action=%s loneliness=%.2f",
            character.name,
            decision.get("action"),
            loneliness,
        )

        if decision.get("action") == "cancel":
            self._log_task(
                session, character.id, "proactive_message", "completed",
                result={"decision": "cancel"},
            )
            return

        # Schedule the message
        scheduled = ScheduledMessage(
            character_id=character.id,
            conversation_id=conv.id,
            content=decision.get("message_content"),
            status=ScheduledMessageStatus.PENDING.value,
            trigger_reason=ProactiveTrigger.LONELINESS.value,
            scheduled_at=(
                utcnow()
                + timedelta(minutes=decision.get("wait_minutes", 0))
            ),
            evaluated_at=utcnow(),
            llm_decision_json=json.dumps(decision, ensure_ascii=False),
        )
        session.add(scheduled)

        self._log_task(
            session,
            character.id,
            "proactive_message",
            "completed",
            result={
                "decision": decision.get("action"),
                "scheduled_for": scheduled.scheduled_at.isoformat(),
                "loneliness": loneliness,
            },
        )

    def _deliver_due_messages(self, session: Session) -> None:
        """Convert due ScheduledMessage rows into actual assistant Message rows.

        Checks all PENDING scheduled messages whose scheduled_at is now or
        in the past, creates a corresponding Message in the conversation,
        and marks the scheduled message as SENT.
        """
        now = utcnow()
        due = session.exec(
            select(ScheduledMessage).where(
                ScheduledMessage.status == ScheduledMessageStatus.PENDING.value,
                ScheduledMessage.scheduled_at <= now,
            )
        ).all()

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
            session.add(message)

            # Update conversation timestamps
            conv = session.exec(
                select(Conversation).where(
                    Conversation.id == scheduled.conversation_id,
                )
            ).first()
            if conv is not None:
                conv.last_message_at = message.created_at
                conv.updated_at = now

            scheduled.status = ScheduledMessageStatus.SENT.value
            logger.info(
                "Delivered proactive message %s → conversation %s",
                scheduled.id,
                scheduled.conversation_id,
            )

    def _ask_llm_for_decision(
        self,
        session: Session,
        character: Character,
        emotion_state: EmotionState,
        hours_since_last: float,
    ) -> dict | None:
        """Ask the LLM whether to initiate contact.

        Returns None if no provider is configured or the call fails.
        """
        from src.chitrika.services.provider_service import (
            resolve_provider_for_character,
            create_llm_client,
        )

        provider = resolve_provider_for_character(
            session,
            provider_id=character.provider_id,
            provider_name=character.provider.name if character.provider else None,
        )
        if provider is None or not provider.api_key:
            return None

        client = create_llm_client(provider.api_key, provider.base_url)
        if client is None:
            return None

        try:
            from src.llmproviders.LLMProvider import Message as LLMMessage
            from src.llmproviders.LLMProvider import Model as LLMModel
            from src.chitrika.services.prompt_service import PromptService

            prompt_service = PromptService()
            prompt = prompt_service.build_proactive_prompt(
                character, emotion_state, hours_since_last
            )

            model_name = provider.default_model or "deepseek-chat"
            model = LLMModel(name=model_name)
            response = client.send(
                model,
                [LLMMessage(role="user", content=prompt)],
            )

            # Parse JSON from response
            content = response.content.strip()
            # Strip markdown code fences if present
            if content.startswith("```"):
                content = content.split("\n", 1)[1]
                if content.endswith("```"):
                    content = content[:-3]

            return json.loads(content)

        except Exception:
            logger.exception("Failed to get LLM proactive decision")
            return None

    # ------------------------------------------------------------------
    # Task logging
    # ------------------------------------------------------------------

    def _log_task(
        self,
        session: Session,
        character_id: str,
        task_type: str | HeartbeatTaskType,
        status: str | TaskStatus,
        result: dict | None = None,
    ) -> None:
        """Record a heartbeat task execution in the audit log."""
        task = HeartbeatTask(
            character_id=character_id,
            task_type=HeartbeatTaskType(task_type).value,
            status=TaskStatus(status).value,
            scheduled_at=utcnow(),
            executed_at=utcnow(),
            result_json=json.dumps(result, ensure_ascii=False) if result else None,
        )
        session.add(task)
