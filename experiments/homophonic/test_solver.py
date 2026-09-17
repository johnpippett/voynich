"""Behavioral tests for the bounded homophonic lexicon solver."""

from __future__ import annotations

from collections import Counter
import itertools
import pathlib
import random
import sys
import unittest


PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from experiments.homophonic.solver import (
    _candidate_compatible,
    solve_lexicon,
)
from experiments.lexicon.solver import solve_lexicon as solve_injective


Word = tuple[str, ...]


def _brute_best(
    ciphertext_counts: dict[Word, int],
    plaintext_lexicon: set[Word],
    plaintext_alphabet: tuple[str, ...],
    capacity: int | None,
) -> tuple[int, dict[str, str]]:
    symbols = tuple(sorted({symbol for word in ciphertext_counts for symbol in word}))
    best_score = -1
    best_key: dict[str, str] = {}
    best_tie: tuple[str, ...] | None = None
    for values in itertools.product(plaintext_alphabet, repeat=len(symbols)):
        if capacity is not None and any(
            count > capacity for count in Counter(values).values()
        ):
            continue
        key = dict(zip(symbols, values, strict=True))
        score = sum(
            weight
            for word, weight in ciphertext_counts.items()
            if tuple(key[symbol] for symbol in word) in plaintext_lexicon
        )
        tie = tuple(key[symbol] for symbol in symbols)
        if score > best_score or (score == best_score and (best_tie is None or tie < best_tie)):
            best_score = score
            best_key = key
            best_tie = tie
    return best_score, best_key


