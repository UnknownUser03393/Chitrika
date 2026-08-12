"""Persistence operations for character memories."""

from __future__ import annotations

from sqlmodel import Session, col, select

from src.chitrika.models.memory import Memory
from src.chitrika.models.message import Message


class MemoryRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, memory_id: str) -> Memory | None:
        return self.session.get(Memory, memory_id)

    def find_duplicate(
        self, character_id: str, memory_type: str, content: str
    ) -> Memory | None:
        return self.session.exec(
            select(Memory).where(
                Memory.character_id == character_id,
                Memory.memory_type == memory_type,
                Memory.content == content,
            )
        ).first()

    def source_message_exists(self, message_id: str) -> bool:
        return self.session.get(Message, message_id) is not None

    def add(self, memory: Memory) -> Memory:
        self.session.add(memory)
        self.session.flush()
        return memory

    def delete(self, memory: Memory) -> None:
        self.session.delete(memory)

    def list_ranked(
        self,
        character_id: str,
        *,
        memory_type: str | None = None,
        limit: int = 10,
        min_importance: float = 0.0,
        include_forgotten: bool = False,
    ) -> list[Memory]:
        statement = select(Memory).where(Memory.character_id == character_id)
        if not include_forgotten:
            statement = statement.where(Memory.is_forgotten.is_(False))
        if memory_type is not None:
            statement = statement.where(Memory.memory_type == memory_type)
        if min_importance > 0:
            statement = statement.where(Memory.importance >= min_importance)
        statement = statement.order_by(
            col(Memory.importance).desc(), col(Memory.last_accessed).desc()
        ).limit(limit)
        return list(self.session.exec(statement).all())

    def search(self, character_id: str, query: str, *, limit: int) -> list[Memory]:
        return list(self.session.exec(
            select(Memory)
            .where(
                Memory.character_id == character_id,
                Memory.is_forgotten.is_(False),
                col(Memory.content).contains(query),
            )
            .order_by(col(Memory.importance).desc())
            .limit(limit)
        ).all())

    def list_short_term(self, character_id: str, *, limit: int) -> list[Memory]:
        return list(self.session.exec(
            select(Memory)
            .where(
                Memory.character_id == character_id,
                Memory.memory_type == "short_term",
                Memory.is_forgotten.is_(False),
            )
            .order_by(col(Memory.created_at).desc())
            .limit(limit)
        ).all())

    def list_active_unpinned(self, character_id: str) -> list[Memory]:
        return list(self.session.exec(
            select(Memory).where(
                Memory.character_id == character_id,
                Memory.is_forgotten.is_(False),
                Memory.is_pinned.is_(False),
            )
        ).all())

    def list_missing_embeddings(self, character_id: str, *, limit: int) -> list[Memory]:
        return list(self.session.exec(
            select(Memory)
            .where(
                Memory.character_id == character_id,
                Memory.is_forgotten.is_(False),
                col(Memory.embedding).is_(None),
            )
            .limit(limit)
        ).all())

    def list_forgotten_before(self, character_id: str, cutoff) -> list[Memory]:
        return list(self.session.exec(
            select(Memory).where(
                Memory.character_id == character_id,
                Memory.is_forgotten.is_(True),
                Memory.last_accessed < cutoff,
            )
        ).all())

