from __future__ import annotations

import unittest

from inference_engineering.kv_simulation import (
    AllocationMode,
    KVEvent,
    KVSimulationConfig,
    simulate_kv,
)


class KVSimulationTests(unittest.TestCase):
    def test_paging_admits_fragmented_request_that_contiguous_rejects(self) -> None:
        paged = simulate_kv(config=KVSimulationConfig(allocation_mode=AllocationMode.PAGED))
        contiguous = simulate_kv(
            config=KVSimulationConfig(allocation_mode=AllocationMode.CONTIGUOUS)
        )

        paged_epsilon = next(item for item in paged.event_log if item["request_id"] == "epsilon")
        contiguous_epsilon = next(
            item for item in contiguous.event_log if item["request_id"] == "epsilon"
        )
        self.assertEqual(paged_epsilon["status"], "allocated")
        self.assertEqual(contiguous_epsilon["status"], "failed")

    def test_default_trace_exposes_eviction_and_recomputation(self) -> None:
        result = simulate_kv()

        self.assertGreater(result.final_state["evicted_blocks"], 0)
        self.assertGreater(result.final_state["recomputed_blocks"], 0)
        self.assertEqual(
            result.final_state["reserved_blocks"] + result.final_state["free_blocks"],
            result.final_state["total_blocks"],
        )

    def test_no_auto_evict_reports_capacity_failure(self) -> None:
        result = simulate_kv(config=KVSimulationConfig(auto_evict=False))

        zeta = next(item for item in result.event_log if item["request_id"] == "zeta")
        self.assertEqual(zeta["status"], "failed")

    def test_failed_contiguous_admission_preserves_allocator_state(self) -> None:
        config = KVSimulationConfig(allocation_mode=AllocationMode.CONTIGUOUS)
        setup_events = tuple(
            KVEvent(tick, "admit", request_id, tokens=4)
            for tick, request_id in enumerate("abcdefghij")
        ) + (
            KVEvent(10, "release", "b"),
            KVEvent(11, "release", "d"),
            KVEvent(12, "release", "f"),
            KVEvent(13, "release", "h"),
        )
        baseline = simulate_kv(setup_events, config)
        failed_admission = KVEvent(14, "admit", "x", tokens=20)
        result = simulate_kv((*setup_events, failed_admission), config)

        self.assertEqual(result.final_state, baseline.final_state)
        self.assertEqual(result.event_log[:-1], baseline.event_log)
        self.assertEqual(
            result.event_log[-1],
            {
                "action": "admit",
                "detail": "free blocks are fragmented for contiguous allocation",
                "request_id": "x",
                "status": "failed",
                "tick": 14,
            },
        )
        self.assertEqual(result.final_state["evicted_blocks"], 0)
        self.assertEqual(result.final_state["evicted_request_ids"], [])
        allocations = {item["request_id"]: item for item in result.final_state["allocations"]}
        self.assertEqual(
            allocations["a"]["logical_to_physical"],
            [{"logical_block": 0, "physical_block": 0}],
        )

    def test_contiguous_admission_commits_eviction_after_successful_preflight(self) -> None:
        result = simulate_kv(
            (
                KVEvent(0, "admit", "a", tokens=12),
                KVEvent(1, "admit", "b", tokens=4),
                KVEvent(2, "admit", "c", tokens=16),
                KVEvent(3, "release", "b"),
                KVEvent(4, "admit", "x", tokens=16),
            ),
            KVSimulationConfig(allocation_mode=AllocationMode.CONTIGUOUS),
        )

        admission = result.event_log[-1]
        self.assertEqual(admission["status"], "allocated")
        self.assertEqual(result.final_state["evicted_blocks"], 3)
        self.assertEqual(result.final_state["evicted_request_ids"], ["a"])
        allocations = {item["request_id"]: item for item in result.final_state["allocations"]}
        self.assertEqual(
            allocations["x"]["logical_to_physical"],
            [
                {"logical_block": 0, "physical_block": 0},
                {"logical_block": 1, "physical_block": 1},
                {"logical_block": 2, "physical_block": 2},
                {"logical_block": 3, "physical_block": 3},
            ],
        )
