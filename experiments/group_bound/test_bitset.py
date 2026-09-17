"""Synthetic differential tests for the bitset pivot-group bound."""

from __future__ import annotations

from collections import Counter
import itertools
from unittest import mock
import pathlib
import sys
import unittest


PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from experiments.group_bound.bitset import (  # noqa: E402
    BitsetCompatibilityError,
    BitsetConstructionError,
    BitsetPivotGroupBound,
)
from experiments.group_bound.pivot import PivotGroupBound  # noqa: E402
from experiments.homophonic import bitset_bound as frozen_bitset  # noqa: E402


Word = tuple[str, ...]


def _word(value: str | Word) -> Word:
    return tuple(value) if isinstance(value, str) else value


def _brute_completion_score(
    counts: dict[str | Word, int],
    lexicon: set[str | Word],
    alphabet: tuple[str, ...],
    capacity: int | None,
    partial: dict[str, str],
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
        if any(key[symbol] != value for symbol, value in partial.items()):
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


class BitsetPivotGroupBoundTests(unittest.TestCase):
    def _compare(
        self,
        counts: dict[str | Word, int],
        lexicon: set[str | Word],
        alphabet: tuple[str, ...],
        capacity: int | None,
        groups=None,
    ) -> tuple[PivotGroupBound, BitsetPivotGroupBound]:
        scalar = PivotGroupBound(
            counts,
            lexicon,
            alphabet,
            capacity=capacity,
            groups=groups,
        )
        bitset = BitsetPivotGroupBound(
            counts,
            lexicon,
            alphabet,
            capacity=capacity,
            groups=groups,
        )
        symbols = tuple(sorted({symbol for word in counts for symbol in _word(word)}))
        for partial in _partial_maps(symbols, alphabet, capacity):
            expected = scalar.bound(partial)
            actual = bitset.bound(partial)
            self.assertEqual(actual["status"], expected["status"], partial)
            self.assertEqual(actual["group_bound"], expected["group_bound"], partial)
            self.assertEqual(
                actual["independent_bound"], expected["independent_bound"], partial
            )
            if actual["group_bound"] is not None:
                self.assertGreaterEqual(
                    actual["group_bound"],
                    _brute_completion_score(
                        counts, lexicon, alphabet, capacity, partial
                    ),
                    partial,
                )
        return scalar, bitset

    def test_strict_fixture_matches_scalar_and_tightens(self) -> None:
        scalar, bitset = self._compare(
            {"x": 1, "xy": 1},
            {"a", "ba"},
            ("a", "b"),
            1,
        )
        self.assertEqual(scalar.bound()["group_bound"], 1)
        self.assertEqual(bitset.bound()["group_bound"], 1)
        self.assertEqual(bitset.bound()["independent_bound"], 2)
        self.assertFalse(bitset.bound()["claims_global_optimality"])

    def test_all_partial_maps_match_scalar_for_all_capacities(self) -> None:
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
        for capacity in (1, 2, None):
            self._compare(counts, lexicon, alphabet, capacity)

    def test_explicit_groups_residual_and_repeated_pivot(self) -> None:
        counts = {"x": 1, "xy": 2, "yz": 3, "z": 4, "zz": 0}
        lexicon = {"a", "ba", "ab", "bc", "c", "bb"}
        groups = [
            ("x", ["x", "xy"]),
            ("y", ["yz"]),
        ]
        scalar, bitset = self._compare(
            counts,
            lexicon,
            ("a", "b", "c"),
            1,
            groups,
        )
        self.assertEqual(bitset.groups, scalar.groups)
        self.assertEqual(bitset.bound()["ungrouped_words"], [["z"], ["z", "z"]])

        same_pivot_groups = [("x", ["x"]), ("x", ["xy"])]
        self._compare(
            {"x": 1, "xy": 1},
            {"a", "ba"},
            ("a", "b"),
            1,
            same_pivot_groups,
        )

    def test_duplicate_repeated_zero_empty_and_unicode_lanes(self) -> None:
        counts = {
            "xy": 2,
            ("x", "y"): 3,
            ("x", "x"): 0,
            (): 4,
            ("ꝑ", "ka"): 5,
        }
        lexicon = ["ab", "ab", "aa", "", ("a", "b")]
        scalar, bitset = self._compare(
            counts,
            set(lexicon),
            ("a", "b"),
            None,
            groups=[("ꝑ", [("ꝑ", "ka")])],
        )
        self.assertEqual(bitset.metadata["candidate_count_total"], scalar.metadata["candidate_count_total"])
        self.assertEqual(bitset.bound()["group_bound"], scalar.bound()["group_bound"])
        self.assertFalse(hasattr(bitset, "_candidate_cache"))

    def test_capacity_infeasibility_has_no_numeric_bound(self) -> None:
        scalar, bitset = self._compare(
            {"x": 1, "y": 1, "z": 1},
            {"a", "b", "c"},
            ("a", "b"),
            1,
        )
        self.assertEqual(scalar.bound()["status"], "infeasible_capacity")
        self.assertEqual(bitset.bound()["status"], "infeasible_capacity")
        self.assertIsNone(bitset.bound()["group_bound"])
        self.assertIsNone(bitset.bound()["independent_bound"])

    def test_declared_row_and_storage_limits_return_no_bound(self) -> None:
        with self.assertRaises(BitsetConstructionError):
            BitsetPivotGroupBound(
                {"x": 1, "xy": 1},
                {"a", "ba"},
                "ab",
                capacity=1,
                max_candidate_rows=1,
            )
        with self.assertRaises(BitsetConstructionError):
            BitsetPivotGroupBound(
                {"x": 1},
                {"a"},
                "ab",
                capacity=1,
                max_estimated_storage_bytes=0,
            )

    def test_private_layout_mismatch_fails_closed(self) -> None:
        original = frozen_bitset.BitsetBound

        class BrokenBitsetBound(original):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                del self._weight_bit_masks

        with mock.patch.object(frozen_bitset, "BitsetBound", BrokenBitsetBound):
            with self.assertRaises(BitsetCompatibilityError):
                BitsetPivotGroupBound(
                    {"x": 1},
                    {"a"},
                    "ab",
                    capacity=1,
                )


if __name__ == "__main__":
    unittest.main()
