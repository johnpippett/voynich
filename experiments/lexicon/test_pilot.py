"""Focused tests for the bounded lexicon pilot helpers."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock


from experiments.lexicon import run_pilot


class PilotTests(unittest.TestCase):
    def test_objective_weights_use_token_and_type_terms(self) -> None:
        counts = {("c00",): 2, ("c01",): 1}

        weights, token_count, type_count, denominator = run_pilot.objective_weights(
            counts
        )

        self.assertEqual((token_count, type_count, denominator), (3, 2, 12))
        self.assertEqual(weights, {("c00",): 7, ("c01",): 5})
        self.assertEqual(sum(weights.values()), denominator)

    def test_branch_order_uses_weighted_type_presence_and_symbol_tie(self) -> None:
        counts = {
            ("c01", "c00"): 5,
            ("c02",): 1,
            ("c00",): 1,
        }

        order = run_pilot.branch_symbol_order(counts)

        self.assertEqual(order, ("c00", "c01", "c02"))

    def test_solver_fit_uses_the_declared_token_type_objective(self) -> None:
        counts = {("c00",): 2, ("c01",): 1}

        solver_result = run_pilot.fit_ciphertext(
            counts,
            {"a", "b"},
            node_budget=100,
        )
        objective = run_pilot.objective_summary(
            counts,
            solver_result["key"],
            {"a", "b"},
        )

        self.assertEqual(solver_result["score"], objective["score_from_key"])
        self.assertEqual(objective["weights_total"], objective["denominator"])
        self.assertTrue(
            run_pilot.score_proof(solver_result, objective)[
                "derived_score_matches_solver"
            ]
        )

    def test_unmapped_units_are_counted_without_key_repairs(self) -> None:
        words = [("c00", "c01"), ("c02",), ("c00", "c01")]

        result = run_pilot.lexicon_hits(words, {"c00": "a"}, {"ab"})

        self.assertEqual(result["token_count"], 3)
        self.assertEqual(result["type_count"], 2)
        self.assertEqual(result["mapped_token_count"], 0)
        self.assertEqual(result["unmapped_token_count"], 3)
        self.assertEqual(result["unmapped_type_count"], 2)
        self.assertEqual(result["unmapped_symbol_occurrences"], 3)
        self.assertEqual(result["token_hits"], 0)
        self.assertEqual(result["type_hits"], 0)

    def test_zero_objective_denominator_is_none(self) -> None:
        objective = run_pilot.objective_summary({}, {}, set())

        self.assertIsNone(objective["denominator"])
        self.assertIsNone(objective["normalized_score"])
        self.assertEqual(objective["fit_hits"]["token_hit_rate"], None)
        self.assertEqual(objective["fit_hits"]["type_hit_rate"], None)

    def test_key_record_is_frozen_before_scorer_runs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            key_path = Path(directory) / "pilot.keys.json"
            events: list[bool] = []

            def scorer() -> dict[str, bool]:
                events.append(key_path.exists())
                return {"scored": True}

            key_hash, result = run_pilot.freeze_key_then_score(
                key_path,
                {"key": {"c00": "a"}},
                scorer,
            )

            self.assertEqual(events, [True])
            self.assertEqual(result, {"scored": True})
            self.assertEqual(
                key_hash,
                hashlib.sha256(key_path.read_bytes()).hexdigest(),
            )

    def test_reference_fit_does_not_pass_oracle_key_to_solver(self) -> None:
        counts = {("c00", "c01"): 2, ("c01", "c00"): 1}
        calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

        def fake_solver(*args: object, **kwargs: object) -> dict[str, object]:
            calls.append((args, kwargs))
            return {
                "status": "bound_certified",
                "score_certified": True,
                "search_exhausted": False,
                "feasible": True,
                "key": {"c00": "a", "c01": "b"},
                "cipher_alphabet": ["c00", "c01"],
            }

        with mock.patch.object(run_pilot, "solve_lexicon", fake_solver):
            run_pilot.fit_ciphertext(counts, {"ab", "ba"}, node_budget=4)

        self.assertEqual(len(calls), 1)
        args, kwargs = calls[0]
        self.assertEqual(
            args[0],
            {
                ("c00", "c01"): 7,
                ("c01", "c00"): 5,
            },
        )
        self.assertNotIn("initial_key", kwargs)
        self.assertNotIn("oracle_key", kwargs)
        self.assertEqual(kwargs["symbol_order"], ("c00", "c01"))
        self.assertEqual(kwargs["bound_engine"], "bitset")

    def test_pinned_source_verification_accepts_matching_hash(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "data/raw").mkdir(parents=True)
            source = root / "data/raw/ZL3b-n.txt"
            source.write_bytes(b"synthetic")
            digest = hashlib.sha256(source.read_bytes()).hexdigest()
            (root / "data/source_manifest.json").write_text(
                json.dumps(
                    {"sources": [{"path": "data/raw/ZL3b-n.txt", "sha256": digest}]}
                )
            )

            hashes = run_pilot.verify_pinned_source(root, "ZL3b-n.txt")

            self.assertEqual(hashes["source_sha256"], digest)
            with self.assertRaises(ValueError):
                source.write_bytes(b"changed")
                run_pilot.verify_pinned_source(root, "ZL3b-n.txt")

    def test_reference_test_score_counts_unmapped_characters(self) -> None:
        result = run_pilot.exact_reference_test_score(
            ["ab", "c"],
            {"a": "c00", "b": "c01", "c": "c02"},
            {"c00": "a", "c01": "b"},
            {"ab"},
        )

        self.assertEqual(result["total_word_count"], 2)
        self.assertEqual(result["exact_word_correct"], 1)
        self.assertEqual(result["fully_mapped_token_count"], 1)
        self.assertEqual(result["unmapped_token_count"], 1)
        self.assertEqual(result["unmapped_symbol_occurrences"], 1)
        self.assertEqual(result["exact_character_correct"], 2)
        self.assertEqual(result["total_character_units"], 3)
        self.assertAlmostEqual(result["exact_character_accuracy"], 2 / 3)

    def test_reference_test_score_keeps_mapped_characters_in_partial_word(self) -> None:
        result = run_pilot.exact_reference_test_score(
            ["ab"],
            {"a": "c00", "b": "c01"},
            {"c00": "a"},
            {"ab"},
        )

        self.assertEqual(result["exact_character_correct"], 1)
        self.assertEqual(result["total_character_units"], 2)
        self.assertEqual(result["exact_word_correct"], 0)
        self.assertEqual(result["unmapped_token_count"], 1)
        self.assertAlmostEqual(result["exact_character_accuracy"], 1 / 2)

    def test_parser_defaults_to_bitset_bound_engine(self) -> None:
        args = run_pilot.build_parser().parse_args(
            [
                "--kind",
                "reference",
                "--language",
                "latin_llct",
                "--node-budget",
                "0",
                "--output",
                "result.json",
            ]
        )

        self.assertEqual(args.bound_engine, "bitset")
        self.assertEqual(args.source, "ZL3b-n.txt")

    def test_existing_output_and_key_are_refused(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "pilot.json"
            key = run_pilot.output_key_path(output)
            output.write_text("{}")
            with self.assertRaises(FileExistsError):
                run_pilot.refuse_existing_outputs(output, key)
            output.unlink()
            key.write_text("{}")
            with self.assertRaises(FileExistsError):
                run_pilot.refuse_existing_outputs(output, key)


if __name__ == "__main__":
    unittest.main()
