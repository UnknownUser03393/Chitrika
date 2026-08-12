"""Chitrika backend launcher — PyInstaller entry point.

Runs the FastAPI app under uvicorn. The Electron shell controls it through
environment variables so the packaged app and the dev server share one code
path:

- CHITRIKA_HOST  (default 127.0.0.1)
- CHITRIKA_PORT  (default 8000)
- CHITRIKA_LOG_DIR — if set, uvicorn logs also go to backend.log in that dir
  (the packaged app is windowed, so a file log is the only way to debug).
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

import uvicorn

from src.main import app


def _configure_file_logging() -> None:
    log_dir = os.environ.get("CHITRIKA_LOG_DIR")
    if not log_dir:
        return
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(Path(log_dir) / "backend.log", encoding="utf-8")
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    )
    root = logging.getLogger()
    root.addHandler(handler)
    root.setLevel(logging.INFO)


if __name__ == "__main__":
    _configure_file_logging()
    uvicorn.run(
        app,
        host=os.environ.get("CHITRIKA_HOST", "127.0.0.1"),
        port=int(os.environ.get("CHITRIKA_PORT", "8000")),
        log_level=os.environ.get("CHITRIKA_LOG_LEVEL", "info"),
    )
