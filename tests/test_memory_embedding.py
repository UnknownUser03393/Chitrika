"""Tests for semantic memory recall (local embedding + cosine re-ranking)."""

from __future__ import annotations

import numpy as np

from src.chitrika.repositories.memory_repository import MemoryRepository
from src.chitrika.services.memory_lifecycle_service import MemoryLifecycleService
from src.chitrika.services.memory_retrieval_service import MemoryRetrievalService
from src.chitrika.utils import memory_embedding


def _services(session):
    repository = MemoryRepository(session)
    return (
        repository,
        MemoryLifecycleService(repository),
        MemoryRetrievalService(repository),
    )


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def test_vector_bytes_round_trip():
    vector = np.array([0.1, -0.2, 0.3], dtype=np.float32)
    restored = memory_embedding.vector_from_bytes(memory_embedding.vector_to_bytes(vector))
    assert restored is not None
    assert np.allclose(restored, vector)


def test_vector_from_bytes_handles_none():
    assert memory_embedding.vector_from_bytes(None) is None
    assert memory_embedding.vector_from_bytes(b"") is None


def test_cosine_similarity_bounds():
    a = np.array([1.0, 0.0], dtype=np.float32)
    assert memory_embedding.cosine_similarity(a, a) == 1.0
    assert memory_embedding.cosine_similarity(a, np.array([0.0, 1.0])) == 0.0
    assert memory_embedding.cosine_similarity(a, np.array([0.0, 0.0])) == 0.0


# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------


def _fake_embed(text: str):
    """Toy embedder: three orthogonal topics so similarity is predictable."""
    lowered = text.lower()
    if any(term in lowered for term in ["猫", "团子", "cat", "kitten"]):
        vec = [1.0, 0.0, 0.0]
    elif any(term in lowered for term in ["工作", "医院", "work"]):
        vec = [0.0, 1.0, 0.0]
    else:
        vec = [0.0, 0.0, 1.0]
    return np.array(vec, dtype=np.float32)


def test_retrieve_relevant_ranks_by_semantic_similarity(session, seeded_character, monkeypatch):
    monkeypatch.setattr(memory_embedding, "embed_text", _fake_embed)
    _, lifecycle, retrieval = _services(session)

    lifecycle.store(seeded_character.id, "long_term", "用户养了一只叫团子的猫", importance=0.5)
    lifecycle.store(seeded_character.id, "long_term", "用户在一家医院工作", importance=0.5)
    lifecycle.store(seeded_character.id, "long_term", "用户喜欢看电影", importance=0.5)

    # "小猫咪" shares no characters with "团子" but is semantically the cat memory.
    results = retrieval.retrieve(seeded_character.id, query="我家小猫咪生病了", limit=1)

    assert len(results) == 1
    assert "团子" in results[0].content


def test_retrieve_relevant_falls_back_to_importance_when_no_model(
    session, seeded_character, monkeypatch
):
    # No embedding model → embed_text returns None → importance ordering.
    monkeypatch.setattr(memory_embedding, "embed_text", lambda _text: None)
    _, lifecycle, retrieval = _services(session)

    lifecycle.store(seeded_character.id, "long_term", "低优先级事实", importance=0.2)
    lifecycle.store(seeded_character.id, "long_term", "高优先级事实", importance=0.9)

    results = retrieval.retrieve(seeded_character.id, query="anything", limit=2)

    assert [m.content for m in results] == ["高优先级事实", "低优先级事实"]


def test_store_persists_embedding(session, seeded_character, monkeypatch):
    monkeypatch.setattr(memory_embedding, "embed_text", _fake_embed)
    _, lifecycle, _ = _services(session)

    memory = lifecycle.store(seeded_character.id, "long_term", "用户养了一只猫", importance=0.5)

    restored = memory_embedding.vector_from_bytes(memory.embedding)
    assert restored is not None
    assert np.allclose(restored, _fake_embed("猫"))


# ---------------------------------------------------------------------------
# Episodic summarization helpers
# ---------------------------------------------------------------------------


