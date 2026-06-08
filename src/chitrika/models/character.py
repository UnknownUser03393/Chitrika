"""Character model — identity, personality, and avatar."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlmodel import Field, SQLModel

from src.chitrika.utils.datetime_helpers import utcnow


class Character(SQLModel, table=True):
    """A digital persona with its own identity, prompt, and emotional state."""

    __tablename__ = "characters"

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
    )
    name: str = Field(
        unique=True,
        index=True,
        description="Internal slug / short name, e.g. 'alvia'",
    )
    display_name: str = Field(
        description="Human-readable name, e.g. '徐悦婷'",
    )
    avatar_url: str | None = Field(default=None)
    description: str | None = Field(
        default=None,
        description="Short biographical description",
    )
    provider: str = Field(
        default="deepseek",
        description="LLM provider slug: 'deepseek', 'openai', etc.",
    )
    personality_prompt: str = Field(
        default="",
        description="Full system prompt injected into every LLM call",
    )
    initials: str = Field(
        default="",
        description="Fallback avatar initials, 1-2 chars",
    )
    color: str = Field(
        default="#4FA3E3",
        description="Hex colour used for avatar background",
    )
    enabled: bool = Field(
        default=True,
        description="Whether this character is active",
    )
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
