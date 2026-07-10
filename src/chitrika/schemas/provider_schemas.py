"""Pydantic schemas for LLM provider API requests and responses."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class LLMProviderCreate(BaseModel):
    """Request body for creating a new LLM provider."""

    name: str = Field(..., min_length=1, max_length=64, description="Unique slug")
    display_name: str = Field(..., min_length=1, max_length=128)
    api_key: str = Field(..., description="API key (plaintext in request)")
    base_url: str = Field(..., description="API base URL")
    default_model: str = Field(default="")
    models: list[str] = Field(default_factory=list, description="Available model names")
    is_default: bool = False


class LLMProviderUpdate(BaseModel):
    """Request body for updating an existing LLM provider.
    Only the fields provided will be updated."""

    display_name: str | None = None
    api_key: str | None = Field(
        default=None,
        description="New API key. Send a non-empty value to update; empty string = no change.",
    )
    base_url: str | None = None
    default_model: str | None = None
    models: list[str] | None = None
    is_default: bool | None = None
    enabled: bool | None = None


class LLMProviderResponse(BaseModel):
    """A provider returned to the local client."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    display_name: str
    api_key: str
    base_url: str
    default_model: str
    models: list[str]
    is_default: bool
    enabled: bool
    created_at: datetime
    updated_at: datetime
