"""Behavioral tests for the public aggregate-result exporter."""

from __future__ import annotations

import copy
import json
import pathlib
import sys
import tempfile
import unittest


PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from voynich.export import export_result
from scripts.export_results import main as export_main


def _result_fixture() -> dict:
    return {
        "status": "exploratory_not_deciphered",
        "provenance": {
            "source_path": "/synthetic/private/fixture.txt",
            "source_sha256": "a" * 64,
            "created_utc": "2026-09-16T00:00:00+00:00",
            "python": "3.14.7",
            "package_version": "0.1.0",
            "code_sha256": {"src/voynich/structure.py": "b" * 64},
            "design_sha256": "c" * 64,
        },
        "config": {
            "seed": 408,
            "uncertain_spaces": "split",
            "input_path": "/synthetic/private/fixture.txt",
        },
        "structure": {
            "inventory": {
                "records": 12,
                "folios": 3,
                "tokens": 42,
                "word_length_histogram": {1: 2, 4: 40},
                "groups": {"H": {"records": 12, "tokens": 42}},
                "h1_bits_per_eva_character": 3.2,
                "h2_bits_per_eva_character": 1.8,
                "top_tokens": [("qokedy", 9)],
            },
            "config": {"permutations": 19, "null": "within-line shuffle"},
            "word_order_sample": {"lines": 5, "tokens": 42},
            "word_order_tests": {"adjacent_near": {"observed": 0.25, "p_value": 0.2}},
            "models": {"secret": {"vocabulary": ["qokedy"]}},
        },
        "predictive": {
            "config": {"seed": 408, "model": {"orders": [0, 1, 2, 3]}},
            "counts": {"records": {"train": 8, "test": 4}},
            "split_manifest": {
                "train": {"leaves": ["1"], "folios": ["f1r"]},
                "validation": {"leaves": ["2"], "folios": ["f2r"]},
                "test": {"leaves": ["7"], "folios": ["f7r"]},
            },
            "models": {
                "observed": {"raw_eva": {"order_3": {"vocabulary": ["qokedy"]}}}
            },
            "scores": {
                "observed": {
                    "raw_eva": {
                        "order_0": {
                            "bits_per_symbol": 1.25,
                            "eos_count": 4,
                            "symbol_counts": {"a": 10, "<EOS>": 4},
                        }
                    },
                    "decoded_variant": {
                        "symbol_counts": {"decoded_word": 1},
                    },
                }
            },
            "interpretation": {"does_not_measure": ["language identity", "meaning"]},
        },
        "context": {
            "config": {"seed": 408, "bootstraps": 19},
            "counts": {"records": {"train": 8, "test": 4}},
            "split_manifest": {
                "manifest_hash": "d" * 64,
                "train": {"leaves": ["1"], "folios": ["f1r"]},
                "test": {"leaves": ["7"], "folios": ["f7r"]},
            },
            "split_manifest_hash": "d" * 64,
            "models": {"original": {"vocabulary": ["qokedy"]}},
            "scores": {"test": {"unigram": {"bits_per_word": 2.5}}},
            "per_leaf_score_sums": {"7": {"targets": 4, "bits": 10.0}},
            "bootstrap": {"draws": 19, "interval": [1.0, 3.0]},
            "caution": "This score does not establish a translation.",
        },
        "records": [{"folio": "f7r", "text_raw": "qokedy", "tokens": ["qokedy"]}],
    }


class ExportResultTests(unittest.TestCase):
    def test_export_selects_aggregates_and_strips_raw_or_model_data(self) -> None:
        result = _result_fixture()

        exported = export_result(result)
        self.assertIn("provenance", exported)
        self.assertIn("predictive", exported)
        encoded = json.dumps(exported, ensure_ascii=False, sort_keys=True)

        self.assertEqual(exported["provenance"]["source_path"], "fixture.txt")
        self.assertNotIn("/synthetic/private", encoded)
        self.assertNotIn("qokedy", encoded)
        self.assertNotIn("top_tokens", encoded)
        self.assertNotIn("records", exported)
        self.assertNotIn("models", encoded)
        self.assertNotIn("vocabulary", encoded)
        self.assertNotIn("decoded_word", encoded)
        self.assertIn("symbol_counts", exported["predictive"]["scores"]["observed"]["raw_eva"]["order_0"])

    def test_export_preserves_scalar_metrics_and_split_identity(self) -> None:
        exported = export_result(_result_fixture())

        self.assertIn("structure", exported)
        self.assertIn("context", exported)
        self.assertEqual(exported["structure"]["inventory"]["tokens"], 42)
        self.assertEqual(exported["structure"]["inventory"]["word_length_histogram"], {1: 2, 4: 40})
        self.assertEqual(exported["predictive"]["scores"]["observed"]["raw_eva"]["order_0"]["bits_per_symbol"], 1.25)
        self.assertEqual(exported["predictive"]["split_manifest"]["test"]["folios"], ["f7r"])
        self.assertEqual(exported["context"]["split_manifest_hash"], "d" * 64)
        self.assertEqual(exported["context"]["per_leaf_score_sums"]["7"]["targets"], 4)

    def test_export_does_not_mutate_input(self) -> None:
        result = _result_fixture()
        before = copy.deepcopy(result)

        export_result(result)

        self.assertEqual(result, before)

    def test_script_writes_report_and_requires_replace_for_existing_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            run = root / "fixture-run"
            run.mkdir()
            (run / "analysis.json").write_text(
                json.dumps(_result_fixture()), encoding="utf-8"
            )
            reports = root / "reports"

            self.assertEqual(export_main(["--reports-dir", str(reports), str(run)]), 0)
            output = reports / "fixture-run.json"
            self.assertTrue(output.is_file())
            self.assertEqual(json.loads(output.read_text())["status"], "exploratory_not_deciphered")
            self.assertEqual(
                export_main(["--reports-dir", str(reports), str(run)]), 2
            )
            self.assertEqual(
                export_main(["--reports-dir", str(reports), "--replace", str(run)]), 0
            )


if __name__ == "__main__":
    unittest.main()
