"""LLM Provider API routes — CRUD for LLM connection configurations."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from src.chitrika.database import get_session, get_transactional_session
from src.chitrika.models.provider import LLMProvider
from src.chitrika.schemas.provider_schemas import (
    LLMProviderCreate,
    LLMProviderResponse,
    LLMProviderUpdate,
    ProviderTypeResponse,
)
from src.chitrika.services.provider_service import (
    provider_model_names,
    get_provider_by_id,
    replace_provider_models,
    create_llm_client,
    list_provider_types,
)
from src.chitrika.utils.datetime_helpers import utcnow

logger = logging.getLogger("chitrika.routes.providers")

router = APIRouter(tags=["providers"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _model_to_response(p: LLMProvider) -> dict:
    """Convert a DB provider to the API response shape.

    Chitrika is a local desktop app, so the settings UI intentionally receives
    the plaintext key to make provider debugging less painful.
    """
    return {
        "id": p.id,
        "name": p.name,
        "display_name": p.display_name,
        "provider_type": p.provider_type,
        "plugin_id": p.plugin_id,
        "api_key": p.api_key,
        "base_url": p.base_url,
        "default_model": p.default_model,
        "custom_config": p.custom_config,
        "models": provider_model_names(p),
        "is_default": p.is_default,
        "enabled": p.enabled,
        "created_at": p.created_at,
        "updated_at": p.updated_at,
    }


def _unset_default(session: Session, exclude_id: str | None = None) -> None:
    """Clear the is_default flag on all providers (optionally excluding one)."""
    stmt = select(LLMProvider).where(LLMProvider.is_default.is_(True))
    if exclude_id is not None:
        stmt = stmt.where(LLMProvider.id != exclude_id)
    for p in session.exec(stmt).all():
        p.is_default = False


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/providers", response_model=list[LLMProviderResponse])
def list_providers(session: Session = Depends(get_session)) -> list[dict]:
    """List all configured LLM providers."""
    providers = session.exec(
        select(LLMProvider).order_by(LLMProvider.created_at)
    ).all()
    return [_model_to_response(p) for p in providers]


@router.get("/provider-types", response_model=list[ProviderTypeResponse])
def get_provider_types(
    session: Session = Depends(get_transactional_session),
) -> list[dict]:
    """List built-in and plugin-backed provider implementation types."""
    return list_provider_types(session)


@router.get("/providers/{provider_id}", response_model=LLMProviderResponse)
def get_provider(
    provider_id: str,
    session: Session = Depends(get_session),
) -> dict:
    """Get a single provider by ID."""
    provider = get_provider_by_id(session, provider_id)
    if provider is None:
        raise HTTPException(status_code=404, detail="Provider not found")
    return _model_to_response(provider)


@router.post("/providers", response_model=LLMProviderResponse, status_code=201)
def create_provider(
    body: LLMProviderCreate,
    session: Session = Depends(get_transactional_session),
) -> dict:
    """Create a new LLM provider."""
    # Check for duplicate name
    existing = session.exec(
        select(LLMProvider).where(LLMProvider.name == body.name)
    ).first()
    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail=f"Provider with name '{body.name}' already exists",
        )

    # If is_default, unset any existing default
    if body.is_default:
        _unset_default(session)

    provider = LLMProvider(
        name=body.name,
        display_name=body.display_name,
        provider_type=body.provider_type,
        plugin_id=body.plugin_id,
        api_key=body.api_key,
        base_url=body.base_url,
        default_model=body.default_model,
        custom_config=body.custom_config,
        is_default=body.is_default,
    )
    session.add(provider)
    session.flush()
    replace_provider_models(session, provider, body.models)
    session.flush()
    logger.info("Created provider '%s' (id=%s)", provider.name, provider.id)
    return _model_to_response(provider)


@router.patch("/providers/{provider_id}", response_model=LLMProviderResponse)
def update_provider(
    provider_id: str,
    body: LLMProviderUpdate,
    session: Session = Depends(get_transactional_session),
) -> dict:
    """Update an existing provider."""
    provider = session.exec(
        select(LLMProvider).where(LLMProvider.id == provider_id)
    ).first()
    if provider is None:
        raise HTTPException(status_code=404, detail="Provider not found")

    update_data = body.model_dump(exclude_unset=True)

    # Treat empty api_key as "don't change" to prevent accidental wipe
    if "api_key" in update_data and not update_data["api_key"]:
        del update_data["api_key"]

    # If is_default, unset any existing default
    if update_data.get("is_default"):
        _unset_default(session, exclude_id=provider_id)

    if "models" in update_data:
        replace_provider_models(session, provider, update_data.pop("models"))

    for key, value in update_data.items():
        setattr(provider, key, value)
    if not provider.enabled:
        provider.is_default = False
    provider.updated_at = utcnow()

    session.flush()
    return _model_to_response(provider)


@router.delete("/providers/{provider_id}", status_code=204)
def delete_provider(
    provider_id: str,
    session: Session = Depends(get_transactional_session),
) -> None:
    """Soft-delete (disable) a provider."""
    provider = session.exec(
        select(LLMProvider).where(LLMProvider.id == provider_id)
    ).first()
    if provider is None:
        raise HTTPException(status_code=404, detail="Provider not found")

    provider.enabled = False
    provider.is_default = False
    provider.updated_at = utcnow()
    session.flush()
    logger.info("Disabled provider '%s' (id=%s)", provider.name, provider.id)


@router.get("/providers/{provider_id}/models")
def fetch_provider_models(
    provider_id: str,
    session: Session = Depends(get_transactional_session),
) -> list[dict]:
    """Fetch available models live from the provider's upstream API."""
    provider = get_provider_by_id(session, provider_id)
    if provider is None:
        raise HTTPException(status_code=404, detail="Provider not found")

    client = create_llm_client(session, provider)
    if client is None:
        raise HTTPException(
            status_code=500, detail="Failed to create LLM client"
        )

    try:
        models = client.getModels()
        return [
            {"name": m.name, "display_name": m.displayName or m.name}
            for m in models
        ]
    except Exception as exc:
        logger.exception("Failed to fetch models from provider '%s'", provider.name)
        raise HTTPException(
            status_code=502,
            detail=f"Upstream API error: {exc}",
        ) from exc
