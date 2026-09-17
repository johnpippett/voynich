"""Synthetic tests for the bounded optimal-set study runner."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from experiments.optimal_set.enumerate import (
    _objective_domain_fingerprint,
    enumerate_equal_score_completions,
)
from experiments.optimal_set.run_study import (
    _candidate_test_diagnostics,
    run_study,
    validate_query_records,
)
from experiments.optimal_set.secondary import rank_secondary


def _fixture() -> dict:
    counts = {"x": 1}
    lexicon = ["a", "b"]
    alphabet = "ab"
    fingerprint = _objective_domain_fingerprint(
        {("x",): 1}, {tuple(word) for word in lexicon}, tuple(alphabet), 2
    )
    return {
        "primary_counts": counts,
        "training_words": lexicon,
        "validation_cipher_counts": counts,
        "plaintext_alphabet": alphabet,
        "capacity": 2,
        "fixed_assignments": {},
        "ambiguous_units": ["x"],
        "baseline_key": {"x": "a"},
        "target": 1,
        "objective_domain_fingerprint": fingerprint,
        "provenance": {
            "source_hashes": {"synthetic-source": "a" * 64},
            "protocol_hashes": {"synthetic-protocol": "b" * 64},
        },
    }


class RunnerTests(unittest.TestCase):
    def test_complete_tie_writes_selection_before_guarded_test(self):
        fixture = _fixture()
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "run"
            seen: list[tuple[str, bool]] = []

            def test_iterator(selection_path: Path):
                seen.append((selection_path.name, selection_path.exists()))
                self.assertTrue(selection_path.exists())
                return iter(("synthetic-test",))

            def diagnostic_scorer(items, selection):
                self.assertEqual(tuple(items), ("synthetic-test",))
                self.assertEqual(selection["maximizer_indices"], [0, 1])
                return {"items_seen": 1}

            result = run_study(
                output_dir=output,
                **fixture,
                test_iterator=test_iterator,
                diagnostic_scorer=diagnostic_scorer,
            )

            self.assertEqual(result["status"], "complete")
            self.assertEqual(seen, [("selection.json", True)])
            self.assertEqual(
                [path.name for path in sorted(output.iterdir())],
                ["enumeration.json", "input.json", "ranking.json", "result.json", "selection.json"],
            )
            selection = json.loads((output / "selection.json").read_bytes())
            self.assertEqual(selection["maximizer_indices"], [0, 1])
            self.assertEqual(selection["baseline_index"], 0)
            self.assertEqual(result["diagnostics"], {"items_seen": 1})
            input_record = json.loads((output / "input.json").read_bytes())
            self.assertIn("model_hash", input_record)
            self.assertEqual(input_record["model_settings"]["order"], 3)
            self.assertNotIn("context_counts", input_record)
            self.assertNotIn("test_words", input_record)

    def test_partial_enumeration_is_retained_and_never_ranked(self):
        fixture = _fixture()
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "partial"
            result = run_study(output_dir=output, **fixture, max_product=1)
            self.assertEqual(result["status"], "not_complete")
            self.assertIn("product", result["reason"])
            self.assertTrue((output / "input.json").exists())
            self.assertTrue((output / "enumeration.json").exists())
            self.assertTrue((output / "result.json").exists())
            self.assertFalse((output / "ranking.json").exists())
            self.assertFalse((output / "selection.json").exists())

    def test_certificate_conflict_is_reported_without_ranking(self):
        fixture = _fixture()
        fixture["target"] = 0
        fixture["baseline_key"] = {"x": "a"}
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "conflict"
            result = run_study(output_dir=output, **fixture)
            self.assertEqual(result["status"], "contradiction")
            self.assertEqual(result["reason"], "certificate_conflict")
            self.assertTrue((output / "enumeration.json").exists())
            self.assertFalse((output / "ranking.json").exists())

    def test_existing_output_is_never_overwritten(self):
        fixture = _fixture()
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "run"
            output.mkdir()
            marker = output / "marker"
            marker.write_text("keep\n")
            with self.assertRaises(FileExistsError):
                run_study(output_dir=output, **fixture)
            self.assertEqual(marker.read_text(), "keep\n")

    def test_incomplete_ranking_is_retained_without_selection(self):
        fixture = _fixture()

        def incomplete_ranker(*args, **kwargs):
            return {
                "status": "not_complete",
                "reason": "ratio_limit",
                "candidate_count": 99,
                "maximizer_indices": [],
            }

        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "rank-limit"
            result = run_study(output_dir=output, **fixture, ranker=incomplete_ranker)
            self.assertEqual(result["status"], "not_complete")
            self.assertEqual(result["reason"], "ratio_limit")
            self.assertTrue((output / "ranking.json").exists())
            self.assertTrue((output / "result.json").exists())
            self.assertFalse((output / "selection.json").exists())
            ranking = json.loads((output / "ranking.json").read_bytes())
            self.assertEqual(ranking["candidate_count"], 99)
            self.assertEqual(ranking["input_candidate_count"], 2)

    def test_query_validation_rejects_malformed_records(self):
        expected = {"x"}
        valid = {
            "cipher_unit": "x",
            "classification": "forced_at_certified_optimum",
            "forbidden": {"x": ["a"]},
            "objective_domain_fingerprint": "f" * 64,
            "raw_query": {
                "cipher_unit": "x",
                "target": 1,
                "problem_fingerprint": "f" * 64,
                "objective_domain_fingerprint": "f" * 64,
                "config": {"capacity": 2},
                "constraints": {},
                "forbidden": {"x": ["a"]},
                "status": "infeasible",
                "upper_bound": 0,
                "search_exhausted": True,
                "feasible": False,
                "infeasible": True,
                "proof_kind": "search_exhausted_no_witness",
                "key": None,
                "score": None,
                "lower_bound": 0,
                "frontier_node_count": 0,
                "node_budget": 10,
            },
        }
        validated = validate_query_records(
            [valid], expected_units=expected, target=1,
            objective_domain_fingerprint="f" * 64, capacity=2,
        )
        self.assertEqual(validated["fixed_assignments"], {"x": "a"})
        strict = validate_query_records(
            [valid], expected_units=expected, target=1,
            objective_domain_fingerprint="f" * 64, capacity=2,
            expected_node_budget=10, require_exhausted_proof=True,
        )
        self.assertEqual(strict["fixed_assignments"], {"x": "a"})
        for mutation in (
            lambda record: record.update(cipher_unit="bad"),
            lambda record: record["raw_query"].update(cipher_unit="bad"),
            lambda record: record.update(objective_domain_fingerprint="0" * 64),
            lambda record: record["raw_query"].update(upper_bound=1),
            lambda record: record["raw_query"].update(constraints={"x": "a"}),
            lambda record: record["raw_query"].update(config={"capacity": 1}),
        ):
            with self.subTest(mutation=mutation):
                record = deepcopy(valid)
                mutation(record)
                with self.assertRaises(ValueError):
                    validate_query_records(
                        [record], expected_units=expected, target=1,
                        objective_domain_fingerprint="f" * 64, capacity=2,
                    )
        strict_bad = deepcopy(valid)
        strict_bad["raw_query"]["feasible"] = True
        with self.assertRaises(ValueError):
            validate_query_records(
                [strict_bad], expected_units=expected, target=1,
                objective_domain_fingerprint="f" * 64, capacity=2,
                expected_node_budget=10, require_exhausted_proof=True,
            )

    def test_run_study_requires_proof_for_direct_fixed_assignments(self):
        fixture = _fixture()
        fixture["fixed_assignments"] = {"x": "a"}
        fixture["ambiguous_units"] = []
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaises(ValueError):
                run_study(output_dir=Path(temporary) / "unproved", **fixture)

    def test_run_study_rejects_status_labels_without_forced_proof(self):
        fixture = _fixture()
        fingerprint = fixture["objective_domain_fingerprint"]
        fixture["query_records"] = [
            {
                "cipher_unit": "x",
                "classification": "forced_at_certified_optimum",
                "forbidden": {"x": ["a"]},
                "incumbent_letter": "a",
                "objective_domain_fingerprint": fingerprint,
                "raw_query": {
                    "cipher_unit": "x",
                    "query_target": 1,
                    "problem_fingerprint": fingerprint,
                    "objective_domain_fingerprint": fingerprint,
                    "capacity": 2,
                    "constraints": {},
                    "forbidden": {"x": ["a"]},
                    "status": "infeasible",
                    "upper_bound": 0,
                    "search_exhausted": True,
                    "node_budget": 10,
                },
            }
        ]
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaises(ValueError):
                run_study(output_dir=Path(temporary) / "labels-only", **fixture)

    def test_node_budget_accepts_only_nonnegative_int_or_none(self):
        fixture = _fixture()
        for value in (True, -1, "100"):
            with self.subTest(value=value), tempfile.TemporaryDirectory() as temporary:
                with self.assertRaises(ValueError):
                    run_study(
                        output_dir=Path(temporary) / "bad-budget",
                        **fixture,
                        node_budget=value,
                    )
        with tempfile.TemporaryDirectory() as temporary:
            result = run_study(
                output_dir=Path(temporary) / "unlimited-budget",
                **fixture,
                node_budget=None,
            )
            self.assertEqual(result["status"], "complete")

    def test_unseen_test_units_are_counted_as_errors(self):
        diagnostics = _candidate_test_diagnostics(
            0,
            {"x": "a"},
            [(('x', 'y'), "ab")],
            {"x": "a", "y": "b"},
            True,
        )
        self.assertEqual(diagnostics["test_positions"], 2)
        self.assertEqual(diagnostics["test_observed_positions"], 1)
        self.assertEqual(diagnostics["test_correct"], 1)
        self.assertEqual(diagnostics["test_errors"], 1)
        self.assertEqual(diagnostics["test_unseen_positions"], 1)
        self.assertEqual(diagnostics["test_unseen_units"], ["y"])
        self.assertEqual(diagnostics["test_word_correct"], 0)

    def test_unresolved_query_keeps_one_letter_exclusion_and_unknown_status(self):
        record = {
            "cipher_unit": "x",
            "classification": "unresolved",
            "forbidden": {"x": ["a"]},
            "incumbent_letter": "a",
            "objective_domain_fingerprint": "f" * 64,
            "raw_query": {
                "cipher_unit": "x",
                "target": 1,
                "problem_fingerprint": "f" * 64,
                "objective_domain_fingerprint": "f" * 64,
                "config": {"capacity": 2},
                "constraints": {},
                "forbidden": {"x": ["a"]},
                "status": "unknown",
            },
        }
        validated = validate_query_records(
            [record], expected_units={"x"}, target=1,
            objective_domain_fingerprint="f" * 64, capacity=2,
        )
        self.assertEqual(validated["unresolved_units"], ("x",))

    def test_ambiguous_query_requires_a_scored_alternative_witness(self):
        record = {
            "cipher_unit": "x",
            "classification": "ambiguous",
            "forbidden": {"x": ["a"]},
            "incumbent_letter": "a",
            "objective_domain_fingerprint": "f" * 64,
            "raw_query": {
                "cipher_unit": "x",
                "target": 1,
                "problem_fingerprint": "f" * 64,
                "objective_domain_fingerprint": "f" * 64,
                "config": {"capacity": 2},
                "constraints": {},
                "forbidden": {"x": ["a"]},
                "status": "feasible",
                "feasible": True,
                "key": {"x": "b"},
                "score": 0,
            },
        }
        with self.assertRaises(ValueError):
            validate_query_records(
                [record], expected_units={"x"}, target=1,
                objective_domain_fingerprint="f" * 64, capacity=2,
                plaintext_alphabet="ab", cipher_counts={"x": 1},
                plaintext_lexicon=["a", "b"],
            )

    def test_complete_enumeration_metadata_is_checked_before_ranking(self):
        fixture = _fixture()

        def bad_enumerator(*args, **kwargs):
            result = enumerate_equal_score_completions(*args, **kwargs)
            result["complete"] = False
            return result

        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaises(ValueError):
                run_study(
                    output_dir=Path(temporary) / "bad-enum",
                    **fixture,
                    enumerator=bad_enumerator,
                )
            self.assertTrue((Path(temporary) / "bad-enum" / "enumeration.json").exists())
            self.assertFalse((Path(temporary) / "bad-enum" / "selection.json").exists())

    def test_complete_ranking_must_cover_and_reconstruct_all_ties(self):
        fixture = _fixture()

        def bad_ranker(*args, **kwargs):
            result = rank_secondary(*args, **kwargs)
            result["candidate_results"] = result["candidate_results"][:-1]
            return result

        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaises(ValueError):
                run_study(
                    output_dir=Path(temporary) / "bad-rank",
                    **fixture,
                    ranker=bad_ranker,
                )
            self.assertTrue((Path(temporary) / "bad-rank" / "ranking.json").exists())
            self.assertFalse((Path(temporary) / "bad-rank" / "selection.json").exists())

    def test_complete_ranking_checks_ratio_baseline_and_definition(self):
        fixture = _fixture()
        mutations = {
            "canonical_index": lambda result: result.update(canonical_candidate_index=1),
            "canonical_ratio": lambda result: result["candidate_results"][0].update(
                likelihood_ratio={
                    "numerator_hex": "0x2",
                    "denominator_hex": "0x1",
                    "numerator_bits": 2,
                    "denominator_bits": 1,
                }
            ),
            "ratio_definition": lambda result: result["config"].update(
                ratio_definition="candidate likelihood divided by two"
            ),
        }
        for name, mutation in mutations.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary:
                def bad_ranker(*args, _mutation=mutation, **kwargs):
                    result = rank_secondary(*args, **kwargs)
                    _mutation(result)
                    return result

                with self.assertRaises(ValueError):
                    run_study(
                        output_dir=Path(temporary) / name,
                        **fixture,
                        ranker=bad_ranker,
                    )

    def test_fingerprint_and_provenance_hashes_are_checked(self):
        fixture = _fixture()
        with tempfile.TemporaryDirectory() as temporary:
            for label, field, bad in (
                ("objective_domain_fingerprint", "objective_domain_fingerprint", "0" * 64),
                ("provenance", "provenance", {"source_hashes": {"synthetic-source": "0" * 63}}),
                (
                    "absolute_provenance_path",
                    "provenance",
                    {
                        "source_hashes": {"/tmp/private-source": "a" * 64},
                        "protocol_hashes": {"synthetic-protocol": "b" * 64},
                    },
                ),
            ):
                with self.subTest(field=label):
                    changed = deepcopy(fixture)
                    changed[field] = bad
                    with self.assertRaises(ValueError):
                        run_study(output_dir=Path(temporary) / label, **changed)


if __name__ == "__main__":
    unittest.main()
