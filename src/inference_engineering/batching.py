"""Deterministic, deliberately abstract batching simulations.

The simulator models scheduler work units, not a GPU. Its purpose is to make
queueing and phase-interference tradeoffs inspectable with a fixed trace.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import asdict, dataclass
from enum import StrEnum
from math import ceil, isfinite
from typing import TypedDict

from inference_engineering.evidence import EvidenceClass, ExperimentRecord, LabeledValue
from inference_engineering.workloads import Request


class BatchingStrategy(StrEnum):
    """Scheduling policy families represented by the small simulator."""

    STATIC = "static"
    CONTINUOUS = "continuous"
    CHUNKED = "chunked"


class RequestResult(TypedDict):
    """A completed request's timings in the abstract scheduler model."""

    admitted_tick: int
    arrival_tick: int
    completion_latency_ticks: int
    completion_tick: int
    input_tokens: int
    output_tokens: int
    queue_ticks: int
    request_id: str
    ttft_ticks: int


@dataclass(frozen=True, slots=True)
class BatchingConfig:
    """Declared assumptions for the discrete-event scheduler model."""

    max_active_requests: int = 4
    capacity_units_per_tick: int = 4
    batch_bonus_units: int = 1
    static_max_wait_ticks: int = 2
    prefill_chunk_tokens: int = 4
    decode_reserve_units: int = 2
    ttft_objective_ticks: int = 18
    completion_objective_ticks: int = 36
    seed: int = 0
    max_ticks: int = 10_000

    def validate(self) -> None:
        positive_names = (
            "max_active_requests",
            "capacity_units_per_tick",
            "prefill_chunk_tokens",
            "ttft_objective_ticks",
            "completion_objective_ticks",
            "max_ticks",
        )
        values = asdict(self)
        for name in positive_names:
            value = values[name]
            if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
                raise ValueError(f"{name} must be a positive integer")
        for name in ("batch_bonus_units", "static_max_wait_ticks", "decode_reserve_units", "seed"):
            value = values[name]
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise ValueError(f"{name} must be a non-negative integer")
        if self.decode_reserve_units > self.capacity_units_per_tick:
            raise ValueError("decode_reserve_units cannot exceed capacity_units_per_tick")


@dataclass(slots=True)
class _RequestState:
    request: Request
    admitted_tick: int
    remaining_prefill: int
    remaining_decode: int
    phase: str = "prefill"
    first_token_tick: int | None = None
    completion_tick: int | None = None

    @classmethod
    def admit(cls, request: Request, tick: int) -> _RequestState:
        return cls(
            request=request,
            admitted_tick=tick,
            remaining_prefill=request.input_tokens,
            remaining_decode=request.output_tokens,
        )

    @property
    def complete(self) -> bool:
        return self.phase == "complete"

    def result_dict(self) -> RequestResult:
        if self.first_token_tick is None or self.completion_tick is None:
            raise RuntimeError("completed request is missing timing data")
        return {
            "admitted_tick": self.admitted_tick,
            "arrival_tick": self.request.arrival_tick,
            "completion_latency_ticks": self.completion_tick - self.request.arrival_tick,
            "completion_tick": self.completion_tick,
            "input_tokens": self.request.input_tokens,
            "output_tokens": self.request.output_tokens,
            "queue_ticks": self.admitted_tick - self.request.arrival_tick,
            "request_id": self.request.request_id,
            "ttft_ticks": self.first_token_tick - self.request.arrival_tick,
        }


