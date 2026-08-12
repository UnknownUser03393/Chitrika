"""Tests for the ONNX emotion classifier adapter."""

from __future__ import annotations

from pathlib import Path

from src.chitrika.utils import emotion_onnx


def test_wordpiece_encoder_handles_cjk_and_padding(tmp_path: Path):
    vocab = {
        "[PAD]": 0,
        "[UNK]": 1,
        "[CLS]": 2,
        "[SEP]": 3,
        "用": 4,
        "户": 5,
        "：": 6,
        "想": 7,
        "你": 8,
    }

    encoded = emotion_onnx._encode_wordpiece("用户：想你", vocab, max_length=10)

    assert encoded["input_ids"][:6] == [2, 4, 5, 6, 7, 8]
    assert encoded["input_ids"][6] == 3
    assert encoded["attention_mask"] == [1, 1, 1, 1, 1, 1, 1, 0, 0, 0]
    assert encoded["token_type_ids"] == [0] * 10


def test_target_emotion_text_prefers_assistant_reply():
    assert emotion_onnx._target_emotion_text("我吓哭了", "我保护你") == "我保护你"
    assert emotion_onnx._target_emotion_text("我吓哭了", "") == "我吓哭了"


def test_probability_to_delta_ignores_below_threshold_scores():
    assert emotion_onnx._probability_to_delta(0.34, threshold=0.35) == 0.0
    assert emotion_onnx._probability_to_delta(0.35, threshold=0.35) == 0.0
    assert emotion_onnx._probability_to_delta(1.0, threshold=0.35) == 0.2


def test_missing_onnx_model_returns_none(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(emotion_onnx.config, "emotion_classifier_model_dir", str(tmp_path / "missing"))
    monkeypatch.setattr(emotion_onnx, "_CLASSIFIER", None)
    monkeypatch.setattr(emotion_onnx, "_LOAD_FAILED", False)

    result = emotion_onnx.classify_with_onnx_if_available("想你", "我也想你")

    assert result is None
