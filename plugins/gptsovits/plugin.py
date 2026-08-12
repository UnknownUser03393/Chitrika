"""GPT-SoVITS (Local Voice) — Chitrika plugin entrypoint.

Manages a local GPT-SoVITS ``api_v2.py`` server and exposes cloned voice
presets (0624xyt) so the app can synthesize assistant replies in a cloned
voice through the core TTS proxy.
"""

from __future__ import annotations

from src.chitrika.plugins.api import (
    CustomProviderField,
    CustomProviderOption,
    PluginAction,
    PluginConfig,
)

from gptsovits_api import DEFAULT_VALUES, _parse_voice_list, get_plugin_api as _get_plugin_api

VOICE_LIST_DEFAULT = DEFAULT_VALUES["voice_list_path"]


def _voice_options() -> tuple[CustomProviderOption, ...]:
    presets = _parse_voice_list(VOICE_LIST_DEFAULT)
    if not presets:
        return ()
    return tuple(
        CustomProviderOption(value=p["value"], label=p["label"]) for p in presets
    )


def get_plugin_config() -> PluginConfig:
    return PluginConfig(
        fields=(
            CustomProviderField(
                key="server_port",
                label="服务端口",
                input_type="text",
                required=False,
                default=DEFAULT_VALUES["server_port"],
                placeholder="9880",
                help_text="api_v2.py 监听的端口，默认 9880。",
                summary=True,
            ),
            CustomProviderField(
                key="python_path",
                label="Python 解释器路径",
                input_type="text",
                required=False,
                default=DEFAULT_VALUES["python_path"],
                placeholder="D:\\Development\\GPT-SoVITS\\venv\\Scripts\\python.exe",
                help_text="GPT-SoVITS venv 里的 python.exe。",
            ),
            CustomProviderField(
                key="api_script",
                label="api_v2.py 路径",
                input_type="text",
                required=False,
                default=DEFAULT_VALUES["api_script"],
                placeholder="D:\\Development\\GPT-SoVITS\\api_v2.py",
                help_text="GPT-SoVITS 的 API 启动脚本。",
            ),
            CustomProviderField(
                key="workdir",
                label="工作目录",
                input_type="text",
                required=False,
                default=DEFAULT_VALUES["workdir"],
                placeholder="D:\\Development\\GPT-SoVITS",
                help_text="启动子进程的工作目录（api_v2.py 依赖 cwd 找预训练模型）。",
            ),
            CustomProviderField(
                key="version",
                label="模型版本",
                input_type="text",
                required=False,
                default=DEFAULT_VALUES["version"],
                placeholder="v4",
                help_text="权重所属版本：v1/v2/v3/v4/v2Pro/v2ProPlus。",
                summary=True,
            ),
            CustomProviderField(
                key="gpt_weights_path",
                label="GPT 权重路径",
                input_type="text",
                required=False,
                default=DEFAULT_VALUES["gpt_weights_path"],
                placeholder="D:\\Development\\GPT-SoVITS\\GPT_weights_v4\\0624xyt-e50.ckpt",
                help_text="微调后的 T2S (GPT) 权重 .ckpt。",
            ),
            CustomProviderField(
                key="sovits_weights_path",
                label="SoVITS 权重路径",
                input_type="text",
                required=False,
                default=DEFAULT_VALUES["sovits_weights_path"],
                placeholder="D:\\Development\\GPT-SoVITS\\SoVITS_weights_v4\\0624xyt_e4_s272_l32.pth",
                help_text="微调后的 VITS 权重 .pth。",
            ),
            CustomProviderField(
                key="device",
                label="计算设备",
                input_type="text",
                required=False,
                default=DEFAULT_VALUES["device"],
                placeholder="cuda",
                help_text="cuda 或 cpu。cuda 不可用时自动回退到 cpu。",
            ),
            CustomProviderField(
                key="voice_list_path",
                label="音色参考列表",
                input_type="text",
                required=False,
                default=DEFAULT_VALUES["voice_list_path"],
                placeholder="D:\\Development\\0624xyt_GPTSoVITS\\0624xyt.list",
                help_text="GPT-SoVITS 标注文件：每行 <wav 路径>|<说话人>|<语言>|<转录文本>。",
            ),
        ),
        actions=(
            PluginAction(
                key="status",
                label="查看服务状态",
                method="GET",
                path="/status",
            ),
            PluginAction(
                key="start",
                label="启动 GPT-SoVITS",
                method="POST",
                path="/start",
            ),
            PluginAction(
                key="stop",
                label="停止 GPT-SoVITS",
                method="POST",
                path="/stop",
                confirm=True,
            ),
            PluginAction(
                key="voices",
                label="刷新音色列表",
                method="GET",
                path="/voices",
            ),
        ),
        values_path="data/config.json",
    )


class _Plugin:
    @staticmethod
    def get_plugin_api():
        return _get_plugin_api()

    @staticmethod
    def get_plugin_config() -> PluginConfig:
        return get_plugin_config()


plugin = _Plugin()
