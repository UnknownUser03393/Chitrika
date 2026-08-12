"""Chitrika one-click startup — runs backend + frontend in the same terminal.

Press Ctrl+C to stop both servers.
"""

import os
import shutil
import signal
import secrets
import subprocess
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BACKEND_DIR / "src" / "frontend"


def _find_exe(name: str) -> str:
    """Resolve a command name to a full path.  On Windows ``name`` may need a
    ``.cmd`` extension which ``Popen`` won't resolve without ``shell=True``."""
    path = shutil.which(name)
    if path is None:
        # On Windows, check for .cmd variant
        path = shutil.which(f"{name}.cmd")
    if path is None:
        raise FileNotFoundError(
            f"'{name}' not found on PATH. Is it installed?"
        )
    return path


def main() -> None:
    api_token = os.environ.get("CHITRIKA_API_TOKEN") or secrets.token_hex(32)
    child_env = os.environ.copy()
    child_env["CHITRIKA_API_TOKEN"] = api_token
    child_env["VITE_CHITRIKA_API_TOKEN"] = api_token
    print("============================================")
    print("  Chitrika — starting backend + frontend")
    print("============================================")
    print()
    print("[1/2] Starting backend (uvicorn) on :8000 ...")
    print("[2/2] Starting frontend (vite) on :8080 ...")
    print()
    print("  Backend  → http://localhost:8000")
    print("  Frontend → http://127.0.0.1:8080")
    print()
    print("Press Ctrl+C to stop all servers.")
    print()

    backend = subprocess.Popen(
        [
            "uv", "run", "uvicorn", "src.main:app",
            "--reload",
            # Restrict the reload watcher to backend directories. Watching the
            # whole repo (incl. src/frontend + node_modules) makes uvicorn
            # reload on every frontend write — on Windows that spawns new
            # worker processes and destabilises the vite dev server.
            "--reload-dir", "src/chitrika",
            "--reload-dir", "src/llmproviders",
            "--reload-dir", "plugins",
            "--host", "0.0.0.0",
            "--port", "8000",
        ],
        cwd=str(BACKEND_DIR),
        env=child_env,
    )
    frontend = subprocess.Popen(
        [_find_exe("pnpm"), "dev"],
        cwd=str(FRONTEND_DIR),
        env=child_env,
    )

    processes = [backend, frontend]

    def _terminate(p: subprocess.Popen) -> None:
        if p.poll() is not None:
            return
        if os.name == "nt":
            # Kill the whole tree — terminate() alone often leaves orphaned
            # node / uvicorn children behind on Windows.
            subprocess.run(
                ["taskkill", "/PID", str(p.pid), "/T", "/F"],
                capture_output=True,
            )
        else:
            p.terminate()
            try:
                p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                p.kill()
                p.wait()

    def shutdown(signum, frame):
        print("\nShutting down...")
        for p in processes:
            _terminate(p)
        print("Servers stopped.")
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    # Block until any child exits (unexpected), or a signal arrives
    try:
        for p in processes:
            p.wait()
    except KeyboardInterrupt:
        shutdown(None, None)


if __name__ == "__main__":
    main()
