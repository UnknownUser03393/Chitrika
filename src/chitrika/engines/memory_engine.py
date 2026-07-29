"""Memory Engine — store, retrieve, decay, and prune character memories.

Memories come in three types:
- short_term:  raw recent messages (capped at 50)
- long_term:   extracted facts about the user / relationship
- episodic:    narrative summaries of past interactions

Importance decays over time unless the memory is pinned or frequently accessed.
"""

from __future__ import annotations

import logging
from datetime import timedelta

from sqlmodel import Session, col, select

from src.chitrika.models.memory import Memory
from src.chitrika.utils.datetime_helpers import days_between, utcnow

logger = logging.getLogger("chitrika.memory")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SHORT_TERM_LIMIT = 50  # max short-term memories per character
DECAY_THRESHOLD = 0.15  # importance below this → mark forgotten
ACCESS_DECAY_DAYS = 30  # not accessed in 30 days → aggressive decay


class MemoryEngine:
    """Manages the lifecycle of character memories."""

    def __init__(self, session: Session):
        self._session = session

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

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
        """Persist a new memory.

        If *importance* is None it is computed automatically from
        *emotional_valence* and *is_pinned*.
        """
        content = content.strip()
        if not content:
            raise ValueError("Memory content cannot be empty")

        # Facts extracted repeatedly from normal conversation should reinforce a
        # memory instead of filling the database with identical rows.
        if memory_type in {"long_term", "episodic"}:
            existing = self._session.exec(
                select(Memory).where(
                    Memory.character_id == character_id,
                    Memory.memory_type == memory_type,
                    Memory.content == content,
                )
            ).first()
            if existing is not None:
                existing.is_forgotten = False
                existing.last_accessed = utcnow()
                existing.access_count += 1
                existing.importance = min(
                    1.0,
                    max(existing.importance, importance or 0.0) + 0.05,
                )
                if is_pinned:
                    existing.is_pinned = True
                self._session.commit()
                self._session.refresh(existing)
                return existing

        if importance is None:
            importance = self._compute_importance(
                emotional_valence=emotional_valence,
                is_pinned=is_pinned,
            )

        memory = Memory(
            character_id=character_id,
            memory_type=memory_type,
            content=content,
            importance=importance,
            emotional_valence=emotional_valence,
            source_message_id=source_message_id,
            is_pinned=is_pinned,
        )
        self._session.add(memory)

        # Enforce short-term cap
        if memory_type == "short_term":
            self._trim_short_term(character_id)

        self._session.commit()
        self._session.refresh(memory)
        return memory

    # ------------------------------------------------------------------
    # Retrieve
    # ------------------------------------------------------------------

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
        """Return the most important active memories for *character_id*.

        Results are ordered by importance DESC, then last_accessed DESC.
        """
        stmt = select(Memory).where(Memory.character_id == character_id)

        if not include_forgotten:
            stmt = stmt.where(Memory.is_forgotten.is_(False))
        if memory_type is not None:
            stmt = stmt.where(Memory.memory_type == memory_type)
        if min_importance > 0:
            stmt = stmt.where(Memory.importance >= min_importance)

        stmt = stmt.order_by(col(Memory.importance).desc(), col(Memory.last_accessed).desc())
        stmt = stmt.limit(limit)

        memories = list(self._session.exec(stmt).all())
        if track_access and memories:
            now = utcnow()
            for memory in memories:
                memory.access_count += 1
                memory.last_accessed = now
            self._session.commit()
        return memories

    def get_by_id(self, memory_id: str) -> Memory | None:
        """Fetch a single memory by ID."""
        return self._session.exec(
            select(Memory).where(Memory.id == memory_id)
        ).first()

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search(
        self,
        character_id: str,
        query: str,
        *,
        limit: int = 20,
    ) -> list[Memory]:
        """Full-text search across memory content (LIKE-based for SQLite)."""
        stmt = (
            select(Memory)
            .where(
                Memory.character_id == character_id,
                Memory.is_forgotten.is_(False),
                col(Memory.content).contains(query),
            )
            .order_by(col(Memory.importance).desc())
            .limit(limit)
        )
        return list(self._session.exec(stmt).all())

    # ------------------------------------------------------------------
    # Access tracking
    # ------------------------------------------------------------------

    def access(self, memory_id: str) -> None:
        """Record that a memory was accessed (increments counter, updates timestamp)."""
        memory = self.get_by_id(memory_id)
        if memory is not None:
            memory.access_count += 1
            memory.last_accessed = utcnow()
            self._session.commit()

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def update(
        self,
        memory_id: str,
        *,
        content: str | None = None,
        importance: float | None = None,
        is_pinned: bool | None = None,
        is_forgotten: bool | None = None,
    ) -> Memory | None:
        """Update fields on an existing memory."""
        memory = self.get_by_id(memory_id)
        if memory is None:
            return None

        if content is not None:
            memory.content = content
        if importance is not None:
            memory.importance = importance
        if is_pinned is not None:
            memory.is_pinned = is_pinned
        if is_forgotten is not None:
            memory.is_forgotten = is_forgotten

        self._session.commit()
        self._session.refresh(memory)
        return memory

    # ------------------------------------------------------------------
    # Decay
    # ------------------------------------------------------------------

    def decay_importance(self, character_id: str) -> int:
        """Reduce importance of unaccessed, unpinned memories.

        Returns the number of memories that were marked forgotten.
        """
        memories = self._session.exec(
            select(Memory).where(
                Memory.character_id == character_id,
                Memory.is_forgotten.is_(False),
                Memory.is_pinned.is_(False),
            )
        ).all()

        now = utcnow()
        forgotten_count = 0

        for mem in memories:
            days_since_access = days_between(now, mem.last_accessed)

            if days_since_access < 7:
                continue  # no decay
            elif days_since_access < ACCESS_DECAY_DAYS:
                mem.importance *= 0.95
            else:
                mem.importance *= 0.80

            if mem.importance < DECAY_THRESHOLD:
                mem.is_forgotten = True
                forgotten_count += 1

        if forgotten_count:
            self._session.commit()
            logger.info(
                "Decayed memories for %s: %d forgotten",
                character_id,
                forgotten_count,
            )
        else:
            self._session.commit()

        return forgotten_count

    def prune_forgotten(self, character_id: str) -> int:
        """Permanently delete forgotten memories that haven't been
        accessed in more than 7 days.
        """
        cutoff = utcnow() - timedelta(days=7)
        stmt = select(Memory).where(
            Memory.character_id == character_id,
            Memory.is_forgotten.is_(True),
            Memory.last_accessed < cutoff,
        )
        to_delete = list(self._session.exec(stmt).all())

        for mem in to_delete:
            self._session.delete(mem)
        self._session.commit()

        if to_delete:
            logger.info("Pruned %d memories for %s", len(to_delete), character_id)
        return len(to_delete)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_importance(
        *,
        emotional_valence: float | None = None,
        repetition_count: int = 0,
        is_pinned: bool = False,
    ) -> float:
        """Score importance [0, 1] from available signals."""
        base = abs(emotional_valence) if emotional_valence is not None else 0.3
        repetition_bonus = min(repetition_count * 0.05, 0.3)
        pinned_bonus = 0.5 if is_pinned else 0.0
        return min(1.0, max(0.0, base + repetition_bonus + pinned_bonus))

    def _trim_short_term(self, character_id: str) -> None:
        """Remove the oldest short-term memories if over the limit."""
        stmt = (
            select(Memory)
            .where(
                Memory.character_id == character_id,
                Memory.memory_type == "short_term",
                Memory.is_forgotten.is_(False),
            )
            .order_by(col(Memory.created_at).asc())
        )
        all_short = list(self._session.exec(stmt).all())

        excess = len(all_short) - SHORT_TERM_LIMIT
        for mem in all_short[:excess]:
            mem.is_forgotten = True
