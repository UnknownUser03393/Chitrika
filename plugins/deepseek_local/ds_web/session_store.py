"""Lightweight conversation continuity store for DeepSeek web sessions."""

from __future__ import annotations

import json
import threading
from pathlib import Path
from uuid import uuid4


class SessionStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.lock = threading.Lock()
        self.state = self._load()

    def _load(self) -> dict:
        if not self.path.exists():
            return {"conversations": {}}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {"conversations": {}}
        if not isinstance(data, dict):
            return {"conversations": {}}
        if not isinstance(data.get("conversations"), dict):
            data["conversations"] = {}
        return data

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(self.state, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def get_conversation(self, conversation_id: str | None):
        if not conversation_id:
            return None
        with self.lock:
            conversation = self.state["conversations"].get(conversation_id)
            if conversation is None:
                return None
            item = dict(conversation)
            item["conversation_id"] = conversation_id
            return item

    def create_conversation(
        self,
        *,
        model_type: str,
        chat_session_id: str,
        parent_message_id=None,
        title=None,
        prompt=None,
        conversation_id: str | None = None,
    ):
        with self.lock:
            conversation_id = conversation_id or uuid4().hex
            conversation = {
                "chat_session_id": chat_session_id,
                "parent_message_id": parent_message_id,
                "model_type": model_type,
                "title": title,
                "last_prompt": prompt,
                "last_response": "",
                "updated_at": "",
            }
            self.state["conversations"][conversation_id] = conversation
            self._save()
            item = dict(conversation)
            item["conversation_id"] = conversation_id
            return item

    def update_conversation(self, conversation_id: str, **changes):
        with self.lock:
            conversation = self.state["conversations"].get(conversation_id)
            if conversation is None:
                return None
            conversation.update(changes)
            self._save()
            item = dict(conversation)
            item["conversation_id"] = conversation_id
            return item
