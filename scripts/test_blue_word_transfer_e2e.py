"""Run artificial end-to-end checks for the blue-word transfer command."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
E2E_ROOT = ROOT / "results" / "blue-word-transfer-v1" / "e2e"
CLI = ROOT / "scripts" / "check_blue_word_transfer.py"
PLAN_SHA256 = "bfd6126b2f1420dd576dae6f46f5bffc1b7187a88c5f82c0b04ae31a1e6a48a8"
COMMAND = "python scripts/check_blue_word_transfer.py MANIFEST SOURCE_ROOT NEW_OUTPUT"
HARNESS_COMMAND = "python scripts/test_blue_word_transfer_e2e.py NEW_ARTIFACT_DIR"
SOURCE_PATHS = {
    "plant_features": "scripts/04_content/plant_features.py",
    "color_tags": "scripts/04_content/color_crossref.py",
    "corpus": "data/transcription/voynich_nlp.json",
}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def json_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(json_bytes(value))


def make_fixture(base: Path, *, foreign: bool = False, dynamic: bool = False) -> dict[str, Path]:
    source_root = base / "source"
    plant_path = source_root / SOURCE_PATHS["plant_features"]
    color_path = source_root / SOURCE_PATHS["color_tags"]
    corpus_path = source_root / SOURCE_PATHS["corpus"]

    features = {"f1r": {"fixture_feature": True}}
    if dynamic:
        plant_text = "PLANT_FEATURES = make_features()\n"
    else:
        plant_text = "PLANT_FEATURES = " + repr(features) + "\n"
        if foreign:
            plant_text += "raise RuntimeError('source code ran')\n"
    plant_path.parent.mkdir(parents=True, exist_ok=True)
    plant_path.write_text(plant_text, encoding="utf-8")

    color_tags = {
        "f1v": {"B": "fixture"},
        "f8r": {"B": "fixture"},
        "f49r": {"B": "fixture"},
        "f50r": {"R": "fixture"},
        "f51r": {"B": "fixture"},
        "f52r": {"B": "fixture"},
    }
    color_path.parent.mkdir(parents=True, exist_ok=True)
    color_path.write_text("COLOR_TAGS = " + repr(color_tags) + "\n", encoding="utf-8")

    sentences = [
        {"folio": "f1v", "unit": "P0", "words": ["key"] * 4, "raw_lines": []},
        {"folio": "f8r", "unit": "P0", "words": ["key"] * 3, "raw_lines": []},
        {"folio": "f49r", "unit": "P0", "words": ["key", "monkey", "key"], "raw_lines": []},
        {"folio": "f50r", "unit": "P0", "words": ["monkey", "keyed"], "raw_lines": []},
        {"folio": "f51r", "unit": "P0", "words": ["key"], "raw_lines": []},
    ]
    metadata = {
        "f1v": {"folio": "f1v", "illustration": "H", "quire": "A", "page_in_quire": "1", "language": "A", "hand": "1"},
        "f8r": {"folio": "f8r", "illustration": "H", "quire": "A", "page_in_quire": "1", "language": "A", "hand": "1"},
        "f49r": {"folio": "f49r", "illustration": "H", "quire": "G", "page_in_quire": "1", "language": "A", "hand": "1"},
        "f50r": {"folio": "f50r", "illustration": "H", "quire": "G", "page_in_quire": "2", "language": "A", "hand": "1"},
        "f51r": {"folio": "f51r", "illustration": "A", "quire": "G", "page_in_quire": "3", "language": "A", "hand": "1"},
        "f52r": {"folio": "f52r", "illustration": "H", "quire": "G", "page_in_quire": "4", "language": "A", "hand": "1"},
    }
    corpus = {"sentences": sentences, "word_order_report": {}, "variant_analysis": {}, "metadata": metadata}
    write_json(corpus_path, corpus)

    roles = {}
    for role, path in (("plant_features", plant_path), ("color_tags", color_path), ("corpus", corpus_path)):
        roles[role] = {
            "path": SOURCE_PATHS[role],
            "sha256": sha256(path.read_bytes()),
            "url": f"https://example.invalid/fixture/{role}",
        }
    manifest = base / "source-manifest.json"
    write_json(manifest, {"schema_version": 1, "sources": roles})
    return {"source_root": source_root, "manifest": manifest, "corpus": corpus_path}


def refresh_corpus_hash(fixture: dict[str, Path]) -> None:
    manifest = json.loads(fixture["manifest"].read_text(encoding="utf-8"))
    manifest["sources"]["corpus"]["sha256"] = sha256(fixture["corpus"].read_bytes())
    write_json(fixture["manifest"], manifest)


def invoke(fixture: dict[str, Path], output: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), str(fixture["manifest"]), str(fixture["source_root"]), str(output)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def check(name: str, passed: bool, observed: object, expected: object) -> dict:
    return {"name": name, "passed": bool(passed), "observed": observed, "expected": expected}


def result_for(path: Path) -> dict | None:
    if not path.is_file():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def inspect_success(fixture: dict[str, Path], first: Path, second: Path | None = None) -> list[dict]:
    value = result_for(first)
    if value is None:
        return [check("result_is_json", False, False, True)]

    decisions = {item.get("folio"): item for item in value.get("folio_decisions", []) if isinstance(item, dict)}
    categories = value.get("categories", {})
    discovery = value.get("discovery_folios", [])
    result_text = first.read_text(encoding="utf-8")
    blue_totals = {"folio_count": 1, "distinct_group_count": 1, "token_count": 3, "key_count": 2, "folios_with_key": ["f49r"]}
    other_totals = {"folio_count": 1, "distinct_group_count": 1, "token_count": 2, "key_count": 0, "folios_with_key": []}
    expected_kept = {
        "f49r": {"group_id": "49", "category": "blue_tag", "token_count": 3, "key_count": 2},
        "f50r": {"group_id": "50", "category": "no_blue_tag", "token_count": 2, "key_count": 0},
    }
    observed_kept = {
        folio: {key: decisions.get(folio, {}).get(key) for key in expected}
        for folio, expected in expected_kept.items()
    }
    checks = [
        check("status", value.get("status") == "complete", value.get("status"), "complete"),
        check("plan_hash", value.get("plan_sha256") == PLAN_SHA256, value.get("plan_sha256"), PLAN_SHA256),
        check("source_hash_roles", sorted(value.get("source_hashes", {})) == sorted(SOURCE_PATHS), sorted(value.get("source_hashes", {})), sorted(SOURCE_PATHS)),
        check("discovery_folio_and_group", discovery == [{"folio": "f1r", "group_id": "1"}], discovery, [{"folio": "f1r", "group_id": "1"}]),
        check("all_color_folios_recorded", set(decisions) == {"f1v", "f8r", "f49r", "f50r", "f51r", "f52r"}, sorted(decisions), ["f1v", "f49r", "f50r", "f51r", "f52r", "f8r"]),
        check("discovery_group_exclusions", all(decisions.get(folio, {}).get("reason") == "discovery_group" for folio in ("f1v", "f8r")), {folio: decisions.get(folio, {}).get("reason") for folio in ("f1v", "f8r")}, {"f1v": "discovery_group", "f8r": "discovery_group"}),
        check("nonherbal_exclusion", decisions.get("f51r", {}).get("reason") == "nonherbal", decisions.get("f51r", {}).get("reason"), "nonherbal"),
        check("missing_text_exclusion", decisions.get("f52r", {}).get("reason") == "missing_text", decisions.get("f52r", {}).get("reason"), "missing_text"),
        check("kept_folios", {folio for folio, item in decisions.items() if item.get("decision") == "kept"} == {"f49r", "f50r"}, sorted(folio for folio, item in decisions.items() if item.get("decision") == "kept"), ["f49r", "f50r"]),
        check("kept_folio_details", observed_kept == expected_kept, observed_kept, expected_kept),
        check("blue_totals", categories.get("blue_tag") == blue_totals, categories.get("blue_tag"), blue_totals),
        check("other_totals", categories.get("no_blue_tag") == other_totals, categories.get("no_blue_tag"), other_totals),
        check("substring_control", (decisions.get("f50r", {}).get("key_count") == 0 and decisions.get("f49r", {}).get("key_count") == 2), {"f49r": decisions.get("f49r", {}).get("key_count"), "f50r": decisions.get("f50r", {}).get("key_count")}, {"f49r": 2, "f50r": 0}),
        check("no_machine_paths", str(ROOT) not in result_text and str(fixture["source_root"]) not in result_text, str(ROOT) in result_text or str(fixture["source_root"]) in result_text, False),
    ]
    if second is not None:
        checks.append(check("deterministic_result_bytes", first.read_bytes() == second.read_bytes(), sha256(first.read_bytes()), sha256(second.read_bytes())))
    return checks


def run_preimplementation(artifact_dir: Path, baseline: dict | None) -> int:
    with tempfile.TemporaryDirectory(prefix="blue-word-transfer-") as temporary:
        fixture = make_fixture(Path(temporary))
        output = Path(temporary) / "result.json"
        completed = invoke(fixture, output)
        receipt = {
            "schema": "blue-word-transfer-e2e-v1",
            "status": "expected_preimplementation_failure",
            "plan_sha256": PLAN_SHA256,
            "test_script_sha256": sha256(Path(__file__).read_bytes()),
            "command_template": COMMAND,
            "harness_command_template": HARNESS_COMMAND,
            "setup": "Synthetic six-folio source fixture; no production corpus is read.",
            "fixture_schema": "Top-level sentences list and folio-keyed metadata map.",
            "schema_correction": "The first red artifact used an invented folios map. This rerun uses the reviewed sentences and metadata shape.",
            "steps": [
                {
                    "name": "real_cli_before_implementation",
                    "expected": "The command must fail before its implementation exists.",
                    "observed": {
                        "cli_file_present": CLI.is_file(),
                        "exit_code": completed.returncode,
                        "result_created": output.exists(),
                    },
                    "passed": not CLI.exists() and completed.returncode != 0 and not output.exists(),
                }
            ],
            "earlier_failures": baseline,
            "limits": "This run checks only the pre-implementation failure. It makes no corpus count.",
        }
    write_json(artifact_dir / "receipt.json", receipt)
    print("status: expected_preimplementation_failure")
    print("receipt: receipt.json")
    return 1


def run_full_suite(artifact_dir: Path, baseline: dict | None) -> int:
    cases = []
    with tempfile.TemporaryDirectory(prefix="blue-word-transfer-") as temporary:
        fixture = make_fixture(Path(temporary))
        first = Path(temporary) / "first.json"
        second = Path(temporary) / "second.json"
        first_process = invoke(fixture, first)
        second_process = invoke(fixture, second)
        checks = [
            check("first_cli_exit", first_process.returncode == 0, first_process.returncode, 0),
            check("second_cli_exit", second_process.returncode == 0, second_process.returncode, 0),
        ]
        if first_process.returncode == 0 and second_process.returncode == 0:
            checks.extend(inspect_success(fixture, first, second))
        cases.append({"name": "fixed_fixture_and_repeatability", "passed": all(item["passed"] for item in checks), "checks": checks})

    with tempfile.TemporaryDirectory(prefix="blue-word-transfer-") as temporary:
        fixture = make_fixture(Path(temporary), foreign=True)
        output = Path(temporary) / "result.json"
        completed = invoke(fixture, output)
        checks = [check("foreign_code_not_run", completed.returncode == 0 and output.exists(), completed.returncode, 0)]
        if output.exists():
            checks.extend(inspect_success(fixture, output))
        cases.append({"name": "foreign_execution_control", "passed": all(item["passed"] for item in checks), "checks": checks})

    with tempfile.TemporaryDirectory(prefix="blue-word-transfer-") as temporary:
        fixture = make_fixture(Path(temporary))
        fixture["corpus"].write_bytes(fixture["corpus"].read_bytes() + b" ")
        output = Path(temporary) / "result.json"
        completed = invoke(fixture, output)
        checks = [check("altered_source_rejected_without_output", completed.returncode != 0 and not output.exists(), {"exit_code": completed.returncode, "output_created": output.exists()}, {"nonzero": True, "output_created": False})]
        cases.append({"name": "altered_source", "passed": all(item["passed"] for item in checks), "checks": checks})

    with tempfile.TemporaryDirectory(prefix="blue-word-transfer-") as temporary:
        fixture = make_fixture(Path(temporary), dynamic=True)
        output = Path(temporary) / "result.json"
        completed = invoke(fixture, output)
        checks = [check("dynamic_map_rejected_without_output", completed.returncode != 0 and not output.exists(), {"exit_code": completed.returncode, "output_created": output.exists()}, {"nonzero": True, "output_created": False})]
        cases.append({"name": "dynamic_map", "passed": all(item["passed"] for item in checks), "checks": checks})

    with tempfile.TemporaryDirectory(prefix="blue-word-transfer-") as temporary:
        fixture = make_fixture(Path(temporary))
        output = Path(temporary) / "existing.json"
        sentinel = b"keep this file\n"
        output.write_bytes(sentinel)
        completed = invoke(fixture, output)
        checks = [check("existing_output_rejected_unchanged", completed.returncode != 0 and output.read_bytes() == sentinel, {"exit_code": completed.returncode, "bytes_unchanged": output.read_bytes() == sentinel}, {"nonzero": True, "bytes_unchanged": True})]
        cases.append({"name": "existing_output", "passed": all(item["passed"] for item in checks), "checks": checks})

    with tempfile.TemporaryDirectory(prefix="blue-word-transfer-") as temporary:
        fixture = make_fixture(Path(temporary))
        corpus = json.loads(fixture["corpus"].read_text(encoding="utf-8"))
        next(row for row in corpus["sentences"] if row["folio"] == "f49r")["words"] = "key"
        write_json(fixture["corpus"], corpus)
        refresh_corpus_hash(fixture)
        output = Path(temporary) / "result.json"
        completed = invoke(fixture, output)
        checks = [check("malformed_selected_text_rejected_without_output", completed.returncode != 0 and not output.exists(), {"exit_code": completed.returncode, "output_created": output.exists()}, {"nonzero": True, "output_created": False})]
        cases.append({"name": "malformed_selected_text", "passed": all(item["passed"] for item in checks), "checks": checks})

    passed = all(case["passed"] for case in cases)
    receipt = {
        "schema": "blue-word-transfer-e2e-v1",
        "status": "complete" if passed else "failed",
        "plan_sha256": PLAN_SHA256,
        "test_script_sha256": sha256(Path(__file__).read_bytes()),
        "command_template": COMMAND,
        "harness_command_template": HARNESS_COMMAND,
        "setup": "Synthetic six-folio source fixture; no production corpus is read.",
        "fixture_schema": "Top-level sentences list and folio-keyed metadata map.",
        "cases": cases,
        "earlier_failures": baseline,
        "limits": "These checks test the command on artificial inputs. They do not run the production count.",
    }
    write_json(artifact_dir / "receipt.json", receipt)
    print(f"status: {receipt['status']}")
    print(f"cases: {sum(case['passed'] for case in cases)}/{len(cases)}")
    print("receipt: receipt.json")
    return 0 if passed else 1


def read_prior_reds() -> list[dict]:
    records = []
    for name in ("red-initial", "red-fixed-schema"):
        path = E2E_ROOT / name / "receipt.json"
        if not path.is_file():
            continue
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            records.append({"artifact": f"{name}/receipt.json", "valid_receipt": False})
            continue
        records.append({
            "artifact": f"{name}/receipt.json",
            "sha256": sha256(path.read_bytes()),
            "status": value.get("status") if isinstance(value, dict) else None,
            "valid_receipt": isinstance(value, dict) and value.get("status") == "expected_preimplementation_failure",
        })
    return records


def main() -> int:
    parser = argparse.ArgumentParser(description="Run artificial end-to-end checks for blue-word transfer.")
    parser.add_argument("new_artifact_dir", help="new ignored result directory")
    args = parser.parse_args()

    requested = Path(args.new_artifact_dir)
    artifact_dir = requested if requested.is_absolute() else ROOT / requested
    try:
        artifact_dir.resolve().relative_to(E2E_ROOT.resolve())
    except ValueError:
        print("error: artifact directory must be under the fixed E2E result directory", file=sys.stderr)
        return 2
    if artifact_dir.exists():
        print("error: artifact directory already exists", file=sys.stderr)
        return 2
    artifact_dir.mkdir(parents=True, exist_ok=False)

    baseline = read_prior_reds()
    if not CLI.is_file():
        return run_preimplementation(artifact_dir, baseline)
    return run_full_suite(artifact_dir, baseline)


if __name__ == "__main__":
    raise SystemExit(main())
