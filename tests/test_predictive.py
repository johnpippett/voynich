"""Behavioral tests for reproducible Voynich character prediction."""

from __future__ import annotations

import pathlib
import sys
import unittest


PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from voynich.predictive import run_predictive
from voynich.groups import split_bucket


def _record(folio: str, tokens: list[str], locus: str = "1") -> dict:
    return {
        "folio": folio,
        "locus": locus,
        "kind": "transcription",
        "tokens": tokens,
        "metadata": {"source": "test"},
    }


def _bucket(leaf: str) -> int:
    return split_bucket(leaf)


class PredictiveBehaviorTests(unittest.TestCase):
    def test_folio_group_split_has_explicit_manifests(self) -> None:
        records = [
            _record("f85r1", ["test_foldout"]),
            _record("f86v2", ["same_foldout_group"]),
            _record("fRos", ["rosette_panel"]),
            _record("f1r1", ["train"]),
            _record("f19r1", ["validation"]),
        ]

        result = run_predictive(records)
        self.assertIn("split_manifest", result)
        manifest = result["split_manifest"]

        self.assertEqual(manifest["train"]["groups"], ["1"])
        self.assertEqual(manifest["train"]["folios"], ["f1r1"])
        self.assertEqual(manifest["validation"]["groups"], ["19"])
        self.assertEqual(manifest["test"]["groups"], ["85"])
        self.assertEqual(manifest["test"]["folios"], ["f85r1", "f86v2", "fRos"])
        self.assertEqual(manifest["train"]["bucket"], _bucket("1"))
        self.assertEqual(manifest["validation"]["bucket"], _bucket("19"))
        self.assertEqual(manifest["test"]["bucket"], _bucket("85"))
        self.assertEqual(manifest["grouping_config"]["confirmed_cross_number_foldout"], [85, 86])
        self.assertEqual(result["counts"]["groups"]["train"], 1)
        self.assertEqual(result["counts"]["leaves"]["train"], 1)

    def test_grouped_and_raw_nulls_declare_different_units(self) -> None:
        result = run_predictive([_record("f1r1", ["cthch"]), _record("f3r1", ["cthch"])])
        null = result["config"]["shuffled_null"]["per_unitization"]

        self.assertEqual(null["raw_eva"]["shuffled_units"], "single raw characters")
        self.assertEqual(null["grouped"]["shuffled_units"], "declared grouped units")
        self.assertTrue(null["grouped"]["preserves_flattened_character_length"])
        self.assertFalse(null["grouped"]["matches_raw_character_permutation_distribution"])

    def test_character_model_keeps_accepted_tokens_on_uncertain_lines(self) -> None:
        result = run_predictive(
            [
                dict(_record("f1r1", ["abc"]), excluded_tokens=1),
                _record("f3r1", ["abc"]),
            ]
        )

        model = result["models"]["observed"]["raw_eva"]["order_0"]
        self.assertIn("a", model["alphabet"])
        self.assertIn("b", model["alphabet"])
        self.assertIn("c", model["alphabet"])

    def test_add_alpha_probabilities_normalize_and_include_end_symbol(self) -> None:
        result = run_predictive(
            [
                _record("f1r1", ["aba", "abb"]),
                _record("f3r1", ["aba"]),
            ]
        )

        self.assertIn("models", result)
        for order_name, model in result["models"]["observed"]["raw_eva"].items():
            with self.subTest(order=order_name):
                self.assertEqual(model["add_alpha"], 0.1)
                self.assertEqual(model["end_symbol"], "<EOS>")
                self.assertIn("<EOS>", model["vocabulary"])
                self.assertIn("<EOS>", model["symbol_counts"])
                for total in model["probability_sums"].values():
                    self.assertAlmostEqual(total, 1.0, places=12)

    def test_test_only_characters_map_to_unk_without_alphabet_leak(self) -> None:
        result = run_predictive(
            [
                _record("f1r1", ["aaaa", "aa"]),
                _record("f3r1", ["az"]),
            ]
        )

        self.assertIn("models", result)
        self.assertIn("scores", result)
        model = result["models"]["observed"]["raw_eva"]["order_0"]
        score = result["scores"]["observed"]["raw_eva"]["order_0"]
        self.assertNotIn("z", model["alphabet"])
        self.assertIn("<UNK>", model["vocabulary"])
        self.assertGreater(score["unknown_symbols"], 0)
        self.assertEqual(score["eos_count"], 1)
        self.assertEqual(score["predicted_symbols"], 3)

    def test_character_ngram_learns_a_repeated_toy_pattern(self) -> None:
        result = run_predictive(
            [
                _record("f1r1", ["aba"] * 40),
                _record("f3r1", ["aba"] * 4),
            ]
        )

        self.assertIn("scores", result)
        scores = result["scores"]["observed"]["raw_eva"]
        self.assertLess(
            scores["order_3"]["bits_per_symbol"],
            scores["order_0"]["bits_per_symbol"],
        )

    def test_shuffled_null_preserves_word_shape_and_is_scored_on_same_test(self) -> None:
        result = run_predictive(
            [
                _record("f1r1", ["abca", "dddd"]),
                _record("f3r1", ["abca"]),
            ]
        )

        self.assertIn("config", result)
        self.assertIn("scores", result)
        null = result["config"]["shuffled_null"]
        self.assertEqual(null["seed"], 408)
        self.assertTrue(null["within_word"])
        self.assertTrue(null["preserves_token_lengths"])
        self.assertTrue(null["preserves_character_multisets"])
        self.assertEqual(
            result["scores"]["shuffled_null"]["raw_eva"]["order_0"]["test_token_count"],
            result["scores"]["observed"]["raw_eva"]["order_0"]["test_token_count"],
        )

    def test_empty_splits_and_repeated_runs_are_robust_and_deterministic(self) -> None:
        records = [_record("f1r1", ["abc"])]

        first = run_predictive(records)
        second = run_predictive(records)

        self.assertEqual(first, second)
        self.assertIn("counts", first)
        self.assertIn("scores", first)
        self.assertEqual(first["counts"]["records"]["test"], 0)
        for score in first["scores"]["observed"]["raw_eva"].values():
            self.assertEqual(score["predicted_symbols"], 0)
            self.assertIsNone(score["bits_per_symbol"])


if __name__ == "__main__":
    unittest.main()
