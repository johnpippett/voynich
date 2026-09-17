"""Tests for the broadword finite-lexicon candidate bound."""

from __future__ import annotations

import itertools
import pathlib
import random
import sys
import unittest


PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from experiments.lexicon.bitset_bound import BitsetBound
from experiments.lexicon.solver import _candidate_lists, _upper_bound


Word = tuple[str, ...]


def _partial_keys(
    cipher_symbols: tuple[str, ...],
    plaintext_alphabet: tuple[str, ...],
):
    yield {}
    for width in range(1, min(len(cipher_symbols), len(plaintext_alphabet)) + 1):
        for cipher_values in itertools.permutations(cipher_symbols, width):
            for plain_values in itertools.permutations(plaintext_alphabet, width):
                yield dict(zip(cipher_values, plain_values, strict=True))


def _assert_matches_reference(
    testcase: unittest.TestCase,
    counts: dict[Word, int],
    candidates: dict[Word, tuple[Word, ...]],
    alphabet: tuple[str, ...],
) -> None:
    engine = BitsetBound(counts, candidates, alphabet)
    symbols = tuple(sorted({symbol for word in counts for symbol in word}))
    for partial_key in _partial_keys(symbols, alphabet):
        expected = _upper_bound(partial_key, counts, candidates)
        testcase.assertEqual(
            engine.bound(partial_key),
            expected,
            msg=f"partial_key={partial_key!r}",
        )


