"""Tests for text-to-speech routes."""

from __future__ import annotations

from fastapi.testclient import TestClient

from src.chitrika.services.tts_service import _speech_url


def test_speech_url_accepts_base_or_endpoint():
    assert _speech_url("https://api.openai.com/v1") == "https://api.openai.com/v1/audio/speech"
    assert _speech_url("https://api.openai.com") == "https://api.openai.com/v1/audio/speech"
    assert _speech_url("https://api.openai.com/v1/audio/speech") == "https://api.openai.com/v1/audio/speech"


def test_synthesize_tts_returns_audio(client: TestClient, monkeypatch):
    def fake_synthesize(request):
        assert request.text == "hello"
        assert request.api_key == "test-key"
        assert request.model == "gpt-4o-mini-tts"
        assert request.voice == "alloy"
        return b"audio-bytes", "audio/mpeg"

    monkeypatch.setattr("src.chitrika.routes.tts_routes.synthesize_speech", fake_synthesize)

    resp = client.post(
        "/api/tts/synthesize",
        json={
            "text": "hello",
            "api_key": "test-key",
            "base_url": "https://api.openai.com/v1",
            "model": "gpt-4o-mini-tts",
            "voice": "alloy",
            "speed": 1,
        },
    )

    assert resp.status_code == 200
    assert resp.headers["content-type"] == "audio/mpeg"
    assert resp.content == b"audio-bytes"


def test_synthesize_tts_requires_credentials(client: TestClient):
    resp = client.post(
        "/api/tts/synthesize",
        json={"text": "hello", "api_key": ""},
    )

    assert resp.status_code == 422


def test_synthesize_gptsovits_returns_wav(client: TestClient, monkeypatch):
    def fake_synthesize(request):
        assert request.provider == "gptsovits"
        assert request.ref_audio_path.endswith(".wav")
        assert request.prompt_text
        assert request.text_lang == "zh"
        return b"RIFFwavbytes", "audio/wav"

    monkeypatch.setattr("src.chitrika.routes.tts_routes.synthesize_speech", fake_synthesize)

    resp = client.post(
        "/api/tts/synthesize",
        json={
            "provider": "gptsovits",
            "text": "你好呀",
            "base_url": "http://127.0.0.1:9880",
            "ref_audio_path": "D:\\voice_abc.wav",
            "prompt_text": "你好",
            "text_lang": "zh",
            "prompt_lang": "zh",
        },
    )

    assert resp.status_code == 200
    assert resp.headers["content-type"] == "audio/wav"
    assert resp.content == b"RIFFwavbytes"


def test_synthesize_gptsovits_strips_v1_suffix(monkeypatch):
    """A leftover /v1 (OpenAI-style) base_url must not break the native /tts call."""
    from src.chitrika.services import tts_service
    from src.chitrika.schemas.tts_schemas import TTSRequest

    captured: dict = {}

    class FakeResponse:
        is_error = False
        content = b"RIFFwavbytes"

        @property
        def headers(self):
            return {"content-type": "audio/wav"}

    def fake_post(url, **kwargs):
        captured["url"] = url
        return FakeResponse()

    monkeypatch.setattr(tts_service.httpx, "post", fake_post)

    request = TTSRequest(
        provider="gptsovits",
        text="你好",
        base_url="http://127.0.0.1:9880/v1",
        ref_audio_path="D:\\voice_abc.wav",
        prompt_text="你好",
    )
    audio, content_type = tts_service.synthesize_speech(request)

    assert captured["url"] == "http://127.0.0.1:9880/tts"
    assert audio == b"RIFFwavbytes"
    assert content_type == "audio/wav"


def test_synthesize_gptsovits_requires_ref_audio(client: TestClient):
    resp = client.post(
        "/api/tts/synthesize",
        json={"provider": "gptsovits", "text": "hello"},
    )

    assert resp.status_code == 422


def test_resolve_gptsovits_prompt_auto_fills(monkeypatch, tmp_path):
    """prompt_text auto-resolves from the voice list when not supplied."""
    from src.chitrika.services import tts_service
    from src.chitrika.schemas.tts_schemas import TTSRequest

    list_file = tmp_path / "voices.list"
    list_file.write_text(
        r"D:\voice_abc.wav|0624xyt|ZH|这是一个参考文本" + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(tts_service, "_gptsovits_voice_list_path", lambda: str(list_file))

    request = TTSRequest(
        provider="gptsovits",
        text="你好",
        ref_audio_path="D:\\voice_abc.wav",
    )
    prompt_text, prompt_lang = tts_service._resolve_gptsovits_prompt(request)

    assert prompt_text == "这是一个参考文本"
    assert prompt_lang == "zh"


def test_resolve_gptsovits_prompt_prefers_explicit(monkeypatch, tmp_path):
    """A caller-supplied prompt_text wins over auto-resolution."""
    from src.chitrika.services import tts_service
    from src.chitrika.schemas.tts_schemas import TTSRequest

    request = TTSRequest(
        provider="gptsovits",
        text="你好",
        ref_audio_path="D:\\voice_abc.wav",
        prompt_text="用户自定文本",
        prompt_lang="zh",
    )
    prompt_text, prompt_lang = tts_service._resolve_gptsovits_prompt(request)

    assert prompt_text == "用户自定文本"
