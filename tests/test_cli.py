from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


def reject_non_standard_constant(value: str) -> object:
    """Reject JavaScript-style numeric constants that strict JSON disallows."""

    raise ValueError(f"non-standard JSON numeric constant: {value}")


class CLITests(unittest.TestCase):
    def test_every_public_command_smoke_tests(self) -> None:
        commands = (
            ("memory", "model"),
            ("memory", "kv"),
            ("roofline",),
            ("simulate", "batching"),
            ("simulate", "kv"),
            ("validate", "experiment"),
        )
        for command in commands:
            with self.subTest(command=" ".join(command)):
                completed = subprocess.run(
                    [sys.executable, "-m", "inference_engineering", *command],
                    check=False,
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(completed.returncode, 0, completed.stderr)
                payload = json.loads(completed.stdout, parse_constant=reject_non_standard_constant)
                if command[0] == "validate":
                    self.assertTrue(payload["valid"])
                else:
                    self.assertIn("evidence", payload)

    def test_roofline_cli_rejects_non_finite_inputs(self) -> None:
        for invalid_value in ("nan", "inf", "-inf"):
            with self.subTest(invalid_value=invalid_value):
                completed = subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "inference_engineering",
                        "roofline",
                        f"--operations={invalid_value}",
                    ],
                    check=False,
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(completed.returncode, 2)
                self.assertIn("operations must be a positive finite number", completed.stderr)

    def test_validate_experiment_cli_rejects_non_standard_json_constants(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "invalid.json"
            for constant in ("NaN", "Infinity", "-Infinity"):
                with self.subTest(constant=constant):
                    path.write_text(f'{{"unknown": {constant}}}', encoding="utf-8")
                    completed = subprocess.run(
                        [
                            sys.executable,
                            "-m",
                            "inference_engineering",
                            "validate",
                            "experiment",
                            str(path),
                        ],
                        check=False,
                        capture_output=True,
                        text=True,
                    )

                    self.assertEqual(completed.returncode, 2)
                    self.assertEqual(completed.stdout, "")
                    self.assertIn(
                        f"non-standard JSON constant: {constant}",
                        completed.stderr,
                    )
