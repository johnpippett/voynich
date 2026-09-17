"""Synthetic tests for the scalar pivot-group upper bound."""

from __future__ import annotations

from collections import Counter
import itertools
import pathlib
import sys
import unittest


PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from experiments.group_bound.pivot import (  # noqa: E402
    CandidateConstructionLimit,
    PivotGroupBound,
)


Word = tuple[str, ...]


def _word(value: str | Word) -> Word:
    return tuple(value) if isinstance(value, str) else value


def _brute_best(
    counts: dict[str | Word, int],
    lexicon: set[str | Word],
    alphabet: tuple[str, ...],
    capacity: int | None,
    partial_key: dict[str, str] | None = None,
) -> int:
    normalized_counts = {_word(word): weight for word, weight in counts.items()}
    normalized_lexicon = {_word(word) for word in lexicon}
    symbols = tuple(sorted({symbol for word in normalized_counts for symbol in word}))
    best = 0
    for values in itertools.product(alphabet, repeat=len(symbols)):
        if capacity is not None and any(
            count > capacity for count in Counter(values).values()
        ):
            continue
        key = dict(zip(symbols, values, strict=True))
        if partial_key and any(
            key[symbol] != value for symbol, value in partial_key.items()
        ):
            continue
        score = sum(
            weight
            for word, weight in normalized_counts.items()
            if tuple(key[symbol] for symbol in word) in normalized_lexicon
        )
        best = max(best, score)
    return best


def _partial_maps(
    symbols: tuple[str, ...],
    alphabet: tuple[str, ...],
    capacity: int | None,
):
    for width in range(len(symbols) + 1):
        for selected in itertools.combinations(symbols, width):
            for values in itertools.product(alphabet, repeat=width):
                if capacity is not None and any(
                    count > capacity for count in Counter(values).values()
                ):
                    continue
                yield dict(zip(selected, values, strict=True))


