# Project opportunity map

This map turns the research directions into a public, clean-room portfolio order. The three P0 repositories exist; P1 and P2 names are planned labels, not existing repositories or commitments from any upstream maintainer.

## Priority summary

### P0

- [inference-engineering](https://github.com/santho090/inference-engineering): maintain the field guide, record format, and deterministic models as the common vocabulary.
- [inference-bottleneck-lab](https://github.com/santho090/inference-bottleneck-lab): the highest near-term adoption project because it can produce small, trace-defined diagnoses that map directly to public runtime seams.
- [kv-policy-lab](https://github.com/santho090/kv-policy-lab): the strongest focused research project because KV admission, reuse, reservation, eviction, and movement create a precise policy surface with useful synthetic counterexamples.

### P1

- phase-scheduler-lab: build only after a bottleneck trace and KV budget define the scheduling problem.
- hetero-placement-lab: build only after profiles, workload slices, and eligibility criteria are recorded.
- adaptive-inference-controller: build only after stable observations, bounded actions, and offline or shadow gates exist.

### P2

- Standalone kernel microbenchmarks.
- A cluster KV-fabric simulator.
- A multi-model pooling runtime.
- MoE placement.
- Energy control.

Level 1 standalone kernel work is deferred unless the learner has supported GPU hardware, a controlled correctness harness, and a non-duplicative gap after inspecting public work such as FlashInfer. A faster isolated operation is not a portfolio priority when the service bottleneck is queueing, cache state, or placement.

## Clean-room and upstream guardrails

- Use public papers, official documentation, public source, and synthetic or otherwise permitted public traces only.
- Write prose, diagrams, code, fixtures, measurements, and tests independently. Do not copy implementation code, figures, tables, benchmark harnesses, or test cases.
- Do not use nonpublic workloads, logs, capacity information, performance results, configuration, paths, metadata, or source material.
- Keep the result label close to each result. A paper claim remains reported; a local trace model remains simulated; a sizing calculation remains estimated.
- Verify license and notice obligations before incorporating any dependency or data. Keep a third-party component outside the project until its license and attribution needs are known.
- Treat each upstream seam as a place to inspect, discuss, or contribute a narrow public change. Do not promise maintainer adoption or compatibility.

## Public upstream seams

| Project | Seam to inspect first | Suitable clean-room evidence |
| --- | --- | --- |
| [FlashInfer](https://docs.flashinfer.ai/) | BatchAttention planning and execution with paged-KV layout and shape metadata. | A correctness-first shape or layout reproducer. |
| [vLLM](https://docs.vllm.ai/) | Scheduler and KV-cache-manager boundaries, including admission, allocation, and transfer configuration. | A request trace with queue, allocation, and completion accounting. |
| [SGLang](https://docs.sglang.io/) | RadixAttention prefix reuse and scheduler-visible cache state. | A prefix tree trace with hit, miss, ownership, and release events. |
| [LMCache](https://docs.lmcache.ai/) | Engine connector lifecycle and documented storage-adapter interfaces. | Synthetic cache identifiers, tier transitions, and fallback behavior. |
| [llm-d](https://llm-d.ai/) | Router endpoint selection, disaggregation profile, and cache-aware scoring path. | A routing scenario with eligibility, predicted boundary, and rollback rule. |

## Level 1: kernel optimization

**Most important mechanisms.** Serving-oriented attention planning, paged-KV layouts, shape specialization, launch reduction, and correctness-preserving fusion. FlashInfer is the current primary implementation reference in this map.

**Legal clean-room project slice.** Extend inference-bottleneck-lab with a roofline worksheet and a synthetic shape ledger. The output is an estimated diagnosis that names bytes, operations, shape, and candidate kernel boundary without using a proprietary benchmark.

**Adoption and upstream seam.** Inspect FlashInfer's documented BatchAttention plan and run boundary. A viable upstream-sized contribution is a public shape/layout reproducer or a regression test, not a replacement attention stack.

**Priority and dependency order.** The field guide is P0. Standalone kernel microbenchmarks are P2 and depend on a P0 bottleneck diagnosis, supported hardware, and a non-duplicative gap.

**What not to build yet.** Do not build a custom kernel library, a hardware ranking suite, or a broad performance claim from an isolated operation.

## Level 2: phase scheduling

**Most important mechanisms.** Continuous batching, chunked prefill, intra-device overlap, spatial-temporal prefill/decode coordination, and load-aware prefill deflection. NanoFlow, Bullet, and load-aware deflection motivate distinct scheduling hypotheses, not one universal policy.

**Legal clean-room project slice.** Phase-scheduler-lab can replay synthetic request arrivals against static, continuous, chunked, and bounded deflection policies. It should emit queue time, TTFT, token delay, completion, and failure accounting as simulated results.

**Adoption and upstream seam.** Inspect vLLM's scheduler and KV-cache-manager boundary and SGLang's scheduler-visible RadixAttention state. Start with a trace or test that makes admission and cache preconditions observable before proposing a policy change.

**Priority and dependency order.** P1 after P0 inference-bottleneck-lab identifies queueing or phase interference and after P0 kv-policy-lab defines admission headroom.

**What not to build yet.** Do not build a universal scheduler, a live traffic controller, or a policy that changes admission and placement together.

## Level 3: cache management

**Most important mechanisms.** Logical-to-physical mapping, prefix identity, reservation, reuse, eviction, recomputation, offload, and tier-aware movement. LMCache and Mooncake show why a KV policy can cross from a local allocator into a state-movement problem.

**Legal clean-room project slice.** Kv-policy-lab should model block allocation, prefix ownership, tier transitions, eviction, and recomputation on public or synthetic traces. It is the strongest focused research project because each policy decision can be isolated and falsified.

**Adoption and upstream seam.** Inspect vLLM KV-cache-manager behavior, SGLang RadixAttention state, and LMCache connector or storage-adapter documentation. A useful first proposal is an event schema or fallback test, not a new remote cache service.

**Priority and dependency order.** P0 after the guide's record vocabulary is stable. It supplies the admission and state evidence required by P1 scheduling and disaggregation work.

**What not to build yet.** Do not build a distributed KV store, lossless cache compression claim, or cross-engine reuse layer without format, identity, lifetime, and fallback evidence.

## Level 4: model and GPU pooling

**Most important mechanisms.** Qualified profile eligibility, multi-model pooling, memory elasticity, token-granular scaling, and heterogeneity-aware allocation. Aegaeon, Prism, and Coral motivate careful profile qualification rather than treating accelerators or models as interchangeable.

**Legal clean-room project slice.** Hetero-placement-lab can rank synthetic qualified profiles using stated capacity, queue, latency, and quality constraints. Its output is an estimated eligibility decision, never an unqualified deployment recommendation.

**Adoption and upstream seam.** Inspect llm-d router endpoint selection and vLLM profile and cache constraints. Start with a scenario that explains why a candidate is eligible or excluded before discussing a scorer.

**Priority and dependency order.** P1 after P0 workload profiles, KV budgets, and failure accounting exist. A multi-model pooling runtime is P2.

**What not to build yet.** Do not build a general router, a market of profiles, or an autoscaler that treats a capacity estimate as a measured service guarantee.

## Level 5: cluster architecture

**Most important mechanisms.** Prefill/decode separation, KV handoff, tiered state movement, selective transfer, and load-aware deflection. LMCache and Mooncake span L3 and L5; SmartGen and load-aware deflection make transfer avoidance and selective movement explicit.

**Legal clean-room project slice.** Add a disaggregation handoff ledger to phase-scheduler-lab or kv-policy-lab: prefill completion, transfer start, transfer finish, decode start, retry, and fallback. It should model the boundary before it models a fabric.

**Adoption and upstream seam.** Inspect LMCache's documented connector lifecycle and llm-d's Router and disaggregation profile. A public issue or small test can state a compatibility or failure-accounting gap without asserting that a new protocol should be adopted.

**Priority and dependency order.** P1 only as an integration experiment after P0 cache-policy and P1 scheduling evidence. A standalone cluster KV-fabric simulator and MoE placement are P2.

**What not to build yet.** Do not build a transport protocol, a distributed cache fabric, or expert-placement runtime before local cache correctness and handoff measurements exist.

## Level 6: adaptive control

**Most important mechanisms.** Guarded selection among bounded actions, offline or shadow validation, cooldowns, rollback, and causal attribution. A controller consumes trustworthy evidence from the earlier levels; it is not a substitute for it.

**Legal clean-room project slice.** Adaptive-inference-controller can evaluate a fixed action set against recorded synthetic traces, rejecting actions that violate stated tail or capacity constraints. Store every candidate, rejection, fallback, and result label.

**Adoption and upstream seam.** Inspect llm-d route scoring and flow-control documentation only after the action set and guardrails are specified. Keep the first contribution to a public scenario, scorer discussion, or observability requirement.

**Priority and dependency order.** P1 after P0 evidence vocabulary and P1 placement or scheduling observability are stable. Energy control is P2 because it needs an additional measured power boundary.

**What not to build yet.** Do not build an online optimizer, a multi-lever search loop, or an energy policy without a safe validation mode and a reversible action boundary.

## Recommended sequence

1. Maintain P0 inference-engineering as the shared language and verification gate.
2. Use P0 inference-bottleneck-lab for small, trace-defined diagnostics and upstream discussions.
3. Use P0 kv-policy-lab for focused cache-policy counterexamples and handoff evidence.
4. Promote only evidence-backed slices into P1 scheduler, placement, and controller labs.
5. Leave P2 systems until a measured bottleneck proves that their additional runtime surface is justified.
