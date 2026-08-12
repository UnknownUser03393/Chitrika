"""OpenAI-compatible text-to-speech client."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from urllib.parse import urljoin

import httpx

from src.chitrika.schemas.tts_schemas import TTSRequest

logger = logging.getLogger("chitrika.tts")


class TTSError(RuntimeError):
    """Raised when an upstream TTS provider rejects a request."""


def _speech_url(base_url: str) -> str:
    stripped = base_url.rstrip("/")
    if stripped.endswith("/audio/speech"):
        return stripped

    normalized = stripped + "/"
    if normalized.endswith("/v1/"):
        return urljoin(normalized, "audio/speech")
    return urljoin(normalized, "v1/audio/speech")


def synthesize_speech(request: TTSRequest) -> tuple[bytes, str]:
    """Synthesize speech, dispatching on the selected provider."""
    if request.provider == "gptsovits":
        return _synthesize_gptsovits(request)
    return _synthesize_openai(request)


def _synthesize_openai(request: TTSRequest) -> tuple[bytes, str]:
    """Synthesize speech through an OpenAI-compatible audio endpoint."""
    payload = {
        "model": request.model,
        "input": request.text,
        "voice": request.voice,
        "response_format": request.response_format,
        "speed": request.speed,
    }

    try:
        response = httpx.post(
            _speech_url(request.base_url),
            headers={"Authorization": f"Bearer {request.api_key}"},
            json=payload,
            timeout=60.0,
        )
    except httpx.HTTPError as exc:
        raise TTSError(f"TTS provider unavailable: {exc}") from exc

    if response.is_error:
        detail = response.text[:500] or f"HTTP {response.status_code}"
        raise TTSError(f"TTS provider error: {detail}")

    content_type = response.headers.get("content-type", "audio/mpeg")
    return response.content, content_type


def _resolve_gptsovits_prompt(request: TTSRequest) -> tuple[str, str]:
    """Return (prompt_text, prompt_lang) for a GPT-SoVITS request.

    Prefers the caller-supplied values; when ``prompt_text`` is empty it is
    resolved automatically from the gptsovits plugin's voice reference list by
    matching ``ref_audio_path``.
    """
    if request.prompt_text.strip():
        return request.prompt_text, request.prompt_lang

    list_path = _gptsovits_voice_list_path()
    for preset in _parse_gptsovits_list(list_path):
        if preset["ref_audio_path"] == request.ref_audio_path:
            return preset["prompt_text"], preset.get("prompt_lang") or request.prompt_lang
    return "", request.prompt_lang


def _gptsovits_voice_list_path() -> str:
    """Read the gptsovits plugin's configured voice list path (if any)."""
    try:
        from src.chitrika.config import config

        plugin_dir = Path(config.plugins_dir) / "gptsovits"
        cfg_file = plugin_dir / "data" / "config.json"
        if cfg_file.is_file():
            data = json.loads(cfg_file.read_text(encoding="utf-8"))
            value = data.get("voice_list_path") if isinstance(data, dict) else None
            if isinstance(value, str) and value.strip():
                return value.strip()
    except Exception:
        logger.warning("gptsovits: failed to read plugin config for voice list", exc_info=True)
    # Built-in default matches the plugin's DEFAULT_VALUES.
    return r"D:\Development\0624xyt_GPTSoVITS\0624xyt.list"


def _parse_gptsovits_list(list_path: str) -> list[dict]:
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
        presets.append(
            {
                "ref_audio_path": parts[0],
                "prompt_text": "|".join(parts[3:]).strip(),
                "prompt_lang": parts[2].lower() or "zh",
            }
        )
    return presets


def _synthesize_gptsovits(request: TTSRequest) -> tuple[bytes, str]:
    """Synthesize speech through a local GPT-SoVITS ``/tts`` endpoint.

    Returns raw wav bytes. ``base_url`` points at the GPT-SoVITS server
    (e.g. ``http://127.0.0.1:9880``).
    """
    base = request.base_url.rstrip("/")
    # Tolerate a leftover "/v1" suffix (e.g. an OpenAI-style URL that was
    # reused for a local GPT-SoVITS server) — its /tts endpoint is at the root.
    if base.endswith("/v1"):
        base = base[: -len("/v1")]
    url = f"{base}/tts"

    prompt_text, prompt_lang = _resolve_gptsovits_prompt(request)

    payload = {
        "text": request.text,
        "text_lang": request.text_lang,
        "ref_audio_path": request.ref_audio_path,
        "prompt_text": prompt_text,
        "prompt_lang": prompt_lang,
        "speed_factor": request.speed,
        "media_type": "wav",
        "streaming_mode": False,
    }

    try:
        response = httpx.post(url, json=payload, timeout=120.0)
    except httpx.HTTPError as exc:
        raise TTSError(f"GPT-SoVITS unavailable: {exc}") from exc

    if response.is_error:
        detail = response.text[:500] or f"HTTP {response.status_code}"
        raise TTSError(f"GPT-SoVITS error: {detail}")

    return response.content, "audio/wav"
