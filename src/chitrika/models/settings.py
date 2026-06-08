"""Settings model — simple key-value store for application preferences."""

from __future__ import annotations

from sqlmodel import Field, SQLModel


class Setting(SQLModel, table=True):
    """A single application setting stored as a key-value pair.

    Values are JSON-encoded strings for flexibility.
    """

    __tablename__ = "settings"

    key: str = Field(primary_key=True)
    value: str = Field(description="JSON-encoded value")
