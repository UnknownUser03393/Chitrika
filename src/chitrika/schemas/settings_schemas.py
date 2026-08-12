"""Pydantic schemas for the settings API."""

from __future__ import annotations

from pydantic import BaseModel, Field


class AppSettings(BaseModel):
    """Application runtime settings (DB-backed; not bootstrap)."""

    heartbeat_interval_minutes: int = Field(
        default=5, ge=1, le=1440,
        description="Minutes between heartbeat ticks",
    )
    emotion_decay_rate: float = Field(
        default=0.15, ge=0.0, le=1.0,
        description="Rate at which emotions drift toward zero per tick",
    )
    loneliness_threshold: float = Field(
        default=0.6, ge=0.0, le=1.0,
        description="Loneliness score that triggers proactive messaging",
    )
    memory_llm_extraction: bool = Field(
        default=False,
        description="Use the LLM to extract durable user facts (costs tokens per message)",
    )
    memory_episodic_summary: bool = Field(
        default=False,
        description="Compress short-term chatter into episodic narrative memories (costs tokens)",
    )


class AppSettingsUpdate(BaseModel):
    """Partial update — every field is optional."""

    heartbeat_interval_minutes: int | None = Field(
        default=None, ge=1, le=1440,
    )
    emotion_decay_rate: float | None = Field(
        default=None, ge=0.0, le=1.0,
    )
    loneliness_threshold: float | None = Field(
        default=None, ge=0.0, le=1.0,
    )
    memory_llm_extraction: bool | None = Field(default=None)
    memory_episodic_summary: bool | None = Field(default=None)
