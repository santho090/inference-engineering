from __future__ import annotations

import copy
import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from typing import cast

from inference_engineering.evidence import (
    SCHEMA_VERSION,
    EvidenceClass,
    LabeledValue,
    load_experiment,
    validate_experiment,
)
from inference_engineering.fixtures import fixture_records

SCHEMA_PATH = (
    Path(__file__).resolve().parents[1] / "docs" / "reference" / "experiment-record.schema.json"
)
PRIMARY_SOURCE_URL_PATTERN = r"^(?![\s\S]*\s)https?://[^/?#\s][^\s]*$"


class UnsupportedJsonValue:
    """A direct-Python value that JSON cannot represent."""


def load_schema() -> dict[str, object]:
    """Load the checked-in schema for focused runtime parity assertions."""

    data = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise AssertionError("experiment record schema must be a JSON object")
    return cast(dict[str, object], data)


def object_value(mapping: dict[str, object], key: str) -> dict[str, object]:
    """Return a schema object member with a useful failure for malformed schema."""

    value = mapping[key]
    if not isinstance(value, dict):
        raise AssertionError(f"schema member {key} must be an object")
    return cast(dict[str, object], value)


def list_value(mapping: dict[str, object], key: str) -> list[object]:
    """Return a schema array member with a useful failure for malformed schema."""

    value = mapping[key]
    if not isinstance(value, list):
        raise AssertionError(f"schema member {key} must be an array")
    return cast(list[object], value)


def result_type_rules(schema: dict[str, object], result_type: str) -> list[dict[str, object]]:
    """Return schema conditionals that apply to one top-level evidence class."""

    rules: list[dict[str, object]] = []
    for candidate in list_value(schema, "allOf"):
        if not isinstance(candidate, dict):
            raise AssertionError("schema conditional must be an object")
        rule = cast(dict[str, object], candidate)
        condition = object_value(rule, "if")
        condition_properties = object_value(condition, "properties")
        condition_result_type = object_value(condition_properties, "result_type")
        if condition_result_type.get("const") == result_type:
            rules.append(rule)
    return rules


