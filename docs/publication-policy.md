# Publication policy

This repository is a clean-room educational project built from public sources and independent work.

## Allowed inputs

- Public papers and proceedings
- Public project documentation and source repositories
- Public datasets and traces whose licenses permit redistribution or derived use
- Synthetic workloads created for this project
- Measurements produced on personally controlled or explicitly authorized hardware

## Prohibited inputs

- Employer or customer source code
- Internal configuration, endpoints, dashboards, or runbooks
- Customer prompts, traces, identifiers, or usage distributions
- Private capacity, pricing, reliability, or benchmark data
- Internal architecture diagrams or incident details
- Text, figures, tables, or code copied from a source without permission and attribution

## Source handling

1. Record every external source in the research map with its stable URL and access date.
2. Cite ideas in the chapter where they are discussed.
3. Write explanations and diagrams independently.
4. Keep copied code out of the repository unless its license is compatible, the copy is necessary, and attribution and NOTICE obligations are satisfied.
5. Record redistributed assets and dependencies in `THIRD_PARTY.md`.
6. Mark paper-reported measurements as reported results. Do not present them as reproduced results.
7. Attach environment and workload metadata to every measurement produced by this project.

## Licensing

Original code and documentation will use Apache License 2.0. The root `LICENSE` will contain the unmodified license text. A `NOTICE` file will be added when incorporated material requires one. Dependency licenses remain their authors' licenses.

## Pre-publication check

- Search the full Git history for internal names, endpoints, domains, identifiers, secrets, and prohibited attribution.
- Verify every bundled dataset and asset has a recorded license.
- Verify that benchmark claims distinguish measured, simulated, estimated, and paper-reported values.
- Verify the README describes limitations and does not imply production validation.
- Verify no generated artifact contains local absolute paths or environment-specific identifiers.
