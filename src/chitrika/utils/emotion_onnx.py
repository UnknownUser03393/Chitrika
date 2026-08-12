"""ONNX Runtime emotion classifier adapter.

Expected model directory:
- model.onnx
- tokenizer.json or vocab.txt
- emotion_config.json
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from src.chitrika.config import config
from src.chitrika.utils.emotion_algorithms import DIMENSIONS, clamp

logger = logging.getLogger("chitrika.emotion.onnx")

DEFAULT_LABELS = list(DIMENSIONS)
DEFAULT_MAX_LENGTH = 192
DEFAULT_LABEL_MAP: dict[str, dict[str, float]] = {
    "anger": {"anger": 1.0},
    "contempt": {"disgust": 0.7, "anger": 0.3},
    "disgust": {"disgust": 1.0},
    "fear": {"fear": 1.0},
    "frustration": {"anger": 0.6, "sadness": 0.3, "disgust": 0.1},
    "gratitude": {"trust": 0.7, "joy": 0.3},
    "joy": {"joy": 1.0},
    "love": {"trust": 0.6, "joy": 0.3, "anticipation": 0.1},
    "neutral": {},
    "sadness": {"sadness": 1.0},
    "surprise": {"surprise": 1.0},
}

_CLASSIFIER: "EmotionONNXClassifier | None" = None
_LOAD_FAILED = False


class EmotionONNXClassifier:
    """Run a local ONNX text classifier and map scores to emotion deltas."""

    def __init__(self, model_dir: str | Path):
        self.model_dir = Path(model_dir).expanduser().resolve()
        self.model_path = self.model_dir / "model.onnx"
        self.tokenizer_path = self.model_dir / "tokenizer.json"
        self.vocab_path = self.model_dir / "vocab.txt"
        self.config_path = self.model_dir / "emotion_config.json"

        if not self.model_path.is_file():
            raise FileNotFoundError(f"ONNX model not found: {self.model_path}")
        if not self.tokenizer_path.is_file() and not self.vocab_path.is_file():
            raise FileNotFoundError(
                f"ONNX tokenizer not found: expected {self.tokenizer_path} or {self.vocab_path}"
            )

        self.config = self._load_config()
        self.labels = self._labels()
        self.label_map = self._label_map()
        self.max_length = int(self.config.get("max_length", DEFAULT_MAX_LENGTH))
        self.multilabel = bool(self.config.get("multilabel", True))
        self.threshold = float(self.config.get("threshold", 0.35))
        self.tokenizer = self._load_tokenizer()
        self.vocab = None if self.tokenizer is not None else _load_vocab(self.vocab_path)

        import onnxruntime as ort

        self.session = ort.InferenceSession(
            str(self.model_path),
            providers=["CPUExecutionProvider"],
        )
        self.input_names = {item.name for item in self.session.get_inputs()}
        self.output_name = self.session.get_outputs()[0].name

    def classify(self, user_text: str, assistant_text: str = "") -> dict[str, float]:
        text = _target_emotion_text(user_text, assistant_text)
        encoded = self._encode(text)
        feeds = self._feeds(encoded)
        output = self.session.run([self.output_name], feeds)[0]
        scores = _flatten_scores(output)
        probabilities = _sigmoid(scores) if self.multilabel else _softmax(scores)

        deltas = {dim: 0.0 for dim in DIMENSIONS}
        delta_by_label: dict[str, dict[str, float]] = {}
        for index, label in enumerate(self.labels):
            if index >= len(probabilities):
                continue
            delta = _probability_to_delta(probabilities[index], self.threshold)
            if delta <= 0:
                continue
            label_delta: dict[str, float] = {}
            for dim, weight in self.label_map.get(label, {}).items():
                if dim in deltas:
                    contribution = delta * float(weight)
                    deltas[dim] += contribution
                    label_delta[dim] = round(contribution, 4)
            if label_delta:
                delta_by_label[label] = label_delta

        result = {
            dim: round(clamp(value, -0.2, 0.2), 4)
            for dim, value in deltas.items()
            if abs(value) >= 0.001
        }
        _publish_debug_event(
            source="onnx",
            model_dir=str(self.model_dir),
            user_text=user_text,
            assistant_text=assistant_text,
            labels=self.labels,
            probabilities=probabilities,
            deltas=result,
            delta_by_label=delta_by_label,
        )
        return result

    def _load_config(self) -> dict[str, Any]:
        if not self.config_path.is_file():
            return {}
        data = json.loads(self.config_path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}

    def _labels(self) -> list[str]:
        labels = self.config.get("labels", DEFAULT_LABELS)
        if not isinstance(labels, list):
            return DEFAULT_LABELS
        return [str(label) for label in labels]

    def _label_map(self) -> dict[str, dict[str, float]]:
        raw = self.config.get("label_map", DEFAULT_LABEL_MAP)
        if not isinstance(raw, dict):
            return DEFAULT_LABEL_MAP
        parsed: dict[str, dict[str, float]] = {}
        for label, mapping in raw.items():
            if not isinstance(mapping, dict):
                continue
            parsed[str(label)] = {
                str(dim): float(weight)
                for dim, weight in mapping.items()
                if str(dim) in DIMENSIONS
            }
        return parsed

    def _load_tokenizer(self):
        if not self.tokenizer_path.is_file():
            return None
        from tokenizers import Tokenizer

        tokenizer = Tokenizer.from_file(str(self.tokenizer_path))
        tokenizer.enable_truncation(max_length=self.max_length)
        tokenizer.enable_padding(length=self.max_length)
        return tokenizer

    def _encode(self, text: str) -> dict[str, list[int]]:
        if self.tokenizer is not None:
            encoded = self.tokenizer.encode(text)
            token_type_ids = encoded.type_ids or [0] * len(encoded.ids)
            return {
                "input_ids": encoded.ids,
                "attention_mask": encoded.attention_mask,
                "token_type_ids": token_type_ids,
            }
        assert self.vocab is not None
        return _encode_wordpiece(text, self.vocab, self.max_length)

    def _feeds(self, encoded: dict[str, list[int]]):
        import numpy as np

        feeds = {}
        if "input_ids" in self.input_names:
            feeds["input_ids"] = np.array([encoded["input_ids"]], dtype=np.int64)
        if "attention_mask" in self.input_names:
            feeds["attention_mask"] = np.array([encoded["attention_mask"]], dtype=np.int64)
        if "token_type_ids" in self.input_names:
            feeds["token_type_ids"] = np.array([encoded["token_type_ids"]], dtype=np.int64)
        return feeds


def _publish_debug_event(
    *,
    source: str,
    model_dir: str,
    user_text: str,
    assistant_text: str,
    labels: list[str],
    probabilities: list[float],
    deltas: dict[str, float],
    delta_by_label: dict[str, dict[str, float]],
) -> None:
    try:
        from src.chitrika.services.emotion_debug_panel import (
            EmotionDebugEvent,
            publish_emotion_debug_event,
        )

        publish_emotion_debug_event(
            EmotionDebugEvent(
                source=source,
                model_dir=model_dir,
                user_text=user_text,
                assistant_text=assistant_text,
                labels=labels,
                probabilities=probabilities,
                deltas=deltas,
                metadata={"delta_by_label": delta_by_label},
            )
        )
    except Exception:
        logger.exception("Failed to publish emotion debug event")


def classify_with_onnx_if_available(
    user_text: str,
    assistant_text: str = "",
) -> dict[str, float] | None:
    """Return ONNX emotion deltas when a local model is configured and loadable."""
    classifier = _get_classifier()
    if classifier is None:
        return None
    return classifier.classify(user_text, assistant_text)


def _get_classifier() -> EmotionONNXClassifier | None:
    global _CLASSIFIER, _LOAD_FAILED
    if _CLASSIFIER is not None:
        return _CLASSIFIER
    if _LOAD_FAILED:
        return None

    model_dir = Path(config.emotion_classifier_model_dir)
    if not model_dir.is_dir():
        _LOAD_FAILED = True
        logger.error("Emotion ONNX model directory not found: %s", model_dir)
        return None

    try:
        _CLASSIFIER = EmotionONNXClassifier(model_dir)
    except Exception:
        _LOAD_FAILED = True
        logger.exception("Failed to load emotion ONNX classifier from %s", model_dir)
        return None
    return _CLASSIFIER


def _load_vocab(path: Path) -> dict[str, int]:
    vocab: dict[str, int] = {}
    for index, token in enumerate(path.read_text(encoding="utf-8").splitlines()):
        token = token.strip()
        if token:
            vocab[token] = index
    return vocab


def _target_emotion_text(user_text: str, assistant_text: str) -> str:
    target = assistant_text.strip()
    if target:
        return target
    return user_text.strip()


def _encode_wordpiece(text: str, vocab: dict[str, int], max_length: int) -> dict[str, list[int]]:
    tokens = ["[CLS]"] + _tokenize(text, vocab)[: max_length - 2] + ["[SEP]"]
    pad_id = vocab.get("[PAD]", 0)
    input_ids = [vocab.get(token, vocab.get("[UNK]", 1)) for token in tokens]
    attention_mask = [1] * len(input_ids)
    token_type_ids = [0] * len(input_ids)

    padding = max_length - len(input_ids)
    if padding > 0:
        input_ids.extend([pad_id] * padding)
        attention_mask.extend([0] * padding)
        token_type_ids.extend([0] * padding)

    return {
        "input_ids": input_ids,
        "attention_mask": attention_mask,
        "token_type_ids": token_type_ids,
    }


def _tokenize(text: str, vocab: dict[str, int]) -> list[str]:
    tokens: list[str] = []
    for word in _basic_tokenize(text):
        if word in vocab:
            tokens.append(word)
            continue
        tokens.extend(_wordpiece(word, vocab))
    return tokens


def _basic_tokenize(text: str) -> list[str]:
    tokens: list[str] = []
    current = ""
    for char in text.strip().lower():
        code = ord(char)
        if char.isspace():
            if current:
                tokens.append(current)
                current = ""
        elif _is_cjk(code):
            if current:
                tokens.append(current)
                current = ""
            tokens.append(char)
        elif char.isalnum() or char in {"_", "-"}:
            current += char
        else:
            if current:
                tokens.append(current)
                current = ""
            tokens.append(char)
    if current:
        tokens.append(current)
    return tokens


def _is_cjk(code: int) -> bool:
    return (
        0x4E00 <= code <= 0x9FFF
        or 0x3400 <= code <= 0x4DBF
        or 0x20000 <= code <= 0x2A6DF
    )


def _wordpiece(word: str, vocab: dict[str, int]) -> list[str]:
    if len(word) > 100:
        return ["[UNK]"]
    pieces: list[str] = []
    start = 0
    while start < len(word):
        end = len(word)
        current = None
        while start < end:
            piece = word[start:end] if start == 0 else f"##{word[start:end]}"
            if piece in vocab:
                current = piece
                break
            end -= 1
        if current is None:
            return ["[UNK]"]
        pieces.append(current)
        start = end
    return pieces


def _flatten_scores(output) -> list[float]:
    if hasattr(output, "tolist"):
        data = output.tolist()
    else:
        data = output
    while isinstance(data, list) and data and isinstance(data[0], list):
        data = data[0]
    return [float(item) for item in data]


def _sigmoid(scores: list[float]) -> list[float]:
    import math

    return [1.0 / (1.0 + math.exp(-score)) for score in scores]


def _softmax(scores: list[float]) -> list[float]:
    import math

    if not scores:
        return []
    peak = max(scores)
    exps = [math.exp(score - peak) for score in scores]
    total = sum(exps)
    return [value / total for value in exps]


def _probability_to_delta(probability: float, threshold: float = 0.35) -> float:
    if probability <= threshold:
        return 0.0
    return (probability - threshold) / (1.0 - threshold) * 0.2
