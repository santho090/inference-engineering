# Answer notes

These notes explain the reasoning target, not a single mandatory wording.

## Workload archetypes

Interactive chat needs TTFT and ITL boundaries because a mean completion value can hide streaming stalls. Shared-prefix retrieval adds cache identity, hit rate, and resident capacity. Long-context analysis starts with memory feasibility because an impossible KV reservation makes scheduler comparisons irrelevant. Mixed-priority batch work needs explicit fairness and failure accounting.

## Level 1

Halving bytes moved doubles arithmetic intensity. It only raises the roofline bound when bandwidth is the lower roof. It does not prove a speedup because launch, synchronization, cache, and queue behavior are omitted.

## Level 2

On the fixed trace, continuous scheduling has the highest simulated output throughput, while chunked scheduling has the lowest simulated p95 TTFT. The trace declares abstract work units and no hardware environment, so it can compare policy mechanics but not rank serving implementations.

## Level 3

The contiguous allocator requires one five-block span. The trace has enough total free blocks but lacks that span. Paging maps one logical allocation across several physical spans. The paged trace then evicts alpha to admit zeta and recomputes alpha after a later touch. A different length distribution, reuse distribution, or block size can change the result.

## Level 4

An estimate that leaves capacity after weights, activations, and KV state is only a candidate. Runtime workspaces, allocator behavior, reservation granularity, model revision, precision, and quality checks can invalidate it.

## Level 5

Disaggregation helps only when removed phase interference exceeds transfer and coordination cost under the relevant objective. The required timestamps localize whether the new delay is transfer, decode queueing, or another handoff stage.

## Level 6

A safe controller operates within an explicit action set and rejects a candidate that violates a tail guardrail even when its average output rate is favorable. Cooldown and rollback prevent rapid oscillation and preserve a known fallback.

## Record exercise

Adding a primary-source URL satisfies the source requirement for `reported`, but it does not convert an external value into a local measurement. A record's conclusion remains bounded by its evidence class.
