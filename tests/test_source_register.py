from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def _copy_repository(destination: Path) -> None:
    shutil.copytree(
        REPOSITORY_ROOT,
        destination,
        ignore=shutil.ignore_patterns(
            ".git",
            ".mypy_cache",
            ".pytest_cache",
            ".ruff_cache",
            ".venv",
            "__pycache__",
            "build",
            "dist",
            "site",
        ),
    )


def _run_source_register_check(repository: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(repository / "scripts" / "check_source_register.py")],
        cwd=repository,
        check=False,
        capture_output=True,
        text=True,
    )


class SourceRegisterTests(unittest.TestCase):
    def test_all_current_markdown_sources_are_registered(self) -> None:
        result = _run_source_register_check(REPOSITORY_ROOT)

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("source-register check passed", result.stdout)

    def test_missing_markdown_source_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            repository = Path(temporary_directory) / "repository"
            _copy_repository(repository)
            readme = repository / "README.md"
            missing_url = "https://example.invalid/unregistered-navigation-source"
            readme.write_text(
                f"{readme.read_text(encoding='utf-8')}\n[Missing source]({missing_url})\n",
                encoding="utf-8",
            )

            result = _run_source_register_check(repository)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(f"README.md: unregistered source {missing_url}", result.stdout)
