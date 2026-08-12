"""Chitrika auto-download — ensure the ONNX models are present.

The emotion (~1.1 GB) and embedding (~470 MB) models are hosted on Hugging Face
Hub, not in git. Run this before first start (or hook it into your launcher) so
``models/`` is populated:

    python chitrika_autodownload.py

It tries huggingface.co first and, on any network failure, automatically
retries through the mainland-China mirror (hf-mirror.com) via ``HF_ENDPOINT``.

Exit code is 0 when both model dirs are complete, 1 on hard failure.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

MIRROR_ENDPOINT = "https://hf-mirror.com"


def _attempt(label: str) -> None:
    print(f"\n--- {label} ---")
    # Imported lazily so a missing huggingface_hub fails with our message,
    # and so the env override below is respected at call time.
    from download_models import ensure_models

    ensure_models()


def main() -> int:
    direct = "hf-mirror" not in os.environ.get("HF_ENDPOINT", "")
    try:
        _attempt("trying huggingface.co (direct)")
    except Exception as exc:  # network errors, auth, etc.
        if not direct:
            print(f"\nDirect download failed ({exc.__class__.__name__}).")
            return 1
        print(f"\nDirect download failed ({exc.__class__.__name__}).")
        os.environ["HF_ENDPOINT"] = MIRROR_ENDPOINT
        try:
            _attempt(f"retrying via mirror ({MIRROR_ENDPOINT})")
        except Exception as mirror_exc:
            print(f"\nMirror download also failed ({mirror_exc.__class__.__name__}).")
            return 1

    print("\nAll models present. Ready to run.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
