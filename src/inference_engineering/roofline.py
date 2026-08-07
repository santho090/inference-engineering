"""A small roofline calculator for explanatory estimates."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from math import isfinite


@dataclass(frozen=True, slots=True)
class RooflineConfig:
    """Operation and qualified-device assumptions for one roofline estimate."""

    operations: float
    bytes_moved: float
    peak_operations_per_second: float
    bandwidth_bytes_per_second: float

    def validate(self) -> None:
        for name, value in asdict(self).items():
            if (
                not isinstance(value, (int, float))
                or isinstance(value, bool)
                or (isinstance(value, float) and not isfinite(value))
                or value <= 0
            ):
                raise ValueError(f"{name} must be a positive finite number")


@dataclass(frozen=True, slots=True)
class RooflineEstimate:
    """Arithmetic intensity and the corresponding idealized upper bound."""

    arithmetic_intensity: float
    compute_ceiling: float
    bandwidth_ceiling: float
    upper_bound: float
    limiting_resource: str

    def __post_init__(self) -> None:
        for name, value in asdict(self).items():
            if name == "limiting_resource":
                continue
            if (
                not isinstance(value, (int, float))
                or isinstance(value, bool)
                or (isinstance(value, float) and not isfinite(value))
            ):
                raise ValueError(f"{name} must be a finite number")

    def to_dict(self) -> dict[str, object]:
        return {
            "arithmetic_intensity_operations_per_byte": self.arithmetic_intensity,
            "bandwidth_ceiling_operations_per_second": self.bandwidth_ceiling,
            "compute_ceiling_operations_per_second": self.compute_ceiling,
            "limiting_resource": self.limiting_resource,
            "upper_bound_operations_per_second": self.upper_bound,
        }


def estimate_roofline(config: RooflineConfig) -> RooflineEstimate:
    """Return an idealized roofline bound, never a throughput prediction."""

    config.validate()
    intensity = config.operations / config.bytes_moved
    bandwidth_ceiling = intensity * config.bandwidth_bytes_per_second
    upper_bound = min(config.peak_operations_per_second, bandwidth_ceiling)
    limiting_resource = (
        "compute" if config.peak_operations_per_second <= bandwidth_ceiling else "memory_bandwidth"
    )
    return RooflineEstimate(
        arithmetic_intensity=intensity,
        compute_ceiling=config.peak_operations_per_second,
        bandwidth_ceiling=bandwidth_ceiling,
        upper_bound=upper_bound,
        limiting_resource=limiting_resource,
    )
