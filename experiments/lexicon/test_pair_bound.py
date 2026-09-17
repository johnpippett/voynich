"""Synthetic tests for the pair-conflict lexicon upper bound."""

from __future__ import annotations

import itertools
import random
import unittest

from experiments.lexicon.pair_bound import pair_conflict_upper_bound


def _tuple_word(word: str | tuple[str, ...]) -> tuple[str, ...]:
    return tuple(word) if isinstance(word, str) else word


def _brute_maximum(
    ciphertext_counts: dict[str | tuple[str, ...], int],
    lexicon: set[str | tuple[str, ...]],
    alphabet: str,
) -> int:
    counts: dict[tuple[str, ...], int] = {}
    for word, weight in ciphertext_counts.items():
        key = _tuple_word(word)
        counts[key] = counts.get(key, 0) + weight
    plain_words = {_tuple_word(word) for word in lexicon}
    symbols = sorted({symbol for word in counts for symbol in word})
    best = 0
    for values in itertools.permutations(alphabet, len(symbols)):
        key = dict(zip(symbols, values))
        score = sum(
            weight
            for word, weight in counts.items()
            if tuple(key[symbol] for symbol in word) in plain_words
        )
        best = max(best, score)
    return best


def _clique_words(result: dict) -> list[tuple[tuple[str, ...], ...]]:
    return [
        tuple(tuple(word) for word in clique["types"])
        for clique in result["cliques"]
    ]


