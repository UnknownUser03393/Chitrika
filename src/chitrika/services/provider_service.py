"""Provider service — resolve provider configs and create LLM clients."""

from __future__ import annotations

import json
import logging

from sqlmodel import Session, select

from src.chitrika.models.provider import LLMProvider

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
    session: Session, provider_name: str
) -> LLMProvider | None:
    """Resolve the provider config for a given provider name string.

    Falls back to the default provider if the named provider is not found.
    """
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


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------


def mask_api_key(key: str) -> str:
    """Mask an API key for display: show first 4 + last 4 chars."""
    if not key:
        return "****"
    if len(key) <= 8:
        if len(key) >= 4:
            return key[:2] + "..." + key[-2:]
        return "****"
    return key[:4] + "..." + key[-4:]


def parse_models_json(models_json: str) -> list[str]:
    """Safely parse the models JSON field."""
    if not models_json:
        return []
    try:
        return json.loads(models_json)
    except (json.JSONDecodeError, TypeError):
        return []


def serialize_models(models: list[str]) -> str:
    """Serialize a model list to JSON string for storage."""
    return json.dumps(models, ensure_ascii=False)
