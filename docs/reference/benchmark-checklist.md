# Benchmark checklist

Use this checklist before presenting a result as `measured`.

## Workload

- [ ] Arrival distribution and burst behavior are recorded.
- [ ] Input-length and output-length distributions are recorded.
- [ ] Prefix-reuse, priority, model mix, and sampling behavior are recorded when applicable.
- [ ] TTFT, TPOT, completion, goodput, quality, cost, reliability, or energy objectives are explicit.
- [ ] Attempted, admitted, completed, failed, and objective-satisfying counts are retained.

## Environment and configuration

- [ ] Model revision, runtime version, precision, parallelism, and serving-profile limits are recorded.
- [ ] Hardware, topology, capacity budget, and relevant transfer path are recorded.
- [ ] Admission, batching, cache, placement, and routing policies are recorded.
- [ ] Baseline and candidate differ only in the intended lever or the difference is declared.
- [ ] Warm-up, cache state, sample size, and percentile rule are recorded.

## Measurement boundaries

- [ ] Admission, engine start, prefill finish, first-token delivery, decode iteration, final-token delivery, and cache-transfer boundaries are identified when relevant.
- [ ] Queue time is separate from engine execution.
- [ ] Client-visible delivery is separate from engine token availability when buffering can matter.
- [ ] Cache hit, miss, allocation, eviction, recomputation, and transfer observations are available for cache claims.

## Interpretation

- [ ] Every numeric value is labeled `measured`, `simulated`, `estimated`, or `reported`.
- [ ] A reported result links to its primary source and retains its source context.
- [ ] Confidence interval, repeatability evidence, or the reason it is unavailable is stated.
- [ ] Negative outcomes, failures, and omitted requests are included.
- [ ] The conclusion states the bottleneck hypothesis and a counterexample that would disprove it.

## Publication

- [ ] No unlicensed data, figure, table, code, or asset is bundled.
- [ ] No local path, credential-shaped value, or environment-specific identifier appears in the result artifact.
- [ ] The record validates with `ie validate experiment`.
- [ ] A reviewer can regenerate deterministic fixtures byte-for-byte.
