from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SETTLED_SOURCES = (
    Path("CONTEXT.md"),
    Path("docs/specification.md"),
    Path("docs/program-roadmap.md"),
    Path("docs/publication-policy.md"),
    Path("docs/adr/0001-repository-boundary.md"),
)


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


def _run_publication_scan(repository: Path, denylist: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(repository / "scripts" / "prepublication_scan.py"),
            "--denylist",
            str(denylist),
        ],
        cwd=repository,
        check=False,
        capture_output=True,
        text=True,
    )


class PublicationScanTests(unittest.TestCase):
    def test_each_settled_source_is_scanned_with_an_external_denylist(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary_root = Path(temporary_directory)
            repository = temporary_root / "repository"
            _copy_repository(repository)
            denylist = temporary_root / "denylist.txt"

            for index, relative_path in enumerate(SETTLED_SOURCES):
                marker = f"external-denylist-settled-source-{index}"
                target = repository / relative_path
                original = target.read_text(encoding="utf-8")
                target.write_text(f"{original}\n{marker}\n", encoding="utf-8")
                denylist.write_text(f"{marker}\n", encoding="utf-8")

                result = _run_publication_scan(repository, denylist)

                self.assertNotEqual(result.returncode, 0)
                self.assertIn(str(relative_path), result.stdout)
                self.assertIn("external denylist match", result.stdout)
                target.write_text(original, encoding="utf-8")

    def test_denylist_match_and_invalid_denylist_fail_clearly(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary_root = Path(temporary_directory)
            repository = temporary_root / "repository"
            _copy_repository(repository)
            marker = "external-denylist-readme-marker"
            readme = repository / "README.md"
            readme.write_text(
                f"{readme.read_text(encoding='utf-8')}\n{marker}\n",
                encoding="utf-8",
            )
            denylist = temporary_root / "denylist.txt"
            denylist.write_text(f"{marker}\n", encoding="utf-8")

            match_result = _run_publication_scan(repository, denylist)

            self.assertNotEqual(match_result.returncode, 0)
            self.assertIn("README.md", match_result.stdout)
            self.assertIn("external denylist match", match_result.stdout)

            missing_result = _run_publication_scan(repository, temporary_root / "missing.txt")

            self.assertNotEqual(missing_result.returncode, 0)
            self.assertIn("denylist file not found", missing_result.stdout)

            denylist.write_text("# comment only\n", encoding="utf-8")
            invalid_result = _run_publication_scan(repository, denylist)

            self.assertNotEqual(invalid_result.returncode, 0)
            self.assertIn("denylist file is invalid: contains no entries", invalid_result.stdout)

    def test_history_scan_applies_external_denylist_rules(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary_root = Path(temporary_directory)
            repository = temporary_root / "repository"
            _copy_repository(repository)
            marker = "external-denylist-history-marker"
            denylist = temporary_root / "denylist.txt"
            denylist.write_text(f"{marker}\n", encoding="utf-8")
            bin_directory = temporary_root / "bin"
            bin_directory.mkdir()
            fake_git = bin_directory / "git"
            fake_git.write_text(
                "\n".join(
                    (
                        f"#!{sys.executable}",
                        "import sys",
                        "if sys.argv[1:3] == ['rev-parse', '--is-inside-work-tree']:",
                        "    print('true')",
                        "elif len(sys.argv) > 1 and sys.argv[1] == 'log':",
                        f"    print('{marker}')",
                        "else:",
                        "    raise SystemExit(2)",
                        "",
                    )
                ),
                encoding="utf-8",
            )
            fake_git.chmod(0o755)
            environment = os.environ.copy()
            environment["PATH"] = f"{bin_directory}{os.pathsep}{environment['PATH']}"

            result = subprocess.run(
                [
                    sys.executable,
                    str(repository / "scripts" / "check_history.py"),
                    "--denylist",
                    str(denylist),
                ],
                cwd=repository,
                env=environment,
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("history line 1: external denylist match", result.stdout)
