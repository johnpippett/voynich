"""Tests for one-unit optimum identifiability assessments."""

from __future__ import annotations

from collections import Counter
import itertools
import unittest

from experiments.identifiability.assess import (
    CertificateContradiction,
    assess_optimum,
)
from experiments.identifiability.threshold import build_threshold_problem


def brute_keys(
    ciphertext_counts: dict[tuple[str, ...], int],
    lexicon: set[tuple[str, ...]],
    alphabet: tuple[str, ...],
    capacity: int | None,
):
    units = tuple(sorted({unit for word in ciphertext_counts for unit in word}))
    for values in itertools.product(alphabet, repeat=len(units)):
        if capacity is not None and any(
            count > capacity for count in Counter(values).values()
        ):
            continue
        key = dict(zip(units, values, strict=True))
        score = sum(
            weight
            for word, weight in ciphertext_counts.items()
            if tuple(key[unit] for unit in word) in lexicon
        )
        yield key, score


class AssessOptimumTests(unittest.TestCase):
    def _problem(self, capacity: int | None):
        counts = {("x",): 2, ("x", "y"): 3, ("y", "x"): 1}
        lexicon = {("a",), ("a", "b"), ("b", "a")}
        return build_threshold_problem(counts, lexicon, "ab", capacity=capacity), counts, lexicon

    def _certificate(self, problem, score: int) -> dict[str, object]:
        return {
            "problem_fingerprint": problem.problem_fingerprint,
            "target": score,
            "provenance": "test-global-bound",
            "proof_kind": "equal-global-bounds",
        }

    def test_all_capacities_match_brute_force_optimum_and_unit_classes(self) -> None:
        for capacity in (1, 2, None):
            problem, counts, lexicon = self._problem(capacity)
            keys = list(brute_keys(counts, lexicon, ("a", "b"), capacity))
            optimum = max(score for _key, score in keys)
            incumbent = next(key for key, score in keys if score == optimum)
            result = assess_optimum(
                problem,
                incumbent,
                optimum,
                certificate=self._certificate(problem, optimum),
                node_budget_per_query=None,
            )
            self.assertEqual(result["status"], "complete")
            expected = {}
            for unit in problem.cipher_symbols:
                alternatives = {
                    key[unit]
                    for key, score in keys
                    if score == optimum and key[unit] != incumbent[unit]
                }
                expected[unit] = bool(alternatives)
            actual = {
                record["cipher_unit"]: record["classification"] == "ambiguous"
                for record in result["records"]
            }
            self.assertEqual(actual, expected)
            self.assertEqual(
                [record["cipher_unit"] for record in result["records"]],
                sorted(problem.cipher_symbols),
            )

    def test_positive_hit_does_not_mean_forced(self) -> None:
        counts = {("x",): 1}
        problem = build_threshold_problem(counts, {("a",), ("b",)}, "ab", capacity=None)
        result = assess_optimum(
            problem,
            {"x": "a"},
            1,
            certificate=self._certificate(problem, 1),
            node_budget_per_query=None,
        )
        self.assertEqual(result["summary"]["ambiguous_units"], ["x"])
        self.assertEqual(result["records"][0]["witness"]["score"], 1)
        self.assertEqual(result["records"][0]["raw_query"]["status"], "feasible")
        self.assertEqual(result["records"][0]["raw_query"]["nodes"], 0)

    def test_exclusion_is_forced_only_when_no_optimal_alternative_exists(self) -> None:
        problem = build_threshold_problem(
            {("x",): 1},
            {("a",)},
            "ab",
            capacity=1,
        )
        result = assess_optimum(
            problem,
            {"x": "a"},
            1,
            certificate=self._certificate(problem, 1),
            node_budget_per_query=None,
        )
        self.assertEqual(result["summary"]["forced_units"], ["x"])
        self.assertIsNone(result["records"][0]["witness"])

    def test_unknown_budget_is_unresolved_when_no_warm_witness_exists(self) -> None:
        counts = {("x", "y"): 1}
        problem = build_threshold_problem(counts, {("a", "b")}, "ab", capacity=1)
        result = assess_optimum(
            problem,
            {"x": "a", "y": "b"},
            1,
            certificate=self._certificate(problem, 1),
            node_budget_per_query=0,
        )
        self.assertEqual(result["summary"]["unresolved_units"], ["x", "y"])
        self.assertTrue(all(record["raw_query"]["status"] == "unknown" for record in result["records"]))

    def test_wrong_target_fingerprint_and_incumbent_are_rejected(self) -> None:
        problem, _counts, _lexicon = self._problem(1)
        incumbent = {"x": "a", "y": "b"}
        with self.assertRaises(ValueError):
            assess_optimum(problem, incumbent, 999, certificate=self._certificate(problem, 999))
        with self.assertRaises(ValueError):
            assess_optimum(
                problem,
                incumbent,
                5,
                certificate={
                    "problem_fingerprint": "wrong",
                    "target": 5,
                    "provenance": "test",
                },
            )
        certificate = self._certificate(problem, 5)
        with self.assertRaises(ValueError):
            assess_optimum(problem, {"x": "a"}, 5, certificate=certificate)
        with self.assertRaises(ValueError):
            assess_optimum(
                problem,
                incumbent,
                5,
                certificate={"score_certified": True},
            )

    def test_certificate_provenance_is_not_a_boolean_flag(self) -> None:
        problem, _counts, _lexicon = self._problem(1)
        with self.assertRaises(ValueError):
            assess_optimum(
                problem,
                {"x": "a", "y": "b"},
                5,
                certificate={
                    "problem_fingerprint": problem.problem_fingerprint,
                    "target": 5,
                    "score_certified": True,
                },
            )

    def test_deterministic_repeat_and_record_fingerprints(self) -> None:
        problem, _counts, _lexicon = self._problem(1)
        certificate = self._certificate(problem, 6)
        first = assess_optimum(
            problem,
            {"x": "a", "y": "b"},
            6,
            certificate=certificate,
            node_budget_per_query=1,
        )
        second = assess_optimum(
            problem,
            {"x": "a", "y": "b"},
            6,
            certificate=certificate,
            node_budget_per_query=1,
        )
        self.assertEqual(first, second)
        self.assertEqual(first["problem_fingerprint"], problem.problem_fingerprint)
        self.assertEqual(
            {record["objective_domain_fingerprint"] for record in first["records"]},
            {first["objective_domain_fingerprint"]},
        )
        self.assertTrue(all("raw_query" in record for record in first["records"]))

    def test_score_above_certificate_aborts(self) -> None:
        counts = {("x",): 1, ("y",): 1}
        problem = build_threshold_problem(counts, {("a",), ("b",)}, "abc", capacity=None)
        with self.assertRaises(CertificateContradiction):
            assess_optimum(
                problem,
                {"x": "a", "y": "c"},
                1,
                certificate=self._certificate(problem, 1),
                node_budget_per_query=None,
            )


if __name__ == "__main__":
    unittest.main()
