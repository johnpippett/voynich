"""Assess one-unit alternatives at a caller-supplied certified optimum.

This module does not prove the global optimum.  The caller must provide the
certificate provenance for the frozen threshold problem.  The assessor then
tests each incumbent assignment against the same finite objective and domain.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
import hashlib
import json
from typing import Any, Iterator

from experiments.identifiability.threshold import ThresholdProblem


class CertificateContradiction(ValueError):
    """A witness scores above the caller's claimed certified optimum."""


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _target_value(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError("certified_score must be a non-negative integer")
    return value


def _budget_value(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError("node_budget_per_query must be a non-negative integer or None")
    return value


def _domain_payload(problem: ThresholdProblem) -> dict[str, Any]:
    """Return a code-independent representation of the frozen objective domain."""

    return {
        "ciphertext_counts": [
            [list(word), weight]
            for word, weight in sorted(problem.ciphertext_counts.items())
        ],
        "plaintext_lexicon": [
            list(word) for word in sorted(problem.plaintext_lexicon)
        ],
        "plaintext_alphabet": list(problem.plaintext_alphabet),
        "capacity": problem.capacity,
    }


def _normalise_certificate(
    problem: ThresholdProblem,
    target: int,
    certificate: Mapping[str, Any] | None,
    certificate_metadata: Mapping[str, Any] | None,
) -> dict[str, Any]:
    if certificate is not None and certificate_metadata is not None:
        raise ValueError("pass certificate or certificate_metadata, not both")
    supplied = certificate if certificate is not None else certificate_metadata
    if not isinstance(supplied, Mapping):
        raise ValueError(
            "certificate metadata must include problem_fingerprint, target, "
            "and provenance"
        )
    if supplied.get("problem_fingerprint") != problem.problem_fingerprint:
        raise ValueError("certificate problem_fingerprint does not match the problem")
    if supplied.get("target") != target:
        raise ValueError("certificate target does not match certified_score")

    provenance_keys = (
        "provenance", "source", "proof_kind", "certificate_id", "kind",
    )
    has_provenance = any(
        isinstance(supplied.get(key), str) and supplied[key].strip()
        for key in provenance_keys
    )
    if not has_provenance:
        raise ValueError("certificate metadata must include global-certificate provenance")
    if "score_certified" in supplied and supplied["score_certified"] is not True:
        raise ValueError("certificate score_certified must be true when supplied")
    for bound_name in ("lower_bound", "upper_bound"):
        if bound_name in supplied and supplied[bound_name] != target:
            raise ValueError(f"certificate {bound_name} does not match target")

    try:
        # Keep the record deterministic and reject opaque objects.
        return json.loads(_canonical_json(dict(supplied)))
    except (TypeError, ValueError) as exc:
        raise ValueError("certificate metadata must be JSON-compatible") from exc


def _normalise_total_key(
    problem: ThresholdProblem,
    supplied_key: Mapping[str, str],
    label: str,
) -> dict[str, str]:
    if not isinstance(supplied_key, Mapping):
        raise TypeError(f"{label} must be a mapping")
    key = dict(supplied_key)
    symbols = set(problem.cipher_symbols)
    if set(key) != symbols:
        raise ValueError(f"{label} must be a complete total map")
    alphabet = set(problem.plaintext_alphabet)
    if any(
        not isinstance(unit, str)
        or not isinstance(letter, str)
        or letter not in alphabet
        for unit, letter in key.items()
    ):
        raise ValueError(f"{label} contains an invalid symbol or letter")
    if problem.capacity is not None:
        counts = Counter(key.values())
        if any(count > problem.capacity for count in counts.values()):
            raise ValueError(f"{label} exceeds plaintext-letter capacity")
    return dict(sorted(key.items()))


def _validate_incumbent(
    problem: ThresholdProblem,
    incumbent_key: Mapping[str, str],
    target: int,
) -> tuple[dict[str, str], int]:
    key = _normalise_total_key(problem, incumbent_key, "incumbent_key")

    score = _score_key(problem, key)
    if score != target:
        raise ValueError("incumbent_key score does not equal certified_score")
    return dict(sorted(key.items())), score


def _score_key(problem: ThresholdProblem, key: Mapping[str, str]) -> int:
    """Score one complete map without using the threshold solver's scorer."""

    score = 0
    lexicon = problem.plaintext_lexicon
    for cipher_word, weight in problem.ciphertext_counts.items():
        decoded = tuple(key[symbol] for symbol in cipher_word)
        if decoded in lexicon:
            score += weight
    return score


def _objective_domain_fingerprint(problem: ThresholdProblem) -> str:
    return _digest(_domain_payload(problem))


def _capacity_allows(
    problem: ThresholdProblem,
    key: Mapping[str, str],
    unit: str,
    letter: str,
) -> bool:
    if problem.capacity is None:
        return True
    usage = Counter(key.values())
    usage[key[unit]] -= 1
    return usage[letter] < problem.capacity


def _warm_witness(
    problem: ThresholdProblem,
    incumbent: Mapping[str, str],
    unit: str,
    target: int,
) -> dict[str, Any] | None:
    incumbent_letter = incumbent[unit]
    for letter in sorted(problem.plaintext_alphabet):
        if letter == incumbent_letter:
            continue
        if not _capacity_allows(problem, incumbent, unit, letter):
            continue
        candidate = dict(incumbent)
        candidate[unit] = letter
        score = _score_key(problem, candidate)
        if score > target:
            raise CertificateContradiction(
                f"warm witness for {unit} scores {score} above certified score {target}"
            )
        if score >= target:
            return {
                "key": dict(sorted(candidate.items())),
                "score": score,
                "changed_unit": unit,
                "changed_from": incumbent_letter,
                "changed_to": letter,
                "method": "one-unit incumbent witness",
            }
    return None


def _validate_query_witness(
    problem: ThresholdProblem,
    query: Mapping[str, Any],
    target: int,
    unit: str,
    incumbent_letter: str,
) -> dict[str, Any] | None:
    if query.get("status") != "feasible":
        return None
    key = query.get("key")
    if not isinstance(key, Mapping):
        raise ValueError(f"threshold query for {unit} returned no witness key")
    if key.get(unit) == incumbent_letter:
        raise ValueError(f"threshold query for {unit} returned the forbidden incumbent letter")
    normalized = _normalise_total_key(problem, key, f"threshold query for {unit}")
    score = _score_key(problem, normalized)
    reported_score = query.get("score")
    if reported_score != score:
        raise ValueError(f"threshold query for {unit} returned an inconsistent score")
    if score > target:
        raise CertificateContradiction(
            f"threshold witness for {unit} scores {score} above certified score {target}"
        )
    if score < target:
        raise ValueError(f"threshold query for {unit} returned a sub-threshold witness")
    return {
        "key": dict(sorted(normalized.items())),
        "score": score,
        "changed_unit": unit,
        "changed_from": incumbent_letter,
        "changed_to": normalized[unit],
        "method": "threshold query witness",
    }


def _record_for_unit(
    problem: ThresholdProblem,
    incumbent: Mapping[str, str],
    target: int,
    node_budget_per_query: int | None,
    domain_fingerprint: str,
    unit: str,
) -> dict[str, Any]:
    incumbent_letter = incumbent[unit]
    forbidden = {unit: [incumbent_letter]}
    warm_witness = _warm_witness(problem, incumbent, unit, target)

    # Validate a warm witness with the threshold API.  The incumbent is
    # forbidden, so pass only the changed, compatible witness as initial_key.
    raw_query = problem.query(
        target,
        forbidden=forbidden,
        node_budget=node_budget_per_query,
        initial_key=None if warm_witness is None else warm_witness["key"],
    )
    query_witness = _validate_query_witness(
        problem,
        raw_query,
        target,
        unit,
        incumbent_letter,
    )
    if raw_query.get("status") == "infeasible" and warm_witness is not None:
        raise ValueError(f"threshold query for {unit} rejected a known warm witness")

    witness = warm_witness or query_witness
    if witness is not None:
        classification = "ambiguous"
    elif raw_query.get("status") == "infeasible":
        classification = "forced_at_certified_optimum"
    elif raw_query.get("status") == "unknown":
        classification = "unresolved"
    else:
        raise ValueError(f"unexpected threshold status for {unit}: {raw_query.get('status')!r}")

    return {
        "cipher_unit": unit,
        "incumbent_letter": incumbent_letter,
        "forbidden": forbidden,
        "classification": classification,
        "objective_domain_fingerprint": domain_fingerprint,
        "raw_query": dict(raw_query),
        "warm_witness": warm_witness,
        "witness": witness,
    }


def _prepare(
    problem: ThresholdProblem,
    incumbent_key: Mapping[str, str],
    certified_score: int,
    *,
    node_budget_per_query: int | None,
    certificate: Mapping[str, Any] | None,
    certificate_metadata: Mapping[str, Any] | None,
) -> tuple[dict[str, str], int, int | None, dict[str, Any], str]:
    if not isinstance(problem, ThresholdProblem):
        raise TypeError("problem must be a ThresholdProblem")
    target = _target_value(certified_score)
    budget = _budget_value(node_budget_per_query)
    provenance = _normalise_certificate(
        problem,
        target,
        certificate,
        certificate_metadata,
    )
    incumbent, score = _validate_incumbent(problem, incumbent_key, target)
    return incumbent, score, budget, provenance, _objective_domain_fingerprint(problem)


def iter_assess_optimum(
    problem: ThresholdProblem,
    incumbent_key: Mapping[str, str],
    certified_score: int,
    *,
    node_budget_per_query: int | None = 1000,
    certificate: Mapping[str, Any] | None = None,
    certificate_metadata: Mapping[str, Any] | None = None,
) -> Iterator[dict[str, Any]]:
    """Yield one identifiability record per sorted cipher unit.

    The caller must supply certificate metadata for a global optimum.  This
    iterator does not verify that certificate; it records and uses its scope.
    """

    incumbent, _score, budget, _provenance, domain_fingerprint = _prepare(
        problem,
        incumbent_key,
        certified_score,
        node_budget_per_query=node_budget_per_query,
        certificate=certificate,
        certificate_metadata=certificate_metadata,
    )
    target = certified_score
    for unit in problem.cipher_symbols:
        yield _record_for_unit(
            problem,
            incumbent,
            target,
            budget,
            domain_fingerprint,
            unit,
        )


def assess_optimum(
    problem: ThresholdProblem,
    incumbent_key: Mapping[str, str],
    certified_score: int,
    *,
    node_budget_per_query: int | None = 1000,
    certificate: Mapping[str, Any] | None = None,
    certificate_metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Assess one-unit alternatives to a caller-supplied optimum.

    ``certificate`` or ``certificate_metadata`` must include matching
    ``problem_fingerprint`` and ``target`` values plus provenance.  A Boolean
    certification flag alone is rejected.  This function does not verify the
    global certificate or consult an oracle key.
    """

    incumbent, score, budget, provenance, domain_fingerprint = _prepare(
        problem,
        incumbent_key,
        certified_score,
        node_budget_per_query=node_budget_per_query,
        certificate=certificate,
        certificate_metadata=certificate_metadata,
    )
    records = list(
        iter_assess_optimum(
            problem,
            incumbent,
            certified_score,
            node_budget_per_query=budget,
            certificate=provenance,
        )
    )
    counts = Counter(record["classification"] for record in records)
    return {
        "status": "complete",
        "problem_fingerprint": problem.problem_fingerprint,
        "objective_domain_fingerprint": domain_fingerprint,
        "certificate": provenance,
        "target": certified_score,
        "incumbent_key": dict(sorted(incumbent.items())),
        "incumbent_score": score,
        "node_budget_per_query": budget,
        "cipher_units": list(problem.cipher_symbols),
        "records": records,
        "summary": {
            "ambiguous_units": [
                record["cipher_unit"]
                for record in records
                if record["classification"] == "ambiguous"
            ],
            "forced_units": [
                record["cipher_unit"]
                for record in records
                if record["classification"] == "forced_at_certified_optimum"
            ],
            "unresolved_units": [
                record["cipher_unit"]
                for record in records
                if record["classification"] == "unresolved"
            ],
            "counts": dict(sorted(counts.items())),
        },
        "interpretation": (
            "The records assess one-unit alternatives in the supplied finite "
            "domain. They do not verify the global certificate or establish "
            "historical meaning."
        ),
    }


__all__ = [
    "CertificateContradiction",
    "assess_optimum",
    "iter_assess_optimum",
]
