"""Debug Engine — force development-only companion actions."""

from __future__ import annotations

import json
import logging
from datetime import timedelta

from sqlmodel import Session, select

from src.chitrika.engines.emotion_engine import EmotionEngine
from src.chitrika.models.base import ProactiveTrigger, ScheduledMessageStatus
from src.chitrika.models.character import Character
from src.chitrika.models.conversation import Conversation
from src.chitrika.models.heartbeat import ScheduledMessage
from src.chitrika.models.message import Message
from src.chitrika.schemas.debug_schemas import DebugActionRequest
from src.chitrika.utils.datetime_helpers import utcnow
from src.chitrika.utils.emotion_algorithms import compute_loneliness
from src.chitrika.services.heartbeat_services import ProactiveMessagingService

logger = logging.getLogger("chitrika.debug")


class DebugEngine:
    """Execute explicit debug actions against a character.

    These methods intentionally bypass normal heartbeat guards such as pending
    scheduled messages and proactive cooldowns, because debug actions are
    manual operator requests.
    """

    def __init__(self, session: Session):
        self.session = session

    def run_action(self, action: str, body: DebugActionRequest) -> dict:
        """Dispatch a named debug action."""
        if action == "loneliness_proactive_message":
            return self.force_loneliness_proactive_message(body)
        raise ValueError(f"Unsupported debug action: {action}")

    def force_loneliness_proactive_message(self, body: DebugActionRequest) -> dict:
        """Queue and optionally deliver a loneliness proactive message now."""
        character = self._get_character(body.character_id)
        conversation = self._resolve_conversation(character.id, body.conversation_id)

        emotion = EmotionEngine(self.session).get_or_create_state(character.id)
        loneliness = compute_loneliness(emotion.to_dict(), hours_since_interaction=24.0)

        content = (body.content or "").strip()
        llm_used = False
        if body.use_llm:
            llm_content = self._generate_llm_content(character, emotion, conversation.id)
            if llm_content is not None:
                content = llm_content
                llm_used = True
        if not content:
            content = ProactiveMessagingService.fallback_message(
                character,
                emotion,
                hours_since_last=24.0,
            )
        now = utcnow()
        decision = {
            "action": "now",
            "wait_minutes": 0,
            "message_content": content,
            "debug_action": "loneliness_proactive_message",
        }

        scheduled = ScheduledMessage(
            character_id=character.id,
            conversation_id=conversation.id,
            content=content,
            status=ScheduledMessageStatus.PENDING.value,
            trigger_reason=ProactiveTrigger.LONELINESS.value,
            scheduled_at=now - timedelta(seconds=1) if body.deliver_now else now,
            evaluated_at=now,
            llm_decision_json=json.dumps(decision, ensure_ascii=False),
        )
        self.session.add(scheduled)
        self.session.flush()

        character_id = character.id
        conversation_id = conversation.id
        scheduled_message_id = scheduled.id

        delivered_message_id = None
        if body.deliver_now:
            delivered_message_id = self._deliver_scheduled_message(scheduled)
            self.session.flush()

        self.session.flush()
        logger.info(
            "Debug action %s forced for character %s",
            "loneliness_proactive_message",
            character_id,
        )

        return {
            "action": "loneliness_proactive_message",
            "status": "ok",
            "character_id": character_id,
            "conversation_id": conversation_id,
            "scheduled_message_id": scheduled_message_id,
            "delivered_message_id": delivered_message_id,
            "delivered": delivered_message_id is not None,
            "details": {
                "loneliness": loneliness,
                "trigger_reason": ProactiveTrigger.LONELINESS.value,
                "forced": True,
                "deliver_now": body.deliver_now,
                "llm_used": llm_used,
                "content": content,
            },
        }

    def _deliver_scheduled_message(self, scheduled: ScheduledMessage) -> str | None:
        if not scheduled.content:
            scheduled.status = ScheduledMessageStatus.CANCELLED.value
            scheduled.cancelled_at = utcnow()
            return None

        now = utcnow()
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
        return message.id

    def _generate_llm_content(
        self,
        character: Character,
        emotion_state,
        conversation_id: str,
    ) -> str | None:
        """Ask the LLM to write a context-aware proactive message.

        Returns None when no provider is configured or the call fails.
        """
        from src.chitrika.services.provider_service import (
            resolve_provider_for_character,
            create_llm_client,
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
            from src.llmproviders.LLMProvider import Message as LLMMessage
            from src.llmproviders.LLMProvider import Model as LLMModel

            # Grab last few messages for context
            recent = self.session.exec(
                select(Message)
                .where(
                    Message.conversation_id == conversation_id,
                    Message.is_deleted.is_(False),
                )
                .order_by(Message.created_at.desc())
                .limit(6)
            ).all()
            recent_lines = [
                f"{'用户' if m.role == 'user' else character.display_name}: {m.content}"
                for m in reversed(recent)
            ]
            context_block = ""
            if recent_lines:
                context_block = "最近的对话：\n" + "\n".join(
                    f"  {line}" for line in recent_lines
                ) + "\n\n"

            emotions = emotion_state.to_dict()
            mood = ""
            try:
                from src.chitrika.utils.emotion_algorithms import compute_mood
                mood = f"心情：{compute_mood(emotions)}。"
            except Exception:
                pass

            prompt = (
                f"你是{character.display_name}。{mood}\n"
                f"{context_block}"
                f"用户突然不回复了，消失了。你现在有点疑惑/在意，想发一条消息问一下。\n"
                f"注意：这不是续写对话，而是你发现对方突然没声了，主动去戳他一下。\n"
                f"消息要短、自然、符合你的性格。像真人发现对方掉线了一样。\n"
                f"只回复消息内容，不要加引号或前缀。"
            )

            model_name = provider.default_model or "deepseek-chat"
            model = LLMModel(name=model_name)
            response = client.send(
                model,
                [LLMMessage(role="user", content=prompt)],
            )
            return response.content.strip()

        except Exception:
            logger.exception("LLM content generation failed for debug action")
            return None

    def _get_character(self, character_id: str) -> Character:
        character = self.session.exec(
            select(Character).where(
                Character.id == character_id,
                Character.enabled.is_(True),
            )
        ).first()
        if character is None:
            raise ValueError("Character not found")
        return character

    def _resolve_conversation(
        self,
        character_id: str,
        conversation_id: str | None,
    ) -> Conversation:
        if conversation_id is not None:
            conversation = self.session.exec(
                select(Conversation).where(
                    Conversation.id == conversation_id,
                    Conversation.character_id == character_id,
                )
            ).first()
            if conversation is None:
                raise ValueError("Conversation not found for character")
            return conversation

        conversation = self.session.exec(
            select(Conversation)
            .where(Conversation.character_id == character_id)
            .order_by(Conversation.last_message_at.desc())
        ).first()
        if conversation is not None:
            return conversation

        conversation = Conversation(character_id=character_id)
        self.session.add(conversation)
        self.session.flush()
        return conversation
