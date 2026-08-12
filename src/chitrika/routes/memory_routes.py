"""Memory API routes — inspect, search, and manage character memories."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from src.chitrika.database import get_session, get_transactional_session
from src.chitrika.models.memory import Memory
from src.chitrika.repositories.memory_repository import MemoryRepository
from src.chitrika.services.memory_lifecycle_service import MemoryLifecycleService
from src.chitrika.services.memory_retrieval_service import MemoryRetrievalService
from src.chitrika.schemas.memory_schemas import (
    MemoryCreate,
    MemoryListResponse,
    MemoryResponse,
    MemoryUpdate,
)

router = APIRouter(tags=["memory"])


# ---------------------------------------------------------------------------
# GET  /api/characters/{character_id}/memories
# ---------------------------------------------------------------------------

@router.get(
    "/characters/{character_id}/memories",
    response_model=MemoryListResponse,
)
def list_memories(
    character_id: str,
    memory_type: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    min_importance: float = Query(default=0.0, ge=0.0, le=1.0),
    include_forgotten: bool = Query(default=False),
    session: Session = Depends(get_session),
) -> dict:
    """List memories for a character, ordered by importance."""
    service = MemoryRetrievalService(MemoryRepository(session))
    memories = service.get_relevant(
        character_id,
        memory_type=memory_type,
        limit=limit,
        min_importance=min_importance,
        include_forgotten=include_forgotten,
    )
    return {
        "memories": [MemoryResponse.model_validate(m) for m in memories],
        "total": len(memories),
    }


# ---------------------------------------------------------------------------
# GET  /api/characters/{character_id}/memories/search
# ---------------------------------------------------------------------------

@router.get(
    "/characters/{character_id}/memories/search",
    response_model=MemoryListResponse,
)
def search_memories(
    character_id: str,
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(default=20, ge=1, le=100),
    session: Session = Depends(get_session),
) -> dict:
    """Full-text search across memory content."""
    service = MemoryRetrievalService(MemoryRepository(session))
    memories = service.search(character_id, q, limit=limit)
    return {
        "memories": [MemoryResponse.model_validate(m) for m in memories],
        "total": len(memories),
    }


# ---------------------------------------------------------------------------
# POST /api/characters/{character_id}/memories
# ---------------------------------------------------------------------------

@router.post(
    "/characters/{character_id}/memories",
    response_model=MemoryResponse,
    status_code=201,
)
def create_memory(
    character_id: str,
    body: MemoryCreate,
    session: Session = Depends(get_transactional_session),
) -> Memory:
    """Manually create a memory for a character."""
    service = MemoryLifecycleService(MemoryRepository(session))
    return service.store(
        character_id=character_id,
        memory_type=body.memory_type,
        content=body.content,
        importance=body.importance,
        emotional_valence=body.emotional_valence,
        is_pinned=body.is_pinned,
    )


# ---------------------------------------------------------------------------
# PATCH  /api/memories/{memory_id}
# ---------------------------------------------------------------------------

@router.patch(
    "/memories/{memory_id}",
    response_model=MemoryResponse,
)
def update_memory(
    memory_id: str,
    body: MemoryUpdate,
    session: Session = Depends(get_transactional_session),
) -> Memory:
    """Update a memory: pin, change importance, edit content, or forget."""
    service = MemoryLifecycleService(MemoryRepository(session))
    updated = service.update(
        memory_id,
        content=body.content,
        importance=body.importance,
        is_pinned=body.is_pinned,
        is_forgotten=body.is_forgotten,
    )
    if updated is None:
        raise HTTPException(status_code=404, detail="Memory not found")
    return updated


# ---------------------------------------------------------------------------
# DELETE /api/memories/{memory_id}
# ---------------------------------------------------------------------------

@router.delete("/memories/{memory_id}", status_code=204)
def delete_memory(
    memory_id: str,
    session: Session = Depends(get_transactional_session),
) -> None:
    """Permanently delete a memory.

    Soft-forgetting is handled through PATCH /api/memories/{id} with
    {"is_forgotten": true}; this endpoint is intentionally destructive.
    """
    repository = MemoryRepository(session)
    memory = repository.get(memory_id)
    if memory is None:
        raise HTTPException(status_code=404, detail="Memory not found")
    repository.delete(memory)
    session.flush()
