"""Differential tests for capacity-aware preserved-hit ambiguity counts."""

from __future__ import annotations

from collections import Counter
import itertools
import unittest

from experiments.homophonic.ambiguity import preserved_hit_completions
from experiments.lexicon.ambiguity import (
    preserved_hit_completions as preserved_injective,
)


Word = tuple[str, ...]


def _symbols(counts: dict[Word, int]) -> tuple[str, ...]:
    return tuple(sorted({symbol for word in counts for symbol in word}))


def _score(
    counts: dict[Word, int], lexicon: set[Word], key: dict[str, str]
) -> int:
    return sum(
        weight
        for word, weight in counts.items()
        if tuple(key[symbol] for symbol in word) in lexicon
    )


def _valid_keys(
    counts: dict[Word, int], alphabet: tuple[str, ...], capacity: int | None
) -> list[dict[str, str]]:
    symbols = _symbols(counts)
    result = []
    for values in itertools.product(alphabet, repeat=len(symbols)):
        if capacity is not None and any(
            count > capacity for count in Counter(values).values()
        ):
            continue
        result.append(dict(zip(symbols, values, strict=True)))
    return result


def _brute_completions(
    counts: dict[Word, int],
    lexicon: set[Word],
    alphabet: tuple[str, ...],
    key: dict[str, str],
    capacity: int | None,
) -> tuple[int, int]:
    symbols = _symbols(counts)
    covered = {
        symbol
        for word, weight in counts.items()
        if weight > 0
        and tuple(key[symbol] for symbol in word) in lexicon
        for symbol in word
    }
    free = [symbol for symbol in symbols if symbol not in covered]
    fixed = {symbol: key[symbol] for symbol in covered}
    incumbent = _score(counts, lexicon, key)
    count = 0
    for values in itertools.product(alphabet, repeat=len(free)):
        candidate = dict(fixed)
        candidate.update(zip(free, values, strict=True))
        if capacity is not None and any(
            used > capacity for used in Counter(candidate.values()).values()
        ):
            continue
        count += 1
        assert _score(counts, lexicon, candidate) >= incumbent
    return count, len(covered)


class HomophonicAmbiguityTests(unittest.TestCase):
    def test_finite_and_unlimited_counts_match_direct_enumeration(self) -> None:
        counts = {
            ("x", "y"): 2,
            ("y", "x"): 1,
            ("z",): 0,
        }
        lexicon = {("a", "a"), ("a", "b"), ("b", "a")}
        alphabet = ("a", "b", "c")

        for capacity in (1, 2, None):
            for key in _valid_keys(counts, alphabet, capacity):
                expected_count, expected_covered = _brute_completions(
                    counts, lexicon, alphabet, key, capacity
                )
                result = preserved_hit_completions(
                    counts, lexicon, alphabet, key, capacity=capacity
                )
                self.assertEqual(result["completion_count"], expected_count)
                self.assertEqual(
                    result["covered_symbol_count"], expected_covered
                )
                self.assertEqual(
                    result["incumbent_score"], _score(counts, lexicon, key)
                )

    def test_capacity_one_matches_existing_injective_helper(self) -> None:
        counts = {
            ("x", "y"): 2,
            ("z",): 0,
        }
        lexicon = {("a", "b"), ("b", "a")}
        key = {"x": "a", "y": "b", "z": "c"}

        expected = preserved_injective(counts, lexicon, "abcd", key)
        result = preserved_hit_completions(
            counts, lexicon, "abcd", key, capacity=1
        )
        self.assertEqual(
            result["completion_count"], expected["keys_preserving_current_hits"]
        )
        self.assertEqual(
            result["covered_symbol_count"], expected["covered_symbol_count"]
        )
        self.assertEqual(result["incumbent_score"], expected["incumbent_score"])

    def test_empty_and_zero_weight_words_leave_all_units_free(self) -> None:
        result = preserved_hit_completions(
            {(): 3, ("x",): 0},
            {()},
            "abc",
            {"x": "a"},
            capacity=2,
        )
        self.assertEqual(result["incumbent_score"], 3)
        self.assertEqual(result["covered_symbol_count"], 0)
        self.assertEqual(result["free_cipher_symbol_count"], 1)
        self.assertEqual(result["completion_count"], 3)

    def test_invalid_inputs_are_rejected(self) -> None:
        valid_counts = {("x",): 1}
        valid_lexicon = {("a",)}
        for counts in (
            {("x",): -1},
            {("x",): True},
            {("x",): 1.0},
        ):
            with self.assertRaises((TypeError, ValueError)):
                preserved_hit_completions(
                    counts, valid_lexicon, "ab", {"x": "a"}, capacity=2
                )
        for capacity in (0, -1, True, 1.0, "2"):
            with self.assertRaises(ValueError):
                preserved_hit_completions(
                    valid_counts,
                    valid_lexicon,
                    "ab",
                    {"x": "a"},
                    capacity=capacity,
                )
        with self.assertRaises(ValueError):
            preserved_hit_completions(
                valid_counts, valid_lexicon, "aa", {"x": "a"}, capacity=2
            )
        with self.assertRaises(ValueError):
            preserved_hit_completions(
                valid_counts, valid_lexicon, "ab", {}, capacity=2
            )
        with self.assertRaises(ValueError):
            preserved_hit_completions(
                valid_counts,
                valid_lexicon,
                "ab",
                {"x": "a", "y": "b"},
                capacity=2,
            )
        with self.assertRaises(ValueError):
            preserved_hit_completions(
                valid_counts,
                valid_lexicon,
                "ab",
                {"x": "a", "x2": "a"},
                capacity=2,
            )


if __name__ == "__main__":
    unittest.main()
