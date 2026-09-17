#!/usr/bin/env python3
"""Build the public optimal-key identifiability report from public records."""

from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_DIR = ROOT / "reports" / "identifiability-v1-latin"
OUTPUT = ROOT / "reports" / "IDENTIFIABILITY.md"

EXPECTED_UNIT_COUNT = 46
EXPECTED_TEST_POSITIONS = 111_052
EXPECTED_TARGET = 370_396_722
EXPECTED_BASELINE_SHA256 = (
    "923dba00df53ff05ca88e91362ea44c693d66b8f0824071d85cc5b0d984ba77e"
)
EXPECTED_BASELINE_PROTOCOL_SHA256 = (
    "0e6a6edf5e0172f5e7a0f1fbf2f7ede8b9b181c7180aa616de58f44ae04d1249"
)
EXPECTED_IDENTIFIABILITY_PROTOCOL_SHA256 = (
    "ba61e56ff7730531f946450ac86b910842fc313bb52b7b34b415391125d6046d"
)
EXPECTED_IMPLEMENTATION_COMMIT = "ce8b626ab3cf8147829716f7828dff7fceba6cde"
EXPECTED_FAMILY = "cap2"
EXPECTED_LANGUAGE = "latin_llct"
EXPECTED_SEED = 7000
EXPECTED_CAPACITY = 2
CLASSIFICATIONS = (
    "forced_at_certified_optimum",
    "ambiguous",
    "unresolved",
)
DIAGNOSTIC_LABELS = (*CLASSIFICATIONS, "unobserved")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
UNIT_NAME = re.compile(r"^c[0-9]{2}$")
ALPHABET = frozenset("abcdefghijklmnopqrstuvwxyz")


def fail(message: str) -> None:
    raise ValueError(message)


def read_public_json(name: str) -> dict[str, Any]:
    """Read one JSON object from the public record directory."""

    if Path(name).name != name or not name.endswith(".json"):
        fail(f"invalid public record name: {name!r}")
    path = PUBLIC_DIR / name
    if not path.is_file():
        fail(f"required public record is missing: {path}")
    try:
        value = json.loads(path.read_bytes())
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"cannot read public record {path}: {exc}")
    if not isinstance(value, dict):
        fail(f"public record is not a JSON object: {path}")
    return value


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require_hash(value: Any, label: str) -> str:
    if not isinstance(value, str) or HEX64.fullmatch(value) is None:
        fail(f"{label} is not a lower-case SHA-256 value")
    return value


