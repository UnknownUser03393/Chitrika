"""Database engine, session factory, and table creation."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager

from sqlmodel import Session, SQLModel, create_engine

from src.chitrika.config import config

# SQLite with WAL mode for concurrent reads during heartbeat writes.
# connect_args applies to every new connection.
_engine = create_engine(
    config.database_url,
    echo=False,
    connect_args={"check_same_thread": False},
)


def _enable_wal() -> None:
    """Enable WAL journal mode for better concurrency."""
    from sqlalchemy import text

    with _engine.connect() as conn:
        conn.execute(text("PRAGMA journal_mode=WAL"))
        conn.commit()


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """Provide a synchronous SQLModel session as a context manager."""
    with Session(_engine) as session:
        yield session


def get_session() -> Generator[Session, None, None]:
    """Yield a synchronous SQLModel session for FastAPI dependencies."""
    with session_scope() as session:
        yield session


def _migrate_columns() -> None:
    """Add missing columns to existing tables without recreating them.

    SQLModel.metadata.create_all() doesn't alter existing tables, so new
    columns added to models after the initial DB creation need explicit
    ALTER TABLE statements.
    """
    from sqlalchemy import text

    migrations: list[tuple[str, str, str]] = [
        # (table, column, definition)
        ("messages", "read_at", "DATETIME"),
        ("messages", "desktop_notified_at", "DATETIME"),
        ("messages", "scheduled_message_id", "TEXT"),
    ]

    with _engine.connect() as conn:
        for table, column, col_type in migrations:
            result = conn.execute(
                text(f"PRAGMA table_info('{table}')"),
            )
            existing = {row[1] for row in result}
            if column not in existing:
                conn.execute(
                    text(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}"),
                )
                conn.commit()


def create_db_and_tables() -> None:
    """Create all tables if they don't exist, then enable WAL mode."""
    # Import all models so SQLModel metadata discovers them
    import src.chitrika.models.character  # noqa: F401
    import src.chitrika.models.conversation  # noqa: F401
    import src.chitrika.models.emotion  # noqa: F401
    import src.chitrika.models.heartbeat  # noqa: F401
    import src.chitrika.models.memory  # noqa: F401
    import src.chitrika.models.message  # noqa: F401
    import src.chitrika.models.provider  # noqa: F401
    import src.chitrika.models.settings  # noqa: F401

    SQLModel.metadata.create_all(_engine)
    _migrate_columns()
    _enable_wal()
