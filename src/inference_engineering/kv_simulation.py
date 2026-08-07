"""A small deterministic model of logical KV blocks and physical allocation."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import asdict, dataclass
from enum import StrEnum
from math import ceil
from typing import TypedDict

from inference_engineering.evidence import EvidenceClass, ExperimentRecord, LabeledValue


class AllocationMode(StrEnum):
    """Physical allocation policies represented by the simulator."""

    CONTIGUOUS = "contiguous"
    PAGED = "paged"


class KVEventResult(TypedDict):
    """The declared outcome for one allocator event."""

    action: str
    detail: str
    request_id: str
    status: str
    tick: int


class KVFinalState(TypedDict):
    """The final physical-block accounting state."""

    allocations: list[dict[str, object]]
    evicted_blocks: int
    evicted_request_ids: list[str]
    fragmentation_blocks: int
    free_blocks: int
    largest_free_span: int
    recomputed_blocks: int
    reserved_blocks: int
    total_blocks: int
    used_blocks: int


@dataclass(frozen=True, slots=True)
class KVSimulationConfig:
    """Capacity and policy assumptions for the logical-block simulator."""

    total_blocks: int = 10
    block_size_tokens: int = 4
    allocation_mode: AllocationMode = AllocationMode.PAGED
    auto_evict: bool = True

    def validate(self) -> None:
        if not _is_positive_integer(self.total_blocks):
            raise ValueError("total_blocks must be a positive integer")
        if not _is_positive_integer(self.block_size_tokens):
            raise ValueError("block_size_tokens must be a positive integer")


@dataclass(frozen=True, slots=True)
class KVEvent:
    """One deterministic allocation, release, eviction, or reuse event."""

    tick: int
    action: str
    request_id: str
    tokens: int = 0
    reserve_tokens: int | None = None

    def validate(self) -> None:
        if not _is_non_negative_integer(self.tick):
            raise ValueError("tick must be a non-negative integer")
        if self.action not in {"admit", "release", "evict", "touch"}:
            raise ValueError("event action must be admit, release, evict, or touch")
        if not self.request_id:
            raise ValueError("event request_id must be non-empty")
        if self.action == "admit":
            reserved = self.reserve_tokens if self.reserve_tokens is not None else self.tokens
            if not _is_positive_integer(self.tokens):
                raise ValueError("tokens must be a positive integer")
            if not _is_positive_integer(reserved):
                raise ValueError("reserve_tokens must be a positive integer")
            if reserved < self.tokens:
                raise ValueError("reserve_tokens cannot be smaller than tokens")
            return

        if not _is_non_negative_integer(self.tokens):
            raise ValueError("tokens must be a non-negative integer")
        if self.reserve_tokens is not None and not _is_non_negative_integer(self.reserve_tokens):
            raise ValueError("reserve_tokens must be a non-negative integer")

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(slots=True)
class _Allocation:
    request_id: str
    used_tokens: int
    reserved_tokens: int
    physical_blocks: list[int]
    last_touch_tick: int

    def used_blocks(self, block_size_tokens: int) -> int:
        return ceil(self.used_tokens / block_size_tokens)

    def to_dict(self, block_size_tokens: int) -> dict[str, object]:
        return {
            "logical_to_physical": [
                {"logical_block": index, "physical_block": physical_block}
                for index, physical_block in enumerate(self.physical_blocks)
            ],
            "request_id": self.request_id,
            "reserved_blocks": len(self.physical_blocks),
            "reserved_tokens": self.reserved_tokens,
            "used_blocks": self.used_blocks(block_size_tokens),
            "used_tokens": self.used_tokens,
        }


@dataclass(frozen=True, slots=True)
class KVSimulationResult:
    """Event log and final block accounting from one allocation-policy run."""

    config: KVSimulationConfig
    event_log: Sequence[KVEventResult]
    final_state: KVFinalState

    def to_dict(self) -> dict[str, object]:
        return {
            "config": {
                **asdict(self.config),
                "allocation_mode": self.config.allocation_mode.value,
            },
            "event_log": list(self.event_log),
            "final_state": self.final_state,
        }

    def to_experiment_record(self, events: Sequence[KVEvent]) -> ExperimentRecord:
        """Wrap a simulation run in the repository's versioned record format."""

        state = self.final_state
        return ExperimentRecord(
            record_id=f"kv-{self.config.allocation_mode.value}-v1",
            title=f"{self.config.allocation_mode.value} allocation on a variable-length KV trace",
            result_type=EvidenceClass.SIMULATED,
            hypothesis=(
                "Physical paging can admit a logical allocation when total free blocks are "
                "sufficient but no contiguous span is large enough."
            ),
            workload={
                "events": [event.to_dict() for event in events],
                "time_unit": "abstract scheduler tick",
            },
            environment={
                "execution": "deterministic CPU-only block-allocation simulation",
                "hardware": "not applicable",
            },
            configuration={
                **asdict(self.config),
                "allocation_mode": self.config.allocation_mode.value,
            },
            raw_measurements=(
                LabeledValue(
                    "reserved_blocks",
                    state["reserved_blocks"],
                    "blocks",
                    EvidenceClass.SIMULATED,
                ),
                LabeledValue(
                    "used_blocks",
                    state["used_blocks"],
                    "blocks",
                    EvidenceClass.SIMULATED,
                ),
                LabeledValue(
                    "free_blocks",
                    state["free_blocks"],
                    "blocks",
                    EvidenceClass.SIMULATED,
                ),
            ),
            derived_metrics=(
                LabeledValue(
                    "evicted_blocks",
                    state["evicted_blocks"],
                    "blocks",
                    EvidenceClass.SIMULATED,
                ),
                LabeledValue(
                    "recomputed_blocks",
                    state["recomputed_blocks"],
                    "blocks",
                    EvidenceClass.SIMULATED,
                ),
                LabeledValue(
                    "fragmentation_blocks",
                    state["fragmentation_blocks"],
                    "blocks",
                    EvidenceClass.SIMULATED,
                ),
            ),
            conclusion=(
                "The trace illustrates allocator state transitions only; it does not estimate "
                "runtime transfer, kernel, or quality costs."
            ),
            limitations=(
                "The eviction rule is least-recently-touched and not a recommendation.",
                "All blocks have one fixed token capacity in this abstract model.",
            ),
            artifacts={"event_log": list(self.event_log), "final_state": state},
            sources=(),
        )


