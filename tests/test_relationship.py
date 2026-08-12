"""Relationship progression and prompt integration tests."""

from src.chitrika.engines.relationship_engine import RelationshipEngine
from src.chitrika.services.prompt_service import PromptService


def test_relationship_progresses_and_records_signals(session, seeded_character):
    engine = RelationshipEngine(session)

    for _ in range(3):
        state = engine.record_interaction(
            seeded_character.id,
            "谢谢你，我想告诉你一个秘密，其实我最近有一点担心自己的工作。",
        )

    assert state.interaction_count == 3
    assert state.positive_interaction_count == 3
    assert state.affinity > 0.1
    assert state.familiarity > 0.08
    assert state.trust > 0.1
    assert state.stage == "acquaintance"


def test_conflict_reduces_affinity_and_trust(session, seeded_character):
    engine = RelationshipEngine(session)
    positive = engine.record_interaction(seeded_character.id, "谢谢你，我很喜欢你。")
    affinity_before = positive.affinity
    trust_before = positive.trust

    conflicted = engine.record_interaction(seeded_character.id, "我讨厌你，闭嘴。")
    assert conflicted.conflict_count == 1
    assert conflicted.affinity < affinity_before
    assert conflicted.trust < trust_before


def test_relationship_is_injected_into_personality_prompt(
    session, seeded_character
):
    from src.chitrika.engines.emotion_engine import EmotionEngine

    relation = RelationshipEngine(session).record_interaction(
        seeded_character.id, "谢谢你，我想告诉你一个秘密。"
    )
    emotion = EmotionEngine(session).get_or_create_state(seeded_character.id)
    prompt = PromptService().build_system_prompt(
        seeded_character,
        emotion,
        [],
        relationship_state=relation,
    )

    assert "你和用户的关系" in prompt
    assert f"关系阶段：{relation.stage}" in prompt
    assert "不要假装关系比实际更亲密" in prompt


def test_relationship_api(client, seeded_character):
    response = client.get(f"/api/characters/{seeded_character.id}/relationship")
    assert response.status_code == 200
    data = response.json()
    assert data["stage"] == "stranger"
    assert data["interaction_count"] == 0


def test_relationship_api_missing_character(client):
    response = client.get("/api/characters/not-real/relationship")
    assert response.status_code == 404
