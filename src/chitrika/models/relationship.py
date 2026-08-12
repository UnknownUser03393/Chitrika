"""Persistent relationship state between a character and the user."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

from src.chitrika.utils.datetime_helpers import utcnow

if TYPE_CHECKING:
    from src.chitrika.models.character import Character


class RelationshipState(SQLModel, table=True):
    """Slow-moving social state built from repeated interactions."""

    __tablename__ = "relationship_states"

    character_id: str = Field(
        primary_key=True,
        foreign_key="characters.id",
        description="Character whose relationship with the user is tracked",
    )
    stage: str = Field(default="stranger", index=True)
    affinity: float = Field(default=0.05, ge=0.0, le=1.0)
    familiarity: float = Field(default=0.0, ge=0.0, le=1.0)
    trust: float = Field(default=0.05, ge=0.0, le=1.0)
    interaction_count: int = Field(default=0, ge=0)
    positive_interaction_count: int = Field(default=0, ge=0)
    conflict_count: int = Field(default=0, ge=0)
    first_interaction_at: datetime | None = Field(default=None)
    last_interaction_at: datetime | None = Field(default=None, index=True)
    updated_at: datetime = Field(default_factory=utcnow, index=True)

    character: "Character" = Relationship(back_populates="relationship_state")
