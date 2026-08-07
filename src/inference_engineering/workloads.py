"""Synthetic workload descriptions and a deterministic request trace."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True, slots=True)
class Request:
    """One admitted request in the abstract scheduler model."""

    request_id: str
    arrival_tick: int
    input_tokens: int
    output_tokens: int
    shared_prefix_tokens: int = 0
    model: str = "example-transformer"
    priority: int = 0

    def validate(self) -> None:
        if not self.request_id:
            raise ValueError("request_id must be non-empty")
        _require_integers(
            {
                "arrival_tick": self.arrival_tick,
                "input_tokens": self.input_tokens,
                "output_tokens": self.output_tokens,
                "shared_prefix_tokens": self.shared_prefix_tokens,
                "priority": self.priority,
            }
        )
        if self.arrival_tick < 0:
            raise ValueError("arrival_tick must be non-negative")
        if self.input_tokens <= 0 or self.output_tokens <= 0:
            raise ValueError("input_tokens and output_tokens must be positive")
        if not 0 <= self.shared_prefix_tokens <= self.input_tokens:
            raise ValueError("shared_prefix_tokens must be between zero and input_tokens")
        if not self.model:
            raise ValueError("model must be non-empty")

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def synthetic_workload_archetypes() -> dict[str, dict[str, object]]:
    """Return four public, synthetic workload archetypes for documentation."""

    return {
        "interactive-chat": {
            "arrival_distribution": "steady with short bursts",
            "prompt_length_distribution": "short to medium",
            "output_length_distribution": "medium",
            "prefix_reuse": "low",
            "models": ["chat-model"],
            "priorities": ["interactive"],
            "objectives": {"ttft": "tight", "tpot": "tight"},
        },
        "shared-prefix-retrieval": {
            "arrival_distribution": "bursty",
            "prompt_length_distribution": "medium with repeated source prefix",
            "output_length_distribution": "short",
            "prefix_reuse": "high",
            "models": ["retrieval-model"],
            "priorities": ["interactive"],
            "objectives": {"ttft": "tight", "cost": "bounded"},
        },
        "long-context-analysis": {
            "arrival_distribution": "low rate with large requests",
            "prompt_length_distribution": "long",
            "output_length_distribution": "medium",
            "prefix_reuse": "low",
            "models": ["long-context-model"],
            "priorities": ["standard"],
            "objectives": {"ttft": "bounded", "completion": "bounded"},
        },
        "mixed-priority-batch": {
            "arrival_distribution": "bursty and mixed",
            "prompt_length_distribution": "short to long",
            "output_length_distribution": "short to long",
            "prefix_reuse": "mixed",
            "models": ["small-model", "large-model"],
            "priorities": ["interactive", "standard", "deferred"],
            "objectives": {"goodput": "maximize subject to objectives"},
        },
    }


def batching_trace() -> tuple[Request, ...]:
    """Return a fixed mixed-length trace for scheduler comparisons."""

    trace = (
        Request("r1", 0, 8, 8, priority=0),
        Request("r2", 0, 12, 4, priority=0),
        Request("r3", 1, 4, 12, priority=1),
        Request("r4", 2, 16, 4, priority=0),
        Request("r5", 3, 6, 10, priority=1),
        Request("r6", 5, 10, 6, priority=0),
        Request("r7", 6, 3, 14, priority=1),
        Request("r8", 8, 14, 5, priority=0),
    )
    for request in trace:
        request.validate()
    return trace


def _require_integers(values: dict[str, int]) -> None:
    for name, value in values.items():
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError(f"{name} must be an integer")
