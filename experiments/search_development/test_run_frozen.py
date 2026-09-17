"""Synthetic tests for the fixed production entrypoint."""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


from experiments.search_development import run_frozen


class FrozenEntrypointTests(unittest.TestCase):
    def _project(self) -> Path:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        for relative in run_frozen.FREEZE_FILES:
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"fixture:{relative}\n", encoding="utf-8")
        manifest = {
            "schema_version": 1,
            "protocol": run_frozen.PROTOCOL,
            "files": [
                {
                    "path": relative.as_posix(),
                    "sha256": run_frozen.sha256_path(root / relative),
                }
                for relative in run_frozen.FREEZE_FILES
            ],
            "command": ["python", "-m", "experiments.search_development.run_frozen"],
            "parameters": dict(run_frozen.EXPECTED_PARAMETERS),
            "resources": dict(run_frozen.EXPECTED_RESOURCES),
            "outputs": {
                "child": [path.as_posix() for path in run_frozen.CHILD_OUTPUT_PATHS],
                "public": run_frozen.PUBLIC_RECEIPT_PATH.as_posix(),
                "private": run_frozen.PRIVATE_RECEIPT_PATH.as_posix(),
            },
            "runtime": {"python": "3.11", "platform": "fixture"},
        }
        freeze_path = root / run_frozen.FREEZE_MANIFEST_PATH
        freeze_path.parent.mkdir(parents=True, exist_ok=True)
        freeze_path.write_bytes(run_frozen.canonical_json_bytes(manifest))
        return root

    def _write_child_outputs(self, root: Path) -> None:
        for relative in run_frozen.CHILD_OUTPUT_PATHS:
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("child\n", encoding="utf-8")

    def test_manifest_verification_checks_exact_files_and_hashes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._copy_fixture(root)
            verified = run_frozen.verify_freeze_manifest(root)
            self.assertEqual(verified["protocol"], run_frozen.PROTOCOL)
            self.assertEqual(verified["manifest_path"], run_frozen.FREEZE_MANIFEST_PATH.as_posix())
            self.assertEqual(len(verified["files"]), len(run_frozen.FREEZE_FILES))
            self.assertNotIn(run_frozen.FREEZE_MANIFEST_PATH.as_posix(), verified["files"])

    def test_manifest_tamper_and_missing_file_stop_before_supervisor(self) -> None:
        for missing in (False, True):
            with self.subTest(missing=missing), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                self._copy_fixture(root)
                target = root / run_frozen.FREEZE_FILES[0]
                if missing:
                    target.unlink()
                else:
                    target.write_text("tampered\n", encoding="utf-8")
                called = False

                def supervisor(*args, **kwargs):
                    nonlocal called
                    called = True
                    raise AssertionError("supervisor must not run")

                with self.assertRaises(run_frozen.FreezeFailure):
                    run_frozen.run_frozen(root, supervisor_fn=supervisor)
                self.assertFalse(called)

    def test_manifest_content_tamper_stops_before_supervisor(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._copy_fixture(root)
            manifest_path = root / run_frozen.FREEZE_MANIFEST_PATH
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["parameters"]["seed"] = 7001
            manifest_path.write_bytes(run_frozen.canonical_json_bytes(manifest))
            called = False

            def supervisor(*args, **kwargs):
                nonlocal called
                called = True

            with self.assertRaises(run_frozen.FreezeFailure):
                run_frozen.run_frozen(root, supervisor_fn=supervisor)
            self.assertFalse(called)

    def test_success_writes_safe_and_private_receipts(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._copy_fixture(root)
            calls = []

            def supervisor(project_root, *, output_paths, limits):
                calls.append((project_root, tuple(output_paths), limits))
                self._write_child_outputs(root)
                return {
                    "public": {
                        "status": "development_only",
                        "reason": "completed",
                        "progress_event_count": 4,
                        "terminal_event_seen": True,
                        "rss_guard": "sampled_proc_rss",
                    },
                    "private": {
                        "return_code": 0,
                        "elapsed_seconds": 1.5,
                        "max_rss_bytes": 123,
                    },
                }

            public = run_frozen.run_frozen(root, supervisor_fn=supervisor)
            self.assertEqual(public["status"], "development_only")
            self.assertTrue(public["numeric_outputs_valid"])
            self.assertEqual(len(calls), 1)
            self.assertEqual(
                calls[0][1],
                tuple(root / path for path in run_frozen.CHILD_OUTPUT_PATHS),
            )
            public_path = root / run_frozen.PUBLIC_RECEIPT_PATH
            private_path = root / run_frozen.PRIVATE_RECEIPT_PATH
            self.assertTrue(public_path.is_file())
            self.assertTrue(private_path.is_file())
            on_disk = json.loads(public_path.read_text(encoding="utf-8"))
            self.assertEqual(on_disk, public)
            private = json.loads(private_path.read_text(encoding="utf-8"))
            self.assertEqual(private["supervisor"]["private"]["max_rss_bytes"], 123)
            self.assertNotIn(str(root), json.dumps(public))
            self.assertNotIn("bound", public)
            self.assertNotIn("score", public)

    def test_resource_failure_keeps_partial_child_files_and_is_not_valid(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._copy_fixture(root)

            def supervisor(project_root, *, output_paths, limits):
                partial = root / run_frozen.CHILD_OUTPUT_PATHS[0]
                partial.parent.mkdir(parents=True, exist_ok=True)
                partial.write_text("partial\n", encoding="utf-8")
                return {
                    "public": {
                        "status": "resource_abstain",
                        "reason": "rss_observed",
                        "progress_event_count": 1,
                        "terminal_event_seen": False,
                        "rss_guard": "sampled_proc_rss",
                    },
                    "private": {"return_code": -15, "terminated_by_supervisor": True},
                }

            public = run_frozen.run_frozen(root, supervisor_fn=supervisor)
            self.assertEqual(public["status"], "resource_abstain")
            self.assertFalse(public["numeric_outputs_valid"])
            self.assertTrue((root / run_frozen.CHILD_OUTPUT_PATHS[0]).is_file())
            self.assertEqual(
                json.loads(
                    (root / run_frozen.PUBLIC_RECEIPT_PATH).read_text(encoding="utf-8")
                )["status"],
                "resource_abstain",
            )

    def test_supervisor_input_and_output_statuses_are_preserved(self) -> None:
        for status in ("input_mismatch", "output_exists"):
            with self.subTest(status=status), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                self._copy_fixture(root)

                def supervisor(project_root, *, output_paths, limits):
                    return {
                        "public": {
                            "status": status,
                            "reason": "fixture",
                        },
                        "private": {},
                    }

                public = run_frozen.run_frozen(root, supervisor_fn=supervisor)
                self.assertEqual(public["status"], status)
                self.assertFalse(public["numeric_outputs_valid"])

    def test_existing_symlink_is_rejected_before_supervisor(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._copy_fixture(root)
            target = root / run_frozen.CHILD_OUTPUT_PATHS[0]
            target.parent.mkdir(parents=True, exist_ok=True)
            target.symlink_to(root / "elsewhere")
            called = False

            def supervisor(*args, **kwargs):
                nonlocal called
                called = True
                raise AssertionError("supervisor must not run")

            with self.assertRaises(FileExistsError):
                run_frozen.run_frozen(root, supervisor_fn=supervisor)
            self.assertFalse(called)

    def test_changed_resource_limit_stops_before_supervisor(self) -> None:
        class DifferentLimits:
            stage_wall_seconds = 1.0
            total_wall_seconds = 2.0
            rss_limit_bytes = 7 * 1024**3
            poll_interval_seconds = 0.25
            terminate_grace_seconds = 5.0
            as_limit_bytes = None
            child_cpu_workers = 1

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._copy_fixture(root)
            called = False

            def supervisor(*args, **kwargs):
                nonlocal called
                called = True

            with self.assertRaises(run_frozen.FreezeFailure):
                run_frozen.run_frozen(
                    root,
                    supervisor_fn=supervisor,
                    limits=DifferentLimits(),
                )
            self.assertFalse(called)

    def test_main_prints_safe_summary_and_maps_failure_to_nonzero(self) -> None:
        safe = {"schema_version": 1, "protocol": run_frozen.PROTOCOL, "status": "development_only"}
        with patch.object(run_frozen, "run_frozen", return_value=safe), patch(
            "builtins.print"
        ) as printer:
            self.assertEqual(run_frozen.main(["--project-root", "/tmp/fixture"]), 0)
        printer.assert_called_once()
        self.assertEqual(json.loads(printer.call_args.args[0]), safe)

    def _copy_fixture(self, root: Path) -> None:
        source = self._project()
        for path in source.rglob("*"):
            relative = path.relative_to(source)
            target = root / relative
            if path.is_file():
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(path.read_bytes())


if __name__ == "__main__":
    unittest.main()
