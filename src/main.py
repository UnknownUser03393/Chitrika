"""Chitrika FastAPI application entry point."""

from __future__ import annotations

import hmac
import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.chitrika.config import config
from src.chitrika.services.startup_service import StartupService
from src.chitrika.runtime import ApplicationContainer

logger = logging.getLogger("chitrika")
container = ApplicationContainer()
runtime = StartupService(container)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> Any:  # noqa: RUF029
    logging.basicConfig(level=logging.INFO)
    logger.info("Chitrika starting up")
    _app.state.container = container
    runtime.start()
    try:
        yield
    finally:
        logger.info("Chitrika shutting down")
        runtime.stop()


app = FastAPI(
    title="Chitrika",
    version="0.1.0",
    description="Desktop-native AI companion API",
    lifespan=lifespan,
)
app.state.container = container

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def require_api_token(request: Request, call_next):
    """Protect every local API endpoint with the per-launch bearer token."""
    if request.url.path.startswith("/api/") and request.method != "OPTIONS":
        authorization = request.headers.get("authorization", "")
        scheme, separator, supplied = authorization.partition(" ")
        valid = (
            separator == " "
            and scheme.lower() == "bearer"
            and bool(config.api_token)
            and hmac.compare_digest(supplied, config.api_token)
        )
        if not valid:
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or missing API bearer token"},
                headers={"WWW-Authenticate": "Bearer"},
            )
    return await call_next(request)


@app.get("/api/health")
def health_check() -> dict[str, object]:
    readiness = runtime.readiness
    return {
        "service": "chitrika",
        "status": readiness.status,
        "ready": readiness.ready,
        "version": "0.1.0",
        "degraded_items": list(readiness.degraded_items),
    }


def _register_routers() -> None:
    """Register routes after app construction to avoid circular imports."""
    from src.chitrika.routes.character_routes import router as character_router
    from src.chitrika.routes.chat_routes import router as chat_router
    from src.chitrika.routes.debug_routes import router as debug_router
    from src.chitrika.routes.desktop_routes import router as desktop_router
    from src.chitrika.routes.emotion_routes import router as emotion_router
    from src.chitrika.routes.export_routes import router as export_router
    from src.chitrika.routes.heartbeat_routes import router as heartbeat_router
    from src.chitrika.routes.import_routes import router as import_router
    from src.chitrika.routes.memory_routes import router as memory_router
    from src.chitrika.routes.plugin_routes import router as plugin_router
    from src.chitrika.routes.provider_routes import router as provider_router
    from src.chitrika.routes.relationship_routes import router as relationship_router
    from src.chitrika.routes.settings_routes import router as settings_router
    from src.chitrika.routes.tts_routes import router as tts_router

    for router in (
        chat_router,
        character_router,
        debug_router,
        desktop_router,
        emotion_router,
        export_router,
        memory_router,
        plugin_router,
        heartbeat_router,
        import_router,
        provider_router,
        relationship_router,
        settings_router,
        tts_router,
    ):
        app.include_router(router, prefix="/api")


_register_routers()
