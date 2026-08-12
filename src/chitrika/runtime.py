"""Process-level application container."""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlmodel import Session

from src.chitrika.services.heartbeat_scheduler import HeartbeatScheduler
from src.chitrika.services.plugin_runtime import PluginRegistry, get_plugin_registry


@dataclass(slots=True)
class ApplicationContainer:
    """Long-lived, thread-safe runtime objects shared by request services."""

    heartbeat_scheduler: HeartbeatScheduler | None = None
    plugin_registry: PluginRegistry = field(default_factory=get_plugin_registry)

    def plugin_services(self, session: Session):
        """Build request-scoped plugin persistence and invocation services."""
        from src.chitrika.repositories.plugin_state_repository import PluginStateRepository
        from src.chitrika.services.plugin_runtime import PluginInvoker

        states = PluginStateRepository(session)
        return states, PluginInvoker(states, self.plugin_registry)

    def memory_services(self, session: Session):
        """Build request-scoped memory repository, lifecycle, and retrieval services."""
        from src.chitrika.repositories.memory_repository import MemoryRepository
        from src.chitrika.services.memory_lifecycle_service import MemoryLifecycleService
        from src.chitrika.services.memory_retrieval_service import MemoryRetrievalService

        repository = MemoryRepository(session)
        return (
            repository,
            MemoryLifecycleService(repository),
            MemoryRetrievalService(repository),
        )
