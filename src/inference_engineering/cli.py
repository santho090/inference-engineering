"""The stable command-line interface for the field guide."""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from inference_engineering.batching import (
    BatchingStrategy,
    run_all_batching_strategies,
    simulate_batching,
)
from inference_engineering.evidence import load_experiment, validate_experiment
from inference_engineering.fixtures import default_experiment_record
from inference_engineering.kv_simulation import AllocationMode, KVSimulationConfig, simulate_kv
from inference_engineering.memory import (
    KVMemoryConfig,
    ModelMemoryConfig,
    estimate_kv_memory,
    estimate_model_memory,
)
from inference_engineering.roofline import RooflineConfig, estimate_roofline
from inference_engineering.workloads import batching_trace

Handler = Callable[[argparse.Namespace], int]


def build_parser() -> argparse.ArgumentParser:
    """Build the ``ie`` command hierarchy without doing any work."""

    parser = argparse.ArgumentParser(
        prog="ie",
        description="CPU-only inference engineering calculators and deterministic simulations.",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    memory = commands.add_parser("memory", help="estimate model or KV memory")
    memory_commands = memory.add_subparsers(dest="memory_command", required=True)

    model = memory_commands.add_parser("model", help="estimate weights and activation residency")
    model.add_argument("--parameters", type=int, default=1_000_000_000)
    model.add_argument("--weight-bytes", type=int, default=2)
    model.add_argument("--layers", type=int, default=24)
    model.add_argument("--hidden-size", type=int, default=4096)
    model.add_argument("--batch-size", type=int, default=4)
    model.add_argument("--sequence-length", type=int, default=512)
    model.add_argument("--activation-bytes", type=int, default=2)
    model.add_argument("--activation-tensors", type=int, default=2)
    model.set_defaults(handler=_memory_model)

    kv = memory_commands.add_parser("kv", help="estimate KV-cache residency")
    kv.add_argument("--layers", type=int, default=24)
    kv.add_argument("--attention-heads", type=int, default=32)
    kv.add_argument("--kv-heads", type=int, default=8)
    kv.add_argument("--head-dim", type=int, default=128)
    kv.add_argument("--tokens", type=int, default=2048)
    kv.add_argument("--concurrency", type=int, default=8)
    kv.add_argument("--element-bytes", type=int, default=2)
    kv.set_defaults(handler=_memory_kv)

    roofline = commands.add_parser("roofline", help="calculate an idealized roofline bound")
    roofline.add_argument("--scenario", choices=("prefill", "decode"), default="prefill")
    roofline.add_argument("--operations", type=float)
    roofline.add_argument("--bytes-moved", type=float)
    roofline.add_argument("--peak-operations-per-second", type=float)
    roofline.add_argument("--bandwidth-bytes-per-second", type=float)
    roofline.set_defaults(handler=_roofline)

    simulate = commands.add_parser("simulate", help="run deterministic scheduler or KV simulations")
    simulation_commands = simulate.add_subparsers(dest="simulation_command", required=True)

    batching = simulation_commands.add_parser("batching", help="compare batching policies")
    batching.add_argument(
        "--strategy",
        choices=("all", *(strategy.value for strategy in BatchingStrategy)),
        default="all",
    )
    batching.set_defaults(handler=_simulate_batching)

    kv_simulation = simulation_commands.add_parser(
        "kv", help="simulate logical KV block allocation"
    )
    kv_simulation.add_argument(
        "--allocation",
        choices=tuple(mode.value for mode in AllocationMode),
        default=AllocationMode.PAGED.value,
    )
    kv_simulation.add_argument("--total-blocks", type=int, default=10)
    kv_simulation.add_argument("--block-size-tokens", type=int, default=4)
    kv_simulation.add_argument("--no-auto-evict", action="store_true")
    kv_simulation.set_defaults(handler=_simulate_kv)

    validate = commands.add_parser("validate", help="validate a versioned experiment record")
    validate_commands = validate.add_subparsers(dest="validate_command", required=True)
    experiment = validate_commands.add_parser("experiment", help="validate JSON record files")
    experiment.add_argument("paths", type=Path, nargs="*")
    experiment.set_defaults(handler=_validate_experiment)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run an ``ie`` command and return a conventional process status."""

    parser = build_parser()
    args = parser.parse_args(argv)
    handler: Handler = args.handler
    try:
        return handler(args)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        parser.error(str(error))
    return 2


def _memory_model(args: argparse.Namespace) -> int:
    config = ModelMemoryConfig(
        parameter_count=args.parameters,
        weight_bytes=args.weight_bytes,
        layers=args.layers,
        hidden_size=args.hidden_size,
        batch_size=args.batch_size,
        sequence_length=args.sequence_length,
        activation_bytes=args.activation_bytes,
        activation_tensors=args.activation_tensors,
    )
    _print_json(
        {
            "configuration": {
                "activation_bytes": config.activation_bytes,
                "activation_tensors": config.activation_tensors,
                "batch_size": config.batch_size,
                "hidden_size": config.hidden_size,
                "layers": config.layers,
                "parameter_count": config.parameter_count,
                "sequence_length": config.sequence_length,
                "weight_bytes": config.weight_bytes,
            },
            "evidence": "estimated",
            "estimate": estimate_model_memory(config).to_dict(),
        }
    )
    return 0


def _memory_kv(args: argparse.Namespace) -> int:
    config = KVMemoryConfig(
        layers=args.layers,
        attention_heads=args.attention_heads,
        kv_heads=args.kv_heads,
        head_dim=args.head_dim,
        tokens_per_sequence=args.tokens,
        concurrent_sequences=args.concurrency,
        element_bytes=args.element_bytes,
    )
    _print_json(
        {
            "configuration": {
                "attention_heads": config.attention_heads,
                "concurrent_sequences": config.concurrent_sequences,
                "element_bytes": config.element_bytes,
                "head_dim": config.head_dim,
                "kv_heads": config.kv_heads,
                "layers": config.layers,
                "tokens_per_sequence": config.tokens_per_sequence,
            },
            "evidence": "estimated",
            "estimate": estimate_kv_memory(config).to_dict(),
        }
    )
    return 0


def _roofline(args: argparse.Namespace) -> int:
    defaults = _roofline_defaults(args.scenario)
    config = RooflineConfig(
        operations=args.operations if args.operations is not None else defaults["operations"],
        bytes_moved=args.bytes_moved if args.bytes_moved is not None else defaults["bytes_moved"],
        peak_operations_per_second=(
            args.peak_operations_per_second
            if args.peak_operations_per_second is not None
            else defaults["peak_operations_per_second"]
        ),
        bandwidth_bytes_per_second=(
            args.bandwidth_bytes_per_second
            if args.bandwidth_bytes_per_second is not None
            else defaults["bandwidth_bytes_per_second"]
        ),
    )
    _print_json(
        {
            "configuration": {
                "bandwidth_bytes_per_second": config.bandwidth_bytes_per_second,
                "bytes_moved": config.bytes_moved,
                "operations": config.operations,
                "peak_operations_per_second": config.peak_operations_per_second,
            },
            "evidence": "estimated",
            "estimate": estimate_roofline(config).to_dict(),
            "scenario": args.scenario,
        }
    )
    return 0


def _roofline_defaults(scenario: str) -> dict[str, float]:
    if scenario == "decode":
        return {
            "operations": 20_000_000.0,
            "bytes_moved": 50_000_000.0,
            "peak_operations_per_second": 2_000_000_000_000.0,
            "bandwidth_bytes_per_second": 1_000_000_000_000.0,
        }
    return {
        "operations": 1_000_000_000.0,
        "bytes_moved": 200_000_000.0,
        "peak_operations_per_second": 2_000_000_000_000.0,
        "bandwidth_bytes_per_second": 1_000_000_000_000.0,
    }


def _simulate_batching(args: argparse.Namespace) -> int:
    trace = batching_trace()
    if args.strategy == "all":
        results = {
            name: result.to_dict() for name, result in run_all_batching_strategies(trace).items()
        }
    else:
        strategy = BatchingStrategy(args.strategy)
        results = {strategy.value: simulate_batching(trace, strategy).to_dict()}
    _print_json({"evidence": "simulated", "results": results})
    return 0


def _simulate_kv(args: argparse.Namespace) -> int:
    config = KVSimulationConfig(
        total_blocks=args.total_blocks,
        block_size_tokens=args.block_size_tokens,
        allocation_mode=AllocationMode(args.allocation),
        auto_evict=not args.no_auto_evict,
    )
    _print_json({"evidence": "simulated", "result": simulate_kv(config=config).to_dict()})
    return 0


def _validate_experiment(args: argparse.Namespace) -> int:
    records: list[tuple[str, dict[str, object]]] = []
    if args.paths:
        records.extend((str(path), load_experiment(path)) for path in args.paths)
    else:
        records.append(("built-in default", default_experiment_record().to_dict()))

    outputs: list[dict[str, Any]] = []
    valid = True
    for name, record in records:
        errors = validate_experiment(record)
        valid = valid and not errors
        outputs.append({"errors": errors, "path": name, "valid": not errors})
    _print_json({"records": outputs, "valid": valid})
    return 0 if valid else 1


def _print_json(data: object) -> None:
    print(json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False))
