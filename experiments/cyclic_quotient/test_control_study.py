"""Synthetic tests for the source-bound cyclic quotient runner."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from experiments.homophonic.controls import seeded_control_key

from . import control_study as runner


def _source_data() -> dict[str, object]:
    metadata = {
        "reference_manifest_sha256": "a" * 64,
        "source_files": {
            "synthetic.conllu": {"sha256": "b" * 64},
        },
    }
    return {
        "latin_llct": {
            "words": {
                "train": ["ab", "ba"],
                "validation": ["ab", "aa"],
                "test": ["ba", "abc"],
            },
            "metadata": metadata,
        },
    }


def _freeze_data() -> dict[str, object]:
    return {
        "manifest_sha256": "c" * 64,
        "files": [
            {"path": "src/voynich/reference.py", "sha256": "d" * 64},
            {"path": "experiments/homophonic/controls.py", "sha256": "e" * 64},
        ],
    }


def _write_json(path: Path, value: object) -> str:
    encoded = (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(encoded)
    return hashlib.sha256(encoded).hexdigest()


def _write_fit_outputs(
    output: Path,
    planted: dict[str, object],
    *,
    status: str = "bound_certified",
) -> None:
    observed = ("c00", "c01")
    unseen = tuple(f"c{index:02d}" for index in range(2, 52))
    quotient = {
        "protocol": runner.PROTOCOL,
        "record_kind": "aggregate_cyclic_quotient_evidence",
        "quotient_status": "proved",
        "declared_units": list(runner.UNITS),
        "declared_unit_count": 52,
        "declared_units_sha256": runner.canonical_hash(list(runner.UNITS)),
        "observed_units": list(observed),
        "unseen_units": list(unseen),
        "observed_unit_count": 2,
        "unseen_unit_count": 50,
        "classes": [list(observed)],
    }
    quotient_hash = _write_json(output / runner.QUOTIENT_FILENAME, quotient)
    letter = planted["cipher_to_plain"]["c00"]
    key = {
        "protocol": runner.PROTOCOL,
        "record_kind": "complete_observed_quotient_key",
        "quotient_status": "proved",
        "quotient_evidence_sha256": quotient_hash,
        "class_names": ["c00+c01"],
        "class_members": {"c00+c01": list(observed)},
        "class_key": {"c00+c01": letter},
        "observed_unit_key": {unit: letter for unit in observed},
        "open_slot_count": 0,
        "coverage": {
            "declared_unit_count": 52,
            "observed_unit_count": 2,
            "unseen_unit_count": 50,
            "mapped_observed_units": 2,
        },
        "fit_status": status,
        "score_certified": status in {"exhaustive", "bound_certified"},
    }
    key_hash = _write_json(output / runner.KEY_FILENAME, key)
    fit = {
        "protocol": runner.PROTOCOL,
        "status": status,
        "quotient_evidence_sha256": quotient_hash,
    }
    fit_hash = _write_json(output / runner.FIT_FILENAME, fit)
    return {
        "protocol": runner.PROTOCOL,
        "status": status,
        "quotient_status": "proved",
        "feasible": True,
        "verified": True,
        "output_hashes": {
            runner.QUOTIENT_FILENAME: quotient_hash,
            runner.KEY_FILENAME: key_hash,
            runner.FIT_FILENAME: fit_hash,
        },
    }


class ControlStudyTests(unittest.TestCase):
    def _patch_common(self, output: Path, encrypt_side_effect):
        planted = seeded_control_key("cap2", 7000)
        validation_cipher = (("c00", "c01"), ("c00", "c01"))
        stream_hash = runner.hash_cipher_partition(validation_cipher)
        return planted, patch.multiple(
            runner,
            load_reference_partitions=lambda _root: _source_data(),
            load_freeze_metadata=lambda _root: _freeze_data(),
            seeded_control_key=lambda family, seed: planted,
            encrypt_words=encrypt_side_effect,
            EXPECTED_VALIDATION_STREAM_HASHES={"latin": stream_hash},
        )

    def test_success_scores_only_after_durable_saved_key(self) -> None:
        calls: list[str] = []
        planted = seeded_control_key("cap2", 7000)
        pure_records: dict[str, tuple[bytes, str]] = {}

        def encrypt(words, _key):
            phase = "validation" if len(words) == 2 and words[0] == "ab" else "test"
            calls.append(phase)
            if phase == "test":
                self.assertTrue((output / "latin" / runner.KEY_FILENAME).is_file())
                self.assertFalse((output / "latin" / "diagnostics.json").exists())
                return [("c00", "c01"), ("c02", "c00", "c01")]
            return [("c00", "c01"), ("c00", "c01")]

        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "results"
            patches = self._patch_common(output, encrypt)

            def fit(_units, _validation, _train, directory):
                result = _write_fit_outputs(directory, planted)
                for name in (
                    runner.QUOTIENT_FILENAME,
                    runner.KEY_FILENAME,
                    runner.FIT_FILENAME,
                ):
                    raw = (directory / name).read_bytes()
                    pure_records[name] = (raw, hashlib.sha256(raw).hexdigest())
                return result

            with patches[1]:
                with patch.object(
                    runner,
                    "run_study",
                    side_effect=fit,
                ):
                    result = runner.run_corpus(Path(temporary), "latin", output)

            self.assertEqual(result["status"], "bound_certified")
            self.assertEqual(calls, ["validation", "test"])
            diagnostics_path = output / "latin" / "diagnostics.json"
            diagnostics = json.loads(diagnostics_path.read_text())
            self.assertEqual(diagnostics["validation"]["word"]["denominator"], 2)
            self.assertEqual(diagnostics["test"]["coverage"]["unexplained_positions"], 1)
            self.assertEqual(diagnostics["test"]["coverage"]["total_positions"], 5)
            self.assertEqual(diagnostics["test"]["word"]["denominator"], 2)
            self.assertEqual(diagnostics["postfit_planted_map"]["denominator"], 2)
            self.assertEqual(diagnostics["provenance"]["source_manifest_sha256"], "a" * 64)
            self.assertEqual(diagnostics["freeze_manifest_sha256"], "c" * 64)
            for name, (raw, digest) in pure_records.items():
                path = output / "latin" / name
                self.assertEqual(path.read_bytes(), raw)
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), digest)
            encoded = diagnostics_path.read_text()
            self.assertNotIn("observed_unit_key", diagnostics)
            self.assertNotIn("class_key", diagnostics)
            self.assertNotIn("ciphertext", diagnostics)
            self.assertNotIn("words", diagnostics)

    def test_quotient_abstention_does_not_encrypt_test_or_write_diagnostics(self) -> None:
        calls: list[str] = []

        def encrypt(words, _key):
            calls.append("test" if len(words) == 2 and words[0] == "ba" else "validation")
            return [("c00", "c01"), ("c00", "c01")]

        def abstain(_units, _validation, _train, directory):
            _write_json(
                directory / runner.QUOTIENT_FILENAME,
                {"protocol": runner.PROTOCOL, "quotient_status": "ambiguous"},
            )
            return {
                "protocol": runner.PROTOCOL,
                "status": "abstained",
                "quotient_status": "ambiguous",
                "feasible": None,
                "verified": False,
            }

        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "results"
            planted, patches = self._patch_common(output, encrypt)
            del planted
            with patches:
                with patch.object(runner, "run_study", side_effect=abstain):
                    result = runner.run_corpus(Path(temporary), "latin", output)
            self.assertEqual(result["status"], "abstained")
            self.assertEqual(calls, ["validation"])
            self.assertFalse((output / "latin" / "diagnostics.json").exists())
            self.assertFalse((output / "latin" / runner.KEY_FILENAME).exists())

    def test_key_validation_failure_precedes_test_encryption(self) -> None:
        calls: list[str] = []

        def encrypt(words, _key):
            calls.append("test" if len(words) == 2 and words[0] == "ba" else "validation")
            return [("c00", "c01"), ("c00", "c01")]

        def bad_fit(_units, _validation, _train, directory):
            _write_fit_outputs(directory, seeded_control_key("cap2", 7000))
            key_path = directory / runner.KEY_FILENAME
            key = json.loads(key_path.read_text())
            key["quotient_evidence_sha256"] = "0" * 64
            _write_json(key_path, key)
            return {
                "status": "bound_certified",
                "quotient_status": "proved",
                "feasible": True,
                "verified": True,
            }

        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "results"
            _planted, patches = self._patch_common(output, encrypt)
            with patches:
                with patch.object(runner, "run_study", side_effect=bad_fit):
                    with self.assertRaises(ValueError):
                        runner.run_corpus(Path(temporary), "latin", output)
            self.assertEqual(calls, ["validation"])
            self.assertFalse((output / "latin" / "diagnostics.json").exists())

    def test_stream_pin_mismatch_stops_before_core(self) -> None:
        calls: list[str] = []

        def encrypt(_words, _key):
            calls.append("validation")
            return [("c00", "c01"), ("c00", "c01")]

        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "results"
            patches = self._patch_common(output, encrypt)
            with patches[1]:
                with patch.object(runner, "EXPECTED_VALIDATION_STREAM_HASHES", {"latin": "0" * 64}):
                    with patch.object(runner, "run_study", side_effect=AssertionError):
                        with self.assertRaises(ValueError):
                            runner.run_corpus(Path(temporary), "latin", output)
            self.assertEqual(calls, ["validation"])
            self.assertFalse((output / "latin").exists())

    def test_rejects_unknown_corpus(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaises(ValueError):
                runner.run_corpus(Path(temporary), "dante", Path(temporary) / "out")

    def test_explicit_corpus_output_is_not_nested_again(self) -> None:
        def encrypt(words, _key):
            return [("c00", "c01") for _ in words]

        def abstain(_units, _validation, _train, directory):
            _write_json(
                directory / runner.QUOTIENT_FILENAME,
                {
                    "protocol": runner.PROTOCOL,
                    "quotient_status": "ambiguous",
                    "declared_unit_count": 52,
                    "declared_units_sha256": runner.canonical_hash(list(runner.UNITS)),
                    "observed_units": [],
                    "unseen_units": list(runner.UNITS),
                    "observed_unit_count": 0,
                    "unseen_unit_count": 52,
                    "classes": [],
                },
            )
            return {"status": "abstained", "quotient_status": "ambiguous"}

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "results" / "cyclic-quotient-recovery-v1" / "latin"
            _planted, patches = self._patch_common(output, encrypt)
            with patches:
                with patch.object(runner, "run_study", side_effect=abstain):
                    runner.run_corpus(root, "latin", output)
            self.assertTrue((output / runner.QUOTIENT_FILENAME).is_file())
            self.assertFalse((output / "latin").exists())


if __name__ == "__main__":
    unittest.main()