def require_int(value: Any, label: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        fail(f"{label} is not an integer greater than or equal to {minimum}")
    return value


def require_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        fail(f"{label} is not a non-empty string")
    return value


def validate_key(
    value: Any,
    units: list[str],
    capacity: int,
    label: str,
) -> dict[str, str]:
    if not isinstance(value, Mapping):
        fail(f"{label} is not a map")
    key = dict(value)
    if set(key) != set(units):
        fail(f"{label} does not cover the complete fitted unit domain")
    if any(
        not isinstance(unit, str)
        or not isinstance(letter, str)
        or letter not in ALPHABET
        for unit, letter in key.items()
    ):
        fail(f"{label} contains an invalid unit or alphabet letter")
    if any(count > capacity for count in Counter(key.values()).values()):
        fail(f"{label} exceeds the declared letter capacity")
    return {unit: key[unit] for unit in units}


def validate_run(run: Mapping[str, Any]) -> tuple[list[str], int, dict[str, Any]]:
    """Validate the fixed study scope and return units, capacity, certificate."""

    if run.get("kind") != "reference_assignment_identifiability":
        fail("run record has the wrong study kind")
    if run.get("language") != EXPECTED_LANGUAGE:
        fail("run record has the wrong reference language")
    if run.get("family") != EXPECTED_FAMILY or run.get("seed") != EXPECTED_SEED:
        fail("run record does not use the fixed Latin cap2 control")
    target = require_int(run.get("target"), "run target")
    if target != EXPECTED_TARGET:
        fail("run target does not match the frozen study")
    node_budget = require_int(run.get("node_budget_per_query"), "node budget")
    if node_budget != 1000:
        fail("run node budget does not match the frozen study")

    incumbent = run.get("incumbent_key")
    if not isinstance(incumbent, Mapping):
        fail("run record has no incumbent map")
    units = sorted(incumbent)
    if len(units) != EXPECTED_UNIT_COUNT or any(
        not isinstance(unit, str) or UNIT_NAME.fullmatch(unit) is None
        for unit in units
    ):
        fail("run record does not contain the complete 46-unit domain")
    validate_key(incumbent, units, EXPECTED_CAPACITY, "run incumbent key")

    symbol_order = run.get("symbol_order")
    if not isinstance(symbol_order, list) or symbol_order != list(dict.fromkeys(symbol_order)):
        fail("run symbol order is not a list of unique units")
    if set(symbol_order) != set(units):
        fail("run symbol order does not cover the fitted unit domain")
    require_hash(run.get("problem_fingerprint"), "run problem fingerprint")
    require_hash(run.get("search_settings_fingerprint"), "run search settings fingerprint")

    certificate = run.get("certificate")
    if not isinstance(certificate, Mapping):
        fail("run record has no certificate metadata")
    if certificate.get("problem_fingerprint") != run["problem_fingerprint"]:
        fail("certificate problem fingerprint does not match the run")
    if certificate.get("target") != target:
        fail("certificate target does not match the run")
    if certificate.get("lower_bound") != target or certificate.get("upper_bound") != target:
        fail("certificate bounds do not equal the certified target")
    if certificate.get("score_certified") is not True:
        fail("certificate does not mark the target as certified")
    if certificate.get("implementation_commit") != EXPECTED_IMPLEMENTATION_COMMIT:
        fail("certificate implementation commit does not match the frozen study")
    if certificate.get("report_sha256") != EXPECTED_BASELINE_SHA256:
        fail("certificate baseline report hash does not match the frozen study")
    require_hash(certificate.get("key_record_sha256"), "certificate key record hash")
    require_string(certificate.get("provenance"), "certificate provenance")
    if "does not independently prove" not in certificate.get("limit", ""):
        fail("certificate limit does not state the independent-proof boundary")

    provenance = run.get("provenance")
    if not isinstance(provenance, Mapping):
        fail("run record has no source provenance")
    if provenance.get("protocol_sha256") != EXPECTED_IDENTIFIABILITY_PROTOCOL_SHA256:
        fail("run record does not use the frozen identifiability protocol")
    code_hashes = provenance.get("code_sha256")
    if not isinstance(code_hashes, Mapping) or not code_hashes:
        fail("run record has no source code hash map")
    for path, digest in code_hashes.items():
        require_string(path, "source path")
        require_hash(digest, f"source hash for {path}")
    required_sources = {
        "experiments/identifiability/assess.py",
        "experiments/identifiability/run_assessment.py",
        "experiments/identifiability/threshold.py",
    }
    if not required_sources.issubset(code_hashes):
        fail("source hash map omits identifiability code")

    return units, EXPECTED_CAPACITY, dict(certificate)


def validate_assessment_identity(
    run: Mapping[str, Any],
    assessment: Mapping[str, Any],
    decisions: Mapping[str, Any],
) -> None:
    if assessment.get("status") != "complete":
        fail("assessment record is not complete")
    for field in (
        "kind", "language", "family", "seed", "target", "certificate",
        "problem_fingerprint", "search_settings_fingerprint", "symbol_order",
        "node_budget_per_query", "incumbent_key", "provenance",
    ):
        if assessment.get(field) != run.get(field):
            fail(f"assessment field does not match run record: {field}")
    decisions_path = PUBLIC_DIR / "decisions.json"
    if assessment.get("decisions_sha256") != sha256_file(decisions_path):
        fail("assessment decisions hash does not match public decisions.json")
    if assessment.get("decisions") != decisions:
        fail("assessment decisions do not match public decisions.json")
    limits = assessment.get("limits")
    if not isinstance(limits, list) or not all(isinstance(item, str) for item in limits):
        fail("assessment limits are missing")
    required_limit_fragments = (
        "inspected control failure",
        "not blind validation",
        "finite objective and domain",
        "neither exclusion nor ambiguity",
    )
    limit_text = " ".join(limits)
    if any(fragment not in limit_text for fragment in required_limit_fragments):
        fail("assessment limits omit a required scope statement")


def validate_query_map(
    value: Any,
    units: list[str],
    capacity: int,
    label: str,
) -> dict[str, str]:
    return validate_key(value, units, capacity, label)


def validate_witness(
    witness: Any,
    *,
    unit: str,
    selected: str,
    incumbent: Mapping[str, str],
    units: list[str],
    capacity: int,
    target: int,
    label: str,
    one_unit_only: bool = False,
) -> None:
    if not isinstance(witness, Mapping):
        fail(f"{label} is not a witness object")
    key = validate_query_map(witness.get("key"), units, capacity, f"{label} key")
    if witness.get("score") != target:
        fail(f"{label} score does not equal the target")
    if witness.get("changed_unit") != unit:
        fail(f"{label} changed unit does not match the query unit")
    if witness.get("changed_from") != selected:
        fail(f"{label} changed-from letter does not match the selected letter")
    if key[unit] == selected or witness.get("changed_to") != key[unit]:
        fail(f"{label} does not satisfy the forbidden-letter query")
    require_string(witness.get("method"), f"{label} method")
    if one_unit_only and any(key[other] != incumbent[other] for other in units if other != unit):
        fail(f"{label} changes more than the queried unit")


def validate_record(
    record: Mapping[str, Any],
    *,
    unit: str,
    units: list[str],
    capacity: int,
    run: Mapping[str, Any],
    classification: str,
) -> None:
    if record.get("cipher_unit") != unit:
        fail(f"record {unit} names a different cipher unit")
    if record.get("classification") != classification:
        fail(f"record {unit} classification does not match decisions.json")
    selected = record.get("incumbent_letter")
    if selected != run["incumbent_key"][unit] or selected not in ALPHABET:
        fail(f"record {unit} selected letter does not match the incumbent map")
    expected_forbidden = {unit: [selected]}
    if record.get("forbidden") != expected_forbidden:
        fail(f"record {unit} has an invalid forbidden-letter map")
    if record.get("objective_domain_fingerprint") != run["problem_fingerprint"]:
        fail(f"record {unit} has a different objective fingerprint")

    query = record.get("raw_query")
    if not isinstance(query, Mapping):
        fail(f"record {unit} has no raw threshold query")
    if query.get("problem_fingerprint") != run["problem_fingerprint"]:
        fail(f"record {unit} query has a different problem fingerprint")
    if query.get("objective_domain_fingerprint") != run["problem_fingerprint"]:
        fail(f"record {unit} query has a different objective fingerprint")
    if query.get("search_settings_fingerprint") != run["search_settings_fingerprint"]:
        fail(f"record {unit} query has different search settings")
    if query.get("query_target") != run["target"]:
        fail(f"record {unit} query target does not match the run")
    if query.get("forbidden") != expected_forbidden:
        fail(f"record {unit} query does not preserve the forbidden letter")
    if query.get("constraints") != {}:
        fail(f"record {unit} has constraints outside the one-unit exclusion")
    if query.get("capacity") != capacity:
        fail(f"record {unit} query capacity is invalid")
    config = query.get("config")
    if not isinstance(config, Mapping) or config.get("capacity") != capacity:
        fail(f"record {unit} query config has an invalid capacity")
    if query.get("bound_engine") != "BitsetBound" or config.get("bound_engine") != "BitsetBound":
        fail(f"record {unit} does not use the frozen bitset bound")
    if query.get("symbol_order") != run["symbol_order"]:
        fail(f"record {unit} query symbol order differs from the run")
    require_hash(query.get("query_fingerprint"), f"query fingerprint for {unit}")
    status = query.get("status")
    expected_status = {
        "forced_at_certified_optimum": "infeasible",
        "ambiguous": "feasible",
        "unresolved": "unknown",
    }[classification]
    if status != expected_status:
        fail(f"record {unit} status does not match its classification")
    if query.get("node_budget") != run["node_budget_per_query"]:
        fail(f"record {unit} query node budget differs from the run")
    for field in ("nodes", "pruned_nodes", "frontier_node_count"):
        require_int(query.get(field), f"{unit} query {field}")
    if query["nodes"] > run["node_budget_per_query"]:
        fail(f"record {unit} query exceeds its node budget")
    for field in ("lower_bound", "upper_bound"):
        require_int(query.get(field), f"{unit} query {field}")
    if query["lower_bound"] > query["upper_bound"]:
        fail(f"record {unit} query has inverted bounds")
    if status == "infeasible" and query["upper_bound"] >= run["target"]:
        fail(f"record {unit} infeasible query has no sub-target upper bound")
    if status == "feasible" and query["lower_bound"] < run["target"]:
        fail(f"record {unit} feasible query has no target lower bound")
    if query.get("feasible") is not (status == "feasible"):
        fail(f"record {unit} feasible flag does not match status")
    if query.get("infeasible") is not (status == "infeasible"):
        fail(f"record {unit} infeasible flag does not match status")

    raw_key = query.get("key")
    if status == "feasible":
        validate_query_map(raw_key, units, capacity, f"record {unit} query witness")
        if raw_key[unit] == selected:
            fail(f"record {unit} query witness uses the forbidden letter")
        if query.get("score") != run["target"]:
            fail(f"record {unit} query witness score does not equal the target")
    elif raw_key is not None or query.get("score") is not None:
        fail(f"record {unit} non-feasible query contains a witness")

    incumbent = run["incumbent_key"]
    warm_witness = record.get("warm_witness")
    witness = record.get("witness")
    if classification == "ambiguous":
        if status != "feasible" or witness is None:
            fail(f"record {unit} ambiguous result has no feasible witness")
        validate_witness(
            witness, unit=unit, selected=selected, incumbent=incumbent,
            units=units, capacity=capacity, target=run["target"],
            label=f"record {unit} witness",
        )
        if warm_witness is not None:
            validate_witness(
                warm_witness, unit=unit, selected=selected, incumbent=incumbent,
                units=units, capacity=capacity, target=run["target"],
                label=f"record {unit} warm witness", one_unit_only=True,
            )
            if witness != warm_witness:
                fail(f"record {unit} does not retain the warm witness")
    elif warm_witness is not None or witness is not None:
        fail(f"record {unit} non-ambiguous result contains a witness")


def validate_decisions(
    decisions: Mapping[str, Any],
    *,
    run: Mapping[str, Any],
    units: list[str],
    records: Mapping[str, Mapping[str, Any]],
) -> None:
    if decisions.get("problem_fingerprint") != run["problem_fingerprint"]:
        fail("decisions problem fingerprint does not match the run")
    if decisions.get("target") != run["target"]:
        fail("decisions target does not match the run")
    assignments = decisions.get("assignments")
    if not isinstance(assignments, Mapping) or set(assignments) != set(units):
        fail("decisions do not contain exactly the 46 fitted units")
    if any(value not in CLASSIFICATIONS for value in assignments.values()):
        fail("decisions contain an unknown classification")
    expected_assignments = {unit: records[unit]["classification"] for unit in units}
    if dict(assignments) != expected_assignments:
        fail("decisions assignments do not match the query records")
    expected_counts = dict(Counter(assignments.values()))
    counts = decisions.get("counts")
    if not isinstance(counts, Mapping) or dict(counts) != expected_counts:
        fail("decisions counts do not match the query records")
    if sum(require_int(value, "classification count") for value in counts.values()) != EXPECTED_UNIT_COUNT:
        fail("decisions counts do not cover all 46 fitted units")

    hashes = decisions.get("query_sha256")
    expected_names = {f"{unit}.json" for unit in units}
    if not isinstance(hashes, Mapping) or set(hashes) != expected_names:
        fail("decisions query hash map is incomplete")
    for name, digest in hashes.items():
        require_hash(digest, f"query hash for {name}")
        actual = sha256_file(PUBLIC_DIR / name)
        if digest != actual:
            fail(f"query hash does not match public bytes: {name}")


def validate_diagnostics(
    diagnostics: Any,
    *,
    assignments: Mapping[str, str],
) -> None:
    if not isinstance(diagnostics, Mapping) or set(diagnostics) != set(DIAGNOSTIC_LABELS):
        fail("post-query diagnostics do not contain the required categories")
    for label in DIAGNOSTIC_LABELS:
        item = diagnostics[label]
        if not isinstance(item, Mapping):
            fail(f"diagnostic category is not an object: {label}")
        for field in (
            "unit_count", "unit_assignments_correct", "test_positions",
            "test_correct", "test_errors",
        ):
            require_int(item.get(field), f"{label} diagnostic {field}")
        if item["unit_assignments_correct"] > item["unit_count"]:
            fail(f"{label} diagnostic has too many matching assignments")
        if item["test_correct"] + item["test_errors"] != item["test_positions"]:
            fail(f"{label} diagnostic character totals do not add up")
    for label in CLASSIFICATIONS:
        if diagnostics[label]["unit_count"] != sum(
            value == label for value in assignments.values()
        ):
            fail(f"{label} diagnostic unit count does not match decisions")
    total_positions = sum(diagnostics[label]["test_positions"] for label in DIAGNOSTIC_LABELS)
    if total_positions != EXPECTED_TEST_POSITIONS:
        fail("diagnostic character positions do not match the frozen test total")


def build_report() -> str:
    """Load and validate every public record before creating Markdown."""

    run = read_public_json("run.json")
    units, capacity, _certificate = validate_run(run)
    decisions = read_public_json("decisions.json")
    assessment = read_public_json("assessment.json")
    records: dict[str, dict[str, Any]] = {}
    for unit in units:
        record = read_public_json(f"{unit}.json")
        records[unit] = record
    validate_decisions(decisions, run=run, units=units, records=records)
    for unit in units:
        validate_record(
            records[unit], unit=unit, units=units, capacity=capacity, run=run,
            classification=decisions["assignments"][unit],
        )
    validate_assessment_identity(run, assessment, decisions)
    validate_diagnostics(
        assessment.get("post_query_diagnostics"),
        assignments=decisions["assignments"],
    )

    counts = decisions["counts"]
    diagnostics = assessment["post_query_diagnostics"]
    protocol_hash = run["provenance"]["protocol_sha256"]
    total_errors = sum(diagnostics[label]["test_errors"] for label in DIAGNOSTIC_LABELS)
    if (
        total_errors == 4
        and diagnostics["forced_at_certified_optimum"]["test_errors"] == 0
        and diagnostics["ambiguous"]["test_errors"] == 4
    ):
        error_note = "All 4 earlier errors are in the ambiguous category."
    else:
        error_note = "The table shows the error count for each category."
    lines = [
        "# Optimal-key identifiability",
        "",
        (
            f"The fixed Latin `{EXPECTED_FAMILY}` control uses target "
            f"`{run['target']}` for a finite lexicon and a capacity of {capacity}."
        ),
        (
            f"The {len(units)} fitted units classify as "
            f"{counts.get('forced_at_certified_optimum', 0)} forced, "
            f"{counts.get('ambiguous', 0)} ambiguous, and "
            f"{counts.get('unresolved', 0)} unresolved."
        ),
        (
            "These classifications apply to the supplied finite objective and domain. "
            "They do not establish historical truth or key uniqueness."
        ),
        (
            "The earlier homophonic pilot had 4 errors in 111052 test character positions."
        ),
        (
            "It recovered 45 of 46 fitted unit assignments. "
            "This assessment does not change that result."
        ),
        (
            f"The forced units cover "
            f"{diagnostics['forced_at_certified_optimum']['test_positions']} test positions "
            f"with {diagnostics['forced_at_certified_optimum']['test_errors']} errors."
        ),
        (
            f"The ambiguous units cover {diagnostics['ambiguous']['test_positions']} "
            f"test positions with {diagnostics['ambiguous']['test_errors']} errors."
        ),
        error_note,
        (
            "This follow-up uses an inspected control failure. "
            "It is exploratory and is not blind validation."
        ),
        "",
        "## Finding",
        "",
        (
            "A `forced` result means that the threshold proof excluded every map "
            "with score at or above the target after it forbade the selected letter."
        ),
        (
            "This result is conditional on the published certificate, finite lexicon, "
            "alphabet, capacity, and query settings."
        ),
        (
            "The query code checks certificate metadata. "
            "It does not prove the global certificate."
        ),
        (
            "An `ambiguous` result has a target-scoring witness with the selected "
            "letter forbidden. Each witness is a separate map."
        ),
        (
            "An `unresolved` result means that the bounded query did not classify "
            "the unit."
        ),
        "",
        "## Test diagnostics",
        "",
        (
            "The table compares each category with the planted control map. "
            "This post-query diagnostic did not set or repair a classification."
        ),
        "",
        "| Category | Units | Map matches | Test positions | Correct | Errors |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for label in DIAGNOSTIC_LABELS:
        item = diagnostics[label]
        lines.append(
            f"| `{label}` | {item['unit_count']} | "
            f"{item['unit_assignments_correct']} | {item['test_positions']} | "
            f"{item['test_correct']} | {item['test_errors']} |"
        )
    lines.extend(
        [
            "",
            (
                f"The diagnostic rows cover {EXPECTED_TEST_POSITIONS} test character positions."
            ),
            "The `unobserved` row covers test units outside the fitted map.",
            "",
            "## Scope and replay",
            "",
            (
                "The source certificate comes from the published Latin homophonic "
                f"control at report SHA-256 `{EXPECTED_BASELINE_SHA256}`."
            ),
            (
                f"The [baseline protocol](../docs/plans/visual-homophonic-pilot.md) has "
                f"SHA-256 `{EXPECTED_BASELINE_PROTOCOL_SHA256}` and uses commit "
                f"`{EXPECTED_IMPLEMENTATION_COMMIT}`."
            ),
            (
                f"The [identifiability protocol](../docs/plans/optimal-key-identifiability-v1.md) "
                f"has SHA-256 `{protocol_hash}`."
            ),
            (
                "The [run record](identifiability-v1-latin/run.json) stores the complete "
                "source hash map and the certificate metadata."
            ),
            (
                "The identifiability protocol is frozen at commit "
                "`f7dbb21d4281f440b05542be0fbd8eec638136fe`."
            ),
            (
                "The [runner](../experiments/identifiability/run_assessment.py), "
                "[assessor](../experiments/identifiability/assess.py), and "
                "[threshold API](../experiments/identifiability/threshold.py) define the replay."
            ),
            "",
            "```sh",
            "python experiments/identifiability/run_assessment.py \\",
            "  --output-dir results/identifiability-v1-latin",
            "```",
            "",
            (
                "Replay inputs include the [baseline report]"
                "(homophonic-feasibility-v1/latin-cold.json) and its "
                "[key record](homophonic-feasibility-v1/latin-cold.keys.json)."
            ),
            "The runner regenerates the 46 query records and writes them to the output directory.",
            "A separate public checkout reproduced all 49 JSON files byte for byte.",
            "The [verification record](identifiability-verification.json) gives the checks and their limits.",
            (
                "The [reference-corpus note](../docs/research/reference-corpora.md) "
                "defines the Latin control source."
            ),
            (
                "No VMS data or plaintext is used in this assessment. "
                "The result does not support a decipherment claim."
            ),
            "",
            "## Public records",
            "",
            (
                "The generator wrote this report only after it verified all 46 query "
                "files, the decisions hash, the query hashes, and the diagnostic totals."
            ),
            "",
            "| Record | Link |",
            "| --- | --- |",
            "| Run | [run.json](identifiability-v1-latin/run.json) |",
            "| Decisions | [decisions.json](identifiability-v1-latin/decisions.json) |",
            "| Assessment | [assessment.json](identifiability-v1-latin/assessment.json) |",
            "",
            "## Unit results",
            "",
            "| Unit | Selected | Result | Nodes | Record |",
            "| --- | --- | --- | ---: | --- |",
        ]
    )
    total_nodes = sum(records[unit]["raw_query"]["nodes"] for unit in units)
    unit_heading_index = lines.index("## Unit results")
    lines[unit_heading_index + 2:unit_heading_index + 2] = [
        f"The 46 queries used {total_nodes} nodes in total.",
        "",
    ]
    for unit in units:
        record = records[unit]
        query = record["raw_query"]
        result_label = (
            "forced"
            if record["classification"] == "forced_at_certified_optimum"
            else record["classification"]
        )
        lines.append(
            f"| `{unit}` | `{record['incumbent_letter']}` | "
            f"`{result_label}` | {query['nodes']} | "
            f"[JSON](identifiability-v1-latin/{unit}.json) |"
        )
    lines.extend(
        [
            "",
            "## Independent review limits",
            "",
            (
                "This report validates public record integrity and scope. "
                "It does not rebuild the corpus or the heavy bound."
            ),
            (
                "The planted-map comparison is an audit diagnostic. "
                "It does not turn a conditional result into a truth claim."
            ),
            (
                "The inspected-control failure limits the evidence. "
                "A later manuscript study would need its own protocol and certificate."
            ),
            "",
            "<!-- Source hashes are retained in run.json. -->",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    try:
        report = build_report()
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"identifiability report not written: {exc}", file=sys.stderr)
        return 1
    OUTPUT.write_text(report, encoding="utf-8")
    print(OUTPUT.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
