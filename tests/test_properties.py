from __future__ import annotations

import random
import unittest

from inference_engineering.kv_simulation import KVBlockSimulator, KVEvent, KVSimulationConfig
from inference_engineering.memory import KVMemoryConfig, estimate_kv_memory


class MemoryPropertyTests(unittest.TestCase):
    def test_kv_memory_scales_linearly_with_concurrency(self) -> None:
        generator = random.Random(20260807)
        for _ in range(100):
            layers = generator.randint(1, 64)
            attention_heads = generator.choice((8, 16, 32, 64))
            kv_heads = generator.choice(
                tuple(
                    head
                    for head in (1, 2, 4, 8, 16, 32, 64)
                    if head <= attention_heads and attention_heads % head == 0
                )
            )
            base = KVMemoryConfig(
                layers=layers,
                attention_heads=attention_heads,
                kv_heads=kv_heads,
                head_dim=generator.choice((64, 128, 256)),
                tokens_per_sequence=generator.randint(1, 4096),
                concurrent_sequences=1,
                element_bytes=generator.choice((1, 2, 4)),
            )
            doubled = KVMemoryConfig(
                layers=base.layers,
                attention_heads=base.attention_heads,
                kv_heads=base.kv_heads,
                head_dim=base.head_dim,
                tokens_per_sequence=base.tokens_per_sequence,
                concurrent_sequences=2,
                element_bytes=base.element_bytes,
            )

            self.assertEqual(
                estimate_kv_memory(doubled).total_bytes, 2 * estimate_kv_memory(base).total_bytes
            )


class BlockAccountingPropertyTests(unittest.TestCase):
    def test_random_event_sequences_preserve_block_accounting(self) -> None:
        generator = random.Random(20260807)
        for sequence_number in range(50):
            config = KVSimulationConfig(
                total_blocks=generator.randint(4, 20),
                block_size_tokens=generator.choice((1, 2, 4, 8)),
                auto_evict=bool(generator.getrandbits(1)),
            )
            events: list[KVEvent] = []
            for tick in range(30):
                request_id = f"r{generator.randint(0, 12)}"
                action = generator.choice(("admit", "release", "evict", "touch"))
                if action == "admit":
                    tokens = generator.randint(1, 32)
                    reserve = tokens + generator.randint(0, 16)
                    events.append(KVEvent(tick, action, request_id, tokens, reserve))
                else:
                    events.append(KVEvent(tick, action, request_id))

            simulator = KVBlockSimulator(config)
            result = simulator.run(events)
            with self.subTest(sequence=sequence_number):
                simulator.assert_invariants()
                self.assertEqual(
                    result.final_state["reserved_blocks"] + result.final_state["free_blocks"],
                    result.final_state["total_blocks"],
                )
                self.assertLessEqual(
                    result.final_state["used_blocks"], result.final_state["reserved_blocks"]
                )
