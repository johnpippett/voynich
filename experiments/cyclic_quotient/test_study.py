"""Synthetic tests for the ciphertext-only cyclic quotient study core."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from experiments.homophonic.solver import solve_lexicon as real_solver

from . import study


UNITS = ("a", "b", "c", "d")
VALIDATION = (
    ("a", "b", "a", "b", "a", "c", "d", "c", "d", "c"),
    ("b", "a", "b", "a", "b", "d", "c", "d", "c", "d"),
)
TRAIN = ("aaaaabbbbb",)


class QuotientStudyTests(unittest.TestCase):
    def run_study(self, directory: Path, **kwargs):
        return study.run_study(
            kwargs.pop("units", UNITS),
            kwargs.pop("validation", VALIDATION),
            kwargs.pop("train", TRAIN),
            directory,
            **kwargs,
        )

    def test_ambiguous_quotient_abstains_without_fitter(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            with patch.object(study, "solve_lexicon", side_effect=AssertionError):
                result = self.run_study(
                    output,
                    units=("a", "b", "x", "y"),
                    validation=(("a", "b"),),
                )
            self.assertEqual(result["status"], "abstained")
            self.assertEqual(result["quotient_status"], "ambiguous")
            self.assertIsNone(result["fit"])
            self.assertTrue((output / "quotient.json").is_file())
            self.assertFalse((output / "fit.json").exists())
            evidence = json.loads((output / "quotient.json").read_text())
            self.assertEqual(evidence["quotient_status"], "ambiguous")
            self.assertEqual(
                evidence["compatibility_graph"]["status"],
                "complete_declared_graph",
            )
            self.assertEqual(
                evidence["residual_graph"]["status"],
                "not_constructed_without_proved_quotient",
            )
            self.assertIsNone(evidence["completion_representation"])
            self.assertNotIn("partitions", evidence)
            self.assertNotIn("validation_cipher_words", evidence)

    def test_infeasible_quotient_abstains_without_fitter(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            with patch.object(study, "solve_lexicon", side_effect=AssertionError):
                result = self.run_study(
                    output,
                    validation=(("a", "a", "b", "b"),),
                )
            self.assertEqual(result["status"], "abstained")
            self.assertEqual(result["quotient_status"], "infeasible")
            self.assertIsNone(result["fit"])
            self.assertFalse((output / "fit.keys.json").exists())

    def test_unknown_quotient_abstains_without_fitter(self) -> None:
        units = tuple("abcdefgh")
        validation = (("g", "b", "h", "f", "d", "b", "g", "h", "f"),)
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            with patch.object(study, "QUOTIENT_NODE_BUDGET", 4):
                with patch.object(study, "solve_lexicon", side_effect=AssertionError):
                    result = self.run_study(
                        output,
                        units=units,
                        validation=validation,
                    )
            self.assertEqual(result["status"], "abstained")
            self.assertEqual(result["quotient_status"], "unknown_budget")
            self.assertIsNone(result["fit"])

    def test_proved_quotient_fits_and_persists_induced_key(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            seen = {}

            def fitter(*args, **kwargs):
                seen["args"] = args
                seen["kwargs"] = kwargs
                self.assertTrue((output / "quotient.json").is_file())
                self.assertFalse((output / "fit.keys.json").exists())
                return real_solver(*args, **kwargs)

            with patch.object(study, "solve_lexicon", side_effect=fitter):
                result = self.run_study(output)

            self.assertEqual(result["quotient_status"], "proved")
            self.assertTrue(result["feasible"])
            self.assertTrue(result["verified"])
            self.assertLessEqual(result["lower_bound"], result["upper_bound"])
            self.assertEqual(result["verified_counts"]["validation_tokens"], 2)
            self.assertEqual(result["verified_counts"]["validation_types"], 2)
            self.assertEqual(result["objective"]["N_token_count"], 2)
            self.assertEqual(result["objective"]["T_type_count"], 1)
            self.assertEqual(result["objective"]["denominator"], 4)
            self.assertEqual(result["objective"]["weights_total"], 4)
            self.assertEqual(seen["kwargs"]["capacity"], 1)
            self.assertEqual(seen["kwargs"]["bound_engine"], "bitset")
            self.assertEqual(seen["kwargs"]["node_budget"], 100_000)
            self.assertNotIn("initial_key", seen["kwargs"])
            self.assertEqual(seen["args"][2], "abcdefghijklmnopqrstuvwxyz")

            key = json.loads((output / "fit.keys.json").read_text())
            self.assertEqual(key["class_key"], {"a+b": "a", "c+d": "b"})
            self.assertEqual(
                key["observed_unit_key"],
                {"a": "a", "b": "a", "c": "b", "d": "b"},
            )
            self.assertEqual(key["class_key"], {
                key["class_names"][0]: key["class_key"][key["class_names"][0]],
                key["class_names"][1]: key["class_key"][key["class_names"][1]],
            })
            fit = json.loads((output / "fit.json").read_text())
            quotient_hash = hashlib.sha256(
                (output / "quotient.json").read_bytes()
            ).hexdigest()
            self.assertEqual(key["quotient_evidence_sha256"], quotient_hash)
            self.assertEqual(fit["quotient_evidence_sha256"], quotient_hash)
            self.assertEqual(key["open_slot_count"], 0)
            self.assertEqual(fit["open_slot_count"], 0)
            self.assertNotIn("candidate_counts", fit)
            self.assertNotIn("validation_cipher_words", fit)

    def test_persisted_open_slot_count_for_singleton_class(self) -> None:
        units = ("a", "b", "c", "d", "e", "f")
        validation = ((
            "a", "b", "a", "b", "a", "c", "d", "c", "d", "c", "e",
        ),)
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            result = self.run_study(
                output,
                units=units,
                validation=validation,
                train=("aaabbbx",),
            )
            self.assertTrue(result["verified"])
            key = json.loads((output / "fit.keys.json").read_text())
            fit = json.loads((output / "fit.json").read_text())
            self.assertEqual(key["open_slot_count"], 1)
            self.assertEqual(fit["open_slot_count"], 1)

    def test_persists_complete_and_residual_candidate_graphs(self) -> None:
        units = ("a", "b", "c", "d", "e", "x", "y", "z")
        validation = ((
            "a", "b", "a", "b", "a", "c", "d", "c", "d", "c", "e",
        ),)

        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            result = self.run_study(
                output,
                units=units,
                validation=validation,
                train=("aaabbbx",),
            )

            self.assertEqual(result["quotient_status"], "proved")
            evidence = json.loads((output / "quotient.json").read_text())
            complete = evidence["compatibility_graph"]
            self.assertEqual(complete["vertices"], list(units))
            expected_edges = [
                ["a", "b"], ["c", "d"], ["e", "x"], ["e", "y"],
                ["e", "z"], ["x", "y"], ["x", "z"], ["y", "z"],
            ]
            self.assertEqual(complete["edges"], expected_edges)
            self.assertEqual(
                {tuple(item["edge"]) for item in complete["edge_orientations"]},
                {tuple(edge) for edge in expected_edges},
            )
            self.assertEqual(
                {
                    tuple(item["edge"]): tuple(item["partition_starts"])
                    for item in complete["edge_orientations"]
                },
                {
                    ("a", "b"): ("a",),
                    ("c", "d"): ("c",),
                    ("e", "x"): ("e",),
                    ("e", "y"): ("e",),
                    ("e", "z"): ("e",),
                    ("x", "y"): (None,),
                    ("x", "z"): (None,),
                    ("y", "z"): (None,),
                },
            )

            residual = evidence["residual_graph"]
            self.assertEqual(residual["status"], "all_candidate_edges")
            self.assertEqual(residual["vertices"], ["e", "x", "y", "z"])
            self.assertEqual(
                residual["edges"], expected_edges[2:],
            )
            self.assertEqual(
                {tuple(item["edge"]) for item in residual["edge_orientations"]},
                {tuple(edge) for edge in expected_edges[2:]},
            )
            self.assertEqual(
                evidence["completion_representation"],
                "all residual full perfect matchings plus forced observed pairs",
            )
            self.assertEqual(
                evidence["forced_observed_observed_edges"], [["a", "b"], ["c", "d"]],
            )
            self.assertFalse(evidence["selected_unseen_mate"])
            self.assertNotIn("validation_cipher_words", evidence)

    def test_outputs_are_exclusive(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            self.run_study(output)
            with self.assertRaises(FileExistsError):
                self.run_study(output)

    def test_rejects_uncovered_cipher_unit_and_non_ascii_training(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            with self.assertRaises(ValueError):
                self.run_study(output, validation=(("a", "z"),))
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            with self.assertRaises(ValueError):
                self.run_study(output, train=("Aa",))


if __name__ == "__main__":
    unittest.main()
