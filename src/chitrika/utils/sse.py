"""Server-Sent Events helpers for streaming LLM responses."""

from __future__ import annotations

import json


def sse_event(event: str, data: dict) -> str:
    """Format a dict as an SSE event string.

    Returns a string suitable for writing to a StreamingResponse body::

        event: {event}
        data: {json}

    """
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    return f"event: {event}\ndata: {payload}\n\n"


def sse_start(message_id: str, user_message_id: str | None = None) -> str:
    """Emit the 'start' event when streaming begins."""
    payload: dict = {"type": "start", "message_id": message_id}
    if user_message_id:
        payload["user_message_id"] = user_message_id
    return sse_event("message", payload)


def sse_content(content: str) -> str:
    """Emit a content chunk."""
    return sse_event("message", {"type": "content", "content": content})


def sse_done(message_id: str, usage: dict | None = None) -> str:
    """Emit the 'done' event when streaming finishes."""
    payload: dict = {"type": "done", "message_id": message_id}
    if usage:
        payload["usage"] = usage
    return sse_event("message", payload)


def sse_error(
    message: str,
    *,
    code: str = "generation_error",
    details: str = "",
    message_id: str | None = None,
) -> str:
    """Emit a structured, user-safe error event."""
    payload: dict[str, object] = {
        "type": "error",
        "code": code,
        "message": message,
        "details": details,
        "message_id": message_id,
    }
    return sse_event("error", payload)
