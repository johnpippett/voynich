"""Tests for the bounded cyclic-pairing control entry point."""

from __future__ import annotations

import hashlib
import json
import os
import platform
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from experiments.cyclic_pairing import run_controls


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _canonical(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_canonical(value))


def _fixture_digest(relative: Path) -> str:
    return _sha256_bytes(f"fixture:{relative.as_posix()}".encode())


def _fixture_provenance(corpus: str) -> dict[str, dict[str, str]]:
    files = {path.as_posix(): _fixture_digest(path) for path in run_controls.FREEZE_FILES}
    source = {
        path.name: files[path.as_posix()]
        for path in run_controls.FREEZE_FILES
        if path.parts[:3] == ("data", "raw", "reference")
        and len(path.parts) > 3
        and path.parts[3] == corpus
        and path.suffix == ".conllu"
    }
    code = {
        path.as_posix(): digest
        for path, digest in ((Path(name), digest) for name, digest in files.items())
        if path.suffix == ".py" and "test" not in path.name
    }
    tests = {
        path.as_posix(): digest
        for path, digest in ((Path(name), digest) for name, digest in files.items())
        if path.suffix == ".py" and "test" in path.name
    }
    return {
        "source_file_hashes": source,
        "code_hashes": code,
        "test_hashes": tests,
        "frozen_file_hashes": files,
    }


def _freeze_fixture(root: Path) -> tuple[Path, dict[str, object]]:
    hashes: list[dict[str, str]] = []
    for relative in run_controls.FREEZE_FILES:
        path = root / relative
        payload = f"fixture:{relative.as_posix()}".encode()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
        hashes.append({"path": relative.as_posix(), "sha256": _sha256_bytes(payload)})
    manifest: dict[str, object] = {
        "schema_version": 1,
        "protocol": run_controls.PROTOCOL,
        "command": list(run_controls.EXPECTED_COMMAND),
        "child_command": list(run_controls.EXPECTED_CHILD_COMMAND),
        "parameters": dict(run_controls.EXPECTED_PARAMETERS),
        "resources": dict(run_controls.EXPECTED_RESOURCES),
        "runtime": {
            "freeze_python": platform.python_version(),
            "implementation": platform.python_implementation(),
            "platform": platform.platform(),
            "runtime_role": "fixture",
        },
        "outputs": {
            "corpora": ["latin_llct", "italian_old"],
            "public": run_controls.PUBLIC_RECEIPT_PATH.as_posix(),
            "private": run_controls.PRIVATE_RECEIPT_PATH.as_posix(),
            "corpus": [path.as_posix() for path in run_controls.CORPUS_OUTPUT_PATHS],
        },
        "files": hashes,
    }
    manifest_path = root / run_controls.FREEZE_MANIFEST_PATH
    _write_json(manifest_path, manifest)
    return manifest_path, manifest


def _valid_input(corpus: str, freeze_hash: str) -> dict[str, object]:
    stream_hashes = {
        "latin_llct": "eb03e98b086b9b8bc883f349afaee968bfeaeee8c95be5f66bec320e54b419b2",
        "italian_old": "d7e9c6e0b716cf7ea1c7deb4f135ca2692ea70b4f927548e99668ab0c1428492",
    }
    provenance = _fixture_provenance(corpus)
    return {
        "record_type": "input",
        "protocol": run_controls.PROTOCOL,
        "corpus": corpus,
        "family": "cap2",
        "seed": 7000,
        "capacity": 2,
        "declared_unit_count": 52,
        "declared_units_sha256": run_controls.EXPECTED_DECLARED_UNITS_SHA256,
        "manifest_sha256": freeze_hash,
        "source_manifest_sha256": provenance["frozen_file_hashes"]["data/reference_manifest.json"],
        **provenance,
        "validation_stream_sha256": stream_hashes[corpus],
        "word_count": 1,
        "unit_token_count": 1,
        "unit_type_count": 1,
        "node_budget": 100_000,
        "max_edge_queries": 26,
        "input_scope": "ciphertext_validation_only",
    }


