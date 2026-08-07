from __future__ import annotations

import unittest

from inference_engineering.memory import (
    KVMemoryConfig,
    ModelMemoryConfig,
    estimate_kv_memory,
    estimate_model_memory,
)


class ModelMemoryTests(unittest.TestCase):
    def test_weights_and_activations_are_dimensionally_composed(self) -> None:
        config = ModelMemoryConfig(
            parameter_count=100,
            weight_bytes=2,
            layers=2,
            hidden_size=8,
            batch_size=3,
            sequence_length=4,
            activation_bytes=2,
            activation_tensors=2,
        )

        estimate = estimate_model_memory(config)

        self.assertEqual(estimate.weights_bytes, 200)
        self.assertEqual(estimate.activation_bytes, 3 * 4 * 8 * 2 * 2)
        self.assertEqual(estimate.total_bytes, 584)

    def test_invalid_model_dimensions_are_rejected(self) -> None:
        config = ModelMemoryConfig(
            parameter_count=0,
            weight_bytes=2,
            layers=1,
            hidden_size=1,
            batch_size=1,
            sequence_length=1,
        )

        with self.assertRaisesRegex(ValueError, "parameter_count"):
            estimate_model_memory(config)


class KVMemoryTests(unittest.TestCase):
    def test_grouped_query_attention_uses_fewer_kv_heads(self) -> None:
        common = {
            "layers": 2,
            "attention_heads": 8,
            "head_dim": 16,
            "tokens_per_sequence": 32,
            "concurrent_sequences": 2,
            "element_bytes": 2,
        }
        non_gqa = estimate_kv_memory(KVMemoryConfig(kv_heads=8, **common))
        gqa = estimate_kv_memory(KVMemoryConfig(kv_heads=2, **common))

        self.assertEqual(non_gqa.bytes_per_token, gqa.bytes_per_token * 4)
        self.assertEqual(gqa.kv_group_size, 4)
        self.assertEqual(gqa.total_bytes, gqa.bytes_per_sequence * 2)

    def test_invalid_head_relationships_are_rejected(self) -> None:
        too_many_kv_heads = KVMemoryConfig(1, 8, 16, 8, 16, 1)
        incompatible_groups = KVMemoryConfig(1, 10, 4, 8, 16, 1)

        with self.assertRaisesRegex(ValueError, "cannot exceed"):
            estimate_kv_memory(too_many_kv_heads)
        with self.assertRaisesRegex(ValueError, "divisible"):
            estimate_kv_memory(incompatible_groups)
