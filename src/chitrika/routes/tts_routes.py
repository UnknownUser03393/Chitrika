"""Text-to-speech API routes."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from src.chitrika.schemas.tts_schemas import TTSRequest
from src.chitrika.services.tts_service import TTSError, synthesize_speech

logger = logging.getLogger("chitrika.routes.tts")

router = APIRouter(tags=["tts"])


@router.post("/tts/synthesize")
def synthesize_tts(body: TTSRequest) -> Response:
    """Return synthesized audio for the supplied text and provider settings."""
    try:
        audio, content_type = synthesize_speech(body)
    except TTSError as exc:
        logger.warning("TTS synthesis failed: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return Response(content=audio, media_type=content_type)
