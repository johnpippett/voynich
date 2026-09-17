"""Synthetic tests for the cyclic quotient outer supervisor."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest import mock

from . import run_frozen


ROOT = Path(__file__).resolve().parents[2]


def _digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _json_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def _stub_control_study() -> bytes:
    return (
        "import argparse, hashlib, json\n"
        "from pathlib import Path\n"
        "p=argparse.ArgumentParser(); p.add_argument('--corpus', required=True); "
        "p.add_argument('--output-dir', required=True); a=p.parse_args()\n"
        "root=Path.cwd(); raw=(root/'experiments/cyclic_quotient/freeze-v1.json').read_bytes()\n"
        "freeze=hashlib.sha256(raw).hexdigest(); out=Path(a.output_dir); out.mkdir(parents=True, exist_ok=True)\n"
        "q={'protocol':'cyclic-quotient-recovery-v1','record_kind':'aggregate_cyclic_quotient_evidence',"
        "'corpus':a.corpus,'freeze_manifest_sha256':freeze,"
        "'quotient_status':'ambiguous','declared_unit_count':52,'declared_units_sha256':'" +
        run_frozen.EXPECTED_DECLARED_UNITS_SHA256 + "','observed_units':[],'unseen_units':" +
        repr(list(run_frozen.UNITS)) + ","
        "'classes':[],'forced_pairs':[],'singleton_units':[],'unknown_edges':[]}\n"
        "(out/'quotient.json').write_bytes((json.dumps(q,sort_keys=True,separators=(',',':'))+'\\n').encode())\n"
    ).encode()


def _write_json(path: Path, value: object) -> str:
    raw = _json_bytes(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return _digest(raw)


def _write_proved_outputs(root: Path, corpus: str, *, infeasible: bool = False) -> None:
    output = root / run_frozen.RESULTS_ROOT / corpus
    observed = list(run_frozen.UNITS)
    classes = [[observed[index], observed[index + 1]] for index in range(0, 52, 2)]
    quotient = {
        "protocol": run_frozen.PROTOCOL,
        "record_kind": "aggregate_cyclic_quotient_evidence",
        "corpus": corpus,
        "quotient_status": "proved",
        "declared_unit_count": 52,
        "declared_units_sha256": run_frozen.EXPECTED_DECLARED_UNITS_SHA256,
        "observed_units": observed,
        "unseen_units": [],
        "observed_unit_count": 52,
        "unseen_unit_count": 0,
        "classes": classes,
        "forced_pairs": classes,
        "singleton_units": [],
        "unknown_edges": [],
    }
    quotient_hash = _write_json(output / "quotient.json", quotient)
    status = "infeasible_capacity" if infeasible else "bound_certified"
    solver = {
        "status": status,
        "feasible": not infeasible,
        "score_certified": not infeasible,
        "search_exhausted": True if infeasible else False,
        "lower_bound": None if infeasible else 7,
        "upper_bound": None if infeasible else 7,
        "score": None if infeasible else 7,
    }
    fit = {
        "protocol": run_frozen.PROTOCOL,
        "record_kind": "aggregate_quotient_lexicon_fit",
        "status": status,
        "quotient_evidence_sha256": quotient_hash,
        "open_slot_count": 0,
        "solver": solver,
        "solver_config": {"capacity": 1, "bound_engine": "bitset", "node_budget": 100_000},
        "class_count": 26,
        "observed_unit_count": 52,
    }
    _write_json(output / "fit.json", fit)
    if infeasible:
        return
    class_key = {"+".join(pair): chr(97 + index) for index, pair in enumerate(classes)}
    observed_key = {
        unit: class_key["+".join(pair)]
        for pair in classes
        for unit in pair
    }
    key = {
        "protocol": run_frozen.PROTOCOL,
        "record_kind": "complete_observed_quotient_key",
        "quotient_status": "proved",
        "quotient_evidence_sha256": quotient_hash,
        "open_slot_count": 0,
        "class_names": sorted(class_key),
        "class_members": {name: name.split("+") for name in sorted(class_key)},
        "class_key": class_key,
        "observed_unit_key": observed_key,
        "coverage": {
            "declared_unit_count": 52,
            "observed_unit_count": 52,
            "unseen_unit_count": 0,
            "mapped_observed_units": 52,
        },
        "fit_status": status,
        "score_certified": True,
    }
    _write_json(output / "fit.keys.json", key)
    partition = {
        "character": {"correct": 3, "denominator": 4},
        "word": {"correct": 1, "denominator": 2},
        "coverage": {
            "mapped_positions": 4,
            "total_positions": 4,
            "unexplained_positions": 0,
            "complete_words": 2,
            "word_denominator": 2,
        },
        "dictionary_hits": {
            "hits": 1,
            "denominator": 2,
            "complete_word_denominator": 2,
        },
    }
    diagnostics = {
        "record_type": "diagnostics",
        "protocol": run_frozen.PROTOCOL,
        "corpus": corpus,
        "status": "complete",
        "freeze_manifest_sha256": "b" * 64,
        "source_manifest_sha256": "c" * 64,
        "source_file_hashes": {"source.conllu": "d" * 64},
        "code_hashes": {"study.py": "e" * 64},
        "quotient_evidence_sha256": quotient_hash,
        "fit_status": status,
        "completion": "complete",
        "score_certified": True,
        "lower_bound": 7,
        "upper_bound": 7,
        "settings": {
            "bound_engine": "bitset",
            "fit_capacity": 1,
            "quotient_node_budget": 100_000,
            "solver_node_budget": 100_000,
        },
        "validation": partition,
        "test": partition,
        "postfit_planted_map": {
            "correct": 52,
            "denominator": 52,
            "observed_unit_count": 52,
            "unseen_unit_count": 0,
        },
    }
    _write_json(output / "diagnostics.json", diagnostics)


class Fixture:
    def __init__(self, root: Path) -> None:
        self.root = root
        self._write_inputs()

    def _write_inputs(self) -> None:
        for relative in run_frozen.FREEZE_FILES:
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            if relative.as_posix() == "experiments/cyclic_quotient/control_study.py":
                payload = _stub_control_study()
            elif relative.as_posix() == "experiments/cyclic_quotient/test_control_study.py":
                payload = b"import unittest\nclass ControlStudyTests(unittest.TestCase):\n def test_stub(self): self.assertTrue(True)\n"
            elif relative.suffix == ".py" and (ROOT / relative).is_file():
                payload = (ROOT / relative).read_bytes()
            else:
                payload = f"synthetic:{relative.as_posix()}\n".encode()
            path.write_bytes(payload)
        (self.root / "experiments" / "__init__.py").write_text("", encoding="utf-8")
        (self.root / "experiments" / "homophonic" / "__init__.py").write_text("", encoding="utf-8")
        (self.root / "experiments" / "lexicon" / "__init__.py").write_text("", encoding="utf-8")
        self.write_freeze()

    def write_freeze(self, *, mutate: str | None = None) -> None:
        entries = []
        for relative in run_frozen.FREEZE_FILES:
            path = self.root / relative
            value = _digest(path.read_bytes())
            if relative.as_posix() == mutate:
                value = "0" * 64
            entries.append({"path": relative.as_posix(), "sha256": value})
        manifest = {
            "schema_version": 1,
            "protocol": run_frozen.PROTOCOL,
            "command": list(run_frozen.EXPECTED_COMMAND),
            "child_command": list(run_frozen.EXPECTED_CHILD_COMMAND),
            "parameters": dict(run_frozen.EXPECTED_PARAMETERS),
            "resources": dict(run_frozen.EXPECTED_RESOURCES),
            "runtime": {
                "freeze_python": platform.python_version(),
                "implementation": platform.python_implementation(),
                "platform": platform.platform(),
            },
            "outputs": {
                "corpora": list(run_frozen.CORPORA),
                "corpus": [path.as_posix() for path in run_frozen.CORPUS_OUTPUT_PATHS],
                "public": run_frozen.PUBLIC_RECEIPT_PATH.as_posix(),
                "private": run_frozen.PRIVATE_RECEIPT_PATH.as_posix(),
            },
            "files": entries,
        }
        path = self.root / run_frozen.FREEZE_MANIFEST_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(_json_bytes(manifest))


class RunnerTests(unittest.TestCase):
    def test_fixed_command_and_outputs(self) -> None:
        self.assertEqual(
            run_frozen.EXPECTED_CHILD_COMMAND,
            (
                "python", "-m", "experiments.cyclic_quotient.control_study",
                "--corpus", "{corpus}", "--output-dir",
                "results/cyclic-quotient-recovery-v1/{corpus}",
            ),
        )
        self.assertNotIn(run_frozen.FREEZE_MANIFEST_PATH, run_frozen.FREEZE_FILES)
        self.assertEqual(len(run_frozen.CORPUS_OUTPUT_PATHS), 8)

    def test_freeze_verification_checks_allowlist_and_runtime(self) -> None:
        with TemporaryDirectory() as temporary:
            fixture = Fixture(Path(temporary))
            result = run_frozen.verify_freeze_manifest(fixture.root)
            self.assertEqual(result["file_count"], len(run_frozen.FREEZE_FILES))
            self.assertRegex(result["manifest_sha256"], r"^[0-9a-f]{64}$")

    def test_freeze_mismatch_happens_before_child_or_source_work(self) -> None:
        with TemporaryDirectory() as temporary:
            fixture = Fixture(Path(temporary))
            fixture.write_freeze(mutate="data/reference_manifest.json")
            with mock.patch.object(run_frozen, "run_synthetic_tests") as synthetic:
                with mock.patch.object(run_frozen, "launch_child") as child:
                    with self.assertRaises(run_frozen.FreezeFailure):
                        run_frozen.run_controls(fixture.root)
            synthetic.assert_not_called()
            child.assert_not_called()

    def test_non_linux_guard_runs_before_freeze_read(self) -> None:
        with TemporaryDirectory() as temporary:
            fixture = Fixture(Path(temporary))
            with mock.patch.object(run_frozen.platform, "system", return_value="Darwin"):
                with mock.patch.object(run_frozen, "verify_freeze_manifest") as verify:
                    with self.assertRaises(run_frozen.ResourceFailure):
                        run_frozen.run_controls(fixture.root)
            verify.assert_not_called()

    def test_preflight_refuses_existing_output_and_symlink_parent(self) -> None:
        with TemporaryDirectory() as temporary:
            fixture = Fixture(Path(temporary))
            output = fixture.root / run_frozen.CORPUS_OUTPUT_PATHS[0]
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text("sentinel", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                run_frozen.preflight_outputs(fixture.root)
        with TemporaryDirectory() as temporary:
            fixture = Fixture(Path(temporary))
            (fixture.root / "results").symlink_to(fixture.root / "elsewhere", target_is_directory=True)
            with self.assertRaises(FileExistsError):
                run_frozen.preflight_outputs(fixture.root)

    def test_abstention_with_only_proved_quotient_is_numeric_valid(self) -> None:
        with TemporaryDirectory() as temporary:
            fixture = Fixture(Path(temporary))

            def child(root: Path, corpus: str, *, resources):
                output = root / run_frozen.RESULTS_ROOT / corpus
                output.mkdir(parents=True, exist_ok=True)
                value = {
                    "protocol": run_frozen.PROTOCOL,
                    "record_kind": "aggregate_cyclic_quotient_evidence",
                    "corpus": corpus,
                    "freeze_manifest_sha256": _digest(
                        (root / run_frozen.FREEZE_MANIFEST_PATH).read_bytes()
                    ),
                    "quotient_status": "ambiguous",
                    "declared_unit_count": 52,
                    "declared_units_sha256": run_frozen.EXPECTED_DECLARED_UNITS_SHA256,
                    "observed_units": [], "unseen_units": list(run_frozen.UNITS), "classes": [],
                    "forced_pairs": [], "singleton_units": [], "unknown_edges": [],
                }
                (output / "quotient.json").write_bytes(_json_bytes(value))
                return {"returncode": 0, "termination_reason": None}

            public = run_frozen.run_controls(
                fixture.root,
                synthetic_runner=lambda _root: {"status": "pass", "count": 1},
                child_runner=child,
            )
            self.assertEqual(public["status"], "complete")
            self.assertTrue(public["numeric_outputs_valid"])
            self.assertTrue((fixture.root / run_frozen.PUBLIC_RECEIPT_PATH).is_file())

    def test_resource_stop_is_publicly_recorded_without_retry(self) -> None:
        with TemporaryDirectory() as temporary:
            fixture = Fixture(Path(temporary))
            calls = []

            def child(root: Path, corpus: str, *, resources):
                calls.append(corpus)
                return {
                    "returncode": -15,
                    "termination_reason": "rss_limit",
                    "elapsed_seconds": 0.1,
                    "max_rss_bytes": 7 * 1024**3,
                }

            public = run_frozen.run_controls(
                fixture.root,
                synthetic_runner=lambda _root: {"status": "pass", "count": 1},
                child_runner=child,
            )
            self.assertEqual(calls, ["latin", "italian"])
            self.assertEqual(public["status"], "resource_abstain")
            self.assertFalse(public["numeric_outputs_valid"])
            self.assertTrue((fixture.root / run_frozen.PUBLIC_RECEIPT_PATH).is_file())

    def test_cli_uses_fixed_no_option_command_in_disposable_project(self) -> None:
        with TemporaryDirectory() as temporary:
            fixture = Fixture(Path(temporary))
            env = dict(os.environ)
            env["PYTHONPATH"] = str(fixture.root)
            completed = subprocess.run(
                [sys.executable, "-m", "experiments.cyclic_quotient.run_frozen"],
                cwd=fixture.root, env=env, check=False,
                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, text=True,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertTrue((fixture.root / run_frozen.PUBLIC_RECEIPT_PATH).is_file())


if __name__ == "__main__":
    unittest.main()
