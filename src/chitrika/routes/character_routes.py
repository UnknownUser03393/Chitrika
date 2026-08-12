"""Character API routes — CRUD for digital personas."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from src.chitrika.database import get_session, get_transactional_session
from src.chitrika.models.character import Character
from src.chitrika.models.emotion import EmotionState
from src.chitrika.services.provider_service import get_provider_by_name
from src.chitrika.utils.datetime_helpers import utcnow
from src.chitrika.schemas.character_schemas import (
    CharacterCreate,
    CharacterListResponse,
    CharacterResponse,
    CharacterUpdate,
)

router = APIRouter(tags=["characters"])


def _character_to_response(character: Character) -> dict:
    """Convert a character model to the stable API response shape."""
    return {
        "id": character.id,
        "name": character.name,
        "display_name": character.display_name,
        "description": character.description,
        "personality_prompt": character.personality_prompt,
        "provider": character.provider.name if character.provider else "deepseek",
        "initials": character.initials,
        "color": character.color,
        "avatar_url": character.avatar_url,
        "enabled": character.enabled,
        "created_at": character.created_at,
        "updated_at": character.updated_at,
    }


# ---------------------------------------------------------------------------
# GET  /api/characters
# ---------------------------------------------------------------------------

@router.get("/characters", response_model=CharacterListResponse)
def list_characters(
    session: Session = Depends(get_session),
) -> dict:
    """List all characters."""
    characters = session.exec(select(Character)).all()
    return {"characters": [_character_to_response(c) for c in characters]}


# ---------------------------------------------------------------------------
# GET  /api/characters/{character_id}
# ---------------------------------------------------------------------------

@router.get("/characters/{character_id}", response_model=CharacterResponse)
def get_character(
    character_id: str,
    session: Session = Depends(get_session),
) -> dict:
    """Get a single character by ID."""
    character = session.exec(
        select(Character).where(Character.id == character_id)
    ).first()
    if character is None:
        raise HTTPException(status_code=404, detail="Character not found")
    return _character_to_response(character)


# ---------------------------------------------------------------------------
# POST /api/characters
# ---------------------------------------------------------------------------

@router.post("/characters", response_model=CharacterResponse, status_code=201)
def create_character(
    body: CharacterCreate,
    session: Session = Depends(get_transactional_session),
) -> dict:
    """Create a new character with a neutral emotion state."""
    # Check for duplicate name
    existing = session.exec(
        select(Character).where(Character.name == body.name)
    ).first()
    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail=f"Character with name '{body.name}' already exists",
        )

    data = body.model_dump()
    provider_name = data.pop("provider", None)
    provider = get_provider_by_name(session, provider_name) if provider_name else None

    character = Character(
        **data,
        provider_id=provider.id if provider else None,
    )
    session.add(character)
    session.flush()

    # Create neutral emotion state
    emotion = EmotionState(character_id=character.id)
    session.add(emotion)
    session.flush()
    return _character_to_response(character)


# ---------------------------------------------------------------------------
# PATCH  /api/characters/{character_id}
# ---------------------------------------------------------------------------

@router.patch("/characters/{character_id}", response_model=CharacterResponse)
def update_character(
    character_id: str,
    body: CharacterUpdate,
    session: Session = Depends(get_transactional_session),
) -> dict:
    """Update an existing character."""
    character = session.exec(
        select(Character).where(Character.id == character_id)
    ).first()
    if character is None:
        raise HTTPException(status_code=404, detail="Character not found")

    update_data = body.model_dump(exclude_unset=True)
    if "provider" in update_data:
        provider_name = update_data.pop("provider")
        provider = get_provider_by_name(session, provider_name) if provider_name else None
        character.provider_id = provider.id if provider else None

    for key, value in update_data.items():
        setattr(character, key, value)
    character.updated_at = utcnow()

    session.flush()
    return _character_to_response(character)


# ---------------------------------------------------------------------------
# DELETE /api/characters/{character_id}
# ---------------------------------------------------------------------------

@router.delete("/characters/{character_id}", status_code=204)
def delete_character(
    character_id: str,
    session: Session = Depends(get_transactional_session),
) -> None:
    """Disable (soft-delete) a character."""
    character = session.exec(
        select(Character).where(Character.id == character_id)
    ).first()
    if character is None:
        raise HTTPException(status_code=404, detail="Character not found")

    character.enabled = False
    character.updated_at = utcnow()
    session.flush()