@dataclass(frozen=True, slots=True)
class BatchingSimulationResult:
    """Per-request timings and aggregate metrics from one policy run."""

    strategy: BatchingStrategy
    config: BatchingConfig
    request_results: Sequence[RequestResult]
    aggregate: dict[str, float | int]

    def __post_init__(self) -> None:
        _validate_finite_aggregate(self.aggregate)

    def to_dict(self) -> dict[str, object]:
        _validate_finite_aggregate(self.aggregate)
        return {
            "aggregate": self.aggregate,
            "config": asdict(self.config),
            "per_request": list(self.request_results),
            "strategy": self.strategy.value,
        }

    def to_experiment_record(self, requests: Sequence[Request]) -> ExperimentRecord:
        """Wrap the simulation in the repository's versioned record format."""

        _validate_finite_aggregate(self.aggregate)
        aggregate = self.aggregate
        return ExperimentRecord(
            record_id=f"batching-{self.strategy.value}-v1",
            title=f"{self.strategy.value} batching on the fixed mixed-length trace",
            result_type=EvidenceClass.SIMULATED,
            hypothesis=(
                "Scheduling policy changes the queueing and phase-interference tradeoff "
                "under the declared abstract work model."
            ),
            workload={
                "requests": [request.to_dict() for request in requests],
                "time_unit": "abstract scheduler tick",
            },
            environment={
                "execution": "deterministic CPU-only discrete-event simulation",
                "hardware": "not applicable",
                "seed": self.config.seed,
            },
            configuration={"strategy": self.strategy.value, **asdict(self.config)},
            raw_measurements=(
                LabeledValue(
                    "completed_requests",
                    int(aggregate["completed_requests"]),
                    "requests",
                    EvidenceClass.SIMULATED,
                ),
                LabeledValue(
                    "completed_output_tokens",
                    int(aggregate["completed_output_tokens"]),
                    "tokens",
                    EvidenceClass.SIMULATED,
                ),
            ),
            derived_metrics=(
                LabeledValue(
                    "p95_ttft",
                    float(aggregate["p95_ttft_ticks"]),
                    "ticks",
                    EvidenceClass.SIMULATED,
                ),
                LabeledValue(
                    "output_throughput",
                    float(aggregate["output_tokens_per_tick"]),
                    "tokens per tick",
                    EvidenceClass.SIMULATED,
                ),
                LabeledValue(
                    "goodput",
                    float(aggregate["goodput_requests_per_tick"]),
                    "requests per tick",
                    EvidenceClass.SIMULATED,
                ),
            ),
            conclusion=(
                "Use this result only to compare declared scheduler rules on this trace; "
                "it is not a hardware measurement."
            ),
            limitations=(
                "Work units abstract kernel, memory, and transfer behavior.",
                "The fixed trace is synthetic and does not represent a live workload.",
            ),
            artifacts={"per_request": list(self.request_results)},
            sources=(),
        )


def simulate_batching(
    requests: Iterable[Request],
    strategy: BatchingStrategy,
    config: BatchingConfig | None = None,
) -> BatchingSimulationResult:
    """Run one deterministic scheduling policy against a fixed request sequence."""

    actual_config = config or BatchingConfig()
    actual_config.validate()
    ordered_requests = tuple(requests)
    if not ordered_requests:
        raise ValueError("at least one request is required")
    _validate_requests(ordered_requests)

    unadmitted = sorted(
        ordered_requests, key=lambda request: (request.arrival_tick, request.request_id)
    )
    active: list[_RequestState] = []
    finished: list[_RequestState] = []
    tick = 0

    while len(finished) < len(ordered_requests):
        if tick >= actual_config.max_ticks:
            raise RuntimeError("simulation exceeded max_ticks")

        if strategy is BatchingStrategy.STATIC:
            _admit_static(unadmitted, active, tick, actual_config)
        else:
            _admit_continuous(unadmitted, active, tick, actual_config)

        if active:
            budget = actual_config.capacity_units_per_tick + (
                max(0, len(active) - 1) * actual_config.batch_bonus_units
            )
            _schedule(active, strategy, budget, tick, actual_config)
            completed = [state for state in active if state.complete]
            if completed:
                finished.extend(completed)
                active = [state for state in active if not state.complete]
        tick += 1

    result_by_id = {state.request.request_id: state.result_dict() for state in finished}
    request_results = [result_by_id[request.request_id] for request in ordered_requests]
    aggregate = _aggregate(request_results, actual_config)
    return BatchingSimulationResult(strategy, actual_config, request_results, aggregate)


def run_all_batching_strategies(
    requests: Iterable[Request], config: BatchingConfig | None = None
) -> dict[str, BatchingSimulationResult]:
    """Run all policy variants with exactly the same inputs."""

    frozen_requests = tuple(requests)
    return {
        strategy.value: simulate_batching(frozen_requests, strategy, config)
        for strategy in BatchingStrategy
    }


def _validate_requests(requests: Sequence[Request]) -> None:
    request_ids: set[str] = set()
    for request in requests:
        request.validate()
        if request.request_id in request_ids:
            raise ValueError(f"duplicate request_id: {request.request_id}")
        request_ids.add(request.request_id)


def _ready_requests(unadmitted: Sequence[Request], tick: int) -> list[Request]:
    return sorted(
        (request for request in unadmitted if request.arrival_tick <= tick),
        key=lambda request: (request.priority, request.arrival_tick, request.request_id),
    )


def _admit_static(
    unadmitted: list[Request],
    active: list[_RequestState],
    tick: int,
    config: BatchingConfig,
) -> None:
    if active:
        return
    ready = _ready_requests(unadmitted, tick)
    if not ready:
        return
    oldest_arrival = min(request.arrival_tick for request in ready)
    waited = tick - oldest_arrival
    if len(ready) < config.max_active_requests and waited < config.static_max_wait_ticks:
        return
    for request in ready[: config.max_active_requests]:
        unadmitted.remove(request)
        active.append(_RequestState.admit(request, tick))


