"""Public database facade: runtime sessions plus migration/integrity entrypoints."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager

from fastapi import Depends
from sqlmodel import Session, SQLModel

from src.chitrika.config import config
from src.chitrika.database_integrity import check_foreign_key_integrity as _check_integrity
from src.chitrika.database_migrations import backup_before_migration, run_migrations
from src.chitrika.database_runtime import configure_sqlite_engine, create_runtime_engine

_engine = create_runtime_engine(config.database_url)


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    with Session(_engine) as session:
        yield session


def get_session() -> Generator[Session, None, None]:
    with session_scope() as session:
        yield session


def get_transactional_session(
    session: Session = Depends(get_session),
) -> Generator[Session, None, None]:
    from src.chitrika.uow import transaction_scope

    with transaction_scope(session):
        yield session


def check_foreign_key_integrity() -> list[dict[str, object]]:
    return _check_integrity(_engine)


def create_db_and_tables() -> None:
    import src.chitrika.models.character  # noqa: F401
    import src.chitrika.models.conversation  # noqa: F401
    import src.chitrika.models.emotion  # noqa: F401
    import src.chitrika.models.heartbeat  # noqa: F401
    import src.chitrika.models.memory  # noqa: F401
    import src.chitrika.models.message  # noqa: F401
    import src.chitrika.models.plugin  # noqa: F401
    import src.chitrika.models.provider  # noqa: F401
    import src.chitrika.models.relationship  # noqa: F401
    import src.chitrika.models.settings  # noqa: F401

    backup_before_migration(_engine)
    SQLModel.metadata.create_all(_engine)
    run_migrations(_engine)
