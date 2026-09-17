#!/usr/bin/env python3
"""Build the public Italian search-development report from pinned outputs."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_DIR = ROOT / "reports" / "homophonic-search-development-v1"
OUTPUT = ROOT / "reports" / "HOMOPHONIC_SEARCH_DEVELOPMENT.md"

EXPECTED_OUTPUT_HASHES = {
    "manifest.json": "4985b91f18a3d6b81ec7de3c63d349ad979217b7c25b041c7bedfde5cc55d190",
    "cold_selected.key.json": "91ffd14f8bc5b6dc94b2cf31cbc1e63488bafdbf5b8618d79b429ce816167de8",
    "assisted_selected.key.json": "d77a7fb931ebf1222c496afcb38a5dd5fe887c19e5eea9f368c5af8fb4a90251",
    "aggregate.json": "1a7c224f08e2e0483edc5be851c69cf13ca198b2e19889d4535929a717511ce7",
    "supervision.json": "0c856c39cf0bf2b223908048cc80b9912f534f5176b305f3fbec9e46e0d83446",
}
EXPECTED_REPLAY_HASH = (
    "1ccdc907e8fe43635190d45a22fc4c0242e15eb8e22dbf797e35dc4d965f326c"
)
EXPECTED_PROTOCOL_SHA256 = (
    "d44a1a2208d4b90a5d8e1ce13ff9d090ba88b24fa35184328c76dc84caf91821"
)
EXPECTED_FREEZE_MANIFEST_SHA256 = (
    "eb880ec0efaa31b500cd540e886b82090963b624f97f609ad3e8f010ea0afed7"
)
EXPECTED_WEIGHTED_COUNTS_SHA256 = (
    "664b6498a147b5430695ec0f0ee276c654fabd6a9e567b4960eb7d1f56fad944"
)
EXPECTED_LEXICON_SHA256 = (
    "29d94e0de2a154071c15a9c524a1bb0b73ba2c3a618935be8716e8d3a32824ef"
)
EXPECTED_STREAM_SHA256 = (
    "d7e9c6e0b716cf7ea1c7deb4f135ca2692ea70b4f927548e99668ab0c1428492"
)
EXPECTED_INPUT = {
    "validation_token_count": 31_681,
    "validation_type_count": 14_170,
    "training_lexicon_type_count": 6_273,
    "cipher_unit_count": 47,
    "objective_denominator": 897_839_540,
}
EXPECTED_ROOT = {
    "candidate_row_count": 12_549_021,
    "group_bound": 892_887_632,
    "independent_bound": 896_647_414,
    "group_count": 39,
    "storage_estimate_bytes": 1_759_288_862,
}
EXPECTED_STARTS = {
    "cold_selected": {
        "initial_score": 90_866_594,
        "final_score": 166_057_138,
        "score_improvement": 75_190_544,
        "accepted_move_count": 8,
        "evaluation_count": 9_584,
    },
    "assisted_selected": {
        "initial_score": 222_253_278,
        "final_score": 565_215_014,
        "score_improvement": 342_961_736,
        "accepted_move_count": 8,
        "evaluation_count": 9_584,
    },
}
EXPECTED_PRIOR_FRONTIER_UPPER_BOUND = 815_036_950
EXPECTED_COMMIT = "46798173ee9efe96d00c480d8aabf75540211d42"
EXPECTED_CI_RUN = "35211177386"
EXPECTED_CI_URL = "https://github.com/johnpippett/voynich/actions/runs/35211177386"
EXPECTED_FIRST_START = "2026-09-17T10:35:59.552720Z"
PRIOR_REPORT_DIR = ROOT / "reports" / "homophonic-feasibility-v1"
EXPECTED_PRIOR_REPORT_HASHES = {
    "italian-cold.json": "4209022e13399bb7347b8f1d098f43c4d0922ae1b9c6df72382ed5553b44b0b3",
    "italian-assisted.json": "461ddb0d5f097227d7d521436a3a6ebb459b8d53de973ed2e1e913af3be42f31",
}
EXPECTED_PRIOR_PROTOCOL_SHA256 = (
    "0e6a6edf5e0172f5e7a0f1fbf2f7ede8b9b181c7180aa616de58f44ae04d1249"
)
ALPHABET = tuple("abcdefghijklmnopqrstuvwxyz")
EXPECTED_CHILD_NAMES = (
    "manifest.json",
    "cold_selected.key.json",
    "assisted_selected.key.json",
    "aggregate.json",
)
FORBIDDEN_PUBLIC_KEYS = {
    "words",
    "ciphertext",
    "ciphertext_counts",
    "weighted_counts",
    "training_lexicon",
    "lexicon",
    "candidate_rows",
    "candidate_cache",
    "groups",
    "ungrouped_words",
    "evaluations",
    "accepted_moves",
}


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def integer(value: Any, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field} must be an integer")
    return value


def mapping(value: Any, *, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{field} must be an object")
    return value


def required_equal(value: Any, expected: Any, *, field: str) -> None:
    if value != expected:
        raise ValueError(f"{field} does not match the pinned value")


def verify_output_hashes() -> dict[str, str]:
    """Verify output bytes before any JSON decoding."""

    actual: dict[str, str] = {}
    for name, expected in EXPECTED_OUTPUT_HASHES.items():
        path = PUBLIC_DIR / name
        if not path.is_file() or path.is_symlink():
            raise FileNotFoundError(f"Missing public output: {path}")
        digest = sha256_bytes(path.read_bytes())
        if digest != expected:
            raise ValueError(f"Pinned output hash mismatch: {name}")
        actual[name] = digest
    return actual


def load_verified_json(name: str) -> dict[str, Any]:
    path = PUBLIC_DIR / name
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Public output is not an object: {name}")
    return value


def verify_prior_report_hashes() -> dict[str, str]:
    """Verify the prior frontier report bytes before any JSON decoding."""

    actual: dict[str, str] = {}
    for name, expected in EXPECTED_PRIOR_REPORT_HASHES.items():
        path = PRIOR_REPORT_DIR / name
        if not path.is_file() or path.is_symlink():
            raise FileNotFoundError(f"Missing pinned prior report: {path}")
        digest = sha256_bytes(path.read_bytes())
        if digest != expected:
            raise ValueError(f"Pinned prior report hash mismatch: {name}")
        actual[name] = digest
    return actual


def load_verified_prior_json(name: str) -> dict[str, Any]:
    path = PRIOR_REPORT_DIR / name
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Pinned prior report is not an object: {name}")
    return value


def validate_prior_report(report: Mapping[str, Any], name: str) -> int:
    """Validate the shared identity and frontier bound in one pinned report."""

    prefix = f"prior.{name}"
    required_equal(report.get("kind"), "synthetic_reference_control", field=f"{prefix}.kind")
    required_equal(report.get("family"), "cap2", field=f"{prefix}.family")
    required_equal(report.get("seed"), 7000, field=f"{prefix}.seed")
    required_equal(report.get("protocol_sha256"), EXPECTED_PRIOR_PROTOCOL_SHA256, field=f"{prefix}.protocol_sha256")

    fit_input = mapping(report.get("fit_input"), field=f"{prefix}.fit_input")
    for field, expected in {
        "sha256": EXPECTED_STREAM_SHA256,
        "token_count": EXPECTED_INPUT["validation_token_count"],
        "type_count": EXPECTED_INPUT["validation_type_count"],
        "unit_count": EXPECTED_INPUT["cipher_unit_count"],
    }.items():
        required_equal(fit_input.get(field), expected, field=f"{prefix}.fit_input.{field}")

    lexicon = mapping(report.get("train_lexicon"), field=f"{prefix}.train_lexicon")
    required_equal(lexicon.get("sha256"), EXPECTED_LEXICON_SHA256, field=f"{prefix}.train_lexicon.sha256")
    required_equal(lexicon.get("type_count"), EXPECTED_INPUT["training_lexicon_type_count"], field=f"{prefix}.train_lexicon.type_count")

    stream_hashes = mapping(report.get("stream_sha256"), field=f"{prefix}.stream_sha256")
    required_equal(stream_hashes.get("cipher_validation"), EXPECTED_STREAM_SHA256, field=f"{prefix}.stream_sha256.cipher_validation")

    encryption = mapping(report.get("encryption"), field=f"{prefix}.encryption")
    required_equal(encryption.get("alphabet"), list(ALPHABET), field=f"{prefix}.encryption.alphabet")
    required_equal(encryption.get("family"), "cap2", field=f"{prefix}.encryption.family")
    required_equal(encryption.get("seed"), 7000, field=f"{prefix}.encryption.seed")

    objective = mapping(report.get("objective"), field=f"{prefix}.objective")
    for field, expected in {
        "N_token_count": EXPECTED_INPUT["validation_token_count"],
        "T_type_count": EXPECTED_INPUT["validation_type_count"],
        "denominator": EXPECTED_INPUT["objective_denominator"],
        "normalization_formula": "2*T*N",
        "weight_formula": "count*T+N",
        "weights_total": EXPECTED_INPUT["objective_denominator"],
        "weights_match_denominator": True,
    }.items():
        required_equal(objective.get(field), expected, field=f"{prefix}.objective.{field}")
    score = integer(objective.get("score_from_key"), field=f"{prefix}.objective.score_from_key")

    solver = mapping(report.get("solver"), field=f"{prefix}.solver")
    solver_config = mapping(solver.get("config"), field=f"{prefix}.solver.config")
    required_equal(solver_config.get("capacity"), 2, field=f"{prefix}.solver.config.capacity")
    required_equal(solver_config.get("objective"), "integer weighted exact lexicon word hits", field=f"{prefix}.solver.config.objective")
    required_equal(solver.get("total_weight"), EXPECTED_INPUT["objective_denominator"], field=f"{prefix}.solver.total_weight")
    required_equal(solver.get("upper_bound"), EXPECTED_PRIOR_FRONTIER_UPPER_BOUND, field=f"{prefix}.solver.upper_bound")
    required_equal(solver.get("lower_bound"), score, field=f"{prefix}.solver.lower_bound")
    required_equal(solver.get("score"), score, field=f"{prefix}.solver.score")
    required_equal(solver.get("status"), "budget_exhausted", field=f"{prefix}.solver.status")
    required_equal(solver.get("score_certified"), False, field=f"{prefix}.solver.score_certified")
    required_equal(solver.get("search_exhausted"), False, field=f"{prefix}.solver.search_exhausted")
    required_equal(solver.get("nodes"), 1_000, field=f"{prefix}.solver.nodes")
    return integer(solver.get("upper_bound"), field=f"{prefix}.solver.upper_bound")


def validate_prior_reports(reports: Mapping[str, Mapping[str, Any]]) -> int:
    if set(reports) != set(EXPECTED_PRIOR_REPORT_HASHES):
        raise ValueError("Pinned prior report set does not match the fixed pair")
    upper_bounds = {
        name: validate_prior_report(report, name)
        for name, report in reports.items()
    }
    if set(upper_bounds.values()) != {EXPECTED_PRIOR_FRONTIER_UPPER_BOUND}:
        raise ValueError("Pinned prior frontier bounds do not match")
    return next(iter(upper_bounds.values()))


def verify_replay_hash() -> str:
    path = PUBLIC_DIR / "replay-verification.json"
    if not path.is_file() or path.is_symlink():
        raise FileNotFoundError(f"Missing replay receipt: {path}")
    digest = sha256_bytes(path.read_bytes())
    if digest != EXPECTED_REPLAY_HASH:
        raise ValueError("Pinned replay receipt hash mismatch")
    return digest


def load_verified_replay() -> dict[str, Any]:
    value = json.loads(
        (PUBLIC_DIR / "replay-verification.json").read_text(encoding="utf-8")
    )
    if not isinstance(value, dict):
        raise ValueError("Replay receipt is not an object")
    return value


def walk_public(value: Any) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if key in FORBIDDEN_PUBLIC_KEYS:
                raise ValueError(f"Public output contains private field: {key}")
            walk_public(child)
    elif isinstance(value, list):
        for child in value:
            walk_public(child)


def validate_manifest(manifest: Mapping[str, Any]) -> None:
    required_equal(manifest.get("kind"), "homophonic_search_development_manifest", field="manifest.kind")
    required_equal(manifest.get("status"), "started", field="manifest.status")
    required_equal(manifest.get("no_test_score"), True, field="manifest.no_test_score")
    protocol = mapping(manifest.get("protocol"), field="manifest.protocol")
    required_equal(protocol.get("name"), "homophonic-search-development-v1", field="manifest.protocol.name")
    required_equal(protocol.get("sha256"), EXPECTED_PROTOCOL_SHA256, field="manifest.protocol.sha256")
    config = mapping(manifest.get("config"), field="manifest.config")
    for field, expected in {
        "capacity": 2,
        "control_family": "cap2",
        "encryption_seed": 7000,
        "move_budget": 8,
        "trace_mode": "summary",
    }.items():
        required_equal(config.get(field), expected, field=f"manifest.config.{field}")
    required_equal(config.get("alphabet"), list(ALPHABET), field="manifest.config.alphabet")
    required_equal(config.get("objective_weight_formula"), "count(word) * T + N", field="manifest.config.objective_weight_formula")
    required_equal(config.get("objective_denominator_formula"), "2 * T * N", field="manifest.config.objective_denominator_formula")
    input_summary = mapping(manifest.get("input_summary"), field="manifest.input_summary")
    for field, expected in EXPECTED_INPUT.items():
        required_equal(integer(input_summary.get(field), field=f"manifest.input_summary.{field}"), expected, field=f"manifest.input_summary.{field}")
    required_equal(input_summary.get("weighted_counts_hash"), EXPECTED_WEIGHTED_COUNTS_SHA256, field="manifest.input_summary.weighted_counts_hash")
    required_equal(input_summary.get("training_lexicon_sha256"), EXPECTED_LEXICON_SHA256, field="manifest.input_summary.training_lexicon_sha256")
    required_equal(input_summary.get("validation_stream_sha256"), EXPECTED_STREAM_SHA256, field="manifest.input_summary.validation_stream_sha256")
    receipts = mapping(manifest.get("source_receipts"), field="manifest.source_receipts")
    required_equal(receipts.get("pinned_verification"), "enforced", field="manifest.source_receipts.pinned_verification")
    required_equal(receipts.get("pinned_mismatch_count"), 0, field="manifest.source_receipts.pinned_mismatch_count")
    required_equal(receipts.get("missing_file_count"), 0, field="manifest.source_receipts.missing_file_count")
    required_equal(receipts.get("protocol_sha256"), EXPECTED_PROTOCOL_SHA256, field="manifest.source_receipts.protocol_sha256")
    output_paths = mapping(manifest.get("output_paths"), field="manifest.output_paths")
    required_equal(set(output_paths), {"manifest", "cold_selected_key", "assisted_selected_key", "aggregate"}, field="manifest.output_paths.keys")
    required_equal(
        output_paths,
        {
            "manifest": "manifest.json",
            "cold_selected_key": "cold_selected.key.json",
            "assisted_selected_key": "assisted_selected.key.json",
            "aggregate": "aggregate.json",
        },
        field="manifest.output_paths",
    )


def validate_key_record(record: Mapping[str, Any], name: str) -> None:
    required_equal(record.get("kind"), "homophonic_search_development_fit_key", field=f"{name}.kind")
    required_equal(record.get("protocol"), "homophonic-search-development-v1", field=f"{name}.protocol")
    required_equal(record.get("control_family"), "cap2", field=f"{name}.control_family")
    required_equal(record.get("encryption_seed"), 7000, field=f"{name}.encryption_seed")
    required_equal(record.get("capacity"), 2, field=f"{name}.capacity")
    key = mapping(record.get("key"), field=f"{name}.key")
    if len(key) != 47:
        raise ValueError(f"{name}.key does not contain the 47 fitted units")
    if any(
        not isinstance(unit, str)
        or not isinstance(letter, str)
        or len(unit) != 3
        or not unit.startswith("c")
        or not unit[1:].isdigit()
        or letter not in ALPHABET
        for unit, letter in key.items()
    ):
        raise ValueError(f"{name}.key contains an invalid map entry")
    counts: dict[str, int] = {}
    for letter in key.values():
        counts[letter] = counts.get(letter, 0) + 1
    if any(count > 2 for count in counts.values()):
        raise ValueError(f"{name}.key exceeds capacity 2")


def validate_supervision(supervision: Mapping[str, Any], output_hashes: Mapping[str, str]) -> None:
    required_equal(supervision.get("schema_version"), 1, field="supervision.schema_version")
    required_equal(supervision.get("protocol"), "homophonic-search-development-v1", field="supervision.protocol")
    required_equal(supervision.get("status"), "development_only", field="supervision.status")
    required_equal(supervision.get("numeric_outputs_valid"), True, field="supervision.numeric_outputs_valid")
    freeze = mapping(supervision.get("freeze"), field="supervision.freeze")
    required_equal(freeze.get("file_count"), 29, field="supervision.freeze.file_count")
    required_equal(freeze.get("manifest_sha256"), EXPECTED_FREEZE_MANIFEST_SHA256, field="supervision.freeze.manifest_sha256")
    supervisor = mapping(supervision.get("supervisor"), field="supervision.supervisor")
    required_equal(supervisor.get("status"), "development_only", field="supervision.supervisor.status")
    required_equal(supervisor.get("terminal_event_seen"), True, field="supervision.supervisor.terminal_event_seen")
    required_equal(supervisor.get("child_error_event_count"), 0, field="supervision.supervisor.child_error_event_count")
    child_outputs = supervision.get("child_outputs")
    if not isinstance(child_outputs, list) or len(child_outputs) != len(EXPECTED_CHILD_NAMES):
        raise ValueError("supervision child output list is invalid")
    observed: dict[str, str] = {}
    for item in child_outputs:
        entry = mapping(item, field="supervision.child_output")
        path = entry.get("path")
        if not isinstance(path, str) or not path.startswith("reports/homophonic-search-development-v1/"):
            raise ValueError("supervision child path is not repository relative")
        name = path.rsplit("/", 1)[-1]
        if name not in EXPECTED_CHILD_NAMES:
            raise ValueError(f"unexpected supervision child: {name}")
        required_equal(entry.get("present"), True, field=f"supervision.child_output.{name}.present")
        observed[name] = entry.get("sha256")
    if tuple(observed) != EXPECTED_CHILD_NAMES:
        raise ValueError("supervision child outputs do not match the fixed set")
    for name in EXPECTED_CHILD_NAMES:
        required_equal(observed[name], output_hashes[name], field=f"supervision.child_output.{name}.sha256")


def validate_replay(
    replay: Mapping[str, Any],
    output_hashes: Mapping[str, str],
) -> None:
    walk_public(replay)
    required_equal(replay.get("schema_version"), 1, field="replay.schema_version")
    required_equal(replay.get("commit"), EXPECTED_COMMIT, field="replay.commit")
    required_equal(
        replay.get("command"),
        "python -m experiments.search_development.run_frozen",
        field="replay.command",
    )
    required_equal(replay.get("exit_code"), 0, field="replay.exit_code")
    required_equal(replay.get("blockers"), [], field="replay.blockers")
    required_equal(replay.get("public_output_equality"), True, field="replay.public_output_equality")
    required_equal(replay.get("receipt_sha256"), output_hashes["supervision.json"], field="replay.receipt_sha256")
    required_equal(replay.get("repository"), "https://github.com/johnpippett/voynich.git", field="replay.repository")
    checkout = mapping(replay.get("checkout"), field="replay.checkout")
    required_equal(checkout.get("clean_before"), True, field="replay.checkout.clean_before")
    required_equal(checkout.get("clean_after"), True, field="replay.checkout.clean_after")
    safe_statuses = mapping(replay.get("safe_statuses"), field="replay.safe_statuses")
    required_equal(safe_statuses.get("numeric_outputs_valid"), True, field="replay.safe_statuses.numeric_outputs_valid")
    required_equal(safe_statuses.get("wrapper"), "development_only", field="replay.safe_statuses.wrapper")
    required_equal(safe_statuses.get("supervisor"), "development_only", field="replay.safe_statuses.supervisor")
    required_equal(safe_statuses.get("terminal_event_seen"), True, field="replay.safe_statuses.terminal_event_seen")
    required_equal(safe_statuses.get("child_error_event_count"), 0, field="replay.safe_statuses.child_error_event_count")
    public_outputs = replay.get("public_outputs")
    if not isinstance(public_outputs, list) or len(public_outputs) != len(EXPECTED_OUTPUT_HASHES):
        raise ValueError("replay public output list is invalid")
    observed: dict[str, Mapping[str, Any]] = {}
    for item in public_outputs:
        entry = mapping(item, field="replay.public_output")
        name = entry.get("name")
        if not isinstance(name, str) or name not in EXPECTED_OUTPUT_HASHES:
            raise ValueError("replay names an unexpected public output")
        observed[name] = entry
    if set(observed) != set(EXPECTED_OUTPUT_HASHES):
        raise ValueError("replay public outputs do not match the fixed set")
    for name, expected in EXPECTED_OUTPUT_HASHES.items():
        required_equal(observed[name].get("primary_sha256"), expected, field=f"replay.public_outputs.{name}.primary_sha256")
        required_equal(observed[name].get("replay_sha256"), expected, field=f"replay.public_outputs.{name}.replay_sha256")


def validate_aggregate(
    aggregate: Mapping[str, Any],
    manifest: Mapping[str, Any],
    key_records: Mapping[str, Mapping[str, Any]],
    output_hashes: Mapping[str, str],
    prior_upper_bound: int,
) -> dict[str, int]:
    walk_public(aggregate)
    required_equal(aggregate.get("status"), "development_only", field="aggregate.status")
    required_equal(aggregate.get("kind"), "homophonic_search_development_v1", field="aggregate.kind")
    required_equal(aggregate.get("manifest_sha256"), output_hashes["manifest.json"], field="aggregate.manifest_sha256")
    required_equal(aggregate.get("config"), manifest.get("config"), field="aggregate.config")
    input_value = mapping(aggregate.get("input"), field="aggregate.input")
    for field, expected in EXPECTED_INPUT.items():
        required_equal(integer(input_value.get(field), field=f"aggregate.input.{field}"), expected, field=f"aggregate.input.{field}")
    for field, expected in (
        ("control_family", "cap2"),
        ("encryption_seed", 7000),
        ("weighted_counts_sha256", EXPECTED_WEIGHTED_COUNTS_SHA256),
        ("training_lexicon_sha256", EXPECTED_LEXICON_SHA256),
        ("validation_stream_sha256", EXPECTED_STREAM_SHA256),
    ):
        required_equal(input_value.get(field), expected, field=f"aggregate.input.{field}")
    fit_splits = mapping(input_value.get("fit_splits"), field="aggregate.input.fit_splits")
    required_equal(fit_splits.get("lexicon_split"), "train", field="aggregate.input.fit_splits.lexicon_split")
    required_equal(fit_splits.get("ciphertext_split"), "validation", field="aggregate.input.fit_splits.ciphertext_split")
    required_equal(fit_splits.get("test_scored"), False, field="aggregate.input.fit_splits.test_scored")

    root = mapping(aggregate.get("root"), field="aggregate.root")
    required_equal(root.get("status"), "complete", field="aggregate.root.status")
    for field, expected in EXPECTED_ROOT.items():
        required_equal(integer(root.get(field), field=f"aggregate.root.{field}"), expected, field=f"aggregate.root.{field}")
    required_equal(root.get("engine"), "BitsetPivotGroupBound", field="aggregate.root.engine")
    required_equal(root.get("independent_minus_group_bound"), EXPECTED_ROOT["independent_bound"] - EXPECTED_ROOT["group_bound"], field="aggregate.root.independent_minus_group_bound")
    if not 0 <= EXPECTED_ROOT["group_bound"] <= EXPECTED_ROOT["independent_bound"]:
        raise ValueError("root bounds are not ordered")
    metadata = mapping(root.get("metadata"), field="aggregate.root.metadata")
    required_equal(metadata.get("candidate_rows_complete"), True, field="aggregate.root.metadata.candidate_rows_complete")
    required_equal(metadata.get("grouping"), "static_min_symbol", field="aggregate.root.metadata.grouping")
    required_equal(metadata.get("source_sha256"), "8ab50b9700497cc493e0ba79a9fc6d452cf95e5b8c7d9d19d0de08b567000f76", field="aggregate.root.metadata.source_sha256")

    starts = mapping(aggregate.get("starts"), field="aggregate.starts")
    if set(starts) != set(EXPECTED_STARTS):
        raise ValueError("aggregate does not contain the two fixed starts")
    finals: dict[str, int] = {}
    for name, expected in EXPECTED_STARTS.items():
        stage = mapping(starts.get(name), field=f"aggregate.starts.{name}")
        for field, value in expected.items():
            required_equal(integer(stage.get(field), field=f"aggregate.starts.{name}.{field}"), value, field=f"aggregate.starts.{name}.{field}")
        required_equal(stage.get("status"), "complete", field=f"aggregate.starts.{name}.status")
        required_equal(stage.get("stop_status"), "move_budget_exhausted", field=f"aggregate.starts.{name}.stop_status")
        required_equal(stage.get("local_neighborhood_checked"), False, field=f"aggregate.starts.{name}.local_neighborhood_checked")
        required_equal(stage.get("key_record_sha256"), output_hashes[f"{name}.key.json"], field=f"aggregate.starts.{name}.key_record_sha256")
        required_equal(key_records[name].get("start"), name, field=f"{name}.key.start")
        required_equal(key_records[name].get("final_score"), expected["final_score"], field=f"{name}.key.final_score")
        finals[name] = expected["final_score"]

    best = max(finals.values())
    required_equal(integer(aggregate.get("best_lower_bound"), field="aggregate.best_lower_bound"), best, field="aggregate.best_lower_bound")
    comparison = mapping(aggregate.get("comparison"), field="aggregate.comparison")
    required_equal(comparison.get("group_bound"), EXPECTED_ROOT["group_bound"], field="aggregate.comparison.group_bound")
    required_equal(comparison.get("best_lower_bound"), best, field="aggregate.comparison.best_lower_bound")
    required_equal(comparison.get("gap"), EXPECTED_ROOT["group_bound"] - best, field="aggregate.comparison.gap")
    required_equal(comparison.get("finite_objective_value_certified"), False, field="aggregate.comparison.finite_objective_value_certified")
    required_equal(comparison.get("key_uniqueness_certified"), False, field="aggregate.comparison.key_uniqueness_certified")
    if best > EXPECTED_ROOT["group_bound"]:
        raise ValueError("a complete map exceeds the root bound")
    if best > prior_upper_bound:
        raise ValueError("best lower bound exceeds the pinned prior frontier upper bound")
    resource = mapping(aggregate.get("resource"), field="aggregate.resource")
    required_equal(resource.get("total_evaluation_count"), 19_168, field="aggregate.resource.total_evaluation_count")
    return {
        "best_lower_bound": best,
        "root_gap": EXPECTED_ROOT["group_bound"] - best,
        "independent_gap": EXPECTED_ROOT["independent_bound"] - EXPECTED_ROOT["group_bound"],
        "prior_upper_bound": prior_upper_bound,
        "frontier_gap": prior_upper_bound - best,
    }


def replay_sentence(replay_hash: str) -> str:
    return (
        "Independent replay matched all five public outputs and reported a clean, "
        f"valid run. See the [replay record](homophonic-search-development-v1/replay-verification.json) "
        f"(SHA-256 `{replay_hash}`)."
    )


def build_report() -> str:
    output_hashes = verify_output_hashes()
    replay_hash = verify_replay_hash()
    prior_hashes = verify_prior_report_hashes()
    prior_reports = {
        name: load_verified_prior_json(name)
        for name in EXPECTED_PRIOR_REPORT_HASHES
    }
    prior_upper_bound = validate_prior_reports(prior_reports)
    manifest = load_verified_json("manifest.json")
    aggregate = load_verified_json("aggregate.json")
    cold_key = load_verified_json("cold_selected.key.json")
    assisted_key = load_verified_json("assisted_selected.key.json")
    supervision = load_verified_json("supervision.json")
    replay = load_verified_replay()
    validate_manifest(manifest)
    walk_public(manifest)
    walk_public(cold_key)
    walk_public(assisted_key)
    walk_public(supervision)
    validate_key_record(cold_key, "cold_selected")
    validate_key_record(assisted_key, "assisted_selected")
    validate_supervision(supervision, output_hashes)
    validate_replay(replay, output_hashes)
    gaps = validate_aggregate(
        aggregate,
        manifest,
        {"cold_selected": cold_key, "assisted_selected": assisted_key},
        output_hashes,
        prior_upper_bound,
    )
    protocol_link = "../docs/plans/homophonic-search-development-v1.md"
    lines = [
        "# Homophonic search development",
        "",
        "The new static root bound is `892,887,632` for the pinned Italian control objective.",
        "The complete independent root bound is `896,647,414`.",
        f"The earlier frontier bound is `{gaps['prior_upper_bound']:,}` for the same pinned objective.",
        "The earlier frontier bound remains stronger than the new root bound.",
        "",
        "This report describes finite optimization on an inspected Old Italian control.",
        "It does not apply a model to the Voynich Manuscript.",
        "It does not produce a translation, decipherment, or historical reading.",
        "",
        "## Run and scope",
        "",
        f"The supervised run used commit `{EXPECTED_COMMIT}`.",
        f"CI run [{EXPECTED_CI_RUN}]({EXPECTED_CI_URL}) passed before the run.",
        f"The run began at `{EXPECTED_FIRST_START}`.",
        "The public supervision receipt reports valid numeric outputs and a 29-file freeze.",
        "The resource receipt remains private.",
        "The manifest records the protocol and source hashes.",
        f"The protocol SHA-256 is `{EXPECTED_PROTOCOL_SHA256}`.",
        f"The freeze manifest SHA-256 is `{EXPECTED_FREEZE_MANIFEST_SHA256}`.",
        "The builder checks the prior frontier report bytes before it reads JSON values.",
        "The [fixed protocol]({}) defines the inputs, bounds, and limits.".format(protocol_link),
        "",
        "The run used capacity `2`, encryption seed `7000`, and a total map over fitted cipher units.",
        "The search used the training lexicon, validation ciphertext, and two saved start maps.",
        "The source loader may read all source partitions, but the search did not score test data.",
        "The score uses integer weights `count(word) * T + N` and denominator `2*T*N`.",
        "",
        "| Input | Value |",
        "| --- | ---: |",
        "| Validation tokens `N` | `31,681` |",
        "| Validation word types `T` | `14,170` |",
        "| Training lexicon types | `6,273` |",
        "| Fitted cipher units | `47` |",
        "| Objective denominator `2*T*N` | `897,839,540` |",
        f"| Weighted counts SHA-256 | `{EXPECTED_WEIGHTED_COUNTS_SHA256}` |",
        f"| Training lexicon SHA-256 | `{EXPECTED_LEXICON_SHA256}` |",
        f"| Validation stream SHA-256 | `{EXPECTED_STREAM_SHA256}` |",
        "",
        "## Bounds",
        "",
        "The current root bounds use the same weighted counts, lexicon, stream hash, capacity, and alphabet.",
        "The static pivot-group bound relaxes conflicts between groups.",
        "The two current root bounds differ by `3,759,782`.",
        "",
        "| Bound | Value | Scope |",
        "| --- | ---: | --- |",
        "| Independent root upper bound | `896,647,414` | Complete independent root |",
        "| Static pivot-group root upper bound | `892,887,632` | Current relaxed root |",
        f"| Earlier frontier upper bound | `{gaps['prior_upper_bound']:,}` | Earlier 1,000-node frontier |",
        "",
        f"The current static root gap above the best lower bound is `{gaps['root_gap']:,}`.",
        f"The earlier frontier gap above that lower bound is `{gaps['frontier_gap']:,}`.",
        "The earlier frontier value comes from the [reference control report](HOMOPHONIC.md).",
        "It does not become a root bound because it came from a different search stage.",
        "",
        "## Local-search results",
        "",
        "Both starts used eight accepted improving moves and reached the move budget.",
        "Neither result certifies a local optimum or a global optimum.",
        "Neither result certifies recovery of the planted key.",
        "",
        "| Start | Initial score | Final lower bound | Gain | Moves | Evaluations | Stop |",
        "| --- | ---: | ---: | ---: | ---: | ---: | --- |",
        "| `cold_selected` | `90,866,594` | `166,057,138` | `75,190,544` | `8` | `9,584` | move budget |",
        "| `assisted_selected` | `222,253,278` | `565,215,014` | `342,961,736` | `8` | `9,584` | move budget |",
        "",
        "The best complete-map lower bound is `565,215,014`.",
        "The root comparison does not certify the finite objective value.",
        "",
        "## Interpretation limits",
        "",
        "The [reference control report](HOMOPHONIC.md) records failed recovery gates for the inspected controls.",
        "These development results do not change those gates.",
        "The controls do not estimate a false-positive rate.",
        "They do not reject all keys, all languages, or all cipher models.",
        "They provide no manuscript decipherment or translation.",
        "",
        replay_sentence(replay_hash),
        "",
        "## Public artifacts",
        "",
        "The builder verifies each output hash before it reads JSON values.",
        "It checks status fields, cross-record hashes, bound ordering, and score arithmetic.",
        "",
        "| File | SHA-256 |",
        "| --- | --- |",
        f"| [Aggregate report](homophonic-search-development-v1/aggregate.json) | `{output_hashes['aggregate.json']}` |",
        f"| [Manifest](homophonic-search-development-v1/manifest.json) | `{output_hashes['manifest.json']}` |",
        f"| [Cold key record](homophonic-search-development-v1/cold_selected.key.json) | `{output_hashes['cold_selected.key.json']}` |",
        f"| [Assisted key record](homophonic-search-development-v1/assisted_selected.key.json) | `{output_hashes['assisted_selected.key.json']}` |",
        f"| [Supervision receipt](homophonic-search-development-v1/supervision.json) | `{output_hashes['supervision.json']}` |",
        f"| [Replay receipt](homophonic-search-development-v1/replay-verification.json) | `{replay_hash}` |",
        f"| [Prior cold control](homophonic-feasibility-v1/italian-cold.json) | `{prior_hashes['italian-cold.json']}` |",
        f"| [Prior assisted control](homophonic-feasibility-v1/italian-assisted.json) | `{prior_hashes['italian-assisted.json']}` |",
        "",
        "The [runner review](../experiments/search_development/RUNNER_REVIEW.md) records synthetic checks and input safeguards.",
        "The [freeze review](../experiments/search_development/FREEZE_REVIEW.md) records the external manifest checks.",
        "",
        "## Reproduction",
        "",
        "Run the summary check from the repository root:",
        "",
        "```text",
        "python scripts/build_search_development_summary.py",
        "```",
        "The fixed run command and resource limits are in the [protocol]({}).".format(protocol_link),
        "The frozen output path refuses existing files.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    OUTPUT.write_text(build_report(), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
