"""Run the bounded primary-optimal-set and secondary-score study.

The public runner accepts a complete synthetic input description.  It writes
each artifact once and stops before ranking when enumeration is incomplete.
The reference loader is separate so synthetic tests cannot read the corpus.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Iterable, Mapping, Sequence
import argparse
from fractions import Fraction
import hashlib
import json
from pathlib import Path
from pathlib import PurePosixPath
import re
import string
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
for import_path in (ROOT, ROOT / "src"):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

from experiments.homophonic.controls import encrypt_words, seeded_control_key
from experiments.lexicon.run_pilot import objective_weights
from experiments.optimal_set.enumerate import (
    _normalise_alphabet,
    _normalise_cipher_counts,
    _normalise_lexicon,
    _domain_fingerprint,
    _objective_domain_fingerprint,
    _validate_fixed_key,
    enumerate_equal_score_completions,
)
from experiments.optimal_set.secondary import rank_secondary
from voynich.reference import load_reference_partitions
from voynich.substitution import fit_language_model


Word = str | tuple[str, ...]
Capacity = int | None

MODEL_ORDER = 3
MODEL_ADD_ALPHA = 0.1
MODEL_ALPHABET = tuple(string.ascii_lowercase)
DEFAULT_MAX_PRODUCT = 1_000_000
DEFAULT_NODE_BUDGET = 1_000_000
DEFAULT_MAX_DELTA_EVENTS = 4096
DEFAULT_MAX_RATIO_BITS = 1_000_000
RATIO_DEFINITION = (
    "candidate likelihood divided by the canonical first-candidate "
    "likelihood; alpha 0.1 is represented as (10*c+1)/(10*t+V)"
)

BASELINE_REPORT = "reports/homophonic-feasibility-v1/latin-cold.json"
BASELINE_KEY = "reports/homophonic-feasibility-v1/latin-cold.keys.json"
BASELINE_REPORT_SHA256 = (
    "923dba00df53ff05ca88e91362ea44c693d66b8f0824071d85cc5b0d984ba77e"
)
REFERENCE_MANIFEST = "data/reference_manifest.json"
REFERENCE_MANIFEST_SHA256 = (
    "f261b781f150991e3305aae5057a94dc91afd8e59c58bb22ff199347f5ce3e6d"
)
ASSIGNMENT_DIR = "reports/identifiability-v1-latin"
ASSIGNMENT_HASHES = {
    "run.json": "7345c627c7ec66d95f1b261963336d6e86ae0671d11558f54a246f91b536dc6d",
    "decisions.json": "607585729d72be0e3bbaaaadabc74225b774b66540ea08f061d0d0459edcfa3d",
    "assessment.json": "0f6401ee435f5bb6c71a8c4172b3c1ea44eaca440637ebc1b1d68c48979e3fbb",
}
ASSIGNMENT_PROTOCOL = "docs/plans/optimal-key-identifiability-v1.md"
BASELINE_PROTOCOL = "docs/plans/visual-homophonic-pilot.md"
SECONDARY_PROTOCOL = "docs/plans/optimal-set-secondary-v1.md"
SECONDARY_PROTOCOL_SHA256 = (
    "17abf949562b5152c104b8fb8c6987079b22514d87bb93aa155236b2d8c6867c"
)
EXPECTED_REFERENCE_FINGERPRINT = (
    "05df3d40e478d73cebac63f282d17f897d013f8337111ab5533c2233d5eb6190"
)
EXPECTED_REFERENCE_TARGET = 370396722

CLASSIFICATIONS = (
    "forced_at_certified_optimum",
    "ambiguous",
    "unresolved",
)


def sha256_bytes(value: bytes) -> str:
    """Return the SHA-256 digest of bytes."""

    return hashlib.sha256(value).hexdigest()


def sha256_path(path: Path) -> str:
    """Return the SHA-256 digest of one file."""

    return sha256_bytes(Path(path).read_bytes())


def canonical_bytes(value: Any) -> bytes:
    """Encode one JSON value with the repository canonical form."""

    return (
        json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")


def canonical_hash(value: Any) -> str:
    """Return the SHA-256 digest of the canonical JSON form."""

    return sha256_bytes(canonical_bytes(value))


def write_new(path: Path, value: Any) -> str:
    """Write one canonical JSON artifact without replacing an existing file."""

    path = Path(path)
    with path.open("xb") as handle:
        handle.write(canonical_bytes(value))
    return sha256_path(path)


def _is_hash(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in string.hexdigits for character in value)
        and value == value.lower()
    )


def _validate_hash_map(value: object, field: str) -> dict[str, str]:
    if not isinstance(value, Mapping) or not value:
        raise ValueError(f"{field} must be a non-empty mapping of SHA-256 hashes")
    result: dict[str, str] = {}
    for path, digest in value.items():
        if not isinstance(path, str) or not path:
            raise ValueError(f"{field} keys must be non-empty strings")
        path_parts = PurePosixPath(path).parts
        if (
            PurePosixPath(path).is_absolute()
            or "\\" in path
            or any(part in ("", ".", "..") for part in path_parts)
        ):
            raise ValueError(f"{field} keys must be relative paths")
        if not _is_hash(digest):
            raise ValueError(f"{field}[{path!r}] is not a lower-case SHA-256 hash")
        result[path] = digest
    return dict(sorted(result.items()))


def _validate_provenance(provenance: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(provenance, Mapping):
        raise TypeError("provenance must be a mapping")
    result = dict(provenance)
    for field in ("source_hashes", "protocol_hashes"):
        result[field] = _validate_hash_map(result.get(field), f"provenance.{field}")
    for field in ("code_hashes", "data_hashes", "query_hashes", "pinned_artifacts"):
        if field in result:
            result[field] = _validate_hash_map(result[field], f"provenance.{field}")
    try:
        canonical_bytes(result)
    except (TypeError, ValueError) as exc:
        raise ValueError("provenance must contain JSON-serializable values") from exc
    return result


def _validate_capacity(capacity: Capacity) -> Capacity:
    if capacity is None:
        return None
    if isinstance(capacity, bool) or not isinstance(capacity, int):
        raise ValueError("capacity must be 1, 2, or None")
    if capacity not in (1, 2):
        raise ValueError("capacity must be 1, 2, or None")
    return capacity


def _validate_nonnegative(value: object, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{field} must be a non-negative integer")
    return value


def _normalise_units(values: Iterable[str] | None, field: str) -> tuple[str, ...]:
    if values is None:
        return ()
    if isinstance(values, str):
        raise TypeError(f"{field} must be an iterable of unit strings")
    try:
        result = tuple(values)
    except TypeError as exc:
        raise TypeError(f"{field} must be an iterable of unit strings") from exc
    if any(not isinstance(value, str) or not value for value in result):
        raise ValueError(f"{field} must contain non-empty strings")
    if len(set(result)) != len(result):
        raise ValueError(f"{field} must not contain duplicate units")
    return tuple(sorted(result))


def _normalise_partial_key(
    key: Mapping[str, str] | None,
    cipher_units: Iterable[str],
    alphabet: tuple[str, ...],
    capacity: Capacity,
    field: str,
) -> dict[str, str]:
    if key is None:
        return {}
    if not isinstance(key, Mapping):
        raise TypeError(f"{field} must be a mapping")
    symbols = set(cipher_units)
    alphabet_set = set(alphabet)
    result: dict[str, str] = {}
    for unit, letter in key.items():
        if not isinstance(unit, str) or not unit:
            raise ValueError(f"{field} keys must be non-empty strings")
        if unit not in symbols:
            raise ValueError(f"{field} contains a unit outside the primary input")
        if not isinstance(letter, str) or letter not in alphabet_set:
            raise ValueError(f"{field} values must be in plaintext_alphabet")
        result[unit] = letter
    if capacity is not None and any(
        count > capacity for count in Counter(result.values()).values()
    ):
        raise ValueError(f"{field} exceeds plaintext-letter capacity")
    return dict(sorted(result.items()))


def _normalise_baseline_key(
    key: Mapping[str, str],
    cipher_units: tuple[str, ...],
    alphabet: tuple[str, ...],
    capacity: Capacity,
) -> dict[str, str]:
    result = _normalise_partial_key(
        key, cipher_units, alphabet, capacity, "baseline_key"
    )
    if set(result) != set(cipher_units):
        raise ValueError("baseline_key must be total over the primary units")
    return result


def _word_payload(word: Word) -> str | list[str]:
    if isinstance(word, str):
        return word
    return list(word)


def _counts_payload(counts: Mapping[tuple[str, ...], int]) -> list[list[Any]]:
    return [
        [list(word), int(weight)]
        for word, weight in sorted(counts.items())
    ]


def _normalise_validation_counts(
    counts: Mapping[Word, int],
) -> dict[tuple[str, ...], int]:
    # The secondary scorer accepts the same token forms as the primary solver.
    return _normalise_cipher_counts(counts)


def validate_query_records(
    records: Iterable[Mapping[str, Any]],
    *,
    expected_units: Iterable[str],
    target: int,
    objective_domain_fingerprint: str,
    capacity: Capacity,
    plaintext_alphabet: Iterable[str] | str | None = None,
    expected_search_settings_fingerprint: str | None = None,
    expected_symbol_order: Iterable[str] | None = None,
    expected_node_budget: int | None = None,
    expected_bound_engine: str | None = None,
    require_exhausted_proof: bool = False,
    cipher_counts: Mapping[Word, int] | None = None,
    plaintext_lexicon: Iterable[Word] | None = None,
) -> dict[str, Any]:
    """Validate the published one-unit queries before using their exclusions."""

    expected = _normalise_units(expected_units, "expected_units")
    if not _is_hash(objective_domain_fingerprint):
        raise ValueError("objective_domain_fingerprint must be a SHA-256 hash")
    _validate_capacity(capacity)
    target = _validate_nonnegative(target, "target")
    alphabet = (
        set(_normalise_alphabet(plaintext_alphabet))
        if plaintext_alphabet is not None
        else None
    )
    fit_counts: dict[tuple[str, ...], int] | None = None
    fit_lexicon: set[tuple[str, ...]] | None = None
    if (cipher_counts is None) != (plaintext_lexicon is None):
        raise ValueError("cipher_counts and plaintext_lexicon must be supplied together")
    if cipher_counts is not None and plaintext_lexicon is not None:
        if alphabet is None:
            raise ValueError("plaintext_alphabet is required to score query witnesses")
        fit_counts = _normalise_cipher_counts(cipher_counts)
        fit_lexicon, _raw, _unique, _rejected = _normalise_lexicon(
            plaintext_lexicon, tuple(sorted(alphabet))
        )
        fit_units = {symbol for word in fit_counts for symbol in word}
        if fit_units != set(expected):
            raise ValueError("query witness fit units do not match expected units")
    symbol_order = (
        tuple(expected_symbol_order) if expected_symbol_order is not None else None
    )
    if symbol_order is not None:
        if any(not isinstance(unit, str) or not unit for unit in symbol_order):
            raise ValueError("expected_symbol_order must contain unit strings")
        if len(set(symbol_order)) != len(symbol_order):
            raise ValueError("expected_symbol_order must not contain duplicates")
        if set(symbol_order) != set(expected):
            raise ValueError("expected_symbol_order must cover the expected units")
    if expected_search_settings_fingerprint is not None and not _is_hash(
        expected_search_settings_fingerprint
    ):
        raise ValueError("expected_search_settings_fingerprint is malformed")
    if expected_node_budget is not None:
        _validate_nonnegative(expected_node_budget, "expected_node_budget")
    if expected_bound_engine is not None and (
        not isinstance(expected_bound_engine, str) or not expected_bound_engine
    ):
        raise ValueError("expected_bound_engine is malformed")
    if isinstance(records, (str, bytes)):
        raise TypeError("records must be an iterable of mappings")
    try:
        values = list(records)
    except TypeError as exc:
        raise TypeError("records must be an iterable of mappings") from exc
    if len(values) != len(expected):
        raise ValueError("published queries must cover every expected unit once")

    by_unit: dict[str, Mapping[str, Any]] = {}
    fixed: dict[str, str] = {}
    ambiguous: list[str] = []
    unresolved: list[str] = []
    for record in values:
        if not isinstance(record, Mapping):
            raise TypeError("each published query must be a mapping")
        unit = record.get("cipher_unit")
        if not isinstance(unit, str) or unit not in expected:
            raise ValueError("published query has an unexpected cipher unit")
        if unit in by_unit:
            raise ValueError("published queries contain a duplicate cipher unit")
        classification = record.get("classification")
        if classification not in CLASSIFICATIONS:
            raise ValueError("published query has an unknown classification")
        if record.get("objective_domain_fingerprint") != objective_domain_fingerprint:
            raise ValueError("published query objective fingerprint mismatch")
        raw = record.get("raw_query")
        if not isinstance(raw, Mapping):
            raise ValueError("published query has no raw query mapping")
        if "cipher_unit" in raw and raw["cipher_unit"] != unit:
            raise ValueError("published raw query cipher unit mismatch")
        for field in ("problem_fingerprint", "objective_domain_fingerprint"):
            if raw.get(field) != objective_domain_fingerprint:
                raise ValueError(f"published raw query {field} mismatch")
        raw_target = raw.get("query_target", raw.get("target"))
        if raw_target != target:
            raise ValueError("published raw query target mismatch")
        raw_capacity = raw.get("capacity")
        config = raw.get("config")
        if raw_capacity is None and isinstance(config, Mapping):
            raw_capacity = config.get("capacity")
        if raw_capacity != capacity:
            raise ValueError("published raw query capacity mismatch")
        if expected_search_settings_fingerprint is not None and raw.get(
            "search_settings_fingerprint"
        ) != expected_search_settings_fingerprint:
            raise ValueError("published query search settings mismatch")
        if symbol_order is not None and tuple(raw.get("symbol_order", ())) != symbol_order:
            raise ValueError("published query symbol order mismatch")
        if expected_node_budget is not None and raw.get("node_budget") != expected_node_budget:
            raise ValueError("published query node budget mismatch")
        if "node_budget" in raw and raw["node_budget"] is not None:
            _validate_nonnegative(raw["node_budget"], "published raw query node_budget")
        if require_exhausted_proof and "node_budget" not in raw:
            raise ValueError("published query has no node budget field")
        if expected_bound_engine is not None:
            if raw.get("bound_engine") != expected_bound_engine:
                raise ValueError("published query bound engine mismatch")
            if isinstance(config, Mapping) and config.get("bound_engine") != expected_bound_engine:
                raise ValueError("published query config bound engine mismatch")
        constraints = raw.get("constraints")
        if constraints != {}:
            raise ValueError("published query contains unapproved constraints")
        forbidden = record.get("forbidden")
        if not isinstance(forbidden, Mapping):
            raise ValueError("published query forbidden field must be a mapping")
        forbidden_copy = dict(forbidden)
        if raw.get("forbidden") != forbidden_copy:
            raise ValueError("published raw forbidden map mismatch")
        forbidden_units = set(forbidden_copy)
        if not forbidden_units.issubset({unit}):
            raise ValueError("published query forbids a different cipher unit")
        values_for_unit = forbidden_copy.get(unit, [])
        if not isinstance(values_for_unit, list):
            raise ValueError("published forbidden values must be lists")
        if set(forbidden_copy) != {unit} or len(values_for_unit) != 1:
            raise ValueError("every published query must forbid one letter for its unit")
        letter = values_for_unit[0]
        if not isinstance(letter, str) or not letter:
            raise ValueError("published forbidden letter is invalid")
        if alphabet is not None and letter not in alphabet:
            raise ValueError("published forbidden letter is outside the alphabet")
        if record.get("incumbent_letter", letter) != letter:
            raise ValueError("published incumbent letter does not match forbidden letter")
        if classification == "forced_at_certified_optimum":
            if raw.get("status") != "infeasible":
                raise ValueError("forced query is not infeasible")
            upper_bound = raw.get("upper_bound")
            if (
                isinstance(upper_bound, bool)
                or not isinstance(upper_bound, int)
                or upper_bound >= target
            ):
                raise ValueError("forced query upper bound does not exclude the target")
            if raw.get("search_exhausted") is not True:
                raise ValueError("forced query is not search-exhausted")
            if require_exhausted_proof and (
                raw.get("feasible") is not False
                or raw.get("infeasible") is not True
                or raw.get("proof_kind") != "search_exhausted_no_witness"
                or raw.get("key") is not None
                or raw.get("score") is not None
                or isinstance(raw.get("frontier_node_count"), bool)
                or not isinstance(raw.get("frontier_node_count"), int)
                or raw.get("frontier_node_count") != 0
            ):
                raise ValueError("forced query does not contain an exhausted no-witness proof")
            if require_exhausted_proof:
                lower_bound = raw.get("lower_bound")
                if (
                    isinstance(lower_bound, bool)
                    or not isinstance(lower_bound, int)
                    or lower_bound < 0
                    or lower_bound > upper_bound
                ):
                    raise ValueError("forced query bound certificate is malformed")
            fixed[unit] = values_for_unit[0]
        elif classification == "ambiguous":
            if raw.get("status") != "feasible" or raw.get("feasible") is not True:
                raise ValueError("ambiguous query does not contain a feasible witness")
            witness = raw.get("key")
            if not isinstance(witness, Mapping) or set(witness) != set(expected):
                raise ValueError("ambiguous query witness is not a total key")
            witness_values: dict[str, str] = {}
            for witness_unit, witness_letter in witness.items():
                if not isinstance(witness_unit, str) or not isinstance(witness_letter, str):
                    raise ValueError("ambiguous query witness symbols must be strings")
                if alphabet is not None and witness_letter not in alphabet:
                    raise ValueError("ambiguous query witness uses an unknown letter")
                witness_values[witness_unit] = witness_letter
            if witness_values[unit] == letter:
                raise ValueError("ambiguous witness does not satisfy the forbidden letter")
            if capacity is not None and any(
                count > capacity for count in Counter(witness_values.values()).values()
            ):
                raise ValueError("ambiguous query witness exceeds capacity")
            witness_score = raw.get("score")
            if (
                isinstance(witness_score, bool)
                or not isinstance(witness_score, int)
                or witness_score != target
            ):
                raise ValueError("ambiguous query witness does not attain the target")
            if fit_counts is not None and fit_lexicon is not None:
                if _score_weighted_key(fit_counts, witness_values, fit_lexicon) != target:
                    raise ValueError("ambiguous query witness fails the independent score check")
            ambiguous.append(unit)
        else:
            if raw.get("status") != "unknown":
                raise ValueError("unresolved query must have unknown raw status")
            unresolved.append(unit)
        by_unit[unit] = record

    if set(by_unit) != set(expected):
        raise ValueError("published queries do not cover the expected unit set")
    return {
        "records": [by_unit[unit] for unit in expected],
        "fixed_assignments": dict(sorted(fixed.items())),
        "ambiguous_units": tuple(sorted(ambiguous)),
        "unresolved_units": tuple(sorted(unresolved)),
        "classifications": {
            unit: by_unit[unit]["classification"] for unit in expected
        },
    }


def _validate_partition(
    cipher_units: tuple[str, ...],
    fixed_assignments: Mapping[str, str],
    ambiguous_units: tuple[str, ...],
    unresolved_units: tuple[str, ...],
) -> None:
    fixed_units = set(fixed_assignments)
    ambiguous = set(ambiguous_units)
    unresolved = set(unresolved_units)
    if fixed_units & ambiguous or fixed_units & unresolved or ambiguous & unresolved:
        raise ValueError("fixed, ambiguous, and unresolved units must be disjoint")
    if fixed_units | ambiguous | unresolved != set(cipher_units):
        raise ValueError(
            "fixed, ambiguous, and unresolved units must partition the primary units"
        )


def _model_settings(model: Any) -> dict[str, Any]:
    required = ("order", "add_alpha", "alphabet", "vocabulary")
    if any(not hasattr(model, field) for field in required):
        raise TypeError("model_builder did not return a language model")
    return {
        "order": model.order,
        "add_alpha": model.add_alpha,
        "alphabet": list(model.alphabet),
        "vocabulary_size": len(model.vocabulary),
        "start_symbol": getattr(model, "start_symbol", None),
        "end_symbol": getattr(model, "end_symbol", None),
        "unknown_symbol": getattr(model, "unknown_symbol", None),
    }


def _result_record(
    *,
    status: str,
    reason: str,
    input_sha256: str,
    enumeration_sha256: str,
    ranking_sha256: str | None,
    selection_sha256: str | None,
    settings: Mapping[str, Any],
    provenance: Mapping[str, Any],
    data_hashes: Mapping[str, str],
    baseline_incumbent: Mapping[str, str] | None = None,
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "kind": "optimal_set_secondary_result",
        "status": status,
        "reason": reason,
        "scope": "supplied fixed domain only",
        "claims_global_optimality": False,
        "claims_fixed_assignments_forced": False,
        "input_sha256": input_sha256,
        "enumeration_sha256": enumeration_sha256,
        "ranking_sha256": ranking_sha256,
        "selection_sha256": selection_sha256,
        "settings": dict(settings),
        "settings_sha256": canonical_hash(settings),
        "source_hashes": dict(provenance["source_hashes"]),
        "protocol_hashes": dict(provenance["protocol_hashes"]),
        "data_hashes": dict(data_hashes),
    }
    if baseline_incumbent is not None:
        result["baseline_incumbent"] = dict(baseline_incumbent)
    if "code_hashes" in provenance:
        result["code_hashes"] = dict(provenance["code_hashes"])
    if "pinned_artifacts" in provenance:
        result["pinned_artifacts"] = dict(provenance["pinned_artifacts"])
    if extra:
        result.update(dict(extra))
    return result


def _positive_fraction_record(value: object, field: str) -> Fraction:
    if not isinstance(value, Mapping):
        raise ValueError(f"{field} must be a fraction record")
    numerator_hex = value.get("numerator_hex")
    denominator_hex = value.get("denominator_hex")
    if (
        not isinstance(numerator_hex, str)
        or not re.fullmatch(r"0x[0-9a-f]+", numerator_hex)
        or not isinstance(denominator_hex, str)
        or not re.fullmatch(r"0x[0-9a-f]+", denominator_hex)
    ):
        raise ValueError(f"{field} contains a malformed hexadecimal fraction")
    numerator = int(numerator_hex, 16)
    denominator = int(denominator_hex, 16)
    if numerator <= 0 or denominator <= 0:
        raise ValueError(f"{field} must be positive")
    fraction = Fraction(numerator, denominator)
    if fraction.numerator != numerator or fraction.denominator != denominator:
        raise ValueError(f"{field} must use a reduced exact fraction")
    if "numerator_bits" in value and value["numerator_bits"] != numerator.bit_length():
        raise ValueError(f"{field} numerator bit count is incorrect")
    if "denominator_bits" in value and value["denominator_bits"] != denominator.bit_length():
        raise ValueError(f"{field} denominator bit count is incorrect")
    return fraction


def _validate_complete_ranking(
    ranking: Mapping[str, Any],
    candidate_maps: list[dict[str, str]],
    *,
    model: Any,
    capacity: Capacity,
    max_delta_events: int,
    max_ratio_bits: int,
) -> tuple[list[int], int, dict[str, str]]:
    """Validate exact candidate ratios and reconstruct all secondary ties."""

    if ranking.get("status") != "complete":
        raise ValueError("ranking is not complete")
    if ranking.get("candidate_count") != len(candidate_maps):
        raise ValueError("ranking candidate count does not match enumeration")
    config = ranking.get("config")
    if not isinstance(config, Mapping):
        raise ValueError("complete ranking has no configuration")
    expected_config = {
        "order": model.order,
        "add_alpha": model.add_alpha,
        "alphabet": list(model.alphabet),
        "vocabulary_size": len(model.vocabulary),
        "start_symbol": model.start_symbol,
        "end_symbol": model.end_symbol,
        "unknown_symbol": model.unknown_symbol,
        "capacity": capacity,
        "max_delta_events": max_delta_events,
        "max_ratio_bits": max_ratio_bits,
        "ratio_definition": RATIO_DEFINITION,
    }
    for field, expected in expected_config.items():
        if config.get(field) != expected:
            raise ValueError(f"ranking configuration field {field!r} does not match input")
    if ranking.get("claims_global_optimality") is not False:
        raise ValueError("secondary ranking makes a global optimality claim")
    if ranking.get("claims_candidate_set_complete") is not False:
        raise ValueError("secondary ranking makes an unscoped completeness claim")
    candidate_results = ranking.get("candidate_results")
    if not isinstance(candidate_results, list) or len(candidate_results) != len(candidate_maps):
        raise ValueError("ranking must contain one result for every candidate map")
    cipher_units = tuple(sorted(candidate_maps[0])) if candidate_maps else ()
    alphabet = tuple(model.alphabet)
    expected_canonical_index = min(
        range(len(candidate_maps)),
        key=lambda index: (
            tuple(candidate_maps[index][unit] for unit in cipher_units),
            index,
        ),
    )
    if ranking.get("canonical_candidate_index") != expected_canonical_index:
        raise ValueError("ranking canonical candidate does not use lexical order")
    ratios: list[Fraction] = []
    for index, candidate_result in enumerate(candidate_results):
        if not isinstance(candidate_result, Mapping):
            raise ValueError("ranking candidate result is not a mapping")
        if candidate_result.get("candidate_index") != index:
            raise ValueError("ranking candidate indices are missing or duplicated")
        key = _normalise_baseline_key(
            candidate_result.get("key"), cipher_units, alphabet, capacity
        )
        if key != candidate_maps[index]:
            raise ValueError("ranking candidate key does not match enumeration")
        ratios.append(
            _positive_fraction_record(
                candidate_result.get("likelihood_ratio"),
                f"candidate_results[{index}].likelihood_ratio",
            )
        )
    if ratios[expected_canonical_index] != Fraction(1, 1):
        raise ValueError("ranking canonical ratio is not exactly one")
    maximum = max(ratios)
    expected_indices = [index for index, ratio in enumerate(ratios) if ratio == maximum]
    supplied_indices = ranking.get("maximizer_indices")
    if supplied_indices != expected_indices:
        raise ValueError("ranking maximizer indices do not match exact ratios")
    supplied_maximum = _positive_fraction_record(
        ranking.get("maximum_likelihood_ratio"), "maximum_likelihood_ratio"
    )
    if supplied_maximum != maximum:
        raise ValueError("ranking maximum ratio does not match candidate ratios")
    expected_display_index = min(
        expected_indices,
        key=lambda index: (
            tuple(candidate_maps[index][unit] for unit in cipher_units),
            index,
        ),
    )
    if ranking.get("display_index") != expected_display_index:
        raise ValueError("ranking display index is not the lexical tie choice")
    display_key = _normalise_baseline_key(
        ranking.get("display_key"), cipher_units, alphabet, capacity
    )
    if display_key != candidate_maps[expected_display_index]:
        raise ValueError("ranking display key does not match display index")
    return expected_indices, expected_display_index, display_key


def run_study(
    *,
    output_dir: Path,
    primary_counts: Mapping[Word, int],
    training_words: Iterable[Word],
    validation_cipher_counts: Mapping[Word, int],
    baseline_key: Mapping[str, str],
    target: int,
    objective_domain_fingerprint: str,
    provenance: Mapping[str, Any],
    plaintext_alphabet: Iterable[str] | str = MODEL_ALPHABET,
    capacity: Capacity = 2,
    fixed_assignments: Mapping[str, str] | None = None,
    ambiguous_units: Iterable[str] | None = None,
    unresolved_units: Iterable[str] | None = None,
    query_records: Iterable[Mapping[str, Any]] | None = None,
    max_product: int | None = DEFAULT_MAX_PRODUCT,
    node_budget: int | None = DEFAULT_NODE_BUDGET,
    max_delta_events: int = DEFAULT_MAX_DELTA_EVENTS,
    max_ratio_bits: int = DEFAULT_MAX_RATIO_BITS,
    test_iterator: Callable[[Path], Iterable[Any]] | None = None,
    diagnostic_scorer: Callable[[Iterable[Any], Mapping[str, Any]], Mapping[str, Any]] | None = None,
    enumerator: Callable[..., Mapping[str, Any]] = enumerate_equal_score_completions,
    ranker: Callable[..., Mapping[str, Any]] = rank_secondary,
    model_builder: Callable[..., Any] = fit_language_model,
    settings: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Write a complete synthetic study or a clearly incomplete result."""

    output_dir = Path(output_dir)
    if output_dir.exists():
        raise FileExistsError("Select a new output directory.")
    capacity = _validate_capacity(capacity)
    max_product_value = (
        None if max_product is None else _validate_nonnegative(max_product, "max_product")
    )
    node_budget_value = (
        None if node_budget is None else _validate_nonnegative(node_budget, "node_budget")
    )
    max_delta_events = _validate_nonnegative(max_delta_events, "max_delta_events")
    max_ratio_bits = _validate_nonnegative(max_ratio_bits, "max_ratio_bits")
    if max_ratio_bits == 0:
        raise ValueError("max_ratio_bits must be positive")
    target = _validate_nonnegative(target, "target")
    alphabet = _normalise_alphabet(plaintext_alphabet)
    counts = _normalise_cipher_counts(primary_counts)
    validation_counts = _normalise_validation_counts(validation_cipher_counts)
    if set(symbol for word in counts for symbol in word) != set(
        symbol for word in validation_counts for symbol in word
    ):
        raise ValueError("validation ciphertext units must match primary units")
    raw_training_words = list(training_words) if not isinstance(training_words, str) else [training_words]
    (
        lexicon,
        lexicon_raw_count,
        lexicon_unique_count,
        lexicon_rejected_count,
    ) = _normalise_lexicon(raw_training_words, alphabet)
    cipher_units = tuple(sorted({symbol for word in counts for symbol in word}))
    fixed = _normalise_partial_key(
        fixed_assignments, cipher_units, alphabet, capacity, "fixed_assignments"
    )
    ambiguous = _normalise_units(ambiguous_units, "ambiguous_units")
    unresolved = _normalise_units(unresolved_units, "unresolved_units")
    query_values: list[Mapping[str, Any]] | None = None
    if query_records is not None:
        query_values = list(query_records)
        validated_queries = validate_query_records(
            query_values,
            expected_units=cipher_units,
            target=target,
            objective_domain_fingerprint=objective_domain_fingerprint,
            capacity=capacity,
            plaintext_alphabet=alphabet,
            require_exhausted_proof=True,
            cipher_counts=counts,
            plaintext_lexicon=lexicon,
        )
        query_fixed = validated_queries["fixed_assignments"]
        query_ambiguous = tuple(validated_queries["ambiguous_units"])
        query_unresolved = tuple(validated_queries["unresolved_units"])
        if fixed_assignments is not None and fixed != query_fixed:
            raise ValueError("fixed_assignments do not match published queries")
        if ambiguous_units is not None and ambiguous != query_ambiguous:
            raise ValueError("ambiguous_units do not match published queries")
        if unresolved_units is not None and unresolved != query_unresolved:
            raise ValueError("unresolved_units do not match published queries")
        fixed, ambiguous, unresolved = (
            query_fixed,
            query_ambiguous,
            query_unresolved,
        )
    elif fixed:
        raise ValueError(
            "fixed_assignments require published forced-query proof records"
        )
    _validate_partition(cipher_units, fixed, ambiguous, unresolved)
    if not _is_hash(objective_domain_fingerprint):
        raise ValueError("objective_domain_fingerprint must be a SHA-256 hash")
    calculated_fingerprint = _objective_domain_fingerprint(
        counts, lexicon, alphabet, capacity
    )
    if calculated_fingerprint != objective_domain_fingerprint:
        raise ValueError("objective_domain_fingerprint does not match normalized inputs")
    # This also checks the fixed map against the same capacity policy as the enumerator.
    fixed = _validate_fixed_key(fixed, cipher_units, alphabet, capacity)
    baseline = _normalise_baseline_key(
        baseline_key, cipher_units, alphabet, capacity
    )
    if any(baseline[unit] != letter for unit, letter in fixed.items()):
        raise ValueError("baseline_key disagrees with fixed_assignments")
    if query_values is not None:
        for query in validated_queries["records"]:
            unit = query["cipher_unit"]
            forbidden = query["forbidden"].get(unit)
            if query.get("incumbent_letter") != baseline[unit]:
                raise ValueError("published query incumbent does not match baseline_key")
            if forbidden != [baseline[unit]]:
                raise ValueError("published query does not forbid only baseline_key letter")
    checked_provenance = _validate_provenance(provenance)

    model = model_builder(
        raw_training_words,
        order=MODEL_ORDER,
        add_alpha=MODEL_ADD_ALPHA,
        alphabet=alphabet,
    )
    model_settings = _model_settings(model)
    if model_settings["order"] != MODEL_ORDER or model_settings["add_alpha"] != MODEL_ADD_ALPHA:
        raise ValueError("model_builder returned settings outside the frozen study")
    if tuple(model_settings["alphabet"]) != alphabet:
        raise ValueError("model_builder returned an unexpected alphabet")
    model_hash = canonical_hash(model.to_dict())
    data_hashes = {
        "primary_weights": canonical_hash(_counts_payload(counts)),
        "training_words": canonical_hash([_word_payload(word) for word in raw_training_words]),
        "training_lexicon": canonical_hash([list(word) for word in sorted(lexicon)]),
        "validation_cipher_counts": canonical_hash(_counts_payload(validation_counts)),
    }
    run_settings: dict[str, Any] = {
        "capacity": capacity,
        "max_product": max_product_value,
        "node_budget": node_budget_value,
        "max_delta_events": max_delta_events,
        "max_ratio_bits": max_ratio_bits,
        "model_order": MODEL_ORDER,
        "model_add_alpha": MODEL_ADD_ALPHA,
        "model_alphabet": list(alphabet),
    }
    if settings is not None:
        if not isinstance(settings, Mapping):
            raise TypeError("settings must be a mapping")
        for name, value in settings.items():
            if name in run_settings and run_settings[name] != value:
                raise ValueError(f"settings cannot override frozen field {name!r}")
            run_settings[name] = value
    # Validate settings before creating the output directory.
    canonical_bytes(run_settings)
    input_record: dict[str, Any] = {
        "kind": "optimal_set_secondary_study_input",
        "scope": "supplied fixed domain only",
        "primary": {
            "weighted_type_count": len(counts),
            "unit_count": len(cipher_units),
            "sha256": data_hashes["primary_weights"],
        },
        "training": {
            "raw_word_count": len(raw_training_words),
            "lexicon_type_count": len(lexicon),
            "raw_entry_count": lexicon_raw_count,
            "unique_entry_count": lexicon_unique_count,
            "rejected_out_of_alphabet_count": lexicon_rejected_count,
            "words_sha256": data_hashes["training_words"],
            "lexicon_sha256": data_hashes["training_lexicon"],
        },
        "validation": {
            "weighted_type_count": len(validation_counts),
            "sha256": data_hashes["validation_cipher_counts"],
        },
        "target": target,
        "objective_domain_fingerprint": objective_domain_fingerprint,
        "plaintext_alphabet": list(alphabet),
        "capacity": capacity,
        "fixed_assignments": dict(fixed),
        "ambiguous_units": list(ambiguous),
        "unresolved_units": list(unresolved),
        "baseline_incumbent": dict(baseline),
        "limits": {
            "max_product": max_product_value,
            "node_budget": node_budget_value,
            "max_delta_events": max_delta_events,
            "max_ratio_bits": max_ratio_bits,
        },
        "model_hash": model_hash,
        "model_settings": model_settings,
        "settings": run_settings,
        "settings_sha256": canonical_hash(run_settings),
        "data_hashes": data_hashes,
        "source_hashes": dict(checked_provenance["source_hashes"]),
        "protocol_hashes": dict(checked_provenance["protocol_hashes"]),
        "provenance": checked_provenance,
    }
    for field in ("code_hashes", "pinned_artifacts"):
        if field in checked_provenance:
            input_record[field] = dict(checked_provenance[field])
    if query_values is not None:
        input_record["query_record_count"] = len(query_values)
        if "query_hashes" in checked_provenance:
            input_record["query_hashes"] = dict(checked_provenance["query_hashes"])
    output_dir.mkdir(parents=True, exist_ok=False)
    input_sha256 = write_new(output_dir / "input.json", input_record)

    enumeration_raw = enumerator(
        counts,
        tuple(sorted(lexicon)),
        alphabet,
        capacity=capacity,
        fixed_key=fixed,
        target=target,
        max_product=max_product_value,
        node_budget=node_budget_value,
    )
    if not isinstance(enumeration_raw, Mapping):
        raise TypeError("enumerator must return a mapping")
    enumeration_record = dict(enumeration_raw)
    enumeration_status = enumeration_raw.get("status")
    raw_maps_for_metadata = enumeration_raw.get("collected_maps")
    if enumeration_status == "complete" and isinstance(raw_maps_for_metadata, list):
        map_payload: list[list[list[str]]] = []
        metadata_maps_valid = True
        for candidate in raw_maps_for_metadata:
            if not isinstance(candidate, Mapping):
                metadata_maps_valid = False
                break
            if any(
                not isinstance(unit, str) or not isinstance(letter, str)
                for unit, letter in candidate.items()
            ):
                metadata_maps_valid = False
                break
            map_payload.append(
                [[unit, candidate[unit]] for unit in sorted(candidate)]
            )
        if metadata_maps_valid:
            canonical_map_set = sorted(map_payload)
            enumeration_record.update(
                {
                    "retained_map_count": len(raw_maps_for_metadata),
                    "retained_map_set_sha256": canonical_hash(canonical_map_set),
                    "baseline_incumbent_present": any(
                        dict(candidate) == baseline for candidate in raw_maps_for_metadata
                    ),
                }
            )
    enumeration_record.update(
        {
            "input_sha256": input_sha256,
            "settings_sha256": canonical_hash(run_settings),
            "source_hashes": dict(checked_provenance["source_hashes"]),
            "protocol_hashes": dict(checked_provenance["protocol_hashes"]),
            "data_hashes": data_hashes,
            "model_hash": model_hash,
        }
    )
    enumeration_sha256 = write_new(output_dir / "enumeration.json", enumeration_record)
    if enumeration_status == "certificate_conflict":
        result = _result_record(
            status="contradiction",
            reason="certificate_conflict",
            input_sha256=input_sha256,
            enumeration_sha256=enumeration_sha256,
            ranking_sha256=None,
            selection_sha256=None,
            settings=run_settings,
            provenance=checked_provenance,
            data_hashes=data_hashes,
            baseline_incumbent=baseline,
            extra={"enumeration_status": enumeration_status},
        )
        write_new(output_dir / "result.json", result)
        return result
    if enumeration_status != "complete":
        reason = str(enumeration_raw.get("reason", "enumeration_not_complete"))
        result = _result_record(
            status="not_complete",
            reason=reason,
            input_sha256=input_sha256,
            enumeration_sha256=enumeration_sha256,
            ranking_sha256=None,
            selection_sha256=None,
            settings=run_settings,
            provenance=checked_provenance,
            data_hashes=data_hashes,
            baseline_incumbent=baseline,
            extra={"enumeration_status": enumeration_status},
        )
        write_new(output_dir / "result.json", result)
        return result

    expected_domain_fingerprint = _domain_fingerprint(
        counts, lexicon, alphabet, capacity, fixed
    )
    expected_free_units = tuple(unit for unit in cipher_units if unit not in fixed)
    expected_enumeration_fields = {
        "complete": True,
        "truncation": False,
        "target": target,
        "capacity": capacity,
        "objective_domain_fingerprint": objective_domain_fingerprint,
        "domain_fingerprint": expected_domain_fingerprint,
        "fixed_assignments": dict(fixed),
        "full_alphabet": list(alphabet),
        "cipher_units": list(cipher_units),
        "free_units": list(expected_free_units),
        "product_bound": len(alphabet) ** len(expected_free_units),
        "max_product": max_product_value,
        "node_budget": node_budget_value,
        "scope": "all feasible completions of the supplied fixed domain",
        "claims_global_optimum": False,
        "claims_fixed_assignments_forced": False,
    }
    for field, expected in expected_enumeration_fields.items():
        actual = enumeration_raw.get(field)
        if field in ("complete", "truncation"):
            matches = actual is expected
        else:
            matches = actual == expected
        if not matches:
            raise ValueError(f"complete enumeration field {field!r} does not match input")

    raw_maps = enumeration_raw.get("collected_maps")
    if not isinstance(raw_maps, list):
        raise ValueError("complete enumeration did not return collected_maps")
    candidate_maps: list[dict[str, str]] = []
    seen_candidates: set[tuple[tuple[str, str], ...]] = set()
    for candidate in raw_maps:
        normalized_candidate = _normalise_baseline_key(
            candidate, cipher_units, alphabet, capacity
        )
        candidate_fingerprint = tuple(normalized_candidate.items())
        if candidate_fingerprint in seen_candidates:
            raise ValueError("complete enumeration returned duplicate maps")
        seen_candidates.add(candidate_fingerprint)
        if any(normalized_candidate[unit] != fixed[unit] for unit in fixed):
            raise ValueError("enumeration map disagrees with fixed assignments")
        candidate_maps.append(normalized_candidate)
    candidate_scores = [
        _score_weighted_key(counts, candidate, lexicon)
        for candidate in candidate_maps
    ]
    above_target = [index for index, score in enumerate(candidate_scores) if score > target]
    if above_target:
        result = _result_record(
            status="contradiction",
            reason="certificate_conflict",
            input_sha256=input_sha256,
            enumeration_sha256=enumeration_sha256,
            ranking_sha256=None,
            selection_sha256=None,
            settings=run_settings,
            provenance=checked_provenance,
            data_hashes=data_hashes,
            baseline_incumbent=baseline,
            extra={
                "enumeration_status": enumeration_status,
                "conflict_candidate_indices": above_target,
                "conflict_scores": {
                    str(index): candidate_scores[index] for index in above_target
                },
            },
        )
        write_new(output_dir / "result.json", result)
        return result
    if any(score != target for score in candidate_scores):
        raise ValueError("complete enumeration returned a map below the target")
    if not candidate_maps:
        result = _result_record(
            status="contradiction",
            reason="empty_primary_optimal_set",
            input_sha256=input_sha256,
            enumeration_sha256=enumeration_sha256,
            ranking_sha256=None,
            selection_sha256=None,
            settings=run_settings,
            provenance=checked_provenance,
            data_hashes=data_hashes,
            baseline_incumbent=baseline,
            extra={"enumeration_status": enumeration_status},
        )
        write_new(output_dir / "result.json", result)
        return result
    try:
        baseline_index = candidate_maps.index(baseline)
    except ValueError:
        result = _result_record(
            status="contradiction",
            reason="baseline_incumbent_missing",
            input_sha256=input_sha256,
            enumeration_sha256=enumeration_sha256,
            ranking_sha256=None,
            selection_sha256=None,
            settings=run_settings,
            provenance=checked_provenance,
            data_hashes=data_hashes,
            baseline_incumbent=baseline,
            extra={"enumeration_status": enumeration_status},
        )
        write_new(output_dir / "result.json", result)
        return result

    candidate_set_payload = sorted(
        [
            [[unit, candidate[unit]] for unit in sorted(candidate)]
            for candidate in candidate_maps
        ]
    )
    candidate_set_sha256 = canonical_hash(candidate_set_payload)

    ranking_raw = ranker(
        model,
        validation_counts,
        candidate_maps,
        capacity=capacity,
        max_delta_events=max_delta_events,
        max_ratio_bits=max_ratio_bits,
    )
    if not isinstance(ranking_raw, Mapping):
        raise TypeError("ranker must return a mapping")
    ranking_record = dict(ranking_raw)
    ranking_record.update(
        {
            "input_sha256": input_sha256,
            "enumeration_sha256": enumeration_sha256,
            "settings_sha256": canonical_hash(run_settings),
            "source_hashes": dict(checked_provenance["source_hashes"]),
            "protocol_hashes": dict(checked_provenance["protocol_hashes"]),
            "data_hashes": data_hashes,
            "model_hash": model_hash,
            "model_settings": model_settings,
            "input_candidate_count": len(candidate_maps),
            "candidate_set_sha256": candidate_set_sha256,
            "baseline_index": baseline_index,
        }
    )
    ranking_sha256 = write_new(output_dir / "ranking.json", ranking_record)
    ranking_status = ranking_raw.get("status")
    if ranking_status != "complete":
        reason = str(ranking_raw.get("reason", "ranking_not_complete"))
        result = _result_record(
            status="not_complete",
            reason=reason,
            input_sha256=input_sha256,
            enumeration_sha256=enumeration_sha256,
            ranking_sha256=ranking_sha256,
            selection_sha256=None,
            settings=run_settings,
            provenance=checked_provenance,
            data_hashes=data_hashes,
            baseline_incumbent=baseline,
            extra={"enumeration_status": enumeration_status},
        )
        write_new(output_dir / "result.json", result)
        return result

    indices, display_index, display_key = _validate_complete_ranking(
        ranking_raw,
        candidate_maps,
        model=model,
        capacity=capacity,
        max_delta_events=max_delta_events,
        max_ratio_bits=max_ratio_bits,
    )
    selection: dict[str, Any] = {
        "kind": "optimal_set_secondary_selection",
        "status": "complete",
        "scope": "all supplied primary-optimal maps",
        "candidate_count": len(candidate_maps),
        "candidate_set_sha256": candidate_set_sha256,
        "primary_target": target,
        "baseline_index": baseline_index,
        "baseline_incumbent": dict(baseline),
        "maximizer_indices": indices,
        "maximizer_count": len(indices),
        "maximizer_maps": [dict(candidate_maps[index]) for index in indices],
        "all_primary_optimal_maps": [dict(candidate) for candidate in candidate_maps],
        "display_index": display_index,
        "display_key": display_key,
        "input_sha256": input_sha256,
        "enumeration_sha256": enumeration_sha256,
        "ranking_sha256": ranking_sha256,
        "model_hash": model_hash,
        "source_hashes": dict(checked_provenance["source_hashes"]),
        "protocol_hashes": dict(checked_provenance["protocol_hashes"]),
        "data_hashes": data_hashes,
        "settings": run_settings,
        "settings_sha256": canonical_hash(run_settings),
        "claims_global_optimality": False,
        "claims_fixed_assignments_forced": False,
    }
    selection_sha256 = write_new(output_dir / "selection.json", selection)

    diagnostics: Mapping[str, Any] = {}
    if test_iterator is not None:
        if not (output_dir / "selection.json").exists():
            raise AssertionError("test iterator was opened before selection.json")
        test_items = test_iterator(output_dir / "selection.json")
        if diagnostic_scorer is None:
            diagnostics = {"test_items_consumed": sum(1 for _ in test_items)}
        else:
            diagnostics = diagnostic_scorer(test_items, selection)
            if not isinstance(diagnostics, Mapping):
                raise TypeError("diagnostic_scorer must return a mapping")
    elif diagnostic_scorer is not None:
        raise ValueError("diagnostic_scorer requires test_iterator")

    result = _result_record(
        status="complete",
        reason="primary_optimal_set_ranked",
        input_sha256=input_sha256,
        enumeration_sha256=enumeration_sha256,
        ranking_sha256=ranking_sha256,
        selection_sha256=selection_sha256,
        settings=run_settings,
        provenance=checked_provenance,
        data_hashes=data_hashes,
        baseline_incumbent=baseline,
        extra={
            "enumeration_status": enumeration_status,
            "ranking_status": ranking_status,
            "primary_optimal_set_complete_within_domain": True,
            "candidate_count": len(candidate_maps),
            "candidate_set_sha256": candidate_set_sha256,
            "model_hash": model_hash,
            "maximizer_indices": indices,
            "diagnostics": dict(diagnostics),
            "selection": selection,
        },
    )
    write_new(output_dir / "result.json", result)
    return result


