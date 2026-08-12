"""Shared test fixtures — in-memory SQLite, test client, mock LLM."""

from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from src.chitrika.config import config

# Import models so metadata is populated
import src.chitrika.models.character  # noqa: F401, E402
import src.chitrika.models.conversation  # noqa: F401, E402
import src.chitrika.models.emotion  # noqa: F401, E402
import src.chitrika.models.heartbeat  # noqa: F401, E402
import src.chitrika.models.memory  # noqa: F401, E402
import src.chitrika.models.message  # noqa: F401, E402
import src.chitrika.models.plugin  # noqa: F401, E402
import src.chitrika.models.provider  # noqa: F401, E402
import src.chitrika.models.relationship  # noqa: F401, E402
import src.chitrika.models.settings  # noqa: F401, E402


# ---------------------------------------------------------------------------
# Test engine — single connection for the entire session
# ---------------------------------------------------------------------------


@pytest.fixture
def test_engine():
    """Session-scoped in-memory SQLite with StaticPool.

    A single persistent connection keeps the in-memory database alive.
    """
    eng = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    from src.chitrika.database import configure_sqlite_engine

    configure_sqlite_engine(eng)
    SQLModel.metadata.create_all(eng)
    yield eng
    eng.dispose()


# ---------------------------------------------------------------------------
# Transaction-per-test: rollback after each test
# ---------------------------------------------------------------------------


@pytest.fixture
def session(test_engine) -> Generator[Session, None, None]:
    """A session on the per-test database shared by short-lived app sessions."""
    sess = Session(test_engine)

    yield sess

    sess.rollback()
    sess.close()


# ---------------------------------------------------------------------------
# Monkeypatch config
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _patch_app(monkeypatch):
    """Force in-memory SQLite and disable heartbeat during tests."""
    monkeypatch.setattr(config, "database_url", "sqlite:///:memory:")
    monkeypatch.setattr(config, "emotion_debug_panel", False)
    monkeypatch.setattr(config, "api_token", "test-api-token")

    # Prevent the heartbeat scheduler from actually starting its worker thread
    def _noop_start(self):
        self._running = True

    monkeypatch.setattr(
        "src.chitrika.services.heartbeat_scheduler.HeartbeatScheduler.start",
        _noop_start,
    )
    monkeypatch.setattr(
        "src.chitrika.services.heartbeat_scheduler.HeartbeatScheduler.stop",
        lambda self: None,
    )

    # Don't seed the default character during tests
    def _noop_seed(_session):
        return None

    monkeypatch.setattr(
        "src.chitrika.services.character_seed.seed_default_character",
        _noop_seed,
    )



# ---------------------------------------------------------------------------
# TestClient
# ---------------------------------------------------------------------------


@pytest.fixture
def client(test_engine, session) -> Generator[TestClient, None, None]:
    """FastAPI TestClient with session and engine overrides."""
    from src.main import app
    from src.chitrika import database

    # Patch module-level engine so lifespan uses the test engine
    original_engine = database._engine
    database._engine = test_engine

    # Override session dependency
    def _override_get_session():
        return session

    app.dependency_overrides[database.get_session] = _override_get_session

    with TestClient(
        app,
        headers={"Authorization": "Bearer test-api-token"},
    ) as tc:
        yield tc

    # Restore
    database._engine = original_engine
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Seeded character (unique name via session-level ID avoids conflicts)
# ---------------------------------------------------------------------------


@pytest.fixture
def seeded_character(session):
    """Create a test character with neutral emotion state (rolled back after test)."""
    import uuid
    from src.chitrika.models.character import Character
    from src.chitrika.models.emotion import EmotionState

    unique_name = f"test_char_{uuid.uuid4().hex[:8]}"
    char = Character(
        name=unique_name,
        display_name="Test Character",
        personality_prompt="You are a helpful test character.",
        initials="TC",
        color="#4FA3E3",
    )
    session.add(char)
    session.flush()

    emotion = EmotionState(character_id=char.id)
    session.add(emotion)
    session.commit()
    session.refresh(char)

    return char
