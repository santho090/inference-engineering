# Experiment-record format

Every checked-in result uses schema version `1.0`. The machine-readable schema is [experiment-record.schema.json](experiment-record.schema.json). The `ie validate experiment` command implements the same required fields and evidence checks without requiring a network connection.

## Required fields

| Field | Purpose |
| --- | --- |
| `schema_version` | Versioned contract identifier. Current value: `1.0`. |
| `record_id` and `title` | Stable human and machine identifiers. |
| `result_type` | One evidence class applied to every numeric result in the record. |
| `hypothesis` | A falsifiable statement the result addresses. |
| `workload` | Arrivals, lengths, reuse, model shape, priorities, and objectives. |
| `environment` | Execution context and hardware or declared abstraction. |
| `configuration` | The changed or held controls. |
| `raw_measurements` | Direct values with name, value, unit, and evidence. |
| `derived_metrics` | Calculated values with name, value, unit, and evidence. |
| `conclusion` | Bounded statement supported by the record. |
| `limitations` | Non-empty list of what the record does not establish. |
| `artifacts` | Optional structured detail such as per-request simulation output. |
| `sources` | URLs required for `reported` records and allowed for other records. |

## Evidence classes

### `measured`

Use only for values produced on a recorded environment. Include the workload, hardware or equivalent profile, runtime, precision, configuration, clock or collection boundaries, and failure accounting.

### `simulated`

Use for a declared model. State its event rules, capacity assumptions, seed if randomness is possible, and omitted behaviors. The built-in batching and KV records are `simulated`.

### `estimated`

Use for arithmetic from stated inputs. Include the equation, dimensions, units, and omitted categories. The built-in memory and roofline records are `estimated`.

### `reported`

Use for values stated by an external primary source. Include the stable primary URL and preserve the source's conditions in surrounding prose. A reported result is not a local measurement or reproduction.

## Minimal example

```json
{
  "schema_version": "1.0",
  "record_id": "example-v1",
  "title": "One declared estimate",
  "result_type": "estimated",
  "hypothesis": "The declared configuration fits the lower-bound formula.",
  "workload": {"concurrent_sequences": 4},
  "environment": {"execution": "CPU-only formula"},
  "configuration": {"element_bytes": 2},
  "raw_measurements": [
    {"name": "input_bytes", "value": 16, "unit": "bytes", "evidence": "estimated"}
  ],
  "derived_metrics": [
    {"name": "total_bytes", "value": 64, "unit": "bytes", "evidence": "estimated"}
  ],
  "conclusion": "The formula returns 64 bytes for these inputs.",
  "limitations": ["This is not a runtime allocation measurement."],
  "artifacts": {},
  "sources": []
}
```

## Validation rules

- Values in `raw_measurements` and `derived_metrics` must be numeric and use a non-empty unit.
- Each result value's `evidence` must match the record's `result_type`.
- `reported` records must include at least one primary-source URL.
- A record must not use fixture output to imply an environment it did not execute on.
- A new checked-in result needs a deterministic generator or a documented reason it cannot be regenerated.

Run `ie validate experiment path/to/record.json`. With no path, the command validates the bundled default record.
