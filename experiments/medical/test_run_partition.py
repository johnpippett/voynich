"""Synthetic tests for the frozen Celsus partition runner."""

from __future__ import annotations

from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from experiments.medical import run_partition as runner


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@contextmanager
def synthetic_fixture(root: Path):
    source_bytes = b"synthetic source bytes\n"
    projection_bytes = b"synthetic projection bytes\n"
    payloads = {
        runner.SOURCE_RELATIVE: source_bytes,
        runner.MODULE_RELATIVE: projection_bytes,
        runner.INDEPENDENT_RELATIVE: projection_bytes,
    }
    source_hash, projection_hash = digest(source_bytes), digest(projection_bytes)
    acceptance = {
        "protocol": "celsus-projection-v1",
        "status": "COMPLETE",
        "result": "PASS",
        "manual_acceptance": "ACCEPTED",
        "source": {"sha256": source_hash},
        "projection": {
            "module": {"sha256": projection_hash},
            "independent": {"sha256": projection_hash},
        },
    }
    for relative in runner.FREEZE_FILES:
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = runner._canonical_json_bytes(acceptance) if relative == runner.ACCEPTANCE_RELATIVE else payloads.get(
            relative, f"synthetic:{relative.as_posix()}\n".encode()
        )
        target.write_bytes(payload)
    entries = [
        {"path": relative.as_posix(), "sha256": digest((root / relative).read_bytes())}
        for relative in runner.FREEZE_FILES
    ]
    freeze = root / runner.FREEZE_RELATIVE
    freeze.parent.mkdir(parents=True, exist_ok=True)
    freeze.write_bytes(
        runner._canonical_json_bytes(
            {"schema_version": 1, "protocol": runner.PROTOCOL, "files": entries}
        )
    )
    fixed = {name: digest((root / Path(name)).read_bytes()) for name in runner.FIXED_HASHES}
    with patch.multiple(
        runner,
        FIXED_HASHES=fixed,
        EXPECTED_ACCEPTANCE_SHA256=fixed[runner.ACCEPTANCE_RELATIVE.as_posix()],
        EXPECTED_INITIAL_SHA256=fixed[runner.INITIAL_RELATIVE.as_posix()],
        EXPECTED_SOURCE_SHA256=source_hash,
        EXPECTED_PROJECTION_SHA256=projection_hash,
        EXPECTED_ORIGINAL_FREEZE_SHA256=fixed["experiments/medical/freeze-v1.json"],
    ):
        yield freeze


