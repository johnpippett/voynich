"""Behavioral tests for bounded threshold queries."""

from __future__ import annotations

from collections import Counter
import itertools
import pathlib
import sys
import unittest


PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from experiments.identifiability.threshold import (
    ThresholdProblem,
    build_threshold_problem,
    query_threshold,
)


Word = tuple[str, ...]


def _brute_keys(
    ciphertext_counts: dict[str, int],
    lexicon: set[str],
    alphabet: tuple[str, ...],
    capacity: int | None,
    constraints: dict[str, str] | None = None,
    forbidden: dict[str, set[str]] | None = None,
):
    constraints = constraints or {}
    forbidden = forbidden or {}
    symbols = tuple(sorted({symbol for word in ciphertext_counts for symbol in word}))
    for values in itertools.product(alphabet, repeat=len(symbols)):
        key = dict(zip(symbols, values, strict=True))
        if any(key[symbol] != value for symbol, value in constraints.items()):
            continue
        if any(key[symbol] in forbidden.get(symbol, set()) for symbol in symbols):
            continue
        if capacity is not None and any(
            count > capacity for count in Counter(values).values()
        ):
            continue
        score = sum(
            weight
            for word, weight in ciphertext_counts.items()
            if "".join(key[symbol] for symbol in word) in lexicon
        )
        yield key, score


