"""Heartbeat API routes — status and manual tick trigger."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Request
from sqlmodel import Session

from src.chitrika.database import get_session
from src.chitrika.engines.settings_engine import SettingsEngine
from src.chitrika.runtime import ApplicationContainer

logger = logging.getLogger("chitrika.routes.heartbeat")

router = APIRouter(tags=["heartbeat"])

def _container(request: Request) -> ApplicationContainer:
    return request.app.state.container


# ---------------------------------------------------------------------------
# GET  /api/heartbeat/status
# ---------------------------------------------------------------------------


@router.get("/heartbeat/status")
def get_heartbeat_status(
    request: Request,
    session: Session = Depends(get_session),
) -> dict:
    """Return the current heartbeat engine status."""
    scheduler = _container(request).heartbeat_scheduler
    if scheduler is None:
        data = SettingsEngine(session).get_typed()
        return {
            "running": False,
            "tick_interval_minutes": data.get("heartbeat_interval_minutes", 5),
            "loneliness_threshold": data.get("loneliness_threshold", 0.6),
            "tick_count": 0,
            "last_tick": None,
        }
    return scheduler.status.as_dict()


# ---------------------------------------------------------------------------
# POST /api/heartbeat/tick
# ---------------------------------------------------------------------------


@router.post("/heartbeat/tick")
def trigger_tick(request: Request) -> dict:
    """Manually trigger a heartbeat tick (for testing/demo)."""
    scheduler = _container(request).heartbeat_scheduler
    if scheduler is None:
        return {"error": "Heartbeat engine is not running"}
    scheduler.tick()
    return {"status": "ok", "tick_count": scheduler.status.tick_count}