def _verify_expected_file(root: Path, relative: str, expected: str) -> None:
    path = root / relative
    if not path.is_file():
        raise ValueError(f"required provenance file is missing: {relative}")
    actual = sha256_path(path)
    if actual != expected:
        raise ValueError(f"provenance hash mismatch: {relative}")


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_bytes())
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid JSON artifact: {path}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"JSON artifact is not an object: {path}")
    return value


def _score_weighted_key(
    counts: Mapping[tuple[str, ...], int],
    key: Mapping[str, str],
    lexicon: set[tuple[str, ...]],
) -> int:
    return sum(
        weight
        for word, weight in counts.items()
        if tuple(key[unit] for unit in word) in lexicon
    )


def _candidate_test_diagnostics(
    candidate_index: int,
    candidate: Mapping[str, str],
    rows: Iterable[tuple[tuple[str, ...], str]],
    planted_key: Mapping[str, str],
    secondary_maximizer: bool,
) -> dict[str, Any]:
    """Measure test positions for one key, including units absent from that key."""

    rows = tuple(rows)
    observed_units = set(planted_key)
    known_units = set(candidate)
    key_positions = sum(
        candidate.get(unit) == planted_key.get(unit) for unit in known_units
    )
    total_positions = correct_positions = word_correct = 0
    observed_positions = observed_correct = 0
    unseen_positions = 0
    unseen_units: set[str] = set()
    for cipher_word, plain_word in rows:
        decoded: list[str] = []
        complete = True
        for unit, letter in zip(cipher_word, plain_word, strict=True):
            total_positions += 1
            if unit not in candidate:
                unseen_positions += 1
                unseen_units.add(unit)
                complete = False
                continue
            decoded.append(candidate[unit])
            observed_positions += 1
            is_correct = candidate[unit] == letter
            observed_correct += is_correct
            correct_positions += is_correct
        if complete and "".join(decoded) == plain_word:
            word_correct += 1
    return {
        "candidate_index": candidate_index,
        "secondary_maximizer": secondary_maximizer,
        "observed_key_units": len(known_units & observed_units),
        "key_positions": len(known_units),
        "key_correct": key_positions,
        "test_observed_positions": observed_positions,
        "test_observed_correct": observed_correct,
        "test_positions": total_positions,
        "test_correct": correct_positions,
        "test_errors": total_positions - correct_positions,
        "test_unseen_positions": unseen_positions,
        "test_unseen_units": sorted(unseen_units),
        "test_word_count": len(rows),
        "test_word_correct": word_correct,
    }


