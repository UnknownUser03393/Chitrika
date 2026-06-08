"""Pydantic schemas for emotion API requests and responses."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class EmotionDelta(BaseModel):
    """Request body for applying emotion deltas."""

    joy: float = Field(default=0.0, ge=-1.0, le=1.0)
    sadness: float = Field(default=0.0, ge=-1.0, le=1.0)
    anger: float = Field(default=0.0, ge=-1.0, le=1.0)
    fear: float = Field(default=0.0, ge=-1.0, le=1.0)
    trust: float = Field(default=0.0, ge=-1.0, le=1.0)
    anticipation: float = Field(default=0.0, ge=-1.0, le=1.0)
    surprise: float = Field(default=0.0, ge=-1.0, le=1.0)
    disgust: float = Field(default=0.0, ge=-1.0, le=1.0)


class EmotionStateResponse(BaseModel):
    """Full emotion analysis returned to the client."""

    model_config = ConfigDict(from_attributes=True)

    character_id: str
    emotions: dict[str, float]
    mood: str
    loneliness: float
    dominant: str
    updated_at: str


class EmotionUpdateResponse(BaseModel):
    """Response after applying emotion deltas."""

    model_config = ConfigDict(from_attributes=True)

    character_id: str
    emotions: dict[str, float]
    mood: str
    loneliness: float
    dominant: str
    updated_at: str
