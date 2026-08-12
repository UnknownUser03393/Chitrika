"""Chitrika LLMProvider implementation over chat.deepseek.com."""

from __future__ import annotations

import hashlib
import json
import logging
import threading
import time
from pathlib import Path
from typing import AsyncIterator, Iterator

from src.chitrika.plugins.api import ProviderContext
from src.llmproviders.LLMProvider import (
    AuthenticationError,
    CompletionRequest,
    CompletionResponse,
    LLMError,
    LLMProvider,
    Message,
    Model,
    StreamChunk,
)

from ds_web import DeepSeekClient
from ds_web.session_store import SessionStore
from ds_web.sse import (
    extract_text,
    iter_sse_payloads,
    normalize_model_name,
    openai_messages_to_prompt,
)

logger = logging.getLogger("chitrika.plugins.deepseek_local")

PLUGIN_DIR = Path(__file__).resolve().parent
DATA_DIR = PLUGIN_DIR / "data"
DEFAULT_AUTH_STATE = DATA_DIR / "auth_state.json"
DEFAULT_SESSION_STORE = DATA_DIR / "session_store.json"
DEFAULT_MODEL = "deepseek-chat"
DEFAULT_LINK_STORE = DATA_DIR / "conversation_links.json"
MAX_CONVERSATION_LINKS = 100
DEFAULT_PLUGIN_CONFIG = DATA_DIR / "config.json"

# Serializes read/write of the conversation-link store. RLock because the
# load/save helpers re-enter the lock from _find_reusable_link / _save_link.
_LINK_LOCK = threading.RLock()

PUBLIC_MODEL_IDS = {
    "default": ["deepseek-chat", "default", "fast"],
    "expert": ["deepseek-reasoner", "expert", "reasoner"],
    "vision": ["vision"],
}


def resolve_auth_state_path(context: ProviderContext) -> Path:
    return _resolve_auth_state_path(context.config or {})


def _resolve_auth_state_path(config: dict) -> Path:
    candidates: list[str] = []
    for key in ("auth_state_path", "auth_state"):
        value = config.get(key)
        if isinstance(value, str) and value.strip():
            candidates.append(value.strip())

    for raw in candidates:
        path = Path(raw).expanduser()
        if path.is_dir():
            path = path / "auth_state.json"
        if path.exists():
            return path

    if DEFAULT_AUTH_STATE.exists():
        return DEFAULT_AUTH_STATE
    if candidates:
        return Path(candidates[0]).expanduser()
    return DEFAULT_AUTH_STATE


