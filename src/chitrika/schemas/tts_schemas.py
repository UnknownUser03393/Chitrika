"""TTS request schemas."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class TTSRequest(BaseModel):
    """Per-request TTS configuration and text.

    ``provider`` selects the backend: ``openai`` (OpenAI-compatible
    ``/v1/audio/speech``) or ``gptsovits`` (local GPT-SoVITS ``/tts``).
    Only the fields relevant to the chosen provider are required.
    """

    provider: Literal["openai", "gptsovits"] = "openai"
    text: str = Field(min_length=1, max_length=4000)
    api_key: str = Field(default="", max_length=4096)
    base_url: str = Field(default="https://api.openai.com/v1", max_length=2048)
    model: str = Field(default="gpt-4o-mini-tts", max_length=200)
    voice: str = Field(default="alloy", max_length=100)
    response_format: str = Field(default="mp3", max_length=20)
    speed: float = Field(default=1.0, ge=0.25, le=4.0)
    # --- GPT-SoVITS native fields (used when provider == "gptsovits") ---
    text_lang: str = Field(default="zh", max_length=50)
    ref_audio_path: str = Field(default="", max_length=1024)
    prompt_text: str = Field(default="", max_length=2000)
    prompt_lang: str = Field(default="zh", max_length=50)

    @model_validator(mode="after")
    def _validate_by_provider(self) -> "TTSRequest":
        if self.provider == "gptsovits":
            if not self.ref_audio_path.strip():
                raise ValueError("ref_audio_path is required for gptsovits provider")
            return self
        if not self.api_key.strip():
            raise ValueError("api_key is required for openai provider")
        return self

    @field_validator("base_url", "model", "voice", "response_format", mode="before")
    @classmethod
    def strip_text_fields(cls, value: str) -> str:
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("text", "api_key", mode="before")
    @classmethod
    def strip_required_fields(cls, value: str) -> str:
        if isinstance(value, str):
            return value.strip()
        return value
