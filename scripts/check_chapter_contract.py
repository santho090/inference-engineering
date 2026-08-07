#!/usr/bin/env python3
"""Verify that every technical chapter carries the settled teaching contract."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TECHNICAL_CHAPTERS = (
    ROOT / "docs" / "foundations" / "01-what-it-controls.md",
    ROOT / "docs" / "foundations" / "02-workloads-and-objectives.md",
    ROOT / "docs" / "foundations" / "03-request-lifecycle.md",
    ROOT / "docs" / "foundations" / "04-measurement-integrity.md",
    ROOT / "docs" / "hardware" / "05-transformer-anatomy.md",
    ROOT / "docs" / "hardware" / "06-gpu-execution.md",
    ROOT / "docs" / "hardware" / "07-roofline.md",
    ROOT / "docs" / "hardware" / "08-memory-sizing.md",
    ROOT / "docs" / "levels" / "09-kernel-optimization.md",
    ROOT / "docs" / "levels" / "10-phase-scheduling.md",
    ROOT / "docs" / "levels" / "11-cache-management.md",
    ROOT / "docs" / "levels" / "12-runtime-levers.md",
    ROOT / "docs" / "production" / "13-pooling-and-placement.md",
    ROOT / "docs" / "production" / "14-cluster-architecture.md",
    ROOT / "docs" / "production" / "15-adaptive-control.md",
    ROOT / "docs" / "production" / "16-observability-and-capacity.md",
    ROOT / "docs" / "future" / "17-where-next.md",
)
REQUIRED_HEADINGS = (
    "## Question",
    "## Mental model",
    "## Workload variables",
    "## Constrained resources and serialized stages",
    "## Metrics and boundaries",
    "## Control levers and preconditions",
    "## Failure modes and counterexamples",
    "## Worked numerical example",
    "## Executable exercise",
    "## Primary references",
)


def main() -> int:
    errors: list[str] = []
    for path in TECHNICAL_CHAPTERS:
        text = path.read_text(encoding="utf-8") if path.is_file() else ""
        for heading in REQUIRED_HEADINGS:
            if heading not in text:
                errors.append(f"{path.relative_to(ROOT)}: missing {heading}")
        if "```mermaid" not in text:
            errors.append(f"{path.relative_to(ROOT)}: missing Mermaid mental-model diagram")
    if errors:
        print("chapter-contract validation failed:")
        print("\n".join(errors))
        return 1
    print(f"validated chapter contract for {len(TECHNICAL_CHAPTERS)} technical chapters")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
