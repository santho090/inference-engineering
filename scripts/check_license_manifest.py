#!/usr/bin/env python3
"""Check the repository's license, notice, and third-party manifest boundary."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IGNORED_PARTS = {
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


def main() -> int:
    errors: list[str] = []
    license_text = _read("LICENSE", errors)
    notice_text = _read("NOTICE", errors)
    third_party_text = _read("THIRD_PARTY.md", errors)
    if "Apache License" not in license_text or "Version 2.0, January 2004" not in license_text:
        errors.append("LICENSE is not recognizable as Apache License 2.0")
    if "inference-engineering" not in notice_text:
        errors.append("NOTICE does not identify the project")
    if "No third-party code, data, or assets are bundled" not in third_party_text:
        errors.append("THIRD_PARTY.md does not state the bundled-material boundary")
    binary_assets = [
        path.relative_to(ROOT)
        for path in ROOT.rglob("*")
        if (
            path.is_file()
            and not set(path.relative_to(ROOT).parts).intersection(IGNORED_PARTS)
            and b"\0" in path.read_bytes()[:1024]
        )
    ]
    if binary_assets:
        errors.append(f"binary assets require manifest entries: {binary_assets}")
    if errors:
        print("license and manifest audit failed:")
        print("\n".join(errors))
        return 1
    print("license, NOTICE, and third-party manifest audit passed")
    return 0


def _read(name: str, errors: list[str]) -> str:
    path = ROOT / name
    if not path.is_file():
        errors.append(f"missing {name}")
        return ""
    return path.read_text(encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
