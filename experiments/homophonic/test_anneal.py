"""Synthetic tests for the homophonic annealing warm-start prototype."""

from __future__ import annotations

from collections import Counter
import inspect
import json
import pathlib
import sys
import unittest
from unittest.mock import patch

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from experiments.homophonic.anneal import (
    anneal_homophonic,
    fit_language_model,
    score_homophonic_key,
    _IncrementalScorer,
)


class HomophonicAnnealTests(unittest.TestCase):
    def test_search_accumulation_drift_is_detected(self) -> None:
        original_commit = _IncrementalScorer.commit

        def corrupt_commit(scorer, indices, contributions):
            original_commit(scorer, indices, contributions)
            scorer.total -= 10000

        with patch.object(_IncrementalScorer, 'commit', corrupt_commit):
            with self.assertRaisesRegex(AssertionError, 'accumulated'):
                anneal_homophonic((('u', 'v'), ('v', 'u')), ('ab', 'ba'),
                                  plaintext_alphabet='ab', capacity=2,
                                  iterations=10, restarts=1, seed=17)

    def test_config_records_temperature_and_plaintext_alphabet(self) -> None:
        result = anneal_homophonic((('u',),), ('a',), plaintext_alphabet='abc',
                                  iterations=0, restarts=1, start_temperature=0.03)
        self.assertEqual(result['config']['start_temperature'], 0.03)
        self.assertEqual(result['config']['plaintext_alphabet'], ['a', 'b', 'c'])
        self.assertIn('alphabet_source', result['config'])

    def test_finite_capacities_keep_full_key_coverage(self) -> None:
        encrypted = (
            ("u", "v"),
            ("v", "w"),
            ("w", "x"),
        )
        train = ("ab", "ba", "aba", "bab")
        for capacity in (1, 2, None):
            result = anneal_homophonic(
                encrypted,
                train,
                plaintext_alphabet="abcd",
                capacity=capacity,
                iterations=8,
                restarts=2,
                seed=17,
            )
            self.assertEqual(set(result["key"]), {"u", "v", "w", "x"})
            counts = Counter(result["key"].values())
            if capacity is not None:
                self.assertLessEqual(max(counts.values()), capacity)
            self.assertEqual(result["score_details"]["mapped_unit_count"], 4)
            self.assertEqual(result["score_details"]["missing_unit_count"], 0)

    def test_capacity_one_rejects_too_many_units(self) -> None:
        with self.assertRaises(ValueError):
            anneal_homophonic(
                (("u", "v", "w"),),
                ("abc",),
                plaintext_alphabet="ab",
                capacity=1,
                iterations=1,
            )

    def test_capacity_two_allows_two_units_per_letter(self) -> None:
        result = anneal_homophonic(
            (("u", "v", "w"),),
            ("aaa", "bbb"),
            plaintext_alphabet="ab",
            capacity=2,
            iterations=4,
            restarts=1,
            seed=4,
        )
        self.assertEqual(len(result["key"]), 3)
        self.assertLessEqual(max(Counter(result["key"].values()).values()), 2)

    def test_same_seed_repeats_the_complete_result(self) -> None:
        args = {
            "encrypted_fit_words": (("u", "v"), ("v", "w"), ("w", "u")),
            "train_words": ("ab", "ba", "aba", "bab"),
            "plaintext_alphabet": "abc",
            "capacity": 2,
            "iterations": 20,
            "restarts": 3,
            "seed": 20260916,
        }
        self.assertEqual(anneal_homophonic(**args), anneal_homophonic(**args))

    def test_known_key_has_better_character_ngram_objective(self) -> None:
        train = ("ab", "aba", "ab", "aba", "bab", "ab")
        model = fit_language_model(
            train,
            order=2,
            add_alpha=0.1,
            alphabet="ab",
        )
        encrypted = (("u", "v"), ("u", "v", "u"), ("v", "u", "v"))
        correct = score_homophonic_key(encrypted, model, {"u": "a", "v": "b"})
        swapped = score_homophonic_key(encrypted, model, {"u": "b", "v": "a"})
        self.assertLess(correct["negative_log2_probability"], swapped["negative_log2_probability"])

    def test_incremental_result_matches_full_score(self) -> None:
        encrypted = (("u", "v"), ("v", "w"), ("w", "u"))
        train = ("ab", "ba", "aba", "bab")
        model = fit_language_model(train, order=2, alphabet="abc")
        for capacity in (2, None):
            result = anneal_homophonic(
                encrypted,
                train,
                plaintext_alphabet="abc",
                capacity=capacity,
                order=2,
                iterations=12,
                restarts=2,
                seed=23,
            )
            full = score_homophonic_key(encrypted, model, result["key"])
            self.assertAlmostEqual(
                result["score"],
                full["negative_log2_probability"],
                places=12,
            )

    def test_result_declares_budget_seed_and_has_no_oracle_interface(self) -> None:
        signature = inspect.signature(anneal_homophonic)
        self.assertNotIn("oracle", signature.parameters)
        self.assertNotIn("reference_key", signature.parameters)
        result = anneal_homophonic(
            (("u", "v"),),
            ("ab",),
            plaintext_alphabet="ab",
            capacity=1,
            iterations=3,
            restarts=2,
            seed=9,
        )
        self.assertEqual(result["seed"], 9)
        self.assertEqual(result["budget"]["iterations_per_restart"], 3)
        self.assertEqual(result["budget"]["restarts"], 2)
        self.assertNotIn("oracle", json.dumps(result).lower())
        self.assertNotIn("reference_key", json.dumps(result).lower())

    def test_tuple_units_are_required(self) -> None:
        with self.assertRaises(TypeError):
            anneal_homophonic(
                ("uv",),
                ("ab",),
                plaintext_alphabet="ab",
            )

    def test_empty_word_keeps_the_end_boundary_score(self) -> None:
        result = anneal_homophonic(
            ((),),
            ("a",),
            plaintext_alphabet="a",
            capacity=1,
            iterations=2,
            restarts=1,
            seed=2,
        )
        self.assertEqual(result["score_details"]["word_count"], 1)
        self.assertEqual(result["score_details"]["predicted_symbols"], 1)
        self.assertGreater(result["score"], 0.0)

    def test_plaintext_alphabet_contains_single_letters(self) -> None:
        with self.assertRaises(ValueError):
            anneal_homophonic(
                (("u",),),
                ("a",),
                plaintext_alphabet=("aa",),
            )


if __name__ == "__main__":
    unittest.main()