def test_list_short_term_returns_recent_batch(session, seeded_character):
    repository, lifecycle, _ = _services(session)
    for i in range(5):
        lifecycle.store(seeded_character.id, "short_term", f"片段 {i}", importance=0.2)

    batch = repository.list_short_term(seeded_character.id, limit=3)

    # Newest first.
    assert [m.content for m in batch] == ["片段 4", "片段 3", "片段 2"]


def test_list_short_term_excludes_archived(session, seeded_character):
    repository, lifecycle, _ = _services(session)
    lifecycle.store(seeded_character.id, "short_term", "活跃片段", importance=0.2)
    dead = lifecycle.store(seeded_character.id, "short_term", "已归档片段", importance=0.2)
    lifecycle.archive([dead.id])

    assert [m.content for m in repository.list_short_term(seeded_character.id, limit=30)] == ["活跃片段"]


def test_short_term_not_trimmed_below_limit(session, seeded_character):
    """Regression: the old trim used a negative slice, forgetting memories
    well before SHORT_TERM_LIMIT. A batch below the cap must survive intact."""
    repository, lifecycle, _ = _services(session)
    for i in range(30):
        lifecycle.store(seeded_character.id, "short_term", f"话 {i}", importance=0.2)

    assert len(repository.list_short_term(seeded_character.id, limit=30)) == 30


def test_archive_memories_soft_forgets(session, seeded_character):
    _, lifecycle, _ = _services(session)
    m1 = lifecycle.store(seeded_character.id, "short_term", "甲", importance=0.2)
    m2 = lifecycle.store(seeded_character.id, "short_term", "乙", importance=0.2)

    archived = lifecycle.archive([m1.id, m2.id, "nonexistent"])

    assert archived == 2
    assert m1.is_forgotten is True
    assert m2.is_forgotten is True


def test_heartbeat_summarizes_filled_batch(session, seeded_character, monkeypatch):
    from sqlmodel import select

    from src.chitrika.engines.settings_engine import SettingsEngine
    from src.chitrika.models.memory import Memory
    from src.chitrika.services.heartbeat_services import EpisodicMemoryService

    SettingsEngine(session).set("memory_episodic_summary", True)

    repository, lifecycle, _ = _services(session)
    for i in range(30):
        lifecycle.store(seeded_character.id, "short_term", f"用户说了些话 {i}", importance=0.2)

    class _FakeResponse:
        content = "我和用户聊了很久，用户分享了日常。"

    class _FakeClient:
        def send(self, model, chat):
            return _FakeResponse()

    class _FakeProvider:
        default_model = "fake-model"

    monkeypatch.setattr(
        "src.chitrika.services.provider_service.resolve_provider_for_character",
        lambda *_a, **_k: _FakeProvider(),
    )
    monkeypatch.setattr(
        "src.chitrika.services.provider_service.create_llm_client",
        lambda *_a, **_k: _FakeClient(),
    )

    EpisodicMemoryService(session, lifecycle).summarize_recent(seeded_character)

    episodic = session.exec(
        select(Memory).where(
            Memory.character_id == seeded_character.id,
            Memory.memory_type == "episodic",
        )
    ).all()
    assert len(episodic) == 1
    assert "聊" in episodic[0].content
    # The summarized short-term batch was archived.
    assert repository.list_short_term(seeded_character.id, limit=30) == []


def test_heartbeat_skips_below_batch_size(session, seeded_character, monkeypatch):
    from src.chitrika.engines.settings_engine import SettingsEngine
    from src.chitrika.services.heartbeat_services import EpisodicMemoryService

    SettingsEngine(session).set("memory_episodic_summary", True)

    repository, lifecycle, _ = _services(session)
    for i in range(5):
        lifecycle.store(seeded_character.id, "short_term", f"话 {i}", importance=0.2)

    EpisodicMemoryService(session, lifecycle).summarize_recent(seeded_character)

    # No LLM call attempted → no episodic memory created.
    from sqlmodel import select

    from src.chitrika.models.memory import Memory

    episodic = session.exec(
        select(Memory).where(
            Memory.character_id == seeded_character.id,
            Memory.memory_type == "episodic",
        )
    ).all()
    assert episodic == []
    assert len(repository.list_short_term(seeded_character.id, limit=30)) == 5
