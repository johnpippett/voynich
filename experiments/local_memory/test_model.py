"""Synthetic tests for the finite-window word-similarity model."""

from __future__ import annotations

import math
import pathlib
import sys
import unittest

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from experiments.local_memory.model import (  # noqa: E402
    LAMBDAS,
    UNK,
    WINDOWS,
    fixed_mixture,
    fit_unigram,
    k0_distribution,
    k1_distribution,
    levenshtein_distance,
    score_lines,
    select_settings,
)


class LocalMemoryModelTests(unittest.TestCase):
    def test_requires_immutable_unit_word_tuples(self) -> None:
        with self.assertRaises(TypeError):
            fit_unigram(((("a",), ["b"]),))
        with self.assertRaises(TypeError):
            fit_unigram(((("a",),), [("b",)]))

    def test_fit_maps_singletons_and_keeps_first_training_words(self) -> None:
        model = fit_unigram(
            (
                (("a",), ("a",), ("b",)),
                (("a",), ("c",)),
            )
        )
        self.assertEqual(model.real_vocabulary, (("a",),))
        self.assertEqual(model.counts[("a",)], 3)
        self.assertEqual(model.counts[UNK], 2)
        self.assertEqual(model.train_word_count, 5)
        self.assertEqual(model.status, "ok")
        self.assertAlmostEqual(sum(model.p0.values()), 1.0)

    def test_empty_and_all_hapax_training_are_explicit(self) -> None:
        empty = fit_unigram(())
        self.assertEqual(empty.real_vocabulary, ())
        self.assertEqual(empty.counts[UNK], 0)
        self.assertEqual(empty.p0, {UNK: 1.0})
        self.assertEqual(empty.status, "degenerate_no_real_vocabulary")

        hapax = fit_unigram(((("a",),), (("b",),)))
        self.assertEqual(hapax.real_vocabulary, ())
        self.assertEqual(hapax.counts[UNK], 2)
        self.assertEqual(hapax.status, "degenerate_no_real_vocabulary")
        self.assertAlmostEqual(hapax.p0[UNK], 1.0)

    def test_exact_distance_has_insert_delete_substitute_only(self) -> None:
        self.assertEqual(levenshtein_distance((), ("a",)), 1)
        self.assertEqual(levenshtein_distance(("a",), ()), 1)
        self.assertEqual(levenshtein_distance(("a",), ("b",)), 1)
        self.assertEqual(levenshtein_distance(("a", "b"), ("b", "a")), 2)
        self.assertEqual(levenshtein_distance(("a", "b"), ("a", "b")), 0)

    def test_k0_is_point_mass_only_for_real_context(self) -> None:
        model = fit_unigram(
            ((("ab",), ("ab",), ("ac",)), (("ac",), ("ac",), ("zz",)))
        )
        real = k0_distribution(model, ("ab",))
        self.assertEqual(real[("ab",)], 1.0)
        self.assertEqual(sum(value for key, value in real.items() if key != ("ab",)), 0.0)
        open_context = k0_distribution(model, ("missing",))
        self.assertEqual(open_context, model.p0)

    def test_k1_uses_all_distance_one_neighbors_and_zero_unk(self) -> None:
        model = fit_unigram(
            (
                (("ab",), ("ab",), ("ac",), ("ac",)),
                (("zz",), ("zz",)),
            )
        )
        distribution = k1_distribution(model, ("aa",))
        self.assertGreater(distribution[("ab",)], 0.0)
        self.assertGreater(distribution[("ac",)], 0.0)
        self.assertEqual(distribution[UNK], 0.0)
        self.assertAlmostEqual(sum(distribution.values()), 1.0)
        fallback = k1_distribution(model, ("q", "q"))
        self.assertEqual(fallback, model.p0)

    def test_fixed_mixture_lambda_zero_equals_baseline(self) -> None:
        model = fit_unigram(
            ((("ab",), ("ab",), ("ac",), ("ac",)),)
        )
        contexts = (("aa",), ("ab",))
        for family in ("exact", "edit"):
            self.assertEqual(fixed_mixture(model, contexts, family=family, lambda_=0.0), model.p0)
            mixed = fixed_mixture(model, contexts, family=family, lambda_=0.5)
            self.assertAlmostEqual(sum(mixed.values()), 1.0)

    def test_score_excludes_first_word_and_does_not_cross_lines(self) -> None:
        model = fit_unigram(
            (
                (("a",), ("a",)),
                (("b",), ("b",)),
            )
        )
        two_singletons = score_lines(model, ((("a",),), (("a",),)), family="baseline", window=1, lambda_=0.0)
        joined = score_lines(model, ((("a",), ("a",)),), family="baseline", window=1, lambda_=0.0)
        self.assertEqual(two_singletons["target_count"], 0)
        self.assertEqual(two_singletons["status"], "no_targets")
        self.assertEqual(joined["target_count"], 1)
        self.assertEqual(joined["line_count"], 1)

    def test_score_counts_oov_targets_and_contexts(self) -> None:
        model = fit_unigram(((("aa",), ("aa",)),),)
        result = score_lines(
            model,
            ((("open",), ("aa",), ("missing",)),),
            family="edit",
            window=4,
            lambda_=0.5,
        )
        self.assertEqual(result["target_count"], 2)
        self.assertEqual(result["target_unk_count"], 1)
        self.assertEqual(result["context_count"], 3)
        self.assertEqual(result["context_oov_count"], 2)
        self.assertEqual(result["status"], "ok")
        self.assertTrue(math.isfinite(result["total_bits"]))

    def test_cached_and_uncached_edit_scores_are_equal(self) -> None:
        model = fit_unigram(
            ((("ab",), ("ab",), ("ac",), ("ac",), ("zz",), ("zz",)),)
        )
        lines = ((("aa",), ("ab",), ("aa",), ("ac",)),)
        cached = score_lines(model, lines, family="edit", window=4, lambda_=0.75, cache=True)
        uncached = score_lines(model, lines, family="edit", window=4, lambda_=0.75, cache=False)
        self.assertEqual(cached, uncached)

    def test_lambda_and_window_are_validated(self) -> None:
        model = fit_unigram(((("a",), ("a",)),),)
        with self.assertRaises(ValueError):
            score_lines(model, ((("a",), ("a",)),), family="exact", window=0, lambda_=0.0)
        with self.assertRaises(ValueError):
            score_lines(model, ((("a",), ("a",)),), family="exact", window=1, lambda_=0.8)
        with self.assertRaises(ValueError):
            score_lines(model, ((("a",), ("a",)),), family="unknown", window=1, lambda_=0.0)

    def test_selection_returns_full_grid_and_smallest_tie_settings(self) -> None:
        model = fit_unigram(((("aa",), ("aa",)),),)
        validation = ((("zz",), ("zz",)),)
        result = select_settings(model, validation)
        self.assertEqual(result["status"], "selected")
        self.assertEqual(len(result["validation_grid"]), len(WINDOWS) * len(LAMBDAS) * 2)
        for family in ("exact", "edit"):
            choice = result["choice"][family]
            self.assertEqual(choice["lambda"], min(LAMBDAS))
            self.assertEqual(choice["window"], min(WINDOWS))

    def test_selection_abstains_without_validation_targets(self) -> None:
        model = fit_unigram(((("a",), ("a",)),),)
        result = select_settings(model, ((("a",),),))
        self.assertEqual(result["status"], "abstain_no_validation_targets")
        self.assertIsNone(result["choice"]["exact"])
        self.assertIsNone(result["choice"]["edit"])
        self.assertTrue(result["validation_grid"])

    def test_scoring_and_selection_do_not_change_fitted_model(self) -> None:
        model = fit_unigram(((("ab",), ("ab",), ("ac",)),),)
        before = (model.counts, model.p0, model.real_vocabulary, model.status)
        score_lines(model, ((("ab",), ("ac",)),), family="exact", window=1, lambda_=0.25)
        select_settings(model, ((("ab",), ("ac",)),))
        after = (model.counts, model.p0, model.real_vocabulary, model.status)
        self.assertEqual(before, after)

    def test_empty_validation_does_not_select(self) -> None:
        model = fit_unigram(((("a",), ("a",)),),)
        result = select_settings(model, ())
        self.assertEqual(result["status"], "abstain_no_validation_targets")
        self.assertEqual(result["validation_target_count"], 0)


if __name__ == "__main__":
    unittest.main()
