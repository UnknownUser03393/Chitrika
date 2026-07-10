"""Toast notification worker — stdin/stdout JSON-line protocol.

Reads JSON requests from stdin, shows Windows toast notifications via
toastlib, and writes JSON responses to stdout.

Protocol (stdin → worker):
    {"type": "notify", "title": "...", "content": "...", "message_id": "..."}
    {"type": "quit"}

Protocol (worker → stdout):
    {"type": "shown", "message_id": "..."}
    {"type": "error", "message_id": "...", "error": "..."}
    {"type": "ready"}
"""

from __future__ import annotations

import json
import sys

# ---------------------------------------------------------------------------
# Bootstrap: add project root to sys.path so toastlib is importable
# ---------------------------------------------------------------------------
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------


def main() -> None:
    from src.toastlib.toastlib import DurationShort, registerApplication, showNotify

    app_name = "Chitrika"
    aumid = registerApplication(app_name)

    # Signal ready
    print(json.dumps({"type": "ready"}), flush=True)

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue

        try:
            request = json.loads(line)
        except json.JSONDecodeError:
            continue

        req_type = request.get("type")

        if req_type == "quit":
            break

        if req_type == "notify":
            message_id = request.get("message_id", "")
            title = request.get("title", "Chitrika")
            content = request.get("content", "")

            try:
                showNotify(
                    app_name,
                    title,
                    content,
                    duration=DurationShort,
                    ttl=10,
                    silent=False,
                )
                print(json.dumps({"type": "shown", "message_id": message_id}), flush=True)
            except Exception as exc:
                print(
                    json.dumps({
                        "type": "error",
                        "message_id": message_id,
                        "error": str(exc),
                    }),
                    flush=True,
                )


if __name__ == "__main__":
    main()
