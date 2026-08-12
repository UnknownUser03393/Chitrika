"""Pydantic schemas for debug action API."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


DebugActionName = Literal["loneliness_proactive_message"]


class DebugActionRequest(BaseModel):
    """Request body for forcing a debug action."""

    character_id: str = Field(..., description="Character to act on")
    conversation_id: str | None = Field(
        default=None,
        description="Optional target conversation; latest conversation is used when omitted",
    )
    deliver_now: bool = Field(
        default=True,
        description="Immediately deliver due scheduled messages after queueing the action",
    )
    content: str | None = Field(
        default=None,
        description="Optional message content override for proactive message actions",
    )
    use_llm: bool = Field(
        default=False,
        description="When true, ask the LLM to generate a context-aware message (falls back to content or fallback on failure)",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Reserved for action-specific debug options",
    )


class DebugActionResponse(BaseModel):
    """Result returned by a forced debug action."""

    action: str
    status: str
    character_id: str
    conversation_id: str | None = None
    scheduled_message_id: str | None = None
    delivered_message_id: str | None = None
    delivered: bool = False
    details: dict[str, Any] = Field(default_factory=dict)
