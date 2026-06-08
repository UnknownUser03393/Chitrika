"""Database engine, session factory, and table creation."""

from __future__ import annotations

from collections.abc import Generator

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


def get_session() -> Generator[Session, None, None]:
    """Yield a synchronous SQLModel session.

    Used by APScheduler (background threads) and anywhere async is not needed.
    """
    with Session(_engine) as session:
        yield session


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
    _enable_wal()
