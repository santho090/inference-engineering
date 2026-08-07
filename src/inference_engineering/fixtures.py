"""Deterministic experiment records used by documentation and golden tests."""

from __future__ import annotations

from dataclasses import asdict

from inference_engineering.batching import BatchingStrategy, simulate_batching
from inference_engineering.evidence import EvidenceClass, ExperimentRecord, LabeledValue
from inference_engineering.kv_simulation import kv_trace, simulate_kv
from inference_engineering.memory import (
    KVMemoryConfig,
    ModelMemoryConfig,
    estimate_kv_memory,
    estimate_model_memory,
)
from inference_engineering.roofline import RooflineConfig, estimate_roofline
from inference_engineering.workloads import batching_trace


def fixture_records() -> dict[str, ExperimentRecord]:
    """Return every checked-in record in a stable filename-to-record mapping."""

    return {
        "model-memory.json": _model_memory_record(),
        "kv-memory.json": _kv_memory_record(),
        "roofline-prefill.json": _roofline_record(),
        "batching-chunked.json": _batching_record(),
        "batching-comparison.json": _batching_comparison_record(),
        "kv-paged.json": _kv_record(),
    }


def default_experiment_record() -> ExperimentRecord:
    """Return the record exercised by ``ie validate experiment`` without a path."""

    return fixture_records()["batching-chunked.json"]


def _model_memory_record() -> ExperimentRecord:
    config = ModelMemoryConfig(
        parameter_count=1_000_000_000,
        weight_bytes=2,
        layers=24,
        hidden_size=4096,
        batch_size=4,
        sequence_length=512,
    )
    estimate = estimate_model_memory(config)
    return ExperimentRecord(
        record_id="model-memory-estimate-v1",
        title="Model residency estimate for a declared synthetic configuration",
        result_type=EvidenceClass.ESTIMATED,
        hypothesis=(
            "The declared weights and one activation working set fit within the stated estimate."
        ),
        workload={
            "concurrent_sequences": config.batch_size,
            "sequence_length": config.sequence_length,
        },
        environment={"execution": "CPU-only formula", "hardware": "not applicable"},
        configuration=asdict(config),
        raw_measurements=(
            LabeledValue("weights", estimate.weights_bytes, "bytes", EvidenceClass.ESTIMATED),
            LabeledValue(
                "activation_working_set",
                estimate.activation_bytes,
                "bytes",
                EvidenceClass.ESTIMATED,
            ),
        ),
        derived_metrics=(
            LabeledValue("total_residency", estimate.total_bytes, "bytes", EvidenceClass.ESTIMATED),
        ),
        conclusion="This lower-bound estimate excludes allocator, runtime, and KV-cache headroom.",
        limitations=(
            "It does not model runtime workspaces or graph capture memory.",
            "It represents one activation working set, not a peak implementation trace.",
        ),
        artifacts={"estimate": estimate.to_dict()},
        sources=(),
    )


def _kv_memory_record() -> ExperimentRecord:
    config = KVMemoryConfig(
        layers=24,
        attention_heads=32,
        kv_heads=8,
        head_dim=128,
        tokens_per_sequence=2048,
        concurrent_sequences=8,
        element_bytes=2,
    )
    estimate = estimate_kv_memory(config)
    return ExperimentRecord(
        record_id="kv-memory-estimate-v1",
        title="Grouped-query KV-cache estimate for a declared synthetic configuration",
        result_type=EvidenceClass.ESTIMATED,
        hypothesis=(
            "KV storage grows linearly with tokens and concurrent sequences under fixed dimensions."
        ),
        workload={
            "concurrent_sequences": config.concurrent_sequences,
            "tokens_per_sequence": config.tokens_per_sequence,
        },
        environment={"execution": "CPU-only formula", "hardware": "not applicable"},
        configuration=asdict(config),
        raw_measurements=(
            LabeledValue(
                "bytes_per_token", estimate.bytes_per_token, "bytes", EvidenceClass.ESTIMATED
            ),
            LabeledValue(
                "bytes_per_sequence",
                estimate.bytes_per_sequence,
                "bytes",
                EvidenceClass.ESTIMATED,
            ),
        ),
        derived_metrics=(
            LabeledValue("total_kv", estimate.total_bytes, "bytes", EvidenceClass.ESTIMATED),
        ),
        conclusion="The estimate excludes block rounding, reservation slack, and transfer copies.",
        limitations=(
            "It assumes dense K and V storage with the declared element size.",
            "It does not model prefix sharing or eviction.",
        ),
        artifacts={"estimate": estimate.to_dict()},
        sources=(),
    )


