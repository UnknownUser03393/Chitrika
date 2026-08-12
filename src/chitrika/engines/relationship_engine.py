"""Relationship progression driven by durable interaction signals."""

from __future__ import annotations

from sqlmodel import Session, select

from src.chitrika.models.character import Character
from src.chitrika.models.relationship import RelationshipState
from src.chitrika.utils.datetime_helpers import utcnow


class RelationshipEngine:
    """Own the lifecycle and progression of a character relationship."""

    def __init__(self, session: Session):
        self._session = session

    def get_or_create(self, character_id: str) -> RelationshipState:
        character = self._session.exec(
            select(Character).where(Character.id == character_id)
        ).first()
        if character is None:
            raise ValueError(f"Character {character_id!r} not found")

        state = self._session.exec(
            select(RelationshipState).where(
                RelationshipState.character_id == character_id
            )
        ).first()
        if state is None:
            state = RelationshipState(character_id=character_id)
            self._session.add(state)
            self._session.flush()
        return state

    def record_interaction(self, character_id: str, user_text: str) -> RelationshipState:
        """Advance relationship state from one completed user interaction."""
        state = self.get_or_create(character_id)
        text = user_text.lower()
        now = utcnow()

        positive = any(word in text for word in (
            "谢谢", "喜欢你", "爱你", "想你", "抱抱", "开心",
            "thank", "love you", "miss you", "trust you",
        ))
        conflict = any(word in text for word in (
            "讨厌你", "闭嘴", "滚", "烦死", "生气",
            "hate you", "shut up", "go away",
        ))
        disclosure = len(user_text.strip()) >= 40 or any(word in text for word in (
            "其实我", "告诉你", "秘密", "我害怕", "我担心",
            "to be honest", "i have never told", "my secret",
        ))

        state.interaction_count += 1
        state.familiarity = _clamp(state.familiarity + 0.012)
        state.affinity = _clamp(state.affinity + 0.004)
        state.trust = _clamp(state.trust + 0.003)

        if positive:
            state.positive_interaction_count += 1
            state.affinity = _clamp(state.affinity + 0.025)
            state.trust = _clamp(state.trust + 0.012)
        if disclosure:
            state.familiarity = _clamp(state.familiarity + 0.018)
            state.trust = _clamp(state.trust + 0.018)
        if conflict:
            state.conflict_count += 1
            state.affinity = _clamp(state.affinity - 0.045)
            state.trust = _clamp(state.trust - 0.035)

        if state.first_interaction_at is None:
            state.first_interaction_at = now
        state.last_interaction_at = now
        state.updated_at = now
        state.stage = _stage_for(state)

        self._session.flush()
        return state


def _clamp(value: float) -> float:
    return min(1.0, max(0.0, value))


def _stage_for(state: RelationshipState) -> str:
    """Classify stage with both time-earned familiarity and social quality."""
    score = state.affinity * 0.4 + state.familiarity * 0.3 + state.trust * 0.3
    if state.interaction_count >= 80 and score >= 0.78:
        return "intimate"
    if state.interaction_count >= 30 and score >= 0.58:
        return "close"
    if state.interaction_count >= 10 and score >= 0.32:
        return "friend"
    if state.interaction_count >= 3 and score >= 0.10:
        return "acquaintance"
    return "stranger"
