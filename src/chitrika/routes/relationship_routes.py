"""Relationship-state inspection API."""

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from src.chitrika.database import get_transactional_session
from src.chitrika.engines.relationship_engine import RelationshipEngine
from src.chitrika.models.relationship import RelationshipState
from src.chitrika.schemas.relationship_schemas import RelationshipResponse

router = APIRouter(tags=["relationship"])


@router.get(
    "/characters/{character_id}/relationship",
    response_model=RelationshipResponse,
)
def get_relationship(
    character_id: str,
    session: Session = Depends(get_transactional_session),
) -> RelationshipState:
    """Return the current relationship, creating its neutral state if needed."""
    try:
        return RelationshipEngine(session).get_or_create(character_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
