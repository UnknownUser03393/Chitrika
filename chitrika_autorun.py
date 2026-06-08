"""Chitrika one-click startup — runs backend + frontend in the same terminal.

Press Ctrl+C to stop both servers.
"""

import shutil
import signal
import subprocess
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = Path(r"D:\Development\Chitrika-frontend")


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
    print("============================================")
    print("  Chitrika — starting backend + frontend")
    print("============================================")
    print()
    print("[1/2] Starting backend (uvicorn) on :8000 ...")
    print("[2/2] Starting frontend (vite) on :5173 ...")
    print()
    print("  Backend  → http://localhost:8000")
    print("  Frontend → http://localhost:5173")
    print()
    print("Press Ctrl+C to stop all servers.")
    print()

    backend = subprocess.Popen(
        ["uv", "run", "uvicorn", "src.main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"],
        cwd=str(BACKEND_DIR),
    )
    frontend = subprocess.Popen(
        [_find_exe("pnpm"), "dev"],
        cwd=str(FRONTEND_DIR),
    )

    processes = [backend, frontend]

    def shutdown(signum, frame):
        print("\nShutting down...")
        for p in processes:
            p.terminate()
        for p in processes:
            try:
                p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                p.kill()
                p.wait()
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
