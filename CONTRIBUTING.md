# Contributing

## Scope

Contributions must preserve the repository boundary: a Markdown-first field guide with CPU-only calculators and deterministic simulations. Do not add a serving runtime, deployment bundle, live benchmark harness, or automatic configuration changer.

## Source and attribution rules

- Write prose, diagrams, exercises, examples, and code independently.
- Use public primary papers or official project documentation for technical claims.
- Link a source close to the claim. Label external paper results as `reported`.
- Do not copy source text, figures, tables, code, datasets, weights, traces, or screenshots without an explicit compatible license and an updated provenance record.
- Do not add non-public information, local paths, credentials, environment-specific identifiers, or unverified performance claims.

## Result records

Changes that add a result must use the [experiment-record format](docs/reference/experiment-record.md). Every numeric result is `measured`, `simulated`, `estimated`, or `reported`. A measured result requires an environment and workload description. A simulated result requires the declared model. An estimated result requires its assumptions. A reported result requires a primary source URL.

## Development checks

Use Python 3.12 or newer. The default package has no runtime dependencies. Install the optional development tools before running repository checks.

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

Run the fixture generator with `--write` only when the changed algorithm and its expected records have been reviewed together.
