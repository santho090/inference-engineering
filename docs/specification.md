# Inference Engineering repository specification

## Problem statement

Inference-engineering material is fragmented across books, papers, runtime documentation, vendor guides, and benchmark scripts. A learner can memorize individual techniques without learning how workload, model, hardware, runtime, cache, network, and service objectives interact. Existing material also tends to blur paper-reported results, reproduced measurements, and production claims.

The repository must teach a falsifiable way to reason about inference systems. A reader should be able to identify the likely bottleneck, choose the right metrics, estimate whether a proposed optimization can matter, and design an experiment that could disprove the hypothesis.

## Solution

Create a public, Markdown-first field guide with executable CPU-only calculators and deterministic simulations. Organize the material around a request's path through the system and a six-level optimization model:

1. Kernel optimization
2. Phase scheduling
3. Cache management
4. Model and GPU pooling
5. Cluster architecture
6. Adaptive control

Each level must connect four things:

- The constrained resource or serialized stage
- The metrics that reveal it
- The control levers available at that level
- The failure modes created at adjacent levels

The repository is educational. It links to the Bottleneck Lab and KV Policy Lab for deeper experimentation rather than absorbing those implementations.

## Intended readers

- Software and platform engineers entering inference systems
- ML engineers who need systems-level performance reasoning
- Infrastructure engineers evaluating serving architectures
- Contributors preparing to work in vLLM, SGLang, FlashInfer, LMCache, or llm-d

The default path assumes basic Python and systems knowledge. CUDA and Kubernetes experience are not prerequisites.

## Learning outcomes

After completing the guide, a reader can:

1. Define a workload using arrival, token-length, reuse, model, and priority distributions.
2. Set separate TTFT, TPOT, goodput, quality, cost, and reliability objectives.
3. Explain why prefill and decode stress different GPU resources.
4. Estimate weight, activation, and KV-cache memory.
5. Use arithmetic intensity and a roofline model to reason about compute and bandwidth bounds.
6. Explain continuous batching, paged KV allocation, prefix reuse, chunked prefill, speculative decoding, and parallelism.
7. Compare colocated and disaggregated execution using queueing, transfer, and interference costs.
8. Explain why heterogeneous hardware requires qualified serving profiles rather than a uniform GPU abstraction.
9. Design a measurement plan that separates client latency, queueing, engine execution, transfer, and cache effects.
10. Distinguish a safe adaptive controller from unconstrained flag search.

## Content architecture

### Part I: define the problem

1. What inference engineering controls
2. Workloads, user experience, and service objectives
3. Request lifecycle and metric boundaries
4. Measurement integrity and experiment records

### Part II: understand the machine

5. Transformer inference anatomy
6. GPU execution and the memory hierarchy
7. Roofline reasoning and arithmetic intensity
8. Model weights, activations, and KV-cache sizing

### Part III: optimize one engine

9. Level 1: attention kernels, fusion, layouts, CUDA graphs, and launch overhead
10. Level 2: continuous batching, chunked prefill, prefill/decode interference, and operation overlap
11. Level 3: paging, prefix reuse, reservation, eviction, compression, tiering, and transfer
12. Quantization, speculative decoding, and parallelism

### Part IV: optimize the service

13. Level 4: multi-model serving, GPU pooling, memory coordination, and heterogeneous placement
14. Level 5: prefill/decode disaggregation, KV fabric, network constraints, and MoE expert placement
15. Level 6: workload prediction, constrained search, Bayesian optimization, and SLO-aware routing
16. Observability, regression testing, capacity planning, cost, and energy
17. Where inference engineering is going

### Appendices

- Glossary
- Equations and notation
- Benchmark checklist
- Research map
- Runtime and project map
- Exercises and answer notes

## Chapter contract

Every technical chapter must contain:

1. A concrete question the chapter answers
2. A mental model using an original diagram
3. The relevant workload variables
4. The constrained resources and serialized stages
5. Metrics and measurement boundaries
6. Control levers and their preconditions
7. Failure modes and counterexamples
8. A worked numerical example
9. An executable exercise or deterministic simulation
10. Primary references and a clear label for paper-reported results

No chapter may lead with product marketing or a list of framework flags.

## User stories

### 1. First-principles orientation

As a reader new to inference systems, I can follow one request from admission to streamed output so that later optimizations have a stable frame of reference.

Acceptance criteria:

- The lifecycle identifies queueing, prefill, first-token delivery, decode, cache operations, and streaming.
- Metric start and stop points are explicit.
- The chapter explains why a single GPU-utilization percentage cannot identify a bottleneck.

### 2. Workload definition

As an engineer, I can describe the workload before tuning the runtime so that an optimization is evaluated under the conditions it targets.

Acceptance criteria:

- A schema represents arrivals, prompt lengths, output lengths, shared prefixes, models, priorities, and objectives.
- At least four synthetic workload archetypes are included.
- Examples demonstrate that the same configuration can rank differently under different workloads.

### 3. Memory calculation

As a learner, I can calculate approximate model and KV memory so that I can reject impossible configurations before benchmarking.

Acceptance criteria:

- A tested calculator accepts model dimensions, precision, batch concurrency, and sequence lengths.
- The explanation states what the estimate omits.
- Unit tests include GQA and non-GQA cases and reject invalid dimensions.

### 4. Roofline reasoning

As a performance engineer, I can estimate whether an operation is compute-bound or bandwidth-bound so that I choose a relevant optimization family.

Acceptance criteria:

