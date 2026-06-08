"""Character API routes — CRUD for digital personas."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from src.chitrika.database import get_session
from src.chitrika.models.character import Character
from src.chitrika.models.emotion import EmotionState
from src.chitrika.utils.datetime_helpers import utcnow
from src.chitrika.schemas.character_schemas import (
    CharacterCreate,
    CharacterListResponse,
    CharacterResponse,
    CharacterUpdate,
)

router = APIRouter(tags=["characters"])


# ---------------------------------------------------------------------------
# GET  /api/characters
# ---------------------------------------------------------------------------

@router.get("/characters", response_model=CharacterListResponse)
def list_characters(
    session: Session = Depends(get_session),
) -> dict:
    """List all characters."""
    characters = session.exec(select(Character)).all()
    return {"characters": [CharacterResponse.model_validate(c) for c in characters]}


# ---------------------------------------------------------------------------
# GET  /api/characters/{character_id}
# ---------------------------------------------------------------------------

@router.get("/characters/{character_id}", response_model=CharacterResponse)
def get_character(
    character_id: str,
    session: Session = Depends(get_session),
) -> Character:
    """Get a single character by ID."""
    character = session.exec(
        select(Character).where(Character.id == character_id)
    ).first()
    if character is None:
        raise HTTPException(status_code=404, detail="Character not found")
    return character


# ---------------------------------------------------------------------------
# POST /api/characters
# ---------------------------------------------------------------------------

@router.post("/characters", response_model=CharacterResponse, status_code=201)
def create_character(
    body: CharacterCreate,
    session: Session = Depends(get_session),
) -> Character:
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

    character = Character(**body.model_dump())
    session.add(character)
    session.flush()

    # Create neutral emotion state
    emotion = EmotionState(character_id=character.id)
    session.add(emotion)
    session.commit()
    session.refresh(character)
    return character


# ---------------------------------------------------------------------------
# PATCH  /api/characters/{character_id}
# ---------------------------------------------------------------------------

@router.patch("/characters/{character_id}", response_model=CharacterResponse)
def update_character(
    character_id: str,
    body: CharacterUpdate,
    session: Session = Depends(get_session),
) -> Character:
    """Update an existing character."""
    character = session.exec(
        select(Character).where(Character.id == character_id)
    ).first()
    if character is None:
        raise HTTPException(status_code=404, detail="Character not found")

    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(character, key, value)
    character.updated_at = utcnow()

    session.commit()
    session.refresh(character)
    return character


# ---------------------------------------------------------------------------
# DELETE /api/characters/{character_id}
# ---------------------------------------------------------------------------

@router.delete("/characters/{character_id}", status_code=204)
def delete_character(
    character_id: str,
    session: Session = Depends(get_session),
) -> None:
    """Disable (soft-delete) a character."""
    character = session.exec(
        select(Character).where(Character.id == character_id)
    ).first()
    if character is None:
        raise HTTPException(status_code=404, detail="Character not found")

    character.enabled = False
    character.updated_at = utcnow()
    session.commit()
