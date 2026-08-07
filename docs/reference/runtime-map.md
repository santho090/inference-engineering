# Runtime and upstream seam map

These public projects expose different integration seams. The seams are version-sensitive places to inspect, not promises that an extension will be accepted or that two projects are compatible. Read each project's current documentation, source tests, license, and contribution guidance before relying on an interface.

| Project | Primary layer | Public source | Concrete seam to inspect | Bounded first contribution shape |
| --- | --- | --- | --- | --- |
| [FlashInfer](https://docs.flashinfer.ai/) | L1 | [Official documentation](https://docs.flashinfer.ai/) and [public source](https://github.com/flashinfer-ai/flashinfer) | BatchAttention planning and execution, including paged-KV layout, batch metadata, and shape-sensitive test coverage. | A public reproducer for one layout or shape edge case, with a correctness reference and no broad kernel rewrite. |
| [vLLM](https://docs.vllm.ai/) | L2 and L3 | [Official documentation](https://docs.vllm.ai/) and [public source](https://github.com/vllm-project/vllm) | The scheduler and KV-cache-manager boundary, including admission, allocation, prefix caching, and KV-transfer configuration. | A trace-defined scheduler or cache-policy observation, followed by a narrow issue or test if the public interface is insufficient. |
| [SGLang](https://docs.sglang.io/) | L2 and L3 | [Official documentation](https://docs.sglang.io/) and [public source](https://github.com/sgl-project/sglang) | RadixAttention prefix reuse and the surrounding scheduler and attention-backend behavior. | A synthetic prefix-reuse trace or observability proposal that keeps cache identity and request outcomes explicit. |
| [LMCache](https://docs.lmcache.ai/) | L3 and L5 | [Official documentation](https://docs.lmcache.ai/) and [public source](https://github.com/LMCache/LMCache) | Engine connectors, cache lookup and storage lifecycle, and the documented L2 adapter or storage-plugin contracts. | A public storage-adapter or connector test using synthetic KV metadata and a declared fallback path. |
| [llm-d](https://llm-d.ai/) | L4 to L6 | [Official documentation](https://llm-d.ai/) and [public source](https://github.com/llm-d/llm-d) | Router endpoint selection, disaggregation profiles, cache-aware scoring, and the documented KV event path. | A scenario definition or small policy-scoring proposal with explicit routing guardrails and failure accounting. |

## Contribution path

1. Reproduce a bounded public problem with synthetic or permitted public fixtures.
2. Identify one documented seam and read its current source tests before proposing a code change.
3. Discuss the smallest useful interface or test change before implementing a large patch.
4. Submit code with a workload definition, measurement boundaries, result labels, and failure accounting.
5. Keep experimental policy code outside a runtime until its abstraction is accepted.

The planned inference-bottleneck-lab and kv-policy-lab projects remain planned until they exist. They are intended to hold broader diagnosis and KV-policy experiments without turning this field guide into a serving system. See the [project opportunity map](project-opportunity-map.md) for dependency order and clean-room project slices.