class PivotGroupBoundTests(unittest.TestCase):
    def test_static_group_tightens_independent_word_bound(self) -> None:
        bound = PivotGroupBound(
            {"x": 1, "xy": 1},
            {"a", "ba"},
            "ab",
            capacity=1,
        )

        result = bound.bound()

        self.assertEqual(result["independent_bound"], 2)
        self.assertEqual(result["group_bound"], 1)
        self.assertEqual(result["bound"], 1)
        self.assertFalse(result["claims_global_optimality"])
        self.assertEqual(result["groups"][0]["pivot"], "x")
        self.assertEqual(
            {tuple(word) for word in result["groups"][0]["words"]},
            {("x",), ("x", "y")},
        )

    def test_every_partial_map_is_between_true_optimum_and_old_bound(self) -> None:
        counts = {
            ("x", "x"): 3,
            ("x", "y"): 4,
            ("y", "x"): 2,
            ("y", "z"): 5,
            ("z",): 1,
            (): 0,
        }
        lexicon = {
            ("a", "a"),
            ("a", "b"),
            ("b", "a"),
            ("b", "b"),
            ("a", "c"),
            ("c",),
            (),
        }
        alphabet = ("a", "b", "c")
        symbols = tuple(sorted({symbol for word in counts for symbol in word}))
        optimum_by_capacity = {
            capacity: _brute_best(counts, lexicon, alphabet, capacity)
            for capacity in (1, 2, None)
        }

        for capacity in (1, 2, None):
            bound = PivotGroupBound(
                counts,
                lexicon,
                alphabet,
                capacity=capacity,
            )
            for partial in _partial_maps(symbols, alphabet, capacity):
                result = bound.bound(partial)
                expected = _brute_best(
                    counts,
                    lexicon,
                    alphabet,
                    capacity,
                    partial,
                )
                self.assertLessEqual(
                    expected, result["group_bound"], (capacity, partial)
                )
                self.assertLessEqual(
                    result["group_bound"], result["independent_bound"],
                    (capacity, partial),
                )
                self.assertGreaterEqual(
                    result["group_bound"], 0, (capacity, partial)
                )
            root = bound.bound()
            self.assertGreaterEqual(root["group_bound"], optimum_by_capacity[capacity])

    def test_explicit_groups_are_validated_and_partition_word_types(self) -> None:
        counts = {"x": 1, "xy": 2, "yz": 3, "z": 4}
        lexicon = {"a", "ba", "ab", "bc", "c"}
        explicit = PivotGroupBound(
            counts,
            lexicon,
            "abc",
            capacity=1,
            groups=[("x", ["x", "xy"]), ("z", ["yz"])],
        )
        result = explicit.bound()
        self.assertEqual(result["group_count"], 2)
        grouped = {
            tuple(word)
            for group in result["groups"]
            for word in group["words"]
        }
        self.assertEqual(grouped, {("x",), ("x", "y"), ("y", "z")})
        self.assertEqual(result["ungrouped_words"], [["z"]])

        invalid_specs = (
            [("x", ["x"]), ("y", ["x"])],
            [("q", ["x"])],
            [("y", ["x"])],
            [("x", [])],
            [("x", ["missing"])],
        )
        for groups in invalid_specs:
            with self.assertRaises(ValueError):
                PivotGroupBound(counts, lexicon, "abc", groups=groups)

    def test_candidate_cache_is_input_independent_and_limited(self) -> None:
        counts = {"x": 1, "xy": 1}
        lexicon = ["a", "ba"]
        alphabet = ["a", "b"]
        bound = PivotGroupBound(
            counts,
            lexicon,
            alphabet,
            capacity=1,
        )
        counts["x"] = 99
        lexicon.append("bb")
        alphabet[0] = "z"
        result = bound.bound()
        self.assertEqual(result["independent_bound"], 2)
        self.assertEqual(result["group_bound"], 1)
        self.assertEqual(bound.metadata["candidate_count_total"], 2)

        merged = PivotGroupBound(
            {"xy": 2, ("x", "y"): 3},
            ["ab", "ab"],
            "ab",
            capacity=1,
        )
        self.assertEqual(merged.candidate_cache[0][1], 5)
        self.assertEqual(len(merged.candidate_cache[0][2]), 1)

        with self.assertRaises(CandidateConstructionLimit):
            PivotGroupBound(
                {"x": 1, "xy": 1},
                {"a", "ba"},
                "ab",
                capacity=1,
                max_candidate_rows=1,
            )

    def test_empty_words_zero_weights_unicode_units_and_no_candidates(self) -> None:
        bound = PivotGroupBound(
            {(): 0, ("ꝑ", "ka"): 2, ("empty",): 0},
            {(), ("a", "b")},
            ("a", "b"),
            capacity=None,
            groups=[("ꝑ", [("ꝑ", "ka")])],
        )
        result = bound.bound()
        self.assertEqual(result["group_bound"], 2)
        self.assertEqual(result["independent_bound"], 2)
        self.assertEqual(result["ungrouped_words"], [[], ["empty"]])

        no_candidates = PivotGroupBound(
            {"xx": 4},
            {"ab"},
            "ab",
            capacity=1,
        )
        no_candidate_result = no_candidates.bound()
        self.assertEqual(no_candidate_result["group_bound"], 0)
        self.assertEqual(no_candidate_result["independent_bound"], 0)

    def test_capacity_and_partial_key_validation_are_explicit(self) -> None:
        for capacity in (0, 3, True, 1.0, "2"):
            with self.assertRaises(ValueError):
                PivotGroupBound({"x": 1}, {"a"}, "ab", capacity=capacity)

        infeasible = PivotGroupBound(
            {"x": 1, "y": 1, "z": 1},
            {"a", "b", "c"},
            "ab",
            capacity=1,
        )
        result = infeasible.bound()
        self.assertEqual(result["status"], "infeasible_capacity")
        self.assertIsNone(result["group_bound"])
        self.assertIsNone(result["independent_bound"])

        bound = PivotGroupBound({"x": 1}, {"a"}, "ab", capacity=1)
        with self.assertRaises(ValueError):
            bound.bound({"q": "a"})
        with self.assertRaises(ValueError):
            bound.bound({"x": "q"})


if __name__ == "__main__":
    unittest.main()