class ThresholdQueryTests(unittest.TestCase):
    def _problem(self, capacity: int | None = 1) -> ThresholdProblem:
        return build_threshold_problem(
            {"xy": 5, "yx": 3, "xx": 2},
            {"aa", "ab", "ba", "bb"},
            "ab",
            capacity=capacity,
        )

    def test_full_queries_match_direct_products_for_all_capacities(self) -> None:
        for capacity in (1, 2, None):
            problem = self._problem(capacity)
            keys = list(
                _brute_keys(
                    {"xy": 5, "yx": 3, "xx": 2},
                    {"aa", "ab", "ba", "bb"},
                    ("a", "b"),
                    capacity,
                )
            )
            maximum = max(score for _key, score in keys)
            for target in (0, maximum, maximum + 1):
                result = problem.query(target)
                expected = any(score >= target for _key, score in keys)
                self.assertEqual(result["status"] == "feasible", expected)
                if expected:
                    self.assertIsInstance(result["key"], dict)
                    self.assertGreaterEqual(result["score"], target)
                    self.assertLessEqual(
                        Counter(result["key"].values()).most_common(1)[0][1],
                        capacity if capacity is not None else 2,
                    )
                else:
                    self.assertEqual(result["status"], "infeasible")
                    self.assertLess(result["frontier_upper"], target)

    def test_budgeted_queries_distinguish_unknown_from_infeasible(self) -> None:
        problem = build_threshold_problem(
            {"xy": 1},
            {"ba"},
            "ab",
            capacity=1,
        )

        unknown = problem.query(1, node_budget=0)
        self.assertEqual(unknown["status"], "unknown")
        self.assertFalse(unknown["feasible"])
        self.assertGreaterEqual(unknown["frontier_upper"], 1)
        self.assertEqual(unknown["nodes"], 0)
        self.assertGreaterEqual(unknown["lower_bound"], 0)

        infeasible = problem.query(2, node_budget=0)
        self.assertEqual(infeasible["status"], "infeasible")
        self.assertEqual(infeasible["proof_kind"], "frontier_upper_below_target")
        self.assertLess(infeasible["frontier_upper"], 2)

        exhausted = problem.query(1)
        self.assertEqual(exhausted["status"], "feasible")
        self.assertGreaterEqual(exhausted["score"], 1)

    def test_budget_zero_one_few_and_unbounded_have_explicit_statuses(self) -> None:
        problem = build_threshold_problem(
            {"xy": 1},
            {"ba"},
            "ab",
            capacity=1,
        )
        results = {
            budget: problem.query(1, node_budget=budget)
            for budget in (0, 1, 2)
        }
        self.assertEqual(results[0]["status"], "unknown")
        self.assertEqual(results[1]["status"], "unknown")
        self.assertEqual(results[2]["status"], "unknown")
        for result in results.values():
            self.assertGreaterEqual(result["lower_bound"], 0)
            self.assertGreaterEqual(result["frontier_upper"], 1)
        self.assertEqual(problem.query(1)["status"], "feasible")

    def test_infeasible_capacity_and_missing_candidates_are_explicit(self) -> None:
        capacity = build_threshold_problem(
            {"xyz": 1},
            {"aaa"},
            "ab",
            capacity=1,
        )
        capacity_result = capacity.query(0)
        self.assertEqual(capacity_result["status"], "infeasible")
        self.assertEqual(capacity_result["proof_kind"], "domain_impossibility")

        missing = build_threshold_problem(
            {"xy": 1},
            {"aa"},
            "ab",
            capacity=1,
        )
        missing_result = missing.query(1)
        self.assertEqual(missing_result["status"], "infeasible")
        self.assertLess(missing_result["frontier_upper"], 1)

    def test_upper_bound_keeps_pruned_branch_certificates(self) -> None:
        # Each incompatible branch has upper bound two, but target three
        # prunes both branches before a complete key is visited.
        problem = build_threshold_problem(
            {"xy": 2, "x": 2},
            {"ab", "b"},
            "ab",
            capacity=2,
            symbol_order=("x", "y"),
        )
        result = problem.query(3)
        self.assertEqual(result["status"], "infeasible")
        self.assertEqual(result["frontier_upper"], 0)
        self.assertGreaterEqual(result["upper_bound"], 2)
        self.assertGreaterEqual(result["upper_bound"], result["lower_bound"])

        keys = list(
            _brute_keys({"xy": 2, "x": 2}, {"ab", "b"}, ("a", "b"), 2)
        )
        maximum = max(score for _key, score in keys)
        for target in range(maximum + 2):
            checked = problem.query(target)
            self.assertGreaterEqual(checked["upper_bound"], maximum)

    def test_constraints_and_forbidden_domains_are_hard_search_constraints(self) -> None:
        problem = self._problem(1)
        result = problem.query(
            5,
            constraints={"x": "a"},
            forbidden={"y": {"a"}},
        )
        self.assertEqual(result["status"], "feasible")
        self.assertEqual(result["key"]["x"], "a")
        self.assertEqual(result["key"]["y"], "b")
        self.assertEqual(result["forbidden"], {"y": ["a"]})
        self.assertEqual(result["constraints"], {"x": "a"})

        impossible = problem.query(
            0,
            constraints={"x": "a"},
            forbidden={"x": {"a", "b"}},
        )
        self.assertEqual(impossible["status"], "infeasible")
        self.assertIn(impossible["proof_kind"], {
            "domain_impossibility",
            "search_exhausted_no_witness",
        })

    def test_forbidden_hall_effect_is_not_called_infeasible_by_greedy_failure(self) -> None:
        problem = build_threshold_problem(
            {"xyz": 1},
            {"aab"},
            "ab",
            capacity=2,
        )
        result = problem.query(0, forbidden={"x": {"b"}, "y": {"b"}, "z": {"b"}})
        self.assertEqual(result["status"], "infeasible")
        self.assertEqual(result["proof_kind"], "search_exhausted_no_witness")
        self.assertIsNone(result["key"])

        feasible = problem.query(0, forbidden={"x": {"b"}, "y": {"b"}})
        self.assertEqual(feasible["status"], "feasible")
        self.assertEqual(feasible["score"], 1)

    def test_initial_key_is_a_warm_start_and_does_not_restrict_root(self) -> None:
        problem = build_threshold_problem({"xy": 1}, {"ba"}, "ab", capacity=1)
        result = problem.query(1, initial_key={"x": "a"}, node_budget=0)

        self.assertEqual(result["status"], "unknown")
        self.assertGreaterEqual(result["frontier_upper"], 1)
        complete = problem.query(1, initial_key={"x": "a"})
        self.assertEqual(complete["status"], "feasible")
        self.assertEqual(complete["key"], {"x": "b", "y": "a"})

        with self.assertRaises(ValueError):
            problem.query(1, initial_key={"x": "a"}, forbidden={"x": {"a"}})

    def test_empty_zero_weight_and_target_zero_cases(self) -> None:
        empty = build_threshold_problem({}, {"a"}, "ab", capacity=1)
        self.assertEqual(empty.query(0)["status"], "feasible")
        self.assertEqual(empty.query(0)["key"], {})
        self.assertEqual(empty.query(1)["status"], "infeasible")

        zero = build_threshold_problem({"x": 0}, {"a"}, "ab", capacity=1)
        self.assertEqual(zero.query(0)["status"], "feasible")
        self.assertEqual(zero.query(1)["status"], "infeasible")

    def test_problem_and_queries_are_reusable_and_fingerprinted(self) -> None:
        problem = self._problem(2)
        first = problem.query(5, node_budget=1)
        second = problem.query(5, node_budget=1)
        wrapper = query_threshold(problem, 5, node_budget=1)
        self.assertEqual(first, second)
        self.assertEqual(first, wrapper)
        self.assertEqual(first["problem_fingerprint"], second["problem_fingerprint"])
        self.assertEqual(first["query_target"], 5)
        self.assertEqual(first["node_budget"], 1)
        self.assertIsInstance(first["frontier_upper"], int)
        self.assertIsInstance(first["nodes"], int)
        self.assertIn(first["status"], {"feasible", "infeasible", "unknown"})
        self.assertIn("threshold witness", first["interpretation"])

    def test_problem_state_is_read_only_and_input_mutation_isolated(self) -> None:
        counts = {"xy": 1}
        lexicon = {"ba"}
        alphabet = ["a", "b"]
        problem = build_threshold_problem(
            counts,
            lexicon,
            alphabet,
            capacity=1,
        )
        before = problem.query(1, node_budget=0)

        counts["xy"] = 99
        counts["zz"] = 1
        lexicon.add("aa")
        alphabet[0] = "q"
        after = problem.query(1, node_budget=0)
        self.assertEqual(before, after)

        with self.assertRaises(TypeError):
            problem.ciphertext_counts[("x", "y")] = 2  # type: ignore[index]
        with self.assertRaises(TypeError):
            problem.root_candidates[("x", "y")] = ()  # type: ignore[index]
        with self.assertRaises(AttributeError):
            problem.capacity = 2  # type: ignore[misc]
        with self.assertRaises(AttributeError):
            problem.plaintext_alphabet = ("c",)  # type: ignore[misc]
        metadata = problem.bound_metadata
        metadata["slot_count"] = -1
        self.assertNotEqual(problem.bound_metadata["slot_count"], -1)

    def test_symbol_order_is_validated_recorded_and_fingerprinted_separately(self) -> None:
        counts = {"xy": 5, "yz": 5, "z": 1}
        problem = build_threshold_problem(counts, {"aaa", "aba"}, "ab")
        # y has weight 10, z has weight 6, and x has weight 5.
        self.assertEqual(problem.symbol_order, ("y", "z", "x"))
        result = problem.query(0, node_budget=0)
        self.assertEqual(
            result["config"]["symbol_order"], ["y", "z", "x"]
        )
        self.assertEqual(result["symbol_order"], ["y", "z", "x"])
        self.assertEqual(
            result["problem_fingerprint"], result["objective_domain_fingerprint"]
        )
        self.assertIn("search_settings_fingerprint", result)

        explicit = build_threshold_problem(
            counts,
            {"aaa", "aba"},
            "ab",
            symbol_order=("x", "z", "y"),
        )
        self.assertEqual(explicit.symbol_order, ("x", "z", "y"))
        self.assertEqual(problem.problem_fingerprint, explicit.problem_fingerprint)
        self.assertNotEqual(
            problem.search_settings_fingerprint,
            explicit.search_settings_fingerprint,
        )
        self.assertNotEqual(
            problem.query(0, node_budget=0)["query_fingerprint"],
            explicit.query(0, node_budget=0)["query_fingerprint"],
        )

        for bad_order in (("x", "y"), ("x", "y", "y"), ("x", "y", "q")):
            with self.assertRaises(ValueError):
                build_threshold_problem(
                    counts,
                    {"aaa"},
                    "ab",
                    symbol_order=bad_order,
                )

    def test_malformed_inputs_and_contradictory_domains(self) -> None:
        with self.assertRaises(ValueError):
            build_threshold_problem({"x": 1}, {"a"}, "ab", capacity=3)
        problem = self._problem(1)
        for target in (-1, True, 1.0):
            with self.assertRaises(ValueError):
                problem.query(target)  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            problem.query(0, constraints={"q": "a"})
        with self.assertRaises(ValueError):
            problem.query(0, constraints={"x": "q"})
        with self.assertRaises(ValueError):
            problem.query(0, forbidden={"q": {"a"}})
        with self.assertRaises(ValueError):
            problem.query(0, forbidden={"x": {"q"}})
        with self.assertRaises(TypeError):
            problem.query(0, forbidden=[("x", {"a"})])  # type: ignore[arg-type]

        contradictory = problem.query(0, constraints={"x": "a", "y": "a"})
        self.assertEqual(contradictory["status"], "infeasible")
        self.assertEqual(contradictory["proof_kind"], "domain_impossibility")


if __name__ == "__main__":
    unittest.main()
