"""Pure ciphertext-only cyclic quotient study core.

The core accepts a declared unit inventory, validation ciphertext words, and a
training lexicon. It proves an observed quotient before fitting any letters.
It has no test input, planted key, corpus loader, or manuscript access.
"""

from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
import string
from typing import Any, Iterable, Mapping, Sequence

from experiments.cyclic_pairing.pairing import Compatibility, build_compatibility
from experiments.cyclic_quotient.quotient import (
    QuotientResult,
    build_observed_quotient,
)
from experiments.homophonic.solver import solve_lexicon
from experiments.lexicon.run_pilot import (
    ALPHABET,
    branch_symbol_order,
    objective_weights,
)


PROTOCOL = "cyclic-quotient-recovery-v1"
QUOTIENT_NODE_BUDGET = 100_000
SOLVER_NODE_BUDGET = 100_000
BOUND_ENGINE = "bitset"
CAPACITY = 1
QUOTIENT_FILENAME = "quotient.json"
FIT_FILENAME = "fit.json"
KEY_FILENAME = "fit.keys.json"


def _canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _canonical_hash(value: Any) -> str:
    return _sha256(_canonical_bytes(value))


def _write_exclusive(path: Path, value: Any) -> str:
    data = _canonical_bytes(value)
    with path.open("xb") as handle:
        handle.write(data)
    return _sha256(data)


def _normalise_units(values: Iterable[str]) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)):
        raise ValueError("declared_units must be a sequence of unit strings")
    units = tuple(values)
    if not units or any(not isinstance(unit, str) or not unit for unit in units):
        raise ValueError("declared_units must contain non-empty strings")
    if len(set(units)) != len(units):
        raise ValueError("declared_units must contain unique units")
    return tuple(sorted(units))


def _normalise_cipher_words(
    words: Iterable[Iterable[str]],
    declared_units: frozenset[str],
) -> tuple[tuple[str, ...], ...]:
    if isinstance(words, (str, bytes)):
        raise ValueError("validation_cipher_words must be a sequence of words")
    normalised: list[tuple[str, ...]] = []
    for raw_word in words:
        if isinstance(raw_word, (str, bytes)):
            raise ValueError("cipher words must preserve atomic unit boundaries")
        word = tuple(raw_word)
        if not word:
            raise ValueError("cipher words must be non-empty")
        if any(
            not isinstance(unit, str) or not unit or unit not in declared_units
            for unit in word
        ):
            raise ValueError("cipher words contain an undeclared unit")
        normalised.append(word)
    if not normalised:
        raise ValueError("validation_cipher_words must be non-empty")
    return tuple(normalised)


def _normalise_train_words(words: Iterable[str | Sequence[str]]) -> tuple[tuple[str, ...], ...]:
    if isinstance(words, (str, bytes)):
        raise ValueError("plaintext_train_words must be a sequence of words")
    normalised: list[tuple[str, ...]] = []
    for raw_word in words:
        if isinstance(raw_word, str):
            word = tuple(raw_word)
        elif isinstance(raw_word, (bytes, bytearray)):
            raise ValueError("training words must contain text or symbol sequences")
        else:
            word = tuple(raw_word)
        if not word:
            raise ValueError("plaintext training words must be non-empty")
        if any(
            not isinstance(symbol, str)
            or len(symbol) != 1
            or symbol not in string.ascii_lowercase
            for symbol in word
        ):
            raise ValueError("training words must use lowercase ASCII letters")
        normalised.append(word)
    if not normalised:
        raise ValueError("plaintext_train_words must be non-empty")
    return tuple(normalised)


def _class_name(members: Sequence[str]) -> str:
    return "+".join(sorted(members))


def _pairs(value: Iterable[tuple[str, str]] | None) -> list[list[str]] | None:
    if value is None:
        return None
    return [[left, right] for left, right in value]