class PartitionRunnerTests(unittest.TestCase):
    def test_exact_fixture_allowlist_and_pins_pass(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with synthetic_fixture(root) as freeze:
                preflight = runner.verify_freeze_manifest(freeze, repository_root=root)
                self.assertEqual(set(preflight.files_sha256), {
                    path.as_posix() for path in runner.FREEZE_FILES
                })
                self.assertEqual(
                    preflight.files_sha256[runner.MODULE_RELATIVE.as_posix()],
                    runner.EXPECTED_PROJECTION_SHA256,
                )
                self.assertEqual(preflight.acceptance["manual_acceptance"], "ACCEPTED")

    def test_pinned_mismatch_stops_before_parser_or_adapter(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with synthetic_fixture(root) as freeze:
                source = root / runner.MODULE_RELATIVE
                source.write_bytes(source.read_bytes() + b"changed")
                with patch.object(runner, "_parse_module_records") as parser, patch.object(
                    runner, "_load_adapter", side_effect=AssertionError("adapter imported")
                ) as loader:
                    with self.assertRaisesRegex(runner.PartitionFailure, "pinned byte hash"):
                        runner._run_partition(root, freeze, root / runner.OUTPUT_RELATIVE)
                parser.assert_not_called()
                loader.assert_not_called()

    def test_changed_receipt_is_rejected_by_fixed_hash_before_json_check(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with synthetic_fixture(root) as freeze:
                receipt = root / runner.ACCEPTANCE_RELATIVE
                payload = json.loads(receipt.read_text())
                payload["manual_acceptance"] = "PENDING"
                changed = runner._canonical_json_bytes(payload)
                receipt.write_bytes(changed)
                freeze_payload = json.loads(freeze.read_text())
                for entry in freeze_payload["files"]:
                    if entry["path"] == runner.ACCEPTANCE_RELATIVE.as_posix():
                        entry["sha256"] = digest(changed)
                freeze.write_bytes(runner._canonical_json_bytes(freeze_payload))
                with patch.object(
                    runner, "_verify_acceptance", side_effect=AssertionError("parsed receipt")
                ) as verifier:
                    with self.assertRaisesRegex(runner.PartitionFailure, "required source pin"):
                        runner.verify_freeze_manifest(freeze, repository_root=root)
                verifier.assert_not_called()

    def test_extra_manifest_entry_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with synthetic_fixture(root) as freeze:
                payload = json.loads(freeze.read_text())
                payload["files"].append({"path": "extra", "sha256": "0" * 64})
                freeze.write_bytes(runner._canonical_json_bytes(payload))
                with self.assertRaisesRegex(runner.PartitionFailure, "file list"):
                    runner.verify_freeze_manifest(freeze, repository_root=root)

    def test_source_bytes_are_not_changed_by_preflight(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with synthetic_fixture(root) as freeze:
                source = root / runner.SOURCE_RELATIVE
                before = source.read_bytes()
                runner.verify_freeze_manifest(freeze, repository_root=root)
                self.assertEqual(source.read_bytes(), before)

    def test_output_directory_rejects_existing_and_symlink_components(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            existing = root / runner.OUTPUT_RELATIVE
            existing.mkdir(parents=True)
            with self.assertRaisesRegex(runner.PartitionFailure, "already exists"):
                runner._prepare_output_dir(existing, root)

            existing.rmdir()
            results = root / "results"
            results.rmdir()
            target = root / "real-results"
            target.mkdir()
            results.symlink_to(target, target_is_directory=True)
            with self.assertRaisesRegex(runner.PartitionFailure, "symlink"):
                runner._prepare_output_dir(root / runner.OUTPUT_RELATIVE, root)

    def test_parent_traversal_is_rejected_before_any_directory_creation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            outside = root / "outside"
            traversal = root / "results" / ".." / "outside"
            with self.assertRaisesRegex(runner.PartitionFailure, "parent traversal"):
                runner._prepare_output_dir(traversal, root)
            self.assertFalse(outside.exists())
            self.assertFalse((root / "results").exists())

    def test_public_manifest_is_deterministic_and_has_no_private_arrays(self) -> None:
        preflight = runner._Preflight(
            root=Path.cwd(),
            freeze_path=runner.FREEZE_RELATIVE.as_posix(),
            freeze_sha256="a" * 64,
            files_sha256={"experiments/medical/reference_adapter.py": "b" * 64},
            bytes_by_path={
                runner.SOURCE_RELATIVE.as_posix(): b"source",
                runner.MODULE_RELATIVE.as_posix(): b"module",
                runner.INDEPENDENT_RELATIVE.as_posix(): b"independent",
            },
            acceptance={
                "status": "COMPLETE",
                "result": "PASS",
                "manual_acceptance": "ACCEPTED",
                "source": {"sha256": runner.EXPECTED_SOURCE_SHA256},
                "projection": {
                    "module": {"sha256": runner.EXPECTED_PROJECTION_SHA256},
                    "independent": {"sha256": runner.EXPECTED_PROJECTION_SHA256},
                },
            },
        )
        adapter_manifest = {"schema_version": 1, "partitions": {"train": {"token_count": 2}}}
        kwargs = {"train.private.json": "c" * 64}
        first = runner._public_manifest(preflight, adapter_manifest, kwargs, {"train.private.json": 4})
        second = runner._public_manifest(preflight, adapter_manifest, kwargs, {"train.private.json": 4})
        self.assertEqual(runner._canonical_json_bytes(first), runner._canonical_json_bytes(second))
        encoded = runner._canonical_json_bytes(first)
        self.assertNotIn(b'"tokens"', encoded)
        self.assertNotIn(b'"text"', encoded)
        self.assertFalse(first["raw_text_included"])

    def test_partition_reads_once_and_calls_adapter_once_after_preflight(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            preflight = runner._Preflight(
                root=root,
                freeze_path=runner.FREEZE_RELATIVE.as_posix(),
                freeze_sha256="a" * 64,
                files_sha256={"experiments/medical/reference_adapter.py": "b" * 64},
                bytes_by_path={
                    runner.MODULE_RELATIVE.as_posix(): b"module",
                    runner.SOURCE_RELATIVE.as_posix(): b"source",
                    runner.INDEPENDENT_RELATIVE.as_posix(): b"independent",
                },
                acceptance={
                    "status": "COMPLETE", "result": "PASS", "manual_acceptance": "ACCEPTED",
                    "source": {"sha256": runner.EXPECTED_SOURCE_SHA256},
                    "projection": {
                        "module": {"sha256": runner.EXPECTED_PROJECTION_SHA256},
                        "independent": {"sha256": runner.EXPECTED_PROJECTION_SHA256},
                    },
                },
            )
            adapted = SimpleNamespace(
                partitions={"train": ("a",), "validation": (), "test": ()},
                paragraphs=(), manifest={"schema_version": 1},
            )
            adapter = patch.object(runner, "_load_adapter", return_value=lambda rows: adapted)
            with patch.object(runner, "verify_freeze_manifest", return_value=preflight), patch.object(
                runner, "_parse_module_records", return_value=({"record": 1},)
            ) as parser, adapter as loader, patch.object(
                runner, "_prepare_output_dir"
            ), patch.object(runner, "_write_new") as write:
                runner._run_partition(root, root / runner.FREEZE_RELATIVE, root / runner.OUTPUT_RELATIVE)
            parser.assert_called_once_with(b"module")
            loader.assert_called_once_with()
            self.assertEqual(write.call_count, 3)


if __name__ == "__main__":
    unittest.main()
