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

    # Seed default character from skill_0624.txt
    try:
        from src.chitrika.database import get_session
        from src.chitrika.services.character_seed import seed_default_character

        session = next(get_session())
        try:
            seed_default_character(session)
        finally:
            session.close()
    except Exception:
        logger.exception("Failed to seed default character — continuing")

    # Seed default LLM provider from environment variables (backward compat)
    try:
        from src.chitrika.database import get_session as _gs
        from src.chitrika.models.provider import LLMProvider
        from sqlmodel import select

        session = next(_gs())
        try:
            existing = session.exec(select(LLMProvider)).first()
            if existing is None and config.deepseek_api_key:
                import json

                provider = LLMProvider(
                    name="deepseek",
                    display_name="DeepSeek",
                    api_key=config.deepseek_api_key,
                    base_url=config.deepseek_base_url,
                    default_model=config.deepseek_model,
                    models_json=json.dumps([config.deepseek_model]),
                    is_default=True,
                )
                session.add(provider)
                session.commit()
                logger.info("Default LLM provider 'deepseek' seeded from environment")
        finally:
            session.close()
    except Exception:
        logger.exception("Failed to seed default provider — continuing")

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


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Chitrika",
    version="0.1.0",
    description="Desktop-native AI companion API",
    lifespan=lifespan,
)

# CORS — allow frontend dev server
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
    from src.chitrika.routes.emotion_routes import router as emotion_router
    from src.chitrika.routes.heartbeat_routes import router as heartbeat_router
    from src.chitrika.routes.memory_routes import router as memory_router
    from src.chitrika.routes.provider_routes import router as provider_router

    app.include_router(chat_router, prefix="/api")
    app.include_router(character_router, prefix="/api")
    app.include_router(emotion_router, prefix="/api")
    app.include_router(memory_router, prefix="/api")
    app.include_router(heartbeat_router, prefix="/api")
    app.include_router(provider_router, prefix="/api")


_register_routers()
