# Inference engineering learning and project roadmap

The repositories are ordered by dependency and evidence quality, not by how ambitious their names sound.

## P0: establish the learning and measurement foundation

The P0 repositories are public under Apache-2.0. Their exit criteria remain maintenance gates for every change, not one-time completion claims.

### [inference-engineering](https://github.com/santho090/inference-engineering)

An executable field guide covering the full inference stack. It provides the shared language, equations, workload models, metrics, and research map used by every later project.

Exit criteria:

- All six levels have a chapter, an original diagram, a worked example, an exercise, and primary references.
- CPU-only calculators cover model memory, KV memory, arithmetic intensity, and latency budgets.
- Deterministic simulations demonstrate continuous batching, KV growth, and queueing effects.
- Documentation and code pass automated validation from a clean checkout.

### [inference-bottleneck-lab](https://github.com/santho090/inference-bottleneck-lab)

A workload runner and offline analyzer that distinguishes queue, compute, memory bandwidth, KV capacity, transfer, and scheduler bottlenecks.

Exit criteria:

- Synthetic mode runs without a GPU.
- Adapters can consume saved or live vLLM and SGLang metrics.
- Every diagnosis links evidence to a falsifiable rule.
- Baseline comparison reports regressions without claiming causal certainty from correlation alone.

### [kv-policy-lab](https://github.com/santho090/kv-policy-lab)

A discrete-event simulator for KV admission, reservation, placement, migration, eviction, transfer, and recomputation policies.

Exit criteria:

- Policies implement one stable interface.
- Workloads cover multi-turn chat, shared-prefix RAG, long context, and bursty arrivals.
- Reports include cache hits by tier, bytes moved, tokens recomputed, TTFT, TPOT, goodput, and SLO violations.
- Results are deterministic for a fixed seed and configuration.

## P1: use the foundation for systems research

### `phase-scheduler-lab`

Trace replay for continuous batching, chunked prefill, phase mixing, disaggregation, and prefill deflection.

### `hetero-placement-lab`

Offline placement and capacity planning across qualified serving profiles and heterogeneous accelerators.

### `adaptive-inference-controller`

Offline-first constrained optimization over validated control levers. It consumes experiment records from the earlier labs and compares search strategies under explicit safety bounds.

## P2: specialize only after measured demand

- Kernel microbenchmarks as a standalone package
- A separate cluster-scale KV-fabric simulator
- Multi-model GPU-pooling runtime components
- MoE expert-placement experiments
- Energy and frequency control on supported hardware

## Upstream contribution path

Independent repositories are not a substitute for collaboration with established runtimes. After each lab reaches its exit criteria:

1. Identify one bounded integration seam in llm-d, LMCache, vLLM, SGLang, or FlashInfer.
2. Reproduce the problem using public fixtures.
3. Discuss the proposed interface with maintainers before a large patch.
4. Submit the smallest useful change with tests and benchmark methodology.
5. Keep experimental policy code in the lab until maintainers accept the abstraction.
