"""Integration tests for the Chitrika REST API."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient


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
            "display_name": "徐悦婷",
            "personality_prompt": "You are Alvia.",
            "initials": "徐",
            "color": "#E84A7A",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "alvia"
    assert data["display_name"] == "徐悦婷"
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
    """Send a message without SSE streaming — the endpoint still works.

    Since we don't have an API key, the LLM provider is None and the
    engine returns an echo response.
    """
    conv = client.post(
        "/api/conversations",
        json={"character_id": seeded_character.id},
    ).json()

    # Send message with streaming — use the stream helper on the response
    with client.stream(
        "POST",
        f"/api/conversations/{conv['id']}/messages",
        json={"content": "你好"},
    ) as resp:
        assert resp.status_code == 200

        body = b""
        for chunk in resp.iter_bytes():
            body += chunk
            if b'"type":"done"' in body or b'"type":"error"' in body:
                break

    text = body.decode("utf-8")
    assert "你好" in text  # echo response (no LLM provider = echo)


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
