"""Importance and semantic retrieval with access ranking."""

from __future__ import annotations

from src.chitrika.models.memory import Memory
from src.chitrika.repositories.memory_repository import MemoryRepository
from src.chitrika.utils import memory_embedding
from src.chitrika.utils.datetime_helpers import utcnow

SEMANTIC_CANDIDATE_POOL = 60
SEMANTIC_WEIGHT = 0.7
IMPORTANCE_WEIGHT = 0.3


class MemoryRetrievalService:
    def __init__(self, repository: MemoryRepository) -> None:
        self.repository = repository

    def get_relevant(
        self,
        character_id: str,
        *,
        memory_type: str | None = None,
        limit: int = 10,
        min_importance: float = 0.0,
        include_forgotten: bool = False,
        track_access: bool = False,
    ) -> list[Memory]:
        memories = self.repository.list_ranked(
            character_id,
            memory_type=memory_type,
            limit=limit,
            min_importance=min_importance,
            include_forgotten=include_forgotten,
        )
        if track_access:
            self._track(memories)
        return memories

    def retrieve(
        self,
        character_id: str,
        query: str,
        *,
        memory_type: str | None = None,
        limit: int = 10,
        min_importance: float = 0.0,
        track_access: bool = False,
    ) -> list[Memory]:
        query = (query or "").strip()
        query_vector = memory_embedding.embed_text(query) if query else None
        if query_vector is None:
            return self.get_relevant(
                character_id,
                memory_type=memory_type,
                limit=limit,
                min_importance=min_importance,
                track_access=track_access,
            )
        candidates = self.repository.list_ranked(
            character_id,
            memory_type=memory_type,
            limit=SEMANTIC_CANDIDATE_POOL,
            min_importance=min_importance,
        )
        scored: list[tuple[float, Memory]] = []
        for memory in candidates:
            vector = memory_embedding.vector_from_bytes(memory.embedding)
            similarity = (
                memory_embedding.cosine_similarity(query_vector, vector)
                if vector is not None else 0.0
            )
            scored.append((
                SEMANTIC_WEIGHT * similarity + IMPORTANCE_WEIGHT * memory.importance,
                memory,
            ))
        scored.sort(key=lambda item: item[0], reverse=True)
        result = [memory for _, memory in scored[:limit]]
        if track_access:
            self._track(result)
        return result

    def search(self, character_id: str, query: str, *, limit: int = 20) -> list[Memory]:
        return self.repository.search(character_id, query, limit=limit)

    def access(self, memory_id: str) -> None:
        memory = self.repository.get(memory_id)
        if memory is not None:
            self._track([memory])

    def _track(self, memories: list[Memory]) -> None:
        if not memories:
            return
        now = utcnow()
        for memory in memories:
            memory.access_count += 1
            memory.last_accessed = now
        self.repository.session.flush()

