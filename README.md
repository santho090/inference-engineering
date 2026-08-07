# Inference Engineering

An executable, Markdown-first field guide for reasoning about generative-model inference as a system. It connects workload shape, service objectives, memory, scheduler behavior, cache state, placement, and adaptive control.

The guide is educational. Its calculators are estimates and its simulations are declared abstract models. They do not benchmark hardware, start a server, download a model, or require a GPU.

## Start here

```bash
python -m pip install -e .
ie memory model
ie memory kv
ie roofline
ie simulate batching
ie simulate kv
ie validate experiment
```

Each command emits deterministic JSON and works with only the Python standard library at runtime.

## Learning path

Read the [field guide](docs/index.md) in request-path order:

1. Define workload, service objectives, lifecycle boundaries, and experiment integrity.
2. Build a memory and roofline model before changing runtime behavior.
3. Work through kernel, scheduling, and KV-cache decisions for one engine.
4. Extend the reasoning to pools, disaggregation, placement, and constrained control.
5. Use the exercises and record format to state what a result can and cannot show.

The six optimization levels are deliberately separate:

| Level | Question | Executable companion |
| --- | --- | --- |
| 1. Kernel optimization | Which operation or data movement is constraining one step? | `ie roofline` |
| 2. Phase scheduling | How do admission, prefill, and decode interact? | `ie simulate batching` |
| 3. Cache management | How does logical KV state consume and fragment physical capacity? | `ie memory kv`, `ie simulate kv` |
| 4. Model and GPU pooling | Which qualified serving profile should receive a request? | Measurement plan |
| 5. Cluster architecture | Is phase separation worth its transfer and coordination cost? | Measurement plan |
| 6. Adaptive control | Which bounded lever may change after evidence arrives? | Experiment record review |

## Evidence labels

Every result record uses one evidence label.

| Label | Meaning |
| --- | --- |
| `measured` | Produced by this repository on a recorded environment. |
| `simulated` | Produced by a declared model. |
| `estimated` | Calculated from stated assumptions. |
| `reported` | Stated by an external primary source. |

The checked-in fixtures and rendered tables are in [examples/experiments](examples/experiments) and [generated results](docs/reference/generated-results.md).

## Scope

This repository is not a serving engine, deployment bundle, hardware benchmark suite, or configuration recommender. The planned `inference-bottleneck-lab` and `kv-policy-lab` projects are separate and remain planned until they exist.

## Sources and authorship

The official *Inference Engineering* guide by [Philip Kiely](https://inferenceengineering.tech/) is a navigational reference. This repository independently writes its explanations, diagrams, exercises, examples, and code. Its [research map](docs/reference/research-map.md) links technical claims to primary papers or official project documentation.

See the [project opportunity map](docs/reference/project-opportunity-map.md) for clean-room project priorities and public integration seams.

## Development

The default installation remains runtime-dependency-free. Install the optional development tools before running repository checks.

```bash
python -m pip install -e ".[dev]"
python -m unittest discover -s tests -v
ruff check .
ruff format --check .
mypy src tests scripts
mkdocs build --strict
python scripts/check_source_register.py
python scripts/check_markdown_links.py
python scripts/generate_fixtures.py --check
python scripts/render_results.py --check
python scripts/prepublication_scan.py
python scripts/check_license_manifest.py
```

See [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md), [NOTICE](NOTICE), and [THIRD_PARTY.md](THIRD_PARTY.md).
