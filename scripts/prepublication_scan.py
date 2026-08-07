#!/usr/bin/env python3
"""Scan intended public deliverables for disclosure and typography failures."""

from __future__ import annotations

import argparse
import re
from collections.abc import Sequence
from pathlib import Path
from typing import Final

ROOT: Final = Path(__file__).resolve().parents[1]
PUBLIC_TOP_LEVEL_FILES: Final = {
    Path("CONTEXT.md"),
    Path("README.md"),
    Path("LICENSE"),
    Path("NOTICE"),
    Path("THIRD_PARTY.md"),
    Path("CONTRIBUTING.md"),
    Path("SECURITY.md"),
    Path("pyproject.toml"),
    Path("mkdocs.yml"),
    Path(".gitignore"),
}
PUBLIC_DIRECTORIES: Final = (".github", "docs", "src", "tests", "examples", "scripts")
BASE_RULES: Final = (
    ("absolute local path", re.compile(r"/(?:Users|home|private|var)/")),
    (
        "credential-shaped value",
        re.compile(r"(?i)\b(?:api[_-]?key|secret|token|sk)[_-][a-z0-9]{16,}\b"),
    ),
    (
        "automation attribution",
        re.compile(
            r"(?i)\b(?:generated|authored|written)\s+(?:by|with)\s+"
            r"(?:an?\s+)?(?:coding\s+)?assistant\b"
        ),
    ),
    ("em dash", re.compile("\\u2014")),
    ("en dash", re.compile("\\u2013")),
)
MAX_FILE_BYTES: Final = 1_000_000
IGNORED_PARTS: Final = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "site",
}
ScanRule = tuple[str, re.Pattern[str]]


def main(argv: Sequence[str] | None = None) -> int:
    """Run the scan and return a process status."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--denylist",
        type=Path,
        help="external newline-delimited literal terms to reject; never publish this file",
    )
    arguments = parser.parse_args(argv)
    try:
        rules = rules_with_denylist(arguments.denylist)
    except ValueError as error:
        print(f"Pre-publication scan failed: {error}")
        return 2

    findings, scanned = scan_public_files(ROOT, rules)
    if findings:
        print("Pre-publication scan failed:")
        print("\n".join(findings))
        return 1
    print(f"pre-publication scan passed for {scanned} public files")
    return 0


def rules_with_denylist(denylist_path: Path | None) -> tuple[ScanRule, ...]:
    """Return base rules plus literal, case-insensitive external denylist terms."""

    rules = list(BASE_RULES)
    if denylist_path is not None:
        terms = load_denylist(denylist_path)
        rules.append(
            (
                "external denylist match",
                re.compile("|".join(re.escape(term) for term in terms), re.IGNORECASE),
            )
        )
    return tuple(rules)


def load_denylist(path: Path) -> tuple[str, ...]:
    """Load one literal term per line without exposing its contents in errors."""

    if not path.exists():
        raise ValueError(f"denylist file not found: {path}")
    if not path.is_file():
        raise ValueError(f"denylist path is not a file: {path}")
    try:
        contents = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as error:
        raise ValueError(f"denylist file is invalid: not UTF-8 text ({error.reason})") from error

    terms: list[str] = []
    seen: set[str] = set()
    errors: list[str] = []
    for line_number, raw_line in enumerate(contents.splitlines(), start=1):
        term = raw_line.strip()
        if not term or term.startswith("#"):
            continue
        if len(term) > 512:
            errors.append(f"line {line_number} exceeds 512 characters")
            continue
        if any(ord(character) < 32 or ord(character) == 127 for character in term):
            errors.append(f"line {line_number} contains a control character")
            continue
        normalized = term.casefold()
        if normalized in seen:
            errors.append(f"line {line_number} duplicates an earlier term")
            continue
        seen.add(normalized)
        terms.append(term)
    if errors:
        raise ValueError(f"denylist file is invalid: {'; '.join(errors)}")
    if not terms:
        raise ValueError("denylist file is invalid: contains no entries")
    return tuple(terms)


def scan_public_files(root: Path, rules: Sequence[ScanRule]) -> tuple[list[str], int]:
    """Scan every intended public source file below the repository root."""

    findings: list[str] = []
    files = _public_files(root)
    for path in files:
        relative = path.relative_to(root)
        if path.stat().st_size > MAX_FILE_BYTES:
            findings.append(f"{relative}: unrecorded artifact larger than {MAX_FILE_BYTES} bytes")
            continue
        if _is_binary(path):
            findings.append(f"{relative}: binary asset needs explicit provenance review")
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            findings.append(f"{relative}: non-UTF-8 text needs explicit provenance review")
            continue
        for rule_name, line in find_rule_matches(text, rules):
            findings.append(f"{relative}:{line}: {rule_name}")
    return findings, len(files)


def find_rule_matches(text: str, rules: Sequence[ScanRule]) -> list[tuple[str, int]]:
    """Return rule names and one-indexed line numbers for every text match."""

    matches: list[tuple[str, int]] = []
    for rule_name, pattern in rules:
        for match in pattern.finditer(text):
            line = text.count("\n", 0, match.start()) + 1
            matches.append((rule_name, line))
    return matches


def _public_files(root: Path) -> list[Path]:
    files = [root / item for item in PUBLIC_TOP_LEVEL_FILES if (root / item).is_file()]
    for directory in PUBLIC_DIRECTORIES:
        directory_root = root / directory
        if not directory_root.is_dir():
            continue
        for path in directory_root.rglob("*"):
            relative = path.relative_to(root)
            if path.is_file() and not set(relative.parts).intersection(IGNORED_PARTS):
                files.append(path)
    return sorted(set(files))


def _is_binary(path: Path) -> bool:
    return b"\0" in path.read_bytes()[:1024]


if __name__ == "__main__":
    raise SystemExit(main())
