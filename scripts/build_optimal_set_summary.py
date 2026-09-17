#!/usr/bin/env python3
"""Validate the public optimal-set records and build their report."""

from __future__ import annotations

import argparse
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RECORDS_DIR = ROOT / "reports" / "optimal-set-secondary-v1-latin"
DEFAULT_OUTPUT = ROOT / "reports" / "OPTIMAL_SET.md"
RECORD_NAMES = ("input.json", "enumeration.json", "ranking.json", "selection.json", "result.json")
HEX64 = re.compile(r"^0x[0-9a-f]+$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
ALPHABET = tuple("abcdefghijklmnopqrstuvwxyz")
SECONDARY_PROTOCOL = "docs/plans/optimal-set-secondary-v1.md"
SECONDARY_PROTOCOL_SHA256 = "17abf949562b5152c104b8fb8c6987079b22514d87bb93aa155236b2d8c6867c"
FREEZE_COMMIT = "883da35809cb1a3828876f272f108ae103fdf98a"
EXPECTED_TARGET = 370396722
EXPECTED_FREE_UNIT = "c40"
EXPECTED_FREE_VALUES = ("j", "w", "y", "z")
EXPECTED_RATIO = Fraction(8036, 1131)
EXPECTED_BASELINE_REPORT_SHA256 = "923dba00df53ff05ca88e91362ea44c693d66b8f0824071d85cc5b0d984ba77e"
EXPECTED_BASELINE_KEY_SHA256 = "965774da55e1ace6522a184a0040f63563c508e0d690270b9d726f6dd7575bb2"
EXPECTED_NEW_SOURCE_HASHES = {
    "experiments/optimal_set/enumerate.py": "443b53105412e28b1b00172c38776e6a9d43ef94c45a774533e2a2e0e443e5d8",
    "experiments/optimal_set/secondary.py": "367d4ed3bd88a7601183a5870d978c19a50b0a2c7ccdd28127185aae559cdc85",
    "experiments/optimal_set/run_study.py": "225ed29bf5ad72733fd7282bcb1f5794a137a1c1ecd9d455cd67b9e020233448",
}
RATIO_DEFINITION = (
    "candidate likelihood divided by the canonical first-candidate "
    "likelihood; alpha 0.1 is represented as (10*c+1)/(10*t+V)"
)


def fail(message: str) -> None:
    """Stop on the first invalid public record."""

    raise ValueError(message)


def canonical_bytes(value: Any) -> bytes:
    """Return the JSON form used by the study writer."""

    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def canonical_hash(value: Any) -> str:
    """Return the SHA-256 hash of one canonical JSON value."""

    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def file_hash(path: Path) -> str:
    """Return the SHA-256 hash of one file."""

    return hashlib.sha256(path.read_bytes()).hexdigest()


def require_hash(value: Any, field: str) -> str:
    if not isinstance(value, str) or SHA256.fullmatch(value) is None:
        fail(f"{field} is not a lower-case SHA-256 hash")
    return value


def require_int(value: Any, field: str, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        fail(f"{field} is not a non-negative integer")
    return value


def read_record(records_dir: Path, name: str) -> tuple[dict[str, Any], str]:
    """Read one canonical public JSON record and return its bytes hash."""

    path = records_dir / name
    if not path.is_file():
        fail(f"missing public record: {path}")
    raw = path.read_bytes()
    try:
        value = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        fail(f"invalid JSON in {path}: {exc}")
    if not isinstance(value, dict):
        fail(f"public record is not an object: {path}")
    if raw != canonical_bytes(value):
        fail(f"public record is not in the canonical byte form: {path}")
    return value, hashlib.sha256(raw).hexdigest()


def ordered_map(value: Any, units: tuple[str, ...], field: str) -> dict[str, str]:
    """Validate one complete lower-case map and return it in unit order."""

    if not isinstance(value, Mapping):
        fail(f"{field} is not a map")
    result = dict(value)
    if set(result) != set(units):
        fail(f"{field} does not cover the complete unit domain")
    if any(not isinstance(unit, str) or not isinstance(letter, str) for unit, letter in result.items()):
        fail(f"{field} has a non-string symbol")
    if any(letter not in ALPHABET for letter in result.values()):
        fail(f"{field} has a letter outside the lower-case ASCII alphabet")
    counts: dict[str, int] = {}
    for letter in result.values():
        counts[letter] = counts.get(letter, 0) + 1
    if any(count > 2 for count in counts.values()):
        fail(f"{field} exceeds the capacity-two limit")
    return {unit: result[unit] for unit in units}


def map_payload(maps: list[dict[str, str]]) -> list[list[list[str]]]:
    """Return the canonical map-set payload used by the runner."""

    return sorted([[[unit, candidate[unit]] for unit in sorted(candidate)] for candidate in maps])


def ratio_record(value: Any, field: str) -> Fraction:
    """Validate one positive reduced hexadecimal fraction."""

    if not isinstance(value, Mapping):
        fail(f"{field} is not a ratio record")
    numerator_hex = value.get("numerator_hex")
    denominator_hex = value.get("denominator_hex")
    if (
        not isinstance(numerator_hex, str)
        or HEX64.fullmatch(numerator_hex) is None
        or not isinstance(denominator_hex, str)
        or HEX64.fullmatch(denominator_hex) is None
    ):
        fail(f"{field} has malformed hexadecimal values")
    numerator = int(numerator_hex, 16)
    denominator = int(denominator_hex, 16)
    if numerator <= 0 or denominator <= 0:
        fail(f"{field} must be positive")
    ratio = Fraction(numerator, denominator)
    if ratio.numerator != numerator or ratio.denominator != denominator:
        fail(f"{field} is not reduced")
    if value.get("numerator_bits") != numerator.bit_length():
        fail(f"{field} has an invalid numerator bit count")
    if value.get("denominator_bits") != denominator.bit_length():
        fail(f"{field} has an invalid denominator bit count")
    return ratio


def validate_records(records_dir: Path) -> dict[str, Any]:
    """Validate the five public records and return report values."""

    loaded: dict[str, dict[str, Any]] = {}
    hashes: dict[str, str] = {}
    for name in RECORD_NAMES:
        loaded[name[:-5]], hashes[name[:-5]] = read_record(records_dir, name)
    input_record = loaded["input"]
    enumeration = loaded["enumeration"]
    ranking = loaded["ranking"]
    selection = loaded["selection"]
    result = loaded["result"]

    if input_record.get("kind") != "optimal_set_secondary_study_input":
        fail("input record has the wrong kind")
    target = require_int(input_record.get("target"), "input.target")
    if target != EXPECTED_TARGET:
        fail("input target does not match the fixed Latin control")
    if input_record.get("capacity") != 2:
        fail("input capacity is not two")
    if tuple(input_record.get("plaintext_alphabet", ())) != ALPHABET:
        fail("input alphabet is not the full lower-case ASCII alphabet")
    objective_fingerprint = require_hash(
        input_record.get("objective_domain_fingerprint"),
        "input.objective_domain_fingerprint",
    )
    fixed = input_record.get("fixed_assignments")
    if not isinstance(fixed, Mapping) or len(fixed) != 45:
        fail("input does not contain 45 forced assignments")
    fixed_units = tuple(sorted(fixed))
    fixed_map = ordered_map(fixed, fixed_units, "input.fixed_assignments")
    if input_record.get("ambiguous_units") != [EXPECTED_FREE_UNIT]:
        fail("input ambiguous unit is not c40")
    if input_record.get("unresolved_units") != []:
        fail("input has unresolved units")
    if input_record.get("query_record_count") != 46:
        fail("input does not record all 46 published queries")

    limits = input_record.get("limits")
    if not isinstance(limits, Mapping) or dict(limits) != {
        "max_delta_events": 4096,
        "max_product": 1_000_000,
        "max_ratio_bits": 1_000_000,
        "node_budget": 1_000_000,
    }:
        fail("input limits do not match the fixed protocol")

    provenance = input_record.get("provenance")
    if not isinstance(provenance, Mapping):
        fail("input provenance is missing")
    source_hashes = provenance.get("source_hashes")
    if not isinstance(source_hashes, Mapping):
        fail("input source hashes are missing")
    for path, digest in source_hashes.items():
        if not isinstance(path, str) or not path:
            fail("input source hash path is invalid")
        require_hash(digest, f"input.provenance.source_hashes[{path}]")
    protocols = provenance.get("protocol_hashes")
    if not isinstance(protocols, Mapping) or protocols.get(SECONDARY_PROTOCOL) != SECONDARY_PROTOCOL_SHA256:
        fail("input does not pin the secondary protocol")
    for record_name, record in loaded.items():
        record_protocols = record.get("protocol_hashes")
        if not isinstance(record_protocols, Mapping) or record_protocols.get(SECONDARY_PROTOCOL) != SECONDARY_PROTOCOL_SHA256:
            fail(f"{record_name} does not carry the secondary protocol pin")

    code_hashes = input_record.get("code_hashes")
    if not isinstance(code_hashes, Mapping) or len(code_hashes) != 17:
        fail("input does not record the 17 implementation hashes")
    for path, digest in code_hashes.items():
        if not isinstance(path, str) or not path:
            fail("input code hash path is invalid")
        require_hash(digest, f"input.code_hashes[{path}]")
    for path, expected in EXPECTED_NEW_SOURCE_HASHES.items():
        if code_hashes.get(path) != expected or source_hashes.get(path) != expected:
            fail(f"input does not carry the pinned hash for {path}")
        source_path = ROOT / path
        if not source_path.is_file() or file_hash(source_path) != expected:
            fail(f"working-tree source hash does not match the public pin: {path}")

    value_certificate = provenance.get("value_certificate")
    if not isinstance(value_certificate, Mapping):
        fail("input value certificate is missing")
    if (
        value_certificate.get("score") != target
        or value_certificate.get("lower_bound") != target
        or value_certificate.get("upper_bound") != target
        or value_certificate.get("score_certified") is not True
        or value_certificate.get("search_exhausted") is not False
        or value_certificate.get("frontier_node_count") != 25
        or value_certificate.get("bound_engine") != "bitset"
        or value_certificate.get("baseline_report_sha256") != EXPECTED_BASELINE_REPORT_SHA256
        or value_certificate.get("key_record_sha256") != EXPECTED_BASELINE_KEY_SHA256
    ):
        fail("input value certificate does not match the pinned baseline")
    pinned = input_record.get("pinned_artifacts")
    if not isinstance(pinned, Mapping) or pinned.get("reports/homophonic-feasibility-v1/latin-cold.json") != EXPECTED_BASELINE_REPORT_SHA256 or pinned.get("reports/homophonic-feasibility-v1/latin-cold.keys.json") != EXPECTED_BASELINE_KEY_SHA256:
        fail("input baseline artifact pins are incomplete")
    baseline_report_path = ROOT / "reports" / "homophonic-feasibility-v1" / "latin-cold.json"
    baseline_key_path = ROOT / "reports" / "homophonic-feasibility-v1" / "latin-cold.keys.json"
    if (
        not baseline_report_path.is_file()
        or not baseline_key_path.is_file()
        or file_hash(baseline_report_path) != EXPECTED_BASELINE_REPORT_SHA256
        or file_hash(baseline_key_path) != EXPECTED_BASELINE_KEY_SHA256
    ):
        fail("working-tree baseline artifact hash does not match the public pin")

    input_hash = hashes["input"]
    enumeration_hash = hashes["enumeration"]
    ranking_hash = hashes["ranking"]
    selection_hash = hashes["selection"]
    if enumeration.get("input_sha256") != input_hash:
        fail("enumeration does not bind input.json")
    if ranking.get("input_sha256") != input_hash or ranking.get("enumeration_sha256") != enumeration_hash:
        fail("ranking does not bind input and enumeration")
    if selection.get("input_sha256") != input_hash or selection.get("enumeration_sha256") != enumeration_hash or selection.get("ranking_sha256") != ranking_hash:
        fail("selection does not bind the earlier records")
    if result.get("input_sha256") != input_hash or result.get("enumeration_sha256") != enumeration_hash or result.get("ranking_sha256") != ranking_hash or result.get("selection_sha256") != selection_hash:
        fail("result does not bind all earlier records")
    if result.get("selection") != selection:
        fail("nested result selection differs from selection.json")

    free_units = (EXPECTED_FREE_UNIT,)
    units = fixed_units + free_units
    if len(units) != 46 or len(set(units)) != 46:
        fail("fixed and free unit domains do not cover 46 units")
    if enumeration.get("status") != "complete" or enumeration.get("complete") is not True or enumeration.get("truncation") is not False:
        fail("enumeration is not complete")
    if (
        enumeration.get("target") != target
        or enumeration.get("capacity") != 2
        or enumeration.get("objective_domain_fingerprint") != objective_fingerprint
        or tuple(enumeration.get("free_units", ())) != free_units
        or tuple(enumeration.get("full_alphabet", ())) != ALPHABET
        or enumeration.get("fixed_assignments") != fixed_map
        or enumeration.get("product_bound") != 26
        or enumeration.get("visited_nodes") != 5
        or enumeration.get("feasible_leaves") != 4
        or enumeration.get("capacity_prunes") != 22
        or enumeration.get("retained_map_count") != 4
        or enumeration.get("claims_global_optimum") is not False
        or enumeration.get("claims_fixed_assignments_forced") is not False
    ):
        fail("enumeration metadata does not match the fixed domain")
    raw_maps = enumeration.get("collected_maps")
    if not isinstance(raw_maps, list) or len(raw_maps) != 4:
        fail("enumeration does not contain the four retained maps")
    maps = [ordered_map(candidate, units, f"enumeration.collected_maps[{index}]") for index, candidate in enumerate(raw_maps)]
    free_values = tuple(candidate[EXPECTED_FREE_UNIT] for candidate in maps)
    if free_values != EXPECTED_FREE_VALUES:
        fail("enumeration map order or c40 values are incorrect")
    if any(any(candidate[unit] != fixed_map[unit] for unit in fixed_units) for candidate in maps):
        fail("enumeration changed a forced assignment")
    if len({tuple(candidate.items()) for candidate in maps}) != 4:
        fail("enumeration retained duplicate maps")
    candidate_set_hash = canonical_hash(map_payload(maps))
    if enumeration.get("retained_map_set_sha256") != candidate_set_hash:
        fail("enumeration map-set hash is incorrect")

    if ranking.get("status") != "complete" or ranking.get("candidate_count") != 4 or ranking.get("input_candidate_count") != 4 or ranking.get("baseline_index") != 0:
        fail("ranking does not contain four complete candidates")
    if ranking.get("candidate_set_sha256") != candidate_set_hash:
        fail("ranking candidate-set hash differs from enumeration")
    config = ranking.get("config")
    if not isinstance(config, Mapping) or config.get("ratio_definition") != RATIO_DEFINITION:
        fail("ranking ratio definition is not the frozen exact convention")
    candidate_results = ranking.get("candidate_results")
    if not isinstance(candidate_results, list) or len(candidate_results) != 4:
        fail("ranking does not contain one result per map")
    ratios: list[Fraction] = []
    for index, candidate_result in enumerate(candidate_results):
        if not isinstance(candidate_result, Mapping) or candidate_result.get("candidate_index") != index:
            fail("ranking candidate indices are not sequential")
        candidate_key = ordered_map(candidate_result.get("key"), units, f"ranking.candidate_results[{index}].key")
        if candidate_key != maps[index]:
            fail("ranking candidate key differs from enumeration")
        ratios.append(ratio_record(candidate_result.get("likelihood_ratio"), f"ranking.candidate_results[{index}].likelihood_ratio"))
    if ratios != [Fraction(1), Fraction(1), Fraction(1), EXPECTED_RATIO]:
        fail("ranking exact ratios or map order differ from the published result")
    if ranking.get("canonical_candidate_index") != 0 or ratios[0] != Fraction(1):
        fail("ranking canonical ratio baseline is invalid")
    maximum = ratio_record(ranking.get("maximum_likelihood_ratio"), "ranking.maximum_likelihood_ratio")
    if maximum != EXPECTED_RATIO or ranking.get("maximizer_indices") != [3] or ranking.get("display_index") != 3:
        fail("ranking maximizer or display order is invalid")
    if ordered_map(ranking.get("display_key"), units, "ranking.display_key") != maps[3]:
        fail("ranking display key is not the selected z map")

    if selection.get("status") != "complete" or selection.get("candidate_count") != 4 or selection.get("candidate_set_sha256") != candidate_set_hash or selection.get("claims_global_optimality") is not False or selection.get("claims_fixed_assignments_forced") is not False:
        fail("selection does not preserve the complete map set")
    selection_maps = selection.get("all_primary_optimal_maps")
    if not isinstance(selection_maps, list) or [ordered_map(candidate, units, "selection map") for candidate in selection_maps] != maps:
        fail("selection map set differs from enumeration")
    if selection.get("maximizer_indices") != [3] or selection.get("maximizer_count") != 1:
        fail("selection maximizer record is invalid")
    if selection.get("maximizer_maps") != [maps[3]] or ordered_map(selection.get("display_key"), units, "selection.display_key") != maps[3] or selection.get("display_index") != 3:
        fail("selection does not name the z map consistently")
    if selection.get("primary_target") != target or selection.get("baseline_index") != 0 or selection.get("baseline_incumbent") != maps[0]:
        fail("selection target or baseline index is invalid")

    if result.get("status") != "complete" or result.get("reason") != "primary_optimal_set_ranked" or result.get("candidate_count") != 4 or result.get("candidate_set_sha256") != candidate_set_hash or result.get("maximizer_indices") != [3] or result.get("primary_optimal_set_complete_within_domain") is not True or result.get("baseline_incumbent") != maps[0] or result.get("claims_global_optimality") is not False or result.get("claims_fixed_assignments_forced") is not False:
        fail("result summary is inconsistent")
    diagnostics = result.get("diagnostics")
    if not isinstance(diagnostics, Mapping) or diagnostics.get("candidate_count") != 4 or diagnostics.get("secondary_maximizer_indices") != [3] or diagnostics.get("test_token_count") != 19931 or diagnostics.get("uses_planted_key_for_diagnostics_only") is not True:
        fail("result diagnostics summary is invalid")
    stream_hashes = diagnostics.get("test_stream_sha256")
    if not isinstance(stream_hashes, Mapping):
        fail("test stream hashes are missing")
    for name, value in stream_hashes.items():
        require_hash(value, f"diagnostics.test_stream_sha256.{name}")
    diagnostic_rows = diagnostics.get("candidate_diagnostics")
    if not isinstance(diagnostic_rows, list) or len(diagnostic_rows) != 4:
        fail("result diagnostics do not cover all maps")
    expected_rows = (
        (45, 111048, 4, 19927),
        (45, 111048, 4, 19927),
        (45, 111048, 4, 19927),
        (46, 111052, 0, 19931),
    )
    for index, (expected_key, expected_correct, expected_errors, expected_words) in enumerate(expected_rows):
        row = diagnostic_rows[index]
        if not isinstance(row, Mapping) or row.get("candidate_index") != index:
            fail("diagnostic candidate order is invalid")
        if (
            row.get("key_correct") != expected_key
            or row.get("key_positions") != 46
            or row.get("secondary_maximizer") is not (index == 3)
            or row.get("test_observed_positions") != 111052
            or row.get("test_observed_correct") != row.get("test_correct")
            or row.get("test_positions") != 111052
            or row.get("test_correct") != expected_correct
            or row.get("test_errors") != expected_errors
            or row.get("test_unseen_positions") != 0
            or row.get("test_unseen_units") != []
            or row.get("test_word_correct") != expected_words
            or row.get("test_word_count") != 19931
        ):
            fail(f"diagnostics for candidate {index} are inconsistent")

    return {
        "records": loaded,
        "hashes": hashes,
        "target": target,
        "objective_fingerprint": objective_fingerprint,
        "maps": maps,
        "ratios": ratios,
        "candidate_set_hash": candidate_set_hash,
        "value_certificate": value_certificate,
        "diagnostics": diagnostics,
        "fixed_count": len(fixed_map),
        "source_hash_count": len(code_hashes),
    }


def render_report(values: Mapping[str, Any]) -> str:
    """Render a deterministic short public report."""

    hashes = values["hashes"]
    maps: list[dict[str, str]] = values["maps"]
    ratios: list[Fraction] = values["ratios"]
    diagnostics = values["diagnostics"]
    certificate = values["value_certificate"]
    enum = values["records"]["enumeration"]
    result = values["records"]["result"]
    lines = [
        "# Complete optimal-set Latin control",
        "",
        "**The project has not deciphered the Voynich manuscript.**",
        "",
        "This report describes one inspected development control. It does not give a manuscript reading, translation, or historical key.",
        "The result covers one declared finite domain and keeps the earlier failed recovery gate unchanged.",
        "",
        "## Scope and result",
        "",
        f"The earlier score certificate gives lower and upper bounds of `{certificate['lower_bound']:,}` for the target `{values['target']:,}`.",
        f"The certificate uses the `bitset` bound and has a live frontier of {certificate['frontier_node_count']} nodes. `search_exhausted` is `{str(certificate['search_exhausted']).lower()}`.",
        f"The published query records force {values['fixed_count']} assignments. Unit `{EXPECTED_FREE_UNIT}` remains ambiguous. No unit remains unresolved.",
        "The enumeration gives unit `c40` the full 26-letter lower-case ASCII alphabet before capacity checks.",
        f"It visits {enum['visited_nodes']} nodes, reaches {enum['feasible_leaves']} feasible leaves, and prunes {enum['capacity_prunes']} capacity branches.",
        f"It retains {len(maps)} maps at the exact target score. The raw product bound is {enum['product_bound']}.",
        "This is complete only for the supplied weighted ciphertext, lexicon, alphabet, capacity, and forced assignment domain.",
        "Together, the score certificate, forced exclusions, and complete enumeration establish exactly four optimum maps in this finite control.",
        "The secondary model uses training plaintext only, a three-character context, and exact additive smoothing 1/10.",
        "It scores validation tokens with a 28-symbol vocabulary, including unknown and end symbols. Ratios use the `j` map as the baseline.",
        "",
        "| Candidate | Free unit `c40` | Exact secondary ratio | Secondary maximizer | Fitted assignments | Test characters | Test words |",
        "| ---: | :---: | :---: | :---: | ---: | ---: | ---: |",
    ]
    diagnostic_rows = diagnostics["candidate_diagnostics"]
    for index, (candidate, ratio, row) in enumerate(zip(maps, ratios, diagnostic_rows, strict=True)):
        ratio_text = f"{ratio.numerator}/{ratio.denominator}"
        lines.append(
            f"| {index} | `{candidate[EXPECTED_FREE_UNIT]}` | `{ratio_text}` | "
            f"{'yes' if index == 3 else 'no'} | {row['key_correct']}/{row['key_positions']} | "
            f"{row['test_correct']}/{row['test_positions']} | {row['test_word_correct']}/{row['test_word_count']} |"
        )
    lines.extend(
        [
            "",
            "The four exact maps use `c40 = j`, `w`, `y`, and `z`.",
            "The maps cover 46 observed cipher units. Assignments for unused cipher units remain unidentified.",
            "The `z` map is the only exact secondary maximizer and the display map.",
            "It matches all 46 fitted assignments, all 111,052 test characters, and all 19,931 test words in this known control.",
            "The baseline map remains a 45-of-46 assignment match with four test-character errors. This follow-up does not change the earlier failed exact-recovery gate.",
            "The test comparison runs after selection. It does not change the candidate set or the tie rule.",
            "",
            "## Provenance and reproduction",
            "",
            f"The publication freeze commit is `{FREEZE_COMMIT}`. The freeze precedes the primary run at `09:14:24.58 UTC`.",
            f"The secondary protocol hash is `{SECONDARY_PROTOCOL_SHA256}`.",
            f"The input records {values['source_hash_count']} implementation hashes. The three new module hashes are checked below.",
            "",
            "| Public record | SHA-256 |",
            "| --- | --- |",
        ]
    )
    for name in ("input", "enumeration", "ranking", "selection", "result"):
        lines.append(f"| `{name}.json` | `{hashes[name]}` |")
    lines.extend(
        [
            "",
            "| New implementation file | SHA-256 |",
            "| --- | --- |",
        ]
    )
    for path, digest in EXPECTED_NEW_SOURCE_HASHES.items():
        lines.append(f"| `{path}` | `{digest}` |")
    lines.extend(
        [
            "",
            "Run the fixed study from the clean freeze checkout:",
            "",
            "```sh",
            f"git checkout {FREEZE_COMMIT}",
            "python scripts/fetch_reference_sources.py",
            "python experiments/optimal_set/run_study.py --output-dir results/optimal-set-secondary-v1-latin",
            "```",
            "",
            "The summary generator is in the later publication checkout. Run it there against the published records:",
            "",
            "```sh",
            "python scripts/build_optimal_set_summary.py",
            "```",
            "",
            "The five public JSON records are byte-for-byte copies of the run records.",
            "This script checks their canonical bytes, SHA-256 links, map set, exact ratios, diagnostic totals, and source hashes.",
            "The [verification receipt](optimal-set-verification.json) records 262 passing tests and a clean public replay.",
            "All five replay files match the primary files byte for byte.",
            "The [independent record audit](optimal-set-record-audit.json) rebuilt model counts and exact ratios without importing the secondary scorer.",
            "All 18 audit checks pass. These are internal computational checks, not external scholarly validation.",
            "",
            "The [independent verifier](../scripts/verify_optimal_set_independently.py) rebuilds this audit from tracked result files and pinned reference sources.",
            "Run it from the publication checkout after fetching the reference sources:",
            "",
            "```sh",
            "python scripts/fetch_reference_sources.py",
            "python scripts/verify_optimal_set_independently.py",
            "cmp reports/optimal-set-record-audit.json results/optimal-set-independent-replay/audit.json",
            "```",
            "",
            "A clean public checkout reproduced the audit byte for byte without private primary-run files.",
            "",
            "## Limits",
            "",
            "The score certificate and 45 exclusions apply to the fixed Latin control only.",
            "The selected `z` map is a finite-control result. It does not identify manuscript language, meaning, authorship, or plaintext.",
            "The study is inspected exploratory development, not blind validation.",
            "",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records-dir", type=Path, default=DEFAULT_RECORDS_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    records_dir = args.records_dir.resolve()
    output = args.output.resolve()
    values = validate_records(records_dir)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_report(values), encoding="utf-8")
    try:
        print(output.relative_to(ROOT))
    except ValueError:
        print(output.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