class HomophonicSolverTests(unittest.TestCase):
    def test_bitset_search_matches_scalar_bounds_keys_and_budgets(self) -> None:
        rng = random.Random(9301)
        for capacity in (1, 2, None):
            for case in range(12):
                counts = {''.join(rng.choices('xyz', k=rng.randrange(1, 5))):
                          rng.randrange(0, 8) for _ in range(8)}
                lexicon = {''.join(rng.choices('abc', k=rng.randrange(1, 5)))
                           for _ in range(12)}
                for budget in (0, 1, 5, None):
                    reference = solve_lexicon(counts, lexicon, 'abc',
                                              capacity=capacity, node_budget=budget)
                    actual = solve_lexicon(counts, lexicon, 'abc',
                                           capacity=capacity, node_budget=budget,
                                           bound_engine='bitset')
                    for name in ('key', 'score', 'lower_bound', 'upper_bound', 'nodes',
                                 'score_certified', 'search_exhausted', 'status'):
                        self.assertEqual(actual[name], reference[name],
                                         (capacity, case, budget, name))

    def test_candidate_metadata_counts_only_root_compatible_entries(self) -> None:
        for counts, lexicon, capacity in (
            ({"xx": 2}, {"ab"}, 1),
            ({"xy": 2}, {"aa"}, 1),
            ({"xyz": 2}, {"aaa"}, 2),
        ):
            result = solve_lexicon(counts, lexicon, "abc", capacity=capacity)
            self.assertEqual(result["candidate_count_total"], 0)
            self.assertEqual(result["candidate_type_count"], 0)
            self.assertEqual(result["missing_candidate_count"], 1)
            self.assertEqual(result["status"], "no_candidates")
            self.assertTrue(result["score_certified"])

    def test_capacity_one_matches_injective_solver_on_tiny_cases(self) -> None:
        cases = (
            (
                {("x", "y"): 3, ("y", "x"): 1, ("x", "x"): 2},
                {("a", "b"), ("b", "a"), ("a", "a")},
                ("a", "b", "c"),
            ),
            (
                {("x", "x"): 5, ("z",): 7},
                {("a", "a"), ("b",)},
                ("a", "b", "c"),
            ),
        )
        for counts, lexicon, alphabet in cases:
            for budget in (0, 1, 2, 5, None):
                expected = solve_injective(
                    counts,
                    lexicon,
                    alphabet,
                    node_budget=budget,
                )
                result = solve_lexicon(
                    counts,
                    lexicon,
                    alphabet,
                    capacity=1,
                    node_budget=budget,
                )
                self.assertEqual(result["lower_bound"], expected["lower_bound"])
                self.assertEqual(result["upper_bound"], expected["upper_bound"])
                self.assertEqual(result["score"], expected["score"])

    def test_capacities_match_direct_products_at_every_budget(self) -> None:
        counts = {
            ("x", "y"): 7,
            ("y", "x"): 5,
            ("x", "x"): 3,
            ("z",): 11,
        }
        lexicon = {
            ("a", "a"),
            ("a", "b"),
            ("b", "a"),
            ("b", "b"),
            ("c",),
        }
        alphabet = ("a", "b", "c")
        for capacity in (1, 2, None):
            expected, _key = _brute_best(counts, lexicon, alphabet, capacity)
            for budget in (0, 1, 2, 5, 20, None):
                result = solve_lexicon(
                    counts,
                    lexicon,
                    alphabet,
                    capacity=capacity,
                    node_budget=budget,
                )
                self.assertLessEqual(result["lower_bound"], expected)
                self.assertGreaterEqual(result["upper_bound"], expected)
                if result["score_certified"]:
                    self.assertEqual(result["lower_bound"], expected)
                    self.assertEqual(result["upper_bound"], expected)

    def test_partial_key_candidate_overlap_obeys_capacity(self) -> None:
        partial = {"x": "a"}
        self.assertFalse(_candidate_compatible(("y",), ("a",), partial, 1))
        self.assertTrue(_candidate_compatible(("y",), ("a",), partial, 2))
        self.assertFalse(
            _candidate_compatible(("x", "y"), ("a", "a"), partial, 1)
        )
        self.assertTrue(
            _candidate_compatible(("x", "y"), ("a", "a"), partial, 2)
        )
        self.assertTrue(
            _candidate_compatible(("x", "y"), ("a", "a"), partial, None)
        )

    def test_initial_key_is_warm_start_and_does_not_restrict_root(self) -> None:
        counts = {("x", "y"): 1}
        lexicon = {("b", "a")}
        for capacity in (1, 2, None):
            for initial_key in ({"x": "a"}, {"x": "a", "y": "b"}):
                result = solve_lexicon(
                    counts,
                    lexicon,
                    ("a", "b"),
                    capacity=capacity,
                    initial_key=initial_key,
                    node_budget=0,
                )
                self.assertEqual(result["status"], "budget_exhausted")
                self.assertEqual(result["lower_bound"], 0)
                self.assertGreaterEqual(result["upper_bound"], 1)

                exhaustive = solve_lexicon(
                    counts,
                    lexicon,
                    ("a", "b"),
                    capacity=capacity,
                    initial_key=initial_key,
                )
                self.assertEqual(exhaustive["score"], 1)
                self.assertTrue(exhaustive["score_certified"])

    def test_repeated_units_can_map_to_one_letter(self) -> None:
        counts = {("x", "x"): 4, ("x", "y"): 3}
        lexicon = {("a", "a"), ("a", "a")}
        for capacity in (1, 2, None):
            result = solve_lexicon(
                counts,
                lexicon,
                ("a", "b"),
                capacity=capacity,
            )
            expected = 4 if capacity == 1 else 7
            self.assertEqual(result["score"], expected)

    def test_tuple_units_and_unlimited_capacity(self) -> None:
        counts = {
            ("ka", "ke"): 3,
            ("ke", "ka"): 2,
        }
        lexicon = {("a", "a"), ("a", "b"), ("b", "a")}
        result = solve_lexicon(
            counts,
            lexicon,
            ("a", "b"),
            capacity=None,
        )
        self.assertEqual(result["score"], 5)
        self.assertEqual(result["upper_bound"], 5)

    def test_duplicates_zero_weights_and_out_of_alphabet_entries(self) -> None:
        result = solve_lexicon(
            {"xy": 2, ("x", "y"): 3, "xx": 0},
            ["ab", "ab", "zz"],
            "ab",
            capacity=1,
        )
        self.assertEqual(result["total_weight"], 5)
        self.assertEqual(result["lexicon_raw_entry_count"], 3)
        self.assertEqual(result["lexicon_unique_normalized_count"], 2)
        self.assertEqual(result["lexicon_usable_count"], 1)
        self.assertEqual(result["lexicon_rejected_out_of_alphabet_count"], 1)
        self.assertEqual(result["score"], 5)

    def test_empty_input_no_candidates_and_zero_weights(self) -> None:
        empty = solve_lexicon({}, {"a"}, "ab", capacity=1)
        self.assertEqual(empty["status"], "empty_input")
        self.assertEqual(empty["lower_bound"], 0)
        self.assertEqual(empty["upper_bound"], 0)
        self.assertTrue(empty["score_certified"])
        self.assertTrue(empty["search_exhausted"])

        no_candidates = solve_lexicon(
            {"xx": 2}, {"a"}, "ab", capacity=1
        )
        self.assertEqual(no_candidates["status"], "no_candidates")
        self.assertEqual(no_candidates["lower_bound"], 0)
        self.assertEqual(no_candidates["upper_bound"], 0)
        self.assertTrue(no_candidates["score_certified"])
        self.assertFalse(no_candidates["search_exhausted"])

        zero = solve_lexicon(
            {"x": 0}, {"a"}, "ab", capacity=1, node_budget=0
        )
        self.assertEqual(zero["status"], "bound_certified")
        self.assertEqual(zero["lower_bound"], 0)
        self.assertEqual(zero["upper_bound"], 0)
        self.assertTrue(zero["score_certified"])
        self.assertFalse(zero["search_exhausted"])

    def test_capacity_infeasibility_has_none_bounds(self) -> None:
        result = solve_lexicon(
            {"xyz": 1}, {"abc"}, "ab", capacity=1
        )
        self.assertEqual(result["status"], "infeasible_capacity")
        self.assertFalse(result["feasible"])
        self.assertEqual(result["infeasibility_reason"], "capacity")
        self.assertIsNone(result["lower_bound"])
        self.assertIsNone(result["upper_bound"])
        self.assertIsNone(result["score"])
        self.assertTrue(result["search_exhausted"])
        self.assertFalse(result["score_certified"])

        feasible_with_capacity_two = solve_lexicon(
            {"xyz": 1}, {"abc"}, "ab", capacity=2
        )
        self.assertTrue(feasible_with_capacity_two["feasible"])
        self.assertNotEqual(feasible_with_capacity_two["status"], "infeasible_capacity")

    def test_tie_breaking_is_deterministic(self) -> None:
        args = ({"xy": 1}, {"ab", "ba"}, "ab")
        first = solve_lexicon(*args, capacity=2)
        second = solve_lexicon(*args, capacity=2)
        self.assertEqual(first, second)
        self.assertEqual(first["key"], {"x": "a", "y": "b"})
        self.assertNotIn("all_keys_enumerated", first)

    def test_invalid_capacity_keys_and_symbol_order_are_rejected(self) -> None:
        for capacity in (0, -1, True, 1.0, "2"):
            with self.assertRaises(ValueError):
                solve_lexicon({"x": 1}, {"a"}, "ab", capacity=capacity)

        with self.assertRaises(ValueError):
            solve_lexicon(
                {"x": 1}, {"a"}, "ab", capacity=1, initial_key={"x": "a", "y": "b"}
            )
        with self.assertRaises(ValueError):
            solve_lexicon(
                {"x": 1}, {"a"}, "ab", capacity=1, initial_key={"x": "a", "x2": "a"}
            )
        with self.assertRaises(ValueError):
            solve_lexicon(
                {"xy": 1}, {"ab"}, "ab", capacity=1, symbol_order=("x",)
            )
        with self.assertRaises(ValueError):
            solve_lexicon({"x": -1}, {"a"}, "ab", capacity=1)
        with self.assertRaises(ValueError):
            solve_lexicon({"x": True}, {"a"}, "ab", capacity=1)
        with self.assertRaises(ValueError):
            solve_lexicon({"x": 1}, {"a"}, "aa", capacity=1)

    def test_random_tiny_cases_match_direct_products(self) -> None:
        rng = random.Random(20260916)
        for alphabet_size in range(1, 4):
            alphabet = tuple("abc"[:alphabet_size])
            for _case in range(24):
                cipher_count = rng.randint(0, alphabet_size)
                cipher_symbols = tuple("wxyz"[:cipher_count])
                counts: dict[Word, int] = {}
                for _word_index in range(rng.randint(0, 5)):
                    length = rng.randint(0, 3) if cipher_symbols else 0
                    word = tuple(rng.choice(cipher_symbols) for _ in range(length))
                    counts[word] = rng.randint(0, 8)
                lexicon = {
                    tuple(rng.choice(alphabet) for _ in range(rng.randint(0, 3)))
                    for _ in range(rng.randint(0, 8))
                }
                for capacity in (1, 2, None):
                    expected, _key = _brute_best(
                        counts, lexicon, alphabet, capacity
                    )
                    for budget in (0, 1, 3, None):
                        result = solve_lexicon(
                            counts,
                            lexicon,
                            alphabet,
                            capacity=capacity,
                            node_budget=budget,
                        )
                        self.assertLessEqual(result["lower_bound"], expected)
                        self.assertGreaterEqual(result["upper_bound"], expected)
                        if result["score_certified"]:
                            self.assertEqual(result["score"], expected)

    def test_random_warm_starts_and_symbol_orders_match_direct_products(self) -> None:
        rng = random.Random(20260917)
        for alphabet_size in range(1, 4):
            alphabet = tuple("abc"[:alphabet_size])
            for _case in range(12):
                cipher_symbols = tuple("wxyz"[: rng.randint(0, alphabet_size)])
                counts: dict[Word, int] = {}
                for _word_index in range(rng.randint(0, 4)):
                    length = rng.randint(0, 3) if cipher_symbols else 0
                    word = tuple(rng.choice(cipher_symbols) for _ in range(length))
                    counts[word] = rng.randint(0, 6)
                lexicon = {
                    tuple(rng.choice(alphabet) for _ in range(rng.randint(0, 3)))
                    for _ in range(rng.randint(0, 6))
                }
                symbols = tuple(sorted({s for word in counts for s in word}))
                order = list(symbols)
                rng.shuffle(order)
                for capacity in (1, 2, None):
                    initial: dict[str, str] = {}
                    usage: Counter[str] = Counter()
                    for cipher_symbol in rng.sample(
                        symbols, rng.randint(0, len(symbols))
                    ):
                        plain_symbol = rng.choice(alphabet)
                        if capacity is not None and usage[plain_symbol] >= capacity:
                            continue
                        initial[cipher_symbol] = plain_symbol
                        usage[plain_symbol] += 1
                    expected, _key = _brute_best(
                        counts, lexicon, alphabet, capacity
                    )
                    for budget in (0, 2, None):
                        result = solve_lexicon(
                            counts,
                            lexicon,
                            alphabet,
                            capacity=capacity,
                            initial_key=initial,
                            symbol_order=order,
                            node_budget=budget,
                        )
                        self.assertLessEqual(result["lower_bound"], expected)
                        self.assertGreaterEqual(result["upper_bound"], expected)
                        if result["score_certified"]:
                            self.assertEqual(result["score"], expected)


if __name__ == "__main__":
    unittest.main()
