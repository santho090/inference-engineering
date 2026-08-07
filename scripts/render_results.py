#!/usr/bin/env python3
"""Render a Markdown page directly from canonical experiment records."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIRECTORY = ROOT / "examples" / "experiments"
OUTPUT_PATH = ROOT / "docs" / "reference" / "generated-results.md"


def main() -> int:
    parser = argparse.ArgumentParser(description="Render checked-in experiment fixture tables.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true", help="write generated Markdown")
    mode.add_argument("--check", action="store_true", help="fail if generated Markdown is stale")
    args = parser.parse_args()

    rendered = render()
    if args.write:
        OUTPUT_PATH.write_text(rendered, encoding="utf-8")
        print(f"wrote {OUTPUT_PATH.relative_to(ROOT)}")
        return 0
    if not OUTPUT_PATH.is_file() or OUTPUT_PATH.read_text(encoding="utf-8") != rendered:
        print(f"generated page differs: {OUTPUT_PATH.relative_to(ROOT)}")
        return 1
    print("verified generated result tables")
    return 0


def render() -> str:
    lines = [
        "# Generated result tables",
        "",
        "This page is rendered from small checked-in JSON fixtures. "
        "Every displayed value retains its evidence label.",
        "",
    ]
    for path in sorted(FIXTURE_DIRECTORY.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        lines.extend(
            [
                f"## {data['title']}",
                "",
                f"Record: `{data['record_id']}`. Result type: `{data['result_type']}`.",
                "",
                "| Metric | Value | Unit | Evidence |",
                "| --- | ---: | --- | --- |",
            ]
        )
        values = [*data["raw_measurements"], *data["derived_metrics"]]
        for value in values:
            lines.append(
                "| {name} | {value} | {unit} | `{evidence}` |".format(
                    name=value["name"],
                    value=_format_number(value["value"]),
                    unit=value["unit"],
                    evidence=value["evidence"],
                )
            )
        lines.extend(["", f"Conclusion: {data['conclusion']}", ""])
    return "\n".join(lines)


def _format_number(value: object) -> str:
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value)


if __name__ == "__main__":
    raise SystemExit(main())
