"""Creation, reinforcement, decay, archival, trimming, and cleanup."""

from __future__ import annotations

import logging
from datetime import timedelta

from src.chitrika.models.memory import Memory
from src.chitrika.repositories.memory_repository import MemoryRepository
from src.chitrika.services.embedding_service import EmbeddingService
from src.chitrika.utils.datetime_helpers import days_between, utcnow

logger = logging.getLogger("chitrika.memory.lifecycle")
SHORT_TERM_LIMIT = 50
DECAY_THRESHOLD = 0.15
ACCESS_DECAY_DAYS = 30


class MemoryLifecycleService:
    def __init__(
        self,
        repository: MemoryRepository,
        embeddings: EmbeddingService | None = None,
    ) -> None:
        self.repository = repository
        self.embeddings = embeddings or EmbeddingService(repository)

    def store(
        self,
        character_id: str,
        memory_type: str,
        content: str,
        *,
        importance: float | None = None,
        emotional_valence: float | None = None,
        source_message_id: str | None = None,
        is_pinned: bool = False,
    ) -> Memory:
        content = content.strip()
        if not content:
            raise ValueError("Memory content cannot be empty")
        if memory_type in {"long_term", "episodic"}:
            existing = self.repository.find_duplicate(character_id, memory_type, content)
            if existing is not None:
                existing.is_forgotten = False
                existing.last_accessed = utcnow()
                existing.access_count += 1
                existing.importance = min(
                    1.0, max(existing.importance, importance or 0.0) + 0.05
                )
                existing.is_pinned = existing.is_pinned or is_pinned
                if existing.embedding is None:
                    existing.embedding = self.embeddings.embed(content)
                self.repository.session.flush()
                return existing
        if importance is None:
            importance = self.compute_importance(
                emotional_valence=emotional_valence, is_pinned=is_pinned
            )
        if source_message_id and not self.repository.source_message_exists(source_message_id):
            logger.warning("Ignoring missing source message %s while storing memory", source_message_id)
            source_message_id = None
        memory = self.repository.add(Memory(
            character_id=character_id,
            memory_type=memory_type,
            content=content,
            importance=importance,
            emotional_valence=emotional_valence,
            source_message_id=source_message_id,
            is_pinned=is_pinned,
            embedding=self.embeddings.embed(content),
        ))
        if memory_type == "short_term":
            self.trim_short_term(character_id)
        return memory

    def update(self, memory_id: str, **values) -> Memory | None:
        memory = self.repository.get(memory_id)
        if memory is None:
            return None
        for key in ("content", "importance", "is_pinned", "is_forgotten"):
            value = values.get(key)
            if value is not None:
                setattr(memory, key, value)
        self.repository.session.flush()
        return memory

    def archive(self, memory_ids: list[str]) -> int:
        count = 0
        for memory_id in memory_ids:
            memory = self.repository.get(memory_id)
            if memory is not None and not memory.is_forgotten:
                memory.is_forgotten = True
                count += 1
        if count:
            self.repository.session.flush()
        return count

    def decay(self, character_id: str) -> int:
        now = utcnow()
        forgotten = 0
        for memory in self.repository.list_active_unpinned(character_id):
            age = days_between(now, memory.last_accessed)
            if age < 7:
                continue
            memory.importance *= 0.95 if age < ACCESS_DECAY_DAYS else 0.80
            if memory.importance < DECAY_THRESHOLD:
                memory.is_forgotten = True
                forgotten += 1
        self.repository.session.flush()
        return forgotten

    def prune(self, character_id: str) -> int:
        memories = self.repository.list_forgotten_before(
            character_id, utcnow() - timedelta(days=7)
        )
        for memory in memories:
            self.repository.delete(memory)
        self.repository.session.flush()
        return len(memories)

    def trim_short_term(self, character_id: str) -> None:
        memories = self.repository.list_short_term(
            character_id, limit=SHORT_TERM_LIMIT + 1000
        )
        # Repository returns newest first; archive the oldest excess.
        excess = len(memories) - SHORT_TERM_LIMIT
        if excess > 0:
            for memory in memories[-excess:]:
                memory.is_forgotten = True

    @staticmethod
    def compute_importance(
        *,
        emotional_valence: float | None = None,
        repetition_count: int = 0,
        is_pinned: bool = False,
    ) -> float:
        base = abs(emotional_valence) if emotional_valence is not None else 0.3
        return min(
            1.0,
            max(0.0, base + min(repetition_count * 0.05, 0.3) + (0.5 if is_pinned else 0.0)),
        )
