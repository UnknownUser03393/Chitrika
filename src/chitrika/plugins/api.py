"""Stable, dependency-light objects passed to plugin hooks."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Literal, Protocol


@dataclass(frozen=True, slots=True)
class PromptContext:
    """Context supplied to ``on_system_prompt``.

    Plugins should return the new system prompt, or ``None`` to leave the
    current prompt unchanged. Hooks run in deterministic plugin-id order.
    """

    character_id: str
    conversation_id: str
    user_content: str
    system_prompt: str


@dataclass(frozen=True, slots=True)
class CustomProviderOption:
    """A selectable option for a custom provider field."""

    value: str
    label: str


@dataclass(frozen=True, slots=True)
class CustomProviderField:
    """Schema for one plugin-defined provider config field."""

    key: str
    label: str
    input_type: Literal["text", "password", "select"] = "text"
    required: bool = False
    secret: bool = False
    default: str = ""
    placeholder: str = ""
    help_text: str = ""
    options: tuple[CustomProviderOption, ...] = ()
    summary: bool = False


@dataclass(frozen=True, slots=True)
class CustomProviderAPI:
    """Plugin-defined config schema exposed to the settings UI."""

    fields: tuple[CustomProviderField, ...] = ()
    supports_model_fetch: bool = False
    model_field_key: str | None = None


@dataclass(frozen=True, slots=True)
class ProviderContext:
    """Context supplied to provider plugins when creating an LLM client."""

    provider_id: str
    provider_name: str
    display_name: str
    api_key: str
    base_url: str
    default_model: str
    plugin_id: str | None
    settings: dict[str, str]
    config: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ProviderSpec:
    """Provider capability metadata exposed to the app settings UI."""

    type: str
    label: str
    plugin_id: str | None = None
    needs_api_key: bool = True
    needs_base_url: bool = True
    default_base_url: str = ""
    default_model: str = ""
    supports_model_fetch: bool = True
    custom_provider_api: CustomProviderAPI | None = None


@dataclass(frozen=True, slots=True)
class PluginEndpoint:
    """One HTTP endpoint a plugin exposes to the operation panel.

    ``path`` is relative to ``/api/plugins/{plugin_id}/api`` — e.g. ``/status``
    resolves to ``GET /api/plugins/{plugin_id}/api/status``.
    """

    method: Literal["GET", "POST", "PATCH", "DELETE"]
    path: str
    summary: str = ""
    description: str = ""


@dataclass(frozen=True, slots=True)
class PluginAPI:
    """Plugin-declared HTTP API surfaced to the frontend operation panel.

    ``handlers`` keys use the ``"{METHOD} {path}"`` form (e.g. ``"GET /status"``).
    Each handler receives ``(query: dict, body: dict)`` and returns a JSON-serializable dict.
    """

    endpoints: tuple[PluginEndpoint, ...] = ()
    handlers: dict[str, Callable[[dict, dict], dict]] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class PluginAction:
    """An action button the plugin config form can trigger.

    ``path`` references a Plugin OpenAPI endpoint relative to
    ``/api/plugins/{plugin_id}/api`` (e.g. ``/status``, ``/sessions/clear``).
    """

    key: str
    label: str
    method: Literal["GET", "POST", "PATCH", "DELETE"] = "POST"
    path: str = ""
    confirm: bool = False


@dataclass(frozen=True, slots=True)
class PluginConfig:
    """Plugin-declared config schema for the settings UI.

    ``fields`` mirror provider custom fields (rendered as a form). ``actions``
    are buttons that invoke Plugin OpenAPI endpoints. ``values_path`` is the
    JSON file (relative to the plugin directory) holding the persisted values;
    an empty string means the plugin does not use persisted config values.
    """

    fields: tuple[CustomProviderField, ...] = ()
    actions: tuple[PluginAction, ...] = ()
    values_path: str = ""


class ProviderFactory(Protocol):
    """Factory returned by plugins to create LLMProvider-compatible clients."""

    def __call__(self, context: ProviderContext): ...
