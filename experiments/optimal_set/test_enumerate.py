"""Synthetic tests for bounded equal-score completion enumeration."""

from __future__ import annotations

from collections import Counter
import itertools
import unittest

from experiments.identifiability.threshold import ThresholdProblem
from experiments.optimal_set.enumerate import enumerate_equal_score_completions


Word = tuple[str, ...]


def _word(value: str | Word) -> Word:
    return tuple(value) if isinstance(value, str) else value


def _brute_maps(
    counts: dict[str | Word, int],
    lexicon: set[str | Word],
    alphabet: str | tuple[str, ...],
    capacity: int | None,
    fixed: dict[str, str] | None = None,
) -> list[tuple[dict[str, str], int]]:
    normal_counts = {_word(word): weight for word, weight in counts.items()}
    normal_lexicon = {_word(word) for word in lexicon}
    alphabet_values = tuple(alphabet)
    symbols = tuple(sorted({symbol for word in normal_counts for symbol in word}))
    fixed = fixed or {}
    free = tuple(symbol for symbol in symbols if symbol not in fixed)
    result: list[tuple[dict[str, str], int]] = []
    for values in itertools.product(alphabet_values, repeat=len(free)):
        key = dict(fixed)
        key.update(zip(free, values, strict=True))
        if capacity is not None and any(
            count > capacity for count in Counter(key.values()).values()
        ):
            continue
        score = sum(
            weight
            for word, weight in normal_counts.items()
            if tuple(key[symbol] for symbol in word) in normal_lexicon
        )
        result.append((dict(sorted(key.items())), score))
    return result


