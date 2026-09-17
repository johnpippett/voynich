#!/usr/bin/env python3
"""Build the public homophonic feasibility report from aggregate JSON records."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_REPORTS = ROOT / "reports" / "homophonic-feasibility-v1"
OUTPUT = ROOT / "reports" / "HOMOPHONIC.md"

RUNS: tuple[tuple[str, str, str, str], ...] = (
    ("latin-cold", "Latin LLCT", "Latin", "none"),
    ("latin-assisted", "Latin LLCT", "Latin", "anneal"),
    ("italian-cold", "Old Italian", "Old Italian", "none"),
    ("italian-assisted", "Old Italian", "Old Italian", "anneal"),
)
RUN_NAMES = tuple(run[0] for run in RUNS)
PROTOCOL_COMMIT = "ce8b626ab3cf8147829716f7828dff7fceba6cde"
PROTOCOL_SHA256 = "0e6a6edf5e0172f5e7a0f1fbf2f7ede8b9b181c7180aa616de58f44ae04d1249"
ALPHABET = tuple("abcdefghijklmnopqrstuvwxyz")


def load_json(name: str) -> dict[str, Any]:
    """Load one public result. Never read private result directories here."""

    path = PUBLIC_REPORTS / f"{name}.json"
    if not path.is_file():
        raise FileNotFoundError(f"Missing public homophonic result: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"The public homophonic result is not an object: {path}")
    return value


def load_key_record(name: str) -> tuple[dict[str, Any], str]:
    path = PUBLIC_REPORTS / f"{name}.keys.json"
    if not path.is_file():
        raise FileNotFoundError(f"Missing public homophonic key record: {path}")
    raw = path.read_bytes()
    value = json.loads(raw.decode("utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"The public homophonic key record is not an object: {path}")
    return value, hashlib.sha256(raw).hexdigest()


def integer(value: Any, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field} must be an integer")
    return value


def percent(value: float | None, digits: int = 2) -> str:
    if value is None:
        return "n/a"
    if value < 1 and round(value * 100, digits) >= 100:
        digits = max(digits, 4)
    if value < 1 and round(value * 100, digits) >= 100:
        return "<100%"
    return f"{value * 100:.{digits}f}%"


def fraction(correct: Any, total: Any, *, field: str) -> str:
    numerator = integer(correct, field=f"{field}.correct")
    denominator = integer(total, field=f"{field}.total")
    if denominator < 0 or numerator < 0 or numerator > denominator:
        raise ValueError(f"Invalid count for {field}: {numerator}/{denominator}")
    rate = numerator / denominator if denominator else None
    return f"{numerator}/{denominator} ({percent(rate)})"


def report_link(name: str) -> str:
    return f"[JSON](homophonic-feasibility-v1/{name}.json)"


def key_link(name: str) -> str:
    return f"[key](homophonic-feasibility-v1/{name}.keys.json)"


def _require_mapping(value: Any, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{field} must be an object")
    return value


def _check_accuracy(metrics: Mapping[str, Any], field: str) -> None:
    for name in (
        "full_char_correct", "full_char_total", "full_token_correct",
        "full_token_total", "observed_position_correct",
        "observed_position_total", "fully_observed_token_correct",
        "fully_observed_token_total", "unobserved_position_count",
    ):
        integer(metrics.get(name), field=f"{field}.{name}")
    fraction(metrics["full_char_correct"], metrics["full_char_total"], field=f"{field}.full_char")
    fraction(metrics["full_token_correct"], metrics["full_token_total"], field=f"{field}.full_token")
    fraction(
        metrics["observed_position_correct"],
        metrics["observed_position_total"],
        field=f"{field}.observed_position",
    )
    fraction(
        metrics["fully_observed_token_correct"],
        metrics["fully_observed_token_total"],
        field=f"{field}.fully_observed_token",
    )


def _check_objective(result: Mapping[str, Any], name: str) -> None:
    objective = _require_mapping(result.get("objective"), f"{name}.objective")
    solver = _require_mapping(result.get("solver"), f"{name}.solver")
    token_count = integer(objective.get("N_token_count"), field=f"{name}.N_token_count")
    type_count = integer(objective.get("T_type_count"), field=f"{name}.T_type_count")
    denominator = integer(objective.get("denominator"), field=f"{name}.denominator")
    if token_count <= 0 or type_count <= 0:
        raise ValueError(f"{name} has an empty objective")
    expected_denominator = 2 * token_count * type_count
    if denominator != expected_denominator:
        raise ValueError(f"{name} has an invalid objective denominator")
    if objective.get("weights_total") != denominator:
        raise ValueError(f"{name} weights do not sum to the denominator")
    if objective.get("weights_match_denominator") is not True:
        raise ValueError(f"{name} does not confirm its denominator arithmetic")
    if objective.get("weight_formula") != "count*T+N":
        raise ValueError(f"{name} has an unexpected weight formula")
    if objective.get("normalization_formula") != "2*T*N":
        raise ValueError(f"{name} has an unexpected normalization formula")

    fit_hits = _require_mapping(objective.get("fit_hits"), f"{name}.objective.fit_hits")
    token_hits = integer(fit_hits.get("token_hits"), field=f"{name}.token_hits")
    type_hits = integer(fit_hits.get("type_hits"), field=f"{name}.type_hits")
    if not (0 <= token_hits <= token_count and 0 <= type_hits <= type_count):
        raise ValueError(f"{name} has invalid fit hit counts")
    expected_score = token_hits * type_count + type_hits * token_count
    score_from_key = integer(objective.get("score_from_key"), field=f"{name}.score_from_key")
    solver_score = integer(solver.get("score"), field=f"{name}.solver.score")
    if score_from_key != expected_score or solver_score != expected_score:
        raise ValueError(f"{name} score does not match its token and type hits")
    if objective.get("weights_total") != denominator:
        raise ValueError(f"{name} objective total is inconsistent")
    try:
        normalized_score = float(objective["normalized_score"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"{name} has no numeric normalized score") from exc
    if abs(normalized_score - score_from_key / denominator) > 1e-12:
        raise ValueError(f"{name} normalized score is inconsistent")

    lower = integer(solver.get("lower_bound"), field=f"{name}.solver.lower_bound")
    upper = integer(solver.get("upper_bound"), field=f"{name}.solver.upper_bound")
    if not lower <= solver_score <= upper:
        raise ValueError(f"{name} score is outside its reported bounds")
    if integer(solver.get("total_weight"), field=f"{name}.solver.total_weight") != denominator:
        raise ValueError(f"{name} solver total differs from objective denominator")
    oracle = _require_mapping(result.get("oracle"), f"{name}.oracle")
    oracle_objective = _require_mapping(oracle.get("objective"), f"{name}.oracle.objective")
    oracle_score = integer(oracle_objective.get("score_from_key"), field=f"{name}.oracle.score_from_key")
    if oracle_score > upper:
        raise ValueError(f"{name} upper bound excludes the planted objective")
    certified = solver.get("score_certified")
    if not isinstance(certified, bool):
        raise ValueError(f"{name} must report score_certified")
    ambiguity = _require_mapping(result.get("ambiguity"), f"{name}.ambiguity")
    preserved = integer(
        ambiguity.get("keys_preserving_current_hits"),
        field=f"{name}.ambiguity.keys_preserving_current_hits",
    )
    if preserved < 0:
        raise ValueError(f"{name} has a negative preserved-hit count")
    completion_count = integer(
        ambiguity.get("completion_count"),
        field=f"{name}.ambiguity.completion_count",
    )
    if completion_count != preserved:
        raise ValueError(f"{name} completion count differs from preserved-hit count")
    optimal_lower = ambiguity.get("optimal_key_count_lower_bound")
    if certified:
        if lower != upper or lower != solver_score:
            raise ValueError(f"{name} claims certification with unequal bounds")
        if (
            isinstance(optimal_lower, bool)
            or not isinstance(optimal_lower, int)
            or optimal_lower < 1
            or optimal_lower != completion_count
        ):
            raise ValueError(f"{name} has no optimal-key lower bound after certification")
    elif optimal_lower is not None:
        raise ValueError(f"{name} reports an optimal-key count without certification")


def _check_inventory(result: Mapping[str, Any], name: str) -> None:
    encryption = _require_mapping(result.get("encryption"), f"{name}.encryption")
    if encryption.get("family") != "cap2" or encryption.get("seed") != 7000:
        raise ValueError(f"{name} does not use the frozen cap2 seed 7000 control")
    units = encryption.get("units")
    if not isinstance(units, list) or len(units) != 52 or len(set(units)) != 52:
        raise ValueError(f"{name} does not report the 52-unit cap2 inventory")
    if any(not isinstance(unit, str) for unit in units):
        raise ValueError(f"{name} has a non-string cipher unit")
    if set(units) != {f"c{index:02d}" for index in range(52)}:
        raise ValueError(f"{name} does not report the c00-c51 inventory")
    if tuple(encryption.get("alphabet", ())) != ALPHABET:
        raise ValueError(f"{name} does not report the lowercase ASCII alphabet")
    cipher_to_plain = _require_mapping(
        encryption.get("cipher_to_plain"),
        f"{name}.encryption.cipher_to_plain",
    )
    if set(cipher_to_plain) != set(units):
        raise ValueError(f"{name} cipher map does not cover the unit inventory")
    letter_counts = {letter: 0 for letter in ALPHABET}
    for unit in units:
        letter = cipher_to_plain[unit]
        if not isinstance(letter, str) or letter not in letter_counts:
            raise ValueError(f"{name} cipher map contains an invalid plaintext letter")
        letter_counts[letter] += 1
    if set(letter_counts.values()) != {2}:
        raise ValueError(f"{name} cipher map does not assign two units to each letter")
    emission = encryption.get("emission_order")
    if not isinstance(emission, Mapping):
        raise ValueError(f"{name} does not report an emission cycle for each letter")
    if tuple(sorted(emission)) != ALPHABET:
        raise ValueError(f"{name} emission cycles do not cover the 26-letter alphabet")
    emitted = []
    for letter in ALPHABET:
        cycle = emission[letter]
        if not isinstance(cycle, list) or len(cycle) != 2:
            raise ValueError(f"{name} does not report exactly two units for {letter}")
        if any(cipher_to_plain[unit] != letter for unit in cycle):
            raise ValueError(f"{name} emission cycles disagree with the cipher map")
        emitted.extend(cycle)
    if sorted(emitted) != sorted(units):
        raise ValueError(f"{name} emission cycles do not match the unit inventory")


def _check_key_record(result: Mapping[str, Any], key_record: Mapping[str, Any], key_sha: str, name: str) -> None:
    expected_sha = result.get("key_record_sha256")
    if not isinstance(expected_sha, str) or expected_sha != key_sha:
        raise ValueError(f"{name} key-record SHA-256 does not match the result")
    if key_record.get("kind") != "synthetic_reference_control":
        raise ValueError(f"{name} key record has an unexpected kind")
    if key_record.get("family") != result.get("family") or key_record.get("seed") != result.get("seed"):
        raise ValueError(f"{name} key record does not match the result control")
    if key_record.get("warm_start") != result.get("warm_start"):
        raise ValueError(f"{name} key record does not match the warm-start mode")
    if not isinstance(key_record.get("key"), Mapping):
        raise ValueError(f"{name} key record has no key object")


def validate_records(records: Mapping[str, Mapping[str, Any]], key_records: Mapping[str, Mapping[str, Any]], key_shas: Mapping[str, str]) -> None:
    if tuple(records) != RUN_NAMES:
        raise ValueError("The public report must contain exactly the four frozen runs")
    protocol_hashes: set[str] = set()
    for name, _label, language_label, start in RUNS:
        result = records[name]
        if result.get("kind") != "synthetic_reference_control":
            raise ValueError(f"{name} is not a reference control")
        expected_language = "latin_llct" if language_label == "Latin" else "italian_old"
        metadata = _require_mapping(result.get("metadata"), f"{name}.metadata")
        if metadata.get("language") != expected_language:
            raise ValueError(f"{name} has an unexpected reference language")
        if result.get("family") != "cap2" or result.get("seed") != 7000:
            raise ValueError(f"{name} does not use the frozen run settings")
        if result.get("node_budget") != 1000 or result.get("bound_engine") != "bitset":
            raise ValueError(f"{name} does not use the frozen search settings")
        if result.get("warm_start") != start:
            raise ValueError(f"{name} has an unexpected warm-start mode")
        if start == "none" and (result.get("heuristic") is not None or result.get("heuristic_diagnostics") is not None):
            raise ValueError(f"{name} reports warm-start data for a cold run")
        if start == "anneal" and not isinstance(result.get("heuristic_diagnostics"), Mapping):
            raise ValueError(f"{name} has no warm-start diagnostics")
        if result.get("emission") != "per-letter cycles, reset at each partition":
            raise ValueError(f"{name} has an unexpected emission rule")
        protocol_sha = result.get("protocol_sha256")
        if protocol_sha != PROTOCOL_SHA256:
            raise ValueError(f"{name} has no protocol SHA-256")
        protocol_hashes.add(protocol_sha)
        _check_inventory(result, name)
        _check_objective(result, name)
        _check_key_record(result, key_records[name], key_shas[name], name)
        for split in ("validation", "test"):
            _check_accuracy(_require_mapping(result["accuracy"].get(split), f"{name}.accuracy.{split}"), f"{name}.accuracy.{split}")
        fitted = _require_mapping(result.get("fitted_key_accuracy"), f"{name}.fitted_key_accuracy")
        fitted_correct = integer(fitted.get("correct"), field=f"{name}.fitted_key_accuracy.correct")
        fitted_total = integer(fitted.get("total"), field=f"{name}.fitted_key_accuracy.total")
        if fitted_total < 0 or fitted_correct < 0 or fitted_correct > fitted_total:
            raise ValueError(f"{name} has invalid fitted-key accuracy")
        gates = _require_mapping(result.get("gates"), f"{name}.gates")
        for split in ("validation", "test"):
            split_gate = _require_mapping(gates.get(split), f"{name}.gates.{split}")
            for flag in ("observed_positions_pass", "fully_observed_tokens_pass", "full_decoding_pass"):
                if split_gate.get(flag) not in (True, False, None):
                    raise ValueError(f"{name}.gates.{split}.{flag} is invalid")

        if start == "anneal":
            _check_warm_diagnostics(result, name)
        if name == "latin-cold":
            _check_positive_hit_error_claim(result)
    if len(protocol_hashes) != 1:
        raise ValueError("The four public records use different protocol hashes")

    for language in ("latin", "italian"):
        cold = records[f"{language}-cold"]
        assisted = records[f"{language}-assisted"]
        for field in ("fit_input", "stream_sha256"):
            cold_value = _require_mapping(cold.get(field), f"{language}-cold.{field}")
            assisted_value = _require_mapping(assisted.get(field), f"{language}-assisted.{field}")
            if field == "fit_input":
                compare = ("sha256", "token_count", "type_count", "unit_count")
            else:
                compare = (
                    "plaintext_train", "plaintext_validation", "plaintext_test",
                    "cipher_train", "cipher_validation", "cipher_test",
                )
            for key in compare:
                if cold_value.get(key) != assisted_value.get(key):
                    raise ValueError(f"{language} cold and anneal runs do not share {field}.{key}")


def _check_warm_diagnostics(result: Mapping[str, Any], name: str) -> None:
    heuristic = _require_mapping(result.get("heuristic"), f"{name}.heuristic")
    char_score = heuristic.get("score")
    if not isinstance(char_score, (int, float)) or isinstance(char_score, bool):
        raise ValueError(f"{name} has no numeric warm character-model score")
    if heuristic.get("seed") != 408 or heuristic.get("capacity") != 2:
        raise ValueError(f"{name} has an unexpected warm-start seed or capacity")
    config = _require_mapping(heuristic.get("config"), f"{name}.heuristic.config")
    if config.get("objective") != "negative log2 conditional character probability with fixed word boundaries":
        raise ValueError(f"{name} warm score does not identify the character objective")
    if config.get("order") != 3 or config.get("capacity") != 2:
        raise ValueError(f"{name} warm model does not use order 3 and capacity 2")
    try:
        add_alpha = float(config["add_alpha"])
        start_temperature = float(config["start_temperature"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"{name} warm model is missing annealing settings") from exc
    if abs(add_alpha - 0.1) > 1e-12 or abs(start_temperature - 0.02) > 1e-12:
        raise ValueError(f"{name} warm model has unexpected smoothing or temperature")
    budget = _require_mapping(heuristic.get("budget"), f"{name}.heuristic.budget")
    if budget.get("iterations_per_restart") != 2000 or budget.get("restarts") != 8:
        raise ValueError(f"{name} warm model has an unexpected annealing budget")
    if budget.get("completed_restarts") != 8:
        raise ValueError(f"{name} warm model did not complete eight restarts")
    diagnostics = _require_mapping(result.get("heuristic_diagnostics"), f"{name}.heuristic_diagnostics")
    warm_objective = _require_mapping(diagnostics.get("objective"), f"{name}.heuristic_diagnostics.objective")
    selected_objective = _require_mapping(result.get("objective"), f"{name}.objective")
    if warm_objective.get("denominator") != selected_objective.get("denominator"):
        raise ValueError(f"{name} warm and selected objectives use different denominators")
    warm_score = integer(warm_objective.get("score_from_key"), field=f"{name}.warm_score_from_key")
    selected_score = integer(selected_objective.get("score_from_key"), field=f"{name}.selected_score_from_key")
    if selected_score < warm_score:
        raise ValueError(f"{name} exact search lost the warm-start lexical score")
    for split in ("validation", "test"):
        _check_accuracy(
            _require_mapping(diagnostics.get(split), f"{name}.heuristic_diagnostics.{split}"),
            f"{name}.heuristic_diagnostics.{split}",
        )


def _check_positive_hit_error_claim(result: Mapping[str, Any]) -> None:
    accuracy = _require_mapping(result.get("accuracy"), "latin-cold.accuracy")
    test = _require_mapping(accuracy.get("test"), "latin-cold.accuracy.test")
    coverage = _require_mapping(
        result.get("positive_hit_unit_coverage"),
        "latin-cold.positive_hit_unit_coverage",
    )
    partitions = _require_mapping(coverage.get("partitions"), "latin-cold.coverage.partitions")
    test_coverage = _require_mapping(partitions.get("test"), "latin-cold.coverage.partitions.test")
    hit_positions = integer(test_coverage.get("hit_used_positions"), field="latin-cold.hit_used_positions")
    hit_correct = integer(test_coverage.get("hit_used_correct"), field="latin-cold.hit_used_correct")
    outside_positions = integer(
        test_coverage.get("observed_outside_hits_positions"),
        field="latin-cold.observed_outside_hits_positions",
    )
    outside_correct = integer(
        test_coverage.get("observed_outside_hits_correct"),
        field="latin-cold.observed_outside_hits_correct",
    )
    unobserved = integer(test_coverage.get("unobserved_positions"), field="latin-cold.unobserved_positions")
    total_errors = integer(test.get("full_char_total"), field="latin-cold.test_char_total") - integer(
        test.get("full_char_correct"),
        field="latin-cold.test_char_correct",
    )
    if hit_correct != hit_positions:
        raise ValueError("latin-cold positive-hit positions are not all correct")
    if outside_positions - outside_correct != total_errors or unobserved != 0:
        raise ValueError("latin-cold test errors are not fully outside positive hits")


def _warm_char_score(result: Mapping[str, Any]) -> str:
    heuristic = _require_mapping(result.get("heuristic"), "heuristic")
    value = heuristic.get("score")
    return f"{float(value):.3f} negative log2" if isinstance(value, (int, float)) else "n/a"


def _char_metric(result: Mapping[str, Any], split: str, prefix: str = "accuracy") -> str:
    metrics = _require_mapping(
        _require_mapping(result.get(prefix), prefix).get(split),
        f"{prefix}.{split}",
    )
    return fraction(
        metrics["full_char_correct"],
        metrics["full_char_total"],
        field=f"{prefix}.{split}.full_char",
    )


def _test_error_cell(result: Mapping[str, Any]) -> str:
    metrics = _require_mapping(
        _require_mapping(result.get("accuracy"), "accuracy").get("test"),
        "accuracy.test",
    )
    total = integer(metrics["full_char_total"], field="test.full_char_total")
    correct = integer(metrics["full_char_correct"], field="test.full_char_correct")
    return f"{total - correct}/{total}"


def _gate_cell(result: Mapping[str, Any], split: str) -> str:
    gate = _require_mapping(
        _require_mapping(result.get("gates"), "gates").get(split),
        f"gates.{split}",
    )
    return "pass" if gate.get("observed_positions_pass") is True and gate.get("fully_observed_tokens_pass") is True else "fail"


def _ambiguity_cell(result: Mapping[str, Any]) -> str:
    ambiguity = _require_mapping(result["ambiguity"], "ambiguity")
    solver = _require_mapping(result["solver"], "solver")
    if solver.get("score_certified") is True:
        count = integer(ambiguity["optimal_key_count_lower_bound"], field="optimal_key_count_lower_bound")
        return f"`{count}`"
    return "not certified"


def reproduction_commands() -> list[str]:
    output_dir = "results/reproduction-homophonic-v1"
    common = "--family cap2 --seed 7000 --nodes 1000 --bound-engine bitset"
    anneal = "--anneal-seed 408 --iterations 2000 --restarts 8 --temperature 0.02"
    return [
        f"mkdir -p {output_dir}",
        f"python experiments/homophonic/run_controls.py --language latin_llct {common} --warm-start none --output {output_dir}/latin-cold.json",
        f"python experiments/homophonic/run_controls.py --language latin_llct {common} --warm-start anneal {anneal} --output {output_dir}/latin-assisted.json",
        f"python experiments/homophonic/run_controls.py --language italian_old {common} --warm-start none --output {output_dir}/italian-cold.json",
        f"python experiments/homophonic/run_controls.py --language italian_old {common} --warm-start anneal {anneal} --output {output_dir}/italian-assisted.json",
    ]


def build_report() -> str:
    records = {name: load_json(name) for name in RUN_NAMES}
    key_records: dict[str, dict[str, Any]] = {}
    key_shas: dict[str, str] = {}
    for name in RUN_NAMES:
        key_records[name], key_shas[name] = load_key_record(name)
    validate_records(records, key_records, key_shas)

    first = records["latin-cold"]
    first_objective = _require_mapping(first["objective"], "latin-cold.objective")
    first_solver = _require_mapping(first["solver"], "latin-cold.solver")
    first_fitted = _require_mapping(first["fitted_key_accuracy"], "latin-cold.fitted_key_accuracy")
    first_test = _require_mapping(
        _require_mapping(first["accuracy"], "latin-cold.accuracy")["test"],
        "latin-cold.accuracy.test",
    )
    first_ambiguity = _require_mapping(first["ambiguity"], "latin-cold.ambiguity")
    first_char_errors = integer(first_test["full_char_total"], field="latin-cold.test_char_total") - integer(
        first_test["full_char_correct"],
        field="latin-cold.test_char_correct",
    )
    first_score = integer(first_solver["score"], field="latin-cold.score")
    first_denominator = integer(first_objective["denominator"], field="latin-cold.denominator")
    first_key_correct = integer(first_fitted["correct"], field="latin-cold.fitted_correct")
    first_key_total = integer(first_fitted["total"], field="latin-cold.fitted_total")
    first_test_total = integer(first_test["full_char_total"], field="latin-cold.test_char_total")
    first_certified = first_solver.get("score_certified") is True
    first_optimal_lower = integer(
        first_ambiguity["optimal_key_count_lower_bound"],
        field="latin-cold.optimal_key_count_lower_bound",
    ) if first_certified else None

    lines = [
        "# Homophonic feasibility pilot",
        "",
        f"The Latin cold control has a {'certified ' if first_certified else ''}finite dictionary score of `{first_score}` over denominator `{first_denominator}`.",
        f"Its selected map has `{first_char_errors}` test character errors in `{first_test_total}` positions.",
        f"Its map matches the planted assignment for `{first_key_correct}/{first_key_total}` units observed in the validation fitting input.",
        f"At least `{first_optimal_lower}` optimal key completions preserve its current hits." if first_certified else "Its score is not certified, so its hit-preserving count is not an optimal-key count.",
        "Other optimal maps can exist.",
        "These runs use reference controls. They contain no manuscript measurement.",
        "",
        "## Frozen scope",
        "",
        "The four runs use Latin LLCT and Old Italian reference partitions.",
        "Latin LLCT contains early medieval Tuscan legal charters.",
        "The Old Italian source is Dante Alighieri's Comedy, an edited text by one author.",
        "The [reference corpora](../docs/research/reference-corpora.md) document these source limits.",
        "Their dates, genres, and editorial histories differ.",
        "Their scores are descriptive controls and are not direct language comparisons.",
        "",
        "Each reference uses one encryption seed, `7000`.",
        "The cold and annealing runs within each reference use the same ciphertext.",
        "The map family is `cap2` with 52 atomic `c##` units and two units for each letter.",
        "Each run uses the bitset bound and a 1,000-node budget.",
        "Annealing uses order `3`, additive smoothing `0.1`, capacity `2`, seed `408`, eight restarts, 2,000 iterations, and temperature `0.02`.",
        "The solver fits only units that occur in the encrypted validation input.",
        "The selected map is written before the test partition is scored.",
        "",
        f"The [frozen protocol](../docs/plans/visual-homophonic-pilot.md) is at commit `{PROTOCOL_COMMIT}`.",
        "The [solver review](../experiments/homophonic/REVIEW.md) records the search limits.",
        "The [reference manifest](../data/reference_manifest.json) identifies the source corpora.",
        "",
        "## Results",
        "",
        "The objective uses exact integer token and type hits.",
        "For a cipher word type with count `n`, the weight is `n*T + N`.",
        "`T` is the cipher word-type count and `N` is the cipher token count.",
        "The denominator is `2*T*N`.",
        "These type counts are cipher word types.",
        "Homophonic cycles can increase the number of cipher types.",
        "Therefore, these scores are not comparable with the old injective Latin score `0.891` in the [injective report](LEXICON.md).",
        "",
        "The primary results table shows fitted key recovery and test character errors.",
        "A score is certified when its valid lower and upper bounds are equal.",
        "A certified score does not prove a unique key or the correct planted key.",
        "",
        "| Run | Reference | Fitted key correct / observed | Test character errors / total | Score certified | Optimal-key lower bound |",
        "| --- | --- | ---: | ---: | --- | ---: |",
    ]
    for name, _label, language_label, _start in RUNS:
        result = records[name]
        solver = _require_mapping(result["solver"], f"{name}.solver")
        fitted = _require_mapping(result["fitted_key_accuracy"], f"{name}.fitted_key_accuracy")
        lines.append(
            f"| `{name}` | {language_label} | `{integer(fitted['correct'], field='fitted_correct')}/{integer(fitted['total'], field='fitted_total')}` | "
            f"`{_test_error_cell(result)}` | {'yes' if solver['score_certified'] else 'no'} | {_ambiguity_cell(result)} |"
        )

    lines.extend([
        "",
        "The bounds table shows raw integer values.",
        "",
        "| Run | Lower bound | Upper bound | Denominator |",
        "| --- | ---: | ---: | ---: |",
    ])
    for name, _label, _language_label, _start in RUNS:
        result = records[name]
        objective = _require_mapping(result["objective"], f"{name}.objective")
        solver = _require_mapping(result["solver"], f"{name}.solver")
        lines.append(
            f"| `{name}` | `{integer(solver['lower_bound'], field='lower_bound')}` | "
            f"`{integer(solver['upper_bound'], field='upper_bound')}` | "
            f"`{integer(objective['denominator'], field='denominator')}` |"
        )

    lines.extend([
        "",
        "The fit and gate table keeps validation and test diagnostics separate.",
        "Validation is a fit diagnostic. Test scoring uses the frozen selected map.",
        "The declared gate requires complete recovery for observed positions and fully observed tokens.",
        "",
        "| Run | Fit token hits | Fit type hits | Validation gate | Test gate |",
        "| --- | ---: | ---: | --- | --- |",
    ])
    for name, _label, _language_label, _start in RUNS:
        result = records[name]
        objective = _require_mapping(result["objective"], f"{name}.objective")
        fit_hits = _require_mapping(objective["fit_hits"], f"{name}.fit_hits")
        lines.append(
            f"| `{name}` | `{integer(fit_hits['token_hits'], field='token_hits')}/{integer(objective['N_token_count'], field='token_count')}` | "
            f"`{integer(fit_hits['type_hits'], field='type_hits')}/{integer(objective['T_type_count'], field='type_count')}` | "
            f"{_gate_cell(result, 'validation')} | {_gate_cell(result, 'test')} |"
        )

    lines.extend([
        "",
        "A failed declared gate keeps the VMS study deferred.",
        "",
        "## Warm-start diagnostics",
        "",
        "The annealing runs fit a character model with fixed word boundaries.",
        "The character-model score is separate from the exact lexicon objective.",
        "The annealing map supplies an incumbent only.",
        "The exact solver selects the final map by the integer lexicon objective.",
        "",
        "| Run | Warm character score | Warm lexical score | Selected lexical score | Warm test characters correct | Selected test characters correct |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ])
    for name, _label, _language_label, start in RUNS:
        if start != "anneal":
            continue
        result = records[name]
        diagnostics = _require_mapping(result["heuristic_diagnostics"], f"{name}.heuristic_diagnostics")
        warm_objective = _require_mapping(diagnostics["objective"], f"{name}.warm_objective")
        selected_objective = _require_mapping(result["objective"], f"{name}.selected_objective")
        lines.append(
            f"| `{name}` | {_warm_char_score(result)} | `{integer(warm_objective['score_from_key'], field='warm_score')}` | "
            f"`{integer(selected_objective['score_from_key'], field='selected_score')}` | "
            f"{_char_metric(result, 'test', prefix='heuristic_diagnostics')} | {_char_metric(result, 'test')} |"
        )

    lines.extend([
        "",
        "The warm character score is a negative log2 probability.",
        "A lower character score and a higher lexical score have different meanings.",
        "The warm and selected test columns show separate map diagnostics.",
        "",
        "## Artifacts",
        "",
        "The public JSON records contain full integer counts, hashes, and partition diagnostics.",
        "The key records contain the selected maps without corpus word arrays.",
        "",
        "| Run | Result | Key record |",
        "| --- | --- | --- |",
    ])
    for name, _label, _language_label, _start in RUNS:
        lines.append(f"| `{name}` | {report_link(name)} | {key_link(name)} |")

    lines.extend([
        "",
        "## Reproduction",
        "",
        "Run these commands from the repository root with new output paths.",
        "The runner refuses an existing result or key file.",
        "",
        "```sh",
        *reproduction_commands(),
        "```",
        "",
        "The four result records and four key records are linked in the tables above.",
        "The [verification receipt](homophonic-verification.json) records checks for the published artifacts.",
        "",
        "## Limits",
        "",
        "The controls use finite reference lexicons and known synthetic ciphertext.",
        "They do not estimate a false-positive rate.",
        "They do not reject all keys, all languages, or all cipher models.",
        "A certified finite score does not establish a historical reading.",
        "The controls provide no decipherment or translation.",
        "",
    ])
    return "\n".join(lines)


def main() -> None:
    OUTPUT.write_text(build_report(), encoding="utf-8")
    print(OUTPUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