class ExperimentRecordTests(unittest.TestCase):
    def _canonical_data(self) -> dict[str, object]:
        return copy.deepcopy(fixture_records()["model-memory.json"].to_dict())

    def _schema_properties(self) -> dict[str, object]:
        return object_value(load_schema(), "properties")

    def _labeled_value_schema(self) -> dict[str, object]:
        definitions = object_value(load_schema(), "$defs")
        return object_value(definitions, "labeledValue")

    def test_all_canonical_records_validate(self) -> None:
        for name, record in fixture_records().items():
            with self.subTest(name=name):
                self.assertEqual(validate_experiment(record.to_dict()), [])

    def test_record_serialization_is_stable(self) -> None:
        record = fixture_records()["batching-chunked.json"]

        self.assertEqual(record.to_json(), record.to_json())
        self.assertIn(f'"schema_version": "{SCHEMA_VERSION}"', record.to_json())

    def test_evidence_mismatch_is_rejected(self) -> None:
        data = copy.deepcopy(fixture_records()["model-memory.json"].to_dict())
        raw_measurements = cast(list[dict[str, object]], data["raw_measurements"])
        first_measurement = raw_measurements[0]
        first_measurement["evidence"] = "simulated"

        errors = validate_experiment(data)

        self.assertIn("raw_measurements[0].evidence must match result_type", errors)

    def test_reported_record_requires_source(self) -> None:
        data = copy.deepcopy(fixture_records()["model-memory.json"].to_dict())
        data["result_type"] = "reported"
        for collection in ("raw_measurements", "derived_metrics"):
            values = cast(list[dict[str, object]], data[collection])
            for value in values:
                value["evidence"] = "reported"

        errors = validate_experiment(data)

        self.assertIn("reported records require at least one primary source URL", errors)

    def test_schema_constrains_reported_sources_and_evidence_matches(self) -> None:
        schema = load_schema()
        reported_rules = result_type_rules(schema, "reported")
        source_rule = next(
            (
                rule
                for rule in reported_rules
                if "sources" in object_value(object_value(rule, "then"), "properties")
            ),
            None,
        )
        self.assertIsNotNone(source_rule)
        if source_rule is None:
            return
        source_properties = object_value(object_value(source_rule, "then"), "properties")
        self.assertEqual(object_value(source_properties, "sources")["minItems"], 1)

        for evidence in ("measured", "simulated", "estimated", "reported"):
            with self.subTest(evidence=evidence):
                matching_rules = result_type_rules(schema, evidence)
                metric_rule = next(
                    (
                        rule
                        for rule in matching_rules
                        if "raw_measurements"
                        in object_value(object_value(rule, "then"), "properties")
                    ),
                    None,
                )
                self.assertIsNotNone(metric_rule)
                if metric_rule is None:
                    continue
                metric_properties = object_value(object_value(metric_rule, "then"), "properties")
                expected_reference = f"#/$defs/{evidence}LabeledValue"
                for collection in ("raw_measurements", "derived_metrics"):
                    collection_schema = object_value(metric_properties, collection)
                    item_schema = object_value(collection_schema, "items")
                    self.assertEqual(item_schema["$ref"], expected_reference)

    def test_empty_limitations_are_rejected(self) -> None:
        data = self._canonical_data()
        data["limitations"] = []

        errors = validate_experiment(data)

        self.assertIn("limitations must be a non-empty list of strings", errors)

    def test_optional_labeled_value_note_is_a_string_in_schema_and_runtime(self) -> None:
        data = self._canonical_data()
        raw_measurements = cast(list[dict[str, object]], data["raw_measurements"])
        raw_measurements[0]["note"] = "Measured with the fixture inputs."

        self.assertEqual(validate_experiment(data), [])

        raw_measurements[0]["note"] = 7
        errors = validate_experiment(data)

        self.assertIn("raw_measurements[0].note must be a string", errors)
        labeled_properties = object_value(self._labeled_value_schema(), "properties")
        note_schema = object_value(labeled_properties, "note")
        self.assertEqual(note_schema["type"], "string")
        labeled_required = self._labeled_value_schema().get("required", [])
        if not isinstance(labeled_required, list):
            self.fail("labeled value required fields must be an array")
        self.assertNotIn("note", labeled_required)

    def test_source_url_schemes_and_types_match_schema_and_runtime(self) -> None:
        source_schema = object_value(self._schema_properties(), "sources")
        item_schema = object_value(source_schema, "items")
        self.assertEqual(item_schema["type"], "string")
        self.assertEqual(item_schema["pattern"], PRIMARY_SOURCE_URL_PATTERN)

        for source in ("https://primary.example/source", "http://primary.example/source"):
            with self.subTest(valid_source=source):
                data = self._canonical_data()
                data["sources"] = [source]
                self.assertEqual(validate_experiment(data), [])

        invalid_sources: tuple[object, ...] = (
            "ftp://primary.example/source",
            "file:///tmp/source",
            "https://",
            "https:///missing-authority",
            " https://primary.example/source",
            7,
        )
        for invalid_source in invalid_sources:
            with self.subTest(invalid_source=invalid_source):
                data = self._canonical_data()
                data["sources"] = [invalid_source]
                self.assertIn(
                    "sources must be a list of http or https URLs",
                    validate_experiment(data),
                )

    def test_whitespace_only_strings_are_rejected_by_schema_and_runtime(self) -> None:
        schema_properties = self._schema_properties()
        required_strings = (
            "record_id",
            "title",
            "hypothesis",
            "conclusion",
            "schema_version",
            "result_type",
        )
        for key in required_strings:
            with self.subTest(required_string=key):
                property_schema = object_value(schema_properties, key)
                self.assertEqual(property_schema["type"], "string")
                self.assertEqual(property_schema["pattern"], r"\S")

                data = self._canonical_data()
                data[key] = " \t "
                self.assertIn(f"{key} must be a non-empty string", validate_experiment(data))

        limitations_schema = object_value(schema_properties, "limitations")
        self.assertEqual(limitations_schema["minItems"], 1)
        limitation_schema = object_value(limitations_schema, "items")
        self.assertEqual(limitation_schema["type"], "string")
        self.assertEqual(limitation_schema["pattern"], r"\S")
        data = self._canonical_data()
        data["limitations"] = [" \t "]
        self.assertIn("limitations must be a non-empty list of strings", validate_experiment(data))

        labeled_properties = object_value(self._labeled_value_schema(), "properties")
        for key in ("name", "unit", "evidence"):
            with self.subTest(labeled_string=key):
                property_schema = object_value(labeled_properties, key)
                self.assertEqual(property_schema["type"], "string")
                self.assertEqual(property_schema["pattern"], r"\S")

                data = self._canonical_data()
                raw_measurements = cast(list[dict[str, object]], data["raw_measurements"])
                raw_measurements[0][key] = " \t "
                self.assertIn(
                    f"raw_measurements[0].{key} must be a non-empty string",
                    validate_experiment(data),
                )

    def test_numeric_booleans_and_empty_metric_arrays_are_rejected(self) -> None:
        labeled_properties = object_value(self._labeled_value_schema(), "properties")
        self.assertEqual(object_value(labeled_properties, "value")["type"], "number")

        for boolean_value in (True, False):
            with self.subTest(boolean_value=boolean_value):
                data = self._canonical_data()
                raw_measurements = cast(list[dict[str, object]], data["raw_measurements"])
                raw_measurements[0]["value"] = boolean_value
                self.assertIn(
                    "raw_measurements[0].value must be a number",
                    validate_experiment(data),
                )

        schema_properties = self._schema_properties()
        for collection in ("raw_measurements", "derived_metrics"):
            with self.subTest(collection=collection):
                collection_schema = object_value(schema_properties, collection)
                self.assertEqual(collection_schema["minItems"], 1)

                data = self._canonical_data()
                data[collection] = []
                self.assertIn(f"{collection} must be a non-empty list", validate_experiment(data))

    def test_non_finite_labeled_values_are_rejected_and_never_serialized(self) -> None:
        for invalid_value in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(invalid_value=invalid_value):
                with self.assertRaisesRegex(ValueError, "value must be a finite number"):
                    LabeledValue("metric", invalid_value, "units", EvidenceClass.ESTIMATED)

                data = self._canonical_data()
                raw_measurements = cast(list[dict[str, object]], data["raw_measurements"])
                raw_measurements[0]["value"] = invalid_value
                self.assertIn(
                    "raw_measurements[0].value must be a finite number",
                    validate_experiment(data),
                )

                record = replace(
                    fixture_records()["model-memory.json"],
                    artifacts={"invalid_value": invalid_value},
                )
                with self.assertRaisesRegex(ValueError, "Out of range float values"):
                    record.to_json()

    def test_non_finite_nested_values_are_rejected_in_every_metadata_object(self) -> None:
        metadata_fields = (
            "workload",
            "environment",
            "configuration",
            "artifacts",
            "future_extension",
        )
        for field in metadata_fields:
            for invalid_value in (float("nan"), float("inf"), float("-inf")):
                with self.subTest(field=field, invalid_value=invalid_value):
                    data = self._canonical_data()
                    if field == "future_extension":
                        metadata: dict[str, object] = {}
                        data[field] = metadata
                    else:
                        metadata = cast(dict[str, object], data[field])
                    metadata["nested"] = {"values": [{"bad": invalid_value}]}

                    self.assertIn(
                        f"{field}.nested.values[0].bad must be a finite number",
                        validate_experiment(data),
                    )

    def test_unknown_json_compatible_properties_remain_permitted(self) -> None:
        data = self._canonical_data()
        data["future_extension"] = {
            "nested": [None, True, False, 7, 2.5, {"kept": "value"}],
        }

        self.assertEqual(validate_experiment(data), [])

    def test_non_json_direct_values_and_mapping_keys_are_rejected(self) -> None:
        for invalid_value in (
            ("not", "a", "json", "array"),
            {"not", "a", "json", "array"},
            UnsupportedJsonValue(),
        ):
            with self.subTest(value_type=type(invalid_value).__name__):
                data = self._canonical_data()
                workload = cast(dict[str, object], data["workload"])
                workload["nested"] = invalid_value

                self.assertIn(
                    "workload.nested must be a JSON-compatible value, not "
                    f"{type(invalid_value).__name__}",
                    validate_experiment(data),
                )

        data = self._canonical_data()
        data["environment"] = {7: "not a JSON object key"}
        self.assertIn(
            "environment has a non-string mapping key",
            validate_experiment(data),
        )

    def test_cyclic_containers_are_rejected_without_recursive_failure(self) -> None:
        cyclic_mapping: dict[str, object] = {}
        cyclic_mapping["self"] = cyclic_mapping
        cyclic_list: list[object] = []
        cyclic_list.append(cyclic_list)

        for cyclic_value, path in (
            (cyclic_mapping, "artifacts.nested.self"),
            (cyclic_list, "artifacts.nested[0]"),
        ):
            with self.subTest(path=path):
                data = self._canonical_data()
                artifacts = cast(dict[str, object], data["artifacts"])
                artifacts["nested"] = cyclic_value

                self.assertIn(
                    f"{path} must not contain a cyclic container",
                    validate_experiment(data),
                )

    def test_load_experiment_rejects_non_standard_json_constants(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "invalid.json"
            for constant in ("NaN", "Infinity", "-Infinity"):
                with self.subTest(constant=constant):
                    path.write_text(f'{{"unknown": {constant}}}', encoding="utf-8")

                    with self.assertRaisesRegex(
                        ValueError,
                        f"non-standard JSON constant: {constant}",
                    ):
                        load_experiment(path)

    def test_load_experiment_rejects_json_float_overflow(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "invalid.json"
            path.write_text('{"unknown": 1e9999}', encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "non-finite JSON number: 1e9999"):
                load_experiment(path)

    def test_unknown_properties_remain_permitted(self) -> None:
        schema = load_schema()
        self.assertNotIn("additionalProperties", schema)

        data = self._canonical_data()
        data["future_extension"] = {"kept": True}
        self.assertEqual(validate_experiment(data), [])
