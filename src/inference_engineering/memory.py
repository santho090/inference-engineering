"""Memory estimates with explicit assumptions and validation."""

from __future__ import annotations

from dataclasses import asdict, dataclass

GIB = 1024**3


def human_bytes(value: int) -> str:
    """Format a byte count using binary units."""

    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("value must be an integer")
    units = ("B", "KiB", "MiB", "GiB", "TiB")
    amount = float(value)
    for unit in units:
        if amount < 1024.0 or unit == units[-1]:
            return f"{amount:.2f} {unit}"
        amount /= 1024.0
    raise AssertionError("unreachable")


@dataclass(frozen=True, slots=True)
class ModelMemoryConfig:
    """Inputs for a lower-bound model-residency estimate."""

    parameter_count: int
    weight_bytes: int
    layers: int
    hidden_size: int
    batch_size: int
    sequence_length: int
    activation_bytes: int = 2
    activation_tensors: int = 2

    def validate(self) -> None:
        _require_positive_ints(asdict(self))


@dataclass(frozen=True, slots=True)
class ModelMemoryEstimate:
    """Estimated persistent weights and one layer's working activations."""

    weights_bytes: int
    activation_bytes: int
    total_bytes: int

    def to_dict(self) -> dict[str, object]:
        return {
            "activation_bytes": self.activation_bytes,
            "activation_human": human_bytes(self.activation_bytes),
            "total_bytes": self.total_bytes,
            "total_human": human_bytes(self.total_bytes),
            "weights_bytes": self.weights_bytes,
            "weights_human": human_bytes(self.weights_bytes),
        }


def estimate_model_memory(config: ModelMemoryConfig) -> ModelMemoryEstimate:
    """Estimate weights plus a configurable one-layer activation working set."""

    config.validate()
    weights = config.parameter_count * config.weight_bytes
    activations = (
        config.batch_size
        * config.sequence_length
        * config.hidden_size
        * config.activation_bytes
        * config.activation_tensors
    )
    return ModelMemoryEstimate(
        weights_bytes=weights,
        activation_bytes=activations,
        total_bytes=weights + activations,
    )


@dataclass(frozen=True, slots=True)
class KVMemoryConfig:
    """Inputs for a per-sequence key-value cache estimate."""

    layers: int
    attention_heads: int
    kv_heads: int
    head_dim: int
    tokens_per_sequence: int
    concurrent_sequences: int
    element_bytes: int = 2

    def validate(self) -> None:
        _require_positive_ints(asdict(self))
        if self.kv_heads > self.attention_heads:
            raise ValueError("kv_heads cannot exceed attention_heads")
        if self.attention_heads % self.kv_heads != 0:
            raise ValueError("attention_heads must be divisible by kv_heads")


@dataclass(frozen=True, slots=True)
class KVMemoryEstimate:
    """KV cache quantities before allocator overhead and reservation slack."""

    bytes_per_token: int
    bytes_per_sequence: int
    total_bytes: int
    kv_group_size: int

    def to_dict(self) -> dict[str, object]:
        return {
            "bytes_per_sequence": self.bytes_per_sequence,
            "bytes_per_sequence_human": human_bytes(self.bytes_per_sequence),
            "bytes_per_token": self.bytes_per_token,
            "bytes_per_token_human": human_bytes(self.bytes_per_token),
            "kv_group_size": self.kv_group_size,
            "total_bytes": self.total_bytes,
            "total_human": human_bytes(self.total_bytes),
        }


def estimate_kv_memory(config: KVMemoryConfig) -> KVMemoryEstimate:
    """Estimate K and V storage for the declared concurrent sequences."""

    config.validate()
    bytes_per_token = config.layers * config.kv_heads * config.head_dim * 2 * config.element_bytes
    per_sequence = bytes_per_token * config.tokens_per_sequence
    total = per_sequence * config.concurrent_sequences
    return KVMemoryEstimate(
        bytes_per_token=bytes_per_token,
        bytes_per_sequence=per_sequence,
        total_bytes=total,
        kv_group_size=config.attention_heads // config.kv_heads,
    )


def _require_positive_ints(values: dict[str, int]) -> None:
    for name, value in values.items():
        if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
            raise ValueError(f"{name} must be a positive integer")
