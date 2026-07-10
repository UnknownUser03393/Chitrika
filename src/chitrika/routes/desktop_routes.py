"""Desktop notification API — pending notifications and acknowledgement.

Used by the Electron main process to poll for undelivered desktop
notifications and ack them after the toast worker shows them.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from src.chitrika.database import get_session

router = APIRouter(tags=["desktop"])


@router.get("/desktop/notifications/pending")
def get_pending_notifications(
    character_id: str | None = Query(default=None),
    session: Session = Depends(get_session),
) -> list[dict]:
    """Return messages that haven't had a desktop notification yet."""
    from src.chitrika.engines.chat_engine import ChatEngine

    engine = ChatEngine(session)
    return engine.get_pending_desktop_notifications(character_id=character_id)


@router.post("/desktop/notifications/{message_id}/ack")
def acknowledge_notification(
    message_id: str,
    session: Session = Depends(get_session),
) -> dict:
    """Mark a message as having had its desktop notification shown."""
    from src.chitrika.engines.chat_engine import ChatEngine

    engine = ChatEngine(session)
    ok = engine.acknowledge_desktop_notification(message_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Message not found")
    return {"acknowledged": message_id}
