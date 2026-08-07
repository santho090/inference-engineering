# Equations and notation

The equations in this guide are estimates. They identify impossible configurations and useful hypotheses. They do not promise realized throughput or memory residency.

| Symbol | Meaning |
| --- | --- |
| `P` | Parameter count |
| `b_w` | Bytes per weight element |
| `B` | Batch or concurrent sequence count |
| `S` | Tokens per sequence |
| `H` | Hidden size |
| `b_a` | Bytes per activation element |
| `a` | Number of modeled activation tensors |
| `L` | Number of layers |
| `H_kv` | Number of key-value heads |
| `d_h` | Head dimension |
| `b_e` | Bytes per KV element |
| `O` | Operations in one modeled operation |
| `D` | Bytes moved in one modeled operation |
| `P_peak` | Qualified peak compute ceiling |
| `BW` | Qualified memory-bandwidth ceiling |

## Weight and activation estimate

```text
weights_bytes = P * b_w
activation_working_set_bytes = B * S * H * b_a * a
total_residency_bytes = weights_bytes + activation_working_set_bytes
```

`ie memory model` calculates this lower-bound residency estimate. It does not include runtime workspaces, graph capture, allocator slack, KV state, transfer copies, or implementation-specific activation lifetime.

## KV-cache estimate

```text
kv_bytes_per_token = L * H_kv * d_h * 2 * b_e
kv_bytes_per_sequence = kv_bytes_per_token * S
total_kv_bytes = kv_bytes_per_sequence * B
```

The factor of two represents keys and values. GQA changes `H_kv`; it is often smaller than the query-head count. The estimate does not include page rounding, reservation slack, prefix-sharing references, tier copies, or eviction and recomputation work.

## Logical blocks

```text
reserved_blocks = ceil(reserve_tokens / block_size_tokens)
used_blocks = ceil(used_tokens / block_size_tokens)
free_blocks + reserved_blocks = total_blocks
```

The final equality is a simulator invariant. It does not imply a contiguous allocation can be made because free blocks may be fragmented.

## Roofline bound

```text
arithmetic_intensity = O / D
bandwidth_ceiling = arithmetic_intensity * BW
upper_bound = min(P_peak, bandwidth_ceiling)
```

The bound omits launch overhead, synchronization, contention, cache effects, and transfer behavior. Use it to reject irrelevant optimization families, then measure the actual phase.

## Request metrics

```text
TTFT = admission_to_engine_start + engine_to_first_token + client_delivery
TPOT = mean(inter_token_latency after first token)
completion = final_token_time - admission_time
goodput = objective_satisfying_completions / time_or_resource_cost
```

Each summand needs an explicit timestamp boundary. Goodput is not raw output throughput; it excludes completions that fail the declared objectives.
