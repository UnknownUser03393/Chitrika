"""Download Chitrika's ONNX models from Hugging Face Hub.

Models are large (emotion ~1.1 GB, embedding ~470 MB) so they are not
committed to git. This script ensures they exist under ``models/`` and
downloads any missing files from Hugging Face.

Usage:
    uv run python scripts/download_models.py
    # or with a custom HF repo / private repos:
    CHITRIKA_EMOTION_MODEL_REPO=your-user/emotion-onnx \\
    CHITRIKA_EMBEDDING_MODEL_REPO=your-user/embedding-onnx \\
    uv run python scripts/download_models.py
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Set your own repo ids via env or CLI args. The defaults match the upstream
# Chitrika repos; change them if you forked or made the repos private.
DEFAULT_EMOTION_REPO = os.environ.get(
    "CHITRIKA_EMOTION_MODEL_REPO", "chitrika/emotion-onnx"
)
DEFAULT_EMBEDDING_REPO = os.environ.get(
    "CHITRIKA_EMBEDDING_MODEL_REPO", "chitrika/embedding-onnx"
)

# Required files per model dir. If any are missing the whole dir is refreshed.
MODEL_SPECS = {
    "emotion": {
        "dir": "models/emotion",
        "repo": DEFAULT_EMOTION_REPO,
        "files": [
            "model.onnx",
            "tokenizer.json",
            "emotion_config.json",
            "tokenizer_config.json",
        ],
    },
    "embedding": {
        "dir": "models/embedding",
        "repo": DEFAULT_EMBEDDING_REPO,
        "files": [
            "model.onnx",
            "tokenizer.json",
            "sentencepiece.bpe.model",
            "embedding_config.json",
            "special_tokens_map.json",
            "tokenizer_config.json",
        ],
    },
}


def _ensure_huggingface_hub() -> None:
    try:
        import huggingface_hub  # noqa: F401
    except ImportError:
        sys.exit(
            "huggingface_hub is not installed. Run:  uv pip install huggingface_hub"
        )


def _download(spec: dict) -> None:
    from huggingface_hub import snapshot_download

    model_dir = PROJECT_ROOT / spec["dir"]
    model_dir.mkdir(parents=True, exist_ok=True)
    missing = [
        name for name in spec["files"] if not (model_dir / name).is_file()
    ]
    if not missing and not args.force:
        print(f"[{spec['repo']}] {model_dir.relative_to(PROJECT_ROOT)}: ok, nothing to do")
        return

    reason = "forced refresh" if args.force else f"missing {', '.join(missing)}"
    print(f"[{spec['repo']}] {model_dir.relative_to(PROJECT_ROOT)}: {reason}, downloading…")
    snapshot_download(
        repo_id=spec["repo"],
        local_dir=model_dir,
        allow_patterns=spec["files"],
    )
    print(f"[{spec['repo']}] done.")


def main() -> None:
    global args
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--emotion-repo",
        default=DEFAULT_EMOTION_REPO,
        help="HF repo for the emotion ONNX model (default: %(default)s)",
    )
    parser.add_argument(
        "--embedding-repo",
        default=DEFAULT_EMBEDDING_REPO,
        help="HF repo for the embedding ONNX model (default: %(default)s)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-download even when all files already exist",
    )
    args = parser.parse_args()

    MODEL_SPECS["emotion"]["repo"] = args.emotion_repo
    MODEL_SPECS["embedding"]["repo"] = args.embedding_repo

    _ensure_huggingface_hub()
    for spec in MODEL_SPECS.values():
        _download(spec)


if __name__ == "__main__":
    main()
