"""Heartbeat API routes — status and manual tick trigger."""

from __future__ import annotations

import logging

from fastapi import APIRouter

from src.chitrika.config import config
from src.chitrika.engines.heartbeat_engine import HeartbeatEngine

logger = logging.getLogger("chitrika.routes.heartbeat")

router = APIRouter(tags=["heartbeat"])

# Reference to the running engine (set by main.py lifespan)
_engine: HeartbeatEngine | None = None


def set_heartbeat_engine(engine: HeartbeatEngine) -> None:
    """Register the running heartbeat engine so routes can query it."""
    global _engine
    _engine = engine


# ---------------------------------------------------------------------------
# GET  /api/heartbeat/status
# ---------------------------------------------------------------------------


@router.get("/heartbeat/status")
def get_heartbeat_status() -> dict:
    """Return the current heartbeat engine status."""
    if _engine is None:
        return {
            "running": False,
            "tick_interval_minutes": config.heartbeat_interval_minutes,
            "loneliness_threshold": config.loneliness_threshold,
            "tick_count": 0,
            "last_tick": None,
        }
    return _engine.status


# ---------------------------------------------------------------------------
# POST /api/heartbeat/tick
# ---------------------------------------------------------------------------


@router.post("/heartbeat/tick")
def trigger_tick() -> dict:
    """Manually trigger a heartbeat tick (for testing/demo)."""
    if _engine is None:
        return {"error": "Heartbeat engine is not running"}
    _engine.tick()
    return {"status": "ok", "tick_count": _engine._tick_count}
