"""Debug API routes — force explicit companion actions."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from src.chitrika.database import get_transactional_session
from src.chitrika.engines.debug_engine import DebugEngine
from src.chitrika.schemas.debug_schemas import DebugActionRequest, DebugActionResponse

router = APIRouter(tags=["debug"])


@router.post(
    "/debug/actions/{action}",
    response_model=DebugActionResponse,
)
def run_debug_action(
    action: str,
    body: DebugActionRequest,
    session: Session = Depends(get_transactional_session),
) -> dict:
    """Run a named debug action against a character."""
    engine = DebugEngine(session)
    try:
        return engine.run_action(action, body)
    except ValueError as exc:
        detail = str(exc)
        status_code = 400 if detail.startswith("Unsupported debug action") else 404
        raise HTTPException(status_code=status_code, detail=detail) from exc
