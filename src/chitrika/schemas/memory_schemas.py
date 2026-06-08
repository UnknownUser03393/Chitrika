"""Pydantic schemas for memory API requests and responses."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class MemoryCreate(BaseModel):
    """Request body for creating a memory manually."""

    memory_type: str = Field(
        default="long_term",
        description="One of: 'short_term', 'long_term', 'episodic'",
    )
    content: str = Field(..., min_length=1, description="The memory text")
    importance: float = Field(default=0.3, ge=0.0, le=1.0)
    emotional_valence: float | None = Field(default=None, ge=-1.0, le=1.0)
    is_pinned: bool = False


class MemoryUpdate(BaseModel):
    """Request body for updating a memory."""

    content: str | None = None
    importance: float | None = Field(default=None, ge=0.0, le=1.0)
    is_pinned: bool | None = None
    is_forgotten: bool | None = None


class MemoryResponse(BaseModel):
    """A single memory returned to the client."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    character_id: str
    memory_type: str
    content: str
    importance: float
    emotional_valence: float | None
    is_pinned: bool
    is_forgotten: bool
    created_at: datetime
    last_accessed: datetime
    access_count: int


class MemoryListResponse(BaseModel):
    """Paginated list of memories."""

    memories: list[MemoryResponse]
    total: int
