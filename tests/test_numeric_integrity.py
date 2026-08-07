from __future__ import annotations

import unittest
from dataclasses import replace
from typing import Any, cast

from inference_engineering.batching import BatchingConfig
from inference_engineering.kv_simulation import KVEvent, KVSimulationConfig
from inference_engineering.memory import human_bytes
from inference_engineering.workloads import Request


class IntegerBoundaryTests(unittest.TestCase):
    def test_non_finite_values_are_rejected_by_integer_typed_public_inputs(self) -> None:
        request = Request("request", 0, 4, 2, shared_prefix_tokens=1, priority=0)
        for invalid_value in (float("nan"), float("inf"), float("-inf")):
            for field_name in (
                "arrival_tick",
                "input_tokens",
                "output_tokens",
                "shared_prefix_tokens",
                "priority",
            ):
                with self.subTest(record="request", field_name=field_name, value=invalid_value):
                    with self.assertRaisesRegex(ValueError, f"{field_name} must be an integer"):
                        replace(cast(Any, request), **{field_name: invalid_value}).validate()

            for field_name in ("total_blocks", "block_size_tokens"):
                with self.subTest(record="kv_config", field_name=field_name, value=invalid_value):
                    with self.assertRaisesRegex(
                        ValueError, f"{field_name} must be a positive integer"
                    ):
                        replace(
                            cast(Any, KVSimulationConfig()), **{field_name: invalid_value}
                        ).validate()

            with self.subTest(record="kv_event_tick", value=invalid_value):
                with self.assertRaisesRegex(ValueError, "tick must be a non-negative integer"):
                    KVEvent(cast(Any, invalid_value), "admit", "request", tokens=1).validate()

            for field_name in ("tokens", "reserve_tokens"):
                with self.subTest(record="kv_event", field_name=field_name, value=invalid_value):
                    with self.assertRaisesRegex(
                        ValueError, f"{field_name} must be a positive integer"
                    ):
                        replace(
                            cast(Any, KVEvent(0, "admit", "request", tokens=1, reserve_tokens=1)),
                            **{field_name: invalid_value},
                        ).validate()

            for field_name in ("tokens", "reserve_tokens"):
                with self.subTest(
                    record="non_admit_kv_event", field_name=field_name, value=invalid_value
                ):
                    with self.assertRaisesRegex(
                        ValueError, f"{field_name} must be a non-negative integer"
                    ):
                        replace(
                            cast(Any, KVEvent(0, "release", "request")),
                            **{field_name: invalid_value},
                        ).validate()

            with self.subTest(record="batching_config", value=invalid_value):
                with self.assertRaisesRegex(ValueError, "max_ticks must be a positive integer"):
                    BatchingConfig(max_ticks=cast(Any, invalid_value)).validate()

            with self.subTest(record="human_bytes", value=invalid_value):
                with self.assertRaisesRegex(ValueError, "value must be an integer"):
                    human_bytes(cast(Any, invalid_value))
