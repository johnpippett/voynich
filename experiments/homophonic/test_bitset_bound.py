"""Behavioral tests for the homophonic bitset upper bound."""

from __future__ import annotations

from collections import Counter
import itertools
import pathlib
import random
import sys
import unittest


PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from experiments.homophonic.bitset_bound import BitsetBound
from experiments.homophonic.solver import _upper_bound


Word = tuple[str, ...]


def _partial_maps(
    cipher_symbols: tuple[str, ...],
    alphabet: tuple[str, ...],
    capacity: int | None,
):
    for width in range(len(cipher_symbols) + 1):
        for selected in itertools.combinations(cipher_symbols, width):
            for values in itertools.product(alphabet, repeat=width):
                if capacity is not None and any(
                    count > capacity for count in Counter(values).values()
                ):
                    continue
                yield dict(zip(selected, values, strict=True))


class HomophonicBitsetBoundTests(unittest.TestCase):
    def _assert_matches_scalar(
        self,
        counts: dict[Word, int],
        candidates: dict[Word, tuple[Word, ...]],
        alphabet: tuple[str, ...],
        capacity: int | None,
    ) -> None:
        engine = BitsetBound(counts, candidates, alphabet, capacity)
        symbols = tuple(sorted({symbol for word in counts for symbol in word}))
        for partial_key in _partial_maps(symbols, alphabet, capacity):
            expected = _upper_bound(partial_key, counts, candidates, capacity)
            self.assertEqual(
                engine.bound(partial_key),
                expected,
                msg=f"capacity={capacity!r}, partial_key={partial_key!r}",
            )

    def test_all_partial_and_complete_maps_match_scalar_for_each_capacity(self) -> None:
        counts = {
            (): 13,
            ("x",): 17,
            ("x", "x"): 19,
            ("x", "y"): 23,
            ("y", "x"): 29,
            ("z",): 0,
        }
        candidates = {
            (): ((),),
            ("x",): (("a",), ("b",), ("c",)),
            ("x", "x"): (("a", "a"), ("b", "b"), ("a", "b")),
            ("x", "y"): (
                ("a", "a"),
                ("a", "b"),
                ("b", "a"),
                ("b", "c"),
            ),
            ("y", "x"): (
                ("a", "a"),
                ("a", "b"),
                ("b", "a"),
            ),
            ("z",): (),
        }
        alphabet = ("a", "b", "c")

        for capacity in (1, 2, None):
            self._assert_matches_scalar(counts, candidates, alphabet, capacity)

    def test_capacity_two_union_rules_cover_overlap_and_two_assigned_units(self) -> None:
        counts = {
            ("x", "y"): 1,
            ("x", "z"): 1,
        }
        candidates = {
            ("x", "y"): (
                ("a", "a"),
                ("a", "b"),
                ("b", "a"),
                ("b", "b"),
            ),
            ("x", "z"): (
                ("a", "a"),
                ("a", "b"),
                ("b", "a"),
                ("b", "b"),
            ),
        }
        engine = BitsetBound(counts, candidates, ("a", "b"), 2)

        self.assertEqual(engine.bound({"x": "a"}), 2)
        self.assertEqual(engine.bound({"x": "a", "y": "a"}), 2)
        self.assertEqual(engine.bound({"x": "a", "y": "b"}), 2)
        with self.assertRaises(ValueError):
            engine.bound({"x": "a", "y": "a", "z": "a"})
        self._assert_matches_scalar(counts, candidates, ("a", "b"), 2)

    def test_root_filters_inconsistent_and_over_capacity_candidates(self) -> None:
        counts = {
            ("x", "x"): 5,
            ("x", "y"): 7,
            (): 11,
        }
        candidates = {
            ("x", "x"): (("a", "b"), ("a", "a"), ("a", "a")),
            ("x", "y"): (("a", "a"), ("a", "b")),
            (): ((),),
        }

        cap1 = BitsetBound(counts, candidates, ("a", "b"), 1)
        cap2 = BitsetBound(counts, candidates, ("a", "b"), 2)
        self.assertEqual(cap1.metadata["candidate_count"], 4)
        self.assertEqual(cap1.metadata["distinct_candidate_count"], 3)
        self.assertEqual(cap2.metadata["candidate_count"], 5)
        self.assertEqual(cap2.metadata["distinct_candidate_count"], 4)
        self.assertEqual(cap1.root_bound, 23)
        self.assertEqual(cap2.root_bound, 23)
        self._assert_matches_scalar(counts, candidates, ("a", "b"), 1)
        self._assert_matches_scalar(counts, candidates, ("a", "b"), 2)

    def test_empty_lanes_zero_weights_and_empty_input(self) -> None:
        counts = {(): 13, ("x",): 0, ("y", "y"): 19}
        candidates = {(): ((),), ("x",): (("a",),), ("y", "y"): ()}

        for capacity in (1, 2, None):
            engine = BitsetBound(counts, candidates, ("a", "b"), capacity)
            self.assertEqual(engine.bound({}), 13)
            self._assert_matches_scalar(counts, candidates, ("a", "b"), capacity)

        empty = BitsetBound({}, {}, ("a", "b"), 1)
        self.assertEqual(empty.bound(), 0)
        self.assertEqual(empty.root_bound, 0)
        self.assertEqual(empty.metadata["lane_count"], 0)

    def test_tuple_units_duplicates_and_large_integer_weights(self) -> None:
        counts = {
            ("ka", "kb"): (1 << 100) + 3,
            ("kb", "ka"): (1 << 7) + 5,
        }
        candidates = {
            ("ka", "kb"): (("a", "b"), ("a", "b"), ("b", "a")),
            ("kb", "ka"): (("a", "b"), ("b", "a")),
        }
        for capacity in (1, 2, None):
            self._assert_matches_scalar(
                counts,
                candidates,
                ("a", "b", "c"),
                capacity,
            )

    def test_random_partial_maps_match_scalar(self) -> None:
        rng = random.Random(20260916)
        for alphabet_size in range(1, 4):
            alphabet = tuple("abc"[:alphabet_size])
            for _case in range(20):
                symbol_count = rng.randint(0, min(3, alphabet_size + 1))
                symbols = tuple("wxyz"[:symbol_count])
                counts: dict[Word, int] = {}
                for _word_index in range(rng.randint(0, 5)):
                    word = tuple(
                        rng.choice(symbols) for _ in range(rng.randint(0, 3))
                    ) if symbols else ()
                    counts[word] = rng.randint(0, 12)
                candidates: dict[Word, tuple[Word, ...]] = {}
                for word in counts:
                    values = tuple(
                        tuple(
                            rng.choice(alphabet)
                            for _ in range(len(word))
                        )
                        for _candidate_index in range(rng.randint(0, 5))
                    )
                    candidates[word] = values
                for capacity in (1, 2, None):
                    self._assert_matches_scalar(
                        counts, candidates, alphabet, capacity
                    )

    def test_many_candidate_lanes_use_a_small_fixed_cipher_alphabet(self) -> None:
        cipher_alphabet = tuple(f"u{index}" for index in range(26))
        plaintext_alphabet = tuple("abcdefghijklmnopqrstuvwxyz")
        counts: dict[Word, int] = {}
        candidates: dict[Word, tuple[Word, ...]] = {}
        for lane_index, cipher_word in enumerate(
            itertools.islice(itertools.permutations(cipher_alphabet, 3), 80)
        ):
            rows = tuple(
                (
                    plaintext_alphabet[candidate_index % 26],
                    plaintext_alphabet[(candidate_index + 1) % 26],
                    plaintext_alphabet[(candidate_index + 2) % 26],
                )
                for candidate_index in range(40)
            )
            counts[cipher_word] = (lane_index % 7) + 1
            candidates[cipher_word] = rows

        engine = BitsetBound(
            counts,
            candidates,
            plaintext_alphabet,
            capacity=2,
        )
        self.assertEqual(engine.metadata["lane_count"], 80)
        self.assertEqual(engine.metadata["candidate_count"], 80 * 40)
        self.assertEqual(engine.metadata["slot_count"], 80 * 41)
        self.assertGreater(engine.metadata["mask_count"], 0)
        self.assertGreater(engine.metadata["estimated_storage_bytes"], 0)
        self.assertEqual(engine.root_bound, sum(counts.values()))

    def test_invalid_capacity_and_partial_keys_are_rejected(self) -> None:
        counts = {("x",): 1}
        candidates = {("x",): (("a",),)}
        for capacity in (0, -1, 3, True, 1.0, "2"):
            with self.assertRaises(ValueError):
                BitsetBound(counts, candidates, ("a", "b"), capacity)

        engine = BitsetBound(counts, candidates, ("a", "b"), 1)
        with self.assertRaises(TypeError):
            engine.bound(("x", "a"))  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            engine.bound({"z": "a"})
        with self.assertRaises(ValueError):
            engine.bound({"x": "z"})
        with self.assertRaises(ValueError):
            engine.bound({"x": "a", "y": "a"})


if __name__ == "__main__":
    unittest.main()
