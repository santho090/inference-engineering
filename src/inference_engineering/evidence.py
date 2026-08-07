"""Versioned, labeled experiment records.

The record format deliberately keeps calculated and simulated values distinct
from measurements and values reported by an external source.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from math import isfinite
from pathlib import Path

SCHEMA_VERSION = "1.0"
PRIMARY_SOURCE_URL_PATTERN = re.compile(r"^(?![\s\S]*\s)https?://[^/?#\s][^\s]*$")


class EvidenceClass(StrEnum):
    """The provenance of an experiment value."""

    MEASURED = "measured"
    SIMULATED = "simulated"
    ESTIMATED = "estimated"
    REPORTED = "reported"


@dataclass(frozen=True, slots=True)
class LabeledValue:
    """A numeric result with a unit and an explicit evidence class."""

    name: str
    value: int | float
    unit: str
    evidence: EvidenceClass
    note: str = ""

    def __post_init__(self) -> None:
        if not _is_finite_number(self.value):
            raise ValueError("value must be a finite number")

    def to_dict(self) -> dict[str, object]:
        data: dict[str, object] = {
            "evidence": self.evidence.value,
            "name": self.name,
            "unit": self.unit,
            "value": self.value,
        }
        if self.note:
            data["note"] = self.note
        return data


@dataclass(frozen=True, slots=True)
class ExperimentRecord:
    """A portable experiment record with stable JSON serialization."""

    record_id: str
    title: str
    result_type: EvidenceClass
    hypothesis: str
    workload: Mapping[str, object]
    environment: Mapping[str, object]
    configuration: Mapping[str, object]
    raw_measurements: Sequence[LabeledValue]
    derived_metrics: Sequence[LabeledValue]
    conclusion: str
    limitations: Sequence[str]
    artifacts: Mapping[str, object] = field(default_factory=dict)
    sources: Sequence[str] = field(default_factory=tuple)
    schema_version: str = SCHEMA_VERSION

    def to_dict(self) -> dict[str, object]:
        data: dict[str, object] = {
            "artifacts": dict(self.artifacts),
            "conclusion": self.conclusion,
            "configuration": dict(self.configuration),
            "derived_metrics": [value.to_dict() for value in self.derived_metrics],
            "environment": dict(self.environment),
            "hypothesis": self.hypothesis,
            "limitations": list(self.limitations),
            "raw_measurements": [value.to_dict() for value in self.raw_measurements],
            "record_id": self.record_id,
            "result_type": self.result_type.value,
            "schema_version": self.schema_version,
            "sources": list(self.sources),
            "title": self.title,
            "workload": dict(self.workload),
        }
        return data

    def to_json(self) -> str:
        """Return canonical JSON suitable for a checked-in fixture."""

        return (
            json.dumps(
                self.to_dict(),
                indent=2,
                sort_keys=True,
                ensure_ascii=False,
                allow_nan=False,
            )
            + "\n"
        )


def load_experiment(path: Path) -> dict[str, object]:
    """Load a JSON experiment record without changing it."""

    with path.open(encoding="utf-8") as handle:
        data = json.load(
            handle,
            parse_constant=_reject_non_standard_json_constant,
            parse_float=_parse_finite_json_float,
        )
    if not isinstance(data, dict):
        raise ValueError("experiment record must be a JSON object")
    return data


def validate_experiment(data: Mapping[str, object]) -> list[str]:
    """Return user-facing validation errors for a version 1.0 record."""

    errors = _validate_json_value(data, "record", set())
    required_strings = (
        "record_id",
        "title",
        "hypothesis",
        "conclusion",
        "schema_version",
        "result_type",
    )
    for key in required_strings:
        value = data.get(key)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{key} must be a non-empty string")

    if data.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION}")

    result_type = data.get("result_type")
    evidence_values = {item.value for item in EvidenceClass}
    if result_type not in evidence_values:
        errors.append("result_type must be measured, simulated, estimated, or reported")

    for key in ("workload", "environment", "configuration", "artifacts"):
        value = data.get(key)
        if not isinstance(value, dict):
            errors.append(f"{key} must be an object")

    limitations = data.get("limitations")
    if (
        not isinstance(limitations, list)
        or not limitations
        or not all(isinstance(item, str) and item.strip() for item in limitations)
    ):
        errors.append("limitations must be a non-empty list of strings")

    sources = data.get("sources")
    if not isinstance(sources, list) or not all(
        isinstance(item, str) and PRIMARY_SOURCE_URL_PATTERN.fullmatch(item) for item in sources
    ):
        errors.append("sources must be a list of http or https URLs")
    elif result_type == EvidenceClass.REPORTED.value and not sources:
        errors.append("reported records require at least one primary source URL")

    for key in ("raw_measurements", "derived_metrics"):
        values = data.get(key)
        if not isinstance(values, list) or not values:
            errors.append(f"{key} must be a non-empty list")
            continue
        for index, value in enumerate(values):
            errors.extend(_validate_labeled_value(key, index, value, result_type))

    return list(dict.fromkeys(errors))


def _reject_non_standard_json_constant(constant: str) -> object:
    """Reject JavaScript-style constants that are not valid JSON numbers."""

    raise ValueError(f"experiment record contains non-standard JSON constant: {constant}")


def _parse_finite_json_float(value: str) -> float:
    """Parse a JSON float while rejecting exponent overflow to infinity."""

    parsed = float(value)
    if not isfinite(parsed):
        raise ValueError(f"experiment record contains a non-finite JSON number: {value}")
    return parsed


def _validate_json_value(value: object, path: str, ancestors: set[int]) -> list[str]:
    """Validate that a direct-Python value has a finite, JSON-compatible shape."""

    if value is None or isinstance(value, (str, bool, int)):
        return []
    if isinstance(value, float):
        if isfinite(value):
            return []
        return [f"{path} must be a finite number"]
    if isinstance(value, dict):
        return _validate_json_mapping(value, path, ancestors)
    if isinstance(value, list):
        return _validate_json_list(value, path, ancestors)
    return [f"{path} must be a JSON-compatible value, not {type(value).__name__}"]


def _validate_json_mapping(
    value: dict[object, object],
    path: str,
    ancestors: set[int],
) -> list[str]:
    """Validate a JSON object recursively and reject cycles by ancestry."""

    container_id = id(value)
    if container_id in ancestors:
        return [f"{path} must not contain a cyclic container"]

    ancestors.add(container_id)
    try:
        errors: list[str] = []
        for key, nested_value in value.items():
            if not isinstance(key, str):
                errors.append(f"{path} has a non-string mapping key")
                continue
            child_path = key if path == "record" else f"{path}.{key}"
            errors.extend(_validate_json_value(nested_value, child_path, ancestors))
        return errors
    finally:
        ancestors.remove(container_id)


def _validate_json_list(value: list[object], path: str, ancestors: set[int]) -> list[str]:
    """Validate a JSON array recursively and reject cycles by ancestry."""

    container_id = id(value)
    if container_id in ancestors:
        return [f"{path} must not contain a cyclic container"]

    ancestors.add(container_id)
    try:
        errors: list[str] = []
        for index, nested_value in enumerate(value):
            errors.extend(_validate_json_value(nested_value, f"{path}[{index}]", ancestors))
        return errors
    finally:
        ancestors.remove(container_id)


def _validate_labeled_value(
    collection: str,
    index: int,
    value: object,
    result_type: object,
) -> list[str]:
    prefix = f"{collection}[{index}]"
    if not isinstance(value, dict):
        return [f"{prefix} must be an object"]

    errors: list[str] = []
    for key in ("name", "unit", "evidence"):
        item = value.get(key)
        if not isinstance(item, str) or not item.strip():
            errors.append(f"{prefix}.{key} must be a non-empty string")

    if "note" in value and not isinstance(value["note"], str):
        errors.append(f"{prefix}.note must be a string")

    numeric_value = value.get("value")
    if not isinstance(numeric_value, (int, float)) or isinstance(numeric_value, bool):
        errors.append(f"{prefix}.value must be a number")
    elif isinstance(numeric_value, float) and not isfinite(numeric_value):
        errors.append(f"{prefix}.value must be a finite number")

    evidence = value.get("evidence")
    allowed = {item.value for item in EvidenceClass}
    if evidence not in allowed:
        errors.append(f"{prefix}.evidence is not a recognized evidence class")
    elif evidence != result_type:
        errors.append(f"{prefix}.evidence must match result_type")
    return errors


def _is_finite_number(value: object) -> bool:
    """Return whether a JSON number is finite without coercing arbitrary integers."""

    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and (not isinstance(value, float) or isfinite(value))
    )
