"""Build a self-contained LLM generation request in one short DB phase."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from sqlmodel import Session, col, select

from src.chitrika.engines.emotion_engine import EmotionEngine
from src.chitrika.engines.relationship_engine import RelationshipEngine
from src.chitrika.models.character import Character
from src.chitrika.models.conversation import Conversation
from src.chitrika.models.message import Message
from src.chitrika.plugins.api import PromptContext
from src.chitrika.repositories.memory_repository import MemoryRepository
from src.chitrika.repositories.plugin_state_repository import PluginStateRepository
from src.chitrika.services.memory_retrieval_service import MemoryRetrievalService
from src.chitrika.services.plugin_runtime import PluginInvoker, get_plugin_registry
from src.chitrika.services.prompt_service import PromptService
from src.chitrika.services.provider_service import (
    create_llm_client,
    resolve_provider_for_character,
)
from src.chitrika.utils.datetime_helpers import utcnow


@dataclass(slots=True)
class PreparedGeneration:
    conversation_id: str
    character_id: str
    user_content: str
    user_message_id: str
    assistant_message_id: str
    llm: Any
    model_name: str
    llm_messages: list[Any]


class ChatGenerationService:
    """Own prompt preparation without depending on the conversation CRUD engine."""

    def __init__(self, session: Session):
        self.session = session
        self.emotions = EmotionEngine(session)
        self.memories = MemoryRetrievalService(MemoryRepository(session))
        self.relationships = RelationshipEngine(session)
        self.prompts = PromptService()

    def prepare(self, conversation_id: str, user_content: str) -> PreparedGeneration:
        conversation = self.session.get(Conversation, conversation_id)
        if conversation is None:
            raise LookupError("Conversation not found")
        character = self.session.get(Character, conversation.character_id)
        if character is None:
            raise LookupError("Character not found")

        provider = resolve_provider_for_character(
            self.session,
            provider_id=character.provider_id,
            provider_name=(
                character.provider.name if character.provider else "deepseek"
            ),
        )
        llm = create_llm_client(self.session, provider) if provider else None
        model_name = provider.default_model if provider else ""

        user_message = Message(
            conversation_id=conversation_id,
            role="user",
            content=user_content,
        )
        self.session.add(user_message)
        conversation.last_message_at = utcnow()
        conversation.updated_at = utcnow()
        self.session.flush()

        emotion_state = self.emotions.get_or_create_state(character.id)
        self.emotions.apply_decay(character.id)
        memories = self.memories.retrieve(
            character.id,
            query=user_content,
            limit=10,
            track_access=True,
        )
        relationship = self.relationships.get_or_create(character.id)
        history = self._recent_messages(conversation_id)

        system_prompt = self.prompts.build_system_prompt(
            character=character,
            emotion_state=emotion_state,
            memories=memories,
            relationship_state=relationship,
        )
        system_prompt = PluginInvoker(
            PluginStateRepository(self.session), get_plugin_registry()
        ).apply_system_prompt(
            PromptContext(
                character_id=character.id,
                conversation_id=conversation_id,
                user_content=user_content,
                system_prompt=system_prompt,
            )
        )
        llm_messages = self.prompts.build_messages(
            character=character,
            emotion_state=emotion_state,
            memories=memories,
            recent_messages=history,
            system_prompt_override=system_prompt,
            relationship_state=relationship,
        )
        return PreparedGeneration(
            conversation_id=conversation_id,
            character_id=character.id,
            user_content=user_content,
            user_message_id=user_message.id,
            assistant_message_id=str(uuid.uuid4()),
            llm=llm,
            model_name=model_name,
            llm_messages=list(llm_messages),
        )

    def _recent_messages(self, conversation_id: str) -> list[Message]:
        statement = (
            select(Message)
            .where(
                Message.conversation_id == conversation_id,
                Message.is_deleted.is_(False),
            )
            .order_by(col(Message.created_at).desc())
            .limit(30)
        )
        messages = list(self.session.exec(statement).all())
        messages.reverse()
        return messages
