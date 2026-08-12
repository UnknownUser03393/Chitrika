"""Character Seeding — create the default character from skill_0624.txt on first run."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from sqlmodel import Session, select

from src.chitrika.models.character import Character
from src.chitrika.models.emotion import EmotionState
from src.chitrika.services.provider_service import get_default_provider

logger = logging.getLogger("chitrika.seed")

# Path to the character definition file (relative to project root).
# Overridable via CHITRIKA_SKILL_FILE so the packaged desktop app can point at
# its bundled resources dir instead of the repo root.
_DEFAULT_CHARACTER_FILE = Path(__file__).parent.parent.parent.parent / "skill_0624.txt"
_CHARACTER_FILE = Path(os.environ.get("CHITRIKA_SKILL_FILE", str(_DEFAULT_CHARACTER_FILE)))


def _load_personality_prompt() -> str:
    """Read the full personality prompt from skill_0624.txt."""
    if not _CHARACTER_FILE.exists():
        logger.warning("Character file not found: %s", _CHARACTER_FILE)
        return "你是徐悦婷（Alvia），一个性格鲜明的AI伴侣。"

    raw = _CHARACTER_FILE.read_text(encoding="utf-8")
    # The file contains a full character definition.
    # Everything after "## 基本身份" serves as the system prompt.
    # We keep the entire file as the personality prompt — it's the character's bible.
    return raw.strip()


def seed_default_character(session: Session) -> Character | None:
    """Create the default 'Alvia' character if it doesn't already exist.

    Also creates a neutral EmotionState for the character.
    Returns the Character, or None if it already existed.
    """
    existing = session.exec(
        select(Character).where(Character.name == "alvia")
    ).first()

    if existing is not None:
        logger.info("Default character 'alvia' already exists — skipping seed")
        return None

    prompt = _load_personality_prompt()
    provider = get_default_provider(session)

    character = Character(
        name="alvia",
        display_name="徐悦婷",
        description="南外女生，英文名Alvia。外表强势、内心柔软，爱发号施令的中二少女。",
        personality_prompt=prompt,
        initials="徐",
        color="#E84A7A",
        enabled=True,
    )
    character.provider_id = provider.id if provider else None
    session.add(character)
    session.flush()  # get the ID

    # Create neutral emotion state
    emotion = EmotionState(character_id=character.id)
    session.add(emotion)

    session.flush()
    logger.info("Seeded default character: %s (%s)", character.display_name, character.id)
    return character