def load_plugin_config_values() -> dict[str, str]:
    """Read the plugin-level config file (``data/config.json``), if any.

    These act as defaults that a provider's own ``custom_config`` can override.
    """
    if not DEFAULT_PLUGIN_CONFIG.exists():
        return {}
    try:
        data = json.loads(DEFAULT_PLUGIN_CONFIG.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {str(key): str(value) for key, value in data.items()}


def _as_bool(value, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return default


def _message_to_dict(message) -> dict:
    """Normalize an OpenAI-style message (dict or object) into ``{"role", "content"}``."""
    if isinstance(message, dict):
        role = str(message.get("role", "user"))
        content = message.get("content", "")
    else:
        role = str(getattr(message, "role", "user"))
        content = getattr(message, "content", "")
    if isinstance(content, list):
        content = "\n".join(
            part.get("text", "") for part in content if isinstance(part, dict)
        )
    elif content is None:
        content = ""
    return {"role": role, "content": content}


def _message_key(message: dict) -> str:
    """Content fingerprint for a single message (used as a conversation-link key)."""
    return hashlib.sha1(
        f"{message.get('role', '')}\x00{message.get('content', '')}".encode("utf-8")
    ).hexdigest()


def _extract_response_message_id(event) -> int | None:
    """Best-effort extraction of the web-side message id for the completed turn."""
    from ds_web.sse import extract_response_message_id

    message_id = extract_response_message_id(event)
    if message_id is not None:
        return message_id

    if not isinstance(event, dict):
        return None
    value = event.get("v")
    if isinstance(value, dict):
        response = value.get("response")
        if isinstance(response, dict):
            for key in ("message_id", "id"):
                candidate = response.get(key)
                if isinstance(candidate, int):
                    return candidate
        for key in ("message_id", "id"):
            candidate = value.get(key)
            if isinstance(candidate, int):
                return candidate
    return None


def link_store_status(path: str | Path | None = None) -> dict:
    """Summarize the conversation-link store (used by the operation panel)."""
    store_path = Path(str(path or DEFAULT_LINK_STORE)).expanduser()
    links: dict = {}
    if store_path.exists():
        try:
            data = json.loads(store_path.read_text(encoding="utf-8"))
            links = data.get("links") if isinstance(data, dict) else {}
            if not isinstance(links, dict):
                links = {}
        except (json.JSONDecodeError, OSError):
            links = {}
    return {
        "link_count": len(links),
        "link_store_path": str(store_path),
        "link_store_exists": store_path.exists(),
    }


def clear_link_store(path: str | Path | None = None) -> int:
    """Wipe the conversation-link store, returning the number of links cleared."""
    store_path = Path(str(path or DEFAULT_LINK_STORE)).expanduser()
    with _LINK_LOCK:
        links: dict = {}
        if store_path.exists():
            try:
                data = json.loads(store_path.read_text(encoding="utf-8"))
                links = data.get("links") if isinstance(data, dict) else {}
                if not isinstance(links, dict):
                    links = {}
            except (json.JSONDecodeError, OSError):
                links = {}
        count = len(links)
        store_path.parent.mkdir(parents=True, exist_ok=True)
        store_path.write_text(
            json.dumps({"links": {}}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return count


class DeepSeekWebProvider(LLMProvider):
    """LLMProvider backed by reverse-engineered chat.deepseek.com client."""

    def __init__(self, context: ProviderContext):
        self.context = context

        # Plugin-level config (data/config.json) provides defaults; a provider's
        # own custom_config overrides them per-key.
        config = dict(context.config or {})
        for key, value in load_plugin_config_values().items():
            config.setdefault(key, value)

        self.auth_state_path = _resolve_auth_state_path(config)
        if not self.auth_state_path.exists():
            raise AuthenticationError(
                f"DeepSeek web auth_state not found: {self.auth_state_path}. "
                "Run: python plugins/deepseek_local/login.py"
            )

        self._client = DeepSeekClient(self.auth_state_path)
        status = self._client.get_auth_status()
        if not status.get("ready"):
            raise AuthenticationError(
                f"DeepSeek web auth_state incomplete at {self.auth_state_path}. "
                "Run: python plugins/deepseek_local/login.py"
            )

        self.thinking_enabled = _as_bool(config.get("thinking") or config.get("reasoning"), False)
        self.search_enabled = _as_bool(config.get("search") or config.get("search_enabled"), False)
        self.default_model = (
            str(config.get("default_model") or context.default_model or DEFAULT_MODEL).strip()
            or DEFAULT_MODEL
        )

        store_path = config.get("session_store_path") or str(DEFAULT_SESSION_STORE)
        self._store = SessionStore(Path(str(store_path)).expanduser())

        self._link_store_path = Path(
            str(config.get("conversation_link_store") or DEFAULT_LINK_STORE)
        ).expanduser()

    # ------------------------------------------------------------------
    # Conversation-link store — lets us reuse one web session across turns
    # ------------------------------------------------------------------

    def _load_links(self) -> dict:
        with _LINK_LOCK:
            if not self._link_store_path.exists():
                return {}
            try:
                data = json.loads(self._link_store_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                return {}
            links = data.get("links") if isinstance(data, dict) else None
            return links if isinstance(links, dict) else {}

    def _save_links(self, links: dict) -> None:
        self._link_store_path.parent.mkdir(parents=True, exist_ok=True)
        self._link_store_path.write_text(
            json.dumps({"links": links}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _find_reusable_link(self, conv: list[dict], model_type: str) -> dict | None:
        """Return the stored web session to continue, or ``None`` for a fresh one.

        ``conv`` is the message list with the system prompt stripped. A turn
        can continue a web session only when it looks like
        ``[..., <user>, <assistant>, <user>]`` — the middle user/assistant pair
        must match a session we previously completed. Matching by the *user*
        message before the last one is robust to Chitrika's rolling history
        window (30 messages): that user is always within the window.
        """
        if len(conv) < 3:
            return None
        if conv[-1]["role"] != "user" or conv[-2]["role"] != "assistant":
            return None
        prev_user = conv[-3]
        if prev_user["role"] != "user":
            return None

        key = _message_key(prev_user)
        with _LINK_LOCK:
            link = self._load_links().get(key)
        if not link:
            return None
        if link.get("model_type") != model_type:
            return None
        if not link.get("chat_session_id") or link.get("reply_message_id") is None:
            return None
        return link

    def _save_link(
        self,
        user_message: dict,
        chat_session_id: str,
        reply_message_id: int,
        model_type: str,
    ) -> None:
        """Remember that *user_message* produced the web message *reply_message_id*.

        The next turn that ends with this user message (i.e. appends a new
        question after its assistant reply) can then continue the same web
        session by replying to ``reply_message_id``.
        """
        key = _message_key(user_message)
        with _LINK_LOCK:
            links = self._load_links()
            links[key] = {
                "chat_session_id": chat_session_id,
                "reply_message_id": reply_message_id,
                "model_type": model_type,
                "ts": time.time(),
            }
            if len(links) > MAX_CONVERSATION_LINKS:
                oldest = sorted(links, key=lambda k: links[k].get("ts", 0))
                for stale_key in oldest[: len(links) - MAX_CONVERSATION_LINKS]:
                    links.pop(stale_key, None)
            self._save_links(links)

    def getModels(self) -> list[Model]:
        try:
            available = self._client.get_available_model_types() or [
                self._client.get_default_model_type()
            ]
        except Exception as exc:
            logger.exception("Failed to list DeepSeek web models")
            raise LLMError(f"Failed to list DeepSeek web models: {exc}") from exc

        models: list[Model] = []
        seen: set[str] = set()
        for model_type in available:
            for public_id in PUBLIC_MODEL_IDS.get(model_type, [model_type]):
                if public_id in seen:
                    continue
                seen.add(public_id)
                models.append(
                    Model(
                        name=public_id,
                        displayName=public_id,
                        maxTokens=None,
                        supportsStreaming=True,
                    )
                )
        if not models:
            models.append(Model(name=DEFAULT_MODEL, displayName=DEFAULT_MODEL))
        return models

    def send(self, model: Model, chat: str | CompletionRequest | list[Message]) -> CompletionResponse:
        messages = chat.messages if isinstance(chat, CompletionRequest) else chat
        parts = [chunk.content for chunk in self.stream(model, messages) if chunk.content]
        return CompletionResponse(
            content="".join(parts),
            model=model.name,
            usage={},
            finishReason="stop",
        )

    async def sendAsync(
        self, model: Model, chat: str | CompletionRequest | list[Message]
    ) -> CompletionResponse:
        return self.send(model, chat)

    def stream(self, model: Model, chat: str | list[Message]) -> Iterator[StreamChunk]:
        # Chitrika always sends full history and does not pass a conversation
        # id into ProviderContext. We still reuse the same web session across
        # turns by matching the message history against a persisted link store.
        if isinstance(chat, str):
            messages = [{"role": "user", "content": chat}]
        else:
            messages = [_message_to_dict(m) for m in chat]

        # The system prompt drifts every call (emotions/memories change), so it
        # is excluded from conversation-linking — only the user/assistant turns
        # matter for deciding whether this is a continuation.
        conv = [m for m in messages if m.get("role") != "system"]

        try:
            default_type = self._client.get_default_model_type()
            model_type = normalize_model_name(model.name or self.default_model, default_type)
            available = set(self._client.get_available_model_types() or [])
            if available and model_type not in available:
                model_type = default_type if default_type in available else next(iter(available))

            link = self._find_reusable_link(conv, model_type)
            if link is not None:
                # Same conversation as before — continue the existing web
                # session by appending only the new user message.
                chat_session_id = link["chat_session_id"]
                parent_message_id = link["reply_message_id"]
                prompt = conv[-1]["content"]
            else:
                session_response = self._client.create_session()
                chat_session = session_response["data"]["biz_data"]["chat_session"]
                chat_session_id = chat_session["id"]
                parent_message_id = None
                prompt = (
                    chat if isinstance(chat, str) else openai_messages_to_prompt(messages)
                )

                # Optional local bookkeeping (not required for correctness).
                self._store.create_conversation(
                    model_type=model_type,
                    chat_session_id=chat_session_id,
                    parent_message_id=None,
                    title=chat_session.get("title"),
                    prompt=prompt,
                )

            payload = {
                "chat_session_id": chat_session_id,
                "parent_message_id": parent_message_id,
                "model_type": model_type,
                "prompt": prompt,
                "ref_file_ids": [],
                "thinking_enabled": self.thinking_enabled,
                "search_enabled": self.search_enabled,
                "action": None,
                "preempt": False,
            }
            response = self._client.completion(payload)
        except Exception as exc:
            status = getattr(getattr(exc, "response", None), "status_code", None)
            if status in {401, 403}:
                raise AuthenticationError(
                    f"DeepSeek web auth rejected (HTTP {status}). "
                    f"Re-login: python plugins/deepseek_local/login.py "
                    f"(auth: {self.auth_state_path})"
                ) from exc
            logger.exception("DeepSeek web completion failed")
            raise LLMError(f"DeepSeek web completion failed: {exc}") from exc

        reply_message_id = None
        try:
            for event in iter_sse_payloads(response):
                message_id = _extract_response_message_id(event)
                if message_id is not None:
                    reply_message_id = message_id
                text = extract_text(event)
                if not text:
                    continue
                yield StreamChunk(content=text, finishReason=None, model=model.name)
        finally:
            try:
                response.close()
            except Exception:
                pass

        # Remember that the user message just sent produced *reply_message_id*,
        # so the next turn can continue this web session. Skipped when we never
        # saw a reply id (e.g. an interrupted stream) — the next turn then falls
        # back to a fresh session instead of corrupting the parent chain.
        if reply_message_id is not None and conv:
            self._save_link(
                conv[-1],
                chat_session_id,
                reply_message_id,
                model_type,
            )

        yield StreamChunk(content="", finishReason="stop", model=model.name)

    async def streamAsync(self, model: Model, chat: str | list[Message]) -> AsyncIterator[StreamChunk]:
        for chunk in self.stream(model, chat):
            yield chunk