def _certificate_record(certificate: Any) -> dict[str, Any]:
    record: dict[str, Any] = {
        "edge": list(certificate.edge),
        "status": certificate.status,
        "query_status": certificate.query_status,
        "nodes_visited": certificate.nodes_visited,
        "certificate": certificate.certificate,
    }
    if certificate.witness is not None:
        record["witness"] = _pairs(certificate.witness)
    return record


def _orientation_records(
    compatibility: Compatibility,
    edges: Iterable[tuple[str, str]] | None = None,
) -> list[dict[str, Any]]:
    allowed = set(edges) if edges is not None else None
    return [
        {
            "edge": list(edge),
            "partition_starts": list(starts),
        }
        for edge, starts in compatibility.edge_orientations
        if allowed is None or edge in allowed
    ]


def _graph_record(
    vertices: Iterable[str],
    edges: Iterable[tuple[str, str]],
    orientations: list[dict[str, Any]],
    *,
    status: str,
) -> dict[str, Any]:
    return {
        "status": status,
        "vertices": list(vertices),
        "edges": _pairs(tuple(edges)) or [],
        "edge_orientations": orientations,
        "edge_label": "compatibility_candidate",
    }


def _residual_graph(
    result: QuotientResult,
    compatibility: Compatibility,
) -> dict[str, Any]:
    if result.status != "proved":
        return {
            "status": "not_constructed_without_proved_quotient",
            "vertices": None,
            "edges": None,
            "edge_orientations": None,
            "edge_label": "compatibility_candidate",
        }
    forced_members = {unit for edge in result.forced_pairs for unit in edge}
    residual_vertices = tuple(
        sorted(set(result.singleton_units) | set(compatibility.unseen_units))
    )
    if forced_members & set(residual_vertices):
        raise RuntimeError("forced observed pair leaked into the residual graph")
    if forced_members | set(residual_vertices) != set(compatibility.units):
        raise RuntimeError("residual graph does not cover the declared inventory")
    residual_edges = tuple(
        edge for edge in compatibility.edges if set(edge) <= set(residual_vertices)
    )
    return _graph_record(
        residual_vertices,
        residual_edges,
        _orientation_records(compatibility, residual_edges),
        status="all_candidate_edges",
    )


def _quotient_evidence(
    result: QuotientResult,
    compatibility: Compatibility,
    validation_words: tuple[tuple[str, ...], ...],
    train_words: tuple[tuple[str, ...], ...],
) -> dict[str, Any]:
    declared_units = compatibility.units
    validation_counts = Counter(validation_words)
    evidence_counts = dict(result.evidence_counts)
    complete_edges = tuple(compatibility.edges)
    compatibility_graph = _graph_record(
        compatibility.units,
        complete_edges,
        _orientation_records(compatibility),
        status="complete_declared_graph",
    )
    quotient_proved = result.status == "proved"
    return {
        "protocol": PROTOCOL,
        "record_kind": "aggregate_cyclic_quotient_evidence",
        "quotient_status": result.status,
        "full_matching_status": result.full_status,
        "certificate": result.certificate,
        "declared_units_sha256": _canonical_hash(list(declared_units)),
        "declared_unit_count": len(declared_units),
        "observed_units": list(result.observed_units),
        "unseen_units": list(result.unseen_units),
        "observed_unit_count": len(result.observed_units),
        "unseen_unit_count": len(result.unseen_units),
        "full_witness": _pairs(result.full_witness),
        "forced_pairs": _pairs(result.forced_pairs),
        "singleton_units": list(result.singleton_units),
        "classes": [list(members) for members in result.classes],
        "unknown_edges": _pairs(result.unknown_edges),
        "evidence_counts": evidence_counts,
        "forced_certificate_count": len(result.forced_certificates),
        "edge_certificate_count": len(result.edge_certificates),
        "forced_certificates": [
            _certificate_record(item) for item in result.forced_certificates
        ],
        "edge_certificates": [
            _certificate_record(item) for item in result.edge_certificates
        ],
        "compatibility_graph": compatibility_graph,
        "residual_graph": _residual_graph(result, compatibility),
        "forced_observed_observed_edges": _pairs(result.forced_pairs) or [],
        "completion_representation": (
            "all residual full perfect matchings plus forced observed pairs"
            if quotient_proved
            else None
        ),
        "selected_unseen_mate": False,
        "input_summary": {
            "validation_token_count": len(validation_words),
            "validation_type_count": len(validation_counts),
            "training_token_count": len(train_words),
            "training_type_count": len(set(train_words)),
            "scope": "validation ciphertext and training lexicon counts only",
        },
    }


