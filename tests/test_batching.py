from __future__ import annotations

import unittest
from dataclasses import replace

from inference_engineering.batching import (
    BatchingStrategy,
    run_all_batching_strategies,
    simulate_batching,
)
from inference_engineering.workloads import Request, batching_trace


class BatchingSimulationTests(unittest.TestCase):
    def test_fixed_trace_is_byte_stable(self) -> None:
        first = simulate_batching(batching_trace(), BatchingStrategy.CHUNKED).to_experiment_record(
            batching_trace()
        )
        second = simulate_batching(batching_trace(), BatchingStrategy.CHUNKED).to_experiment_record(
            batching_trace()
        )

        self.assertEqual(first.to_json(), second.to_json())

    def test_each_strategy_completes_every_request(self) -> None:
        results = run_all_batching_strategies(batching_trace())

        for name, result in results.items():
            with self.subTest(strategy=name):
                self.assertEqual(result.aggregate["completed_requests"], len(batching_trace()))
                self.assertTrue(all(int(item["ttft_ticks"]) > 0 for item in result.request_results))
                self.assertTrue(
                    all(
                        int(item["completion_latency_ticks"]) >= int(item["ttft_ticks"])
                        for item in result.request_results
                    )
                )

    def test_fixed_trace_exposes_throughput_tail_tradeoff(self) -> None:
        results = run_all_batching_strategies(batching_trace())
        continuous = results["continuous"].aggregate
        chunked = results["chunked"].aggregate

        self.assertLess(chunked["p95_ttft_ticks"], continuous["p95_ttft_ticks"])
        self.assertLess(chunked["output_tokens_per_tick"], continuous["output_tokens_per_tick"])

    def test_duplicate_request_ids_are_rejected(self) -> None:
        requests = (Request("same", 0, 1, 1), Request("same", 1, 1, 1))

        with self.assertRaisesRegex(ValueError, "duplicate"):
            simulate_batching(requests, BatchingStrategy.CONTINUOUS)

    def test_non_finite_aggregate_metrics_are_rejected(self) -> None:
        result = simulate_batching(batching_trace(), BatchingStrategy.CHUNKED)
        for invalid_value in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(invalid_value=invalid_value):
                aggregate = {**result.aggregate, "goodput_request_fraction": invalid_value}
                with self.assertRaisesRegex(
                    ValueError, "aggregate goodput_request_fraction must be a finite number"
                ):
                    replace(result, aggregate=aggregate)