- A calculator reports arithmetic intensity and a roofline upper bound.
- Worked examples contrast prefill-shaped and decode-shaped operations.
- The text explains why the estimate is a bound rather than a throughput promise.

### 5. Scheduling simulation

As a reader, I can compare static batching, continuous batching, and chunked prefill on a deterministic request trace.

Acceptance criteria:

- The simulation emits per-request TTFT and completion time plus aggregate throughput and goodput.
- Results are identical for a fixed input and seed.
- At least one scenario shows a throughput and tail-latency tradeoff.

### 6. KV-cache simulation

As a reader, I can observe KV growth, fragmentation, paging, and eviction so that cache policy is more concrete than a memory formula.

Acceptance criteria:

- A deterministic simulation allocates logical token blocks to physical blocks.
- The simulation exposes reserved, used, free, evicted, and recomputed blocks.
- An exercise compares contiguous allocation with paging under variable sequence lengths.

### 7. Research navigation

As a prospective contributor, I can map a research idea to the serving layer, public implementation, and unresolved engineering question.

Acceptance criteria:

- Every research entry links to a primary paper or official project source.
- Entries record publication year, layer, central mechanism, reported objective, and implementation availability.
- The map distinguishes foundational, current, and speculative directions.

### 8. Experiment integrity

As a practitioner, I can tell whether a benchmark claim is measured, simulated, estimated, or copied from a paper.

Acceptance criteria:

- Every result table carries a result-type label.
- Generated experiment records include environment and workload metadata.
- Documentation never converts a paper's reported number into a repository claim.

### 9. Clean-room reuse

As an adopter, I can use the repository without inheriting unknown proprietary material.

Acceptance criteria:

- The root contains Apache-2.0 `LICENSE`, `NOTICE` when required, and `THIRD_PARTY.md`.
- All bundled data and assets have provenance records.
- A pre-publication scanner checks for secrets, local paths, prohibited domains, and unrecorded large artifacts.

## Implementation decisions

### Markdown-first documentation

Canonical content lives in Markdown under `docs/`. A static documentation site may render it, but the repository remains readable and reviewable without the site toolchain.

### Python 3.12 standard path

Calculators and simulations use Python 3.12. The default installation must not require CUDA, a model download, network access, or a running inference server.

### Small public package

Executable material lives in `src/inference_engineering/` with a stable command-line interface. It is not a general serving library.

Planned commands:

```text
ie memory model
ie memory kv
ie roofline
ie simulate batching
ie simulate kv
ie validate experiment
```

### Structured experiment records

Examples emit versioned JSON records. Documentation renders tables from checked-in small fixtures rather than embedding unexplained numbers.

### Original visual language

Use Mermaid for architecture and sequence diagrams when possible. Any raster image must have a source record and redistribution permission.

### Explicit evidence classes

Use four labels throughout the repository:

- `measured`: produced by this repository on a recorded environment
- `simulated`: produced by a declared model
- `estimated`: calculated from stated assumptions
- `reported`: stated by an external source

## Repository structure

```text
inference-engineering/
├── README.md
├── LICENSE
├── NOTICE
├── THIRD_PARTY.md
├── CONTRIBUTING.md
├── SECURITY.md
├── CONTEXT.md
├── pyproject.toml
├── mkdocs.yml
├── docs/
│   ├── index.md
│   ├── specification.md
│   ├── program-roadmap.md
│   ├── publication-policy.md
│   ├── foundations/
│   ├── hardware/
│   ├── levels/
│   ├── production/
│   ├── future/
│   ├── reference/
│   └── adr/
├── src/inference_engineering/
├── tests/
├── examples/
└── scripts/
```

## Testing decisions

The highest-value seam is the boundary between equations or policy descriptions and executable examples. Tests must prove that examples are deterministic, dimensionally correct, and honest about assumptions.

Required checks:

- Unit tests for calculators and simulation state transitions
- Property tests for memory invariants and block accounting
- Golden tests for small deterministic experiment records
- CLI smoke tests from an installed package
- Markdown link validation
- Documentation build with warnings treated as errors
- Secret and prohibited-pattern scan over the full Git history before publication
- License and third-party manifest validation

The repository does not need GPU performance tests. Optional GPU exercises must provide a recorded environment and must never gate the default test suite.

## Acceptance gates

### Content gate

- All six requested levels meet the chapter contract.
- The official book attribution is Philip Kiely.
- Research claims link to primary sources.
- Prose passes a plain-language and unsupported-claim review.

### Software gate

- Clean Python 3.12 environment installs the package.
- All default commands run without network or GPU access.
- Tests, lint, typing, and docs validation pass.
- Generated fixtures reproduce byte-for-byte from their declared inputs.

### Publication gate

- The root license is detectable as Apache-2.0.
- Third-party and provenance manifests are complete.
- Full-history scans find no prohibited material or tool attribution.
- Public repository description, topics, and README match the implemented scope.
- The repository is pushed only after an independent read-only review returns `ship`.

## Out of scope

- A new inference runtime or attention engine
- Production deployment manifests
- Claims about unsupported hardware
- Reproduction of paper headline numbers without equivalent hardware and workloads
- Vendor ranking
- Internal company architecture or operational guidance
- A universal configuration recommender
- Automatic changes to a live serving system

## Further notes

The official *Inference Engineering* book and companion materials by Philip Kiely are navigational references, not source text for this repository. The guide must develop its own explanations, diagrams, examples, and organization. Paper and project coverage should favor mechanisms and falsifiable claims over popularity.

The next repository begins only after this repository's measurement vocabulary and experiment-record format are stable enough to reuse.
