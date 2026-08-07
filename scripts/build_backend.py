"""A dependency-free PEP 517 backend for this small pure-Python package."""

from __future__ import annotations

import re
import tarfile
import tomllib
from base64 import urlsafe_b64encode
from collections.abc import Mapping
from dataclasses import dataclass
from gzip import GzipFile
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from typing import Final, cast
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

ROOT: Final = Path(__file__).resolve().parents[1]
SOURCE_ROOT: Final = ROOT / "src"


@dataclass(frozen=True)
class ProjectMetadata:
    """Static project metadata loaded from the PEP 621 table."""

    name: str
    version: str
    summary: str
    readme_path: Path
    requires_python: str
    license_expression: str
    license_files: tuple[str, ...]
    authors: tuple[str, ...]
    classifiers: tuple[str, ...]
    dependencies: tuple[str, ...]
    optional_dependencies: tuple[tuple[str, tuple[str, ...]], ...]
    scripts: tuple[tuple[str, str], ...]


def _load_project_metadata() -> ProjectMetadata:
    """Load static PEP 621 metadata without a third-party build dependency."""

    with (ROOT / "pyproject.toml").open("rb") as handle:
        parsed = tomllib.load(handle)
    raw_project = parsed.get("project")
    if not isinstance(raw_project, Mapping):
        raise ValueError("pyproject.toml must define a [project] table")
    project = cast(Mapping[str, object], raw_project)

    readme_path = ROOT / _required_string(project, "readme")
    if readme_path.suffix not in {".md", ".markdown"}:
        raise ValueError("[project].readme must name a Markdown file")
    if not readme_path.is_file():
        raise ValueError(f"[project].readme does not exist: {readme_path.name}")

    license_files = _string_list(project, "license-files")
    for license_file in license_files:
        license_path = Path(license_file)
        if license_path.is_absolute() or ".." in license_path.parts:
            raise ValueError("[project].license-files must use repository-relative paths")
        if not (ROOT / license_path).is_file():
            raise ValueError(f"[project].license-files entry does not exist: {license_file}")

    raw_authors = project.get("authors")
    if not isinstance(raw_authors, list):
        raise ValueError("[project].authors must be a list")
    authors: list[str] = []
    for raw_author in raw_authors:
        if not isinstance(raw_author, Mapping):
            raise ValueError("each [project].authors entry must be a table")
        authors.append(_required_string(cast(Mapping[str, object], raw_author), "name"))

    raw_optional_dependencies = project.get("optional-dependencies")
    if not isinstance(raw_optional_dependencies, Mapping):
        raise ValueError("[project.optional-dependencies] must be a table")
    optional_dependencies: list[tuple[str, tuple[str, ...]]] = []
    for extra, raw_dependencies in raw_optional_dependencies.items():
        if not isinstance(extra, str):
            raise ValueError("[project.optional-dependencies] keys must be strings")
        optional_dependencies.append((extra, tuple(_string_sequence(raw_dependencies, extra))))

    raw_scripts = project.get("scripts")
    if not isinstance(raw_scripts, Mapping):
        raise ValueError("[project.scripts] must be a table")
    scripts: list[tuple[str, str]] = []
    for script_name, script_target in raw_scripts.items():
        if not isinstance(script_name, str) or not isinstance(script_target, str):
            raise ValueError("[project.scripts] entries must map strings to strings")
        scripts.append((script_name, script_target))

    return ProjectMetadata(
        name=_required_string(project, "name"),
        version=_required_string(project, "version"),
        summary=_required_string(project, "description"),
        readme_path=readme_path,
        requires_python=_required_string(project, "requires-python"),
        license_expression=_required_string(project, "license"),
        license_files=tuple(license_files),
        authors=tuple(authors),
        classifiers=tuple(_string_list(project, "classifiers")),
        dependencies=tuple(_string_list(project, "dependencies")),
        optional_dependencies=tuple(sorted(optional_dependencies)),
        scripts=tuple(sorted(scripts)),
    )


def _required_string(table: Mapping[str, object], key: str) -> str:
    """Return a non-empty project string or a useful backend error."""

    value = table.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"[project].{key} must be a non-empty string")
    return value


def _string_list(table: Mapping[str, object], key: str) -> list[str]:
    """Read one PEP 621 string list from the project table."""

    return _string_sequence(table.get(key), f"[project].{key}")


def _string_sequence(value: object, field_name: str) -> list[str]:
    """Validate a TOML array of non-empty strings."""

    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        raise ValueError(f"{field_name} must be a list of non-empty strings")
    return list(cast(list[str], value))


