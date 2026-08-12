"""Memory vector generation and historical backfill."""

from __future__ import annotations

import logging

from src.chitrika.repositories.memory_repository import MemoryRepository
from src.chitrika.utils import memory_embedding

logger = logging.getLogger("chitrika.memory.embedding")


class EmbeddingService:
    def __init__(self, repository: MemoryRepository) -> None:
        self.repository = repository

    @staticmethod
    def embed(content: str) -> bytes | None:
        vector = memory_embedding.embed_text(content)
        return None if vector is None else memory_embedding.vector_to_bytes(vector)

    def backfill(self, character_id: str, *, limit: int = 50) -> int:
        if not memory_embedding.embedding_available():
            return 0
        filled = 0
        for memory in self.repository.list_missing_embeddings(character_id, limit=limit):
            blob = self.embed(memory.content)
            if blob is not None:
                memory.embedding = blob
                filled += 1
        if filled:
            self.repository.session.flush()
            logger.info("Backfilled %d memory embeddings for %s", filled, character_id)
        return filled