def _valid_pairing(corpus: str, freeze_hash: str) -> dict[str, object]:
    provenance = _fixture_provenance(corpus)
    return {
        "record_type": "pairing",
        "protocol": run_controls.PROTOCOL,
        "corpus": corpus,
        "family": "cap2",
        "seed": 7000,
        "capacity": 2,
        "input_scope": "ciphertext_validation_only",
        "node_budget": 100_000,
        "max_edge_queries": 26,
        "declared_unit_count": 52,
        "declared_units_sha256": run_controls.EXPECTED_DECLARED_UNITS_SHA256,
        "validation_stream_sha256": (
            "eb03e98b086b9b8bc883f349afaee968bfeaeee8c95be5f66bec320e54b419b2"
            if corpus == "latin_llct"
            else "d7e9c6e0b716cf7ea1c7deb4f135ca2692ea70b4f927548e99668ab0c1428492"
        ),
        "word_count": 1,
        "unit_token_count": 1,
        "manifest_sha256": freeze_hash,
        "source_manifest_sha256": provenance["frozen_file_hashes"]["data/reference_manifest.json"],
        **provenance,
        "graph": {
            "vertex_count": 52,
            "edge_count": 26,
            "edge_counts_by_category": {
                "observed_observed": 0,
                "observed_unseen": 0,
                "unseen_unseen": 26,
            },
            "observed_vertex_count": 0,
            "unseen_vertex_count": 52,
        },
        "matching": {
            "scope": "full",
            "node_budget": 100_000,
            "status": "unknown_budget",
            "witness_count": 0,
            "witnesses": [],
            "nodes_visited": 100_000,
            "scope_unit_count": 52,
            "unseen_unit_count": 52,
        },
        "forced": {
            "status": "unknown_budget",
            "original_status": "unknown_budget",
            "original_witness_count": 0,
            "original_node_budget": 100_000,
            "original_nodes_visited": 100_000,
            "selected_witness": None,
            "edge_evidence": [],
            "category_counts": {
                category: {status: 0 for status in ("forced", "not_forced", "unknown")}
                for category in ("observed_observed", "observed_unseen", "unseen_unseen")
            },
            "protocol_max_edge_queries": 26,
            "queries_run": 0,
            "queries_skipped": 0,
        },
    }


def _valid_diagnostics(corpus: str, freeze_hash: str) -> dict[str, object]:
    control_pairs = [
        ["c00", "c33"], ["c01", "c18"], ["c02", "c45"], ["c03", "c09"],
        ["c04", "c50"], ["c05", "c51"], ["c06", "c46"], ["c07", "c49"],
        ["c08", "c22"], ["c10", "c31"], ["c11", "c47"], ["c12", "c16"],
        ["c13", "c19"], ["c14", "c30"], ["c15", "c23"], ["c17", "c39"],
        ["c20", "c25"], ["c21", "c26"], ["c24", "c40"], ["c27", "c43"],
        ["c28", "c35"], ["c29", "c32"], ["c34", "c38"], ["c36", "c44"],
        ["c37", "c41"], ["c42", "c48"],
    ]
    provenance = _fixture_provenance(corpus)
    return {
        "record_type": "diagnostics",
        "protocol": run_controls.PROTOCOL,
        "corpus": corpus,
        "input_scope": "ciphertext_validation_only",
        "manifest_sha256": freeze_hash,
        "source_manifest_sha256": provenance["frozen_file_hashes"]["data/reference_manifest.json"],
        "status": "unknown_budget",
        "full_matching_status": "unknown_budget",
        "matching_status": "unknown_budget",
        "matching_witness_count": 0,
        "control_pair_count": 26,
        "control_pair_set_sha256": run_controls.EXPECTED_CONTROL_PAIR_SET_SHA256,
        "graph_control_pair_overlap_count": 26,
        "graph_control_pair_overlap": control_pairs,
        "graph_control_pair_missing": [],
        "control_pair_counts_by_category": {
            "observed_observed": 0,
            "observed_unseen": 0,
            "unseen_unseen": 26,
        },
        "orientation": {
            "comparable_count": 0,
            "match_count": 0,
            "mismatch_count": 0,
        },
        "witnesses": [],
    }