class PairConflictBoundTests(unittest.TestCase):
    def test_positive_no_conflict_bound_is_total_possible_weight(self) -> None:
        result = pair_conflict_upper_bound(
            {"x": 2, "y": 3},
            {"a", "b"},
            "abc",
            top_k=None,
        )

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["upper_bound"], 5)
        self.assertEqual(result["clique_bound"], 5)
        self.assertEqual(result["omitted_weight"], 0)
        self.assertEqual(len(result["cliques"]), 2)
        self.assertEqual(result["conflict_pair_count"], 0)

    def test_three_way_conflict_clique_keeps_only_maximum_weight(self) -> None:
        result = pair_conflict_upper_bound(
            {"xy": 1, "uv": 5, "uz": 3},
            {"ab", "c"},
            "abcde",
            top_k=None,
        )

        self.assertEqual(result["upper_bound"], 5)
        self.assertEqual(result["clique_bound"], 5)
        self.assertEqual(result["conflict_pair_count"], 3)
        self.assertEqual(len(result["cliques"]), 1)
        self.assertEqual(
            set(_clique_words(result)[0]),
            {("x", "y"), ("u", "v"), ("u", "z")},
        )
        self.assertEqual(result["cliques"][0]["max_weight"], 5)

    def test_triangle_free_conflicts_make_a_valid_greedy_partition(self) -> None:
        # xy and uv conflict through the one candidate ``ab``.  uv and u
        # conflict on the shared symbol.  xy and u can coexist.
        result = pair_conflict_upper_bound(
            {"xy": 1, "uv": 2, "u": 4},
            {"ab", "c"},
            "abcde",
            top_k=None,
        )

        self.assertEqual(result["conflict_pair_count"], 2)
        self.assertEqual(result["upper_bound"], 5)
        self.assertEqual(result["clique_bound"], 5)
        self.assertEqual(sum(clique["bound"] for clique in result["cliques"]), 5)
        for clique in result["cliques"]:
            self.assertGreaterEqual(len(clique["types"]), 1)

    def test_missing_candidates_contribute_zero(self) -> None:
        result = pair_conflict_upper_bound(
            {"x": 5, "yy": 7},
            {"a"},
            "abc",
            top_k=None,
        )

        self.assertEqual(result["upper_bound"], 5)
        self.assertEqual(result["missing_candidate_count"], 1)
        self.assertEqual(result["missing_candidate_weight"], 7)
        self.assertEqual(result["candidate_type_count"], 1)

    def test_differing_lengths_use_separate_pattern_candidates(self) -> None:
        result = pair_conflict_upper_bound(
            {"x": 2, "yy": 3},
            {"a", "bb"},
            "abc",
            top_k=None,
        )

        rows = {tuple(row["cipher_word"]): row for row in result["candidate_counts"]}
        self.assertEqual(result["upper_bound"], 5)
        self.assertEqual(rows[("x",)]["candidate_count"], 1)
        self.assertEqual(rows[("y", "y")]["candidate_count"], 1)

    def test_empty_words_are_normalized_and_counted(self) -> None:
        result = pair_conflict_upper_bound(
            {"": 2, "x": 3},
            {"", "a"},
            "ab",
            top_k=None,
        )

        self.assertEqual(result["upper_bound"], 5)
        self.assertEqual(result["cipher_type_count"], 2)
        self.assertEqual(result["candidate_type_count"], 2)

    def test_duplicate_words_and_zero_weights_are_normalized(self) -> None:
        result = pair_conflict_upper_bound(
            {"xy": 0, ("x", "y"): 2, "yx": 1},
            {"ab", "ba"},
            "abc",
            top_k=None,
        )

        self.assertEqual(result["cipher_type_count"], 2)
        self.assertEqual(result["total_weight"], 3)
        self.assertEqual(result["upper_bound"], 3)
        self.assertEqual(result["candidate_type_count"], 2)

    def test_top_k_adds_omitted_possible_weight_to_keep_global_bound(self) -> None:
        full = pair_conflict_upper_bound(
            {"x": 5, "y": 4},
            {"a", "b"},
            "abc",
            top_k=None,
        )
        limited = pair_conflict_upper_bound(
            {"x": 5, "y": 4},
            {"a", "b"},
            "abc",
            top_k=1,
        )

        self.assertEqual(full["upper_bound"], 9)
        self.assertEqual(limited["upper_bound"], 9)
        self.assertEqual(limited["selected_type_count"], 1)
        self.assertEqual(limited["omitted_type_count"], 1)
        self.assertEqual(limited["omitted_weight"], 4)

    def test_random_small_cases_never_underestimate_exhaustive_score(self) -> None:
        rng = random.Random(20260916)
        for case in range(100):
            alphabet = "abcd"[: rng.randint(2, 4)]
            cipher_symbols = "wxyz"[: rng.randint(1, len(alphabet))]
            ciphertext: dict[str, int] = {}
            for _ in range(rng.randint(1, 5)):
                word = "".join(rng.choice(cipher_symbols) for _ in range(rng.randint(1, 3)))
                ciphertext[word] = rng.randint(0, 5)
            lexicon = {
                "".join(rng.choice(alphabet) for _ in range(rng.randint(1, 3)))
                for _ in range(rng.randint(0, 8))
            }

            result = pair_conflict_upper_bound(
                ciphertext,
                lexicon,
                alphabet,
                top_k=None,
            )
            expected = _brute_maximum(ciphertext, lexicon, alphabet)
            with self.subTest(case=case, ciphertext=ciphertext, lexicon=lexicon):
                self.assertGreaterEqual(result["upper_bound"], expected)
                self.assertLessEqual(result["upper_bound"], result["total_weight"])

    def test_empty_and_infeasible_inputs_are_explicit(self) -> None:
        empty = pair_conflict_upper_bound({}, {"a"}, "a", top_k=None)
        infeasible = pair_conflict_upper_bound(
            {"xy": 1},
            {"ab"},
            "a",
            top_k=None,
        )

        self.assertEqual(empty["status"], "empty_input")
        self.assertEqual(empty["upper_bound"], 0)
        self.assertEqual(infeasible["status"], "infeasible_alphabet")
        self.assertFalse(infeasible["feasible"])
        self.assertIsNone(infeasible["upper_bound"])

    def test_top_k_and_weights_are_validated(self) -> None:
        with self.assertRaises(ValueError):
            pair_conflict_upper_bound({"a": 1}, {"a"}, "a", top_k=-1)
        with self.assertRaises(ValueError):
            pair_conflict_upper_bound({"a": 1}, {"a"}, "a", top_k=True)
        with self.assertRaises(ValueError):
            pair_conflict_upper_bound({"a": -1}, {"a"}, "a")


if __name__ == "__main__":
    unittest.main()
