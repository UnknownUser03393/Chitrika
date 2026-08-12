"""Read-only database integrity checks."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Engine


def check_foreign_key_integrity(engine: Engine) -> list[dict[str, object]]:
    if engine.dialect.name != "sqlite":
        return []
    with engine.connect() as connection:
        rows = connection.execute(text("PRAGMA foreign_key_check")).all()
    return [
        {"table": row[0], "rowid": row[1], "parent": row[2], "foreign_key": row[3]}
        for row in rows
    ]

