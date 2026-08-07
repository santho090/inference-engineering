#!/usr/bin/env python3
"""Validate local Markdown links and anchors without network access."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
LINK_PATTERN = re.compile(r"(?<!!)\[[^]]*\]\(([^)]+)\)")
HEADING_PATTERN = re.compile(r"^#{1,6}\s+(.+?)\s*#*\s*$")


def main() -> int:
    errors: list[str] = []
    for path in sorted(DOCS.rglob("*.md")):
        errors.extend(_validate_file(path))
    if errors:
        print("Markdown link validation failed:")
        print("\n".join(errors))
        return 1
    print("validated local Markdown links and anchors without network access")
    return 0


def _validate_file(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    errors: list[str] = []
    for match in LINK_PATTERN.finditer(text):
        target = match.group(1).strip().split(maxsplit=1)[0].strip("<>")
        if not target or target.startswith(("https://", "http://", "mailto:")):
            continue
        target_path_text, separator, anchor = target.partition("#")
        target_path = path if not target_path_text else (path.parent / target_path_text).resolve()
        if target_path.suffix == "":
            target_path = target_path.with_suffix(".md")
        if not target_path.is_file():
            errors.append(f"{path.relative_to(ROOT)}: missing local target {target}")
            continue
        if separator and anchor and _slug(anchor) not in _anchors(target_path):
            errors.append(f"{path.relative_to(ROOT)}: missing anchor {target}")
    return errors


def _anchors(path: Path) -> set[str]:
    anchors: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        match = HEADING_PATTERN.match(line)
        if match:
            anchors.add(_slug(match.group(1)))
    return anchors


def _slug(text: str) -> str:
    normalized = text.lower().strip()
    normalized = re.sub(r"[^\w\s-]", "", normalized)
    return re.sub(r"[\s-]+", "-", normalized).strip("-")


if __name__ == "__main__":
    raise SystemExit(main())
