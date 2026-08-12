"""Local sentence-embedding adapter for semantic memory recall.

Mirrors the emotion ONNX adapter (``emotion_onnx.py``): a lazily-loaded
singleton that runs a local sentence-transformer via ONNX Runtime on CPU, so
memory recall costs nothing per message and needs no network.

Expected model directory (see ``scripts/export_embedding_onnx.py``):
- model.onnx
- tokenizer.json
- embedding_config.json  (optional: max_length, normalize)

When no model is configured or it fails to load, ``embed`` returns ``None`` and
callers fall back to importance-only retrieval — so the feature degrades
gracefully rather than breaking chat.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from src.chitrika.config import config

logger = logging.getLogger("chitrika.memory.embedding")

DEFAULT_MAX_LENGTH = 256

_EMBEDDER: "MemoryEmbedder | None" = None
_LOAD_FAILED = False


class MemoryEmbedder:
    """Run a local ONNX sentence encoder and return a normalized vector."""

    def __init__(self, model_dir: str | Path):
        self.model_dir = Path(model_dir).expanduser().resolve()
        self.model_path = self.model_dir / "model.onnx"
        self.tokenizer_path = self.model_dir / "tokenizer.json"
        self.config_path = self.model_dir / "embedding_config.json"

        if not self.model_path.is_file():
            raise FileNotFoundError(f"Embedding model not found: {self.model_path}")
        if not self.tokenizer_path.is_file():
            raise FileNotFoundError(f"Embedding tokenizer not found: {self.tokenizer_path}")

        self.config = self._load_config()
        self.max_length = int(self.config.get("max_length", DEFAULT_MAX_LENGTH))
        self.normalize = bool(self.config.get("normalize", True))

        from tokenizers import Tokenizer

        self.tokenizer = Tokenizer.from_file(str(self.tokenizer_path))
        self.tokenizer.enable_truncation(max_length=self.max_length)
        self.tokenizer.enable_padding(length=self.max_length)

        import onnxruntime as ort

        self.session = ort.InferenceSession(
            str(self.model_path),
            providers=["CPUExecutionProvider"],
        )
        self.input_names = {item.name for item in self.session.get_inputs()}
        self.output_names = [item.name for item in self.session.get_outputs()]

    def embed(self, text: str):
        """Return a 1-D float32 numpy vector for *text* (normalized by default)."""
        import numpy as np

        text = (text or "").strip()
        if not text:
            return None

        encoded = self.tokenizer.encode(text)
        attention_mask = list(encoded.attention_mask)

        feeds: dict[str, Any] = {}
        if "input_ids" in self.input_names:
            feeds["input_ids"] = np.array([encoded.ids], dtype=np.int64)
        if "attention_mask" in self.input_names:
            feeds["attention_mask"] = np.array([attention_mask], dtype=np.int64)
        if "token_type_ids" in self.input_names:
            type_ids = encoded.type_ids or [0] * len(encoded.ids)
            feeds["token_type_ids"] = np.array([type_ids], dtype=np.int64)

        outputs = self.session.run(None, feeds)
        vector = self._pool(outputs, np.array(attention_mask, dtype=np.float32), np)
        if self.normalize:
            norm = float(np.linalg.norm(vector))
            if norm > 0:
                vector = vector / norm
        return vector.astype(np.float32)

    def _pool(self, outputs: list, mask, np):
        """Reduce model outputs to a single sentence vector.

        Prefers a pre-pooled 2-D output (e.g. ``sentence_embedding`` /
        ``pooler_output``); otherwise mean-pools token embeddings over the
        attention mask.
        """
        # Pick a pre-pooled output if the model exposes one.
        for name, out in zip(self.output_names, outputs):
            arr = np.asarray(out)
            if arr.ndim == 2 and name.lower() in {"sentence_embedding", "pooler_output", "embeddings"}:
                return arr[0].astype(np.float32)

        # Otherwise mean-pool the first 3-D output (batch, seq, hidden).
        for out in outputs:
            arr = np.asarray(out, dtype=np.float32)
            if arr.ndim == 3:
                tokens = arr[0]  # (seq, hidden)
                weights = mask[: tokens.shape[0], None]
                summed = (tokens * weights).sum(axis=0)
                denom = max(float(weights.sum()), 1e-9)
                return summed / denom

        # Fallback: first output squeezed to 1-D.
        return np.asarray(outputs[0], dtype=np.float32).reshape(-1)

    def _load_config(self) -> dict[str, Any]:
        if not self.config_path.is_file():
            return {}
        try:
            data = json.loads(self.config_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return data if isinstance(data, dict) else {}


def vector_to_bytes(vector) -> bytes:
    """Serialize a numpy float32 vector to bytes for DB storage."""
    import numpy as np

    return np.asarray(vector, dtype=np.float32).tobytes()


def vector_from_bytes(buffer: bytes | None):
    """Deserialize DB bytes back into a numpy float32 vector, or None."""
    if not buffer:
        return None
    import numpy as np

    return np.frombuffer(buffer, dtype=np.float32)


def cosine_similarity(a, b) -> float:
    """Cosine similarity between two vectors (0 when either is degenerate)."""
    import numpy as np

    va = np.asarray(a, dtype=np.float32)
    vb = np.asarray(b, dtype=np.float32)
    denom = float(np.linalg.norm(va) * np.linalg.norm(vb))
    if denom <= 1e-9:
        return 0.0
    return float(np.dot(va, vb) / denom)


def embed_text(text: str):
    """Embed *text* with the local model, or return None when unavailable."""
    embedder = _get_embedder()
    if embedder is None:
        return None
    try:
        return embedder.embed(text)
    except Exception:
        logger.exception("Embedding failed for text of length %d", len(text or ""))
        return None


def embedding_available() -> bool:
    """True when a local embedding model is loaded and ready."""
    return _get_embedder() is not None


def _get_embedder() -> MemoryEmbedder | None:
    global _EMBEDDER, _LOAD_FAILED
    if _EMBEDDER is not None:
        return _EMBEDDER
    if _LOAD_FAILED:
        return None

    model_dir = Path(config.embedding_model_dir)
    if not model_dir.is_dir():
        _LOAD_FAILED = True
        logger.info("Embedding model directory not found (semantic recall disabled): %s", model_dir)
        return None

    try:
        _EMBEDDER = MemoryEmbedder(model_dir)
    except Exception:
        _LOAD_FAILED = True
        logger.exception("Failed to load embedding model from %s", model_dir)
        return None
    return _EMBEDDER
