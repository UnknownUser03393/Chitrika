"""Versioned JSON backup export and atomic restore application logic."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.exc import IntegrityError, StatementError
from sqlmodel import Session, select

from src.chitrika.models.character import Character
from src.chitrika.models.conversation import Conversation
from src.chitrika.models.emotion import EmotionState
from src.chitrika.models.memory import Memory
from src.chitrika.models.message import Message
from src.chitrika.models.relationship import RelationshipState
from src.chitrika.models.settings import Setting
from src.chitrika.utils.datetime_helpers import utcnow

BACKUP_FORMAT = "chitrika-backup"
BACKUP_VERSION = 1
MAX_BACKUP_ENTITIES = 500_000


@dataclass(slots=True)
class BackupError(ValueError):
    detail: str
    status_code: int = 400


def _pick_fields(model: type, data: dict) -> dict:
    return {key: value for key, value in data.items() if key in model.model_fields}


class BackupService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def export_payload(self) -> dict:
        emotions = {row.character_id: row for row in self.session.exec(select(EmotionState)).all()}
        relationships = {
            row.character_id: row for row in self.session.exec(select(RelationshipState)).all()
        }
        characters = []
        for character in self.session.exec(select(Character)).all():
            value = character.model_dump()
            emotion = emotions.get(character.id)
            relationship = relationships.get(character.id)
            value["emotion_state"] = emotion.model_dump() if emotion else None
            value["relationship_state"] = relationship.model_dump() if relationship else None
            characters.append(value)
        messages_by_conversation: dict[str, list[dict]] = {}
        for message in self.session.exec(select(Message)).all():
            messages_by_conversation.setdefault(message.conversation_id, []).append(
                message.model_dump()
            )
        conversations = []
        for conversation in self.session.exec(select(Conversation)).all():
            value = conversation.model_dump()
            value["messages"] = messages_by_conversation.get(conversation.id, [])
            conversations.append(value)
        memories = [
            memory.model_dump(exclude={"embedding"})
            for memory in self.session.exec(select(Memory)).all()
        ]
        settings = {row.key: row.value for row in self.session.exec(select(Setting)).all()}
        exported_at = utcnow()
        return {
            "format": BACKUP_FORMAT,
            "version": BACKUP_VERSION,
            "exported_at": exported_at,
            "counts": {
                "characters": len(characters),
                "conversations": len(conversations),
                "messages": sum(len(items) for items in messages_by_conversation.values()),
                "memories": len(memories),
                "settings": len(settings),
            },
            "characters": characters,
            "conversations": conversations,
            "memories": memories,
            "settings": settings,
        }

    @staticmethod
    def validate(payload: object) -> dict:
        if not isinstance(payload, dict):
            raise BackupError("Backup root must be a JSON object")
        if payload.get("format") != BACKUP_FORMAT:
            raise BackupError(f"Backup format mismatch: expected {BACKUP_FORMAT}")
        if payload.get("version") != BACKUP_VERSION:
            raise BackupError(f"Unsupported backup version: expected {BACKUP_VERSION}")
        for key in ("characters", "conversations", "memories"):
            if not isinstance(payload.get(key), list):
                raise BackupError(f"Backup field '{key}' must be a list")
            if any(not isinstance(item, dict) for item in payload[key]):
                raise BackupError(f"Every item in backup field '{key}' must be an object")
        if not isinstance(payload.get("settings"), dict):
            raise BackupError("Backup field 'settings' must be an object")
        message_count = 0
        for index, character in enumerate(payload["characters"]):
            for nested in ("emotion_state", "relationship_state"):
                if character.get(nested) is not None and not isinstance(character[nested], dict):
                    raise BackupError(f"Character at index {index} has invalid {nested}")
        for index, conversation in enumerate(payload["conversations"]):
            if not isinstance(conversation.get("messages"), list):
                raise BackupError(f"Conversation at index {index} has invalid messages")
            if any(not isinstance(message, dict) for message in conversation["messages"]):
                raise BackupError(
                    f"Conversation at index {index} contains a non-object message"
                )
            message_count += len(conversation["messages"])
        total = sum(len(payload[key]) for key in ("characters", "conversations", "memories"))
        total += message_count + len(payload["settings"])
        if total > MAX_BACKUP_ENTITIES:
            raise BackupError("Backup contains too many entities", 413)
        return payload

    def restore(self, raw_payload: object) -> dict:
        payload = self.validate(raw_payload)
        existing_chars = {row.id for row in self.session.exec(select(Character)).all()}
        existing_convs = {row.id for row in self.session.exec(select(Conversation)).all()}
        existing_messages = {row.id for row in self.session.exec(select(Message)).all()}
        existing_memories = {row.id for row in self.session.exec(select(Memory)).all()}
        existing_settings = {row.key for row in self.session.exec(select(Setting)).all()}
        counts = {
            "characters_created": 0, "characters_skipped": 0,
            "emotions_created": 0, "relationships_created": 0,
            "conversations_created": 0, "conversations_skipped": 0,
            "messages_created": 0, "messages_skipped": 0,
            "memories_created": 0, "memories_skipped": 0,
            "settings_created": 0, "settings_skipped": 0,
        }
        try:
            for source in payload["characters"]:
                data = dict(source)
                character_id = data.get("id")
                if character_id in existing_chars:
                    counts["characters_skipped"] += 1
                    continue
                emotion = data.pop("emotion_state", None)
                relationship = data.pop("relationship_state", None)
                self.session.add(Character(**_pick_fields(Character, data)))
                existing_chars.add(character_id)
                counts["characters_created"] += 1
                if emotion and emotion.get("character_id") == character_id:
                    self.session.add(EmotionState(**_pick_fields(EmotionState, emotion)))
                    counts["emotions_created"] += 1
                if relationship and relationship.get("character_id") == character_id:
                    self.session.add(RelationshipState(**_pick_fields(RelationshipState, relationship)))
                    counts["relationships_created"] += 1
            for source in payload["conversations"]:
                data = dict(source)
                conversation_id = data.get("id")
                if conversation_id in existing_convs:
                    counts["conversations_skipped"] += 1
                    continue
                self.session.add(Conversation(**_pick_fields(Conversation, data)))
                existing_convs.add(conversation_id)
                counts["conversations_created"] += 1
                for message_data in data.get("messages", []):
                    message_id = message_data.get("id")
                    if message_id in existing_messages:
                        counts["messages_skipped"] += 1
                        continue
                    self.session.add(Message(**_pick_fields(Message, message_data)))
                    existing_messages.add(message_id)
                    counts["messages_created"] += 1
            for source in payload["memories"]:
                data = dict(source)
                memory_id = data.get("id")
                if memory_id in existing_memories:
                    counts["memories_skipped"] += 1
                    continue
                data.pop("embedding", None)
                self.session.add(Memory(**_pick_fields(Memory, data)))
                existing_memories.add(memory_id)
                counts["memories_created"] += 1
            for key, value in payload["settings"].items():
                if key in existing_settings:
                    counts["settings_skipped"] += 1
                    continue
                self.session.add(Setting(key=key, value=value))
                existing_settings.add(key)
                counts["settings_created"] += 1
            self.session.flush()
        except (IntegrityError, StatementError, ValueError, TypeError) as exc:
            raise BackupError(
                f"Backup entities failed validation: {type(exc).__name__}"
            ) from exc
        return {"status": "ok", **counts}