def _class_maps(result: QuotientResult) -> tuple[dict[str, tuple[str, ...]], dict[str, str]]:
    classes = {
        _class_name(members): tuple(sorted(members))
        for members in result.classes
    }
    if len(classes) != len(result.classes):
        raise RuntimeError("quotient class names are not unique")
    unit_to_class: dict[str, str] = {}
    for unit, members in result.unit_to_class:
        name = _class_name(members)
        if name not in classes or unit not in classes[name]:
            raise RuntimeError("quotient unit-to-class evidence is inconsistent")
        if unit in unit_to_class and unit_to_class[unit] != name:
            raise RuntimeError("a unit has multiple quotient classes")
        unit_to_class[unit] = name
    if set(unit_to_class) != set(result.observed_units):
        raise RuntimeError("quotient does not cover every observed unit")
    return classes, unit_to_class


def _transform_words(
    words: tuple[tuple[str, ...], ...],
    unit_to_class: Mapping[str, str],
) -> tuple[tuple[str, ...], ...]:
    transformed: list[tuple[str, ...]] = []
    for word in words:
        try:
            transformed.append(tuple(unit_to_class[unit] for unit in word))
        except KeyError as error:
            raise RuntimeError("a validation unit has no quotient class") from error
    return tuple(transformed)


def _verify_key(
    solver_result: Mapping[str, Any],
    class_names: Mapping[str, tuple[str, ...]],
    unit_to_class: Mapping[str, str],
    transformed_words: tuple[tuple[str, ...], ...],
    validation_words: tuple[tuple[str, ...], ...],
) -> tuple[dict[str, str], dict[str, str]]:
    raw_key = solver_result.get("key")
    if not isinstance(raw_key, Mapping):
        raise RuntimeError("solver did not return a class key")
    class_key = {str(symbol): str(letter) for symbol, letter in raw_key.items()}
    expected = set(class_names)
    if set(class_key) != expected:
        raise RuntimeError("solver returned an incomplete class key")
    if any(letter not in ALPHABET for letter in class_key.values()):
        raise RuntimeError("solver returned a non-ASCII plaintext letter")
    if len(set(class_key.values())) != len(class_key):
        raise RuntimeError("capacity-one class key is not injective")

    observed_key = {
        unit: class_key[class_name]
        for unit, class_name in unit_to_class.items()
    }
    if set(observed_key) != set(unit_to_class):
        raise RuntimeError("induced key does not cover observed units")
    for original, transformed in zip(validation_words, transformed_words, strict=True):
        if tuple(unit_to_class[unit] for unit in original) != transformed:
            raise RuntimeError("unit-to-class round trip changed a word")
        class_decoded = tuple(class_key[symbol] for symbol in transformed)
        unit_decoded = tuple(observed_key[unit] for unit in original)
        if class_decoded != unit_decoded:
            raise RuntimeError("class and observed-unit keys disagree")
    return dict(sorted(class_key.items())), dict(sorted(observed_key.items()))


