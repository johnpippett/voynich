"""Behavioral tests for the bounded finite-lexicon substitution solver."""

from __future__ import annotations

import itertools
import pathlib
import random
import sys
import unittest


PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from experiments.lexicon.solver import solve_lexicon


def _word(value: str | tuple[str, ...]) -> tuple[str, ...]:
    return tuple(value) if isinstance(value, str) else value


def _brute_score(
    ciphertext_counts: dict[str, int],
    lexicon: set[str],
    alphabet: str,
) -> int:
    symbols = sorted({symbol for word in ciphertext_counts for symbol in word})
    best = 0
    for values in itertools.permutations(alphabet, len(symbols)):
        key = dict(zip(symbols, values))
        score = sum(
            weight
            for word, weight in ciphertext_counts.items()
            if "".join(key[symbol] for symbol in word) in lexicon
        )
        best = max(best, score)
    return best


class LexiconSolverTests(unittest.TestCase):
    @staticmethod
    def _without_engine_label(result: dict) -> dict:
        copy = dict(result)
        copy["config"] = dict(result["config"])
        copy["config"].pop("bound_engine", None)
        return copy

    def test_reference_and_bitset_engines_match_edge_cases(self) -> None:
        cases = [
            ({}, {"a"}, "abc", None, None),
            ({"xx": 2}, {"ab"}, "abc", None, None),
            ({"xyz": 1}, {"abc"}, "ab", None, None),
            (
                {"xy": 3, "yx": 1, "xx": 2},
                {"ab", "ba", "aa"},
                "abc",
                0,
                {"x": "a"},
            ),
            (
                {"xy": 3, "yx": 1, "xx": 2},
                {"ab", "ba", "aa"},
                "abc",
                1,
                {"x": "a"},
            ),
            (
                {"xy": 3, "yx": 1, "xx": 2},
                {"ab", "ba", "aa"},
                "abc",
                None,
                {"x": "a"},
            ),
        ]
        for ciphertext, lexicon, alphabet, budget, initial_key in cases:
            kwargs = {"node_budget": budget, "initial_key": initial_key}
            reference = solve_lexicon(
                ciphertext,
                lexicon,
                alphabet,
                bound_engine="reference",
                **kwargs,
            )
            bitset = solve_lexicon(
                ciphertext,
                lexicon,
                alphabet,
                bound_engine="bitset",
                **kwargs,
            )
            self.assertEqual(
                self._without_engine_label(reference),
                self._without_engine_label(bitset),
            )
            self.assertEqual(reference["config"]["bound_engine"], "reference")
            self.assertEqual(bitset["config"]["bound_engine"], "bitset")

    def test_reference_and_bitset_engines_match_random_cases_and_brute_optimum(self) -> None:
        rng = random.Random(20260916)
        for alphabet_size in range(1, 5):
            alphabet = "abcd"[:alphabet_size]
            for _case in range(12):
                symbols = "wxyz"[: rng.randint(0, alphabet_size)]
                ciphertext: dict[str, int] = {}
                for _word_index in range(rng.randint(0, 5)):
                    word = "".join(
                        rng.choice(symbols) for _ in range(rng.randint(0, 3))
                    ) if symbols else ""
                    ciphertext[word] = rng.randint(0, 7)
                lexicon = {
                    "".join(
                        rng.choice(alphabet) for _ in range(rng.randint(0, 3))
                    )
                    for _ in range(rng.randint(0, 8))
                }
                ordered_symbols = sorted({symbol for word in ciphertext for symbol in word})
                width = rng.randint(0, min(len(ordered_symbols), len(alphabet)))
                shuffled_plain = list(alphabet)
                rng.shuffle(shuffled_plain)
                initial_key = dict(
                    zip(ordered_symbols[:width], shuffled_plain[:width], strict=True)
                ) or None
                budget = rng.choice([0, 1, 2, 5, None])
                kwargs = {
                    "node_budget": budget,
                    "initial_key": initial_key,
                }
                reference = solve_lexicon(
                    ciphertext,
                    lexicon,
                    alphabet,
                    bound_engine="reference",
                    **kwargs,
                )
                bitset = solve_lexicon(
                    ciphertext,
                    lexicon,
                    alphabet,
                    bound_engine="bitset",
                    **kwargs,
                )
                self.assertEqual(
                    self._without_engine_label(reference),
                    self._without_engine_label(bitset),
                )
                if budget is None and reference["feasible"]:
                    self.assertEqual(
                        reference["score"],
                        _brute_score(ciphertext, lexicon, alphabet),
                    )

    def test_search_exhaustion_matches_small_alphabet_optimum(self) -> None:
        ciphertext = {"xy": 3, "yx": 1, "xx": 2, "zz": 1}
        lexicon = {"ab", "ba", "aa", "cc"}
        expected = _brute_score(ciphertext, lexicon, "abc")

        result = solve_lexicon(ciphertext, lexicon, "abc")

        self.assertEqual(result["status"], "search_exhausted")
        self.assertTrue(result["score_certified"])
        self.assertTrue(result["search_exhausted"])
        self.assertNotIn("all_keys_enumerated", result)
        self.assertEqual(result["lower_bound"], expected)
        self.assertEqual(result["upper_bound"], expected)
        self.assertEqual(result["score"], expected)
        self.assertEqual(len(set(result["key"].values())), len(result["key"]))

    def test_pruning_does_not_claim_every_feasible_key_was_visited(self) -> None:
        result = solve_lexicon(
            {"xy": 3, "yx": 1, "xx": 2, "zz": 1},
            {"ab", "ba", "aa", "cc"},
            "abc",
        )

        self.assertEqual(result["status"], "search_exhausted")
        self.assertTrue(result["search_exhausted"])
        self.assertTrue(result["score_certified"])
        self.assertGreater(result["pruned_nodes"], 0)
        self.assertLess(result["nodes"], 6)  # 3P3 feasible injective keys.
        self.assertNotIn("all_keys_enumerated", result)

    def test_budget_bounds_cover_all_unsearched_branches(self) -> None:
        ciphertext = {"xy": 1}
        lexicon = {"ba"}
        expected = _brute_score(ciphertext, lexicon, "ab")

        for budget in (0, 1, 2):
            result = solve_lexicon(
                ciphertext,
                lexicon,
                "ab",
                node_budget=budget,
            )

            self.assertGreaterEqual(result["upper_bound"], expected)
            self.assertLessEqual(result["lower_bound"], result["upper_bound"])
            self.assertLessEqual(result["nodes"], budget)
            if budget == 1:
                self.assertEqual(result["status"], "budget_exhausted")
                self.assertFalse(result["score_certified"])
                self.assertFalse(result["search_exhausted"])
                self.assertGreater(result["frontier_node_count"], 0)

    def test_missing_candidates_are_reported_without_invented_hits(self) -> None:
        result = solve_lexicon(
            {"xy": 2, "xx": 3},
            {"ab"},
            "abc",
        )

        rows = {"".join(row["cipher_word"]): row for row in result["candidate_counts"]}
        self.assertEqual(result["status"], "search_exhausted")
        self.assertEqual(result["score"], 2)
        self.assertEqual(result["missing_candidate_count"], 1)
        self.assertEqual(rows["xy"]["candidate_count"], 1)
        self.assertEqual(rows["xx"]["candidate_count"], 0)

    def test_no_candidates_is_a_certified_zero_bound(self) -> None:
        result = solve_lexicon({"xx": 2, "xyz": 3}, {"ab"}, "abc")

        self.assertEqual(result["status"], "no_candidates")
        self.assertTrue(result["score_certified"])
        self.assertTrue(result["search_exhausted"])
        self.assertEqual(result["lower_bound"], 0)
        self.assertEqual(result["upper_bound"], 0)
        self.assertEqual(result["missing_candidate_count"], 2)

    def test_infeasible_cipher_alphabet_is_reported(self) -> None:
        result = solve_lexicon({"xyz": 1}, {"abc"}, "ab")

        self.assertEqual(result["status"], "infeasible_alphabet")
        self.assertFalse(result["feasible"])
        self.assertEqual(result["key"], {})
        self.assertIsNone(result["lower_bound"])
        self.assertIsNone(result["upper_bound"])
        self.assertIsNone(result["score"])
        self.assertTrue(result["infeasibility_certified"])

    def test_partial_initial_key_is_validated_and_used_as_a_lower_bound(self) -> None:
        result = solve_lexicon(
            {"xy": 2, "yx": 1},
            {"ab", "ba"},
            "abc",
            initial_key={"x": "a"},
            node_budget=0,
        )

        self.assertEqual(result["key"]["x"], "a")
        self.assertGreaterEqual(result["lower_bound"], 0)
        self.assertGreaterEqual(result["upper_bound"], result["lower_bound"])
        with self.assertRaises(ValueError):
            solve_lexicon({"xy": 1}, {"ab"}, "abc", initial_key={"x": "a", "y": "a"})

    def test_initial_key_is_warm_start_and_does_not_restrict_root_search(self) -> None:
        ciphertext = {"xy": 1}
        lexicon = {"ba"}
        expected = _brute_score(ciphertext, lexicon, "ab")

        for initial_key in ({"x": "a"}, {"x": "a", "y": "b"}):
            for budget in (0, 1):
                result = solve_lexicon(
                    ciphertext,
                    lexicon,
                    "ab",
                    initial_key=initial_key,
                    node_budget=budget,
                )
                self.assertEqual(result["status"], "budget_exhausted")
                self.assertEqual(result["lower_bound"], 0)
                self.assertGreaterEqual(result["upper_bound"], expected)

            completed = solve_lexicon(
                ciphertext,
                lexicon,
                "ab",
                initial_key=initial_key,
            )
            self.assertEqual(completed["status"], "search_exhausted")
            self.assertTrue(completed["score_certified"])
            self.assertTrue(completed["search_exhausted"])
            self.assertEqual(completed["lower_bound"], expected)
            self.assertEqual(completed["upper_bound"], expected)

    def test_completion_statuses_have_separate_score_and_search_flags(self) -> None:
        cases = {
            "empty_input": solve_lexicon({}, {"a"}, "a"),
            "infeasible_alphabet": solve_lexicon({"xy": 1}, {"ab"}, "a"),
            "no_candidates": solve_lexicon({"xx": 1}, {"ab"}, "abc"),
            "bound_certified": solve_lexicon(
                {"xy": 1}, {"ab", "ba"}, "ab", node_budget=0
            ),
            "budget_exhausted": solve_lexicon(
                {"xy": 1}, {"ba"}, "ab", node_budget=0
            ),
            "search_exhausted": solve_lexicon({"xy": 1}, {"ba"}, "ab"),
        }
        expected_flags = {
            "empty_input": (True, True),
            "infeasible_alphabet": (False, True),
            "no_candidates": (True, True),
            "bound_certified": (True, False),
            "budget_exhausted": (False, False),
            "search_exhausted": (True, True),
        }
        expected_infeasibility = {
            "empty_input": False,
            "infeasible_alphabet": True,
            "no_candidates": False,
            "bound_certified": False,
            "budget_exhausted": False,
            "search_exhausted": False,
        }
        for expected_status, result in cases.items():
            self.assertEqual(result["status"], expected_status)
            self.assertEqual(
                (result["score_certified"], result["search_exhausted"]),
                expected_flags[expected_status],
            )
            self.assertIsInstance(result["score_certified"], bool)
            self.assertIsInstance(result["search_exhausted"], bool)
            self.assertEqual(
                result["infeasibility_certified"],
                expected_infeasibility[expected_status],
            )
            if result["feasible"]:
                self.assertLessEqual(result["lower_bound"], result["upper_bound"])
                if result["score_certified"]:
                    self.assertEqual(result["lower_bound"], result["upper_bound"])
            else:
                self.assertFalse(result["score_certified"])
                self.assertIsNone(result["lower_bound"])
                self.assertIsNone(result["upper_bound"])

    def test_lexicon_counts_distinguish_raw_and_unique_normalized_entries(self) -> None:
        result = solve_lexicon(
            {"xy": 1},
            ["ab", "ab", "zz"],
            "ab",
        )

        self.assertEqual(result["lexicon_raw_entry_count"], 3)
        self.assertEqual(result["lexicon_unique_normalized_count"], 2)
        self.assertEqual(result["lexicon_usable_count"], 1)
        self.assertEqual(result["lexicon_rejected_out_of_alphabet_count"], 1)
        self.assertNotIn("lexicon_input_count", result)

    def test_budgeted_runs_are_deterministic_and_report_scope(self) -> None:
        args = ({"xy": 2, "yx": 1}, {"ab", "ba"}, "abc")
        first = solve_lexicon(*args, node_budget=1)
        second = solve_lexicon(*args, node_budget=1)

        self.assertEqual(first, second)
        self.assertNotIn("all_keys_enumerated", first)
        self.assertIn("search_exhausted", first)
        self.assertIsInstance(first["scope_limits"], list)
        self.assertIsInstance(first["performance_followups"], list)
        self.assertIsInstance(first["lower_bound"], int)
        self.assertIsInstance(first["upper_bound"], int)

    def test_weights_and_inputs_are_validated(self) -> None:
        with self.assertRaises(ValueError):
            solve_lexicon({"a": -1}, {"a"}, "a")
        with self.assertRaises(ValueError):
            solve_lexicon({"a": True}, {"a"}, "a")
        with self.assertRaises(ValueError):
            solve_lexicon({"a": 1}, {"a"}, "aa")
        with self.assertRaises(ValueError):
            solve_lexicon({"a": 1}, {"a"}, "a", bound_engine="other")
        with self.assertRaises(ValueError):
            solve_lexicon({"a": 1}, {"a"}, "a", bound_engine=[])  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
