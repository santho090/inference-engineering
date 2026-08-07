# Glossary

| Term | Definition |
| --- | --- |
| Inference engineering | Engineering a trained generative model into a service that meets declared latency, throughput, quality, reliability, cost, and energy objectives. |
| Workload | A distribution of request arrivals, input lengths, output lengths, prefix reuse, models, priorities, and objectives. |
| Service objective | A measurable requirement for user-visible latency, throughput, availability, quality, cost, or energy. |
| TTFT | Elapsed time from request admission until the first generated token is available to the client. |
| TPOT | Mean elapsed time between output tokens after the first token, over a declared population. |
| ITL | The distribution of delays between adjacent output tokens. |
| Goodput | Completed useful work that satisfies the stated objectives, measured per unit time or resource cost. |
| Prefill | The phase that processes input tokens and creates initial KV state. |
| Decode | The autoregressive phase that produces output tokens and extends KV state one step at a time. |
| KV cache | Per-sequence attention state retained so later decode steps do not recompute prior keys and values. |
| KV policy | A rule for admitting, reserving, placing, moving, sharing, compressing, evicting, or recomputing KV state. |
| Serving profile | A qualified combination of model revision, runtime, precision, parallelism, hardware, limits, and measured behavior. |
| Placement | Assignment of model replicas, phases, experts, or cache state to eligible resources that persists beyond one request. |
| Routing | Per-request selection of an eligible endpoint or execution path. |
| Disaggregation | Execution in which serving phases or state-management responsibilities use separate resource pools. |
| KV fabric | Mechanisms and policies that locate and move KV state across workers and storage tiers. |
| Control lever | A configuration or policy choice that can alter performance or resource use. |
| Bottleneck | The constrained resource or serialized stage whose relief would improve the selected objective under the measured workload. |
| Experiment record | A reproducible bundle of hypothesis, workload, environment, configuration, raw values, derived metrics, conclusion, and limitations. |

The definitions are operational. If a term cannot be connected to a workload, metric boundary, or control lever, it is not yet precise enough to guide a change.
