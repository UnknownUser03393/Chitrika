"""Plugin discovery, activation, hook, and management API tests."""

from __future__ import annotations

import json

import pytest

from src.chitrika.plugins.api import PromptContext
from src.chitrika.repositories.plugin_state_repository import PluginStateRepository
from src.chitrika.services.plugin_runtime import (
    PluginDiscoveryService,
    PluginError,
    PluginInvoker,
    get_plugin_registry,
)


def _write_plugin(root, folder: str, manifest: dict, code: str) -> None:
    directory = root / folder
    directory.mkdir(parents=True)
    (directory / "plugin.json").write_text(json.dumps(manifest), encoding="utf-8")
    (directory / "plugin.py").write_text(code, encoding="utf-8")


def _manifest(plugin_id: str, **overrides) -> dict:
    data = {
        "manifest_version": 1,
        "id": plugin_id,
        "name": plugin_id.title(),
        "version": "1.0.0",
        "entrypoint": "plugin.py:plugin",
    }
    data.update(overrides)
    return data


def _runtime(session, plugin_dir):
    states = PluginStateRepository(session)
    registry = get_plugin_registry()
    return (
        states,
        PluginDiscoveryService(states, registry, plugin_dir),
        PluginInvoker(states, registry),
    )


def test_discover_is_disabled_by_default_and_preserves_activation(session, tmp_path):
    _write_plugin(tmp_path, "tone", _manifest("tone"), "plugin = object()\n")
    states, discovery, invoker = _runtime(session, tmp_path)

    records, invalid = discovery.discover()
    assert invalid == []
    assert len(records) == 1
    assert records[0].available is True
    assert records[0].enabled is False

    invoker.set_enabled("tone", True)
    _write_plugin(
        tmp_path,
        "second",
        _manifest("second"),
        "plugin = object()\n",
    )
    discovery.discover()
    assert states.get("tone").enabled is True
    assert states.get("second").enabled is False


def test_missing_plugin_becomes_unavailable(session, tmp_path):
    _write_plugin(tmp_path, "tone", _manifest("tone"), "plugin = object()\n")
    states, discovery, invoker = _runtime(session, tmp_path)
    discovery.discover()

    (tmp_path / "tone" / "plugin.json").unlink()
    discovery.discover()
    record = states.get("tone")
    assert record is not None
    assert record.available is False
    with pytest.raises(PluginError, match="no longer present"):
        invoker.set_enabled("tone", True)


def test_prompt_hooks_run_in_id_order_and_isolate_failure(session, tmp_path):
    _write_plugin(
        tmp_path,
        "b",
        _manifest("b-plugin"),
        """class Plugin:
    def on_system_prompt(self, context):
        return context.system_prompt + "|b"
plugin = Plugin()
""",
    )
    _write_plugin(
        tmp_path,
        "a",
        _manifest("a-plugin"),
        """class Plugin:
    def on_system_prompt(self, context):
        return context.system_prompt + "|a"
plugin = Plugin()
""",
    )
    _write_plugin(
        tmp_path,
        "broken",
        _manifest("broken"),
        """class Plugin:
    def on_system_prompt(self, context):
        raise RuntimeError("boom")
plugin = Plugin()
""",
    )
    states, discovery, invoker = _runtime(session, tmp_path)
    discovery.discover()
    for plugin_id in ("b-plugin", "a-plugin", "broken"):
        invoker.set_enabled(plugin_id, True)

    result = invoker.apply_system_prompt(PromptContext(
        character_id="character",
        conversation_id="conversation",
        user_content="hello",
        system_prompt="base",
    ))

    assert result == "base|a|b"
    assert states.get("broken").load_error == "Hook failed: boom"


def test_invalid_manifest_and_entrypoint_are_reported(session, tmp_path):
    _write_plugin(tmp_path, "bad-id", _manifest("Bad ID"), "plugin = object()\n")
    _, discovery, invoker = _runtime(session, tmp_path)
    records, invalid = discovery.discover()
    assert records == []
    assert len(invalid) == 1

    _write_plugin(
        tmp_path,
        "bad-entrypoint",
        _manifest("bad-entrypoint", entrypoint="../escape.py:plugin"),
        "plugin = object()\n",
    )
    discovery.discover()
    with pytest.raises(PluginError, match="escapes"):
        invoker.set_enabled("bad-entrypoint", True)


def test_registry_cache_hit_and_rescan_fingerprint_invalidation(session, tmp_path):
    _write_plugin(
        tmp_path,
        "cache",
        _manifest("cache-plugin"),
        "plugin = {'version': 1}\n",
    )
    states, discovery, invoker = _runtime(session, tmp_path)
    discovery.discover()
    invoker.set_enabled("cache-plugin", True)
    registry = get_plugin_registry()
    record = states.get("cache-plugin")
    first = registry.load(record)
    assert registry.load(record) is first

    (tmp_path / "cache" / "plugin.py").write_text(
        "plugin = {'version': 200}\n", encoding="utf-8"
    )
    discovery.discover()
    second = registry.load(states.get("cache-plugin"))
    assert second == {"version": 200}
    assert second is not first


def test_plugin_management_api(client, monkeypatch, tmp_path):
    from src.chitrika.config import config

    _write_plugin(tmp_path, "tone", _manifest("tone"), "plugin = object()\n")
    monkeypatch.setattr(config, "plugins_dir", str(tmp_path))

    response = client.get("/api/plugins")
    assert response.status_code == 200
    assert response.json()[0]["id"] == "tone"
    assert response.json()[0]["enabled"] is False

    response = client.patch("/api/plugins/tone", json={"enabled": True})
    assert response.status_code == 200
    assert response.json()["enabled"] is True


def test_chat_engine_applies_enabled_prompt_plugin(
    session, seeded_character, monkeypatch, tmp_path
):
    from src.chitrika.config import config
    from types import SimpleNamespace

    from src.chitrika.repositories.chat_repository import ChatRepository
    from src.chitrika.services import chat_generation_service
    from src.chitrika.services.chat_generation_service import ChatGenerationService

    _write_plugin(
        tmp_path,
        "chat",
        _manifest("chat-prompt"),
        """class Plugin:
    def on_system_prompt(self, context):
        return context.system_prompt + "\\nPLUGIN_MARKER"
plugin = Plugin()
""",
    )
    monkeypatch.setattr(config, "plugins_dir", str(tmp_path))
    _, discovery, invoker = _runtime(session, tmp_path)
    discovery.discover()
    invoker.set_enabled("chat-prompt", True)

    class CapturingLLM:
        pass

    llm = CapturingLLM()
    monkeypatch.setattr(
        chat_generation_service,
        "resolve_provider_for_character",
        lambda *_args, **_kwargs: SimpleNamespace(default_model="fake"),
    )
    monkeypatch.setattr(
        chat_generation_service,
        "create_llm_client",
        lambda *_args, **_kwargs: llm,
    )
    chat = ChatRepository(session)
    conversation = chat.create_conversation(seeded_character.id)
    prepared = ChatGenerationService(session).prepare(conversation.id, "hello")

    assert prepared.llm_messages[0]["role"] == "system"
    assert prepared.llm_messages[0]["content"].endswith("PLUGIN_MARKER")
