# Generated result tables

This page is rendered from small checked-in JSON fixtures. Every displayed value retains its evidence label.

## chunked batching on the fixed mixed-length trace

Record: `batching-chunked-v1`. Result type: `simulated`.

| Metric | Value | Unit | Evidence |
| --- | ---: | --- | --- |
| completed_requests | 8 | requests | `simulated` |
| completed_output_tokens | 63 | tokens | `simulated` |
| p95_ttft | 12 | ticks | `simulated` |
| output_throughput | 2.86364 | tokens per tick | `simulated` |
| goodput | 0.363636 | requests per tick | `simulated` |

Conclusion: Use this result only to compare declared scheduler rules on this trace; it is not a hardware measurement.

## Static, continuous, and chunked scheduling on the fixed mixed-length trace

Record: `batching-comparison-v1`. Result type: `simulated`.

| Metric | Value | Unit | Evidence |
| --- | ---: | --- | --- |
| static_p95_ttft | 16 | ticks | `simulated` |
| continuous_p95_ttft | 13 | ticks | `simulated` |
| chunked_p95_ttft | 12 | ticks | `simulated` |
| static_output_throughput | 2.625 | tokens per tick | `simulated` |
| continuous_output_throughput | 3 | tokens per tick | `simulated` |
| chunked_output_throughput | 2.86364 | tokens per tick | `simulated` |

Conclusion: Chunked scheduling has the lowest p95 TTFT in this trace, while continuous scheduling has the highest output throughput.

## Grouped-query KV-cache estimate for a declared synthetic configuration

Record: `kv-memory-estimate-v1`. Result type: `estimated`.

| Metric | Value | Unit | Evidence |
| --- | ---: | --- | --- |
| bytes_per_token | 98304 | bytes | `estimated` |
| bytes_per_sequence | 201326592 | bytes | `estimated` |
| total_kv | 1610612736 | bytes | `estimated` |

Conclusion: The estimate excludes block rounding, reservation slack, and transfer copies.

## paged allocation on a variable-length KV trace

Record: `kv-paged-v1`. Result type: `simulated`.

| Metric | Value | Unit | Evidence |
| --- | ---: | --- | --- |
| reserved_blocks | 10 | blocks | `simulated` |
| used_blocks | 8 | blocks | `simulated` |
| free_blocks | 0 | blocks | `simulated` |
| evicted_blocks | 4 | blocks | `simulated` |
| recomputed_blocks | 2 | blocks | `simulated` |
| fragmentation_blocks | 0 | blocks | `simulated` |

Conclusion: The trace illustrates allocator state transitions only; it does not estimate runtime transfer, kernel, or quality costs.

## Model residency estimate for a declared synthetic configuration

Record: `model-memory-estimate-v1`. Result type: `estimated`.

| Metric | Value | Unit | Evidence |
| --- | ---: | --- | --- |
| weights | 2000000000 | bytes | `estimated` |
| activation_working_set | 33554432 | bytes | `estimated` |
| total_residency | 2033554432 | bytes | `estimated` |

Conclusion: This lower-bound estimate excludes allocator, runtime, and KV-cache headroom.

## Prefill-shaped roofline estimate with synthetic device ceilings

Record: `roofline-prefill-estimate-v1`. Result type: `estimated`.

| Metric | Value | Unit | Evidence |
| --- | ---: | --- | --- |
| arithmetic_intensity | 5 | operations per byte | `estimated` |
| bandwidth_ceiling | 5e+12 | operations per second | `estimated` |
| roofline_upper_bound | 2e+12 | operations per second | `estimated` |

Conclusion: The lower roof is compute in this synthetic configuration.
