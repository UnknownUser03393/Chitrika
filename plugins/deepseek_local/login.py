"""Browser login helper — saves Playwright storage state for DeepSeek web.

Usage:
    uv run python plugins/deepseek_local/login.py
    uv run python plugins/deepseek_local/login.py --out plugins/deepseek_local/data/auth_state.json
"""

from __future__ import annotations

import argparse
from pathlib import Path

DEEPSEEK_URL = "https://chat.deepseek.com"
DEFAULT_OUT = Path(__file__).resolve().parent / "data" / "auth_state.json"


def main() -> None:
    parser = argparse.ArgumentParser(description="Login to chat.deepseek.com and save auth_state.json")
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help=f"Output path (default: {DEFAULT_OUT})",
    )
    args = parser.parse_args()

    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise SystemExit(
            "playwright is required for login.\n"
            "  uv pip install playwright\n"
            "  playwright install chromium"
        ) from exc

    out: Path = args.out.expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        page.goto(DEEPSEEK_URL, wait_until="domcontentloaded")

        print("Log in to DeepSeek in the opened browser window.")
        print("After the chat UI is fully loaded, press Enter here to save auth state.")
        input()

        context.storage_state(path=str(out))
        browser.close()

    print(f"Saved {out}")


if __name__ == "__main__":
    main()
