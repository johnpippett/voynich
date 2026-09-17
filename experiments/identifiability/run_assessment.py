#!/usr/bin/env python3
"""Assess assignments in the fixed Latin homophonic control."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys
from typing import Any, Callable, Iterable, Mapping

ROOT = Path(__file__).resolve().parents[2]
for import_path in (ROOT, ROOT / "src"):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

from experiments.homophonic.controls import encrypt_words, seeded_control_key
from experiments.identifiability.assess import iter_assess_optimum
from experiments.identifiability.threshold import ThresholdProblem
from experiments.lexicon.run_pilot import (
    ALPHABET, canonical_bytes, canonical_hash, objective_summary,
    objective_weights, sha256_path,
)
from voynich.reference import load_reference_partitions


BASELINE = "reports/homophonic-feasibility-v1/latin-cold.json"
BASELINE_SHA256 = "923dba00df53ff05ca88e91362ea44c693d66b8f0824071d85cc5b0d984ba77e"
BASELINE_COMMIT = "ce8b626ab3cf8147829716f7828dff7fceba6cde"
PROTOCOL = "docs/plans/optimal-key-identifiability-v1.md"
CLASSIFICATIONS = ("forced_at_certified_optimum", "ambiguous", "unresolved")


def write_new(path: Path, value: Any) -> None:
    with path.open("xb") as handle:
        handle.write(canonical_bytes(value))


def verify_baseline_files(root: Path) -> tuple[dict, dict]:
    """Check hashes and bind queries to the published baseline records and code."""
    path = root / BASELINE
    if sha256_path(path) != BASELINE_SHA256:
        raise ValueError("baseline report hash does not match the study")
    report = json.loads(path.read_bytes())
    key_path = path.with_suffix(".keys.json")
    if sha256_path(key_path) != report["key_record_sha256"]:
        raise ValueError("baseline key hash does not match the report")
    for source, expected in report["code_sha256"].items():
        if sha256_path(root / source) != expected:
            raise ValueError(f"baseline source hash mismatch: {source}")
    if sha256_path(root / "docs/plans/visual-homophonic-pilot.md") != report["protocol_sha256"]:
        raise ValueError("baseline protocol hash mismatch")
    return report, json.loads(key_path.read_bytes())


def prepare_problem(
    report: Mapping[str, Any],
    key_record: Mapping[str, Any],
    words: Mapping[str, Iterable[str]],
) -> tuple[ThresholdProblem, dict[str, str], int, dict[str, Any]]:
    """Rebuild the fit problem without iterating the test stream."""
    if report.get("kind") != "synthetic_reference_control":
        raise ValueError("baseline is not a reference control")
    if report.get("family") != "cap2" or report.get("seed") != 7000:
        raise ValueError("baseline control does not match the study")
    if report.get("metadata", {}).get("language") != "latin_llct":
        raise ValueError("baseline reference does not match the study")
    solver = report["solver"]
    target = solver["score"]
    if isinstance(target, bool) or not isinstance(target, int) or target < 0:
        raise ValueError("baseline target is invalid")
    if solver.get("score_certified") is not True or not (
        solver["lower_bound"] == target == solver["upper_bound"]
    ):
        raise ValueError("baseline does not certify an optimum")
    if solver["config"].get("capacity") != 2:
        raise ValueError("baseline capacity does not match the study")
    if key_record.get("family") != "cap2" or key_record.get("seed") != 7000:
        raise ValueError("baseline key domain does not match the study")

    train = list(words["train"])
    validation = list(words["validation"])
    planted = seeded_control_key("cap2", 7000)
    cipher = encrypt_words(validation, planted)
    lexicon = set(train)
    streams = {
        "plaintext_train": train,
        "plaintext_validation": validation,
        "cipher_train": encrypt_words(train, planted),
        "cipher_validation": cipher,
    }
    for name, stream in streams.items():
        if canonical_hash(stream) != report["stream_sha256"][name]:
            raise ValueError(f"baseline stream mismatch: {name}")
    if canonical_hash(sorted(lexicon)) != report["train_lexicon"]["sha256"]:
        raise ValueError("baseline lexicon hash mismatch")
    counts = Counter(cipher)
    weights, tokens, types, denominator = objective_weights(counts)
    expected_fit = {
        "sha256": canonical_hash(cipher), "token_count": tokens,
        "type_count": types, "unit_count": len({unit for word in counts for unit in word}),
    }
    if expected_fit != report["fit_input"]:
        raise ValueError("baseline fit input mismatch")
    if denominator != report["objective"]["denominator"]:
        raise ValueError("baseline denominator mismatch")
    key = dict(key_record["key"])
    symbols = {unit for word in counts for unit in word}
    if set(key) != symbols or any(value not in ALPHABET for value in key.values()):
        raise ValueError("baseline map is not total over the fitted domain")
    if any(count > 2 for count in Counter(key.values()).values()):
        raise ValueError("baseline map exceeds capacity")
    if objective_summary(counts, key, lexicon)["score_from_key"] != target:
        raise ValueError("baseline map does not attain its certified score")
    problem = ThresholdProblem(weights, lexicon, ALPHABET, capacity=2)
    certificate = {
        "problem_fingerprint": problem.problem_fingerprint,
        "target": target, "lower_bound": target, "upper_bound": target,
        "score_certified": True,
        "provenance": "Published homophonic solver report with equal global bounds.",
        "implementation_commit": BASELINE_COMMIT,
        "report_sha256": canonical_hash(report),
        "key_record_sha256": canonical_hash(key_record),
        "limit": "The query runner checks scope and hashes. It does not independently prove the global certificate.",
    }
    return problem, key, target, certificate


def source_hashes(root: Path, baseline: Mapping[str, Any]) -> dict[str, str]:
    paths = set(baseline["code_sha256"])
    paths.update(f"experiments/identifiability/{name}.py" for name in (
        "threshold", "assess", "run_assessment",
    ))
    return {path: sha256_path(root / path) for path in sorted(paths)}


def run_assessment(
    report: Mapping[str, Any],
    key_record: Mapping[str, Any],
    words: Mapping[str, Iterable[str]],
    *,
    output_dir: Path,
    node_budget: int = 1000,
    provenance: Mapping[str, Any] | None = None,
    query_iterator: Callable = iter_assess_optimum,
) -> dict[str, Any]:
    """Write all assignment decisions before reading planted assignments for diagnostics."""
    if isinstance(node_budget, bool) or not isinstance(node_budget, int) or node_budget < 0:
        raise ValueError("node budget must be a non-negative integer")
    output_dir = Path(output_dir)
    if output_dir.exists():
        raise FileExistsError("Select a new output directory.")
    problem, key, target, certificate = prepare_problem(report, key_record, words)
    output_dir.mkdir(parents=True, exist_ok=False)
    run_record = {
        "kind": "reference_assignment_identifiability", "language": "latin_llct",
        "family": "cap2", "seed": 7000, "target": target,
        "certificate": certificate, "problem_fingerprint": problem.problem_fingerprint,
        "search_settings_fingerprint": problem.search_settings_fingerprint,
        "symbol_order": list(problem.symbol_order),
        "node_budget_per_query": node_budget,
        "incumbent_key": key, "provenance": dict(provenance or {}),
    }
    write_new(output_dir / "run.json", run_record)
    records = []
    expected_units = list(problem.cipher_symbols)
    for index, record in enumerate(query_iterator(
        problem, key, target, node_budget_per_query=node_budget, certificate=certificate,
    )):
        if index >= len(expected_units) or record["cipher_unit"] != expected_units[index]:
            raise ValueError("query records do not follow the complete unit order")
        if record["classification"] not in CLASSIFICATIONS:
            raise ValueError("query record has an unknown classification")
        unit = record["cipher_unit"]
        write_new(output_dir / f"{unit}.json", record)
        records.append(record)
        print(json.dumps({"unit": unit, "classification": record["classification"],
                          "nodes": record["raw_query"]["nodes"]}), flush=True)
    if len(records) != len(expected_units):
        raise ValueError("query iterator omitted a fitted unit")
    decision = {
        "problem_fingerprint": problem.problem_fingerprint,
        "target": target,
        "counts": dict(Counter(record["classification"] for record in records)),
        "assignments": {record["cipher_unit"]: record["classification"] for record in records},
        "query_sha256": {f"{unit}.json": sha256_path(output_dir / f"{unit}.json")
                         for unit in expected_units},
    }
    write_new(output_dir / "decisions.json", decision)

    # Test scoring and planted-assignment diagnostics start after decisions.json exists.
    planted = seeded_control_key("cap2", 7000)
    test = list(words["test"])
    cipher_test = encrypt_words(test, planted)
    for name, stream in (("plaintext_test", test), ("cipher_test", cipher_test)):
        if canonical_hash(stream) != report["stream_sha256"][name]:
            raise ValueError(f"baseline test stream mismatch: {name}")
    diagnostics = {}
    for label in (*CLASSIFICATIONS, "unobserved"):
        units = ({unit for word in cipher_test for unit in word if unit not in key}
                 if label == "unobserved" else
                 {unit for unit, category in decision["assignments"].items() if category == label})
        positions = correct = 0
        for cipher_word, plain_word in zip(cipher_test, test, strict=True):
            for unit, letter in zip(cipher_word, plain_word, strict=True):
                if unit in units:
                    positions += 1
                    correct += key.get(unit) == letter
        diagnostics[label] = {
            "unit_count": len(units),
            "unit_assignments_correct": sum(key.get(u) == planted["cipher_to_plain"][u] for u in units),
            "test_positions": positions, "test_correct": correct,
            "test_errors": positions - correct,
        }
    result = {
        **run_record, "status": "complete", "decisions_sha256": sha256_path(output_dir / "decisions.json"),
        "decisions": decision, "post_query_diagnostics": diagnostics,
        "limits": [
            "This study follows an inspected control failure. It is not blind validation.",
            "Forced assignments concern one finite objective and domain, not historical truth.",
            "Unknown searches establish neither exclusion nor ambiguity.",
        ],
    }
    write_new(output_dir / "assessment.json", result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    baseline, key = verify_baseline_files(ROOT)
    data = load_reference_partitions(ROOT)["latin_llct"]
    run_assessment(
        baseline, key, data["words"], output_dir=args.output_dir,
        provenance={"code_sha256": source_hashes(ROOT, baseline),
                    "protocol_sha256": sha256_path(ROOT / PROTOCOL)},
    )


if __name__ == "__main__":
    main()
