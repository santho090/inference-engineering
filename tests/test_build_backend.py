from __future__ import annotations

import importlib.util
import shutil
import sys
import tarfile
import tempfile
import tomllib
import unittest
from email import policy
from email.message import Message
from email.parser import BytesParser
from hashlib import sha256
from pathlib import Path
from types import ModuleType
from typing import cast
from zipfile import ZipFile

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DIST_NAME = "inference_engineering"
VERSION = "0.1.0"
DIST_INFO = f"{DIST_NAME}-{VERSION}.dist-info"
SOURCE_ARCHIVE_ROOT = f"{DIST_NAME}-{VERSION}"
FORBIDDEN_PARTS = {
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


def _load_backend(repository: Path) -> ModuleType:
    backend_path = repository / "scripts" / "build_backend.py"
    spec = importlib.util.spec_from_file_location("archive_test_backend", backend_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load the local build backend")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(spec.name, None)
    return module


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


def _write_disallowed_artifacts(repository: Path, local_path: str) -> None:
    artifacts = {
        repository / "src" / "inference_engineering" / "__pycache__" / "leak.pyc": local_path,
        repository / "site" / "generated.html": local_path,
        repository / "build" / "build-output.txt": local_path,
        repository / "dist" / "artifact.txt": local_path,
        repository / ".mypy_cache" / "state.json": local_path,
        repository / ".venv" / "state.txt": local_path,
        repository / ".git" / "config": local_path,
    }
    for path, content in artifacts.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def _assert_publishable_names(test_case: unittest.TestCase, names: list[str]) -> None:
    for name in names:
        with test_case.subTest(name=name):
            parts = set(Path(name).parts)
            test_case.assertFalse(parts.intersection(FORBIDDEN_PARTS))
            test_case.assertFalse(name.endswith(".pyc"))


def _assert_normalized_sdist_members(
    test_case: unittest.TestCase, members: list[tarfile.TarInfo]
) -> None:
    for member in members:
        with test_case.subTest(member=member.name):
            test_case.assertTrue(member.isfile())
            test_case.assertEqual(member.type, tarfile.REGTYPE)
            test_case.assertEqual(member.uid, 0)
            test_case.assertEqual(member.gid, 0)
            test_case.assertEqual(member.uname, "")
            test_case.assertEqual(member.gname, "")
            test_case.assertEqual(member.mtime, 0)
            test_case.assertEqual(member.mode, 0o644)
            test_case.assertEqual(member.pax_headers, {})


def _load_project_metadata(repository: Path) -> dict[str, object]:
    with (repository / "pyproject.toml").open("rb") as handle:
        project_file = tomllib.load(handle)
    project = project_file.get("project")
    if not isinstance(project, dict):
        raise AssertionError("pyproject.toml must define a [project] table")
    return cast(dict[str, object], project)


def _project_string(project: dict[str, object], key: str) -> str:
    value = project.get(key)
    if not isinstance(value, str):
        raise AssertionError(f"[project].{key} must be a string")
    return value


def _project_string_list(project: dict[str, object], key: str) -> list[str]:
    value = project.get(key)
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise AssertionError(f"[project].{key} must be a list of strings")
    return cast(list[str], value)


def _project_author_names(project: dict[str, object]) -> list[str]:
    authors = project.get("authors")
    if not isinstance(authors, list):
        raise AssertionError("[project].authors must be a list")
    names: list[str] = []
    for author in authors:
        if not isinstance(author, dict) or not isinstance(author.get("name"), str):
            raise AssertionError("each [project].authors entry must define a name")
        names.append(author["name"])
    return names


def _project_dev_dependencies(project: dict[str, object]) -> list[str]:
    optional_dependencies = project.get("optional-dependencies")
    if not isinstance(optional_dependencies, dict):
        raise AssertionError("[project.optional-dependencies] must be a table")
    dev_dependencies = optional_dependencies.get("dev")
    if not isinstance(dev_dependencies, list) or not all(
        isinstance(dependency, str) for dependency in dev_dependencies
    ):
        raise AssertionError("[project.optional-dependencies].dev must be a list of strings")
    return cast(list[str], dev_dependencies)


def _parse_metadata(content: bytes) -> Message:
    return BytesParser(policy=policy.default).parsebytes(content)


def _assert_metadata_parity(
    test_case: unittest.TestCase,
    content: bytes,
    project: dict[str, object],
    repository: Path,
) -> None:
    metadata = _parse_metadata(content)
    test_case.assertEqual(metadata["Name"], _project_string(project, "name"))
    test_case.assertEqual(metadata["Version"], _project_string(project, "version"))
    test_case.assertEqual(metadata["Summary"], _project_string(project, "description"))
    test_case.assertEqual(metadata.get_all("Author"), _project_author_names(project))
    test_case.assertEqual(
        metadata["Requires-Python"],
        _project_string(project, "requires-python"),
    )
    test_case.assertEqual(
        metadata.get_all("Classifier"), _project_string_list(project, "classifiers")
    )
    test_case.assertEqual(metadata["License-Expression"], _project_string(project, "license"))
    test_case.assertEqual(
        metadata.get_all("License-File"),
        _project_string_list(project, "license-files"),
    )
    test_case.assertEqual(metadata["Description-Content-Type"], "text/markdown")
    test_case.assertEqual(
        metadata.get_payload(),
        (repository / _project_string(project, "readme")).read_text(encoding="utf-8"),
    )

    dev_dependencies = _project_dev_dependencies(project)
    test_case.assertEqual(metadata.get_all("Provides-Extra"), ["dev"])
    test_case.assertEqual(
        metadata.get_all("Requires-Dist"),
        [f'{dependency} ; extra == "dev"' for dependency in dev_dependencies],
    )


class BuildBackendArchiveTests(unittest.TestCase):
    def test_archives_are_publishable_and_sdist_is_reproducible(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary_root = Path(temporary_directory)
            repository = temporary_root / "repository"
            first_distribution_directory = temporary_root / "first-distribution"
            second_distribution_directory = temporary_root / "second-distribution"
            _copy_repository(repository)
            local_path = str(repository / "private-source-path")
            _write_disallowed_artifacts(repository, local_path)
            backend = _load_backend(repository)
            project = _load_project_metadata(repository)

            wheel_name = backend.build_wheel(str(first_distribution_directory))
            second_wheel_name = backend.build_wheel(str(second_distribution_directory))
            first_sdist_name = backend.build_sdist(str(first_distribution_directory))
            second_sdist_name = backend.build_sdist(str(second_distribution_directory))

            wheel_path = first_distribution_directory / wheel_name
            second_wheel_path = second_distribution_directory / second_wheel_name
            self.assertEqual(wheel_name, second_wheel_name)
            self.assertEqual(wheel_path.read_bytes(), second_wheel_path.read_bytes())
            self.assertEqual(
                sha256(wheel_path.read_bytes()).hexdigest(),
                sha256(second_wheel_path.read_bytes()).hexdigest(),
            )
            with ZipFile(wheel_path) as wheel:
                wheel_names = wheel.namelist()
                _assert_publishable_names(self, wheel_names)
                self.assertIn(f"{DIST_INFO}/licenses/LICENSE", wheel_names)
                self.assertIn(f"{DIST_INFO}/licenses/NOTICE", wheel_names)
                self.assertEqual(
                    wheel.read(f"{DIST_INFO}/licenses/LICENSE"),
                    (repository / "LICENSE").read_bytes(),
                )
                self.assertEqual(
                    wheel.read(f"{DIST_INFO}/licenses/NOTICE"),
                    (repository / "NOTICE").read_bytes(),
                )
                wheel_metadata = wheel.read(f"{DIST_INFO}/METADATA")
                _assert_metadata_parity(self, wheel_metadata, project, repository)
                self.assertEqual(
                    wheel.read(f"{DIST_INFO}/entry_points.txt"),
                    b"[console_scripts]\nie = inference_engineering.cli:main\n",
                )
                wheel_contents = b"".join(wheel.read(name) for name in wheel_names)
                self.assertNotIn(local_path.encode("utf-8"), wheel_contents)

            first_sdist_path = first_distribution_directory / first_sdist_name
            second_sdist_path = second_distribution_directory / second_sdist_name
            self.assertEqual(first_sdist_name, second_sdist_name)
            first_sdist_bytes = first_sdist_path.read_bytes()
            self.assertEqual(first_sdist_bytes, second_sdist_path.read_bytes())
            self.assertEqual(
                sha256(first_sdist_bytes).hexdigest(),
                sha256(second_sdist_path.read_bytes()).hexdigest(),
            )
            self.assertEqual(first_sdist_bytes[3], 0)
            self.assertEqual(first_sdist_bytes[4:8], b"\0\0\0\0")
            self.assertNotIn(local_path.encode("utf-8"), first_sdist_bytes)

            with tarfile.open(first_sdist_path, "r:gz") as source_archive:
                sdist_names = source_archive.getnames()
                _assert_publishable_names(self, sdist_names)
                _assert_normalized_sdist_members(self, source_archive.getmembers())
                self.assertIn(f"{SOURCE_ARCHIVE_ROOT}/LICENSE", sdist_names)
                self.assertIn(f"{SOURCE_ARCHIVE_ROOT}/NOTICE", sdist_names)
                self.assertIn(f"{SOURCE_ARCHIVE_ROOT}/PKG-INFO", sdist_names)
                package_info = source_archive.extractfile(f"{SOURCE_ARCHIVE_ROOT}/PKG-INFO")
                if package_info is None:
                    self.fail("sdist PKG-INFO must be readable")
                sdist_metadata = package_info.read()
                self.assertEqual(sdist_metadata, wheel_metadata)
                _assert_metadata_parity(self, sdist_metadata, project, repository)
                sdist_contents = b"".join(
                    member_file.read()
                    for member in source_archive.getmembers()
                    if member.isfile()
                    and (member_file := source_archive.extractfile(member)) is not None
                )
                self.assertNotIn(local_path.encode("utf-8"), sdist_contents)
