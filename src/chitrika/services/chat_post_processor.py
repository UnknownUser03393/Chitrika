"""Post-generation emotion, memory, and relationship updates."""

from __future__ import annotations

import json
import re

from sqlmodel import Session

from src.chitrika.engines.emotion_engine import EmotionEngine
from src.chitrika.engines.relationship_engine import RelationshipEngine
from src.chitrika.engines.settings_engine import SettingsEngine
from src.chitrika.repositories.memory_repository import MemoryRepository
from src.chitrika.services.memory_lifecycle_service import MemoryLifecycleService


class ChatPostProcessor:
    """Apply secondary state changes after an assistant reply is durable."""

    def __init__(self, session: Session, llm=None, model_name: str = ""):
        self.session = session
        self.llm = llm
        self.model_name = model_name
        self.emotions = EmotionEngine(session)
        self.memories = MemoryLifecycleService(MemoryRepository(session))
        self.relationships = RelationshipEngine(session)

    def process(
        self,
        character_id: str,
        user_text: str,
        assistant_text: str,
        source_message_id: str,
    ) -> None:
        self.update_emotions(character_id, user_text, assistant_text)
        self.extract_memories(
            character_id, user_text, assistant_text, source_message_id
        )
        if self.llm is not None and SettingsEngine(self.session).get(
            "memory_llm_extraction", False
        ):
            self.extract_memories_with_llm(
                character_id, user_text, assistant_text, source_message_id
            )
        self.relationships.record_interaction(character_id, user_text)

    def update_emotions(
        self, character_id: str, user_text: str, assistant_text: str
    ) -> None:
        from src.chitrika.utils.emotion_nlp import classify_emotion_delta
        from src.chitrika.utils.emotion_onnx import classify_with_onnx_if_available

        deltas = classify_with_onnx_if_available(user_text, assistant_text)
        if deltas is None:
            deltas = classify_emotion_delta(user_text, assistant_text)
        if deltas:
            self.emotions.update_emotion(character_id, deltas)

    def extract_memories(
        self,
        character_id: str,
        user_text: str,
        assistant_text: str,
        source_message_id: str,
    ) -> None:
        del assistant_text  # deterministic extraction currently uses the user turn
        if len(user_text) > 5:
            emotional_valence = 0.0
            for word in (
                "喜欢", "爱", "好", "开心", "棒", "厉害",
                "love", "good", "great", "happy",
            ):
                if word in user_text:
                    emotional_valence += 0.2
            for word in (
                "讨厌", "烦", "难过", "伤心", "生气",
                "hate", "bad", "sad", "angry",
            ):
                if word in user_text:
                    emotional_valence -= 0.2
            importance = abs(emotional_valence) or 0.25
            self.memories.store(
                character_id=character_id,
                memory_type="short_term",
                content=user_text,
                importance=min(1.0, importance),
                emotional_valence=max(-1.0, min(1.0, emotional_valence)),
                source_message_id=source_message_id,
            )

        fact_patterns = (
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
        )
        for pattern, template in fact_patterns:
            for match in re.finditer(pattern, user_text, flags=re.IGNORECASE):
                value = match.group(1).strip(" 的了呢啊呀 ")
                if value:
                    self.memories.store(
                        character_id=character_id,
                        memory_type="long_term",
                        content=template.format(value),
                        importance=0.65,
                        emotional_valence=None,
                        source_message_id=source_message_id,
                    )

    def extract_memories_with_llm(
        self,
        character_id: str,
        user_text: str,
        assistant_text: str,
        source_message_id: str,
    ) -> None:
        from src.llmproviders.LLMProvider import Message as LLMMessage
        from src.llmproviders.LLMProvider import Model as LLMModel

        system = (
            "You extract durable, long-term facts about the USER from a chat "
            "exchange. Return ONLY a JSON array of short factual strings (at most "
            "8), each written in the third person. Match the language of the fact "
            "to how the user said it. Exclude fleeting mood and small talk. Return "
            "an empty array [] when there is nothing worth remembering."
        )
        response = self.llm.send(
            LLMModel(name=self.model_name or "deepseek-chat"),
            [
                LLMMessage(role="system", content=system),
                LLMMessage(
                    role="user",
                    content=f"User: {user_text}\nAssistant: {assistant_text}",
                ),
            ],
        )
        for fact in parse_fact_list(response.content):
            self.memories.store(
                character_id=character_id,
                memory_type="long_term",
                content=fact,
                importance=0.7,
                emotional_valence=None,
                source_message_id=source_message_id,
            )


def parse_fact_list(raw: str) -> list[str]:
    if not raw:
        return []
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text[:4].lower() == "json":
            text = text[4:]
    start, end = text.find("["), text.rfind("]")
    if start == -1 or end <= start:
        return []
    try:
        data = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    facts: list[str] = []
    seen: set[str] = set()
    for item in data:
        if not isinstance(item, str):
            continue
        fact = item.strip()
        key = fact.lower()
        if not fact or len(fact) > 200 or key in seen:
            continue
        seen.add(key)
        facts.append(fact)
        if len(facts) == 8:
            break
    return facts
