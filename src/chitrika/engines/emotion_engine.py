"""Emotion Engine — maintains evolving emotional state for each character.

Wraps the pure functions in emotion_algorithms.py with database persistence.
"""

from __future__ import annotations

import logging
from sqlmodel import Session, select

from src.chitrika.models.character import Character
from src.chitrika.models.emotion import EmotionState
from src.chitrika.utils import emotion_algorithms as algo
from src.chitrika.utils.datetime_helpers import hours_between, utcnow

logger = logging.getLogger("chitrika.emotion")


class EmotionEngine:
    """Manages emotional state persistence, decay, and analysis."""

    def __init__(self, session: Session):
        self._session = session

    # ------------------------------------------------------------------
    # State retrieval / creation
    # ------------------------------------------------------------------

    def get_state(self, character_id: str) -> EmotionState | None:
        """Return the current EmotionState for *character_id*, or None."""
        return self._session.exec(
            select(EmotionState).where(EmotionState.character_id == character_id)
        ).first()

    def get_or_create_state(self, character_id: str) -> EmotionState:
        """Return existing state or create a neutral default."""
        state = self.get_state(character_id)
        if state is None:
            # Verify character exists
            char = self._session.exec(
                select(Character).where(Character.id == character_id)
            ).first()
            if char is None:
                raise ValueError(f"Character '{character_id}' not found")

            state = EmotionState(character_id=character_id)
            self._session.add(state)
            self._session.commit()
            self._session.refresh(state)
            logger.info("Created neutral emotion state for character %s", character_id)
        return state

    # ------------------------------------------------------------------
    # Decay
    # ------------------------------------------------------------------

    def apply_decay(
        self,
        character_id: str,
        decay_rate: float = 0.15,
    ) -> EmotionState:
        """Apply time-based decay and persist the result."""
        state = self.get_or_create_state(character_id)

        hours = hours_between(utcnow(), state.updated_at)
        if hours < 0.08:
            return state

        current = state.to_dict()
        decayed = algo.apply_decay(current, hours, decay_rate)

        for dim in algo.DIMENSIONS:
            setattr(state, dim, decayed[dim])
        state.updated_at = utcnow()

        self._session.commit()
        self._session.refresh(state)
        return state

    # ------------------------------------------------------------------
    # Delta / event
    # ------------------------------------------------------------------

    def update_emotion(
        self,
        character_id: str,
        deltas: dict[str, float],
    ) -> EmotionState:
        """Apply emotion deltas from an event and persist.

        Example::
            engine.update_emotion(char_id, {"joy": 0.1, "trust": 0.05})
        """
        state = self.get_or_create_state(character_id)
        current = state.to_dict()
        updated = algo.apply_delta(current, deltas)

        for dim in algo.DIMENSIONS:
            setattr(state, dim, updated[dim])
        state.updated_at = utcnow()

        self._session.commit()
        self._session.refresh(state)
        return state

    # ------------------------------------------------------------------
    # Analysis (read-only, but may apply decay)
    # ------------------------------------------------------------------

    def analyse(
        self,
        character_id: str,
        *,
        apply_decay_before: bool = True,
    ) -> dict:
        """Return the full emotion analysis for *character_id*.

        The returned dict has keys:
            character_id, emotions (dict), mood, loneliness, dominant,
            updated_at
        """
        state = self.get_or_create_state(character_id)

        if apply_decay_before:
            state = self.apply_decay(character_id)

        current = state.to_dict()
        return {
            "character_id": character_id,
            "emotions": current,
            "mood": algo.compute_mood(current),
            "loneliness": algo.compute_loneliness(current),
            "dominant": max(algo.DIMENSIONS, key=lambda d: abs(current[d])),
            "updated_at": state.updated_at.isoformat(),
        }

    # ------------------------------------------------------------------
    # Batch
    # ------------------------------------------------------------------

    def decay_all_characters(self, decay_rate: float = 0.15) -> list[str]:
        """Apply decay to every enabled character. Returns list of character IDs."""
        characters = self._session.exec(
            select(Character).where(Character.enabled.is_(True))
        ).all()

        processed: list[str] = []
        for char in characters:
            try:
                self.apply_decay(char.id, decay_rate)
                processed.append(char.id)
            except Exception:
                logger.exception("Decay failed for character %s", char.id)
        return processed