def _reference_source_hashes(root: Path, manifest: Mapping[str, Any]) -> dict[str, str]:
    paths: dict[str, str] = {REFERENCE_MANIFEST: sha256_path(root / REFERENCE_MANIFEST)}
    raw_dir = manifest.get("raw_output_dir")
    if not isinstance(raw_dir, str):
        raise ValueError("reference manifest raw_output_dir is invalid")
    for corpus in manifest.get("corpora", []):
        if not isinstance(corpus, Mapping):
            raise ValueError("reference manifest corpus entry is invalid")
        corpus_id = corpus.get("id")
        if not isinstance(corpus_id, str):
            raise ValueError("reference manifest corpus id is invalid")
        for entry in corpus.get("files", []):
            if not isinstance(entry, Mapping) or not isinstance(entry.get("name"), str):
                raise ValueError("reference manifest source entry is invalid")
            if entry.get("role") not in ("conllu", "readme", "license"):
                continue
            relative = f"{raw_dir}/{corpus_id}/{entry['name']}"
            expected = entry.get("sha256")
            if not _is_hash(expected):
                raise ValueError(f"reference manifest has an invalid hash: {relative}")
            _verify_expected_file(root, relative, expected)
            paths[relative] = expected
    return dict(sorted(paths.items()))


def _verify_reference_bundle(root: Path) -> dict[str, Any]:
    """Validate the pinned baseline and the 46 published query records."""

    root = Path(root)
    _verify_expected_file(root, REFERENCE_MANIFEST, REFERENCE_MANIFEST_SHA256)
    manifest = _load_json(root / REFERENCE_MANIFEST)
    source_hashes = _reference_source_hashes(root, manifest)
    _verify_expected_file(root, BASELINE_REPORT, BASELINE_REPORT_SHA256)
    baseline_report = _load_json(root / BASELINE_REPORT)
    baseline_key = _load_json(root / BASELINE_KEY)
    baseline_key_hash = sha256_path(root / BASELINE_KEY)
    if baseline_key_hash != baseline_report.get("key_record_sha256"):
        raise ValueError("baseline key record hash does not match its report")
    if baseline_report.get("kind") != "synthetic_reference_control":
        raise ValueError("baseline is not a synthetic reference control")
    if baseline_report.get("family") != "cap2" or baseline_report.get("seed") != 7000:
        raise ValueError("baseline control does not match the fixed study")
    solver = baseline_report.get("solver")
    if not isinstance(solver, Mapping):
        raise ValueError("baseline solver record is missing")
    target = solver.get("score")
    if target != EXPECTED_REFERENCE_TARGET:
        raise ValueError("baseline target does not match the fixed study")
    if (
        solver.get("score_certified") is not True
        or solver.get("lower_bound") != target
        or solver.get("upper_bound") != target
        or solver.get("config", {}).get("capacity") != 2
        or solver.get("feasible") is not True
        or solver.get("status") != "bound_certified"
    ):
        raise ValueError("baseline does not carry the required score certificate")
    for relative, expected in baseline_report.get("code_sha256", {}).items():
        if not isinstance(relative, str) or not _is_hash(expected):
            raise ValueError("baseline code provenance is malformed")
        _verify_expected_file(root, relative, expected)
        source_hashes[relative] = expected
    baseline_protocol_hash = baseline_report.get("protocol_sha256")
    if not _is_hash(baseline_protocol_hash):
        raise ValueError("baseline protocol provenance is malformed")
    _verify_expected_file(root, BASELINE_PROTOCOL, baseline_protocol_hash)
    protocol_hashes = {
        BASELINE_PROTOCOL: baseline_protocol_hash,
        ASSIGNMENT_PROTOCOL: "",
        SECONDARY_PROTOCOL: "",
    }

    assignment: dict[str, dict[str, Any]] = {}
    for name, expected in ASSIGNMENT_HASHES.items():
        relative = f"{ASSIGNMENT_DIR}/{name}"
        _verify_expected_file(root, relative, expected)
        assignment[name] = _load_json(root / relative)
        source_hashes[relative] = expected
    run_record = assignment["run.json"]
    decisions = assignment["decisions.json"]
    assessment = assignment["assessment.json"]
    for record in (run_record, assessment):
        if (
            record.get("family") != "cap2"
            or record.get("seed") != 7000
            or record.get("target") != target
            or record.get("problem_fingerprint") != EXPECTED_REFERENCE_FINGERPRINT
        ):
            raise ValueError("assignment provenance does not match the fixed study")
    if (
        decisions.get("target") != target
        or decisions.get("problem_fingerprint") != EXPECTED_REFERENCE_FINGERPRINT
    ):
        raise ValueError("assignment decisions do not match the fixed study")
    if run_record.get("incumbent_key") != baseline_key.get("key"):
        raise ValueError("assignment run does not bind the baseline incumbent")
    if assessment.get("incumbent_key") != baseline_key.get("key"):
        raise ValueError("assignment assessment does not bind the baseline incumbent")
    if assessment.get("decisions_sha256") != ASSIGNMENT_HASHES["decisions.json"]:
        raise ValueError("assessment does not bind the published decisions")
    for record in (run_record, assessment):
        provenance = record.get("provenance")
        if not isinstance(provenance, Mapping):
            raise ValueError("assignment provenance is missing")
        for relative, expected in provenance.get("code_sha256", {}).items():
            if not isinstance(relative, str) or not _is_hash(expected):
                raise ValueError("assignment code provenance is malformed")
            _verify_expected_file(root, relative, expected)
            source_hashes[relative] = expected
        expected_protocol = provenance.get("protocol_sha256")
        if not _is_hash(expected_protocol):
            raise ValueError("assignment protocol provenance is malformed")
        _verify_expected_file(root, ASSIGNMENT_PROTOCOL, expected_protocol)
        protocol_hashes[ASSIGNMENT_PROTOCOL] = expected_protocol

    query_hashes = decisions.get("query_sha256")
    if not isinstance(query_hashes, Mapping) or len(query_hashes) != 46:
        raise ValueError("assignment decisions must bind 46 query records")
    query_records: list[dict[str, Any]] = []
    for filename, expected in sorted(query_hashes.items()):
        if not isinstance(filename, str) or not filename.endswith(".json"):
            raise ValueError("assignment query filename is malformed")
        if not _is_hash(expected):
            raise ValueError("assignment query hash is malformed")
        relative = f"{ASSIGNMENT_DIR}/{filename}"
        _verify_expected_file(root, relative, expected)
        query = _load_json(root / relative)
        stem = filename[:-5]
        if query.get("cipher_unit") != stem:
            raise ValueError("assignment query filename does not match its unit")
        query_records.append(query)
        source_hashes[relative] = expected
    validated_queries = validate_query_records(
        query_records,
        expected_units=[record["cipher_unit"] for record in query_records],
        target=target,
        objective_domain_fingerprint=EXPECTED_REFERENCE_FINGERPRINT,
        capacity=2,
        plaintext_alphabet=MODEL_ALPHABET,
        expected_search_settings_fingerprint=run_record.get(
            "search_settings_fingerprint"
        ),
        expected_symbol_order=run_record.get("symbol_order"),
        expected_node_budget=run_record.get("node_budget_per_query"),
        expected_bound_engine="BitsetBound",
        require_exhausted_proof=True,
    )
    if (
        len(validated_queries["fixed_assignments"]) != 45
        or len(validated_queries["ambiguous_units"]) != 1
        or validated_queries["unresolved_units"]
    ):
        raise ValueError("published assignment classifications are not 45 forced and 1 ambiguous")
    if decisions.get("counts") != {
        "ambiguous": 1,
        "forced_at_certified_optimum": 45,
    }:
        raise ValueError("assignment classification counts do not match the protocol")
    query_hashes_sorted = {str(name): str(value) for name, value in sorted(query_hashes.items())}

    _verify_expected_file(root, SECONDARY_PROTOCOL, SECONDARY_PROTOCOL_SHA256)
    protocol_hashes[SECONDARY_PROTOCOL] = SECONDARY_PROTOCOL_SHA256
    protocol_hashes = dict(sorted(protocol_hashes.items()))
    partitions = load_reference_partitions(root)["latin_llct"]
    words = partitions["words"]
    train = list(words["train"])
    validation = list(words["validation"])
    test = list(words["test"])
    planted = seeded_control_key("cap2", 7000)
    cipher_train = encrypt_words(train, planted)
    cipher_validation = encrypt_words(validation, planted)
    cipher_test = encrypt_words(test, planted)
    expected_streams = {
        "plaintext_train": train,
        "plaintext_validation": validation,
        "plaintext_test": test,
        "cipher_train": cipher_train,
        "cipher_validation": cipher_validation,
        "cipher_test": cipher_test,
    }
    stream_hashes = baseline_report.get("stream_sha256")
    if not isinstance(stream_hashes, Mapping):
        raise ValueError("baseline stream hashes are missing")
    for name, stream in expected_streams.items():
        if canonical_hash(stream) != stream_hashes.get(name):
            raise ValueError(f"baseline stream mismatch: {name}")
    lexicon_strings = set(train)
    if canonical_hash(sorted(lexicon_strings)) != baseline_report.get("train_lexicon", {}).get("sha256"):
        raise ValueError("baseline lexicon hash mismatch")
    lexicon = {tuple(word) for word in lexicon_strings}
    counts = Counter(cipher_validation)
    weights, token_count, type_count, denominator = objective_weights(counts)
    fit_input = baseline_report.get("fit_input")
    expected_fit = {
        "sha256": canonical_hash(cipher_validation),
        "token_count": token_count,
        "type_count": type_count,
        "unit_count": len({unit for word in counts for unit in word}),
    }
    if fit_input != expected_fit:
        raise ValueError("baseline fit input mismatch")
    objective = baseline_report.get("objective")
    if not isinstance(objective, Mapping):
        raise ValueError("baseline objective record is missing")
    if (
        objective.get("denominator") != denominator
        or objective.get("N_token_count") != token_count
        or objective.get("T_type_count") != type_count
        or objective.get("weights_total") != denominator
        or objective.get("weights_match_denominator") is not True
        or objective.get("weight_formula") != "count*T+N"
        or objective.get("normalization_formula") != "2*T*N"
        or solver.get("total_weight") != denominator
        or objective.get("score_from_key") != target
    ):
        raise ValueError("baseline objective denominator mismatch")
    validated_queries = validate_query_records(
        query_records,
        expected_units=[record["cipher_unit"] for record in query_records],
        target=target,
        objective_domain_fingerprint=EXPECTED_REFERENCE_FINGERPRINT,
        capacity=2,
        plaintext_alphabet=MODEL_ALPHABET,
        expected_search_settings_fingerprint=run_record.get(
            "search_settings_fingerprint"
        ),
        expected_symbol_order=run_record.get("symbol_order"),
        expected_node_budget=run_record.get("node_budget_per_query"),
        expected_bound_engine="BitsetBound",
        require_exhausted_proof=True,
        cipher_counts=weights,
        plaintext_lexicon=lexicon_strings,
    )
    baseline_map = baseline_key.get("key")
    if not isinstance(baseline_map, Mapping):
        raise ValueError("baseline key record has no key mapping")
    baseline_map = _normalise_baseline_key(
        baseline_map,
        tuple(sorted({unit for word in counts for unit in word})),
        MODEL_ALPHABET,
        2,
    )
    for query in validated_queries["records"]:
        unit = query["cipher_unit"]
        forbidden = query["forbidden"].get(unit, [])
        if query.get("incumbent_letter") != baseline_map[unit]:
            raise ValueError("assignment query incumbent does not match the baseline")
        if forbidden != [baseline_map[unit]]:
            raise ValueError("assignment query does not forbid only the baseline letter")
    if _score_weighted_key(weights, baseline_map, lexicon) != target:
        raise ValueError("baseline incumbent does not attain the target")
    objective_fingerprint = _objective_domain_fingerprint(
        weights,
        lexicon,
        MODEL_ALPHABET,
        2,
    )
    if objective_fingerprint != EXPECTED_REFERENCE_FINGERPRINT:
        raise ValueError("reconstructed objective fingerprint mismatch")
    data_hashes = {
        "reference_manifest": REFERENCE_MANIFEST_SHA256,
        "plaintext_train": canonical_hash(train),
        "plaintext_validation": canonical_hash(validation),
        "cipher_train": canonical_hash(cipher_train),
        "cipher_validation": canonical_hash(cipher_validation),
        "train_lexicon": canonical_hash(sorted(lexicon_strings)),
    }
    baseline_config = solver.get("config")
    bound_metadata = solver.get("bound_metadata")
    if not isinstance(baseline_config, Mapping) or not isinstance(bound_metadata, Mapping):
        raise ValueError("baseline value certificate metadata is missing")
    bound_engine = baseline_config.get("bound_engine")
    if not isinstance(bound_engine, str) or not bound_engine:
        raise ValueError("baseline bound engine is missing")
    value_certificate = {
        "score": target,
        "lower_bound": solver.get("lower_bound"),
        "upper_bound": solver.get("upper_bound"),
        "score_certified": solver.get("score_certified"),
        "search_exhausted": solver.get("search_exhausted"),
        "frontier_node_count": solver.get("frontier_node_count"),
        "bound_engine": bound_engine,
        "bound_metadata": dict(bound_metadata),
        "baseline_report_sha256": BASELINE_REPORT_SHA256,
        "key_record_sha256": baseline_key_hash,
    }
    canonical_bytes(value_certificate)
    code_hashes: dict[str, str] = {}
    for record in (baseline_report, run_record, assessment):
        code_map = record.get("code_sha256") or record.get("provenance", {}).get("code_sha256", {})
        if isinstance(code_map, Mapping):
            for relative, digest in code_map.items():
                if isinstance(relative, str) and isinstance(digest, str):
                    code_hashes[relative] = digest
    for relative in (
        "experiments/optimal_set/enumerate.py",
        "experiments/optimal_set/secondary.py",
        "experiments/optimal_set/run_study.py",
    ):
        digest = sha256_path(root / relative)
        source_hashes[relative] = digest
        code_hashes[relative] = digest
    source_hashes = dict(sorted(source_hashes.items()))
    provenance = {
        "source_hashes": dict(sorted(source_hashes.items())),
        "protocol_hashes": protocol_hashes,
        "code_hashes": dict(sorted(code_hashes.items())),
        "query_hashes": query_hashes_sorted,
        "pinned_artifacts": {
            BASELINE_REPORT: BASELINE_REPORT_SHA256,
            BASELINE_KEY: baseline_key_hash,
            f"{ASSIGNMENT_DIR}/run.json": ASSIGNMENT_HASHES["run.json"],
            f"{ASSIGNMENT_DIR}/decisions.json": ASSIGNMENT_HASHES["decisions.json"],
            f"{ASSIGNMENT_DIR}/assessment.json": ASSIGNMENT_HASHES["assessment.json"],
        },
        "data_hashes": data_hashes,
        "baseline_report_sha256": BASELINE_REPORT_SHA256,
        "baseline_key_sha256": sha256_path(root / BASELINE_KEY),
        "assignment_run_sha256": ASSIGNMENT_HASHES["run.json"],
        "assignment_decisions_sha256": ASSIGNMENT_HASHES["decisions.json"],
        "assignment_assessment_sha256": ASSIGNMENT_HASHES["assessment.json"],
        "value_certificate": value_certificate,
    }

    def guarded_test_iterator(selection_path: Path) -> Iterable[tuple[tuple[str, ...], str]]:
        if not Path(selection_path).is_file():
            raise AssertionError("test iterator opened before selection.json")
        return tuple(zip(cipher_test, test, strict=True))

    def diagnostics(
        items: Iterable[tuple[tuple[str, ...], str]], selection: Mapping[str, Any]
    ) -> Mapping[str, Any]:
        rows = tuple(items)
        maps = selection.get("all_primary_optimal_maps")
        if not isinstance(maps, list):
            raise ValueError("selection does not contain primary maps")
        maximizers = set(selection.get("maximizer_indices", []))
        candidate_rows: list[dict[str, Any]] = []
        for index, candidate in enumerate(maps):
            if not isinstance(candidate, Mapping):
                raise ValueError("selection contains an invalid map")
            candidate_rows.append(
                _candidate_test_diagnostics(
                    index,
                    candidate,
                    rows,
                    planted["cipher_to_plain"],
                    index in maximizers,
                )
            )
        return {
            "candidate_count": len(candidate_rows),
            "secondary_maximizer_indices": sorted(maximizers),
            "test_token_count": len(rows),
            "test_stream_sha256": {
                "plaintext_test": canonical_hash(test),
                "cipher_test": canonical_hash(cipher_test),
            },
            "candidate_diagnostics": candidate_rows,
            "uses_planted_key_for_diagnostics_only": True,
        }

    return {
        "primary_counts": weights,
        "training_words": train,
        "validation_cipher_counts": counts,
        "baseline_key": baseline_map,
        "target": target,
        "objective_domain_fingerprint": objective_fingerprint,
        "provenance": provenance,
        "plaintext_alphabet": MODEL_ALPHABET,
        "capacity": 2,
        "fixed_assignments": validated_queries["fixed_assignments"],
        "ambiguous_units": validated_queries["ambiguous_units"],
        "unresolved_units": validated_queries["unresolved_units"],
        "query_records": validated_queries["records"],
        "test_iterator": guarded_test_iterator,
        "diagnostic_scorer": diagnostics,
        "max_product": DEFAULT_MAX_PRODUCT,
        "node_budget": DEFAULT_NODE_BUDGET,
        "max_delta_events": DEFAULT_MAX_DELTA_EVENTS,
        "max_ratio_bits": DEFAULT_MAX_RATIO_BITS,
    }


def load_reference_inputs(root: Path = ROOT) -> dict[str, Any]:
    """Validate pinned Latin inputs and return lazy runner arguments."""

    return _verify_reference_bundle(Path(root))


def main(argv: Sequence[str] | None = None) -> dict[str, Any]:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    inputs = load_reference_inputs(ROOT)
    return run_study(output_dir=args.output_dir, **inputs)


__all__ = [
    "BASELINE_REPORT",
    "BASELINE_REPORT_SHA256",
    "SECONDARY_PROTOCOL_SHA256",
    "canonical_bytes",
    "canonical_hash",
    "load_reference_inputs",
    "main",
    "run_study",
    "sha256_path",
    "validate_query_records",
    "write_new",
]


if __name__ == "__main__":
    main()
