"""Guard against mojibake creeping back into source and docs."""

from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

TEXT_SUFFIXES = {
    ".md",
    ".py",
    ".ps1",
    ".toml",
    ".ts",
    ".tsx",
    ".json",
    ".css",
    ".html",
    ".mjs",
}

SKIP_PARTS = {
    ".git",
    ".idea",
    ".pytest_cache",
    ".venv",
    "__pycache__",
    "node_modules",
    "dist",
}

MOJIBAKE_MARKERS = (
    "\ufffd",
    "\u9205",  # mojibake for punctuation/box drawing
    "\u922b",  # mojibake for arrows
    "\u922e",  # mojibake for math symbols
    "\u8133",
    "\u922d",
    "\u5bf0\u61319",
    "\u6d63\u72b2\u30bd",
    "\u9352\u6c2c\u57ae",
    "\u9352\u55db\u9363",
    "\u704f\u5fd4\u6902",
    "\u6fa7\u255e\u588d",
    "\u6d93\u3c81\u6e80",
    "\u7ec3",
    "\u92910",
    "\u951b",
)


def _text_files() -> list[Path]:
    files: list[Path] = []
    for path in PROJECT_ROOT.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_PARTS for part in path.parts):
            continue
        if path.suffix.lower() in TEXT_SUFFIXES:
            files.append(path)
    return files


def test_text_files_are_utf8_without_mojibake_markers():
    failures: list[str] = []
    for path in _text_files():
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            failures.append(f"{path.relative_to(PROJECT_ROOT)} is not UTF-8: {exc}")
            continue

        if text.startswith("\ufeff"):
            failures.append(f"{path.relative_to(PROJECT_ROOT)} has a UTF-8 BOM")

        found = [marker for marker in MOJIBAKE_MARKERS if marker in text]
        if found:
            escaped = ", ".join(marker.encode("unicode_escape").decode() for marker in found)
            failures.append(f"{path.relative_to(PROJECT_ROOT)} contains mojibake: {escaped}")

    assert not failures, "\n".join(failures)
