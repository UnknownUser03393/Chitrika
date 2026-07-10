"""Provider service — resolve provider configs and create LLM clients."""

from __future__ import annotations

import logging

from sqlmodel import Session, select

from src.chitrika.models.provider import LLMProvider, LLMProviderModel

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


def create_llm_client(api_key: str, base_url: str):
    """Create an OpenAIClient from provider config.

    Returns None if the API key is empty.
    """
    if not api_key:
        return None
    try:
        from src.llmproviders.OpenAIProvider import OpenAIClient

        return OpenAIClient(apiKey=api_key, baseUrl=base_url)
    except Exception:
        logger.exception("Failed to create LLM client")
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
