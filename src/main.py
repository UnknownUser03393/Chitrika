"""Chitrika — FastAPI application entry point.

Starts the API server, initialises the database, seeds default characters,
and manages the heartbeat engine lifecycle.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.chitrika.config import config

logger = logging.getLogger("chitrika")

# Module-level reference so routes can query heartbeat status
_heartbeat_engine = None


# ---------------------------------------------------------------------------
# Lifespan — startup / shutdown
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(_app: FastAPI) -> Any:  # noqa: RUF029
    """Application lifespan: create tables, seed data, start heartbeat."""
    global _heartbeat_engine

    # --- startup ---
    logging.basicConfig(level=logging.INFO)
    logger.info("Chitrika starting up …")

    from src.chitrika.database import create_db_and_tables

    create_db_and_tables()
    logger.info("Database tables ready")

    # Discover local plugins. New plugins remain disabled until explicitly
    # enabled through the management API.
    try:
        from src.chitrika.database import get_session as _plugin_session
        from src.chitrika.engines.plugin_engine import PluginEngine

        session = next(_plugin_session())
        try:
            discovered, invalid = PluginEngine(session).discover()
            logger.info("Discovered %d local plugins", len(discovered))
            for error in invalid:
                logger.warning("Plugin discovery error: %s", error)
        finally:
            session.close()
    except Exception:
        logger.exception("Failed to discover plugins - continuing")

    # Seed default settings rows (no-op if they already exist)
    from src.chitrika.database import get_session
    from src.chitrika.engines.settings_engine import SettingsEngine

    try:
        session = next(get_session())
        try:
            engine = SettingsEngine(session)
            created = engine.apply_defaults()
            if created:
                logger.info("Seeded %d default settings", created)
        finally:
            session.close()
    except Exception:
        logger.exception("Failed to seed default settings — continuing")

    # Seed default character from skill_0624.txt
    try:
        from src.chitrika.database import get_session as _gs2
        from src.chitrika.services.character_seed import seed_default_character

        session = next(_gs2())
        try:
            seed_default_character(session)
        finally:
            session.close()
    except Exception:
        logger.exception("Failed to seed default character — continuing")

    # Seed default LLM provider (hardcoded defaults; user configures via Settings UI)
    try:
        from src.chitrika.database import get_session as _gs3
        from src.chitrika.models.provider import LLMProvider
        from src.chitrika.services.provider_service import replace_provider_models
        from sqlmodel import select

        session = next(_gs3())
        try:
            existing = session.exec(select(LLMProvider)).first()
            if existing is None:
                provider = LLMProvider(
                    name="deepseek",
                    display_name="DeepSeek",
                    api_key="",
                    base_url="https://api.deepseek.com/v1",
                    default_model="deepseek-chat",
                    is_default=True,
                )
                session.add(provider)
                session.flush()
                replace_provider_models(session, provider, ["deepseek-chat"])
                session.commit()
                logger.info("Default LLM provider 'deepseek' seeded")
        finally:
            session.close()
    except Exception:
        logger.exception("Failed to seed default provider — continuing")

    # Start optional local emotion inference debug panel.
    if config.emotion_debug_panel:
        try:
            from src.chitrika.services.emotion_debug_panel import start_emotion_debug_panel

            start_emotion_debug_panel()
            logger.info("Emotion debug panel started")
        except Exception:
            logger.exception("Failed to start emotion debug panel — continuing")

    # Start heartbeat engine
    try:
        from src.chitrika.engines.heartbeat_engine import HeartbeatEngine
        from src.chitrika.routes.heartbeat_routes import set_heartbeat_engine

        _heartbeat_engine = HeartbeatEngine()
        _heartbeat_engine.start()
        set_heartbeat_engine(_heartbeat_engine)
        logger.info("Heartbeat engine started")
    except Exception:
        logger.exception("Failed to start heartbeat engine — continuing")

    yield  # --- app runs here ---

    # --- shutdown ---
    logger.info("Chitrika shutting down …")
    if _heartbeat_engine is not None:
        try:
            _heartbeat_engine.stop()
            logger.info("Heartbeat engine stopped")
        except Exception:
            logger.exception("Error stopping heartbeat engine")

    if config.emotion_debug_panel:
        try:
            from src.chitrika.services.emotion_debug_panel import stop_emotion_debug_panel

            stop_emotion_debug_panel()
        except Exception:
            logger.exception("Error stopping emotion debug panel")


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Chitrika",
    version="0.1.0",
    description="Desktop-native AI companion API",
    lifespan=lifespan,
)

# CORS — from chitrika.json / env at startup (change requires restart).
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


@app.get("/api/health")
def health_check() -> dict[str, str]:
    """Basic health check endpoint."""
    return {"status": "ok", "version": "0.1.0"}


# ---------------------------------------------------------------------------
# Router registration (deferred imports to avoid circular deps)
# ---------------------------------------------------------------------------


def _register_routers() -> None:
    from src.chitrika.routes.chat_routes import router as chat_router
    from src.chitrika.routes.character_routes import router as character_router
    from src.chitrika.routes.debug_routes import router as debug_router
    from src.chitrika.routes.desktop_routes import router as desktop_router
    from src.chitrika.routes.emotion_routes import router as emotion_router
    from src.chitrika.routes.heartbeat_routes import router as heartbeat_router
    from src.chitrika.routes.import_routes import router as import_router
    from src.chitrika.routes.memory_routes import router as memory_router
    from src.chitrika.routes.plugin_routes import router as plugin_router
    from src.chitrika.routes.provider_routes import router as provider_router
    from src.chitrika.routes.relationship_routes import router as relationship_router
    from src.chitrika.routes.settings_routes import router as settings_router

    app.include_router(chat_router, prefix="/api")
    app.include_router(character_router, prefix="/api")
    app.include_router(debug_router, prefix="/api")
    app.include_router(desktop_router, prefix="/api")
    app.include_router(emotion_router, prefix="/api")
    app.include_router(memory_router, prefix="/api")
    app.include_router(plugin_router, prefix="/api")
    app.include_router(heartbeat_router, prefix="/api")
    app.include_router(import_router, prefix="/api")
    app.include_router(provider_router, prefix="/api")
    app.include_router(relationship_router, prefix="/api")
    app.include_router(settings_router, prefix="/api")


_register_routers()
