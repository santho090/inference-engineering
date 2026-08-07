# Inference Engineering Context

This repository teaches how to reason about generative-model inference as a system. The language below keeps the educational material, calculators, and later labs consistent.

## Language

**Inference engineering**:
The engineering discipline that turns a trained model into a service that meets latency, throughput, quality, reliability, and cost objectives.
_Avoid_: GPU tuning, model serving optimization

**Workload**:
A distribution of request arrivals, input lengths, output lengths, prefix reuse, models, priorities, and service objectives.
_Avoid_: traffic when the distribution matters

**Service objective**:
A measurable requirement for user-visible latency, throughput, availability, quality, cost, or energy.
_Avoid_: target, SLA when no agreement exists

**Time to first token (TTFT)**:
Elapsed time from request admission until the first generated token is available to the client.
_Avoid_: startup latency

**Time per output token (TPOT)**:
Average elapsed time between generated tokens after the first token.
_Avoid_: decode latency when referring to an end-to-end metric

**Inter-token latency (ITL)**:
The distribution of delays between adjacent generated tokens.
_Avoid_: TPOT when tail behavior matters

**Goodput**:
Completed useful work that satisfies the stated service objectives, measured over time or resource cost.
_Avoid_: throughput when SLO compliance matters

**Prefill**:
The phase that processes input tokens and creates the initial key-value state.
_Avoid_: prompt processing

**Decode**:
The autoregressive phase that produces output tokens and extends key-value state one step at a time.
_Avoid_: generation when distinguishing serving phases

**Key-value cache (KV cache)**:
Per-sequence attention state retained so later decode steps do not recompute prior keys and values.
_Avoid_: memory, context cache

**KV policy**:
A rule for admitting, reserving, placing, moving, sharing, compressing, evicting, or recomputing KV state.
_Avoid_: cache algorithm when several decisions are coupled

**Serving profile**:
A qualified combination of model revision, runtime, precision, parallelism, hardware, limits, and measured performance.
_Avoid_: GPU type, deployment config

**Placement**:
The assignment of model replicas, phases, experts, or cache state to eligible resources.
_Avoid_: routing when the assignment persists beyond one request

**Routing**:
The per-request selection of an eligible serving endpoint or execution path.
_Avoid_: placement

**Disaggregation**:
Execution in which serving phases or state-management responsibilities run on separate resource pools.
_Avoid_: distributed inference when separation of responsibilities is the point

**KV fabric**:
The mechanisms and policies that locate and move KV state across workers and storage tiers.
_Avoid_: KV cache when cluster coordination is meant

**Control lever**:
A configuration or policy choice that the system can change to alter performance or resource use.
_Avoid_: optimization when referring to the action rather than the objective

**Bottleneck**:
The constrained resource or serialized stage whose relief would improve the selected objective under the measured workload.
_Avoid_: low utilization, slow component

**Experiment record**:
A reproducible bundle containing the hypothesis, workload, environment, configuration, raw measurements, derived metrics, and conclusion.
_Avoid_: benchmark result
