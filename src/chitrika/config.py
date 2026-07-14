"""Bootstrap configuration (must be known before the database is ready).

Load order (highest priority first):

1. Environment variables ``DATABASE_URL`` / ``CORS_ORIGINS`` (CI / overrides)
2. ``chitrika.json`` in the project root (or current working directory)
3. Built-in defaults

Runtime knobs (heartbeat, emotion decay, loneliness) live in the SQLite
``settings`` table and are managed through the settings API / UI — not here.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

logger = logging.getLogger("chitrika.config")

DEFAULT_DATABASE_URL = "sqlite:///./chitrika.db"
DEFAULT_CORS_ORIGINS: list[str] = [
    "http://localhost:5173",
    "http://localhost:3000",
    "http://localhost:8080",
    "http://127.0.0.1:8080",
]

CONFIG_FILENAME = "chitrika.json"


def _project_root() -> Path:
    """Repo root: ``src/chitrika/config.py`` → parents[2]."""
    return Path(__file__).resolve().parents[2]


def _find_config_file() -> Path | None:
    """Return the first existing ``chitrika.json`` (cwd, then project root)."""
    for directory in (Path.cwd(), _project_root()):
        candidate = directory / CONFIG_FILENAME
        if candidate.is_file():
            return candidate
    return None


def _normalize_cors(value: object) -> str:
    """Accept a JSON list or a comma-separated string → single CSV string."""
    if isinstance(value, list):
        return ",".join(str(item).strip() for item in value if str(item).strip())
    if isinstance(value, str):
        return value.strip()
    return ",".join(DEFAULT_CORS_ORIGINS)


def _load_json_file(path: Path) -> dict[str, object]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Failed to read %s: %s — using defaults", path, exc)
        return {}
    if not isinstance(raw, dict):
        logger.warning("%s root must be a JSON object — ignoring", path)
        return {}
    return raw


class ChitrikaConfig:
    """Infrastructure bootstrap config (DB location + CORS)."""

    def __init__(self) -> None:
        file_data: dict[str, object] = {}
        config_path = _find_config_file()
        if config_path is not None:
            file_data = _load_json_file(config_path)
            logger.debug("Loaded bootstrap config from %s", config_path)

        env_db = os.environ.get("DATABASE_URL", "").strip()
        file_db = file_data.get("database_url")
        if env_db:
            self.database_url = env_db
        elif isinstance(file_db, str) and file_db.strip():
            self.database_url = file_db.strip()
        else:
            self.database_url = DEFAULT_DATABASE_URL

        env_cors = os.environ.get("CORS_ORIGINS", "").strip()
        if env_cors:
            self.cors_origins = env_cors
        elif "cors_origins" in file_data:
            self.cors_origins = _normalize_cors(file_data["cors_origins"])
        else:
            self.cors_origins = ",".join(DEFAULT_CORS_ORIGINS)

    @property
    def cors_origin_list(self) -> list[str]:
        """Parse comma-separated CORS origins into a list."""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


# Singleton — imported by database.py / main.py at startup
config = ChitrikaConfig()
