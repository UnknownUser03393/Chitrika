"""Schemas for plugin manifests and the plugin management API."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class PluginManifest(BaseModel):
    """The supported ``plugin.json`` format."""

    model_config = ConfigDict(extra="forbid")

    manifest_version: int = Field(default=1, ge=1, le=1)
    id: str = Field(pattern=r"^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$")
    name: str = Field(min_length=1, max_length=100)
    version: str = Field(min_length=1, max_length=50)
    description: str = Field(default="", max_length=500)
    author: str = Field(default="", max_length=100)
    entrypoint: str = Field(default="plugin.py:plugin", min_length=3, max_length=200)


class PluginUpdate(BaseModel):
    enabled: bool


class PluginResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    version: str
    description: str
    author: str
    entrypoint: str
    path: str
    available: bool
    enabled: bool
    load_error: str | None
    installed_at: datetime
    updated_at: datetime
    plugin_api: PluginAPIResponse | None = None
    has_config: bool = False


class PluginScanResponse(BaseModel):
    discovered: int
    invalid: list[str]


class PluginEndpointResponse(BaseModel):
    method: str
    path: str
    summary: str = ""
    description: str = ""


class PluginAPIResponse(BaseModel):
    endpoints: list[PluginEndpointResponse] = Field(default_factory=list)


class PluginConfigOptionResponse(BaseModel):
    value: str
    label: str


class PluginConfigFieldResponse(BaseModel):
    key: str
    label: str
    input_type: Literal["text", "password", "select"]
    required: bool
    secret: bool
    default: str
    placeholder: str
    help_text: str
    options: list[PluginConfigOptionResponse] = Field(default_factory=list)
    summary: bool = False


class PluginActionResponse(BaseModel):
    key: str
    label: str
    method: str
    path: str
    confirm: bool = False


class PluginConfigResponse(BaseModel):
    fields: list[PluginConfigFieldResponse] = Field(default_factory=list)
    values: dict[str, str] = Field(default_factory=dict)
    actions: list[PluginActionResponse] = Field(default_factory=list)


class PluginConfigUpdate(BaseModel):
    values: dict[str, str] = Field(default_factory=dict)
