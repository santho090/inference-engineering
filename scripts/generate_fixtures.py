#!/usr/bin/env python3
"""Generate or verify canonical JSON experiment fixtures."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "src"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from inference_engineering.fixtures import fixture_records  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate deterministic experiment fixtures.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true", help="write canonical fixtures")
    mode.add_argument(
        "--check", action="store_true", help="fail if fixtures differ from generation"
    )
    args = parser.parse_args()

    fixture_directory = ROOT / "examples" / "experiments"
    records = fixture_records()
    mismatches: list[Path] = []
    for name, record in records.items():
        path = fixture_directory / name
        expected = record.to_json()
        if args.write:
            path.write_text(expected, encoding="utf-8")
            print(f"wrote {path.relative_to(ROOT)}")
        elif not path.is_file() or path.read_text(encoding="utf-8") != expected:
            mismatches.append(path)

    if mismatches:
        for path in mismatches:
            print(f"fixture differs: {path.relative_to(ROOT)}")
        return 1
    if args.check:
        print(f"verified {len(records)} deterministic experiment fixtures")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
