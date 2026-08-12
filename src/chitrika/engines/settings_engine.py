"""Settings Engine — CRUD for the key-value Setting table."""

from __future__ import annotations

import json
import logging

from sqlmodel import Session, select

from src.chitrika.models.settings import Setting

logger = logging.getLogger("chitrika.settings_engine")

# Default values used when no DB row exists yet.
# Bootstrap-only keys (database_url, cors_origins) live in chitrika.json — not here.
DEFAULT_SETTINGS: dict[str, object] = {
    "heartbeat_interval_minutes": 5,
    "emotion_decay_rate": 0.15,
    "loneliness_threshold": 0.6,
    # Off by default: LLM-based memory extraction costs tokens per message.
    # The regex extractor always runs regardless as a free fallback.
    "memory_llm_extraction": False,
    # Off by default: compressing short-term chatter into episodic narrative
    # memories costs an LLM call every time a short-term batch fills up.
    "memory_episodic_summary": False,
}

# Known setting keys and their expected types for safe coercion.
SETTING_TYPES: dict[str, type] = {
    "heartbeat_interval_minutes": int,
    "emotion_decay_rate": float,
    "loneliness_threshold": float,
    "memory_llm_extraction": bool,
    "memory_episodic_summary": bool,
}


class SettingsEngine:
    """Read/write application settings stored in the ``settings`` table.

    Values are JSON-encoded in the DB.  The engine transparently
    serialises / deserialises so callers work with native Python types.
    """

    def __init__(self, session: Session) -> None:
        self.session = session

    # ------------------------------------------------------------------
    # Single-key access
    # ------------------------------------------------------------------

    def get(self, key: str, default: object = None) -> object:
        """Return a single setting value, or *default* if not found."""
        setting = self.session.get(Setting, key)
        if setting is None:
            return default
        try:
            return json.loads(setting.value)
        except (json.JSONDecodeError, TypeError):
            return setting.value

    def set(self, key: str, value: object) -> None:
        """Create or update a single setting in the caller's transaction."""
        setting = self.session.get(Setting, key)
        raw = json.dumps(value, ensure_ascii=False)
        if setting is None:
            setting = Setting(key=key, value=raw)
            self.session.add(setting)
        else:
            setting.value = raw
        self.session.flush()
        logger.debug("Setting %s = %s", key, value)

    def delete(self, key: str) -> bool:
        """Remove a setting.  Returns True if it existed."""
        setting = self.session.get(Setting, key)
        if setting is None:
            return False
        self.session.delete(setting)
        self.session.flush()
        return True

    # ------------------------------------------------------------------
    # Bulk access
    # ------------------------------------------------------------------

    def get_all(self) -> dict[str, object]:
        """Return all settings as a dict, with defaults filled in."""
        rows = self.session.exec(select(Setting)).all()
        result: dict[str, object] = dict(DEFAULT_SETTINGS)
        for row in rows:
            try:
                result[row.key] = json.loads(row.value)
            except (json.JSONDecodeError, TypeError):
                result[row.key] = row.value
        return result

    def get_typed(self) -> dict[str, object]:
        """Like ``get_all()`` but coerces values to their expected types."""
        raw = self.get_all()
        for key, typ in SETTING_TYPES.items():
            if key in raw and not isinstance(raw[key], typ):
                try:
                    raw[key] = typ(raw[key])
                except (ValueError, TypeError):
                    raw[key] = DEFAULT_SETTINGS.get(key)
        return raw

    def apply_defaults(self) -> int:
        """Ensure every key in DEFAULT_SETTINGS has a row.  Returns count of
        newly-created rows."""
        count = 0
        for key, default_value in DEFAULT_SETTINGS.items():
            if self.session.get(Setting, key) is None:
                self.session.add(
                    Setting(
                        key=key,
                        value=json.dumps(default_value, ensure_ascii=False),
                    )
                )
                count += 1
        if count:
            self.session.flush()
        return count
