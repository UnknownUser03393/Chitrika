"""Settings API routes — read/write application configuration."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from sqlmodel import Session

from src.chitrika.database import get_session, get_transactional_session
from src.chitrika.engines.settings_engine import SettingsEngine
from src.chitrika.schemas.settings_schemas import AppSettings, AppSettingsUpdate

logger = logging.getLogger("chitrika.routes.settings")

router = APIRouter(tags=["settings"])


# ---------------------------------------------------------------------------
# GET /api/settings
# ---------------------------------------------------------------------------


@router.get("/settings", response_model=AppSettings)
def get_settings(session: Session = Depends(get_session)) -> AppSettings:
    """Return all application settings (with defaults filled in)."""
    engine = SettingsEngine(session)
    return AppSettings.model_validate(engine.get_typed())


# ---------------------------------------------------------------------------
# PUT /api/settings
# ---------------------------------------------------------------------------


@router.put("/settings", response_model=AppSettings)
def update_settings(
    body: AppSettingsUpdate,
    session: Session = Depends(get_transactional_session),
) -> AppSettings:
    """Update application settings.  Only sent fields are changed."""
    engine = SettingsEngine(session)

    # Ensure defaults exist
    engine.apply_defaults()

    updates = body.model_dump(exclude_unset=True, exclude_none=True)
    for key, value in updates.items():
        engine.set(key, value)

    logger.info("Settings updated: %s", list(updates.keys()))

    return AppSettings.model_validate(engine.get_typed())
