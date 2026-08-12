"""SSE parsing helpers for chat.deepseek.com completion streams."""

from __future__ import annotations

import json
from typing import Any, Iterator

from .client import normalize_model_type

MODEL_ALIASES = {
    "deepseek-chat": "default",
    "gpt-4o-mini": "default",
    "gpt-4o": "default",
    "default": "default",
    "fast": "default",
    "expert": "expert",
    "deepseek-reasoner": "expert",
    "reasoner": "expert",
    "vision": "vision",
}


def normalize_model_name(model: str | None, default_model_type: str = "default") -> str:
    return normalize_model_type(
        MODEL_ALIASES.get(model or "", model or default_model_type),
        default_model_type=default_model_type,
    )


def openai_messages_to_prompt(messages: list[Any]) -> str:
    if not isinstance(messages, list) or not messages:
        raise ValueError("messages must be a non-empty list")

    parts: list[str] = []
    for message in messages:
        if not isinstance(message, dict):
            role = str(getattr(message, "role", "user")).strip().lower() or "user"
            content = getattr(message, "content", "")
        else:
            role = str(message.get("role", "user")).strip().lower() or "user"
            content = message.get("content", "")

        if isinstance(content, list):
            text_parts: list[str] = []
            for item in content:
                if not isinstance(item, dict):
                    continue
                if item.get("type") == "text":
                    text = item.get("text")
                    if isinstance(text, str) and text:
                        text_parts.append(text)
            content = "\n".join(text_parts)
        elif content is None:
            content = ""
        elif not isinstance(content, str):
            content = json.dumps(content, ensure_ascii=False)

        parts.append(f"{role}: {content}".rstrip())

    return "\n\n".join(parts)


def iter_sse_payloads(response) -> Iterator[dict[str, Any]]:
    event_type = None
    for line in response.iter_lines(decode_unicode=True):
        if not line:
            event_type = None
            continue

        if line.startswith("event:"):
            event_type = line[6:].strip() or None
            continue

        if not line.startswith("data:"):
            yield {"type": event_type or "raw", "raw": line}
            continue

        data = line[5:].strip()
        if not data or data == "[DONE]":
            continue

        try:
            payload = json.loads(data)
            if isinstance(payload, dict) and "type" not in payload:
                payload["type"] = event_type or "message"
            yield payload
        except json.JSONDecodeError:
            yield {"type": event_type or "raw", "raw": data}


def extract_text(event: dict[str, Any] | Any) -> str | None:
    if not isinstance(event, dict):
        return None

    event_type = event.get("type")
    if event_type in {"title", "close", "update_session", "ready", "raw"}:
        return None

    if event.get("o") == "APPEND" and event.get("p") == "response/fragments/-1/content":
        value = event.get("v")
        if isinstance(value, str) and value:
            return value

    response_container = event.get("v")
    response = response_container.get("response") if isinstance(response_container, dict) else None
    if isinstance(response, dict):
        fragments = response.get("fragments")
        if isinstance(fragments, list):
            parts: list[str] = []
            for fragment in fragments:
                if not isinstance(fragment, dict):
                    continue
                content = fragment.get("content")
                if isinstance(content, str) and content:
                    parts.append(content)
            if parts:
                return "".join(parts)

    direct_value = event.get("v")
    if isinstance(direct_value, str) and direct_value:
        if direct_value in {"FINISHED", "WIP"}:
            return None
        return direct_value

    for key in ("content", "text", "message"):
        value = event.get(key)
        if isinstance(value, str) and value:
            return value

    delta = event.get("delta")
    if isinstance(delta, dict):
        for key in ("content", "text", "reasoning_content"):
            value = delta.get(key)
            if isinstance(value, str) and value:
                return value

    choices = event.get("choices")
    if isinstance(choices, list):
        for choice in choices:
            if not isinstance(choice, dict):
                continue
            delta = choice.get("delta")
            if isinstance(delta, dict):
                for key in ("content", "text", "reasoning_content"):
                    value = delta.get(key)
                    if isinstance(value, str) and value:
                        return value
            message = choice.get("message")
            if isinstance(message, dict):
                for key in ("content", "text"):
                    value = message.get(key)
                    if isinstance(value, str) and value:
                        return value

    data = event.get("data")
    if isinstance(data, dict):
        return extract_text(data)
    return None


def extract_response_message_id(event: dict[str, Any] | Any) -> int | None:
    if not isinstance(event, dict):
        return None
    response_message_id = event.get("response_message_id")
    if isinstance(response_message_id, int):
        return response_message_id
    response = event.get("v")
    if isinstance(response, dict):
        message = response.get("response")
        if isinstance(message, dict):
            mid = message.get("message_id")
            if isinstance(mid, int):
                return mid
    return None
