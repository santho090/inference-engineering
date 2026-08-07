# Inference Engineering field guide

Inference engineering turns a trained generative model into a service that meets stated latency, throughput, quality, reliability, cost, and energy objectives. The discipline begins with a workload and a measurable service objective, not a runtime flag.

This guide follows one request from admission to streamed output. It uses six levels of control: kernels, phase scheduling, cache management, pools, cluster architecture, and adaptive control. The default exercises are CPU-only estimates or deterministic simulations.

## How to use the guide

1. Start with [workloads and objectives](foundations/02-workloads-and-objectives.md), then write down what counts as useful completion.
2. Use the [request lifecycle](foundations/03-request-lifecycle.md) to place each latency measurement boundary.
3. Calculate [roofline](hardware/07-roofline.md) and [memory](hardware/08-memory-sizing.md) limits before tuning a scheduler.
4. Move through levels 1 to 3 before proposing a pool or cluster change.
5. Use an [experiment record](reference/experiment-record.md) to preserve evidence class and assumptions.

## Evidence discipline

The guide uses four labels for result values:

| Label | Definition | Example in this repository |
| --- | --- | --- |
| `measured` | Produced on a recorded environment. | None are bundled by default. |
| `simulated` | Produced by a declared model. | [Batching and KV fixtures](reference/generated-results.md). |
| `estimated` | Calculated from declared assumptions. | [Memory and roofline fixtures](reference/generated-results.md). |
| `reported` | Stated by an external primary source. | [Research-map objective fields](reference/research-map.md). |

## Executable path

```bash
ie memory model
ie memory kv
ie roofline
ie simulate batching
ie simulate kv
ie validate experiment
```

The commands require neither a GPU nor a network connection. The [generated result tables](reference/generated-results.md) are rendered from the checked-in JSON records that these calculators and simulations reproduce.

## Attribution and scope

The official *Inference Engineering* guide by [Philip Kiely](https://inferenceengineering.tech/) is a navigational reference. This repository independently writes its text, diagrams, exercises, examples, and code.

The planned `inference-bottleneck-lab` and `kv-policy-lab` projects are intentionally outside this repository. They remain planned until they exist. This guide supplies the shared vocabulary and record format those projects can reuse.
