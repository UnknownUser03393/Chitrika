"""Regression coverage for the P0/P1 local-security and streaming boundaries."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient
from sqlmodel import Session, create_engine, select


def _conversation(client: TestClient, character_id: str) -> str:
    response = client.post("/api/conversations", json={"character_id": character_id})
    assert response.status_code == 201
    return response.json()["id"]


def test_cors_rejects_arbitrary_origin_and_allows_local_dev(client: TestClient):
    headers = {
        "Origin": "https://attacker.invalid",
        "Access-Control-Request-Method": "GET",
    }
    rejected = client.options("/api/health", headers=headers)
    assert rejected.status_code == 400
    assert "access-control-allow-origin" not in rejected.headers

    allowed = client.options(
        "/api/health",
        headers={**headers, "Origin": "http://127.0.0.1:8080"},
    )
    assert allowed.status_code == 200
    assert allowed.headers["access-control-allow-origin"] == "http://127.0.0.1:8080"


def test_completed_stream_status_is_returned_in_history(
    client: TestClient, seeded_character
):
    conversation_id = _conversation(client, seeded_character.id)
    response = client.post(
        f"/api/conversations/{conversation_id}/messages",
        json={"content": "hello"},
    )
    assert response.status_code == 200
    assert '"type":"done"' in response.text

    messages = client.get(
        f"/api/conversations/{conversation_id}/messages"
    ).json()["messages"]
    assistant = next(message for message in messages if message["role"] == "assistant")
    assert assistant["generation_status"] == "complete"
    assert assistant["error_detail"] is None


def test_second_generation_for_same_conversation_returns_conflict(
    client: TestClient, seeded_character
):
    from src.chitrika.application.chat_stream_runtime import (
        release_conversation,
        try_reserve_conversation,
    )

    conversation_id = _conversation(client, seeded_character.id)
    assert try_reserve_conversation(conversation_id)
    try:
        response = client.post(
            f"/api/conversations/{conversation_id}/messages",
            json={"content": "second"},
        )
        assert response.status_code == 409
    finally:
        release_conversation(conversation_id)


def test_upstream_failure_persists_partial_response_and_structured_error(
    client: TestClient, seeded_character, monkeypatch
):
    from src.chitrika.services import chat_generation_service

    class FakeLLM:
        def stream(self, _model, _messages):
            yield SimpleNamespace(content="partial ")
            raise RuntimeError("api_key=super-secret upstream exploded")

    monkeypatch.setattr(
        chat_generation_service,
        "resolve_provider_for_character",
        lambda *_args, **_kwargs: SimpleNamespace(default_model="fake"),
    )
    monkeypatch.setattr(
        chat_generation_service,
        "create_llm_client",
        lambda *_args, **_kwargs: FakeLLM(),
    )

    conversation_id = _conversation(client, seeded_character.id)
    response = client.post(
        f"/api/conversations/{conversation_id}/messages",
        json={"content": "hello"},
    )
    events = [
        json.loads(line[6:])
        for line in response.text.splitlines()
        if line.startswith("data: ")
    ]
    error = next(event for event in events if event["type"] == "error")
    assert error["code"] == "upstream_error"
    assert error["message_id"]
    assert "super-secret" not in error["details"]

    messages = client.get(
        f"/api/conversations/{conversation_id}/messages"
    ).json()["messages"]
    assistant = next(message for message in messages if message["role"] == "assistant")
    assert assistant["content"] == "partial "
    assert assistant["generation_status"] == "error"
    assert "super-secret" not in assistant["error_detail"]


def test_zero_content_upstream_failure_still_persists_error_message(
    client: TestClient, seeded_character, monkeypatch
):
    from src.chitrika.services import chat_generation_service

    class EmptyFailure:
        def stream(self, _model, _messages):
            raise TimeoutError("upstream timed out")
            yield  # pragma: no cover - makes this a generator

    monkeypatch.setattr(
        chat_generation_service,
        "resolve_provider_for_character",
        lambda *_args, **_kwargs: SimpleNamespace(default_model="fake"),
    )
    monkeypatch.setattr(
        chat_generation_service,
        "create_llm_client",
        lambda *_args, **_kwargs: EmptyFailure(),
    )
    conversation_id = _conversation(client, seeded_character.id)
    response = client.post(
        f"/api/conversations/{conversation_id}/messages",
        json={"content": "hello"},
    )
    assert '"code":"upstream_error"' in response.text
    messages = client.get(
        f"/api/conversations/{conversation_id}/messages"
    ).json()["messages"]
    assistant = next(message for message in messages if message["role"] == "assistant")
    assert assistant["content"] == ""
    assert assistant["generation_status"] == "error"


def test_client_disconnect_persists_partial_as_interrupted(
    client: TestClient, seeded_character, monkeypatch
):
    from src.chitrika.database import session_scope
    from src.chitrika.application.chat_stream_runtime import (
        prepare_chat_stream,
        stream_prepared_response,
        try_reserve_conversation,
    )
    monkeypatch.setattr(
        "src.chitrika.services.chat_generation_service.resolve_provider_for_character",
        lambda *_args, **_kwargs: None,
    )

    conversation_id = _conversation(client, seeded_character.id)
    assert try_reserve_conversation(conversation_id)
    with session_scope() as session:
        prepared = prepare_chat_stream(session, conversation_id, "hello")
    stream = stream_prepared_response(prepared)
    next(stream)  # start
    next(stream)  # echo content
    stream.close()

    messages = client.get(
        f"/api/conversations/{conversation_id}/messages"
    ).json()["messages"]
    assistant = next(message for message in messages if message["role"] == "assistant")
    assert assistant["generation_status"] == "interrupted"
    assert assistant["content"] == "[echo] hello"
    assert assistant["error_detail"]


def test_existing_database_migrates_with_backup_and_repairs_defaults(tmp_path: Path):
    from src.chitrika import database

    db_path = tmp_path / "legacy.db"
    with sqlite3.connect(db_path) as connection:
        connection.executescript(
            """
            CREATE TABLE messages (
                id TEXT PRIMARY KEY, conversation_id TEXT NOT NULL, role TEXT NOT NULL,
                content TEXT NOT NULL, created_at DATETIME NOT NULL, edited_at DATETIME,
                is_deleted BOOLEAN NOT NULL DEFAULT 0, read_at DATETIME,
                desktop_notified_at DATETIME, scheduled_message_id TEXT
            );
            CREATE TABLE llm_providers (
                id TEXT PRIMARY KEY, name TEXT, display_name TEXT, provider_type TEXT,
                plugin_id TEXT, api_key TEXT, base_url TEXT, default_model TEXT,
                custom_config JSON, is_default BOOLEAN, enabled BOOLEAN,
                created_at DATETIME, updated_at DATETIME
            );
            INSERT INTO llm_providers VALUES
                ('a','a','A','openai',NULL,'','','','{}',1,1,'2020-01-01','2020-01-01'),
                ('b','b','B','openai',NULL,'','','','{}',1,1,'2021-01-01','2021-01-01'),
                ('c','c','C','openai',NULL,'','','','{}',1,0,'2022-01-01','2022-01-01');
            """
        )

    original_engine = database._engine
    engine = create_engine(
        f"sqlite:///{db_path.as_posix()}",
        connect_args={"check_same_thread": False},
    )
    database.configure_sqlite_engine(engine)
    database._engine = engine
    try:
        database.create_db_and_tables()
        database.create_db_and_tables()  # idempotent
        with engine.connect() as connection:
            columns = {
                row[1] for row in connection.exec_driver_sql("PRAGMA table_info(messages)")
            }
            defaults = list(connection.exec_driver_sql(
                "SELECT id FROM llm_providers WHERE enabled=1 AND is_default=1"
            ))
            disabled_default = connection.exec_driver_sql(
                "SELECT is_default FROM llm_providers WHERE id='c'"
            ).scalar_one()
        assert {"generation_status", "error_detail"} <= columns
        assert defaults == [("b",)]
        assert disabled_default == 0
        assert list(tmp_path.glob("legacy.db.pre-migration-*.bak"))
    finally:
        engine.dispose()
        database._engine = original_engine


def test_restore_rejects_invalid_shapes_and_rolls_back(client: TestClient):
    malformed = client.post(
        "/api/restore",
        files={"file": ("backup.json", b"[]", "application/json")},
    )
    assert malformed.status_code == 400

    payload = {
        "format": "chitrika-backup",
        "version": 1,
        "characters": [{"id": "would-have-been-created"}],
        "conversations": [],
        "memories": [{"id": "invalid-memory"}],
        "settings": {},
    }
    failed = client.post(
        "/api/restore",
        files={
            "file": (
                "backup.json",
                json.dumps(payload).encode(),
                "application/json",
            )
        },
    )
    assert failed.status_code >= 400
    characters = client.get("/api/characters").json()["characters"]
    assert all(character["id"] != "would-have-been-created" for character in characters)


def test_restore_enforces_bounded_chunked_read(client: TestClient, monkeypatch):
    monkeypatch.setattr("src.chitrika.routes.export_routes.MAX_BACKUP_BYTES", 32)
    response = client.post(
        "/api/restore",
        files={"file": ("large.json", b"x" * 33, "application/json")},
    )
    assert response.status_code == 413


def test_disabling_default_provider_clears_default_flag(client: TestClient):
    created = client.post(
        "/api/providers",
        json={
            "name": "hardening-provider",
            "display_name": "Hardening Provider",
            "is_default": True,
        },
    )
    assert created.status_code == 201
    provider_id = created.json()["id"]
    disabled = client.patch(
        f"/api/providers/{provider_id}",
        json={"enabled": False},
    )
    assert disabled.status_code == 200
    assert disabled.json()["enabled"] is False
    assert disabled.json()["is_default"] is False
