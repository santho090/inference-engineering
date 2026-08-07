# Exercises

Every exercise uses synthetic inputs. Do not replace them with data that lacks a clear redistribution and provenance record.

## Workload archetypes

| Archetype | Arrival shape | Token shape | Reuse | Priority | First question |
| --- | --- | --- | --- | --- | --- |
| Interactive chat | Steady with short bursts | Short to medium input, medium output | Low | Interactive | Which queue and decode tail dominate TTFT and TPOT? |
| Shared-prefix retrieval | Bursty | Medium input, short output | High | Interactive | Does safe prefix reuse reduce prefill enough to offset lookup and capacity cost? |
| Long-context analysis | Low rate | Long input, medium output | Low | Standard | Is prefill, KV capacity, or transfer the first impossible constraint? |
| Mixed-priority batch | Bursty and mixed | Short to long input and output | Mixed | Interactive, standard, deferred | Which admission and fairness policy maximizes goodput without starving a class? |

The schema for these archetypes is implemented in `inference_engineering.workloads.synthetic_workload_archetypes`. One matching JSON example is `examples/workloads/interactive-chat.json`.

## Level 1: kernel question

Choose a prefill-shaped operation. Use `ie roofline` to calculate an estimated upper bound. Halve the assumed bytes moved, keep operations constant, and state whether the bound changes. List the launch and synchronization measurements missing from the calculation.

## Level 2: scheduler question

Run `ie simulate batching`. Write one sentence for the throughput winner and one for the p95 TTFT winner. Change no values in the generated record. Explain why the result is `simulated` and why it cannot choose a real runtime policy.

## Level 3: KV allocation question

Run both allocation modes:

```bash
ie simulate kv --allocation contiguous
ie simulate kv --allocation paged
```

For `epsilon`, explain why fragmentation blocks the contiguous request. For the paged case, identify the later eviction and recomputation event. State one workload variable that could make this trace unrepresentative.

## Level 4: profile question

Choose a synthetic 16 GiB capacity budget. Use `ie memory model` and `ie memory kv` to reserve weights, one activation working set, and KV state. Record which category is not represented by the calculators. Do not claim a profile qualifies until runtime reservation behavior is measured.

## Level 5: disaggregation question

Draw four timestamps for prefill completion, state-transfer start, state-transfer finish, and decode start. Give an estimated case where phase separation helps, then one where transfer queueing reverses the outcome.

## Level 6: controller question

Define an action set of three batch budgets. Define one tail TTFT guardrail, one cooldown, one rollback trigger, and one prohibited action. Create an `estimated` record for the decision rule and validate it with `ie validate experiment`.

## Record exercise

Copy a canonical fixture to a temporary location. Change the record type and every result evidence label from `estimated` to `reported`, leave `sources` empty, and run validation. Then add one primary-source URL and explain why the record still describes a reported value rather than a measurement.