def _admit_continuous(
    unadmitted: list[Request],
    active: list[_RequestState],
    tick: int,
    config: BatchingConfig,
) -> None:
    capacity = config.max_active_requests - len(active)
    if capacity <= 0:
        return
    for request in _ready_requests(unadmitted, tick)[:capacity]:
        unadmitted.remove(request)
        active.append(_RequestState.admit(request, tick))


def _schedule(
    active: Sequence[_RequestState],
    strategy: BatchingStrategy,
    budget: int,
    tick: int,
    config: BatchingConfig,
) -> None:
    if strategy is BatchingStrategy.STATIC:
        phase = "prefill" if any(state.phase == "prefill" for state in active) else "decode"
        _serve_phase(active, phase, budget, tick)
        return

    if strategy is BatchingStrategy.CONTINUOUS:
        spent = _serve_phase(active, "prefill", budget, tick)
        _serve_phase(active, "decode", budget - spent, tick)
        return

    reserved_decode = min(config.decode_reserve_units, budget)
    spent = _serve_phase(active, "decode", reserved_decode, tick)
    remaining = budget - spent
    spent += _serve_phase(
        active,
        "prefill",
        remaining,
        tick,
        per_request_limit=config.prefill_chunk_tokens,
    )
    _serve_phase(active, "decode", budget - spent, tick)


def _serve_phase(
    active: Sequence[_RequestState],
    phase: str,
    budget: int,
    tick: int,
    per_request_limit: int | None = None,
) -> int:
    """Spend abstract work units round-robin across states in one phase."""

    candidates = sorted(
        (state for state in active if state.phase == phase),
        key=lambda state: (state.request.priority, state.admitted_tick, state.request.request_id),
    )
    used_by_request: dict[str, int] = {}
    spent = 0
    while spent < budget:
        made_progress = False
        for state in candidates:
            if spent >= budget or state.phase != phase:
                continue
            request_id = state.request.request_id
            if (
                per_request_limit is not None
                and used_by_request.get(request_id, 0) >= per_request_limit
            ):
                continue
            _consume_unit(state, phase, tick)
            used_by_request[request_id] = used_by_request.get(request_id, 0) + 1
            spent += 1
            made_progress = True
        if not made_progress:
            break
    return spent


def _consume_unit(state: _RequestState, phase: str, tick: int) -> None:
    if phase == "prefill":
        state.remaining_prefill -= 1
        if state.remaining_prefill == 0:
            state.phase = "decode"
        return

    state.remaining_decode -= 1
    if state.first_token_tick is None:
        state.first_token_tick = tick + 1
    if state.remaining_decode == 0:
        state.completion_tick = tick + 1
        state.phase = "complete"


def _aggregate(
    request_results: Sequence[RequestResult], config: BatchingConfig
) -> dict[str, float | int]:
    ttfts = [item["ttft_ticks"] for item in request_results]
    completions = [item["completion_latency_ticks"] for item in request_results]
    completion_ticks = [item["completion_tick"] for item in request_results]
    arrival_ticks = [item["arrival_tick"] for item in request_results]
    output_tokens = sum(item["output_tokens"] for item in request_results)
    duration = max(completion_ticks) - min(arrival_ticks)
    duration = max(duration, 1)
    good_requests = sum(
        ttft <= config.ttft_objective_ticks and completion <= config.completion_objective_ticks
        for ttft, completion in zip(ttfts, completions, strict=True)
    )
    return {
        "completed_output_tokens": output_tokens,
        "completed_requests": len(request_results),
        "goodput_request_fraction": good_requests / len(request_results),
        "goodput_requests_per_tick": good_requests / duration,
        "makespan_ticks": duration,
        "output_tokens_per_tick": output_tokens / duration,
        "p50_completion_ticks": _percentile(completions, 0.5),
        "p50_ttft_ticks": _percentile(ttfts, 0.5),
        "p95_completion_ticks": _percentile(completions, 0.95),
        "p95_ttft_ticks": _percentile(ttfts, 0.95),
        "request_throughput_per_tick": len(request_results) / duration,
    }


def _percentile(values: Sequence[int], percentile: float) -> int:
    if not values:
        raise ValueError("cannot calculate a percentile of no values")
    ordered = sorted(values)
    index = max(0, ceil(percentile * len(ordered)) - 1)
    return ordered[index]


def _validate_finite_aggregate(aggregate: dict[str, float | int]) -> None:
    for name, value in aggregate.items():
        if (
            not isinstance(value, (int, float))
            or isinstance(value, bool)
            or (isinstance(value, float) and not isfinite(value))
        ):
            raise ValueError(f"aggregate {name} must be a finite number")
