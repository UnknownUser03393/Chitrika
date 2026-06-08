"""Application configuration loaded from environment variables."""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

from pydantic_settings import BaseSettings, SettingsConfigDict


class ChitrikaConfig(BaseSettings):
    """Chitrika configuration, loaded from .env and environment variables."""

    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- DeepSeek ---
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com/v1"
    deepseek_model: str = "deepseek-chat"

    # --- Database ---
    database_url: str = "sqlite:///./chitrika.db"

    # --- Heartbeat ---
    heartbeat_interval_minutes: int = 5
    emotion_decay_rate: float = 0.15
    loneliness_threshold: float = 0.6

    # --- CORS ---
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    @property
    def cors_origin_list(self) -> list[str]:
        """Parse comma-separated CORS origins into a list."""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


# Singleton
config = ChitrikaConfig()
