"""APScheduler lifecycle and immutable heartbeat runtime status."""

from __future__ import annotations

import logging
from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from sqlmodel import Session

from src.chitrika.database import session_scope
from src.chitrika.engines.settings_engine import SettingsEngine
from src.chitrika.services.heartbeat_coordinator import HeartbeatCoordinator
from src.chitrika.uow import UnitOfWork
from src.chitrika.utils.datetime_helpers import utcnow

logger = logging.getLogger("chitrika.heartbeat.scheduler")


@dataclass(frozen=True, slots=True)
class HeartbeatStatus:
    running: bool
    tick_interval_minutes: int
    loneliness_threshold: float
    tick_count: int
    last_tick: str | None

    def as_dict(self) -> dict[str, object]:
        return {
            "running": self.running,
            "tick_interval_minutes": self.tick_interval_minutes,
            "loneliness_threshold": self.loneliness_threshold,
            "tick_count": self.tick_count,
            "last_tick": self.last_tick,
        }


class HeartbeatScheduler:
    def __init__(
        self,
        session_factory: Callable[[], AbstractContextManager[Session]] | None = None,
        *,
        scheduler: BackgroundScheduler | None = None,
    ) -> None:
        self.session_factory = session_factory or session_scope
        self.coordinator = HeartbeatCoordinator(self.session_factory)
        self._scheduler = scheduler or BackgroundScheduler()
        self._running = False
        self._tick_count = 0
        self._last_tick: datetime | None = None
        self._interval, self._threshold, self._decay_rate = self._read_settings()

    def _read_settings(self) -> tuple[int, float, float]:
        try:
            with UnitOfWork(session_factory=self.session_factory) as uow:
                settings = SettingsEngine(uow.session)
                settings.apply_defaults()
                values = settings.get_typed()
            return (
                int(values.get("heartbeat_interval_minutes", 5)),
                float(values.get("loneliness_threshold", 0.6)),
                float(values.get("emotion_decay_rate", 0.15)),
            )
        except Exception:
            logger.exception("Failed to load heartbeat settings, using defaults")
            return 5, 0.6, 0.15

    @property
    def status(self) -> HeartbeatStatus:
        return HeartbeatStatus(
            running=self._running,
            tick_interval_minutes=self._interval,
            loneliness_threshold=self._threshold,
            tick_count=self._tick_count,
            last_tick=self._last_tick.isoformat() if self._last_tick else None,
        )

    def start(self) -> None:
        if self._running:
            return
        self._scheduler.add_job(
            self.tick,
            "interval",
            minutes=self._interval,
            id="heartbeat_tick",
            replace_existing=True,
            next_run_time=datetime.now(timezone.utc) + timedelta(seconds=10),
        )
        self._scheduler.start()
        self._running = True

    def stop(self) -> None:
        if not self._running:
            return
        self._scheduler.shutdown(wait=False)
        self._running = False

    def restart(self) -> None:
        was_running = self._running
        if was_running:
            self.stop()
        self._interval, self._threshold, self._decay_rate = self._read_settings()
        if was_running:
            self.start()

    def tick(self) -> None:
        self._tick_count += 1
        self._last_tick = utcnow()
        interval, threshold, decay_rate = self._read_settings()
        self._interval, self._threshold, self._decay_rate = interval, threshold, decay_rate
        self._reschedule_if_needed()
        self.coordinator.run_cycle(
            decay_rate=self._decay_rate,
            loneliness_threshold=self._threshold,
        )

    def _reschedule_if_needed(self) -> None:
        job = self._scheduler.get_job("heartbeat_tick")
        if job is None:
            return
        current = job.trigger.interval.total_seconds() / 60  # type: ignore[union-attr]
        if int(current) != self._interval:
            job.reschedule(trigger="interval", minutes=self._interval)
