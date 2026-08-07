# Keep education, diagnosis, and policy experimentation separate

The `inference-engineering` repository will be a Markdown-first field guide with deterministic calculators and small simulations. It will not become a serving engine, production benchmark suite, or policy research framework. Bottleneck diagnosis belongs in `inference-bottleneck-lab`; cache-policy experiments belong in `kv-policy-lab`. This boundary keeps the first repository readable while allowing the later labs to evolve as real software projects.

## Considered options

- One monorepo would make cross-linking easy but would mix educational stability with experimental release cycles.
- Documentation alone would be simpler but would not let readers test the equations and tradeoffs.
- A complete serving engine would offer deeper implementation work but would duplicate mature runtimes and require hardware-specific validation.

## Consequences

The guide may depend on stable command-line interfaces exposed by the labs, but it must not import their implementation packages. Examples in the guide must run without a GPU unless they are clearly marked optional.
