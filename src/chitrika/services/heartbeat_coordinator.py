"""Per-character transaction coordination for heartbeat work."""

from __future__ import annotations

import logging
from collections.abc import Callable
from contextlib import AbstractContextManager

from sqlmodel import Session, select

from src.chitrika.models.character import Character
from src.chitrika.services.heartbeat_services import (
    CharacterMaintenanceService,
    ScheduledMessageDeliveryService,
)
from src.chitrika.uow import UnitOfWork

logger = logging.getLogger("chitrika.heartbeat.coordinator")


class HeartbeatCoordinator:
    def __init__(
        self,
        session_factory: Callable[[], AbstractContextManager[Session]],
    ) -> None:
        self.session_factory = session_factory

    def run_cycle(self, *, decay_rate: float, loneliness_threshold: float) -> None:
        try:
            with self.session_factory() as session:
                character_ids = list(session.exec(
                    select(Character.id).where(Character.enabled.is_(True))
                ).all())
        except Exception:
            logger.exception("Heartbeat could not enumerate enabled characters")
            return

        for character_id in character_ids:
            try:
                with UnitOfWork(session_factory=self.session_factory) as uow:
                    character = uow.session.get(Character, character_id)
                    if character is None or not character.enabled:
                        continue
                    CharacterMaintenanceService(
                        uow.session,
                        decay_rate=decay_rate,
                        loneliness_threshold=loneliness_threshold,
                    ).maintain(character)
            except Exception:
                logger.exception("Heartbeat failed for character %s", character_id)

        try:
            with UnitOfWork(session_factory=self.session_factory) as uow:
                ScheduledMessageDeliveryService(uow.session).deliver_due()
        except Exception:
            logger.exception("Heartbeat scheduled-message delivery failed")

