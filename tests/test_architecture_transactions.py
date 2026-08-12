"""Architectural transaction ownership and atomicity regression tests."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path

import pytest
from sqlmodel import Session

from src.chitrika.services.heartbeat_coordinator import HeartbeatCoordinator
from src.chitrika.uow import UnitOfWork


def test_engines_domain_services_and_routes_do_not_own_transactions():
    roots = [
        Path("src/chitrika/engines"),
        Path("src/chitrika/repositories"),
        Path("src/chitrika/routes"),
        Path("src/chitrika/services"),
    ]
    violations: list[str] = []
    for root in roots:
        for path in root.rglob("*.py"):
            source = path.read_text(encoding="utf-8")
            if ".commit(" in source or ".rollback(" in source:
                violations.append(str(path))
    assert violations == []


def test_unit_of_work_commits_once_or_rolls_back_once():
    class TrackingSession:
        commits = 0
        rollbacks = 0

        def commit(self):
            self.commits += 1

        def rollback(self):
            self.rollbacks += 1

    successful = TrackingSession()
    with UnitOfWork(successful):
        pass
    assert (successful.commits, successful.rollbacks) == (1, 0)

    failed = TrackingSession()
    with pytest.raises(RuntimeError):
        with UnitOfWork(failed):
            raise RuntimeError("boom")
    assert (failed.commits, failed.rollbacks) == (0, 1)

    class CommitFailure(TrackingSession):
        def commit(self):
            self.commits += 1
            raise RuntimeError("commit failed")

    commit_failure = CommitFailure()
    with pytest.raises(RuntimeError, match="commit failed"):
        with UnitOfWork(commit_failure):
            pass
    assert (commit_failure.commits, commit_failure.rollbacks) == (1, 1)


def test_heartbeat_rolls_back_failed_character_and_continues(
    test_engine, session, seeded_character, monkeypatch
):
    from src.chitrika.models.character import Character
    from src.chitrika.services import heartbeat_coordinator

    second = Character(
        name="heartbeat-second",
        display_name="Second",
        personality_prompt="test",
    )
    session.add(second)
    session.commit()
    first_id, second_id = seeded_character.id, second.id

    def maintain(self, character):
        character.display_name = "maintained"
        self.session.flush()
        if character.id == first_id:
            raise RuntimeError("character failure")

    monkeypatch.setattr(
        heartbeat_coordinator.CharacterMaintenanceService, "maintain", maintain
    )

    @contextmanager
    def sessions():
        with Session(test_engine) as isolated:
            yield isolated

    HeartbeatCoordinator(sessions).run_cycle(decay_rate=0.15, loneliness_threshold=0.6)
    session.expire_all()
    assert session.get(Character, first_id).display_name == "Test Character"
    assert session.get(Character, second_id).display_name == "maintained"


def test_chat_post_processing_is_atomic(session, seeded_character, monkeypatch):
    from sqlmodel import select

    from src.chitrika.engines.emotion_engine import EmotionEngine
    from src.chitrika.models.memory import Memory
    from src.chitrika.services.chat_post_processor import ChatPostProcessor

    original_joy = EmotionEngine(session).get_or_create_state(seeded_character.id).joy
    processor = ChatPostProcessor(session)

    def update_emotions(character_id, _user, _assistant):
        EmotionEngine(session).update_emotion(character_id, {"joy": 0.8})

    monkeypatch.setattr(processor, "update_emotions", update_emotions)
    monkeypatch.setattr(
        processor.relationships,
        "record_interaction",
        lambda *_args: (_ for _ in ()).throw(RuntimeError("relationship failed")),
    )

    with pytest.raises(RuntimeError, match="relationship failed"):
        with UnitOfWork(session):
            processor.process(
                seeded_character.id,
                "I really enjoy long conversations with you",
                "Me too",
                "missing-source",
            )

    session.expire_all()
    assert EmotionEngine(session).get_state(seeded_character.id).joy == original_joy
    memories = session.exec(
        select(Memory).where(Memory.character_id == seeded_character.id)
    ).all()
    assert memories == []


def test_backup_restore_failure_leaves_no_partial_import(session):
    from sqlmodel import select

    from src.chitrika.models.character import Character
    from src.chitrika.services.backup_service import BackupError, BackupService

    payload = {
        "format": "chitrika-backup",
        "version": 1,
        "characters": [{
            "id": "restored-character",
            "name": "restored-character",
            "display_name": "Restored",
            "personality_prompt": "test",
        }],
        "conversations": [{
            "id": "broken-conversation",
            "character_id": "missing-character",
            "messages": [],
        }],
        "memories": [],
        "settings": {},
    }

    with pytest.raises(BackupError):
        with UnitOfWork(session):
            BackupService(session).restore(payload)

    session.expire_all()
    assert session.exec(
        select(Character).where(Character.id == "restored-character")
    ).first() is None
