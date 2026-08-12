"""Small versioned schema migrations and pre-migration SQLite backups."""

from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine, make_url

logger = logging.getLogger("chitrika.database.migrations")


def database_file(engine: Engine) -> Path | None:
    url = make_url(str(engine.url))
    if url.get_backend_name() != "sqlite" or not url.database or url.database == ":memory:":
        return None
    return Path(url.database).expanduser().resolve()


def migration_required(engine: Engine) -> bool:
    inspector = inspect(engine)
    if "messages" not in inspector.get_table_names():
        return False
    columns = {column["name"] for column in inspector.get_columns("messages")}
    indexes = (
        {index["name"] for index in inspector.get_indexes("llm_providers")}
        if "llm_providers" in inspector.get_table_names() else set()
    )
    return (
        "generation_status" not in columns
        or "error_detail" not in columns
        or "uq_llm_providers_enabled_default" not in indexes
    )


def backup_before_migration(engine: Engine) -> Path | None:
    source_path = database_file(engine)
    if source_path is None or not source_path.is_file() or not migration_required(engine):
        return None
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    target_path = source_path.with_name(f"{source_path.name}.pre-migration-{stamp}.bak")
    with sqlite3.connect(source_path) as source, sqlite3.connect(target_path) as target:
        source.backup(target)
    logger.info("Created pre-migration database backup at %s", target_path)
    return target_path


def run_migrations(engine: Engine) -> None:
    columns = [
        ("messages", "read_at", "DATETIME"),
        ("messages", "desktop_notified_at", "DATETIME"),
        ("messages", "scheduled_message_id", "TEXT"),
        ("llm_providers", "provider_type", "TEXT DEFAULT 'openai'"),
        ("llm_providers", "plugin_id", "TEXT"),
        ("llm_providers", "custom_config", "TEXT DEFAULT '{}'"),
        ("memories", "embedding", "BLOB"),
        ("messages", "generation_status", "TEXT NOT NULL DEFAULT 'complete'"),
        ("messages", "error_detail", "TEXT"),
    ]
    with engine.begin() as connection:
        connection.execute(text(
            "CREATE TABLE IF NOT EXISTS schema_migrations ("
            "version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)"
        ))
        for table, column, definition in columns:
            existing = {
                row[1] for row in connection.execute(text(f"PRAGMA table_info('{table}')"))
            }
            if column not in existing:
                connection.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {definition}"))
        connection.execute(text(
            "UPDATE llm_providers SET is_default = 0 WHERE enabled = 0 AND is_default = 1"
        ))
        defaults = list(connection.execute(text(
            "SELECT id FROM llm_providers WHERE enabled = 1 AND is_default = 1 "
            "ORDER BY updated_at DESC, created_at DESC, id"
        )))
        for duplicate in defaults[1:]:
            connection.execute(
                text("UPDATE llm_providers SET is_default = 0 WHERE id = :id"),
                {"id": duplicate[0]},
            )
        connection.execute(text(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_llm_providers_enabled_default "
            "ON llm_providers(is_default) WHERE enabled = 1 AND is_default = 1"
        ))
        connection.execute(text(
            "INSERT OR IGNORE INTO schema_migrations(version, applied_at) "
            "VALUES (1, :applied_at)"
        ), {"applied_at": datetime.now(timezone.utc).isoformat()})
