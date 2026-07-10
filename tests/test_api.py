"""Integration tests for the Chitrika REST API."""

from __future__ import annotations

import json
from contextlib import contextmanager
from datetime import timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


def test_health(client: TestClient):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "version" in data


# ---------------------------------------------------------------------------
# Characters
# ---------------------------------------------------------------------------


def test_list_characters_empty(client: TestClient):
    """No characters initially (in-memory DB is fresh)."""
    resp = client.get("/api/characters")
    assert resp.status_code == 200
    data = resp.json()
    assert data["characters"] == []


def test_create_character(client: TestClient):
    resp = client.post(
        "/api/characters",
        json={
            "name": "alvia",
            "display_name": "\u5f90\u60a6\u5a77",
            "personality_prompt": "You are Alvia.",
            "initials": "\u5f90",
            "color": "#E84A7A",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "alvia"
    assert data["display_name"] == "\u5f90\u60a6\u5a77"
    assert data["enabled"] is True
    assert "id" in data


def test_create_duplicate_character(client: TestClient):
    """Creating a character with a duplicate name should 409."""
    client.post("/api/characters", json={"name": "dup", "display_name": "Dup"})
    resp = client.post("/api/characters", json={"name": "dup", "display_name": "Dup"})
    assert resp.status_code == 409


def test_get_character(client: TestClient, seeded_character):
    resp = client.get(f"/api/characters/{seeded_character.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == seeded_character.name


def test_get_character_404(client: TestClient):
    resp = client.get("/api/characters/nonexistent")
    assert resp.status_code == 404


def test_update_character(client: TestClient, seeded_character):
    resp = client.patch(
        f"/api/characters/{seeded_character.id}",
        json={"display_name": "Updated Name"},
    )
    assert resp.status_code == 200
    assert resp.json()["display_name"] == "Updated Name"


def test_delete_character(client: TestClient, seeded_character):
    """Soft-delete: character should be marked disabled."""
    resp = client.delete(f"/api/characters/{seeded_character.id}")
    assert resp.status_code == 204

    # Verify it's disabled
    resp2 = client.get(f"/api/characters/{seeded_character.id}")
    assert resp2.json()["enabled"] is False


# ---------------------------------------------------------------------------
# Emotion
# ---------------------------------------------------------------------------


def test_get_emotion(client: TestClient, seeded_character):
    resp = client.get(f"/api/characters/{seeded_character.id}/emotion")
    assert resp.status_code == 200
    data = resp.json()
    assert "emotions" in data
    assert "mood" in data
    assert "loneliness" in data
    assert "dominant" in data
    # Default neutral: all emotions should be 0.0
    for v in data["emotions"].values():
        assert v == pytest.approx(0.0)


def test_apply_emotion_delta(client: TestClient, seeded_character):
    resp = client.post(
        f"/api/characters/{seeded_character.id}/emotion",
        json={"joy": 0.5, "trust": 0.3, "sadness": -0.1},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["emotions"]["joy"] == pytest.approx(0.5)
    assert data["emotions"]["trust"] == pytest.approx(0.3)
    assert data["mood"] in ("happy", "ecstatic", "calm", "neutral")


def test_get_emotion_404(client: TestClient):
    resp = client.get("/api/characters/nonexistent/emotion")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Conversations
# ---------------------------------------------------------------------------


def test_list_conversations_empty(client: TestClient):
    resp = client.get("/api/conversations")
    assert resp.status_code == 200
    assert resp.json() == []


def test_create_conversation(client: TestClient, seeded_character):
    resp = client.post(
        "/api/conversations",
        json={"character_id": seeded_character.id},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["character_id"] == seeded_character.id
    assert "id" in data


def test_create_conversation_bad_character(client: TestClient):
    resp = client.post(
        "/api/conversations",
        json={"character_id": "nonexistent"},
    )
    assert resp.status_code == 404


def test_get_conversation(client: TestClient, seeded_character):
    # Create first
    created = client.post(
        "/api/conversations",
        json={"character_id": seeded_character.id},
    ).json()

    resp = client.get(f"/api/conversations/{created['id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == created["id"]


def test_delete_conversation(client: TestClient, seeded_character):
    created = client.post(
        "/api/conversations",
        json={"character_id": seeded_character.id},
    ).json()

    resp = client.delete(f"/api/conversations/{created['id']}")
    assert resp.status_code == 204

    # Verify it's gone
    resp2 = client.get(f"/api/conversations/{created['id']}")
    assert resp2.status_code == 404


def test_chats_alias(client: TestClient):
    """GET /api/chats should work as alias for /api/conversations."""
    resp = client.get("/api/chats")
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Messages
# ---------------------------------------------------------------------------


def test_get_messages_empty(client: TestClient, seeded_character):
    conv = client.post(
        "/api/conversations",
        json={"character_id": seeded_character.id},
    ).json()

    resp = client.get(f"/api/conversations/{conv['id']}/messages")
    assert resp.status_code == 200
    data = resp.json()
    assert data["messages"] == []


def test_send_message_stream(client: TestClient, seeded_character):
    """Send a message through the SSE endpoint.

    Since we don't have an API key, the LLM provider is None and the
    engine returns an echo response.
    """
    conv = client.post(
        "/api/conversations",
        json={"character_id": seeded_character.id},
    ).json()

    with client.stream(
        "POST",
        f"/api/conversations/{conv['id']}/messages",
        json={"content": "\u4f60\u597d"},
    ) as resp:
        assert resp.status_code == 200

        body = b""
        for chunk in resp.iter_bytes():
            body += chunk
            if b'"type":"done"' in body or b'"type":"error"' in body:
                break

    text = body.decode("utf-8")
    assert "\u4f60\u597d" in text


def test_stream_response_single_message(session, seeded_character):
    """The entire LLM response is delivered as one message bubble."""
    from sqlmodel import select

    from src.chitrika.engines.chat_engine import ChatEngine
    from src.chitrika.models.message import Message

    class Chunk:
        def __init__(self, content: str):
            self.content = content

    class FakeLLM:
        def stream(self, _model, _messages):
            yield Chunk("\u7b2c\u4e00\u53e5\u3002")
            yield Chunk("\u7b2c\u4e8c\u53e5\uff01\n\u7b2c\u4e09\u53e5")

    engine = ChatEngine(session, llm_provider=FakeLLM(), model_name="fake")
    conv = engine.create_conversation(seeded_character.id)

    events = list(engine.stream_response(conv.id, "\u4f60\u597d"))

    assert sum('"type":"start"' in event for event in events) == 1
    assert sum('"type":"done"' in event for event in events) == 1

    messages = list(
        session.exec(
            select(Message)
            .where(Message.conversation_id == conv.id)
            .order_by(Message.created_at)
        ).all()
    )
    assistant_contents = [m.content for m in messages if m.role == "assistant"]
    assert assistant_contents == ["\u7b2c\u4e00\u53e5\u3002\u7b2c\u4e8c\u53e5\uff01\n\u7b2c\u4e09\u53e5"]


def test_post_process_emotions_uses_nuanced_signals(session, seeded_character):
    """A mixed message should update multiple emotion dimensions."""
    from src.chitrika.engines.chat_engine import ChatEngine

    engine = ChatEngine(session)
    engine._emotion.get_or_create_state(seeded_character.id)

    engine._post_process_emotions(
        seeded_character.id,
        "\u6211\u6709\u70b9\u62c5\u5fc3\uff0c\u4e5f\u5f88\u671f\u5f85\u4f60\u56de\u6765\uff0c\u8c22\u8c22\uff01",
        "\u6211\u4e5f\u5f88\u5f00\u5fc3\uff0c\u8c22\u8c22\u4f60\u544a\u8bc9\u6211\u3002",
    )

    analysis = engine._emotion.analyse(seeded_character.id, apply_decay_before=False)
    emotions = analysis["emotions"]

    assert emotions["fear"] > 0
    assert emotions["anticipation"] > emotions["fear"]
    assert emotions["trust"] > 0
    assert emotions["joy"] > 0
    assert emotions["surprise"] > 0


def test_relative_time_uses_readable_chinese_labels():
    from src.chitrika.engines.chat_engine import _relative_time
    from src.chitrika.utils.datetime_helpers import utcnow

    now = utcnow()
    assert _relative_time(now) == "\u521a\u521a"
    assert _relative_time(now - timedelta(minutes=5)) == "5\u5206\u949f\u524d"
    assert _relative_time(now - timedelta(hours=2)) == "2\u5c0f\u65f6\u524d"
    assert _relative_time(now - timedelta(days=3)) == "3\u5929\u524d"


def test_edit_message(client: TestClient, seeded_character):
    """Edit a message after sending."""
    conv = client.post(
        "/api/conversations",
        json={"character_id": seeded_character.id},
    ).json()

    # Send message (streaming)
    with client.stream(
        "POST",
        f"/api/conversations/{conv['id']}/messages",
        json={"content": "Hi"},
    ) as resp:
        for chunk in resp.iter_bytes():
            if b'"type":"done"' in chunk:
                break

    # Get messages to find the user message ID
    msgs = client.get(f"/api/conversations/{conv['id']}/messages").json()
    user_msg = [m for m in msgs["messages"] if m["role"] == "user"][0]

    # Edit it
    edit_resp = client.patch(
        f"/api/messages/{user_msg['id']}",
        json={"content": "Hello, edited!"},
    )
    assert edit_resp.status_code == 200
    assert edit_resp.json()["content"] == "Hello, edited!"


def test_delete_message(client: TestClient, seeded_character):
    """Soft-delete a message."""
    conv = client.post(
        "/api/conversations",
        json={"character_id": seeded_character.id},
    ).json()

    # Send message (streaming)
    with client.stream(
        "POST",
        f"/api/conversations/{conv['id']}/messages",
        json={"content": "Delete me"},
    ) as resp:
        for chunk in resp.iter_bytes():
            if b'"type":"done"' in chunk:
                break

    msgs = client.get(f"/api/conversations/{conv['id']}/messages").json()
    user_msg = [m for m in msgs["messages"] if m["role"] == "user"][0]

    resp = client.delete(f"/api/messages/{user_msg['id']}")
    assert resp.status_code == 204

    # Deleted message should not appear in list
    msgs2 = client.get(f"/api/conversations/{conv['id']}/messages").json()
    assert all(m["id"] != user_msg["id"] for m in msgs2["messages"])


def test_recall_message(client: TestClient, seeded_character):
    """Recall keeps the message visible with a recalled marker."""
    conv = client.post(
        "/api/conversations",
        json={"character_id": seeded_character.id},
    ).json()

    with client.stream(
        "POST",
        f"/api/conversations/{conv['id']}/messages",
        json={"content": "Recall me"},
    ) as resp:
        for chunk in resp.iter_bytes():
            if b'"type":"done"' in chunk:
                break

    msgs = client.get(f"/api/conversations/{conv['id']}/messages").json()
    user_msg = [m for m in msgs["messages"] if m["role"] == "user"][0]

    resp = client.post(f"/api/messages/{user_msg['id']}/recall")
    assert resp.status_code == 200
    assert resp.json()["content"] == '(recalled) "Recall me"'
    assert resp.json()["edited_at"] is not None

    msgs2 = client.get(f"/api/conversations/{conv['id']}/messages").json()
    recalled = [m for m in msgs2["messages"] if m["id"] == user_msg["id"]][0]
    assert recalled["content"] == '(recalled) "Recall me"'


def test_recall_assistant_message_is_rejected(client: TestClient, seeded_character):
    """Assistant messages are received messages; they can be deleted, not recalled."""
    conv = client.post(
        "/api/conversations",
        json={"character_id": seeded_character.id},
    ).json()

    with client.stream(
        "POST",
        f"/api/conversations/{conv['id']}/messages",
        json={"content": "Delete assistant only"},
    ) as resp:
        for chunk in resp.iter_bytes():
            if b'"type":"done"' in chunk:
                break

    msgs = client.get(f"/api/conversations/{conv['id']}/messages").json()
    assistant_msg = [m for m in msgs["messages"] if m["role"] == "assistant"][0]

    resp = client.post(f"/api/messages/{assistant_msg['id']}/recall")
    assert resp.status_code == 400


def test_clear_conversation_messages(client: TestClient, seeded_character):
    """Clear all messages while keeping the conversation."""
    conv = client.post(
        "/api/conversations",
        json={"character_id": seeded_character.id},
    ).json()

    with client.stream(
        "POST",
        f"/api/conversations/{conv['id']}/messages",
        json={"content": "Clear this history"},
    ) as resp:
        for chunk in resp.iter_bytes():
            if b'"type":"done"' in chunk:
                break

    before = client.get(f"/api/conversations/{conv['id']}/messages").json()
    assert len(before["messages"]) > 0

    resp = client.delete(f"/api/conversations/{conv['id']}/messages")
    assert resp.status_code == 204

    conv_resp = client.get(f"/api/conversations/{conv['id']}")
    assert conv_resp.status_code == 200

    after = client.get(f"/api/conversations/{conv['id']}/messages").json()
    assert after["messages"] == []

    chats = client.get("/api/conversations").json()
    assert len(chats) == 1
    assert chats[0]["lastMessage"] == ""
    assert chats[0]["time"] == ""


# ---------------------------------------------------------------------------
# Chat list enrichment
# ---------------------------------------------------------------------------


def test_conversation_list_enriched(client: TestClient, seeded_character):
    """After creating a conversation and sending a message, the chat list
    should show the last message preview and character info."""
    # Create conversation
    conv = client.post(
        "/api/conversations",
        json={"character_id": seeded_character.id},
    ).json()

    # Send a message (streaming)
    with client.stream(
        "POST",
        f"/api/conversations/{conv['id']}/messages",
        json={"content": "Hello world"},
    ) as resp:
        for chunk in resp.iter_bytes():
            if b'"type":"done"' in chunk:
                break

    # Check chat list
    chats = client.get("/api/conversations").json()
    assert len(chats) == 1
    assert chats[0]["name"] == seeded_character.display_name
    assert chats[0]["initials"] == seeded_character.initials


def test_conversation_list_uses_batched_enrichment(session, seeded_character):
    from src.chitrika.engines.chat_engine import ChatEngine
    from src.chitrika.models.message import Message

    engine = ChatEngine(session)
    conversations = [
        engine.create_conversation(seeded_character.id)
        for _ in range(3)
    ]
    for index, conv in enumerate(conversations):
        session.add(
            Message(
                conversation_id=conv.id,
                role="user",
                content=f"message {index}",
            )
        )
    session.commit()

    statements: list[str] = []

    def _record(_conn, _cursor, statement, _parameters, _context, _executemany):
        statements.append(statement)

    event.listen(session.bind, "before_cursor_execute", _record)
    try:
        chats = engine.list_conversations()
    finally:
        event.remove(session.bind, "before_cursor_execute", _record)

    assert len(chats) == 3
    assert len(statements) <= 4  # conversations + characters + last_message + unread


# ---------------------------------------------------------------------------
# Memories
# ---------------------------------------------------------------------------


def test_create_memory(client: TestClient, seeded_character):
    resp = client.post(
        f"/api/characters/{seeded_character.id}/memories",
        json={
            "memory_type": "long_term",
            "content": "User likes cats",
            "importance": 0.7,
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["content"] == "User likes cats"
    assert data["importance"] == pytest.approx(0.7)


def test_list_memories(client: TestClient, seeded_character):
    # Create a couple memories
    client.post(
        f"/api/characters/{seeded_character.id}/memories",
        json={"content": "Memory 1", "importance": 0.5},
    )
    client.post(
        f"/api/characters/{seeded_character.id}/memories",
        json={"content": "Memory 2", "importance": 0.8},
    )

    resp = client.get(f"/api/characters/{seeded_character.id}/memories")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    # Ordered by importance DESC
    assert data["memories"][0]["content"] == "Memory 2"


def test_search_memories(client: TestClient, seeded_character):
    client.post(
        f"/api/characters/{seeded_character.id}/memories",
        json={"content": "User loves programming", "importance": 0.6},
    )
    client.post(
        f"/api/characters/{seeded_character.id}/memories",
        json={"content": "User hates broccoli", "importance": 0.4},
    )

    resp = client.get(
        f"/api/characters/{seeded_character.id}/memories/search",
        params={"q": "programming"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert "programming" in data["memories"][0]["content"]


def test_update_memory(client: TestClient, seeded_character):
    created = client.post(
        f"/api/characters/{seeded_character.id}/memories",
        json={"content": "Original", "importance": 0.3},
    ).json()

    resp = client.patch(
        f"/api/memories/{created['id']}",
        json={"is_pinned": True, "importance": 0.9},
    )
    assert resp.status_code == 200
    assert resp.json()["is_pinned"] is True
    assert resp.json()["importance"] == pytest.approx(0.9)


def test_delete_memory(client: TestClient, seeded_character):
    created = client.post(
        f"/api/characters/{seeded_character.id}/memories",
        json={"content": "To be deleted"},
    ).json()

    resp = client.delete(f"/api/memories/{created['id']}")
    assert resp.status_code == 204

    missing = client.patch(
        f"/api/memories/{created['id']}",
        json={"is_forgotten": True},
    )
    assert missing.status_code == 404


# ---------------------------------------------------------------------------
# Heartbeat
# ---------------------------------------------------------------------------


def test_heartbeat_status(client: TestClient):
    resp = client.get("/api/heartbeat/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "running" in data
    assert "tick_interval_minutes" in data
    assert "loneliness_threshold" in data


def test_heartbeat_uses_injected_session_factory(session, seeded_character):
    from sqlmodel import select

    from src.chitrika.engines.heartbeat_engine import HeartbeatEngine
    from src.chitrika.models.heartbeat import HeartbeatTask

    @contextmanager
    def _session_factory():
        yield session

    engine = HeartbeatEngine(session_factory=_session_factory)
    engine.tick()

    assert engine.status["tick_count"] == 1
    task = session.exec(
        select(HeartbeatTask).where(HeartbeatTask.character_id == seeded_character.id)
    ).first()
    assert task is not None


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------


def test_404_character(client: TestClient):
    resp = client.get("/api/characters/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


def test_404_conversation(client: TestClient):
    resp = client.get("/api/conversations/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


def test_404_message(client: TestClient):
    resp = client.patch(
        "/api/messages/00000000-0000-0000-0000-000000000000",
        json={"content": "nope"},
    )
    assert resp.status_code == 404
