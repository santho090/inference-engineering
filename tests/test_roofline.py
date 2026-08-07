from __future__ import annotations

import unittest
from dataclasses import replace

from inference_engineering.roofline import RooflineConfig, estimate_roofline


class RooflineTests(unittest.TestCase):
    def test_compute_bound_estimate_uses_compute_ceiling(self) -> None:
        estimate = estimate_roofline(
            RooflineConfig(
                operations=1_000.0,
                bytes_moved=10.0,
                peak_operations_per_second=50.0,
                bandwidth_bytes_per_second=10.0,
            )
        )

        self.assertEqual(estimate.arithmetic_intensity, 100.0)
        self.assertEqual(estimate.bandwidth_ceiling, 1_000.0)
        self.assertEqual(estimate.upper_bound, 50.0)
        self.assertEqual(estimate.limiting_resource, "compute")

    def test_bandwidth_bound_estimate_uses_bandwidth_ceiling(self) -> None:
        estimate = estimate_roofline(
            RooflineConfig(
                operations=10.0,
                bytes_moved=10.0,
                peak_operations_per_second=500.0,
                bandwidth_bytes_per_second=100.0,
            )
        )

        self.assertEqual(estimate.upper_bound, 100.0)
        self.assertEqual(estimate.limiting_resource, "memory_bandwidth")

    def test_invalid_roofline_input_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "bytes_moved"):
            estimate_roofline(RooflineConfig(1.0, 0.0, 1.0, 1.0))

    def test_non_finite_roofline_inputs_and_results_are_rejected(self) -> None:
        baseline = RooflineConfig(1.0, 1.0, 1.0, 1.0)
        for field_name in (
            "operations",
            "bytes_moved",
            "peak_operations_per_second",
            "bandwidth_bytes_per_second",
        ):
            for invalid_value in (float("nan"), float("inf"), float("-inf")):
                with self.subTest(field_name=field_name, invalid_value=invalid_value):
                    config = replace(baseline, **{field_name: invalid_value})
                    with self.assertRaisesRegex(ValueError, f"{field_name}.*finite"):
                        estimate_roofline(config)

        overflowing = RooflineConfig(
            operations=1e308,
            bytes_moved=1e-308,
            peak_operations_per_second=1e308,
            bandwidth_bytes_per_second=1e308,
        )
        with self.assertRaisesRegex(ValueError, "arithmetic_intensity.*finite"):
            estimate_roofline(overflowing)
