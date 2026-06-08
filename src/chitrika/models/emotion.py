"""Emotion state model — one row per character, eight dimensions."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlmodel import Field, SQLModel

from src.chitrika.utils.datetime_helpers import utcnow

# Plutchik-inspired emotion dimensions (module-level constant, not a DB column)
DIMENSIONS: tuple[str, ...] = (
    "joy",
    "sadness",
    "anger",
    "fear",
    "trust",
    "anticipation",
    "surprise",
    "disgust",
)


class EmotionState(SQLModel, table=True):
    """The current emotional state of a character.

    Each dimension ranges from -1.0 to +1.0.
    One row per character (enforced by unique constraint on character_id).
    """

    __tablename__ = "emotion_states"

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
    )
    character_id: str = Field(
        foreign_key="characters.id",
        unique=True,
        index=True,
        description="The character whose emotional state this represents",
    )

    # --- Eight emotion dimensions ---
    joy: float = Field(default=0.0, ge=-1.0, le=1.0)
    sadness: float = Field(default=0.0, ge=-1.0, le=1.0)
    anger: float = Field(default=0.0, ge=-1.0, le=1.0)
    fear: float = Field(default=0.0, ge=-1.0, le=1.0)
    trust: float = Field(default=0.0, ge=-1.0, le=1.0)
    anticipation: float = Field(default=0.0, ge=-1.0, le=1.0)
    surprise: float = Field(default=0.0, ge=-1.0, le=1.0)
    disgust: float = Field(default=0.0, ge=-1.0, le=1.0)

    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, float]:
        """Return all eight dimensions as a dict."""
        return {d: getattr(self, d) for d in DIMENSIONS}

    def dominant_emotion(self) -> str:
        """Return the dimension with the highest absolute value."""
        return max(DIMENSIONS, key=lambda d: abs(getattr(self, d)))
