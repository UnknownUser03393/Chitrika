"""DeepSeek Web Local — Chitrika provider plugin entrypoint.

Bundles the reverse-engineered chat.deepseek.com client (browser auth + PoW).
No platform.deepseek.com API key is used.
"""

from __future__ import annotations

from pathlib import Path

from src.chitrika.plugins.api import (
    CustomProviderAPI,
    CustomProviderField,
    PluginAction,
    PluginConfig,
    ProviderContext,
    ProviderSpec,
)

from provider import DEFAULT_AUTH_STATE, DEFAULT_MODEL, DeepSeekWebProvider

from api import get_plugin_api as _get_plugin_api

PLUGIN_DIR = Path(__file__).resolve().parent


def get_provider_specs() -> list[ProviderSpec]:
    return [
        ProviderSpec(
            type="deepseek-local",
            label="DeepSeek Web (Local)",
            plugin_id="deepseek_local",
            needs_api_key=False,
            needs_base_url=False,
            default_base_url="",
            default_model=DEFAULT_MODEL,
            supports_model_fetch=True,
            custom_provider_api=CustomProviderAPI(
                fields=(
                    CustomProviderField(
                        key="auth_state_path",
                        label="auth_state.json path",
                        input_type="text",
                        required=False,
                        secret=False,
                        default=str(DEFAULT_AUTH_STATE),
                        placeholder=str(DEFAULT_AUTH_STATE),
                        help_text=(
                            "Playwright storage state for chat.deepseek.com. "
                            "Leave blank to use plugins/deepseek_local/data/auth_state.json. "
                            "Create/refresh with: python plugins/deepseek_local/login.py"
                        ),
                        summary=True,
                    ),
                    CustomProviderField(
                        key="default_model",
                        label="Default Model",
                        input_type="text",
                        required=False,
                        default=DEFAULT_MODEL,
                        placeholder=DEFAULT_MODEL,
                        help_text="Aliases: deepseek-chat/default/fast, deepseek-reasoner/expert, vision.",
                        summary=True,
                    ),
                    CustomProviderField(
                        key="thinking",
                        label="Thinking",
                        input_type="text",
                        required=False,
                        default="false",
                        placeholder="false",
                        help_text="true/false — enable thinking_enabled on web completions.",
                        summary=False,
                    ),
                    CustomProviderField(
                        key="search",
                        label="Web Search",
                        input_type="text",
                        required=False,
                        default="false",
                        placeholder="false",
                        help_text="true/false — enable search_enabled on web completions.",
                        summary=False,
                    ),
                ),
                supports_model_fetch=True,
                model_field_key="default_model",
            ),
        )
    ]


def get_provider_factory(provider_type: str):
    if provider_type != "deepseek-local":
        return None

    def factory(context: ProviderContext):
        return DeepSeekWebProvider(context)

    return factory


def get_plugin_config() -> PluginConfig:
    """Plugin-level config (decoupled from any single provider) + actions."""
    return PluginConfig(
        fields=(
            CustomProviderField(
                key="auth_state_path",
                label="auth_state.json 路径",
                input_type="text",
                required=False,
                secret=False,
                default=str(DEFAULT_AUTH_STATE),
                placeholder=str(DEFAULT_AUTH_STATE),
                help_text=(
                    "Playwright 登录状态文件。留空用默认 plugins/deepseek_local/data/auth_state.json。"
                ),
                summary=True,
            ),
            CustomProviderField(
                key="session_store_path",
                label="Session store 文件",
                input_type="text",
                required=False,
                default="",
                placeholder="data/session_store.json",
                help_text="会话书签文件（SessionStore）。留空用默认 data/session_store.json。",
            ),
            CustomProviderField(
                key="conversation_link_store",
                label="会话复用链文件",
                input_type="text",
                required=False,
                default="",
                placeholder="data/conversation_links.json",
                help_text="web 会话复用索引。留空用默认 data/conversation_links.json。",
            ),
            CustomProviderField(
                key="thinking",
                label="Thinking（深度思考）",
                input_type="text",
                required=False,
                default="false",
                placeholder="false",
                help_text="true/false — 在 web 端启用思考模式。",
            ),
            CustomProviderField(
                key="search",
                label="Web Search（联网）",
                input_type="text",
                required=False,
                default="false",
                placeholder="false",
                help_text="true/false — 在 web 端启用联网搜索。",
            ),
            CustomProviderField(
                key="default_model",
                label="默认模型",
                input_type="text",
                required=False,
                default=DEFAULT_MODEL,
                placeholder=DEFAULT_MODEL,
                help_text="别名：deepseek-chat/default/fast, deepseek-reasoner/expert, vision。",
                summary=True,
            ),
        ),
        actions=(
            PluginAction(
                key="status",
                label="查看登录状态与会话统计",
                method="GET",
                path="/status",
            ),
            PluginAction(
                key="relogin",
                label="重新登录",
                method="POST",
                path="/auth/relogin",
                confirm=True,
            ),
            PluginAction(
                key="clear_sessions",
                label="清空会话复用链",
                method="POST",
                path="/sessions/clear",
                confirm=True,
            ),
        ),
        values_path="data/config.json",
    )


class _Plugin:
    @staticmethod
    def get_provider_specs() -> list[ProviderSpec]:
        return get_provider_specs()

    @staticmethod
    def get_provider_factory(provider_type: str):
        return get_provider_factory(provider_type)

    @staticmethod
    def get_plugin_api():
        return _get_plugin_api()

    @staticmethod
    def get_plugin_config() -> PluginConfig:
        return get_plugin_config()


plugin = _Plugin()
