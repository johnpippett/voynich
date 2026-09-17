"""Synthetic tests for the fixed local-cyclic source runner."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest import mock

from . import run_frozen


ROOT = Path(__file__).resolve().parents[2]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _synthetic_ivtff(source_id: str) -> bytes:
    return (
        "#=IVTFF Eva- synthetic\n"
        f"<{source_id}>\n"
        f"<{source_id}.1,@P0;A> aa.aba.foo<->bar\n"
        f"<{source_id}.2,@P0;A> aa\n"
    ).encode("utf-8")


class RunnerFixture:
    def __init__(self, path: Path) -> None:
        self.root = path
        self._copy_frozen_inputs()

    def _copy_frozen_inputs(self) -> None:
        for relative in run_frozen.FROZEN_FILES:
            destination = self.root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            if relative == "data/raw/ZL3b-n.txt":
                destination.write_bytes(_synthetic_ivtff("ZL3b"))
            elif relative == "data/raw/IT2a-n.txt":
                destination.write_bytes(_synthetic_ivtff("IT2a"))
            elif relative == "docs/plans/vms-local-cyclic-falsification-v1.md":
                destination.write_text("synthetic frozen plan\n", encoding="utf-8")
            elif relative == "data/source_manifest.json":
                destination.write_text("{}\n", encoding="utf-8")
            else:
                source = ROOT / relative
                destination.write_bytes(source.read_bytes())
        (self.root / "experiments" / "__init__.py").write_text("", encoding="utf-8")
        (self.root / "experiments" / "homophonic" / "__init__.py").write_text(
            "", encoding="utf-8"
        )
        self.write_freeze()

    def write_freeze(self, *, mutate: str | None = None) -> None:
        entries = []
        for relative in run_frozen.FROZEN_FILES:
            path = self.root / relative
            digest = _sha256(path)
            if relative == mutate:
                digest = "0" * 64
            entries.append({"path": relative, "sha256": digest})
        manifest = {
            "schema_version": 1,
            "protocol": run_frozen.PROTOCOL,
            "command": ["python", "-m", "experiments.local_cyclic.run_frozen"],
            "uncertain_spaces": "split",
            "source_ids": ["ZL3b-n", "IT2a-n"],
            "unitizations": ["raw_eva", "visual_six"],
            "outputs": [path.as_posix() for path in run_frozen.OUTPUT_PATHS],
            "runtime": {"python": "synthetic"},
            "files": entries,
        }
        freeze = self.root / run_frozen.FREEZE_RELATIVE
        freeze.parent.mkdir(parents=True, exist_ok=True)
        freeze.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


class RunnerTests(unittest.TestCase):
    def test_manifest_allowlist_excludes_itself_and_has_fixed_inputs(self) -> None:
        self.assertNotIn(run_frozen.FREEZE_RELATIVE, run_frozen.FROZEN_FILES)
        self.assertEqual(len(run_frozen.FROZEN_FILES), 13)
        self.assertEqual(
            run_frozen.OUTPUT_RELATIVES,
            (
                "results/vms-local-cyclic-falsification-v1/ZL3b-n-raw_eva.json",
                "results/vms-local-cyclic-falsification-v1/ZL3b-n-visual_six.json",
                "results/vms-local-cyclic-falsification-v1/IT2a-n-raw_eva.json",
                "results/vms-local-cyclic-falsification-v1/IT2a-n-visual_six.json",
            ),
        )

    def test_hash_gate_rejects_pinned_byte_mismatch_before_import(self) -> None:
        with TemporaryDirectory() as temporary:
            fixture = RunnerFixture(Path(temporary))
            fixture.write_freeze(mutate="experiments/local_cyclic/certificate.py")
            with self.assertRaises(run_frozen.FreezeError):
                run_frozen.verify_freeze(fixture.root)

    def test_hash_gate_rejects_before_parser_or_source_work(self) -> None:
        with TemporaryDirectory() as temporary:
            fixture = RunnerFixture(Path(temporary))
            fixture.write_freeze(mutate="data/raw/ZL3b-n.txt")
            with mock.patch.object(run_frozen, "_load_runtime") as load_runtime:
                with self.assertRaises(run_frozen.FreezeError):
                    run_frozen.run_frozen(fixture.root)
            load_runtime.assert_not_called()

    def test_synthetic_records_sum_repeated_word_indexes_and_keep_locations(self) -> None:
        with TemporaryDirectory() as temporary:
            fixture = RunnerFixture(Path(temporary))
            reports = run_frozen.run_frozen(fixture.root)
            self.assertEqual(len(reports), 4)
            report = reports[("ZL3b-n", "raw_eva")]
            self.assertEqual(
                report["counts"],
                {
                    "record_count": 2,
                    "eligible_word_count": 3,
                    "eligible_unit_count": 7,
                    "adjacent_pair_count": 4,
                    "certificate_count": 2,
                    "affected_word_count": 2,
                },
            )
            self.assertEqual(report["counts"]["affected_word_count"], 2)
            self.assertEqual(report["counts"]["certificate_count"], 2)
            self.assertEqual(len(report["certificate_locations"]), 2)
            self.assertEqual(
                [(item["record_index"], item["candidate_word_index"])
                 for item in report["certificate_locations"]],
                [(0, 0), (1, 0)],
            )
            self.assertNotIn("tokens", json.dumps(report))
            self.assertNotIn("surface", json.dumps(report))
            self.assertEqual(report["status"], "falsified_for_fixed_track")
            self.assertEqual(
                report["counts"]["eligible_word_count"],
                reports[("ZL3b-n", "visual_six")]["counts"]["eligible_word_count"],
            )
            self.assertEqual(report["excluded_word_counts"], {"diagram_marker": 1})
            self.assertEqual(
                report["excluded_word_counts"],
                reports[("ZL3b-n", "visual_six")]["excluded_word_counts"],
            )

    def test_visual_location_contains_only_half_open_unit_span(self) -> None:
        with TemporaryDirectory() as temporary:
            fixture = RunnerFixture(Path(temporary))
            reports = run_frozen.run_frozen(fixture.root)
            location = reports[("IT2a-n", "visual_six")]["certificate_locations"][0]
            self.assertEqual(location["unit_span"], [0, 1])
            self.assertEqual(location["unit"], "a")

    def test_runner_refuses_existing_output_before_source_work(self) -> None:
        with TemporaryDirectory() as temporary:
            fixture = RunnerFixture(Path(temporary))
            output = fixture.root / run_frozen.OUTPUT_RELATIVES[0]
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text("sentinel\n", encoding="utf-8")
            with self.assertRaises(run_frozen.OutputExistsError):
                run_frozen.run_frozen(fixture.root)
            self.assertEqual(output.read_text(encoding="utf-8"), "sentinel\n")

    def test_runner_refuses_symlinked_output_directory(self) -> None:
        with TemporaryDirectory() as temporary:
            fixture = RunnerFixture(Path(temporary))
            results = fixture.root / "results"
            results.symlink_to(fixture.root / "elsewhere", target_is_directory=True)
            with self.assertRaises(run_frozen.OutputExistsError):
                run_frozen.run_frozen(fixture.root)

    def test_cli_runs_with_no_options_in_a_disposable_project(self) -> None:
        with TemporaryDirectory() as temporary:
            fixture = RunnerFixture(Path(temporary))
            environment = dict(os.environ)
            environment["PYTHONPATH"] = str(fixture.root)
            completed = subprocess.run(
                [sys.executable, "-m", "experiments.local_cyclic.run_frozen"],
                cwd=fixture.root,
                env=environment,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(len(list((fixture.root / "results").rglob("*.json"))), 4)


if __name__ == "__main__":
    unittest.main()
