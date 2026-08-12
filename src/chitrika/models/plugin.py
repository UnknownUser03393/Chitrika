"""Installed local plugin metadata and activation state."""

from __future__ import annotations

from datetime import datetime

from sqlmodel import Field, SQLModel

from src.chitrika.utils.datetime_helpers import utcnow


class PluginInstallation(SQLModel, table=True):
    """A plugin discovered from the local plugin directory.

    Executable code is never stored in SQLite.  The row is the durable source
    of truth for whether a discovered plugin is enabled and for its last load
    error.
    """

    __tablename__ = "plugin_installations"

    id: str = Field(primary_key=True, description="Stable manifest plugin id")
    name: str
    version: str
    description: str = ""
    author: str = ""
    entrypoint: str
    path: str
    available: bool = Field(default=True, index=True)
    enabled: bool = Field(default=False, index=True)
    load_error: str | None = None
    installed_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow, index=True)
