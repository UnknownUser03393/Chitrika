"""GPT-SoVITS plugin — manage a local api_v2.py server and voice presets.

Handlers are declared through ``get_plugin_api()`` and dispatched by the core
via ``/api/plugins/gptsovits/api/...``. They manage a single GPT-SoVITS
subprocess (start/stop/status) and parse the voice reference list
(``0624xyt.list``) into selectable presets.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import time
from pathlib import Path

from src.chitrika.plugins.api import PluginAPI, PluginEndpoint

logger = logging.getLogger("chitrika.plugins.gptsovits.api")

PLUGIN_DIR = Path(__file__).resolve().parent
DATA_DIR = PLUGIN_DIR / "data"
CONFIG_PATH = DATA_DIR / "config.json"
INFER_PATH = DATA_DIR / "tts_infer_0624xyt.yaml"

# ---------------------------------------------------------------------------
# Defaults + persisted config
# ---------------------------------------------------------------------------

DEFAULT_VALUES: dict[str, str] = {
    "server_port": "9880",
    "python_path": r"D:\Development\GPT-SoVITS\venv\Scripts\python.exe",
    "api_script": r"D:\Development\GPT-SoVITS\api_v2.py",
    "workdir": r"D:\Development\GPT-SoVITS",
    "version": "v4",
    "gpt_weights_path": r"D:\Development\GPT-SoVITS\GPT_weights_v4\0624xyt-e50.ckpt",
    "sovits_weights_path": r"D:\Development\GPT-SoVITS\SoVITS_weights_v4\0624xyt_e4_s272_l32.pth",
    "voice_list_path": r"D:\Development\0624xyt_GPTSoVITS\0624xyt.list",
    "ref_audio_path": "",
    "text_lang": "zh",
    "prompt_lang": "zh",
    "device": "cuda",
}

_process: subprocess.Popen | None = None
_process_lock = False


def _read_values() -> dict[str, str]:
    values = dict(DEFAULT_VALUES)
    if CONFIG_PATH.exists():
        try:
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                values.update({str(k): str(v) for k, v in data.items()})
        except (OSError, json.JSONDecodeError):
            logger.warning("gptsovits: failed to read %s", CONFIG_PATH)
    return values


# ---------------------------------------------------------------------------
# Voice list parsing (0624xyt.list)
# ---------------------------------------------------------------------------


def _parse_voice_list(list_path: str) -> list[dict]:
    """Parse a GPT-SoVITS ``.list`` file into voice presets.

    Each line: ``<wav path>|<speaker>|<prompt_lang>|<prompt_text>``
    """
    path = Path(list_path)
    if not path.is_file():
        return []
    presets: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split("|")
        if len(parts) < 4:
            continue
        ref_audio_path, _speaker, prompt_lang, prompt_text = (
            parts[0],
            parts[1],
            parts[2],
            "|".join(parts[3:]),
        )
        prompt_text = prompt_text.strip()
        presets.append(
            {
                "value": ref_audio_path,
                "label": prompt_text[:48] or Path(ref_audio_path).name,
                "ref_audio_path": ref_audio_path,
                "prompt_text": prompt_text,
                "prompt_lang": (prompt_lang or "zh").lower(),
            }
        )
    return presets


# ---------------------------------------------------------------------------
# Subprocess management
# ---------------------------------------------------------------------------


def _resolve_python(values: dict[str, str]) -> str:
    python_path = values.get("python_path", "")
    if python_path and Path(python_path).is_file():
        return python_path
    return sys.executable


def _build_infer_config(values: dict[str, str]) -> str:
    """Write a GPT-SoVITS tts_infer.yaml pointing at the fine-tuned weights."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    def _fwd(p: str) -> str:
        return p.replace("\\", "/")

    gpt_weights = _fwd(values.get("gpt_weights_path", ""))
    sovits_weights = _fwd(values.get("sovits_weights_path", ""))
    workdir = _fwd(values.get("workdir", ""))
    version = values.get("version", "v4") or "v4"
    device = values.get("device", "cuda") or "cuda"
    is_half = "true" if device.lower() == "cuda" else "false"

    content = f"""custom:
  device: {device}
  is_half: {is_half}
  version: {version}
  t2s_weights_path: {gpt_weights}
  vits_weights_path: {sovits_weights}
  bert_base_path: {workdir}/GPT_SoVITS/pretrained_models/chinese-roberta-wwm-ext-large
  cnhuhuber_base_path: {workdir}/GPT_SoVITS/pretrained_models/chinese-hubert-base
"""
    INFER_PATH.write_text(content, encoding="utf-8")
    return str(INFER_PATH)


