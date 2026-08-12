"""Application startup/shutdown orchestration and readiness reporting."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from sqlmodel import select

from src.chitrika.config import config
from src.chitrika.runtime import ApplicationContainer
from src.chitrika.uow import UnitOfWork
from src.chitrika.database import (
    check_foreign_key_integrity,
    create_db_and_tables,
    session_scope,
)

logger = logging.getLogger("chitrika.startup")


@dataclass(slots=True)
class ReadinessState:
    """Mutable runtime readiness details exposed by the health endpoint."""

    ready: bool = False
    degraded_items: list[str] = field(default_factory=list)

    @property
    def status(self) -> str:
        return "degraded" if self.degraded_items else "ok"

    def reset(self) -> None:
        self.ready = False
        self.degraded_items.clear()

    def degrade(self, item: str) -> None:
        if item not in self.degraded_items:
            self.degraded_items.append(item)


class StartupService:
    """Run critical boot steps and isolate optional subsystem failures."""

    def __init__(self, container: ApplicationContainer | None = None) -> None:
        self.readiness = ReadinessState()
        self.container = container or ApplicationContainer()

    def start(self) -> None:
        self.readiness.reset()
        self._require_api_token()
        self._initialize_database()
        self._discover_plugins()
        self._initialize_settings()
        self._seed_default_character()
        self._seed_default_provider()
        self._start_debug_panel()
        self._start_heartbeat()
        self.readiness.ready = True

    def stop(self) -> None:
        if self.container.heartbeat_scheduler is not None:
            try:
                self.container.heartbeat_scheduler.stop()
                logger.info("Heartbeat engine stopped")
            except Exception:
                logger.exception("Error stopping heartbeat engine")
            finally:
                self.container.heartbeat_scheduler = None

        if config.emotion_debug_panel:
            try:
                from src.chitrika.services.emotion_debug_panel import (
                    stop_emotion_debug_panel,
                )

                stop_emotion_debug_panel()
            except Exception:
                logger.exception("Error stopping emotion debug panel")
        self.readiness.ready = False

    @staticmethod
    def _require_api_token() -> None:
        if not config.api_token:
            raise RuntimeError(
                "CHITRIKA_API_TOKEN is required. Set the same token for the "
                "backend and frontend/Electron launcher."
            )

    def _initialize_database(self) -> None:
        create_db_and_tables()
        logger.info("Database tables ready")
        violations = check_foreign_key_integrity()
        if not violations:
            return
        self.readiness.degrade(
            f"database_foreign_key_violations:{len(violations)}"
        )
        logger.error(
            "Database foreign-key integrity check found %d orphaned rows; "
            "no user data was modified. Sample: %s",
            len(violations),
            violations[:10],
        )

    def _discover_plugins(self) -> None:
        try:
            from src.chitrika.repositories.plugin_state_repository import PluginStateRepository
            from src.chitrika.services.plugin_runtime import (
                PluginDiscoveryService,
                PluginInvoker,
            )

            with UnitOfWork(session_factory=session_scope) as uow:
                states = PluginStateRepository(uow.session)
                discovered, invalid = PluginDiscoveryService(
                    states, self.container.plugin_registry
                ).discover()
                logger.info("Discovered %d local plugins", len(discovered))
                for error in invalid:
                    logger.warning("Plugin discovery error: %s", error)
                if invalid:
                    self.readiness.degrade(
                        f"plugin_manifests_invalid:{len(invalid)}"
                    )
                plugin = states.get("deepseek_local")
                if plugin is not None and plugin.available and not plugin.enabled:
                    PluginInvoker(states, self.container.plugin_registry).set_enabled(
                        "deepseek_local", True
                    )
                    logger.info("Enabled bundled plugin 'deepseek_local'")
        except Exception:
            logger.exception("Failed to discover plugins - continuing")
            self.readiness.degrade("plugin_discovery_failed")

    @staticmethod
    def _initialize_settings() -> None:
        from src.chitrika.engines.settings_engine import SettingsEngine

        try:
            with UnitOfWork(session_factory=session_scope) as uow:
                created = SettingsEngine(uow.session).apply_defaults()
                if created:
                    logger.info("Seeded %d default settings", created)
        except Exception:
            logger.exception("Failed to seed required default settings")
            raise

    def _seed_default_character(self) -> None:
        try:
            from src.chitrika.services.character_seed import seed_default_character

            with UnitOfWork(session_factory=session_scope) as uow:
                seed_default_character(uow.session)
        except Exception:
            logger.exception("Failed to seed default character - continuing")
            self.readiness.degrade("default_character_seed_failed")

    def _seed_default_provider(self) -> None:
        try:
            from src.chitrika.models.provider import LLMProvider
            from src.chitrika.services.provider_service import replace_provider_models

            with UnitOfWork(session_factory=session_scope) as uow:
                session = uow.session
                if session.exec(select(LLMProvider)).first() is not None:
                    return
                provider = LLMProvider(
                    name="deepseek",
                    display_name="DeepSeek Web (Local)",
                    provider_type="deepseek-local",
                    plugin_id="deepseek_local",
                    api_key="",
                    base_url="",
                    default_model="deepseek-chat",
                    custom_config={
                        "auth_state_path": str(
                            Path(config.plugins_dir)
                            / "deepseek_local"
                            / "data"
                            / "auth_state.json"
                        ),
                        "default_model": "deepseek-chat",
                    },
                    is_default=True,
                )
                session.add(provider)
                session.flush()
                replace_provider_models(session, provider, ["deepseek-chat"])
                logger.info("Default LLM provider 'deepseek' seeded")
        except Exception:
            logger.exception("Failed to seed default provider - continuing")
            self.readiness.degrade("default_provider_seed_failed")

    def _start_debug_panel(self) -> None:
        if not config.emotion_debug_panel:
            return
        try:
            from src.chitrika.services.emotion_debug_panel import (
                start_emotion_debug_panel,
            )

            start_emotion_debug_panel()
            logger.info("Emotion debug panel started")
        except Exception:
            logger.exception("Failed to start emotion debug panel - continuing")
            self.readiness.degrade("emotion_debug_panel_failed")

    def _start_heartbeat(self) -> None:
        try:
            from src.chitrika.services.heartbeat_scheduler import HeartbeatScheduler

            self.container.heartbeat_scheduler = HeartbeatScheduler()
            self.container.heartbeat_scheduler.start()
            logger.info("Heartbeat engine started")
        except Exception:
            logger.exception("Failed to start heartbeat engine - continuing")
            self.container.heartbeat_scheduler = None
            self.readiness.degrade("heartbeat_start_failed")
