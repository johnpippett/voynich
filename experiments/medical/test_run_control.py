"""Synthetic tests for the bounded Celsus control wrapper."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock
from contextlib import redirect_stdout
from io import StringIO

from experiments.medical import run_control as wrapper


def _bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


class RunControlTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.old_files = wrapper.FREEZE_FILES
        self.old_outputs = wrapper.ALL_OUTPUT_PATHS
        self.old_code_paths = wrapper.EXPECTED_CODE_PATHS
        self.old_paths = {
            name: getattr(wrapper, name)
            for name in (
                "COLD_PATH", "KEY_PATH", "PUBLIC_RECEIPT_PATH",
                "PRIVATE_RECEIPT_PATH", "PARTITION_MANIFEST_PATH",
                "PARTITIONS_PATH", "PARAGRAPHS_PATH",
            )
        }
        wrapper.COLD_PATH = Path("results/cold.json")
        wrapper.KEY_PATH = Path("results/cold.keys.json")
        wrapper.PUBLIC_RECEIPT_PATH = Path("reports/supervision.json")
        wrapper.PRIVATE_RECEIPT_PATH = Path("results/resources.private.json")
        wrapper.PARTITION_MANIFEST_PATH = Path("synthetic/partition-manifest.json")
        wrapper.PARTITIONS_PATH = Path("synthetic/partitions.private.json")
        wrapper.PARAGRAPHS_PATH = Path("synthetic/paragraphs.private.jsonl")
        wrapper.EXPECTED_CODE_PATHS = frozenset({"synthetic/core.py"})
        wrapper.FREEZE_FILES = (
            Path("synthetic/plan.md"),
            Path("synthetic/core.py"),
            Path("docs/plans/visual-homophonic-pilot.md"),
            wrapper.PARTITION_MANIFEST_PATH,
            wrapper.PARTITIONS_PATH,
            wrapper.PARAGRAPHS_PATH,
        )
        wrapper.ALL_OUTPUT_PATHS = (
            Path("results/cold.json"),
            Path("results/cold.keys.json"),
            Path("reports/supervision.json"),
            Path("results/resources.private.json"),
        )

    def tearDown(self) -> None:
        wrapper.FREEZE_FILES = self.old_files
        wrapper.ALL_OUTPUT_PATHS = self.old_outputs
        wrapper.EXPECTED_CODE_PATHS = self.old_code_paths
        for name, value in self.old_paths.items():
            setattr(wrapper, name, value)
        self.temp.cleanup()

    def _freeze(self, *, runtime: dict[str, str] | None = None) -> None:
        for relative in wrapper.FREEZE_FILES:
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes((relative.as_posix() + "\n").encode())
        partitions = self.root / wrapper.PARTITIONS_PATH
        paragraphs = self.root / wrapper.PARAGRAPHS_PATH
        partitions.write_bytes(b'{"train":["a"],"validation":["b"],"test":["c"]}\n')
        paragraphs.write_bytes(b'{"private":true}\n')
        partition_manifest = self.root / wrapper.PARTITION_MANIFEST_PATH
        partition_manifest.write_bytes(_bytes({
            "schema_version": 1,
            "protocol": wrapper.PROTOCOL,
            "raw_text_included": False,
            "private_outputs": {
                "partitions.private.json": {
                    "sha256": hashlib.sha256(partitions.read_bytes()).hexdigest(),
                },
                "paragraphs.private.jsonl": {
                    "sha256": hashlib.sha256(paragraphs.read_bytes()).hexdigest(),
                },
            },
        }))
        if partition_manifest != self.root / wrapper.PARTITION_MANIFEST_PATH:
            raise AssertionError("partition fixture path changed")
        files = [
            {
                "path": relative.as_posix(),
                "sha256": hashlib.sha256((self.root / relative).read_bytes()).hexdigest(),
            }
            for relative in wrapper.FREEZE_FILES
        ]
        value = {
            "schema_version": 1,
            "protocol": wrapper.PROTOCOL,
            "command": list(wrapper.EXPECTED_COMMAND),
            "child_command": list(wrapper.EXPECTED_CHILD_COMMAND),
            "parameters": dict(wrapper.EXPECTED_PARAMETERS),
            "resources": dict(wrapper.EXPECTED_RESOURCES),
            "runtime": runtime or {
                "freeze_python": "Python 3.11",
                "implementation": "CPython",
                "platform": "Linux",
            },
            "outputs": {
                "cold": "results/cold.json",
                "keys": "results/cold.keys.json",
                "public": "reports/supervision.json",
                "private": "results/resources.private.json",
            },
            "files": files,
        }
        manifest = self.root / wrapper.FREEZE_MANIFEST_PATH
        manifest.parent.mkdir(parents=True, exist_ok=True)
        manifest.write_bytes(_bytes(value))

    def _child_records(
        self,
        *,
        score_certified: bool = True,
        key_hash: str | None = None,
        metadata_ok: bool = True,
        oracle_score: int | None = 6,
        include_oracle: bool = True,
        include_code_hash: bool = True,
        unit_count: int = 3,
    ) -> None:
        key = {
            "kind": "synthetic_reference_control",
            "family": "cap2",
            "seed": 7000,
            "node_budget": 1000,
            "bound_engine": "bitset",
            "fit_scope": "encrypted validation words and plaintext training lexicon",
            "solver_status": "bound_certified" if score_certified else "budget_exhausted",
            "key": {"c00": "a", "c01": "a", "c02": "b"},
            "warm_start": "none",
        }
        key_path = self.root / "results/cold.keys.json"
        key_path.parent.mkdir(parents=True, exist_ok=True)
        key_path.write_bytes(_bytes(key))
        actual_key_hash = hashlib.sha256(key_path.read_bytes()).hexdigest()
        manifest_path = self.root / wrapper.PARTITION_MANIFEST_PATH
        partitions_path = self.root / wrapper.PARTITIONS_PATH
        visual_path = self.root / "docs/plans/visual-homophonic-pilot.md"
        report = {
            "kind": "synthetic_reference_control",
            "family": "cap2",
            "seed": 7000,
            "node_budget": 1000,
            "bound_engine": "bitset",
            "warm_start": "none",
            "metadata": {
                "language": "celsus",
                "reference": "Celsus projected paragraphs",
                "partition_manifest_path": wrapper.PARTITION_MANIFEST_PATH.as_posix(),
                "partition_manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
                "partitions_private_path": wrapper.PARTITIONS_PATH.as_posix(),
                "partitions_private_sha256": hashlib.sha256(partitions_path.read_bytes()).hexdigest(),
                "partition_protocol": wrapper.PROTOCOL,
                "scope": "one ancient medical author and work; descriptive known-cipher control",
            },
            "solver": {
                "status": "bound_certified" if score_certified else "budget_exhausted",
                "feasible": True,
                "score_certified": score_certified,
                "search_exhausted": score_certified,
                "nodes": 1,
                "pruned_nodes": 0,
                "frontier_node_count": 0 if score_certified else 1,
                "lower_bound": 7,
                "upper_bound": 7 if score_certified else 9,
                "score": 7,
                "hit_type_count": 1,
                "candidate_count_total": 1,
                "candidate_type_count": 1,
                "missing_candidate_count": 0,
                "cipher_type_count": 3,
                "total_weight": 9,
                "config": {
                    "capacity": 2,
                    "bound_engine": "bitset",
                    "node_budget": 1000,
                    "objective": "integer weighted exact lexicon word hits",
                    "initial_key_role": "completed warm-start incumbent only; root search has no fixed assignments",
                },
            },
            "objective": {
                "score_from_key": 7,
                "weights_total": 9,
                "weights_match_denominator": True,
                "N_token_count": 1,
                "T_type_count": 1,
            },
            "gates": {
                "validation": {
                    "observed_positions_pass": True,
                    "fully_observed_tokens_pass": True,
                    "full_decoding_pass": True,
                },
                "test": {
                    "observed_positions_pass": True,
                    "fully_observed_tokens_pass": True,
                    "full_decoding_pass": True,
                },
            },
            "test_fully_observed": True,
            "fit_input": {"token_count": 1, "type_count": 1, "unit_count": unit_count},
            "fitted_key_accuracy": {"correct": 3, "total": 3},
            "key_record_sha256": key_hash or actual_key_hash,
            "protocol_sha256": hashlib.sha256(visual_path.read_bytes()).hexdigest(),
            "code_sha256": {
                "synthetic/core.py": hashlib.sha256(
                    (self.root / "synthetic/core.py").read_bytes()
                ).hexdigest(),
            } if include_code_hash else {},
            "limits": [
                "These are known-cipher controls. They contain no manuscript measurement.",
                "A dictionary optimum does not imply a unique key or correct plaintext.",
            ],
        }
        if not metadata_ok:
            report["metadata"]["partition_protocol"] = "wrong-protocol"
        if include_oracle:
            report["oracle"] = {"objective": {"score_from_key": oracle_score}}
        report_path = self.root / "results/cold.json"
        report_path.write_bytes(_bytes(report))

    def test_verify_freeze_checks_exact_allowlist_and_hashes(self) -> None:
        self._freeze()
        result = wrapper.verify_control_freeze(self.root)
        self.assertEqual(result["file_count"], 6)
        self.assertEqual(result["protocol"], wrapper.PROTOCOL)
        (self.root / "synthetic/core.py").write_text("changed", encoding="utf-8")
        with self.assertRaises(wrapper.FreezeFailure):
            wrapper.verify_control_freeze(self.root)

    def test_verify_freeze_rejects_parameter_or_runtime_drift(self) -> None:
        self._freeze()
        manifest = self.root / wrapper.FREEZE_MANIFEST_PATH
        value = json.loads(manifest.read_text())
        value["parameters"]["seed"] = 408
        manifest.write_bytes(_bytes(value))
        with self.assertRaises(wrapper.FreezeFailure):
            wrapper.verify_control_freeze(self.root)

    def test_preflight_rejects_symlinked_parent_and_existing_output(self) -> None:
        self._freeze()
        (self.root / "results").symlink_to(self.root / "synthetic", target_is_directory=True)
        with self.assertRaises(FileExistsError):
            wrapper.preflight_outputs(self.root)
        (self.root / "results").unlink()
        (self.root / "results").mkdir()
        (self.root / "results/cold.json").write_text("{}", encoding="utf-8")
        with self.assertRaises(FileExistsError):
            wrapper.preflight_outputs(self.root)

    def test_output_validation_requires_key_hash_and_pinned_partition_metadata(self) -> None:
        self._freeze()
        self._child_records(metadata_ok=False)
        freeze = wrapper.verify_control_freeze(self.root)
        value = wrapper.validate_child_outputs(self.root, freeze)
        self.assertFalse(value["numeric_valid"])
        self.assertEqual(value["reason"], "partition_metadata_invalid")

    def test_status_is_incomplete_when_score_is_not_certified(self) -> None:
        self._freeze()
        self._child_records(score_certified=False)
        freeze = wrapper.verify_control_freeze(self.root)
        validation = wrapper.validate_child_outputs(self.root, freeze)
        self.assertTrue(validation["numeric_valid"])
        self.assertEqual(wrapper.control_status({"returncode": 0, "termination_reason": None}, validation), "incomplete_search")

    def test_key_hash_mismatch_is_implementation_failure(self) -> None:
        self._freeze()
        self._child_records(key_hash="0" * 64)
        freeze = wrapper.verify_control_freeze(self.root)
        validation = wrapper.validate_child_outputs(self.root, freeze)
        self.assertFalse(validation["numeric_valid"])
        self.assertEqual(validation["reason"], "key_hash_mismatch")

    def test_solver_record_requires_oracle_objective(self) -> None:
        self._freeze()
        self._child_records(include_oracle=False)
        freeze = wrapper.verify_control_freeze(self.root)
        validation = wrapper.validate_child_outputs(self.root, freeze)
        self.assertFalse(validation["numeric_valid"])
        self.assertEqual(validation["reason"], "solver_record_invalid")

    def test_solver_record_rejects_oracle_score_above_reported_upper_bound(self) -> None:
        self._freeze()
        self._child_records(oracle_score=8)
        freeze = wrapper.verify_control_freeze(self.root)
        validation = wrapper.validate_child_outputs(self.root, freeze)
        self.assertFalse(validation["numeric_valid"])
        self.assertEqual(validation["reason"], "solver_record_invalid")

    def test_solver_record_requires_key_count_to_match_fit_count(self) -> None:
        self._freeze()
        self._child_records(unit_count=4)
        freeze = wrapper.verify_control_freeze(self.root)
        validation = wrapper.validate_child_outputs(self.root, freeze)
        self.assertFalse(validation["numeric_valid"])
        self.assertEqual(validation["reason"], "solver_record_invalid")

    def test_solver_record_requires_complete_child_code_hash_set(self) -> None:
        self._freeze()
        self._child_records(include_code_hash=False)
        freeze = wrapper.verify_control_freeze(self.root)
        validation = wrapper.validate_child_outputs(self.root, freeze)
        self.assertFalse(validation["numeric_valid"])
        self.assertEqual(validation["reason"], "code_hashes_invalid")

    def test_run_writes_safe_receipts_after_successful_synthetic_child(self) -> None:
        self._freeze()

        def child_runner(root: Path, *, resources: object) -> dict[str, object]:
            self._child_records()
            return {
                "returncode": 0,
                "termination_reason": None,
                "elapsed_seconds": 0.1,
                "max_rss_bytes": 123,
                "rss_sample_count": 1,
            }

        with mock.patch.object(wrapper, "ensure_linux_rss_support"):
            public = wrapper.run_control(self.root, child_runner=child_runner)
        self.assertEqual(public["status"], "completed")
        self.assertTrue(public["numeric_outputs_valid"])
        self.assertTrue((self.root / "reports/supervision.json").is_file())
        self.assertTrue((self.root / "results/resources.private.json").is_file())
        raw = (self.root / "reports/supervision.json").read_text(encoding="utf-8")
        self.assertNotIn('"key"', raw)
        self.assertNotIn("source_path", raw)
        private = (self.root / "results/resources.private.json").read_text(encoding="utf-8")
        self.assertNotIn('"key"', private)

    def test_freeze_failure_stops_before_child_runner(self) -> None:
        called = False

        def child_runner(root: Path, *, resources: object) -> dict[str, object]:
            nonlocal called
            called = True
            return {}

        with mock.patch.object(wrapper, "verify_control_freeze", side_effect=wrapper.FreezeFailure("changed")):
            with self.assertRaises(wrapper.FreezeFailure):
                wrapper.run_control(self.root, child_runner=child_runner)
        self.assertFalse(called)

    def test_resource_termination_has_resource_abstain_status(self) -> None:
        self._freeze()

        def child_runner(root: Path, *, resources: object) -> dict[str, object]:
            return {
                "returncode": -15,
                "termination_reason": "rss_limit",
                "elapsed_seconds": 1.0,
                "max_rss_bytes": wrapper.EXPECTED_RESOURCES["rss_limit_bytes"],
                "rss_sample_count": 4,
            }

        with mock.patch.object(wrapper, "ensure_linux_rss_support"):
            public = wrapper.run_control(self.root, child_runner=child_runner)
        self.assertEqual(public["status"], "resource_abstain")
        self.assertFalse(public["numeric_outputs_valid"])

    def test_monitor_uses_process_group_and_fixed_limits(self) -> None:
        self.assertEqual(wrapper.EXPECTED_RESOURCES["rss_limit_bytes"], 7 * 1024**3)
        self.assertEqual(wrapper.EXPECTED_RESOURCES["poll_interval_seconds"], 0.25)
        self.assertEqual(wrapper.EXPECTED_RESOURCES["terminate_grace_seconds"], 5.0)
        self.assertIsNone(wrapper.EXPECTED_RESOURCES["as_limit_bytes"])

    def test_monitor_rechecks_exit_after_missing_rss_sample(self) -> None:
        class ExitedAfterPoll:
            pid = 321
            returncode = 0

            def __init__(self) -> None:
                self.poll_count = 0

            def poll(self) -> int | None:
                self.poll_count += 1
                return None if self.poll_count == 1 else self.returncode

            def wait(self, timeout: float | None = None) -> int:
                return self.returncode

        process = ExitedAfterPoll()
        with mock.patch.object(wrapper, "sample_rss_bytes", return_value=None):
            result = wrapper.monitor_process(process)  # type: ignore[arg-type]
        self.assertEqual(result["returncode"], 0)
        self.assertIsNone(result["termination_reason"])

    def test_public_entry_point_rejects_project_root_option(self) -> None:
        output = StringIO()
        with redirect_stdout(output):
            status = wrapper.main(["--project-root", str(self.root)])
        self.assertEqual(status, 1)
        self.assertEqual(json.loads(output.getvalue())["reason"], "fixed_command_takes_no_options")


if __name__ == "__main__":
    unittest.main()
