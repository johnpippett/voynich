"""Synthetic tests for exact frozen-model secondary ranking."""

from __future__ import annotations

from collections import Counter
from dataclasses import replace
from fractions import Fraction
import itertools
import json
import math
import pathlib
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from voynich.substitution import (  # noqa: E402
    END_SYMBOL,
    START_SYMBOL,
    LanguageModel,
    fit_language_model,
)
from experiments.optimal_set.secondary import rank_secondary  # noqa: E402


def _word(value: str | tuple[str, ...]) -> tuple[str, ...]:
    return tuple(value) if isinstance(value, str) else value


def _model_maps(model: LanguageModel):
    counts = {
        tuple(json.loads(context)): dict(rows)
        for context, rows in model.context_counts
    }
    totals = dict(model.context_total_map)
    totals = {
        tuple(json.loads(context)): total for context, total in model.context_totals
    }
    return counts, totals


def _context(sequence: tuple[str, ...], position: int, order: int) -> tuple[str, ...]:
    if order == 0:
        return ()
    prefix_length = max(0, order - position)
    history = sequence[max(0, position - order) : position]
    return (START_SYMBOL,) * prefix_length + history


def _brute_likelihood(
    model: LanguageModel,
    counts: dict[str | tuple[str, ...], int],
    key: dict[str, str],
) -> Fraction:
    model_counts, model_totals = _model_maps(model)
    likelihood = Fraction(1, 1)
    for raw_word, weight in counts.items():
        word = _word(raw_word)
        mapped = tuple(key[symbol] for symbol in word)
        for position, target in enumerate((*mapped, END_SYMBOL)):
            context = _context(mapped, position, model.order)
            event_count = model_counts.get(context, {}).get(target, 0)
            context_total = model_totals.get(context, 0)
            probability = Fraction(
                10 * event_count + 1,
                10 * context_total + len(model.vocabulary),
            )
            likelihood *= probability**weight
    return likelihood


def _ratio(result: dict[str, object], index: int) -> Fraction:
    encoded = result["candidate_results"][index]["likelihood_ratio"]  # type: ignore[index]
    return Fraction(
        int(encoded["numerator_hex"], 16),  # type: ignore[index]
        int(encoded["denominator_hex"], 16),  # type: ignore[index]
    )


