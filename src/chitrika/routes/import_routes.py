"""Import routes — migrate conversation history from external platforms."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from src.chitrika.database import get_transactional_session
from src.chitrika.models.character import Character
from src.chitrika.models.conversation import Conversation
from src.chitrika.models.emotion import EmotionState

router = APIRouter(tags=["import"])


class DoubaoImportRequest(BaseModel):
    source_path: str


def _ts(secs: float) -> datetime:
    """Convert Unix timestamp (seconds) to naive UTC datetime."""
    return datetime.fromtimestamp(secs, tz=timezone.utc).replace(tzinfo=None)


@router.post("/import/doubao")
def import_doubao(
    body: DoubaoImportRequest,
    session: Session = Depends(get_transactional_session),
) -> dict:
    """Import Doubao conversation history from an agentmsg-shify export directory."""
    source = Path(body.source_path)
    cache_file = source / "doubao_conversations_cache.json"

    if not cache_file.exists():
        raise HTTPException(
            status_code=400,
            detail=f"doubao_conversations_cache.json not found at {cache_file}",
        )

    with open(cache_file, "r", encoding="utf-8") as fh:
        data = json.load(fh)

    conversations: list[dict] = data.get("conversations", [])
    if not conversations:
        return {"imported_characters": 0, "imported_conversations": 0}

    # Group conversations by bot_id → one Chitrika character per Doubao bot
    bots: dict[str, list[dict]] = {}
    for conv in conversations:
        bot_id = conv.get("bot_id", "unknown")
        bots.setdefault(bot_id, []).append(conv)

    imported_chars = 0
    imported_convs = 0
    skipped_convs = 0

    for bot_id, convs in bots.items():
        char_name = f"doubao-{bot_id[-8:]}"
        display_name = f"豆包·{bot_id[-4:]}"

        # Find or create character
        existing = session.exec(
            select(Character).where(Character.name == char_name)
        ).first()

        if existing is None:
            character = Character(
                name=char_name,
                display_name=display_name,
                description="从豆包导入的对话历史",
                personality_prompt="",
                initials="豆",
                color="#6EC668",
                enabled=True,
            )
            session.add(character)
            session.flush()

            emotion = EmotionState(character_id=character.id)
            session.add(emotion)
            imported_chars += 1
        else:
            character = existing

        # Import conversations
        for conv in convs:
            doubao_id = conv.get("id", "")
            prefixed_id = f"doubao-{doubao_id}"

            already = session.exec(
                select(Conversation).where(Conversation.id == prefixed_id)
            ).first()
            if already is not None:
                skipped_convs += 1
                continue

            created = _ts(conv.get("created_at", 0))
            updated = _ts(conv.get("updated_at", 0))

            chitrika_conv = Conversation(
                id=prefixed_id,
                character_id=character.id,
                title=conv.get("title") or "未命名对话",
                created_at=created,
                updated_at=updated,
                last_message_at=updated,
            )
            session.add(chitrika_conv)
            imported_convs += 1

    session.flush()

    return {
        "imported_characters": imported_chars,
        "imported_conversations": imported_convs,
        "skipped_conversations": skipped_convs,
        "total_in_source": len(conversations),
    }
