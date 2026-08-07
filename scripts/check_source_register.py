#!/usr/bin/env python3
"""Require every external Markdown source URL to appear in the research map."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESEARCH_MAP = ROOT / "docs" / "reference" / "research-map.md"
URL_PATTERN = re.compile(r"https?://[^\s<>()\[\]\"']+")
TRAILING_PUNCTUATION = ".,;:!?"


def main() -> int:
    """Check that Markdown citations are registered without contacting their hosts."""

    registered_urls = _extract_urls(RESEARCH_MAP)
    errors: list[str] = []
    cited_urls: set[str] = set()
    for path in _citation_files():
        urls = _extract_urls(path)
        cited_urls.update(urls)
        for url in sorted(urls - registered_urls):
            errors.append(f"{path.relative_to(ROOT)}: unregistered source {url}")

    if errors:
        print("source-register check failed:")
        print("\n".join(errors))
        return 1

    print(f"source-register check passed for {len(cited_urls)} cited Markdown URLs")
    return 0


def _citation_files() -> list[Path]:
    """Return README and documentation Markdown, excluding the register itself."""

    files = [ROOT / "README.md"]
    documentation_root = ROOT / "docs"
    if documentation_root.is_dir():
        files.extend(path for path in documentation_root.rglob("*.md") if path != RESEARCH_MAP)
    return sorted(path for path in files if path.is_file())


def _extract_urls(path: Path) -> set[str]:
    """Extract exact HTTP(S) URLs from Markdown text without normalizing them."""

    text = path.read_text(encoding="utf-8")
    return {
        match.group(0).rstrip(TRAILING_PUNCTUATION)
        for match in URL_PATTERN.finditer(text)
        if match.group(0).rstrip(TRAILING_PUNCTUATION)
    }


if __name__ == "__main__":
    raise SystemExit(main())
