from __future__ import annotations

import unittest
from pathlib import Path

from inference_engineering.fixtures import fixture_records

ROOT = Path(__file__).resolve().parents[1]


class FixtureTests(unittest.TestCase):
    def test_checked_in_fixtures_match_deterministic_generation(self) -> None:
        for name, record in fixture_records().items():
            with self.subTest(name=name):
                path = ROOT / "examples" / "experiments" / name
                self.assertEqual(path.read_text(encoding="utf-8"), record.to_json())