def _server_running() -> bool:
    return _process is not None and _process.poll() is None


def _port_open(port: str) -> bool:
    import socket

    try:
        with socket.create_connection(("127.0.0.1", int(port)), timeout=0.5):
            return True
    except OSError:
        return False


def _start_server() -> dict:
    global _process
    if _server_running():
        return {
            "ok": True,
            "running": True,
            "message": "GPT-SoVITS 服务已在运行",
        }

    values = _read_values()
    python_path = _resolve_python(values)
    api_script = values.get("api_script", "")
    workdir = values.get("workdir", "")
    port = values.get("server_port", "9880") or "9880"

    if not api_script or not Path(api_script).is_file():
        return {
            "ok": False,
            "message": f"找不到 api_v2.py：{api_script}",
        }
    if not workdir or not Path(workdir).is_dir():
        return {
            "ok": False,
            "message": f"工作目录不存在：{workdir}",
        }

    infer_path = _build_infer_config(values)
    cmd = [
        python_path,
        api_script,
        "-a",
        "127.0.0.1",
        "-p",
        str(port),
        "-c",
        infer_path,
    ]

    try:
        log_file = open(DATA_DIR / "server.log", "a", encoding="utf-8")
        _process = subprocess.Popen(
            cmd,
            cwd=workdir,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("gptsovits: failed to start server")
        _process = None
        return {"ok": False, "message": f"启动 GPT-SoVITS 失败：{exc}"}

    return {
        "ok": True,
        "running": True,
        "pid": _process.pid,
        "port": port,
        "message": f"GPT-SoVITS 启动中（端口 {port}），模型加载需要一些时间",
    }


def _stop_server() -> dict:
    global _process
    if _process is None:
        return {"ok": True, "running": False, "message": "GPT-SoVITS 服务未运行"}
    try:
        _process.terminate()
        try:
            _process.wait(timeout=8)
        except subprocess.TimeoutExpired:
            _process.kill()
    except Exception:  # noqa: BLE001
        pass
    _process = None
    return {"ok": True, "running": False, "message": "GPT-SoVITS 服务已停止"}


# ---------------------------------------------------------------------------
# Handlers (Plugin OpenAPI)
# ---------------------------------------------------------------------------


def handle_status(query: dict, body: dict) -> dict:
    values = _read_values()
    port = values.get("server_port", "9880") or "9880"
    running = _server_running()
    return {
        "running": running,
        "pid": _process.pid if running else None,
        "port": port,
        "ready": _port_open(port) if running else False,
        "version": values.get("version"),
        "ref_audio_path": values.get("ref_audio_path", ""),
        "text_lang": values.get("text_lang", "zh"),
        "hint": "模型加载可能需要几十秒，加载完成后 ready 变为 true",
    }


def handle_start(query: dict, body: dict) -> dict:
    return _start_server()


def handle_stop(query: dict, body: dict) -> dict:
    return _stop_server()


def handle_voices(query: dict, body: dict) -> dict:
    values = _read_values()
    presets = _parse_voice_list(values.get("voice_list_path", ""))
    return {
        "list_path": values.get("voice_list_path", ""),
        "voices": presets,
        "count": len(presets),
    }


def get_plugin_api() -> PluginAPI:
    return PluginAPI(
        endpoints=(
            PluginEndpoint(
                method="GET",
                path="/status",
                summary="服务状态",
                description="GPT-SoVITS 子进程是否在运行、端口是否就绪",
            ),
            PluginEndpoint(
                method="POST",
                path="/start",
                summary="启动服务",
                description="启动本地 GPT-SoVITS api_v2.py（使用微调好的权重）",
            ),
            PluginEndpoint(
                method="POST",
                path="/stop",
                summary="停止服务",
                description="停止本地 GPT-SoVITS 子进程",
            ),
            PluginEndpoint(
                method="GET",
                path="/voices",
                summary="音色列表",
                description="解析 voice_list_path 中的参考音频与转录，返回可选的音色预设",
            ),
        ),
        handlers={
            "GET /status": handle_status,
            "POST /start": handle_start,
            "POST /stop": handle_stop,
            "GET /voices": handle_voices,
        },
    )
