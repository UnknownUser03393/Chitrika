"""Pydantic schemas for LLM provider API requests and responses."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class CustomProviderOptionResponse(BaseModel):
    value: str
    label: str


class CustomProviderFieldResponse(BaseModel):
    key: str
    label: str
    input_type: Literal["text", "password", "select"]
    required: bool
    secret: bool
    default: str
    placeholder: str
    help_text: str
    options: list[CustomProviderOptionResponse] = Field(default_factory=list)
    summary: bool = False


class CustomProviderAPIResponse(BaseModel):
    fields: list[CustomProviderFieldResponse] = Field(default_factory=list)
    supports_model_fetch: bool = False
    model_field_key: str | None = None


class PluginEndpointResponse(BaseModel):
    method: str
    path: str
    summary: str = ""
    description: str = ""


class PluginAPIResponse(BaseModel):
    endpoints: list[PluginEndpointResponse] = Field(default_factory=list)


class ProviderTypeResponse(BaseModel):
    type: str
    label: str
    plugin_id: str | None
    needs_api_key: bool
    needs_base_url: bool
    default_base_url: str
    default_model: str
    supports_model_fetch: bool
    custom_provider_api: CustomProviderAPIResponse | None = None
    plugin_api: PluginAPIResponse | None = None


class LLMProviderCreate(BaseModel):
    """Request body for creating a new LLM provider."""

    name: str = Field(..., min_length=1, max_length=64, description="Unique slug")
    display_name: str = Field(..., min_length=1, max_length=128)
    provider_type: str = Field(default="openai", min_length=1, max_length=64)
    plugin_id: str | None = Field(default=None, max_length=128)
    api_key: str = Field(default="", description="API key (plaintext in request)")
    base_url: str = Field(default="", description="API base URL")
    default_model: str = Field(default="")
    custom_config: dict[str, Any] = Field(default_factory=dict)
    models: list[str] = Field(default_factory=list, description="Available model names")
    is_default: bool = False


class LLMProviderUpdate(BaseModel):
    """Request body for updating an existing LLM provider.
    Only the fields provided will be updated."""

    display_name: str | None = None
    provider_type: str | None = Field(default=None, min_length=1, max_length=64)
    plugin_id: str | None = Field(default=None, max_length=128)
    api_key: str | None = Field(
        default=None,
        description="New API key. Send a non-empty value to update; empty string = no change.",
    )
    base_url: str | None = None
    default_model: str | None = None
    custom_config: dict[str, Any] | None = None
    models: list[str] | None = None
    is_default: bool | None = None
    enabled: bool | None = None


class LLMProviderResponse(BaseModel):
    """A provider returned to the local client."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    display_name: str
    provider_type: str
    plugin_id: str | None
    api_key: str
    base_url: str
    default_model: str
    custom_config: dict[str, Any]
    models: list[str]
    is_default: bool
    enabled: bool
    created_at: datetime
    updated_at: datetime