def _fit_record(
    solver_result: Mapping[str, Any],
    objective: Mapping[str, Any],
    class_count: int,
    observed_unit_count: int,
    quotient_evidence_sha256: str,
    open_slot_count: int,
) -> dict[str, Any]:
    solver_fields = (
        "status",
        "feasible",
        "score_certified",
        "search_exhausted",
        "nodes",
        "pruned_nodes",
        "frontier_node_count",
        "lower_bound",
        "upper_bound",
        "score",
        "hit_type_count",
        "candidate_count_total",
        "candidate_type_count",
        "missing_candidate_count",
        "cipher_type_count",
        "total_weight",
    )
    return {
        "protocol": PROTOCOL,
        "record_kind": "aggregate_quotient_lexicon_fit",
        "status": solver_result.get("status"),
        "key_uniqueness": "not_tested",
        "quotient_evidence_sha256": quotient_evidence_sha256,
        "open_slot_count": open_slot_count,
        "solver": {
            field: solver_result.get(field) for field in solver_fields
        },
        "solver_config": dict(solver_result.get("config", {})),
        "objective": dict(objective),
        "class_count": class_count,
        "observed_unit_count": observed_unit_count,
        "scope": "validation ciphertext counts and plaintext training lexicon",
    }


def _verified_counts(
    units: tuple[str, ...],
    quotient: QuotientResult,
    validation_words: tuple[tuple[str, ...], ...],
    train_words: tuple[tuple[str, ...], ...],
    transformed_words: tuple[tuple[str, ...], ...] | None = None,
) -> dict[str, int]:
    values = {
        "declared_units": len(units),
        "observed_units": len(quotient.observed_units),
        "unseen_units": len(quotient.unseen_units),
        "class_count": len(quotient.classes),
        "open_slot_count": sum(
            len(members) == 1 for members in quotient.classes
        ),
        "validation_tokens": len(validation_words),
        "validation_types": len(set(validation_words)),
        "training_tokens": len(train_words),
        "training_types": len(set(train_words)),
    }
    if transformed_words is not None:
        values["transformed_validation_types"] = len(set(transformed_words))
    return values