def _roofline_record() -> ExperimentRecord:
    config = RooflineConfig(
        operations=1_000_000_000.0,
        bytes_moved=200_000_000.0,
        peak_operations_per_second=2_000_000_000_000.0,
        bandwidth_bytes_per_second=1_000_000_000_000.0,
    )
    estimate = estimate_roofline(config)
    return ExperimentRecord(
        record_id="roofline-prefill-estimate-v1",
        title="Prefill-shaped roofline estimate with synthetic device ceilings",
        result_type=EvidenceClass.ESTIMATED,
        hypothesis=(
            "The declared operation has sufficient arithmetic intensity to meet "
            "the compute ceiling."
        ),
        workload={"phase": "prefill", "operation_shape": "many input tokens"},
        environment={"execution": "CPU-only formula", "hardware": "synthetic qualified profile"},
        configuration=asdict(config),
        raw_measurements=(
            LabeledValue(
                "arithmetic_intensity",
                estimate.arithmetic_intensity,
                "operations per byte",
                EvidenceClass.ESTIMATED,
            ),
            LabeledValue(
                "bandwidth_ceiling",
                estimate.bandwidth_ceiling,
                "operations per second",
                EvidenceClass.ESTIMATED,
            ),
        ),
        derived_metrics=(
            LabeledValue(
                "roofline_upper_bound",
                estimate.upper_bound,
                "operations per second",
                EvidenceClass.ESTIMATED,
            ),
        ),
        conclusion="The lower roof is compute in this synthetic configuration.",
        limitations=(
            "Ceilings are supplied assumptions, not a device measurement.",
            "The calculation omits launch, synchronization, and cache effects.",
        ),
        artifacts={"estimate": estimate.to_dict()},
        sources=(),
    )


def _batching_record() -> ExperimentRecord:
    requests = batching_trace()
    result = simulate_batching(requests, BatchingStrategy.CHUNKED)
    return result.to_experiment_record(requests)


def _batching_comparison_record() -> ExperimentRecord:
    requests = batching_trace()
    static = simulate_batching(requests, BatchingStrategy.STATIC)
    continuous = simulate_batching(requests, BatchingStrategy.CONTINUOUS)
    chunked = simulate_batching(requests, BatchingStrategy.CHUNKED)
    return ExperimentRecord(
        record_id="batching-comparison-v1",
        title="Static, continuous, and chunked scheduling on the fixed mixed-length trace",
        result_type=EvidenceClass.SIMULATED,
        hypothesis=(
            "A policy can improve tail TTFT while reducing aggregate output throughput "
            "under the declared abstract work model."
        ),
        workload={
            "requests": [request.to_dict() for request in requests],
            "time_unit": "abstract scheduler tick",
        },
        environment={
            "execution": "deterministic CPU-only discrete-event simulation",
            "hardware": "not applicable",
            "seed": 0,
        },
        configuration={"strategies": ["static", "continuous", "chunked"]},
        raw_measurements=(
            LabeledValue(
                "static_p95_ttft",
                float(static.aggregate["p95_ttft_ticks"]),
                "ticks",
                EvidenceClass.SIMULATED,
            ),
            LabeledValue(
                "continuous_p95_ttft",
                float(continuous.aggregate["p95_ttft_ticks"]),
                "ticks",
                EvidenceClass.SIMULATED,
            ),
            LabeledValue(
                "chunked_p95_ttft",
                float(chunked.aggregate["p95_ttft_ticks"]),
                "ticks",
                EvidenceClass.SIMULATED,
            ),
        ),
        derived_metrics=(
            LabeledValue(
                "static_output_throughput",
                float(static.aggregate["output_tokens_per_tick"]),
                "tokens per tick",
                EvidenceClass.SIMULATED,
            ),
            LabeledValue(
                "continuous_output_throughput",
                float(continuous.aggregate["output_tokens_per_tick"]),
                "tokens per tick",
                EvidenceClass.SIMULATED,
            ),
            LabeledValue(
                "chunked_output_throughput",
                float(chunked.aggregate["output_tokens_per_tick"]),
                "tokens per tick",
                EvidenceClass.SIMULATED,
            ),
        ),
        conclusion=(
            "Chunked scheduling has the lowest p95 TTFT in this trace, while continuous "
            "scheduling has the highest output throughput."
        ),
        limitations=(
            "The scheduler capacity is an abstract work-unit model.",
            "The trace is synthetic and intentionally small for inspection.",
        ),
        artifacts={
            "aggregates": {
                "chunked": chunked.aggregate,
                "continuous": continuous.aggregate,
                "static": static.aggregate,
            }
        },
        sources=(),
    )


def _kv_record() -> ExperimentRecord:
    result = simulate_kv()
    return result.to_experiment_record(kv_trace())
