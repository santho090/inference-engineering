#!/usr/bin/env python3
"""Scan reachable repository history with the public disclosure rules."""

from __future__ import annotations

import argparse
import subprocess
from collections.abc import Sequence
from pathlib import Path

from prepublication_scan import ROOT, find_rule_matches, rules_with_denylist


def main(argv: Sequence[str] | None = None) -> int:
    """Run the history scan and return a process status."""

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
        print(f"history scan failed: {error}")
        return 2

    probe = subprocess.run(
        ["git", "rev-parse", "--is-inside-work-tree"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if probe.returncode != 0 or probe.stdout.strip() != "true":
        print("history scan skipped: no Git work tree is available")
        return 0

    history = subprocess.run(
        ["git", "log", "--all", "-p", "--format=fuller", "--", "."],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if history.returncode != 0:
        print(f"history scan failed: {history.stderr.strip()}")
        return 1
    if not history.stdout:
        print("history scan passed: no reachable commits contain this repository path")
        return 0

    findings = [
        f"history line {line}: {rule_name}"
        for rule_name, line in find_rule_matches(history.stdout, rules)
    ]
    if findings:
        print("history scan failed:")
        print("\n".join(findings))
        return 1
    print("history scan passed for all reachable commits affecting this repository path")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
