"""Behavioral tests for the bounded monoalphabetic substitution search."""

from __future__ import annotations

import json
import pathlib
import sys
import unittest


PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from voynich.substitution import (
    fit_language_model,
    score_heldout,
    score_with_key,
    score_with_key_incremental,
    search_substitution,
)


def _toy_training() -> list[str]:
    heldout = ["abde", "caba", "deca", "bace", "edab"]
    # Train on distinct words that preserve useful local character patterns.
    # The suffix/prefix variants keep every held-out word out of the fit set.
    variants = [
        *(word + "a" for word in heldout),
        *("a" + word for word in heldout),
        *(word + "b" for word in heldout),
        *("b" + word for word in heldout),
    ]
    return variants * 12


def _encipher(words: list[str], plaintext_to_cipher: dict[str, str]) -> list[str]:
    return ["".join(plaintext_to_cipher[char] for char in word) for word in words]


class SubstitutionBehaviorTests(unittest.TestCase):
    def test_model_has_fixed_boundaries_and_serializable_definition(self) -> None:
        model = fit_language_model(
            [("a", "b", "a"), ("b", "a")],
            order=2,
            alphabet=("a", "b", "c"),
        )

        self.assertEqual(model.order, 2)
        self.assertEqual(model.start_symbol, "<BOS>")
        self.assertEqual(model.end_symbol, "<EOS>")
        self.assertEqual(model.alphabet, ("a", "b", "c"))
        self.assertIn("definition", model.to_dict())
        json.dumps(model.to_dict())

    def test_empty_and_unknown_inputs_are_scored_without_invented_mapping(self) -> None:
        model = fit_language_model(["ab", "ba"], alphabet="ab")

        empty = search_substitution([], model, iterations=5, restarts=1)
        self.assertIn("status", empty)
        self.assertEqual(empty["status"], "empty_input")
        self.assertEqual(empty["key"], {})

        score = score_heldout(["az"], model, {"a": "a"})
        self.assertGreater(score["unknown_cipher_symbols"], 0)
        self.assertGreater(score["missing_key_types"], 0)
        self.assertEqual(score["word_count"], 1)

        complete = score_heldout(
            ["qx"],
            model,
            {"q": "a", "x": "b"},
            {"q": "a", "x": "b"},
        )
        self.assertFalse(complete["partial_key_coverage"])
        self.assertEqual(complete["recovery_metrics"]["exact_word_accuracy"], 1.0)

    def test_alphabet_mismatch_is_reported_without_many_to_one_mapping(self) -> None:
        model = fit_language_model(["abc", "bca"], alphabet="abc")

        result = search_substitution(["wxyz"], model, iterations=10, restarts=2)

        self.assertIn("status", result)
        self.assertEqual(result["status"], "alphabet_mismatch")
        self.assertEqual(result["key"], {})
        self.assertEqual(result["config"]["mapping_kind"], "injective")
        self.assertEqual(result["alphabet"]["cipher_size"], 4)

    def test_known_cipher_recovery_reports_weighted_character_and_key_metrics(self) -> None:
        plaintext_to_cipher = {"a": "q", "b": "x", "c": "m", "d": "t", "e": "r"}
        heldout_plain = ["abde", "caba", "deca", "bace", "edab"]
        cipher = _encipher(heldout_plain, plaintext_to_cipher)
        reference_key = {cipher_symbol: plain_symbol for plain_symbol, cipher_symbol in plaintext_to_cipher.items()}
        model = fit_language_model(_toy_training(), order=3, alphabet="abcde")

        result = search_substitution(
            cipher,
            model,
            iterations=2500,
            restarts=12,
            seed=17,
            reference_key=reference_key,
        )

        self.assertIn("status", result)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(len(result["key"]), 5)
        self.assertEqual(len(set(result["key"].values())), len(result["key"]))
        metrics = result["recovery_metrics"]
        self.assertEqual(metrics["key_coverage"], 1.0)
        self.assertEqual(metrics["key_assignment_accuracy"], 1.0)
        self.assertEqual(metrics["key_assignment_correct"], 5)
        self.assertEqual(metrics["key_assignment_total"], 5)
        self.assertEqual(metrics["exact_character_correct"], metrics["exact_character_total"])
        self.assertEqual(metrics["exact_word_correct"], metrics["exact_word_total"])
        self.assertGreaterEqual(metrics["exact_character_accuracy"], 0.8)
        self.assertGreaterEqual(metrics["exact_word_accuracy"], 0.6)
        self.assertNotIn("weighted_recovery", metrics)

    def test_search_and_incremental_score_are_reproducible(self) -> None:
        plaintext_to_cipher = {"a": "q", "b": "x", "c": "m", "d": "t", "e": "r"}
        cipher = _encipher(["abca", "deca", "bace"], plaintext_to_cipher)
        model = fit_language_model(_toy_training(), order=3, alphabet="abcde")

        first = search_substitution(cipher, model, iterations=400, restarts=4, seed=23)
        second = search_substitution(cipher, model, iterations=400, restarts=4, seed=23)
        self.assertEqual(first, second)

        self.assertIn("key", first)
        direct = score_with_key(cipher, model, first["key"])
        incremental = score_with_key_incremental(cipher, model, first["key"])
        self.assertAlmostEqual(direct["negative_log2_probability"], incremental["negative_log2_probability"], places=10)
        self.assertEqual(direct["predicted_symbols"], incremental["predicted_symbols"])

    def test_duplicate_plaintext_assignments_are_rejected(self) -> None:
        model = fit_language_model(["ab", "ba"], alphabet="ab")

        with self.assertRaises(ValueError):
            score_with_key(["ab"], model, {"a": "a", "b": "a"})


if __name__ == "__main__":
    unittest.main()
