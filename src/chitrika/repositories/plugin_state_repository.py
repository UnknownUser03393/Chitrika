"""Persistence for plugin availability, activation, and diagnostics."""

from __future__ import annotations

from sqlmodel import Session, select

from src.chitrika.models.plugin import PluginInstallation
from src.chitrika.utils.datetime_helpers import utcnow


class PluginStateRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, plugin_id: str) -> PluginInstallation | None:
        return self.session.get(PluginInstallation, plugin_id)

    def all(self) -> list[PluginInstallation]:
        return list(self.session.exec(select(PluginInstallation)).all())

    def available(self) -> list[PluginInstallation]:
        return list(self.session.exec(
            select(PluginInstallation)
            .where(PluginInstallation.available.is_(True))
            .order_by(PluginInstallation.id)
        ).all())

    def enabled(self) -> list[PluginInstallation]:
        return list(self.session.exec(
            select(PluginInstallation)
            .where(
                PluginInstallation.enabled.is_(True),
                PluginInstallation.available.is_(True),
            )
            .order_by(PluginInstallation.id)
        ).all())

    def upsert(self, values: dict) -> PluginInstallation:
        record = self.get(values["id"])
        if record is None:
            record = PluginInstallation(**values)
            self.session.add(record)
        else:
            for key, value in values.items():
                setattr(record, key, value)
            record.updated_at = utcnow()
        return record

    def set_error(self, record: PluginInstallation, detail: str | None) -> None:
        record.load_error = detail
        record.updated_at = utcnow()
        self.session.flush()

