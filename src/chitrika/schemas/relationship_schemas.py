"""API schemas for persistent character-user relationship state."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class RelationshipResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    character_id: str
    stage: str
    affinity: float
    familiarity: float
    trust: float
    interaction_count: int
    positive_interaction_count: int
    conflict_count: int
    first_interaction_at: datetime | None
    last_interaction_at: datetime | None
    updated_at: datetime