class KVBlockSimulator:
    """Maps logical request blocks to a bounded physical block pool."""

    def __init__(self, config: KVSimulationConfig) -> None:
        config.validate()
        self.config = config
        self.free_blocks: set[int] = set(range(config.total_blocks))
        self.allocations: dict[str, _Allocation] = {}
        self.evicted_allocations: dict[str, _Allocation] = {}
        self.evicted_blocks = 0
        self.recomputed_blocks = 0

    def run(self, events: Iterable[KVEvent]) -> KVSimulationResult:
        """Execute ordered events and return an immutable result object."""

        ordered_events = tuple(events)
        previous_tick = -1
        event_log: list[KVEventResult] = []
        for event in ordered_events:
            event.validate()
            if event.tick < previous_tick:
                raise ValueError("events must be ordered by non-decreasing tick")
            previous_tick = event.tick
            event_log.append(self._apply_event(event))
            self.assert_invariants()
        return KVSimulationResult(self.config, event_log, self.snapshot())

    def _apply_event(self, event: KVEvent) -> KVEventResult:
        if event.action == "admit":
            status, detail = self._admit(event)
        elif event.action == "release":
            status, detail = self._release(event)
        elif event.action == "evict":
            status, detail = self._evict_request(event.request_id)
        else:
            status, detail = self._touch(event)
        return {
            "action": event.action,
            "detail": detail,
            "request_id": event.request_id,
            "status": status,
            "tick": event.tick,
        }

    def _admit(self, event: KVEvent) -> tuple[str, str]:
        if event.request_id in self.allocations or event.request_id in self.evicted_allocations:
            return "failed", "request_id is already known"
        reserve_tokens = event.reserve_tokens if event.reserve_tokens is not None else event.tokens
        succeeded, reason = self._allocate(
            event.request_id,
            event.tokens,
            reserve_tokens,
            event.tick,
            recomputation=False,
        )
        return ("allocated", reason) if succeeded else ("failed", reason)

    def _release(self, event: KVEvent) -> tuple[str, str]:
        allocation = self.allocations.pop(event.request_id, None)
        if allocation is not None:
            self.free_blocks.update(allocation.physical_blocks)
            return "released", f"released {len(allocation.physical_blocks)} blocks"
        if self.evicted_allocations.pop(event.request_id, None) is not None:
            return "discarded", "discarded evicted request metadata"
        return "ignored", "request_id is not allocated"

    def _evict_request(self, request_id: str) -> tuple[str, str]:
        allocation = self.allocations.pop(request_id, None)
        if allocation is None:
            return "ignored", "request_id is not allocated"
        self.free_blocks.update(allocation.physical_blocks)
        self.evicted_allocations[request_id] = allocation
        self.evicted_blocks += len(allocation.physical_blocks)
        return "evicted", f"evicted {len(allocation.physical_blocks)} blocks"

    def _touch(self, event: KVEvent) -> tuple[str, str]:
        allocation = self.allocations.get(event.request_id)
        if allocation is not None:
            allocation.last_touch_tick = event.tick
            return "touched", "updated recency for resident allocation"

        evicted = self.evicted_allocations.pop(event.request_id, None)
        if evicted is None:
            return "ignored", "request_id is not known"
        succeeded, reason = self._allocate(
            evicted.request_id,
            evicted.used_tokens,
            evicted.reserved_tokens,
            event.tick,
            recomputation=True,
        )
        if not succeeded:
            self.evicted_allocations[event.request_id] = evicted
            return "failed", reason
        return "recomputed", reason

    def _allocate(
        self,
        request_id: str,
        used_tokens: int,
        reserved_tokens: int,
        tick: int,
        *,
        recomputation: bool,
    ) -> tuple[bool, str]:
        required_blocks = ceil(reserved_tokens / self.config.block_size_tokens)
        if required_blocks > self.config.total_blocks:
            return False, "reservation exceeds total block capacity"

        evictions: list[str] = []
        available_blocks = self.free_blocks
        if len(self.free_blocks) < required_blocks:
            if not self.config.auto_evict:
                return False, "insufficient free blocks"
            eviction_plan = self._plan_evictions(required_blocks, exclude=request_id)
            if eviction_plan is None:
                return False, "insufficient free blocks after eviction"
            evictions, available_blocks = eviction_plan

        blocks = self._select_blocks(required_blocks, free_blocks=available_blocks)
        if blocks is None:
            return False, "free blocks are fragmented for contiguous allocation"
        for victim in evictions:
            self._evict_request(victim)
        self.free_blocks.difference_update(blocks)
        self.allocations[request_id] = _Allocation(
            request_id=request_id,
            used_tokens=used_tokens,
            reserved_tokens=reserved_tokens,
            physical_blocks=blocks,
            last_touch_tick=tick,
        )
        if recomputation:
            self.recomputed_blocks += required_blocks
            return True, f"recomputed {required_blocks} blocks"
        return True, f"allocated {required_blocks} blocks"

    def _plan_evictions(
        self,
        required_blocks: int,
        *,
        exclude: str,
    ) -> tuple[list[str], set[int]] | None:
        """Plan capacity evictions without changing simulator state."""

        planned_allocations = dict(self.allocations)
        planned_free_blocks = set(self.free_blocks)
        evictions: list[str] = []
        while len(planned_free_blocks) < required_blocks:
            victim = self._select_victim_from(planned_allocations, exclude=exclude)
            if victim is None:
                return None
            allocation = planned_allocations.pop(victim)
            planned_free_blocks.update(allocation.physical_blocks)
            evictions.append(victim)
        return evictions, planned_free_blocks

    def _select_blocks(
        self,
        required_blocks: int,
        *,
        free_blocks: set[int] | None = None,
    ) -> list[int] | None:
        available_blocks = self.free_blocks if free_blocks is None else free_blocks
        if self.config.allocation_mode is AllocationMode.PAGED:
            if len(available_blocks) < required_blocks:
                return None
            return sorted(available_blocks)[:required_blocks]

        run_start: int | None = None
        run_length = 0
        previous: int | None = None
        for block in sorted(available_blocks):
            if previous is not None and block == previous + 1:
                run_length += 1
            else:
                run_start = block
                run_length = 1
            if run_length == required_blocks:
                if run_start is None:
                    raise AssertionError("contiguous run has no start")
                return list(range(run_start, run_start + required_blocks))
            previous = block
        return None

    def _select_victim(self, *, exclude: str) -> str | None:
        return self._select_victim_from(self.allocations, exclude=exclude)

    @staticmethod
    def _select_victim_from(
        allocations: dict[str, _Allocation],
        *,
        exclude: str,
    ) -> str | None:
        candidates = [item for request_id, item in allocations.items() if request_id != exclude]
        if not candidates:
            return None
        return min(
            candidates,
            key=lambda allocation: (allocation.last_touch_tick, allocation.request_id),
        ).request_id

    def snapshot(self) -> KVFinalState:
        reserved_blocks = sum(len(item.physical_blocks) for item in self.allocations.values())
        used_blocks = sum(
            item.used_blocks(self.config.block_size_tokens) for item in self.allocations.values()
        )
        largest_free_span = _largest_contiguous_span(self.free_blocks)
        return {
            "allocations": [
                self.allocations[request_id].to_dict(self.config.block_size_tokens)
                for request_id in sorted(self.allocations)
            ],
            "evicted_blocks": self.evicted_blocks,
            "evicted_request_ids": sorted(self.evicted_allocations),
            "fragmentation_blocks": len(self.free_blocks) - largest_free_span,
            "free_blocks": len(self.free_blocks),
            "largest_free_span": largest_free_span,
            "recomputed_blocks": self.recomputed_blocks,
            "reserved_blocks": reserved_blocks,
            "total_blocks": self.config.total_blocks,
            "used_blocks": used_blocks,
        }

    def assert_invariants(self) -> None:
        """Raise if block accounting or logical mapping becomes inconsistent."""

        all_allocated = [
            block
            for allocation in self.allocations.values()
            for block in allocation.physical_blocks
        ]
        if len(all_allocated) != len(set(all_allocated)):
            raise AssertionError("a physical block is assigned to more than one request")
        if any(block < 0 or block >= self.config.total_blocks for block in all_allocated):
            raise AssertionError("allocation contains an out-of-range physical block")
        if any(block < 0 or block >= self.config.total_blocks for block in self.free_blocks):
            raise AssertionError("free block set contains an out-of-range physical block")
        if set(all_allocated).intersection(self.free_blocks):
            raise AssertionError("allocated and free block sets overlap")
        if len(all_allocated) + len(self.free_blocks) != self.config.total_blocks:
            raise AssertionError("reserved plus free blocks must equal total blocks")
        if set(self.allocations).intersection(self.evicted_allocations):
            raise AssertionError("a request cannot be resident and evicted")
        for allocation in self.allocations.values():
            if allocation.used_blocks(self.config.block_size_tokens) > len(
                allocation.physical_blocks
            ):
                raise AssertionError("used blocks cannot exceed reserved blocks")