class EqualScoreEnumerationTests(unittest.TestCase):
    def test_complete_maps_match_independent_brute_force_for_all_capacities(
        self,
    ) -> None:
        counts = {"x": 2, "y": 1, "xy": 3}
        lexicon = {"a", "b", "ab", "ba"}
        for capacity in (1, 2, None):
            brute = _brute_maps(counts, lexicon, "ab", capacity)
            target = max(score for _key, score in brute)
            expected = [key for key, score in brute if score == target]
            result = enumerate_equal_score_completions(
                counts,
                lexicon,
                "ab",
                capacity=capacity,
                target=target,
            )
            self.assertEqual(result["status"], "complete")
            self.assertEqual(result["collected_maps"], expected)
            self.assertEqual(result["feasible_leaves"], len(brute))
            self.assertEqual(result["product_bound"], 4)
            self.assertFalse(result["truncation"])

    def test_random_complete_maps_match_brute_force(self) -> None:
        import random

        rng = random.Random(20260917)
        for _case in range(24):
            alphabet = tuple("abc"[: rng.randrange(1, 4)])
            units = tuple("xyz"[: rng.randrange(0, 4)])
            counts: dict[str, int] = {}
            for _index in range(rng.randrange(0, 5)):
                word = (
                    "".join(rng.choice(units) for _ in range(rng.randrange(0, 4)))
                    if units
                    else ""
                )
                counts[word] = rng.randrange(0, 5)
            lexicon = {
                "".join(
                    rng.choice(alphabet) for _ in range(rng.randrange(0, 4))
                )
                for _index in range(rng.randrange(0, 8))
            }
            for capacity in (1, 2, None):
                brute = _brute_maps(counts, lexicon, alphabet, capacity)
                target = max((score for _key, score in brute), default=0)
                expected = [key for key, score in brute if score == target]
                result = enumerate_equal_score_completions(
                    counts,
                    lexicon,
                    alphabet,
                    capacity=capacity,
                    target=target,
                )
                self.assertEqual(result["status"], "complete")
                self.assertEqual(result["collected_maps"], expected)

    def test_fixed_domain_is_reported_without_global_claims(self) -> None:
        result = enumerate_equal_score_completions(
            {"xy": 1},
            {"ab", "ba"},
            "abc",
            capacity=1,
            fixed_key={"x": "a"},
            target=1,
        )

        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["reason"], "all_domain_completions_checked")
        self.assertEqual(result["fixed_assignments"], {"x": "a"})
        self.assertEqual(result["full_alphabet"], ["a", "b", "c"])
        self.assertEqual(result["free_units"], ["y"])
        self.assertEqual(result["product_bound"], 3)
        self.assertEqual(result["collected_maps"], [{"x": "a", "y": "b"}])
        self.assertFalse(result["claims_global_optimum"])
        self.assertFalse(result["claims_fixed_assignments_forced"])

        reordered = enumerate_equal_score_completions(
            {"xy": 1},
            {"ba", "ab"},
            ("c", "b", "a"),
            capacity=1,
            fixed_key={"x": "a"},
            target=1,
        )
        self.assertEqual(result["domain_fingerprint"], reordered["domain_fingerprint"])

    def test_objective_fingerprint_matches_threshold_and_ignores_fixed_key(
        self,
    ) -> None:
        expected = ThresholdProblem(
            {"xy": 1},
            {"ab", "ba"},
            "abc",
            capacity=1,
        ).problem_fingerprint
        unfixed = enumerate_equal_score_completions(
            {"xy": 1},
            {"ab", "ba"},
            "abc",
            capacity=1,
            target=1,
        )
        fixed = enumerate_equal_score_completions(
            {"xy": 1},
            {"ab", "ba"},
            "abc",
            capacity=1,
            fixed_key={"x": "a"},
            target=1,
        )
        self.assertEqual(unfixed["objective_domain_fingerprint"], expected)
        self.assertEqual(fixed["objective_domain_fingerprint"], expected)
        self.assertNotEqual(
            unfixed["domain_fingerprint"], fixed["domain_fingerprint"]
        )

    def test_empty_input_full_fixed_and_zero_target(self) -> None:
        empty = enumerate_equal_score_completions({}, set(), "ab", target=0)
        self.assertEqual(empty["status"], "complete")
        self.assertEqual(empty["collected_maps"], [{}])
        self.assertEqual(empty["visited_nodes"], 1)
        self.assertEqual(empty["feasible_leaves"], 1)
        self.assertEqual(empty["product_bound"], 1)

        full = enumerate_equal_score_completions(
            {"x": 2},
            {"a"},
            "ab",
            capacity=1,
            fixed_key={"x": "a"},
            target=2,
        )
        self.assertEqual(full["status"], "complete")
        self.assertEqual(full["collected_maps"], [{"x": "a"}])
        self.assertEqual(full["feasible_leaves"], 1)
        self.assertEqual(full["product_bound"], 1)

    def test_capacity_pruning_and_capacity_infeasibility_are_explicit(self) -> None:
        result = enumerate_equal_score_completions(
            {"x": 1, "y": 1},
            set(),
            "ab",
            capacity=1,
            target=0,
        )
        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["feasible_leaves"], 2)
        self.assertEqual(result["capacity_prunes"], 2)
        self.assertEqual(len(result["collected_maps"]), 2)

        impossible = enumerate_equal_score_completions(
            {"x": 1, "y": 1, "z": 1},
            set(),
            "ab",
            capacity=1,
            target=0,
        )
        self.assertEqual(impossible["status"], "complete")
        self.assertEqual(impossible["reason"], "capacity_infeasible")
        self.assertEqual(impossible["feasible_leaves"], 0)
        self.assertGreater(impossible["capacity_prunes"], 0)
        self.assertEqual(impossible["collected_maps"], [])

    def test_product_limit_stops_before_search(self) -> None:
        result = enumerate_equal_score_completions(
            {"x": 1, "y": 1, "z": 1},
            {"aaa"},
            "abc",
            capacity=None,
            target=0,
            max_product=8,
        )
        self.assertEqual(result["status"], "not_complete")
        self.assertEqual(result["reason"], "product_limit")
        self.assertEqual(result["product_bound"], 27)
        self.assertEqual(result["visited_nodes"], 0)
        self.assertEqual(result["feasible_leaves"], 0)
        self.assertEqual(result["truncation"], "product_limit")
        self.assertEqual(result["collected_maps"], [])

    def test_node_budget_zero_and_live_frontier_are_not_complete(self) -> None:
        result = enumerate_equal_score_completions(
            {"x": 1, "y": 1},
            {"aa", "bb"},
            "ab",
            capacity=2,
            target=2,
            node_budget=0,
        )
        self.assertEqual(result["status"], "not_complete")
        self.assertEqual(result["reason"], "node_budget")
        self.assertEqual(result["visited_nodes"], 0)
        self.assertEqual(result["truncation"], "node_budget")

        shallow = enumerate_equal_score_completions(
            {"x": 1, "y": 1},
            {"aa", "bb"},
            "ab",
            capacity=2,
            target=2,
            node_budget=2,
        )
        self.assertEqual(shallow["status"], "not_complete")
        self.assertEqual(shallow["visited_nodes"], 2)
        self.assertEqual(shallow["feasible_leaves"], 0)
        self.assertEqual(shallow["truncation"], "node_budget")

    def test_score_above_target_is_a_certificate_conflict(self) -> None:
        result = enumerate_equal_score_completions(
            {"x": 1},
            {"a"},
            "ab",
            capacity=1,
            target=0,
        )
        self.assertEqual(result["status"], "certificate_conflict")
        self.assertEqual(result["reason"], "complete_key_above_target")
        self.assertEqual(result["conflict_score"], 1)
        self.assertEqual(result["conflict_key"], {"x": "a"})
        self.assertEqual(result["collected_maps"], [])
        self.assertFalse(result["truncation"])

    def test_target_without_a_matching_score_can_complete(self) -> None:
        result = enumerate_equal_score_completions(
            {"x": 1},
            set(),
            "ab",
            capacity=1,
            target=1,
        )
        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["reason"], "all_domain_completions_checked")
        self.assertEqual(result["collected_maps"], [])
        self.assertEqual(result["feasible_leaves"], 2)

    def test_long_singleton_domain_uses_no_recursion(self) -> None:
        units = tuple(f"u{index}" for index in range(1100))
        counts = {units: 0}
        lexicon = {tuple("a" for _index in units)}
        result = enumerate_equal_score_completions(
            counts,
            lexicon,
            ("a",),
            capacity=None,
            target=0,
            max_product=1,
            node_budget=2000,
        )
        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["visited_nodes"], 1101)
        self.assertEqual(result["feasible_leaves"], 1)
        self.assertEqual(len(result["collected_maps"]), 1)
        self.assertEqual(len(result["collected_maps"][0]), 1100)

    def test_invalid_arguments_and_fixed_maps_are_rejected(self) -> None:
        base = ({"x": 1}, {"a"}, "ab")
        for kwargs in (
            {"target": -1},
            {"target": True},
            {"max_product": -1},
            {"max_product": True},
            {"node_budget": -1},
            {"node_budget": True},
            {"capacity": 0},
            {"capacity": 3},
            {"fixed_key": {"missing": "a"}},
            {"fixed_key": {"x": "missing"}},
        ):
            with self.assertRaises((TypeError, ValueError)):
                enumerate_equal_score_completions(*base, **kwargs)

        with self.assertRaises(ValueError):
            enumerate_equal_score_completions(
                {"x": 1, "y": 1},
                {"a"},
                "ab",
                capacity=1,
                fixed_key={"x": "a", "y": "a"},
            )


if __name__ == "__main__":
    unittest.main()
