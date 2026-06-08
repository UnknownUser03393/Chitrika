"""LLM Provider model — API connection configuration for external LLM services."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlmodel import Field, SQLModel

from src.chitrika.utils.datetime_helpers import utcnow


class LLMProvider(SQLModel, table=True):
    """A configured LLM provider with API key, base URL, and available models."""

    __tablename__ = "llm_providers"

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
    )
    name: str = Field(
        unique=True,
        index=True,
        description="Unique slug, e.g. 'deepseek', 'openai'",
    )
    display_name: str = Field(
        description="Human-readable name, e.g. 'DeepSeek V4'",
    )
    api_key: str = Field(
        default="",
        description="API key for this provider",
    )
    base_url: str = Field(
        default="",
        description="API base URL, e.g. 'https://api.deepseek.com/v1'",
    )
    default_model: str = Field(
        default="",
        description="Default model name (first in the list if not set)",
    )
    models_json: str = Field(
        default="[]",
        description="JSON array of available model name strings",
    )
    is_default: bool = Field(
        default=False,
        description="Whether this provider is used as the fallback default",
    )
    enabled: bool = Field(default=True)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