def kv_trace() -> tuple[KVEvent, ...]:
    """Return a trace that demonstrates fragmentation, eviction, and recomputation."""

    return (
        KVEvent(0, "admit", "alpha", tokens=4, reserve_tokens=8),
        KVEvent(1, "admit", "beta", tokens=8, reserve_tokens=8),
        KVEvent(2, "admit", "gamma", tokens=8, reserve_tokens=8),
        KVEvent(3, "admit", "delta", tokens=8, reserve_tokens=8),
        KVEvent(4, "release", "beta"),
        KVEvent(5, "release", "delta"),
        KVEvent(6, "admit", "epsilon", tokens=18, reserve_tokens=20),
        KVEvent(7, "admit", "zeta", tokens=8, reserve_tokens=12),
        KVEvent(8, "touch", "alpha"),
    )


def simulate_kv(
    events: Iterable[KVEvent] | None = None,
    config: KVSimulationConfig | None = None,
) -> KVSimulationResult:
    """Run the supplied or built-in variable-length allocation trace."""

    return KVBlockSimulator(config or KVSimulationConfig()).run(events or kv_trace())


def _largest_contiguous_span(blocks: set[int]) -> int:
    largest = 0
    current = 0
    previous: int | None = None
    for block in sorted(blocks):
        if previous is not None and block == previous + 1:
            current += 1
        else:
            current = 1
        largest = max(largest, current)
        previous = block
    return largest


def _is_positive_integer(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _is_non_negative_integer(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0