PROJECT: Final = _load_project_metadata()
DIST_NAME: Final = re.sub(r"[-_.]+", "_", PROJECT.name)
PROJECT_NAME: Final = PROJECT.name
VERSION: Final = PROJECT.version
DIST_INFO: Final = f"{DIST_NAME}-{VERSION}.dist-info"
WHEEL_NAME: Final = f"{DIST_NAME}-{VERSION}-py3-none-any.whl"
LICENSE_FILES: Final = PROJECT.license_files
ROOT_SOURCE_FILES: Final = (
    ".gitignore",
    "CONTEXT.md",
    "CONTRIBUTING.md",
    "README.md",
    "SECURITY.md",
    "THIRD_PARTY.md",
    "mkdocs.yml",
    "pyproject.toml",
)
EXCLUDED_PARTS: Final = frozenset(
    {
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
)
SDIST_TREE_RULES: Final[tuple[tuple[Path, frozenset[str], frozenset[str]], ...]] = (
    (Path(".github"), frozenset({".md", ".yaml", ".yml"}), frozenset()),
    (Path("docs"), frozenset({".json", ".md"}), frozenset()),
    (Path("examples"), frozenset({".json"}), frozenset()),
    (Path("scripts"), frozenset({".py"}), frozenset()),
    (Path("src") / DIST_NAME, frozenset({".py", ".pyi"}), frozenset({"py.typed"})),
    (Path("tests"), frozenset({".py"}), frozenset()),
)


def get_requires_for_build_wheel(
    config_settings: Mapping[str, object] | None = None,
) -> list[str]:
    """Declare that wheel creation has no external build requirement."""

    del config_settings
    return []


def get_requires_for_build_editable(
    config_settings: Mapping[str, object] | None = None,
) -> list[str]:
    """Declare that editable creation has no external build requirement."""

    del config_settings
    return []


def prepare_metadata_for_build_wheel(
    metadata_directory: str,
    config_settings: Mapping[str, object] | None = None,
) -> str:
    """Write core metadata for wheel consumers that request it early."""

    del config_settings
    return _write_metadata(Path(metadata_directory))


def prepare_metadata_for_build_editable(
    metadata_directory: str,
    config_settings: Mapping[str, object] | None = None,
) -> str:
    """Write the same metadata for editable consumers."""

    return prepare_metadata_for_build_wheel(metadata_directory, config_settings)


def build_wheel(
    wheel_directory: str,
    config_settings: Mapping[str, object] | None = None,
    metadata_directory: str | None = None,
) -> str:
    """Build a pure Python wheel containing the package source."""

    del config_settings, metadata_directory
    return _build_wheel(Path(wheel_directory), editable=False)


def build_editable(
    wheel_directory: str,
    config_settings: Mapping[str, object] | None = None,
    metadata_directory: str | None = None,
) -> str:
    """Build an editable wheel using a source-tree path file."""

    del config_settings, metadata_directory
    return _build_wheel(Path(wheel_directory), editable=True)


def build_sdist(
    sdist_directory: str,
    config_settings: Mapping[str, object] | None = None,
) -> str:
    """Build a compact source archive for standard packaging workflows."""

    del config_settings
    archive_name = f"{DIST_NAME}-{VERSION}.tar.gz"
    archive_path = Path(sdist_directory) / archive_name
    root_name = f"{DIST_NAME}-{VERSION}"
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    with archive_path.open("wb") as archive_file:
        with GzipFile(filename="", mode="wb", fileobj=archive_file, mtime=0) as gzip_file:
            with tarfile.open(fileobj=gzip_file, mode="w", format=tarfile.GNU_FORMAT) as archive:
                for path in _sdist_files():
                    _add_file_to_tar(
                        archive,
                        f"{root_name}/{path.relative_to(ROOT).as_posix()}",
                        path,
                    )
                _add_bytes_to_tar(archive, f"{root_name}/PKG-INFO", _core_metadata())
    return archive_name


def _write_metadata(metadata_directory: Path) -> str:
    target = metadata_directory / DIST_INFO
    target.mkdir(parents=True, exist_ok=True)
    for relative_path, content in _metadata_files().items():
        (target / relative_path).write_bytes(content)
    license_directory = target / "licenses"
    license_directory.mkdir(exist_ok=True)
    for license_name in LICENSE_FILES:
        (license_directory / license_name).write_bytes((ROOT / license_name).read_bytes())
    return DIST_INFO


def _build_wheel(wheel_directory: Path, *, editable: bool) -> str:
    wheel_directory.mkdir(parents=True, exist_ok=True)
    contents: dict[str, bytes] = {}
    if editable:
        contents[f"{DIST_NAME}.pth"] = f"{SOURCE_ROOT}\n".encode()
    else:
        for path in _package_files():
            contents[path.relative_to(SOURCE_ROOT).as_posix()] = path.read_bytes()
    for relative_path, content in _metadata_files().items():
        contents[f"{DIST_INFO}/{relative_path}"] = content
    for license_name in LICENSE_FILES:
        contents[f"{DIST_INFO}/licenses/{license_name}"] = (ROOT / license_name).read_bytes()
    contents[f"{DIST_INFO}/RECORD"] = _record(contents)

    wheel_path = wheel_directory / WHEEL_NAME
    with ZipFile(wheel_path, "w", compression=ZIP_DEFLATED) as archive:
        for name, content in sorted(contents.items()):
            info = ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            archive.writestr(info, content)
    return WHEEL_NAME


def _metadata_files() -> dict[str, bytes]:
    wheel = "\n".join(
        (
            "Wheel-Version: 1.0",
            "Generator: inference-engineering build backend",
            "Root-Is-Purelib: true",
            "Tag: py3-none-any",
            "",
        )
    ).encode("utf-8")
    entry_points = _entry_points()
    return {"METADATA": _core_metadata(), "WHEEL": wheel, "entry_points.txt": entry_points}


def _core_metadata() -> bytes:
    headers = [
        "Metadata-Version: 2.4",
        f"Name: {PROJECT_NAME}",
        f"Version: {VERSION}",
        f"Summary: {PROJECT.summary}",
        *(f"Author: {author}" for author in PROJECT.authors),
        f"Requires-Python: {PROJECT.requires_python}",
        *(f"Classifier: {classifier}" for classifier in PROJECT.classifiers),
        f"License-Expression: {PROJECT.license_expression}",
        *(f"License-File: {license_file}" for license_file in LICENSE_FILES),
        *(f"Requires-Dist: {dependency}" for dependency in PROJECT.dependencies),
    ]
    for extra, dependencies in PROJECT.optional_dependencies:
        headers.append(f"Provides-Extra: {extra}")
        headers.extend(
            f'Requires-Dist: {dependency} ; extra == "{extra}"' for dependency in dependencies
        )
    headers.append("Description-Content-Type: text/markdown")
    return ("\n".join(headers) + "\n\n" + PROJECT.readme_path.read_text(encoding="utf-8")).encode(
        "utf-8"
    )


def _entry_points() -> bytes:
    """Render console-script entry points declared in the static project table."""

    lines = ["[console_scripts]"]
    lines.extend(f"{name} = {target}" for name, target in PROJECT.scripts)
    return ("\n".join(lines) + "\n").encode("utf-8")


def _record(contents: Mapping[str, bytes]) -> bytes:
    lines = []
    for name, content in sorted(contents.items()):
        digest = urlsafe_b64encode(sha256(content).digest()).decode("ascii").rstrip("=")
        lines.append(f"{name},sha256={digest},{len(content)}")
    lines.append(f"{DIST_INFO}/RECORD,,")
    return ("\n".join(lines) + "\n").encode("utf-8")


def _package_files() -> list[Path]:
    package_root = SOURCE_ROOT / DIST_NAME
    return _tree_files(package_root, frozenset({".py", ".pyi"}), frozenset({"py.typed"}))


def _sdist_files() -> list[Path]:
    files = [ROOT / relative_path for relative_path in ROOT_SOURCE_FILES]
    files.extend(ROOT / license_file for license_file in LICENSE_FILES)
    for relative_directory, suffixes, names in SDIST_TREE_RULES:
        files.extend(_tree_files(ROOT / relative_directory, suffixes, names))
    return sorted({path for path in files if path.is_file()})


def _tree_files(
    directory: Path,
    allowed_suffixes: frozenset[str],
    allowed_names: frozenset[str],
) -> list[Path]:
    if not directory.is_dir():
        return []
    return sorted(
        path
        for path in directory.rglob("*")
        if path.is_file()
        and not path.is_symlink()
        and not _is_excluded(path.relative_to(ROOT))
        and (path.suffix in allowed_suffixes or path.name in allowed_names)
    )


def _is_excluded(relative_path: Path) -> bool:
    return bool(set(relative_path.parts).intersection(EXCLUDED_PARTS))


def _add_bytes_to_tar(archive: tarfile.TarFile, name: str, content: bytes) -> None:
    info = tarfile.TarInfo(name=name)
    info.type = tarfile.REGTYPE
    info.size = len(content)
    info.mode = 0o644
    info.uid = 0
    info.gid = 0
    info.uname = ""
    info.gname = ""
    info.mtime = 0
    info.pax_headers = {}
    archive.addfile(info, BytesIO(content))


def _add_file_to_tar(archive: tarfile.TarFile, name: str, path: Path) -> None:
    """Add a regular source file without preserving host filesystem metadata."""

    _add_bytes_to_tar(archive, name, path.read_bytes())
