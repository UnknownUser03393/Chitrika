"""Thread-safe plugin loading, discovery, invocation, and configuration."""

from __future__ import annotations

import importlib.util
import json
import logging
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from threading import RLock
from types import ModuleType
from typing import Any

from pydantic import ValidationError

from src.chitrika.config import config as app_config
from src.chitrika.models.plugin import PluginInstallation
from src.chitrika.plugins.api import PluginAPI, PluginConfig, PromptContext, ProviderSpec
from src.chitrika.repositories.plugin_state_repository import PluginStateRepository
from src.chitrika.schemas.plugin_schemas import PluginManifest
from src.chitrika.utils.datetime_helpers import utcnow

logger = logging.getLogger("chitrika.plugins")
ENTRYPOINT_PATTERN = re.compile(r"^([A-Za-z0-9_./-]+\.py):([A-Za-z_][A-Za-z0-9_]*)$")


class PluginError(ValueError):
    pass


@dataclass(slots=True)
class _LoadedPlugin:
    fingerprint: tuple[str, str, int, int]
    plugin: Any
    module_name: str


class PluginRegistry:
    """One process-level cache for trusted plugin modules."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._cache: dict[str, _LoadedPlugin] = {}

    def load(self, record: PluginInstallation) -> Any:
        with self._lock:
            fingerprint, module_path, attribute = self._resolve(record)
            cached = self._cache.get(record.id)
            if cached is not None and cached.fingerprint == fingerprint:
                return cached.plugin
            self._invalidate_locked(record.id)
            safe_id = record.id.replace(".", "_").replace("-", "_")
            module_name = f"chitrika_local_plugin_{safe_id}_{abs(hash(fingerprint)):x}"
            spec = importlib.util.spec_from_file_location(module_name, module_path)
            if spec is None or spec.loader is None:
                raise PluginError("could not create module loader")
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            directory = str(module_path.parent)
            sys.path.insert(0, directory)
            try:
                self._execute_module(spec.loader, module)
            except Exception:
                sys.modules.pop(module_name, None)
                raise
            finally:
                sys.path.remove(directory)
            if not hasattr(module, attribute):
                sys.modules.pop(module_name, None)
                raise PluginError(f"entrypoint attribute '{attribute}' was not found")
            plugin = getattr(module, attribute)
            self._cache[record.id] = _LoadedPlugin(fingerprint, plugin, module_name)
            return plugin

    def invalidate(self, plugin_id: str) -> None:
        with self._lock:
            self._invalidate_locked(plugin_id)

    def invalidate_if_changed(self, record: PluginInstallation) -> None:
        with self._lock:
            cached = self._cache.get(record.id)
            if cached is None:
                return
            try:
                fingerprint, _, _ = self._resolve(record)
            except PluginError:
                self._invalidate_locked(record.id)
                return
            if cached.fingerprint != fingerprint:
                self._invalidate_locked(record.id)

    def _invalidate_locked(self, plugin_id: str) -> None:
        cached = self._cache.pop(plugin_id, None)
        if cached is not None:
            sys.modules.pop(cached.module_name, None)

    @staticmethod
    def _resolve(record: PluginInstallation):
        match = ENTRYPOINT_PATTERN.fullmatch(record.entrypoint)
        if match is None:
            raise PluginError("entrypoint must use the form relative_file.py:attribute")
        relative_file, attribute = match.groups()
        directory = Path(record.path).resolve()
        module_path = (directory / relative_file).resolve()
        if directory != module_path.parent and directory not in module_path.parents:
            raise PluginError("entrypoint escapes the plugin directory")
        if not module_path.is_file():
            raise PluginError(f"entrypoint file does not exist: {relative_file}")
        stat = module_path.stat()
        return (
            (str(module_path), record.entrypoint, stat.st_mtime_ns, stat.st_size),
            module_path,
            attribute,
        )

    @staticmethod
    def _execute_module(loader: Any, module: ModuleType) -> None:
        loader.exec_module(module)


_PROCESS_REGISTRY = PluginRegistry()


def get_plugin_registry() -> PluginRegistry:
    return _PROCESS_REGISTRY


class PluginDiscoveryService:
    def __init__(
        self,
        states: PluginStateRepository,
        registry: PluginRegistry,
        plugin_dir: Path | str | None = None,
    ) -> None:
        self.states = states
        self.registry = registry
        self.plugin_dir = Path(plugin_dir or app_config.plugins_dir).resolve()

    def discover(self) -> tuple[list[PluginInstallation], list[str]]:
        self.plugin_dir.mkdir(parents=True, exist_ok=True)
        for record in self.states.all():
            record.available = False
        found: list[PluginInstallation] = []
        invalid: list[str] = []
        for manifest_path in sorted(self.plugin_dir.glob("*/plugin.json")):
            try:
                raw = json.loads(manifest_path.read_text(encoding="utf-8"))
                if not isinstance(raw, dict):
                    raise PluginError("manifest root must be an object")
                manifest = PluginManifest.model_validate(raw)
                values = manifest.model_dump(exclude={"manifest_version"})
                values.update(path=str(manifest_path.parent.resolve()), available=True)
                record = self.states.upsert(values)
                self.registry.invalidate_if_changed(record)
                found.append(record)
            except (OSError, json.JSONDecodeError, ValidationError, PluginError) as exc:
                invalid.append(f"{manifest_path.relative_to(self.plugin_dir)}: {exc}")
        for record in self.states.all():
            if not record.available:
                self.registry.invalidate(record.id)
        self.states.session.flush()
        return found, invalid


class PluginInvoker:
    """Validate and isolate all public plugin hook calls."""

    def __init__(self, states: PluginStateRepository, registry: PluginRegistry) -> None:
        self.states = states
        self.registry = registry

    def set_enabled(self, plugin_id: str, enabled: bool) -> PluginInstallation:
        record = self.states.get(plugin_id)
        if record is None:
            raise PluginError(f"Plugin '{plugin_id}' was not found")
        if enabled and not record.available:
            raise PluginError(f"Plugin '{plugin_id}' is no longer present on disk")
        if enabled:
            try:
                self.registry.load(record)
            except Exception as exc:
                record.enabled = False
                self.states.set_error(record, str(exc))
                raise PluginError(str(exc)) from exc
        else:
            self.registry.invalidate(plugin_id)
        record.enabled = enabled
        record.load_error = None
        record.updated_at = utcnow()
        self.states.session.flush()
        return record

    def apply_system_prompt(self, context: PromptContext) -> str:
        current = context.system_prompt
        for record in self.states.enabled():
            try:
                hook = getattr(self.registry.load(record), "on_system_prompt", None)
                if hook is None:
                    continue
                result = hook(PromptContext(
                    character_id=context.character_id,
                    conversation_id=context.conversation_id,
                    user_content=context.user_content,
                    system_prompt=current,
                ))
                if result is not None:
                    if not isinstance(result, str):
                        raise PluginError("on_system_prompt must return str or None")
                    current = result
                self.states.set_error(record, None)
            except Exception as exc:
                self.states.set_error(record, f"Hook failed: {exc}")
                logger.exception("Plugin '%s' prompt hook failed", record.id)
        return current

    def list_provider_specs(self) -> list[ProviderSpec]:
        specs: list[ProviderSpec] = []
        for record in self.states.enabled():
            try:
                hook = getattr(self.registry.load(record), "get_provider_specs", None)
                values = hook() if hook else None
                if values is not None:
                    if not isinstance(values, list) or not all(isinstance(v, ProviderSpec) for v in values):
                        raise PluginError("get_provider_specs must return list[ProviderSpec]")
                    specs.extend(values)
                self.states.set_error(record, None)
            except Exception as exc:
                self.states.set_error(record, f"Provider spec hook failed: {exc}")
                logger.exception("Plugin '%s' provider spec hook failed", record.id)
        return specs

    def get_config(self, plugin_id: str) -> PluginConfig | None:
        return self._typed_hook(plugin_id, "get_plugin_config", PluginConfig, "config")

    def get_api(self, plugin_id: str) -> PluginAPI | None:
        return self._typed_hook(plugin_id, "get_plugin_api", PluginAPI, "API")

    def get_provider_factory(self, plugin_id: str, provider_type: str):
        record = self._enabled_record(plugin_id)
        try:
            hook = getattr(self.registry.load(record), "get_provider_factory", None)
            if hook is None:
                raise PluginError(f"Plugin '{plugin_id}' does not expose provider factories")
            factory = hook(provider_type)
            if factory is None:
                raise PluginError(f"Plugin '{plugin_id}' does not handle provider type '{provider_type}'")
            self.states.set_error(record, None)
            return factory
        except Exception as exc:
            self.states.set_error(record, f"Provider factory hook failed: {exc}")
            raise PluginError(str(exc)) from exc

    def _typed_hook(self, plugin_id: str, hook_name: str, expected: type, label: str):
        try:
            record = self._enabled_record(plugin_id)
        except PluginError:
            return None
        try:
            hook = getattr(self.registry.load(record), hook_name, None)
            value = hook() if hook else None
            if value is not None and not isinstance(value, expected):
                raise PluginError(f"{hook_name} returned an invalid value")
            self.states.set_error(record, None)
            return value
        except Exception as exc:
            self.states.set_error(record, f"Plugin {label} hook failed: {exc}")
            logger.exception("Plugin '%s' %s hook failed", plugin_id, label)
            return None

    def _enabled_record(self, plugin_id: str) -> PluginInstallation:
        record = self.states.get(plugin_id)
        if record is None or not record.enabled or not record.available:
            raise PluginError(f"Plugin '{plugin_id}' is not enabled")
        return record


class PluginConfigService:
    def __init__(self, record: PluginInstallation, config: PluginConfig) -> None:
        self.record = record
        self.config = config

    @property
    def path(self) -> Path:
        directory = Path(self.record.path).resolve()
        raw = (self.config.values_path or "").strip()
        candidate = (directory / raw).resolve() if raw else directory / "data" / "config.json"
        if candidate != directory and directory not in candidate.parents:
            raise PluginError("Plugin config values_path escapes the plugin directory")
        return candidate

    def read(self) -> dict[str, str]:
        if not self.path.exists():
            return {}
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return {str(key): str(item) for key, item in value.items()} if isinstance(value, dict) else {}

    def update(self, updates: dict[str, str]) -> dict[str, str]:
        allowed = {field.key for field in self.config.fields}
        unknown = set(updates) - allowed
        if unknown:
            raise PluginError(f"Unknown config keys: {', '.join(sorted(unknown))}")
        values = self.read()
        values.update(updates)
        path = self.path
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(json.dumps(values, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(path)
        return values
