# Level 2: phase scheduling

## Question

How should a scheduler admit, batch, and interleave prefill and decode work under a stated TTFT, TPOT, and goodput objective?

## Mental model

```mermaid
flowchart LR
    Q[Ready requests] --> A[Admission rule]
    A --> P[Prefill work]
    P --> D[Decode work]
    D --> A
    P -. competes for .-> B[Batch budget]
    D -. competes for .-> B
```

Static batching holds a group until it reaches a launch condition. Continuous batching admits new work as slots free. Chunked prefill bounds each prefill contribution so existing decodes can receive service. These are policy families, not interchangeable flags.

## Workload variables

Arrival burstiness, prompt and output lengths, priority, TTFT objective, TPOT objective, maximum active requests, prefill chunk size, and available KV capacity determine the relevant schedule. A scheduler cannot be ranked by one total token rate alone.

## Constrained resources and serialized stages

Admission slots, batch budget, prefill work, decode iterations, cache admission, and output streaming interact. Prefill-decode interference is a scheduling fact: both phases consume a finite per-step budget in a colocated engine.

## Metrics and boundaries

Collect queue time, TTFT distribution, ITL or TPOT distribution, completion distribution, output throughput, and goodput. Attribute queue time separately. Report tail percentiles with their rank rule and population. A high aggregate rate is not goodput when requests miss their objective.

## Control levers and preconditions

Continuous batching needs safe per-request KV state and a way to remove completed sequences. Chunked prefill needs a chunk policy and a decoder service guarantee. Priority scheduling needs a fairness limit. Operation overlap needs independently measured stages that can actually overlap.

## Current mechanisms to study

[NanoFlow, arXiv:2408.12757](https://arxiv.org/abs/2408.12757) studies smaller work units and overlap among different device resources. [Bullet, DOI:10.1145/3779212.3790135](https://doi.org/10.1145/3779212.3790135) studies spatial-temporal coordination of prefill and decode with a performance model. Both belong at Level 2 because their central decision is how work is sequenced within a serving step.

[Towards Load-Aware Prefill Deflection, arXiv:2607.02043](https://arxiv.org/abs/2607.02043) adds a constrained decision: whether a decode node can run bounded prefill work while preserving its token-delay objective. Its placement prerequisite makes it a Level 2 mechanism that also crosses into Level 5. The local experiment must retain queue, chunk, token-delay, and handoff boundaries before it can support a deflection rule.

## Failure modes and counterexamples

Static batching can build a full batch and still raise tail TTFT through batch wait. Continuous prefill-first scheduling can increase decode delay during a prompt burst. A strict decode reservation can lower tail TTFT while leaving capacity unused in a sparse state. No policy is universally preferable.

## Worked numerical example

The fixed trace in this repository produces `simulated` results. Continuous scheduling has 3 output tokens per tick and p95 TTFT of 13 ticks. Chunked scheduling has 2.86364 output tokens per tick and p95 TTFT of 12 ticks. This is a throughput and tail-latency tradeoff under an abstract work-unit model, not a hardware result. The source record and all values are in the [generated table](../reference/generated-results.md#static-continuous-and-chunked-scheduling-on-the-fixed-mixed-length-trace).

## Executable exercise

Run `ie simulate batching`. Compare all three `aggregate` objects. Then run `ie simulate batching --strategy static`. Identify which result fields would need a real engine measurement before choosing a scheduler for a workload with a tight TPOT objective.

## Primary references

- [ORCA, Yu et al., OSDI 2022](https://www.usenix.org/conference/osdi22/presentation/yu)
- [Sarathi-Serve, Agrawal et al.](https://arxiv.org/abs/2403.02310)
- [NanoFlow, arXiv:2408.12757](https://arxiv.org/abs/2408.12757)
- [Bullet, DOI:10.1145/3779212.3790135](https://doi.org/10.1145/3779212.3790135)
- [Towards Load-Aware Prefill Deflection, arXiv:2607.02043](https://arxiv.org/abs/2607.02043)
- [Reported-results policy](../reference/experiment-record.md#reported)
