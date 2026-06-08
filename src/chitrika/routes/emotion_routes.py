"""Emotion API routes — query and influence character emotional state."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from src.chitrika.database import get_session
from src.chitrika.engines.emotion_engine import EmotionEngine
from src.chitrika.schemas.emotion_schemas import (
    EmotionDelta,
    EmotionStateResponse,
    EmotionUpdateResponse,
)

router = APIRouter(tags=["emotion"])


# ---------------------------------------------------------------------------
# GET  /api/characters/{character_id}/emotion
# ---------------------------------------------------------------------------

@router.get(
    "/characters/{character_id}/emotion",
    response_model=EmotionStateResponse,
)
def get_emotion(
    character_id: str,
    session: Session = Depends(get_session),
) -> dict:
    """Get the current emotional state, mood, and loneliness for a character."""
    engine = EmotionEngine(session)
    try:
        return engine.analyse(character_id, apply_decay_before=True)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# POST /api/characters/{character_id}/emotion
# ---------------------------------------------------------------------------

@router.post(
    "/characters/{character_id}/emotion",
    response_model=EmotionUpdateResponse,
    status_code=200,
)
def apply_emotion_delta(
    character_id: str,
    delta: EmotionDelta,
    session: Session = Depends(get_session),
) -> dict:
    """Apply an emotion delta and return the updated state.

    Example body::

        {"joy": 0.15, "trust": 0.05, "sadness": -0.1}
    """
    engine = EmotionEngine(session)
    try:
        engine.update_emotion(character_id, delta.model_dump())
        return engine.analyse(character_id, apply_decay_before=False)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
