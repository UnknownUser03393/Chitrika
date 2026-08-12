"""Provider service — resolve provider configs and create LLM clients."""

from __future__ import annotations

import logging
from dataclasses import asdict
from typing import Any

from sqlmodel import Session, select

from src.chitrika.models.provider import LLMProvider, LLMProviderModel
from src.chitrika.plugins.api import ProviderContext, ProviderSpec
from src.chitrika.repositories.plugin_state_repository import PluginStateRepository
from src.chitrika.services.plugin_runtime import (
    PluginError,
    PluginInvoker,
    get_plugin_registry,
)

logger = logging.getLogger("chitrika.providers")


# ---------------------------------------------------------------------------
# Resolution helpers
# ---------------------------------------------------------------------------


def get_provider_by_name(session: Session, name: str) -> LLMProvider | None:
    """Look up an enabled provider by its slug name."""
    return session.exec(
        select(LLMProvider).where(
            LLMProvider.name == name,
            LLMProvider.enabled.is_(True),
        )
    ).first()


def get_provider_by_id(session: Session, provider_id: str) -> LLMProvider | None:
    """Look up a provider by its UUID."""
    return session.exec(
        select(LLMProvider).where(LLMProvider.id == provider_id)
    ).first()


def get_default_provider(session: Session) -> LLMProvider | None:
    """Return the first enabled provider marked as default.

    Falls back to the first enabled provider if no default is set.
    """
    provider = session.exec(
        select(LLMProvider).where(
            LLMProvider.is_default.is_(True),
            LLMProvider.enabled.is_(True),
        )
    ).first()
    if provider is not None:
        return provider
    # Fallback: first enabled provider
    return session.exec(
        select(LLMProvider).where(LLMProvider.enabled.is_(True))
    ).first()


def resolve_provider_for_character(
    session: Session, provider_name: str | None = None, provider_id: str | None = None
) -> LLMProvider | None:
    """Resolve the provider config for a character.

    Prefer a direct provider id. Fall back to a provider slug, then default.
    """
    if provider_id:
        provider = get_provider_by_id(session, provider_id)
        if provider is not None and provider.enabled:
            return provider

    if provider_name:
        provider = get_provider_by_name(session, provider_name)
        if provider is not None:
            return provider
        logger.warning("Provider '%s' not found, falling back to default", provider_name)

    return get_default_provider(session)


# ---------------------------------------------------------------------------
# LLM client factory
# ---------------------------------------------------------------------------


def list_provider_types(session: Session) -> list[dict]:
    """Return built-in and plugin-backed provider types for the settings UI.

    Each plugin-backed entry also carries the plugin's declared operation-panel
    API (``plugin_api``) when the plugin is enabled and exposes one.
    """
    from src.chitrika.schemas.provider_schemas import (
        PluginAPIResponse,
        PluginEndpointResponse,
    )

    builtins = [
        ProviderSpec(
            type="openai",
            label="OpenAI-Compatible",
            plugin_id=None,
            needs_api_key=True,
            needs_base_url=True,
            supports_model_fetch=True,
        )
    ]
    invoker = PluginInvoker(PluginStateRepository(session), get_plugin_registry())
    plugin_specs = invoker.list_provider_specs()

    results: list[dict] = []
    for spec in [*builtins, *plugin_specs]:
        data = asdict(spec)
        plugin_api = None
        if spec.plugin_id:
            api = invoker.get_api(spec.plugin_id)
            if api is not None:
                plugin_api = PluginAPIResponse(
                    endpoints=[
                        PluginEndpointResponse(**asdict(endpoint))
                        for endpoint in api.endpoints
                    ]
                )
        data["plugin_api"] = plugin_api
        results.append(data)
    return results


def create_llm_client(session: Session, provider: LLMProvider):
    """Create an LLM client for either a built-in or plugin-backed provider."""
    if provider.provider_type == "openai":
        return _create_openai_client(provider)

    if not provider.plugin_id:
        logger.error(
            "Provider '%s' uses '%s' but has no plugin_id",
            provider.name,
            provider.provider_type,
        )
        return None

    try:
        spec = _get_plugin_provider_spec(session, provider)
        context = _build_plugin_provider_context(provider)
        if spec is not None and spec.needs_api_key and not context.api_key:
            return None

        factory = PluginInvoker(
            PluginStateRepository(session), get_plugin_registry()
        ).get_provider_factory(
            provider.plugin_id,
            provider.provider_type,
        )
        return factory(context)
    except PluginError:
        logger.exception("Failed to create plugin-backed LLM client")
        return None
    except Exception as exc:
        # Let auth / config errors surface in chat instead of silent echo mode.
        from src.llmproviders.LLMProvider import AuthenticationError, LLMError

        if isinstance(exc, (AuthenticationError, LLMError)):
            raise
        logger.exception("Provider plugin factory crashed")
        return None


def _create_openai_client(provider: LLMProvider):
    if not provider.api_key:
        return None
    try:
        from src.llmproviders.OpenAIProvider import OpenAIClient

        return OpenAIClient(apiKey=provider.api_key, baseUrl=provider.base_url)
    except Exception:
        logger.exception("Failed to create LLM client")
        return None


def _build_plugin_provider_context(provider: LLMProvider) -> ProviderContext:
    config = dict(provider.custom_config or {})
    api_key = _resolve_provider_config_value(config, "api_key", provider.api_key)
    base_url = _resolve_provider_config_value(config, "base_url", provider.base_url)
    default_model = _resolve_provider_config_value(
        config,
        "default_model",
        provider.default_model,
    )

    normalized_config: dict[str, Any] = dict(config)
    if api_key:
        normalized_config["api_key"] = api_key
    if base_url:
        normalized_config["base_url"] = base_url
    if default_model:
        normalized_config["default_model"] = default_model

    return ProviderContext(
        provider_id=provider.id,
        provider_name=provider.name,
        display_name=provider.display_name,
        api_key=api_key,
        base_url=base_url,
        default_model=default_model,
        plugin_id=provider.plugin_id,
        settings={},
        config=normalized_config,
    )



def _resolve_provider_config_value(
    config: dict[str, Any],
    key: str,
    fallback: str,
) -> str:
    value = config.get(key)
    if isinstance(value, str):
        stripped = value.strip()
        if stripped:
            return stripped
    return fallback.strip()



def _get_plugin_provider_spec(
    session: Session,
    provider: LLMProvider,
) -> ProviderSpec | None:
    invoker = PluginInvoker(PluginStateRepository(session), get_plugin_registry())
    for spec in invoker.list_provider_specs():
        if spec.plugin_id == provider.plugin_id and spec.type == provider.provider_type:
            return spec
    return None


def provider_model_names(provider: LLMProvider) -> list[str]:
    """Return the enabled model names configured for a provider."""
    return provider.model_names


def replace_provider_models(
    session: Session,
    provider: LLMProvider,
    models: list[str],
) -> None:
    """Replace a provider's stored model catalog."""
    existing = session.exec(
        select(LLMProviderModel).where(LLMProviderModel.provider_id == provider.id)
    ).all()
    for model in existing:
        session.delete(model)

    seen: set[str] = set()
    for name in models:
        model_name = name.strip()
        if not model_name or model_name in seen:
            continue
        seen.add(model_name)
        session.add(
            LLMProviderModel(
                provider_id=provider.id,
                name=model_name,
                display_name=model_name,
            )
        )
