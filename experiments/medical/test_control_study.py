"""Synthetic tests for the bounded Celsus control core."""

from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
from contextlib import redirect_stderr, redirect_stdout
import tempfile
import unittest
from unittest.mock import patch

from experiments.medical import control_study as study


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def fixture(root: Path, partitions: dict[str, list[str]] | None = None) -> dict[str, object]:
    words = partitions or {
        "train": ["a", "ab", "ba"],
        "validation": ["ab", "ba"],
        "test": ["a", "b"],
    }
    partition_bytes = canonical(words)
    paragraph_bytes = b"synthetic paragraph metadata\n"
    manifest_value = {
        "schema_version": 1,
        "protocol": study.PROTOCOL,
        "raw_text_included": False,
        "private_outputs": {
            "partitions.private.json": {"sha256": digest(partition_bytes)},
            "paragraphs.private.jsonl": {"sha256": digest(paragraph_bytes)},
        },
    }
    manifest_bytes = canonical(manifest_value)
    partition_path = root / "partitions.private.json"
    manifest_path = root / "partition-manifest.json"
    partition_path.write_bytes(partition_bytes)
    manifest_path.write_bytes(manifest_bytes)
    return {
        "partitions_path": partition_path,
        "manifest_path": manifest_path,
        "output_path": root / "model" / "cold.json",
        "key_path": root / "model" / "cold.keys.json",
        "partitions_hash": digest(partition_bytes),
        "paragraphs_hash": digest(paragraph_bytes),
        "manifest_hash": digest(manifest_bytes),
    }


def pins(values: dict[str, object]):
    return patch.multiple(
        study,
        PARTITIONS_PATH=values["partitions_path"],
        MANIFEST_PATH=values["manifest_path"],
        OUTPUT_PATH=values["output_path"],
        KEY_PATH=values["key_path"],
        PARTITIONS_SHA256=values["partitions_hash"],
        PARAGRAPHS_SHA256=values["paragraphs_hash"],
        MANIFEST_SHA256=values["manifest_hash"],
    )


class ControlStudyTests(unittest.TestCase):
    def test_hash_failure_stops_before_json_parsing_or_old_runner(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            values = fixture(Path(temporary))
            values["partitions_path"].write_bytes(b"changed\n")
            with pins(values), patch.object(study, "_parse_manifest") as manifest_parser, patch.object(
                study, "_parse_partitions"
            ) as partition_parser, patch.object(study, "frozen_run_control") as old_runner:
                with self.assertRaisesRegex(study.ControlStudyFailure, "hash does not match"):
                    study.run_celsus_control()
            manifest_parser.assert_not_called()
            partition_parser.assert_not_called()
            old_runner.assert_not_called()

    def test_fixed_runner_receives_celsus_provenance_and_settings(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            values = fixture(Path(temporary))
            expected = {"status": "fixture"}
            with pins(values), patch.object(study, "frozen_run_control", return_value=expected) as old_runner:
                result = study.run_celsus_control()
            self.assertIs(result, expected)
            args, kwargs = old_runner.call_args
            self.assertEqual(args[0]["train"], ["a", "ab", "ba"])
            self.assertEqual(args[0]["validation"], ["ab", "ba"])
            self.assertEqual(args[0]["test"], ["a", "b"])
            self.assertEqual(kwargs["family"], "cap2")
            self.assertEqual(kwargs["seed"], 7000)
            self.assertEqual(kwargs["node_budget"], 1000)
            self.assertEqual(kwargs["bound_engine"], "bitset")
            self.assertEqual(kwargs["warm_start"], "none")
            self.assertEqual(kwargs["output_path"], values["output_path"])
            metadata = kwargs["metadata"]
            self.assertEqual(metadata["partition_manifest_sha256"], values["manifest_hash"])
            self.assertEqual(metadata["partitions_private_sha256"], values["partitions_hash"])
            self.assertEqual(metadata["partition_protocol"], study.PROTOCOL)

    def test_fixed_outputs_must_be_absent_before_old_runner(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            values = fixture(Path(temporary))
            values["output_path"].parent.mkdir()
            values["output_path"].write_text("preserve")
            with pins(values), patch.object(study, "frozen_run_control") as old_runner:
                with self.assertRaisesRegex(study.ControlStudyFailure, "already exists"):
                    study.run_celsus_control()
            old_runner.assert_not_called()
            self.assertEqual(values["output_path"].read_text(), "preserve")

    def test_empty_and_non_ascii_words_are_rejected(self) -> None:
        bad_cases = (
            {"train": ["a"], "validation": [""], "test": ["a"]},
            {"train": ["a"], "validation": ["é"], "test": ["a"]},
        )
        for bad in bad_cases:
            with self.subTest(bad=bad), tempfile.TemporaryDirectory() as temporary:
                values = fixture(Path(temporary), bad)
                with pins(values), patch.object(study, "frozen_run_control") as old_runner:
                    with self.assertRaises(study.ControlStudyFailure):
                        study.run_celsus_control()
                old_runner.assert_not_called()

    def test_manifest_pin_must_match_partition_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            values = fixture(Path(temporary))
            manifest = json.loads(values["manifest_path"].read_text())
            manifest["private_outputs"]["partitions.private.json"]["sha256"] = "0" * 64
            changed = canonical(manifest)
            values["manifest_path"].write_bytes(changed)
            values["manifest_hash"] = digest(changed)
            with pins(values), patch.object(study, "frozen_run_control") as old_runner:
                with self.assertRaisesRegex(study.ControlStudyFailure, "hash is not pinned"):
                    study.run_celsus_control()
            old_runner.assert_not_called()

    def test_main_prints_only_safe_summary_after_patched_run(self) -> None:
        stdout, stderr = io.StringIO(), io.StringIO()
        report = {"solver": {"status": "budget_exhausted"}, "key": {"private": "data"}}
        with patch.object(study, "run_celsus_control", return_value=report) as run:
            with redirect_stdout(stdout), redirect_stderr(stderr):
                status = study.main()
        run.assert_called_once_with()
        self.assertEqual(status, 0)
        self.assertEqual(json.loads(stdout.getvalue()), {
            "family": "cap2", "status": "budget_exhausted",
        })
        self.assertEqual(stderr.getvalue(), "")
        self.assertNotIn("private", stdout.getvalue())

    def test_main_returns_nonzero_without_report_on_fixed_failure(self) -> None:
        stdout, stderr = io.StringIO(), io.StringIO()
        failure = study.ControlStudyFailure("input_hash_mismatch", "private detail")
        with patch.object(study, "run_celsus_control", side_effect=failure):
            with redirect_stdout(stdout), redirect_stderr(stderr):
                status = study.main()
        self.assertEqual(status, 2)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("input_hash_mismatch", stderr.getvalue())
        self.assertNotIn("private detail", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