class SecondaryRankingTests(unittest.TestCase):
    def test_exact_ratios_match_brute_for_all_orders_and_eos_unknown(self) -> None:
        training = ["ab", "ba", "aq", "a"]
        counts = {"xx": 2, "xy": 1, ("y", "x"): 3}
        candidates = [
            {"x": "a", "y": "b"},
            {"x": "b", "y": "a"},
            {"x": "a", "y": "a"},
        ]
        for order in range(5):
            model = fit_language_model(training, order=order, add_alpha=0.1, alphabet="ab")
            result = rank_secondary(model, counts, candidates, capacity=2)
            self.assertEqual(result["status"], "complete")
            self.assertEqual(result["config"]["order"], order)
            self.assertEqual(result["config"]["vocabulary_size"], 4)
            likelihoods = [
                _brute_likelihood(model, counts, candidate) for candidate in candidates
            ]
            baseline = likelihoods[result["canonical_candidate_index"]]
            for index, likelihood in enumerate(likelihoods):
                self.assertEqual(_ratio(result, index), likelihood / baseline)
                self.assertAlmostEqual(
                    result["candidate_results"][index]["log2_ratio"],  # type: ignore[index]
                    math.log2(float(likelihood / baseline)),
                    places=12,
                )
            self.assertFalse(result["claims_global_optimality"])
            self.assertFalse(result["claims_candidate_set_complete"])

    def test_exact_ties_retain_all_maximizers_and_use_display_tie_only(self) -> None:
        model = fit_language_model(["a", "b"], order=0, add_alpha=0.1, alphabet="ab")
        candidates = [{"x": "b"}, {"x": "a"}, {"x": "a"}]
        result = rank_secondary(model, {"x": 4}, candidates, capacity=1)
        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["maximizer_indices"], [0, 1, 2])
        self.assertEqual(result["display_key"], {"x": "a"})
        self.assertEqual(result["display_index"], 1)

        near_model = fit_language_model(
            ["a"] * 1000 + ["b"] * 999,
            order=0,
            add_alpha=0.1,
            alphabet="ab",
        )
        near = rank_secondary(
            near_model,
            {"x": 1},
            [{"x": "a"}, {"x": "b"}],
            capacity=1,
        )
        self.assertEqual(near["maximizer_indices"], [0])
        self.assertNotEqual(_ratio(near, 0), _ratio(near, 1))

    def test_capacity_and_complete_key_validation(self) -> None:
        model = fit_language_model(["ab"], order=2, add_alpha=0.1, alphabet="ab")
        counts = {"xy": 1}
        with self.assertRaises(ValueError):
            rank_secondary(model, counts, [{"x": "a", "y": "a"}], capacity=1)
        with self.assertRaises(ValueError):
            rank_secondary(model, counts, [{"x": "a"}], capacity=2)
        with self.assertRaises(ValueError):
            rank_secondary(model, counts, [{"x": "a", "y": "q"}], capacity=2)
        with self.assertRaises(ValueError):
            rank_secondary(model, counts, [{"x": "a", "y": "b", "z": "a"}])
        with self.assertRaises(ValueError):
            rank_secondary(model, counts, [{"x": "a", "y": "b"}], capacity=3)

        result = rank_secondary(
            model,
            counts,
            [{"x": "a", "y": "a"}],
            capacity=2,
        )
        self.assertEqual(result["status"], "complete")

    def test_delta_and_ratio_limits_return_no_declared_winner(self) -> None:
        model = fit_language_model(["a", "b"], order=1, add_alpha=0.1, alphabet="ab")
        candidates = [{"x": "a"}, {"x": "b"}]
        delta_limited = rank_secondary(
            model,
            {"x": 1},
            candidates,
            max_delta_events=0,
        )
        self.assertEqual(delta_limited["status"], "not_complete")
        self.assertEqual(delta_limited["reason"], "max_delta_events")
        self.assertEqual(delta_limited["maximizer_indices"], [])
        self.assertIsNone(delta_limited["display_key"])

        ratio_limited = rank_secondary(
            model,
            {"x": 1},
            candidates,
            max_ratio_bits=1,
        )
        self.assertEqual(ratio_limited["status"], "not_complete")
        self.assertEqual(ratio_limited["reason"], "max_ratio_bits")
        self.assertEqual(ratio_limited["maximizer_indices"], [])

    def test_input_copies_model_alpha_and_empty_case(self) -> None:
        model = fit_language_model(["ab"], order=3, add_alpha=0.1, alphabet="ab")
        counts = {"x": 2}
        candidates = [{"x": "a"}, {"x": "b"}]
        result = rank_secondary(model, counts, candidates)
        counts["x"] = 99
        candidates[0]["x"] = "b"
        self.assertEqual(result["candidate_results"][0]["key"], {"x": "a"})

        with self.assertRaises(ValueError):
            rank_secondary(replace(model, add_alpha=0.2), {"x": 1}, [{"x": "a"}])
        with self.assertRaises(ValueError):
            rank_secondary(model, {"x": True}, [{"x": "a"}])  # type: ignore[dict-item]
        with self.assertRaises(TypeError):
            rank_secondary(model, {"x": 1}, [None])  # type: ignore[list-item]

        empty = rank_secondary(model, {}, [{}], capacity=1)
        self.assertEqual(empty["status"], "complete")
        self.assertEqual(empty["maximizer_indices"], [0])
        self.assertEqual(_ratio(empty, 0), Fraction(1, 1))

    def test_malformed_model_tables_are_rejected_before_ranking(self) -> None:
        model = fit_language_model(
            ["ab", "ba"],
            order=1,
            add_alpha=0.1,
            alphabet="ab",
        )
        counts = {"x": 1, "xy": 1}
        candidates = [{"x": "a", "y": "b"}, {"x": "b", "y": "a"}]

        valid = rank_secondary(model, counts, candidates)
        self.assertEqual(valid["maximizer_indices"], [0, 1])

        missing_row = replace(
            model,
            context_counts=tuple(
                row for row in model.context_counts if json.loads(row[0]) != ["a"]
            ),
        )
        with self.assertRaisesRegex(ValueError, "context"):
            rank_secondary(missing_row, counts, candidates)

        extra_total = replace(
            model,
            context_totals=(*model.context_totals, (json.dumps(["extra"]), 0)),
        )
        with self.assertRaisesRegex(ValueError, "context"):
            rank_secondary(extra_total, counts, candidates)

        repeated_context = replace(
            model,
            context_counts=(model.context_counts[0], model.context_counts[0]),
        )
        with self.assertRaisesRegex(ValueError, "duplicate"):
            rank_secondary(repeated_context, counts, candidates)

        context_key, rows = model.context_counts[0]
        repeated_target = replace(
            model,
            context_counts=(
                (context_key, (*rows, rows[0])),
                *model.context_counts[1:],
            ),
        )
        with self.assertRaisesRegex(ValueError, "target"):
            rank_secondary(repeated_target, counts, candidates)

        boolean_count = replace(
            model,
            context_counts=(
                (context_key, ((rows[0][0], True), *rows[1:])),
                *model.context_counts[1:],
            ),
        )
        with self.assertRaisesRegex(ValueError, "count"):
            rank_secondary(boolean_count, counts, candidates)

        out_of_vocab_zero = replace(
            model,
            context_counts=(
                (context_key, ((*rows, ("q", 0)))),
                *model.context_counts[1:],
            ),
        )
        with self.assertRaisesRegex(ValueError, "target"):
            rank_secondary(out_of_vocab_zero, counts, candidates)

        invalid_length = replace(
            model,
            context_counts=(
                (json.dumps(["a", "b"]), rows),
                *model.context_counts[1:],
            ),
        )
        with self.assertRaisesRegex(ValueError, "length"):
            rank_secondary(invalid_length, counts, candidates)

        start_model = fit_language_model(
            ["ab", "ba"],
            order=2,
            add_alpha=0.1,
            alphabet="ab",
        )
        _start_context_key, start_rows = start_model.context_counts[0]
        invalid_start = replace(
            start_model,
            context_counts=(
                (json.dumps(["a", START_SYMBOL]), start_rows),
                *start_model.context_counts[1:],
            ),
        )
        with self.assertRaisesRegex(ValueError, "START"):
            rank_secondary(invalid_start, counts, candidates)

        unknown_override = replace(model, unknown_symbol="a")
        with self.assertRaisesRegex(ValueError, "unknown"):
            rank_secondary(unknown_override, counts, candidates)



if __name__ == "__main__":
    unittest.main()
