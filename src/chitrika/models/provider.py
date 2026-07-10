"""LLM provider configuration and available model catalog."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

from src.chitrika.models.base import new_id
from src.chitrika.utils.datetime_helpers import utcnow

if TYPE_CHECKING:
    from src.chitrika.models.character import Character


class LLMProvider(SQLModel, table=True):
    """A configured LLM provider with API key, base URL, and available models."""

    __tablename__ = "llm_providers"

    id: str = Field(default_factory=new_id, primary_key=True)
    name: str = Field(
        unique=True,
        index=True,
        description="Unique slug, e.g. 'deepseek', 'openai'",
    )
    display_name: str = Field(
        description="Human-readable name, e.g. 'DeepSeek V4'",
    )
    api_key: str = Field(
        default="",
        description="API key for this provider",
    )
    base_url: str = Field(
        default="",
        description="API base URL, e.g. 'https://api.deepseek.com/v1'",
    )
    default_model: str = Field(
        default="",
        description="Default model name (first in the list if not set)",
    )
    is_default: bool = Field(
        default=False,
        index=True,
        description="Whether this provider is used as the fallback default",
    )
    enabled: bool = Field(default=True, index=True)
    created_at: datetime = Field(default_factory=utcnow, index=True)
    updated_at: datetime = Field(default_factory=utcnow, index=True)

    characters: list["Character"] = Relationship(back_populates="provider")
    models: list["LLMProviderModel"] = Relationship(
        back_populates="provider",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )

    @property
    def model_names(self) -> list[str]:
        """Return enabled model names in insertion order."""
        return [model.name for model in self.models if model.enabled]


class LLMProviderModel(SQLModel, table=True):
    """A model name offered by an LLM provider."""

    __tablename__ = "llm_provider_models"

    id: str = Field(default_factory=new_id, primary_key=True)
    provider_id: str = Field(foreign_key="llm_providers.id", index=True)
    name: str = Field(index=True)
    display_name: str = Field(default="")
    enabled: bool = Field(default=True, index=True)

    provider: LLMProvider = Relationship(back_populates="models")
