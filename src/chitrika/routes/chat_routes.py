"""Chat API routes — conversations, messages, and SSE streaming."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlmodel import Session

from src.chitrika.application.chat_stream_service import ChatStreamApplicationService
from src.chitrika.database import get_session, get_transactional_session
from src.chitrika.application.chat_service import (
    ConversationApplicationService,
    MessageApplicationService,
)
from src.chitrika.schemas.chat_schemas import (
    ChatResponse,
    ConversationBatchRequest,
    ConversationBatchResponse,
    ConversationCreate,
    ConversationDetail,
    MessageEdit,
    MessageListResponse,
    MessageResponse,
    SendMessage,
)

logger = logging.getLogger("chitrika.routes.chat")

router = APIRouter(tags=["chat"])


# ---------------------------------------------------------------------------
# Conversation list — GET /api/conversations  (also /api/chats for compat)
# ---------------------------------------------------------------------------


@router.get("/conversations")
def list_conversations(
    character_id: str | None = Query(default=None),
    session: Session = Depends(get_session),
) -> list[ChatResponse]:
    """List all conversations, enriched for the frontend ChatListView."""
    return ConversationApplicationService(session).list(character_id)


# Frontend compatibility alias
@router.get("/chats")
def list_chats(
    character_id: str | None = Query(default=None),
    session: Session = Depends(get_session),
) -> list[ChatResponse]:
    """Alias for GET /api/conversations (frontend compat)."""
    return list_conversations(character_id=character_id, session=session)


# ---------------------------------------------------------------------------
# Create conversation — POST /api/conversations
# ---------------------------------------------------------------------------


@router.post("/conversations", status_code=201)
def create_conversation(
    body: ConversationCreate,
    session: Session = Depends(get_transactional_session),
) -> ConversationDetail:
    """Create a new conversation with a character."""
    try:
        return ConversationApplicationService(session).create(
            body.character_id, body.title
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Batch conversation operations
# ---------------------------------------------------------------------------


@router.post("/conversations/batch/delete")
def batch_delete_conversations(
    body: ConversationBatchRequest | list[str],
    session: Session = Depends(get_transactional_session),
) -> ConversationBatchResponse:
    """Delete multiple conversations and all their messages."""
    ids = _conversation_batch_ids(body)
    return ConversationApplicationService(session).delete_batch(ids)


@router.post("/conversations/batch/clear-messages")
def batch_clear_conversation_messages(
    body: ConversationBatchRequest | list[str],
    session: Session = Depends(get_transactional_session),
) -> ConversationBatchResponse:
    """Clear messages from multiple conversations without deleting them."""
    ids = _conversation_batch_ids(body)
    return ConversationApplicationService(session).clear_batch(ids)


def _conversation_batch_ids(body: ConversationBatchRequest | list[str]) -> list[str]:
    ids = body if isinstance(body, list) else body.ids
    if not ids:
        raise HTTPException(status_code=422, detail="At least one conversation id is required")
    return ids


# ---------------------------------------------------------------------------
# Get conversation — GET /api/conversations/{conversation_id}
# ---------------------------------------------------------------------------


@router.get("/conversations/{conversation_id}")
def get_conversation(
    conversation_id: str,
    session: Session = Depends(get_session),
) -> ConversationDetail:
    """Get a single conversation by ID."""
    conv = ConversationApplicationService(session).get(conversation_id)
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv


# ---------------------------------------------------------------------------
# Delete conversation — DELETE /api/conversations/{conversation_id}
# ---------------------------------------------------------------------------


@router.delete("/conversations/{conversation_id}", status_code=204)
def delete_conversation(
    conversation_id: str,
    session: Session = Depends(get_transactional_session),
) -> None:
    """Delete a conversation and all its messages."""
    try:
        ConversationApplicationService(session).delete(conversation_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Mark conversation read — POST /api/conversations/{conversation_id}/read
# ---------------------------------------------------------------------------


@router.post("/conversations/{conversation_id}/read")
def mark_conversation_read(
    conversation_id: str,
    session: Session = Depends(get_transactional_session),
) -> dict:
    """Mark all unread assistant messages in a conversation as read."""
    count = ConversationApplicationService(session).mark_read(conversation_id)
    return {"marked_read": count}


# ---------------------------------------------------------------------------
# Get messages — GET /api/conversations/{conversation_id}/messages
# ---------------------------------------------------------------------------


@router.get("/conversations/{conversation_id}/messages")
def get_messages(
    conversation_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    before: str | None = Query(default=None, alias="before"),
    session: Session = Depends(get_session),
) -> MessageListResponse:
    """Get messages for a conversation, newest last."""
    return MessageApplicationService(session).list(
        conversation_id, limit=limit, before_id=before
    )


# ---------------------------------------------------------------------------
# Send message — POST /api/conversations/{conversation_id}/messages  (SSE)
# ---------------------------------------------------------------------------


@router.delete("/conversations/{conversation_id}/messages", status_code=204)
def clear_conversation_messages(
    conversation_id: str,
    session: Session = Depends(get_transactional_session),
) -> None:
    """Clear all chat messages while keeping the conversation."""
    try:
        ConversationApplicationService(session).clear(conversation_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/conversations/{conversation_id}/messages")
def send_message(
    conversation_id: str,
    body: SendMessage,
) -> StreamingResponse:
    """Send a message and stream the AI response via SSE.

    Returns ``text/event-stream`` with these event types:
        - start   — streaming begins (contains message_id)
        - content — a chunk of the response
        - done    — streaming complete
        - error   — an error occurred
    """
    service = ChatStreamApplicationService()
    try:
        prepared = service.reserve_and_prepare(conversation_id, body.content)
        if prepared is None:
            raise HTTPException(
                status_code=409,
                detail="A response is already being generated for this conversation",
            )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to prepare chat stream")
        raise HTTPException(status_code=500, detail="Failed to prepare response")

    return StreamingResponse(
        service.stream(prepared),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


# ---------------------------------------------------------------------------
# Edit message — PATCH /api/messages/{message_id}
# ---------------------------------------------------------------------------


@router.patch("/messages/{message_id}")
def edit_message(
    message_id: str,
    body: MessageEdit,
    session: Session = Depends(get_transactional_session),
) -> MessageResponse:
    """Edit a message's content."""
    try:
        return MessageApplicationService(session).edit(message_id, body.content)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Delete message — DELETE /api/messages/{message_id}
# ---------------------------------------------------------------------------


@router.post("/messages/{message_id}/recall")
def recall_message(
    message_id: str,
    session: Session = Depends(get_transactional_session),
) -> MessageResponse:
    """Mark a message as recalled."""
    try:
        return MessageApplicationService(session).recall(message_id)
    except PermissionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/messages/{message_id}", status_code=204)
def delete_message(
    message_id: str,
    session: Session = Depends(get_transactional_session),
) -> None:
    """Soft-delete a message."""
    try:
        MessageApplicationService(session).delete(message_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