def run_study(
    declared_units: Iterable[str],
    validation_cipher_words: Iterable[Iterable[str]],
    plaintext_train_words: Iterable[str | Sequence[str]],
    output_directory: str | Path,
) -> dict[str, Any]:
    """Run the fixed observed-quotient fit without any held-out input."""

    units = _normalise_units(declared_units)
    validation_words = _normalise_cipher_words(
        validation_cipher_words, frozenset(units)
    )
    train_words = _normalise_train_words(plaintext_train_words)
    output = Path(output_directory)
    if output.exists() and not output.is_dir():
        raise ValueError("output_directory must be a directory")
    output.mkdir(parents=True, exist_ok=True)
    quotient_path = output / QUOTIENT_FILENAME
    fit_path = output / FIT_FILENAME
    key_path = output / KEY_FILENAME
    if any(path.exists() for path in (quotient_path, fit_path, key_path)):
        raise FileExistsError("a quotient study output already exists")

    compatibility = build_compatibility(units, [validation_words])
    quotient = build_observed_quotient(
        compatibility, node_budget=QUOTIENT_NODE_BUDGET
    )
    evidence = _quotient_evidence(
        quotient, compatibility, validation_words, train_words
    )
    quotient_hash = _write_exclusive(quotient_path, evidence)
    counts = _verified_counts(units, quotient, validation_words, train_words)

    if quotient.status != "proved":
        return {
            "protocol": PROTOCOL,
            "status": "abstained",
            "quotient_status": quotient.status,
            "feasible": None,
            "verified": False,
            "lower_bound": None,
            "upper_bound": None,
            "verified_counts": counts,
            "fit": None,
            "output_hashes": {QUOTIENT_FILENAME: quotient_hash},
        }

    classes, unit_to_class = _class_maps(quotient)
    if len(classes) > len(ALPHABET):
        return {
            "protocol": PROTOCOL,
            "status": "infeasible_capacity",
            "quotient_status": quotient.status,
            "feasible": False,
            "verified": False,
            "lower_bound": None,
            "upper_bound": None,
            "verified_counts": counts,
            "fit": None,
            "output_hashes": {QUOTIENT_FILENAME: quotient_hash},
        }

    transformed_words = _transform_words(validation_words, unit_to_class)
    transformed_counts = Counter(transformed_words)
    weights, token_count, type_count, denominator = objective_weights(
        transformed_counts
    )
    objective = {
        "weight_formula": "count*T+N",
        "normalization_formula": "2*T*N",
        "N_token_count": token_count,
        "T_type_count": type_count,
        "denominator": denominator,
        "weights_total": sum(weights.values()),
        "weights_match_denominator": (
            sum(weights.values()) == denominator
            if denominator is not None
            else None
        ),
    }
    order = branch_symbol_order(transformed_counts, weights=weights)
    solver_result = solve_lexicon(
        weights,
        set(train_words),
        ALPHABET,
        capacity=CAPACITY,
        node_budget=SOLVER_NODE_BUDGET,
        symbol_order=order,
        bound_engine=BOUND_ENGINE,
    )
    fit = _fit_record(
        solver_result,
        objective,
        len(classes),
        len(quotient.observed_units),
        quotient_hash,
        sum(len(members) == 1 for members in classes.values()),
    )
    counts = _verified_counts(
        units, quotient, validation_words, train_words, transformed_words
    )
    if not solver_result.get("feasible"):
        fit_hash = _write_exclusive(fit_path, fit)
        return {
            "protocol": PROTOCOL,
            "status": "fit_infeasible",
            "quotient_status": quotient.status,
            "feasible": False,
            "verified": False,
            "lower_bound": solver_result.get("lower_bound"),
            "upper_bound": solver_result.get("upper_bound"),
            "verified_counts": counts,
            "objective": objective,
            "fit": fit,
            "output_hashes": {
                QUOTIENT_FILENAME: quotient_hash,
                FIT_FILENAME: fit_hash,
            },
        }

    class_key, observed_key = _verify_key(
        solver_result,
        classes,
        unit_to_class,
        transformed_words,
        validation_words,
    )
    key_record = {
        "protocol": PROTOCOL,
        "record_kind": "complete_observed_quotient_key",
        "quotient_status": quotient.status,
        "full_matching_status": quotient.full_status,
        "key_uniqueness": "not_tested",
        "quotient_evidence_sha256": quotient_hash,
        "open_slot_count": sum(
            len(members) == 1 for members in classes.values()
        ),
        "class_names": sorted(classes),
        "class_members": {
            name: list(classes[name]) for name in sorted(classes)
        },
        "class_key": class_key,
        "observed_unit_key": observed_key,
        "coverage": {
            "declared_unit_count": len(units),
            "observed_unit_count": len(quotient.observed_units),
            "unseen_unit_count": len(quotient.unseen_units),
            "mapped_observed_units": len(observed_key),
        },
        "fit_status": solver_result.get("status"),
        "score_certified": solver_result.get("score_certified"),
    }
    key_hash = _write_exclusive(key_path, key_record)
    fit_hash = _write_exclusive(fit_path, fit)
    return {
        "protocol": PROTOCOL,
        "status": solver_result.get("status"),
        "quotient_status": quotient.status,
        "feasible": True,
        "verified": True,
        "lower_bound": solver_result.get("lower_bound"),
        "upper_bound": solver_result.get("upper_bound"),
        "verified_counts": counts,
        "objective": objective,
        "fit": fit,
        "output_hashes": {
            QUOTIENT_FILENAME: quotient_hash,
            KEY_FILENAME: key_hash,
            FIT_FILENAME: fit_hash,
        },
    }


__all__ = [
    "BOUND_ENGINE",
    "CAPACITY",
    "FIT_FILENAME",
    "KEY_FILENAME",
    "PROTOCOL",
    "QUOTIENT_FILENAME",
    "QUOTIENT_NODE_BUDGET",
    "SOLVER_NODE_BUDGET",
    "run_study",
]
