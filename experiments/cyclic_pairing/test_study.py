"""Behavioral tests for the compact cyclic control study core."""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from experiments.cyclic_pairing import study
from experiments.homophonic.controls import encrypt_words, seeded_control_key


UNITS = tuple(f"c{index:02d}" for index in range(52))
FORBIDDEN_KEYS = {
    "words",
    "plaintext",
    "ciphertext",
    "partitions",
    "key",
    "cipher_to_plain",
    "emission_order",
    "lexicon",
    "model",
}


def _assert_public_tree(value: object) -> None:
    if isinstance(value, dict):
        assert not FORBIDDEN_KEYS.intersection(value)
        for key, child in value.items():
            assert not isinstance(key, Path)
            _assert_public_tree(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            _assert_public_tree(child)


def _source_metadata() -> dict[str, object]:
    return {
        "reference_manifest_sha256": "a" * 64,
        "source_files": {
            "la_llct-ud-dev.conllu": {
                "sha256": "d" * 64,
                "extraction": {"sentences": 2, "words": 4},
            },
        },
        "split_counts": {"validation": {"sentences": 2, "words": 4}},
        "normalization": "fixed synthetic normalization",
        "source_path": "/private/source/file",
    }


def _freeze_metadata() -> dict[str, object]:
    return {
        "manifest_sha256": "f" * 64,
        "source_manifest_sha256": "m" * 64,
        "protocol_sha256": "e" * 64,
        "code_hashes": {"pairing.py": "a" * 64},
        "test_hashes": {"test_pairing.py": "b" * 64},
        "source_hashes": {"relative/file": "c" * 64},
        "private_note": "must not enter a public record",
    }


class StudyTests(unittest.TestCase):
  def test_stream_hash_uses_the_frozen_canonical_json_contract(self) -> None:
    partition = (("c00", "c01"), ("c02",))
    canonical = json.dumps(
        [["c00", "c01"], ["c02"]], sort_keys=True, separators=(",", ":")
    ) + "\n"
    expected = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    self.assertEqual(study.hash_cipher_partition(partition), expected)


  def test_freeze_loader_hashes_raw_bytes_and_overrides_embedded_digest(self) -> None:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        freeze_path = root / study.FREEZE_RELATIVE
        raw = b'{"manifest_sha256":"' + b"0" * 64 + b'"}\n'
        freeze_path.parent.mkdir(parents=True)
        freeze_path.write_bytes(raw)
        loaded = study.load_freeze_metadata(root)

    self.assertEqual(loaded["manifest_sha256"], hashlib.sha256(raw).hexdigest())
    self.assertNotEqual(loaded["manifest_sha256"], "0" * 64)


  def test_input_record_has_counts_hashes_and_no_raw_stream_or_paths(self) -> None:
    partition = (("c00", "c01"), ("c02",))
    record = study.build_input_record(
        "latin_llct",
        source_metadata=_source_metadata(),
        freeze_metadata=_freeze_metadata(),
        ciphertext_partition=partition,
    )

    self.assertEqual(record["protocol"], "cyclic-pairing-control-v1")
    self.assertEqual(record["family"], "cap2")
    self.assertEqual(record["manifest_sha256"], "f" * 64)
    self.assertEqual(record["source_file_hashes"]["la_llct-ud-dev.conllu"], "d" * 64)
    self.assertEqual(record["code_hashes"]["pairing.py"], "a" * 64)
    self.assertEqual(record["test_hashes"]["test_pairing.py"], "b" * 64)
    self.assertEqual(record["input_scope"], "ciphertext_validation_only")
    self.assertEqual(record["word_count"], 2)
    self.assertEqual(record["unit_token_count"], 3)
    self.assertEqual(record["validation_stream_sha256"], study.hash_cipher_partition(partition))
    self.assertEqual(record["declared_unit_count"], 52)
    _assert_public_tree(record)
    encoded = json.dumps(record, sort_keys=True)
    self.assertNotIn("c00", encoded)
    self.assertNotIn("/private", encoded)


  def test_required_provenance_rejects_missing_or_malformed_values(self) -> None:
    missing_source = _source_metadata()
    del missing_source["reference_manifest_sha256"]
    with self.assertRaisesRegex(ValueError, "source manifest"):
        study.build_input_record(
            "latin_llct",
            source_metadata=missing_source,
            freeze_metadata=_freeze_metadata(),
            ciphertext_partition=[("c00",)],
        )

    malformed_source = _source_metadata()
    malformed_source["source_files"]["la_llct-ud-dev.conllu"]["sha256"] = "z" * 64
    with self.assertRaisesRegex(ValueError, "source file hash"):
        study.build_input_record(
            "latin_llct",
            source_metadata=malformed_source,
            freeze_metadata=_freeze_metadata(),
            ciphertext_partition=[("c00",)],
        )

    missing_freeze = _freeze_metadata()
    del missing_freeze["manifest_sha256"]
    with self.assertRaisesRegex(ValueError, "freeze manifest"):
        study.build_input_record(
            "latin_llct",
            source_metadata=_source_metadata(),
            freeze_metadata=missing_freeze,
            ciphertext_partition=[("c00",)],
        )

    malformed_freeze = _freeze_metadata()
    malformed_freeze["code_hashes"] = {"pairing.py": "not-a-digest"}
    with self.assertRaisesRegex(ValueError, "code_hashes"):
        study.build_input_record(
            "latin_llct",
            source_metadata=_source_metadata(),
            freeze_metadata=malformed_freeze,
            ciphertext_partition=[("c00",)],
        )


  def test_pairing_stage_requires_fixed_inventory_and_protocol_limits(self) -> None:
    with self.assertRaisesRegex(ValueError, "52"):
        study.run_pairing_stage([("c00",)], units=("c00", "c01"))
    with self.assertRaisesRegex(ValueError, "edge query"):
        study.run_pairing_stage(
            [("c00", "c01")], units=UNITS, max_edge_queries=27
        )
    with self.assertRaisesRegex(ValueError, "non-negative"):
        study.run_pairing_stage([("c00",)], units=UNITS, node_budget=-1)


  def test_pairing_stage_reports_safe_full_graph_and_forced_categories(self) -> None:
    partition = (("c00", "c01", "c00"), ("c02", "c03"))
    record = study.run_pairing_stage(partition, units=UNITS, node_budget=100_000)

    self.assertEqual(record["input_scope"], "ciphertext_validation_only")
    self.assertEqual(record["graph"]["vertex_count"], 52)
    self.assertEqual(sum(record["graph"]["edge_counts_by_category"].values()), record["graph"]["edge_count"])
    self.assertEqual(record["matching"]["scope"], "full")
    self.assertEqual(record["matching"]["node_budget"], 100_000)
    self.assertLessEqual(record["forced"]["queries_run"], 26)
    self.assertEqual(record["forced"]["protocol_max_edge_queries"], 26)
    _assert_public_tree(record)
    encoded = json.dumps(record, sort_keys=True)
    self.assertIn("c00", encoded)
    self.assertIn("c01", encoded)


  def test_pairing_stage_preserves_none_and_budget_unknown_semantics(self) -> None:
    impossible = study.run_pairing_stage(
        [("c00", "c00")], units=UNITS, node_budget=100_000
    )
    self.assertEqual(impossible["matching"]["status"], "none")
    self.assertEqual(impossible["forced"]["status"], "infeasible")

    budget = study.run_pairing_stage([], units=UNITS, node_budget=0)
    self.assertEqual(budget["matching"]["status"], "unknown_budget")
    self.assertEqual(budget["forced"]["status"], "unknown_budget")
    self.assertEqual(budget["forced"]["queries_run"], 0)


  def test_pairing_stage_rejects_repeated_base_search_disagreement(self) -> None:
    planted = seeded_control_key("cap2", 7000)
    partition = tuple(encrypt_words(["ab", "ba", "aba"], planted))
    compatibility = study.build_compatibility(UNITS, [partition])
    repeated = study.forced_edges(compatibility, node_budget=100_000)
    bad_repeated = replace(
        repeated, original_nodes_visited=repeated.original_nodes_visited + 1
    )
    with patch.object(study, "forced_edges", return_value=bad_repeated):
        with self.assertRaisesRegex(ValueError, "node count"):
            study.run_pairing_stage(partition, units=UNITS)


  def test_control_diagnostics_use_unit_pairs_without_plaintext_mapping(self) -> None:
    planted = seeded_control_key("cap2", 7000)
    partition = tuple(encrypt_words(["ab", "ba", "aba"], planted))
    pairing_record = study.run_pairing_stage(partition, units=UNITS)
    compatibility = study.build_compatibility(UNITS, [partition])
    diagnostics = study.build_control_diagnostics(
        pairing_record,
        compatibility=compatibility,
        planted_key=planted,
    )

    self.assertEqual(diagnostics["control_pair_count"], 26)
    self.assertEqual(diagnostics["graph_control_pair_overlap_count"], 26)
    self.assertGreaterEqual(diagnostics["orientation"]["comparable_count"], 0)
    self.assertTrue(all(
        category in {"observed_observed", "observed_unseen", "unseen_unseen"}
        for category in diagnostics["control_pair_counts_by_category"]
    ))
    _assert_public_tree(diagnostics)
    encoded = json.dumps(diagnostics, sort_keys=True)
    self.assertNotIn("cipher_to_plain", encoded)
    self.assertNotIn('"key"', encoded)
    self.assertNotIn('"letter"', encoded)


  def test_unknown_positive_result_is_valid_when_graph_control_is_consistent(self) -> None:
    planted = seeded_control_key("cap2", 7000)
    partition: tuple[tuple[str, ...], ...] = ()
    pairing_record = study.run_pairing_stage(partition, units=UNITS, node_budget=0)
    compatibility = study.build_compatibility(UNITS, [partition])
    diagnostics = study.build_control_diagnostics(
        pairing_record, compatibility=compatibility, planted_key=planted
    )
    self.assertEqual(diagnostics["status"], "unknown_budget")
    self.assertEqual(diagnostics["graph_control_pair_overlap_count"], 26)


  def test_run_one_corpus_saves_pairing_before_diagnostics_and_refuses_overwrite(self) -> None:
    validation_words = ["ab", "ba", "aba"]
    metadata = _source_metadata()
    fake_partitions = {
        "latin_llct": {"words": {"validation": validation_words}, "metadata": metadata},
        "italian_old": {"words": {"validation": ["ab"]}, "metadata": metadata},
    }
    with tempfile.TemporaryDirectory() as temporary:
        tmp_path = Path(temporary)
        planted = seeded_control_key("cap2", 7000)
        expected_hash = study.hash_cipher_partition(encrypt_words(validation_words, planted))
        with patch.object(study, "load_reference_partitions", return_value=fake_partitions), patch.object(
            study,
            "EXPECTED_VALIDATION_STREAM_HASHES",
            {"latin_llct": expected_hash, "italian_old": "0" * 64},
        ):
            output_root = tmp_path / "results"
            observed: list[bool] = []
            original = study.build_control_diagnostics

            def checked_diagnostics(*args: object, **kwargs: object) -> dict[str, object]:
                observed.append((output_root / "latin_llct" / "pairing.json").is_file())
                return original(*args, **kwargs)

            with patch.object(study, "build_control_diagnostics", checked_diagnostics):
                result = study.run_one_corpus(
                    tmp_path,
                    "latin_llct",
                    output_root,
                    _freeze_metadata(),
                )

            self.assertEqual(result["status"], "complete")
            self.assertEqual(observed, [True])
            corpus_dir = output_root / "latin_llct"
            self.assertEqual(
                {path.name for path in corpus_dir.iterdir()},
                {"input.json", "pairing.json", "diagnostics.json"},
            )
            for path in corpus_dir.iterdir():
                _assert_public_tree(json.loads(path.read_text()))
            with self.assertRaises(FileExistsError):
                study.run_one_corpus(tmp_path, "latin_llct", output_root, _freeze_metadata())


  def test_stream_pin_mismatch_happens_before_input_write(self) -> None:
    fake_partitions = {
        "latin_llct": {"words": {"validation": ["ab"]}, "metadata": _source_metadata()},
        "italian_old": {"words": {"validation": ["ab"]}, "metadata": _source_metadata()},
    }
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        output_root = root / "results"
        with patch.object(study, "load_reference_partitions", return_value=fake_partitions), patch.object(
            study,
            "EXPECTED_VALIDATION_STREAM_HASHES",
            {"latin_llct": "0" * 64, "italian_old": "0" * 64},
        ):
            with self.assertRaisesRegex(ValueError, "stream hash mismatch"):
                study.run_one_corpus(root, "latin_llct", output_root, _freeze_metadata())
        self.assertFalse((output_root / "latin_llct" / "input.json").exists())
        self.assertFalse((output_root / "latin_llct" / "pairing.json").exists())


  def test_postdiagnostic_failure_writes_safe_failure_and_keeps_pairing(self) -> None:
    validation_words = ["ab", "ba", "aba"]
    fake_partitions = {
        "latin_llct": {"words": {"validation": validation_words}, "metadata": _source_metadata()},
        "italian_old": {"words": {"validation": ["ab"]}, "metadata": _source_metadata()},
    }
    planted = seeded_control_key("cap2", 7000)
    expected_hash = study.hash_cipher_partition(encrypt_words(validation_words, planted))
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        output_root = root / "results"
        with patch.object(study, "load_reference_partitions", return_value=fake_partitions), patch.object(
            study,
            "EXPECTED_VALIDATION_STREAM_HASHES",
            {"latin_llct": expected_hash, "italian_old": "0" * 64},
        ), patch.object(
            study,
            "build_control_diagnostics",
            side_effect=ValueError("synthetic post-diagnostic failure"),
        ):
            with self.assertRaisesRegex(RuntimeError, "post-pairing"):
                study.run_one_corpus(root, "latin_llct", output_root, _freeze_metadata())
        pairing = json.loads((output_root / "latin_llct" / "pairing.json").read_text())
        diagnostics = json.loads((output_root / "latin_llct" / "diagnostics.json").read_text())
        self.assertEqual(pairing["record_type"], "pairing")
        self.assertEqual(diagnostics["status"], "implementation_failure")
        self.assertNotIn("synthetic post-diagnostic failure", json.dumps(diagnostics))
