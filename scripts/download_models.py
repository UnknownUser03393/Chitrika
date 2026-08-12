"""Download Chitrika's ONNX models from Hugging Face Hub.

Models are large (emotion ~1.1 GB, embedding ~470 MB) so they are not
committed to git. This script ensures they exist under ``models/`` and
downloads any missing files from Hugging Face.

Files are fetched by direct ``resolve`` URL with resumable chunked downloads
(no dependency on the ``huggingface_hub`` package, whose API listing is not
served by the mainland-China mirror). If the direct endpoint fails, the file is
retried through the official mirror ``hf-mirror.com``.

Usage:
    uv run python scripts/download_models.py
    # or with a custom HF repo:
    CHITRIKA_EMOTION_MODEL_REPO=your-user/emotion-onnx \\
    uv run python scripts/download_models.py
"""

from __future__ import annotations

import argparse
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_EMOTION_REPO = os.environ.get(
    "CHITRIKA_EMOTION_MODEL_REPO", "NeatAvocado14/emotion-onnx"
)
DEFAULT_EMBEDDING_REPO = os.environ.get(
    "CHITRIKA_EMBEDDING_MODEL_REPO", "NeatAvocado14/embedding-onnx"
)
DIRECT_ENDPOINT = "https://huggingface.co"
MIRROR_ENDPOINT = os.environ.get("HF_ENDPOINT", "https://hf-mirror.com").rstrip("/")

# Required files per model dir. If any are missing the whole dir is refreshed.
MODEL_SPECS = {
    "emotion": {
        "dir": "models/emotion",
        "files": [
            "model.onnx",
            "tokenizer.json",
            "emotion_config.json",
            "tokenizer_config.json",
        ],
    },
    "embedding": {
        "dir": "models/embedding",
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

_CHUNK = 1 << 16  # 64 KiB


def ensure_models(
    *,
    force: bool = False,
    emotion_repo: str | None = None,
    embedding_repo: str | None = None,
) -> None:
    """Ensure both ONNX model dirs exist, downloading any missing files.

    Raises RuntimeError if a download ultimately fails, so callers (e.g.
    ``chitrika_autodownload.py``) can react.
    """
    repos = {
        "emotion": emotion_repo or DEFAULT_EMOTION_REPO,
        "embedding": embedding_repo or DEFAULT_EMBEDDING_REPO,
    }
    for name, spec in MODEL_SPECS.items():
        _download_spec(name, repos[name], spec, force=force)


def _download_spec(name: str, repo: str, spec: dict, *, force: bool) -> None:
    model_dir = PROJECT_ROOT / spec["dir"]
    model_dir.mkdir(parents=True, exist_ok=True)
    missing = [
        fname for fname in spec["files"] if not (model_dir / fname).is_file()
    ]
    if not missing and not force:
        print(f"[{repo}] {spec['dir']}: ok, nothing to do")
        return

    reason = "forced refresh" if force else f"missing {', '.join(missing)}"
    print(f"[{repo}] {spec['dir']}: {reason}, downloading…")
    for fname in spec["files"]:
        if (model_dir / fname).is_file() and not force:
            continue
        _download_file(repo, fname, model_dir / fname)
    print(f"[{repo}] {spec['dir']}: done.")


def _download_file(repo: str, fname: str, dest: Path) -> None:
    """Download a single known file, direct then mirror, with resume."""
    errors: list[str] = []
    for endpoint in _endpoints():
        url = f"{endpoint}/{repo}/resolve/main/{fname}"
        try:
            _stream_download(url, dest)
            print(f"    {fname}: ok")
            return
        except Exception as exc:  # noqa: BLE001 — report and try next endpoint
            errors.append(f"{endpoint}: {exc.__class__.__name__}")
            _truncate_partial(dest)
    raise RuntimeError(f"failed to download {repo}/{fname} ({', '.join(errors)})")


def _endpoints():
    """Direct first, then mirror — skip the mirror if HF_ENDPOINT already pins it."""
    if os.environ.get("HF_ENDPOINT", "").strip():
        return [MIRROR_ENDPOINT]
    return [DIRECT_ENDPOINT, MIRROR_ENDPOINT]


def _stream_download(url: str, dest: Path, *, retries: int = 3) -> None:
    """Stream *url* to *dest*, resuming an existing partial file via Range."""
    for attempt in range(retries):
        existing = dest.stat().st_size if dest.is_file() else 0
        headers = {"User-Agent": "chitrika/1.0"}
        if existing:
            headers["Range"] = f"bytes={existing}-"
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                # Server answered 200 instead of 206 — restart from scratch.
                if existing and resp.status == 200:
                    existing = 0
                    dest.unlink(missing_ok=True)
                mode = "ab" if existing else "wb"
                with open(dest, mode) as fh:
                    while True:
                        chunk = resp.read(_CHUNK)
                        if not chunk:
                            break
                        fh.write(chunk)
                return
        except urllib.error.HTTPError as exc:
            if exc.code == 416:  # range not satisfiable → file already complete
                return
            if attempt == retries - 1:
                raise
        except OSError:
            if attempt == retries - 1:
                raise
    # Unreachable; loop returns or raises on its last iteration.


def _truncate_partial(dest: Path) -> None:
    """Drop a corrupt partial file so the next endpoint starts cleanly."""
    try:
        if dest.is_file():
            dest.unlink()
    except OSError:
        pass


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--emotion-repo",
        default=None,
        help=f"HF repo for the emotion ONNX model (default: {DEFAULT_EMOTION_REPO})",
    )
    parser.add_argument(
        "--embedding-repo",
        default=None,
        help=f"HF repo for the embedding ONNX model (default: {DEFAULT_EMBEDDING_REPO})",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-download even when all files already exist",
    )
    args = parser.parse_args()

    try:
        ensure_models(
            force=args.force,
            emotion_repo=args.emotion_repo,
            embedding_repo=args.embedding_repo,
        )
    except RuntimeError as exc:
        print(f"\nerror: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