class RunControlsTests(unittest.TestCase):
    def test_freeze_verification_accepts_exact_allowlist_and_returns_hash(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _freeze_fixture(root)

            verified = run_controls.verify_freeze_manifest(root)

            self.assertEqual(verified["protocol"], run_controls.PROTOCOL)
            self.assertEqual(verified["file_count"], len(run_controls.FREEZE_FILES))
            self.assertEqual(len(verified["files"]), len(run_controls.FREEZE_FILES))
            self.assertRegex(verified["manifest_sha256"], r"^[0-9a-f]{64}$")

    def test_freeze_verification_rejects_extra_file_entry(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest_path, manifest = _freeze_fixture(root)
            manifest["files"].append({"path": "extra.txt", "sha256": "0" * 64})  # type: ignore[union-attr]
            _write_json(manifest_path, manifest)

            with self.assertRaises(run_controls.FreezeFailure):
                run_controls.verify_freeze_manifest(root)

    def test_freeze_verification_rejects_changed_input_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _freeze_fixture(root)
            (root / run_controls.FREEZE_FILES[0]).write_bytes(b"changed")

            with self.assertRaises(run_controls.FreezeFailure):
                run_controls.verify_freeze_manifest(root)

    def test_freeze_verification_requires_runtime_record(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest_path, manifest = _freeze_fixture(root)
            del manifest["runtime"]
            _write_json(manifest_path, manifest)

            with self.assertRaises(run_controls.FreezeFailure):
                run_controls.verify_freeze_manifest(root)

    def test_freeze_mismatch_happens_before_synthetic_tests_or_child(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _freeze_fixture(root)
            manifest_path = root / run_controls.FREEZE_MANIFEST_PATH
            manifest = json.loads(manifest_path.read_text())
            manifest["parameters"]["seed"] = 7001
            _write_json(manifest_path, manifest)

            with patch.object(run_controls, "run_synthetic_tests") as synthetic, patch.object(
                run_controls, "launch_child", side_effect=AssertionError("child launched")
            ):
                with self.assertRaises(run_controls.FreezeFailure):
                    run_controls.run_controls(root)
            synthetic.assert_not_called()

    def test_output_preflight_rejects_regular_file_and_symlink_components(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _freeze_fixture(root)
            first = root / run_controls.CORPUS_OUTPUT_PATHS[0]
            first.parent.mkdir(parents=True, exist_ok=True)
            first.write_text("existing")
            with self.assertRaises(FileExistsError):
                run_controls.preflight_outputs(root)

            first.unlink()
            first.parent.rmdir()
            regular_parent = root / run_controls.RESULTS_ROOT
            regular_parent.rmdir()
            regular_parent.write_text("regular parent")
            with self.assertRaises(FileExistsError):
                run_controls.preflight_outputs(root)
            regular_parent.unlink()
            symlink_parent = root / run_controls.RESULTS_ROOT.relative_to(Path(".")) / "latin_llct"
            symlink_parent.parent.mkdir(parents=True, exist_ok=True)
            target = root / "target"
            target.mkdir()
            symlink_parent.symlink_to(target, target_is_directory=True)
            with self.assertRaises(FileExistsError):
                run_controls.preflight_outputs(root)

    def test_output_validation_requires_full_scope_and_safe_records(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _freeze_fixture(root)
            freeze = run_controls.verify_freeze_manifest(root)
            corpus_dir = root / run_controls.RESULTS_ROOT / "latin_llct"
            _write_json(corpus_dir / "input.json", _valid_input("latin_llct", freeze["manifest_sha256"]))
            _write_json(corpus_dir / "pairing.json", _valid_pairing("latin_llct", freeze["manifest_sha256"]))
            _write_json(corpus_dir / "diagnostics.json", _valid_diagnostics("latin_llct", freeze["manifest_sha256"]))

            result = run_controls.validate_corpus_outputs(root, "latin_llct", freeze)
            self.assertTrue(result["numeric_valid"])
            self.assertEqual(len(result["outputs"]), 3)

            pairing = json.loads((corpus_dir / "pairing.json").read_text())
            pairing["matching"]["scope"] = "observed"
            _write_json(corpus_dir / "pairing.json", pairing)
            self.assertFalse(run_controls.validate_corpus_outputs(root, "latin_llct", freeze)["numeric_valid"])

            pairing["matching"]["scope"] = "full"
            pairing["record_type"] = "diagnostics"
            _write_json(corpus_dir / "pairing.json", pairing)
            self.assertFalse(run_controls.validate_corpus_outputs(root, "latin_llct", freeze)["numeric_valid"])

    def test_output_validation_marks_missing_file_invalid(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _freeze_fixture(root)
            freeze = run_controls.verify_freeze_manifest(root)
            corpus_dir = root / run_controls.RESULTS_ROOT / "latin_llct"
            _write_json(corpus_dir / "input.json", _valid_input("latin_llct", freeze["manifest_sha256"]))
            _write_json(corpus_dir / "pairing.json", _valid_pairing("latin_llct", freeze["manifest_sha256"]))

            result = run_controls.validate_corpus_outputs(root, "latin_llct", freeze)
            self.assertFalse(result["numeric_valid"])
            self.assertFalse(result["complete"])

    def test_output_validation_rejects_incomplete_positive_control_diagnostic(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _freeze_fixture(root)
            freeze = run_controls.verify_freeze_manifest(root)
            corpus_dir = root / run_controls.RESULTS_ROOT / "latin_llct"
            _write_json(corpus_dir / "input.json", _valid_input("latin_llct", freeze["manifest_sha256"]))
            _write_json(corpus_dir / "pairing.json", _valid_pairing("latin_llct", freeze["manifest_sha256"]))
            diagnostics = _valid_diagnostics("latin_llct", freeze["manifest_sha256"])
            diagnostics["control_pair_count"] = 25
            _write_json(corpus_dir / "diagnostics.json", diagnostics)

            self.assertFalse(run_controls.validate_corpus_outputs(root, "latin_llct", freeze)["numeric_valid"])

    def test_output_validation_rejects_missing_positive_control_pair(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _freeze_fixture(root)
            freeze = run_controls.verify_freeze_manifest(root)
            corpus_dir = root / run_controls.RESULTS_ROOT / "latin_llct"
            _write_json(corpus_dir / "input.json", _valid_input("latin_llct", freeze["manifest_sha256"]))
            _write_json(corpus_dir / "pairing.json", _valid_pairing("latin_llct", freeze["manifest_sha256"]))
            diagnostics = _valid_diagnostics("latin_llct", freeze["manifest_sha256"])
            diagnostics["graph_control_pair_overlap_count"] = 25
            diagnostics["graph_control_pair_overlap"] = diagnostics["graph_control_pair_overlap"][:-1]  # type: ignore[index]
            diagnostics["graph_control_pair_missing"] = [["c42", "c48"]]
            _write_json(corpus_dir / "diagnostics.json", diagnostics)

            self.assertFalse(run_controls.validate_corpus_outputs(root, "latin_llct", freeze)["numeric_valid"])

    def test_output_validation_rejects_wrong_orientation_or_forced_status(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _freeze_fixture(root)
            freeze = run_controls.verify_freeze_manifest(root)
            corpus_dir = root / run_controls.RESULTS_ROOT / "latin_llct"
            _write_json(corpus_dir / "input.json", _valid_input("latin_llct", freeze["manifest_sha256"]))
            pairing = _valid_pairing("latin_llct", freeze["manifest_sha256"])
            pairing["forced"]["status"] = "analyzed"  # type: ignore[index]
            _write_json(corpus_dir / "pairing.json", pairing)
            _write_json(corpus_dir / "diagnostics.json", _valid_diagnostics("latin_llct", freeze["manifest_sha256"]))
            self.assertFalse(run_controls.validate_corpus_outputs(root, "latin_llct", freeze)["numeric_valid"])

            pairing["forced"]["status"] = "unknown_budget"  # type: ignore[index]
            diagnostics = _valid_diagnostics("latin_llct", freeze["manifest_sha256"])
            diagnostics["orientation"]["comparable_count"] = 1  # type: ignore[index]
            diagnostics["orientation"]["match_count"] = 0  # type: ignore[index]
            diagnostics["orientation"]["mismatch_count"] = 1  # type: ignore[index]
            _write_json(corpus_dir / "pairing.json", pairing)
            _write_json(corpus_dir / "diagnostics.json", diagnostics)
            self.assertFalse(run_controls.validate_corpus_outputs(root, "latin_llct", freeze)["numeric_valid"])

    def test_unique_diagnostic_requires_the_planted_witness(self) -> None:
        pairing = _valid_pairing("latin_llct", "f" * 64)
        pairing["matching"]["status"] = "unique"  # type: ignore[index]
        pairing["matching"]["witness_count"] = 1  # type: ignore[index]
        pairing["matching"]["witnesses"] = [  # type: ignore[index]
            [[left, right] for left, right in run_controls.EXPECTED_CONTROL_PAIRS]
        ]
        diagnostics = _valid_diagnostics("latin_llct", "f" * 64)
        diagnostics["status"] = "unique"
        diagnostics["full_matching_status"] = "unique"
        diagnostics["matching_status"] = "unique"
        diagnostics["matching_witness_count"] = 1
        diagnostics["witnesses"] = [
            {
                "witness_index": 0,
                "pair_set_sha256": "a" * 64,
                "control_pair_overlap_count": 0,
                "control_pairs_in_witness": [],
            }
        ]
        self.assertFalse(run_controls._validate_diagnostics_record(diagnostics, pairing))

    def test_non_linux_platform_stops_before_synthetic_or_child(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _freeze_fixture(root)
            with patch.object(run_controls.sys, "platform", "darwin"), patch.object(
                run_controls, "run_synthetic_tests"
            ) as synthetic, patch.object(run_controls, "launch_child") as child:
                with self.assertRaises(run_controls.FreezeFailure):
                    run_controls.run_controls(root)
            synthetic.assert_not_called()
            child.assert_not_called()

    def test_output_validation_rejects_non_digest_input_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _freeze_fixture(root)
            freeze = run_controls.verify_freeze_manifest(root)
            corpus_dir = root / run_controls.RESULTS_ROOT / "latin_llct"
            input_record = _valid_input("latin_llct", freeze["manifest_sha256"])
            input_record["validation_stream_sha256"] = "short"
            _write_json(corpus_dir / "input.json", input_record)
            _write_json(corpus_dir / "pairing.json", _valid_pairing("latin_llct", freeze["manifest_sha256"]))
            _write_json(corpus_dir / "diagnostics.json", _valid_diagnostics("latin_llct", freeze["manifest_sha256"]))

            self.assertFalse(run_controls.validate_corpus_outputs(root, "latin_llct", freeze)["numeric_valid"])

    def test_output_validation_binds_provenance_to_freeze_and_pairing(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _freeze_fixture(root)
            freeze = run_controls.verify_freeze_manifest(root)
            corpus_dir = root / run_controls.RESULTS_ROOT / "latin_llct"
            input_record = _valid_input("latin_llct", freeze["manifest_sha256"])
            pairing = _valid_pairing("latin_llct", freeze["manifest_sha256"])
            _write_json(corpus_dir / "input.json", input_record)
            _write_json(corpus_dir / "pairing.json", pairing)
            _write_json(corpus_dir / "diagnostics.json", _valid_diagnostics("latin_llct", freeze["manifest_sha256"]))
            self.assertTrue(run_controls.validate_corpus_outputs(root, "latin_llct", freeze)["numeric_valid"])

            input_record["source_manifest_sha256"] = "0" * 64
            _write_json(corpus_dir / "input.json", input_record)
            self.assertFalse(run_controls.validate_corpus_outputs(root, "latin_llct", freeze)["numeric_valid"])

            input_record["source_manifest_sha256"] = _fixture_provenance("latin_llct")["frozen_file_hashes"]["data/reference_manifest.json"]
            pairing["code_hashes"] = {"wrong.py": "0" * 64}
            _write_json(corpus_dir / "input.json", input_record)
            _write_json(corpus_dir / "pairing.json", pairing)
            self.assertFalse(run_controls.validate_corpus_outputs(root, "latin_llct", freeze)["numeric_valid"])

    def test_monitor_terminates_process_group_on_wall_limit(self) -> None:
        process = subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(3)"],
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            result = run_controls.monitor_process(
                process,
                wall_seconds=0.05,
                rss_limit_bytes=7 * 1024**3,
                poll_interval_seconds=0.01,
                terminate_grace_seconds=0.05,
            )
            self.assertEqual(result["termination_reason"], "wall_timeout")
            self.assertIsNotNone(process.poll())
        finally:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()

    def test_monitor_terminates_process_on_rss_limit(self) -> None:
        process = subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(3)"],
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            with patch.object(run_controls, "sample_rss_bytes", return_value=1):
                result = run_controls.monitor_process(
                    process,
                    wall_seconds=2,
                    rss_limit_bytes=1,
                    poll_interval_seconds=0.01,
                    terminate_grace_seconds=0.05,
                )
            self.assertEqual(result["termination_reason"], "rss_limit")
            self.assertIsNotNone(process.poll())
        finally:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()

    def test_public_receipt_excludes_private_resource_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _freeze_fixture(root)
            with patch.object(run_controls, "run_synthetic_tests", return_value={"status": "pass", "count": 20}), patch.object(
                run_controls, "launch_child", return_value={"returncode": 0, "termination_reason": None, "elapsed_seconds": 0.01, "max_rss_bytes": 100}
            ) as child:
                with patch.object(run_controls, "validate_corpus_outputs", return_value={"numeric_valid": False, "complete": False, "outputs": []}):
                    public = run_controls.run_controls(root)
            self.assertEqual(public["protocol"], run_controls.PROTOCOL)
            self.assertIn("corpora", public["supervision"])
            encoded = json.dumps(public, sort_keys=True)
            self.assertNotIn("elapsed_seconds", encoded)
            self.assertNotIn("max_rss_bytes", encoded)
            self.assertEqual(child.call_count, 2)

    def test_numeric_valid_requires_zero_exit_and_all_three_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _freeze_fixture(root)

            def child(project_root: Path, corpus: str, *, resources: object) -> dict[str, object]:
                freeze = run_controls.verify_freeze_manifest(project_root)
                corpus_dir = project_root / run_controls.RESULTS_ROOT / corpus
                _write_json(corpus_dir / "input.json", _valid_input(corpus, freeze["manifest_sha256"]))
                _write_json(corpus_dir / "pairing.json", _valid_pairing(corpus, freeze["manifest_sha256"]))
                _write_json(corpus_dir / "diagnostics.json", _valid_diagnostics(corpus, freeze["manifest_sha256"]))
                return {"returncode": 0, "termination_reason": None, "elapsed_seconds": 0.01, "max_rss_bytes": 100}

            public = run_controls.run_controls(
                root,
                synthetic_runner=lambda _root: {"status": "pass", "count": 20},
                child_runner=child,
            )
            self.assertEqual(public["status"], "complete")
            self.assertTrue(public["numeric_outputs_valid"])
            self.assertTrue(all(item["numeric_outputs_valid"] for item in public["corpora"]))
            self.assertTrue((root / run_controls.PUBLIC_RECEIPT_PATH).is_file())
            self.assertTrue((root / run_controls.PRIVATE_RECEIPT_PATH).is_file())

    def test_wrapper_module_does_not_import_study(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                "-c",
                "import sys; import experiments.cyclic_pairing.run_controls; "
                "sys.exit(1 if 'experiments.cyclic_pairing.study' in sys.modules else 0)",
            ],
            cwd=Path(__file__).resolve().parents[2],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self.assertEqual(completed.returncode, 0)


if __name__ == "__main__":
    unittest.main()