class BitsetBoundTests(unittest.TestCase):
    def test_exhaustive_small_assignments_match_solver_bound(self) -> None:
        counts = {
            ("x", "y"): 3,
            ("y", "x"): 5,
            ("x", "x"): 7,
            ("z",): 11,
        }
        candidates = {
            ("x", "y"): (("a", "b"), ("b", "a")),
            ("y", "x"): (("a", "b"), ("b", "a")),
            ("x", "x"): (("a", "a"), ("b", "b")),
            ("z",): (("c",),),
        }

        _assert_matches_reference(self, counts, candidates, ("a", "b", "c"))

    def test_empty_word_and_empty_candidate_lanes(self) -> None:
        counts = {
            (): 13,
            ("x",): 17,
            ("y", "y"): 19,
        }
        candidates = {
            (): ((),),
            ("x",): (("a",),),
            ("y", "y"): (),
        }
        engine = BitsetBound(counts, candidates, ("a", "b", "c"))

        self.assertEqual(engine.bound({}), 30)
        self.assertEqual(engine.bound({"x": "a"}), 30)
        self.assertEqual(engine.bound({"x": "b"}), 13)
        self.assertEqual(engine.bound({"y": "a"}), 13)
        self.assertEqual(engine.metadata["candidate_count"], 2)
        _assert_matches_reference(self, counts, candidates, ("a", "b", "c"))

    def test_no_candidates_have_no_sentinel_hits(self) -> None:
        counts = {
            (): 2**12,
            ("x",): 2**13,
            ("x", "x"): 2**14,
        }
        candidates = {word: () for word in counts}
        engine = BitsetBound(counts, candidates, ("a", "b"))

        self.assertEqual(engine.bound({}), 0)
        self.assertEqual(engine.bound({"x": "a"}), 0)
        self.assertEqual(engine.root_bound, 0)
        self.assertEqual(engine.metadata["candidate_count"], 0)
        self.assertEqual(engine.metadata["sentinel_count"], 3)

    def test_zero_weights_do_not_create_weight_bits(self) -> None:
        counts = {("x",): 0, ("y",): 0}
        candidates = {
            ("x",): (("a",),),
            ("y",): (("b",),),
        }
        engine = BitsetBound(counts, candidates, ("a", "b", "c"))

        self.assertEqual(engine.bound({}), 0)
        self.assertEqual(engine.metadata["weight_bit_count"], 0)
        _assert_matches_reference(self, counts, candidates, ("a", "b", "c"))

    def test_repeated_cipher_symbols_and_absent_plaintext_letter(self) -> None:
        counts = {
            ("x", "x"): 23,
            ("x", "y"): 29,
            ("y", "x"): 31,
        }
        candidates = {
            ("x", "x"): (("a", "a"), ("b", "b")),
            ("x", "y"): (("a", "b"), ("b", "a")),
            ("y", "x"): (("a", "b"), ("b", "a")),
        }
        engine = BitsetBound(counts, candidates, ("a", "b", "c"))

        self.assertEqual(engine.bound({"x": "c"}), 0)
        self.assertEqual(engine.bound({"x": "a"}), 23 + 29 + 31)
        self.assertEqual(engine.bound({"x": "a", "y": "b"}), 23 + 29 + 31)
        _assert_matches_reference(self, counts, candidates, ("a", "b", "c"))

    def test_tuple_symbols_and_large_weight_bits(self) -> None:
        counts = {
            ("ka", "kb"): (1 << 100_000) + 3,
            ("kb", "ka"): (1 << 7) + 5,
        }
        candidates = {
            ("ka", "kb"): (("a", "b"), ("b", "a")),
            ("kb", "ka"): (("a", "b"), ("b", "a")),
        }
        engine = BitsetBound(counts, candidates, ("a", "b", "c"))
        self.assertEqual(engine.metadata["weight_bit_count"], 5)
        _assert_matches_reference(self, counts, candidates, ("a", "b", "c"))

    def test_duplicate_candidate_bits_do_not_change_lane_hit(self) -> None:
        counts = {("x",): 37}
        candidates = {("x",): (("a",), ("a",), ("b",))}
        engine = BitsetBound(counts, candidates, ("a", "b"))

        self.assertEqual(engine.bound({}), 37)
        self.assertEqual(engine.bound({"x": "a"}), 37)
        self.assertEqual(engine.bound({"x": "b"}), 37)
        self.assertEqual(engine.metadata["candidate_count"], 3)

    def test_empty_input_and_root_metadata(self) -> None:
        engine = BitsetBound({}, {}, ("a", "b"))

        self.assertEqual(engine.bound(), 0)
        self.assertEqual(engine.root_bound, 0)
        self.assertEqual(
            engine.metadata,
            {
                "lane_count": 0,
                "candidate_count": 0,
                "slot_count": 0,
                "sentinel_count": 0,
                "weight_bit_count": 0,
            },
        )
        self.assertNotIn("_active", vars(engine))

    def test_random_exhaustive_partial_keys(self) -> None:
        rng = random.Random(20260916)
        for alphabet_size in range(1, 5):
            alphabet = tuple("abcd"[:alphabet_size])
            for _case in range(20):
                cipher_symbol_count = rng.randint(0, alphabet_size)
                cipher_symbols = tuple("wxyz"[:cipher_symbol_count])
                counts: dict[Word, int] = {}
                for _word_index in range(rng.randint(0, 6)):
                    word_length = rng.randint(0, 3)
                    if not cipher_symbols:
                        word_length = 0
                    word = tuple(
                        rng.choice(cipher_symbols)
                        for _ in range(word_length)
                    )
                    counts[word] = rng.randint(0, 15)
                lexicon = {
                    tuple(
                        rng.choice(alphabet)
                        for _ in range(rng.randint(0, 3))
                    )
                    for _ in range(rng.randint(0, 10))
                }
                candidates = _candidate_lists(counts, lexicon)
                _assert_matches_reference(self, counts, candidates, alphabet)

    def test_rejects_invalid_candidate_and_partial_key_inputs(self) -> None:
        counts = {("x",): 1}
        with self.assertRaises(ValueError):
            BitsetBound(counts, {})
        with self.assertRaises(ValueError):
            BitsetBound(counts, {("x",): (("a", "b"),)})
        duplicate = BitsetBound(
            counts,
            {("x",): (("a",), ("a",))},
            ("a",),
        )
        self.assertEqual(duplicate.bound({}), 1)
        with self.assertRaises(ValueError):
            BitsetBound(counts, {("x",): (("a",), ("b",))}, ("a",))

        engine = BitsetBound(
            counts,
            {("x",): (("a",), ("b",))},
            ("a", "b"),
        )
        with self.assertRaises(TypeError):
            engine.bound(("x", "a"))  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            engine.bound({"z": "a"})
        with self.assertRaises(ValueError):
            engine.bound({"x": "z"})
        with self.assertRaises(ValueError):
            engine.bound({"x": "a", "z": "a"})

        two_engine = BitsetBound(
            {("x",): 1, ("y",): 1},
            {("x",): (("a",),), ("y",): (("b",),)},
            ("a", "b"),
        )
        with self.assertRaises(ValueError):
            two_engine.bound({"x": "a", "y": "a"})


if __name__ == "__main__":
    unittest.main()
