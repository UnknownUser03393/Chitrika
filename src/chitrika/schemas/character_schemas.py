"""Pydantic schemas for character API requests and responses."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CharacterCreate(BaseModel):
    """Request body for creating a new character."""

    name: str = Field(..., min_length=1, max_length=64, description="Internal slug")
    display_name: str = Field(..., min_length=1, max_length=128)
    description: str | None = None
    provider: str = Field(default="deepseek", description="LLM provider: 'deepseek', 'openai'")
    personality_prompt: str = Field(default="", description="Full system prompt")
    initials: str = Field(default="", max_length=2)
    color: str = Field(default="#4FA3E3", description="Hex colour")
    avatar_url: str | None = None
    enabled: bool = True


class CharacterUpdate(BaseModel):
    """Request body for updating an existing character."""

    display_name: str | None = None
    description: str | None = None
    provider: str | None = None
    personality_prompt: str | None = None
    initials: str | None = None
    color: str | None = None
    avatar_url: str | None = None
    enabled: bool | None = None


class CharacterResponse(BaseModel):
    """A character returned to the client."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    display_name: str
    description: str | None
    provider: str = "deepseek"
    initials: str
    color: str
    avatar_url: str | None
    enabled: bool
    created_at: datetime
    updated_at: datetime


class CharacterListResponse(BaseModel):
    """List of characters."""

    characters: list[CharacterResponse]
