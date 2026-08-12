"""Explicit transaction boundaries for synchronous SQLModel work."""

from __future__ import annotations

from collections.abc import Callable, Generator
from contextlib import AbstractContextManager, contextmanager
from types import TracebackType

from sqlmodel import Session


class UnitOfWork:
    """Own exactly one database transaction.

    Repositories, engines, and domain services receive ``session`` and may
    flush, but this object is the only runtime component that commits or rolls
    back application work.
    """

    def __init__(
        self,
        session: Session | None = None,
        *,
        session_factory: Callable[[], AbstractContextManager[Session]] | None = None,
    ) -> None:
        if (session is None) == (session_factory is None):
            raise ValueError("Provide either session or session_factory")
        self._provided_session = session
        self._session_factory = session_factory
        self._session_context: AbstractContextManager[Session] | None = None
        self.session: Session

    def __enter__(self) -> UnitOfWork:
        if self._provided_session is not None:
            self.session = self._provided_session
        else:
            assert self._session_factory is not None
            self._session_context = self._session_factory()
            self.session = self._session_context.__enter__()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool:
        try:
            if exc_type is None:
                try:
                    self.session.commit()
                except BaseException:
                    self.session.rollback()
                    raise
            else:
                self.session.rollback()
        finally:
            if self._session_context is not None:
                self._session_context.__exit__(exc_type, exc, traceback)
        return False


@contextmanager
def transaction_scope(session: Session) -> Generator[Session, None, None]:
    """Commit once on success and roll back the complete command on failure."""
    with UnitOfWork(session) as uow:
        yield uow.session
