#!/usr/bin/env python3
"""Independently verify the frozen optimal-set Latin result.

This script does not import ``experiments.optimal_set.secondary``.  It rebuilds
the reference streams, model counts, primary scores, candidate enumeration,
secondary ratios, test diagnostics, and provenance links.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from fractions import Fraction
import argparse
import hashlib
import json
import math
from pathlib import Path
import random
import string
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from voynich.reference import load_reference_partitions


# The frozen primary artifacts are public report inputs.
RUN = ROOT / "reports" / "optimal-set-secondary-v1-latin"
DEFAULT_OUTPUT = Path("results/optimal-set-independent-replay/audit.json")
PUBLISHED_ARTIFACT_HASHES = {
    "input.json": "3a9b5f0fe4dc69abcb13e10dcbf63d8086c2bf329af84d62b47b0477c6470eec",
    "enumeration.json": "4a5e43e6331c7e1a4ce32fae3ff84d5af6defcc6d77e641a4260bc6a53b2776c",
    "ranking.json": "8641d91ab568326e70539711cb0e48ccc69ec0514b2043496ccef3b65f2d39e0",
    "selection.json": "1eb5be203055324320b8d517e83bc42ee8579090bd1718e3194ef09be04f9b82",
    "result.json": "112fd2823d569462a6cccd6422d023eafcca987eb4dcb3ed550262d1dc3cb54a",
}
ALPHABET = tuple(string.ascii_lowercase)
BOS = "<BOS>"
EOS = "<EOS>"
UNK = "<UNK>"
ORDER = 3
ADD_ALPHA = 0.1
CAPACITY = 2


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_path(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode(
        "utf-8"
    )


def canonical_hash(value: Any) -> str:
    return sha256_bytes(canonical_bytes(value))


def digest_without_newline(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256_bytes(encoded)


def context_key(context: tuple[str, ...]) -> str:
    return json.dumps(list(context), ensure_ascii=False, separators=(",", ":"))


def context_for(sequence: tuple[str, ...], position: int, order: int) -> tuple[str, ...]:
    prefix_length = max(0, order - position)
    history = sequence[max(0, position - order) : position]
    return (BOS,) * prefix_length + history


def planted_streams(words: list[str]) -> dict[str, Any]:
    """Rebuild the seed-7000 cap2 emitter without importing control code."""

    rng = random.Random(7000)
    units = [f"c{index:02d}" for index in range(52)]
    rng.shuffle(units)
    shuffled_letters = list(ALPHABET)
    rng.shuffle(shuffled_letters)
    assigned_letters = list(ALPHABET) * 2
    rng.shuffle(assigned_letters)
    cipher_to_plain = dict(zip(units, assigned_letters, strict=True))
    cycles: dict[str, list[str]] = {letter: [] for letter in ALPHABET}
    for unit, letter in cipher_to_plain.items():
        cycles[letter].append(unit)
    for letter in ALPHABET:
        rng.shuffle(cycles[letter])

    offsets = {letter: 0 for letter in ALPHABET}
    encrypted: list[tuple[str, ...]] = []
    for word in words:
        cipher_word: list[str] = []
        for letter in word:
            cycle = cycles[letter]
            offset = offsets[letter]
            cipher_word.append(cycle[offset % len(cycle)])
            offsets[letter] = offset + 1
        encrypted.append(tuple(cipher_word))
    return {
        "cipher_words": encrypted,
        "cipher_to_plain": cipher_to_plain,
        "cycles": cycles,
    }


def fit_model_payload(words: list[str]) -> dict[str, Any]:
    """Rebuild the frozen order-3 model payload from training words."""

    vocabulary = (*ALPHABET, UNK, EOS)
    counts: defaultdict[tuple[str, ...], Counter[str]] = defaultdict(Counter)
    unigram = Counter({symbol: 0 for symbol in vocabulary})
    symbol_count = 0
    unknown_count = 0
    for word in words:
        mapped: list[str] = []
        for symbol in word:
            if symbol in ALPHABET:
                mapped.append(symbol)
            else:
                mapped.append(UNK)
                unknown_count += 1
        symbol_count += len(mapped)
        sequence = tuple(mapped)
        for position, target in enumerate((*sequence, EOS)):
            context = context_for(sequence, position, ORDER)
            counts[context][target] += 1
            unigram[target] += 1

    frozen_counts = tuple(
        (
            context_key(context),
            tuple(sorted((symbol, int(amount)) for symbol, amount in counter.items())),
        )
        for context, counter in sorted(counts.items(), key=lambda item: context_key(item[0]))
    )
    frozen_totals = tuple(
        (key, sum(amount for _symbol, amount in rows))
        for key, rows in frozen_counts
    )
    frozen_unigrams = tuple((symbol, int(unigram[symbol])) for symbol in vocabulary)
    return {
        "order": ORDER,
        "add_alpha": ADD_ALPHA,
        "alphabet": list(ALPHABET),
        "vocabulary": list(vocabulary),
        "start_symbol": BOS,
        "end_symbol": EOS,
        "unknown_symbol": UNK,
        "context_counts": {key: dict(rows) for key, rows in frozen_counts},
        "context_totals": dict(frozen_totals),
        "unigram_counts": dict(frozen_unigrams),
        "training_word_count": len(words),
        "training_symbol_count": symbol_count,
        "unknown_training_symbols": unknown_count,
        "alphabet_source": "declared",
        "definition": (
            "Fixed-boundary conditional character n-gram objective: "
            "P(next symbol | previous order symbols), with add-alpha smoothing. "
            "Scores are weighted n-gram evidence, not a composite full-probability claim."
        ),
        "_counts": counts,
        "_totals": {context: sum(counter.values()) for context, counter in counts.items()},
    }


def primary_weights(cipher_counts: Counter[tuple[str, ...]]) -> dict[tuple[str, ...], int]:
    token_count = sum(cipher_counts.values())
    type_count = len(cipher_counts)
    return {
        word: count * type_count + token_count
        for word, count in sorted(cipher_counts.items())
    }


def score_key(
    counts: dict[tuple[str, ...], int],
    key: dict[str, str],
    lexicon: set[tuple[str, ...]],
) -> int:
    return sum(
        weight
        for word, weight in counts.items()
        if tuple(key[unit] for unit in word) in lexicon
    )


def event_histogram(
    counts: Counter[tuple[str, ...]], key: dict[str, str]
) -> Counter[tuple[tuple[str, ...], str]]:
    histogram: Counter[tuple[tuple[str, ...], str]] = Counter()
    for word, weight in counts.items():
        mapped = tuple(key[unit] for unit in word)
        for position, target in enumerate((*mapped, EOS)):
            histogram[(context_for(mapped, position, ORDER), target)] += weight
    return histogram


def ratio_from_delta(
    delta: dict[tuple[tuple[str, ...], str], int],
    model_payload: dict[str, Any],
) -> Fraction:
    model_counts = model_payload["_counts"]
    model_totals = model_payload["_totals"]
    ratio = Fraction(1, 1)
    for event in sorted(delta):
        amount = delta[event]
        if not amount:
            continue
        context, target = event
        event_count = model_counts.get(context, {}).get(target, 0)
        context_total = model_totals.get(context, 0)
        factor = Fraction(10 * event_count + 1, 10 * context_total + 28)
        if amount > 0:
            ratio *= factor**amount
        else:
            ratio /= factor ** (-amount)
    return ratio


def ratio_record(value: Fraction) -> dict[str, Any]:
    return {
        "numerator_hex": hex(value.numerator),
        "denominator_hex": hex(value.denominator),
        "numerator_bits": value.numerator.bit_length(),
        "denominator_bits": value.denominator.bit_length(),
        "fraction": f"{value.numerator}/{value.denominator}",
    }


def candidate_diagnostics(
    candidates: list[dict[str, str]],
    cipher_test: list[tuple[str, ...]],
    plaintext_test: list[str],
    planted_map: dict[str, str],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    secondary_maximizer = 3
    for index, candidate in enumerate(candidates):
        known_units = set(candidate)
        key_correct = sum(candidate[unit] == planted_map[unit] for unit in known_units)
        total_positions = 0
        correct_positions = 0
        word_correct = 0
        observed_positions = 0
        observed_correct = 0
        unseen_positions = 0
        unseen_units: set[str] = set()
        for cipher_word, plain_word in zip(cipher_test, plaintext_test, strict=True):
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
        rows.append(
            {
                "candidate_index": index,
                "secondary_maximizer": index == secondary_maximizer,
                "observed_key_units": len(known_units & set(planted_map)),
                "key_positions": len(known_units),
                "key_correct": key_correct,
                "test_observed_positions": observed_positions,
                "test_observed_correct": observed_correct,
                "test_positions": total_positions,
                "test_correct": correct_positions,
                "test_errors": total_positions - correct_positions,
                "test_unseen_positions": unseen_positions,
                "test_unseen_units": sorted(unseen_units),
                "test_word_count": len(plaintext_test),
                "test_word_correct": word_correct,
            }
        )
    return rows


def load_pinned_json(name: str) -> dict[str, Any]:
    """Read one frozen report artifact after checking its published hash."""

    path = RUN / name
    if sha256_path(path) != PUBLISHED_ARTIFACT_HASHES[name]:
        raise ValueError("published optimal-set artifact hash mismatch")
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError("published optimal-set artifact is not a JSON object")
    return value


def build_report() -> dict[str, Any]:
    input_record = load_pinned_json("input.json")
    enumeration = load_pinned_json("enumeration.json")
    ranking = load_pinned_json("ranking.json")
    selection = load_pinned_json("selection.json")
    result = load_pinned_json("result.json")
    partitions = load_reference_partitions(ROOT)["latin_llct"]["words"]
    train = list(partitions["train"])
    validation = list(partitions["validation"])
    test = list(partitions["test"])

    streams = {
        "plaintext_train": train,
        "plaintext_validation": validation,
        "plaintext_test": test,
    }
    encrypted: dict[str, list[tuple[str, ...]]] = {}
    planted_map: dict[str, str] | None = None
    for name, words in streams.items():
        built = planted_streams(words)
        encrypted[name.replace("plaintext", "cipher")] = built["cipher_words"]
        if planted_map is None:
            planted_map = built["cipher_to_plain"]
    assert planted_map is not None
    cipher_train = encrypted["cipher_train"]
    cipher_validation = encrypted["cipher_validation"]
    cipher_test = encrypted["cipher_test"]
    stream_values = {
        "plaintext_train": train,
        "plaintext_validation": validation,
        "plaintext_test": test,
        "cipher_train": cipher_train,
        "cipher_validation": cipher_validation,
        "cipher_test": cipher_test,
    }
    baseline_report = json.loads(
        (ROOT / "reports/homophonic-feasibility-v1/latin-cold.json").read_text()
    )
    expected_streams = baseline_report["stream_sha256"]
    stream_matches = {
        name: canonical_hash(value) == expected_streams.get(name)
        for name, value in stream_values.items()
    }

    lexicon = {tuple(word) for word in train}
    cipher_counts = Counter(cipher_validation)
    weights = primary_weights(cipher_counts)
    model_payload_full = fit_model_payload(train)
    model_payload = {
        key: value
        for key, value in model_payload_full.items()
        if not key.startswith("_")
    }
    model_hash = canonical_hash(model_payload)
    model_hash_expected = input_record["model_hash"]

    data_hashes = {
        "plaintext_train": canonical_hash(train),
        "plaintext_validation": canonical_hash(validation),
        "cipher_train": canonical_hash(cipher_train),
        "cipher_validation": canonical_hash(cipher_validation),
        "train_lexicon": canonical_hash(sorted(lexicon)),
        "training_words": canonical_hash(train),
        "training_lexicon": canonical_hash([list(word) for word in sorted(lexicon)]),
        "validation_cipher_counts": canonical_hash(
            [[list(word), int(weight)] for word, weight in sorted(cipher_counts.items())]
        ),
        "primary_weights": canonical_hash(
            [[list(word), int(weight)] for word, weight in sorted(weights.items())]
        ),
    }
    expected_data = input_record["data_hashes"]
    data_match = {
        name: digest == expected_data.get(name)
        for name, digest in data_hashes.items()
        if name in expected_data
    }
    objective_payload = {
        "ciphertext_counts": [
            [list(word), weight] for word, weight in sorted(weights.items())
        ],
        "plaintext_lexicon": [list(word) for word in sorted(lexicon)],
        "plaintext_alphabet": list(ALPHABET),
        "capacity": CAPACITY,
    }
    objective_fingerprint = digest_without_newline(objective_payload)

    fixed = dict(input_record["fixed_assignments"])
    usage = Counter(fixed.values())
    choices = [letter for letter in ALPHABET if usage[letter] < CAPACITY]
    candidates: list[dict[str, str]] = []
    for letter in choices:
        candidate = dict(fixed)
        candidate["c40"] = letter
        candidates.append(dict(sorted(candidate.items())))
    candidates.sort(key=lambda key: tuple(key[unit] for unit in sorted(key)))
    candidate_set_payload = sorted(
        [[[unit, key[unit]] for unit in sorted(key)] for key in candidates]
    )
    candidate_set_hash = canonical_hash(candidate_set_payload)
    primary_scores = [score_key(weights, key, lexicon) for key in candidates]
    target = input_record["target"]
    model_counts = Counter(cipher_counts)
    baseline_index = next(
        index for index, key in enumerate(candidates) if key == input_record["baseline_incumbent"]
    )
    baseline_histogram = event_histogram(model_counts, candidates[baseline_index])
    ratios: list[Fraction] = []
    deltas: list[int] = []
    for key in candidates:
        histogram = event_histogram(model_counts, key)
        delta = {
            event: histogram.get(event, 0) - baseline_histogram.get(event, 0)
            for event in set(histogram).union(baseline_histogram)
            if histogram.get(event, 0) != baseline_histogram.get(event, 0)
        }
        deltas.append(sum(abs(amount) for amount in delta.values()))
        ratios.append(ratio_from_delta(delta, model_payload_full))
    maximum = max(ratios)
    maximizers = [index for index, value in enumerate(ratios) if value == maximum]
    diagnostics = candidate_diagnostics(candidates, cipher_test, test, planted_map)

    # Verify the published query and certificate binding without importing the runner.
    assignment_dir = ROOT / "reports/identifiability-v1-latin"
    decisions = json.loads((assignment_dir / "decisions.json").read_text())
    queries = []
    query_hash_matches = True
    query_checks = []
    for filename, expected_hash in sorted(decisions["query_sha256"].items()):
        path = assignment_dir / filename
        actual_hash = sha256_path(path)
        query_hash_matches = query_hash_matches and actual_hash == expected_hash
        query = json.loads(path.read_text())
        raw = query["raw_query"]
        classification = query["classification"]
        forbidden = query.get("forbidden")
        forbidden_fields_valid = (
            forbidden == {query["cipher_unit"]: [query.get("incumbent_letter")]}
            and raw.get("forbidden") == forbidden
            and raw.get("constraints") == {}
        )
        if classification == "forced_at_certified_optimum":
            valid = (
                raw.get("status") == "infeasible"
                and raw.get("feasible") is False
                and raw.get("infeasible") is True
                and raw.get("search_exhausted") is True
                and raw.get("proof_kind") == "search_exhausted_no_witness"
                and raw.get("upper_bound", target) < target
                and raw.get("frontier_node_count") == 0
                and raw.get("score") is None
            )
        elif classification == "ambiguous":
            witness = raw.get("key")
            valid = (
                raw.get("status") == "feasible"
                and raw.get("feasible") is True
                and raw.get("score") == target
                and raw.get("search_exhausted") is False
                and isinstance(witness, dict)
                and witness.get(query["cipher_unit"]) != query["incumbent_letter"]
            )
        else:
            valid = False
        valid = valid and raw.get("query_target", raw.get("target")) == target
        valid = valid and raw.get("capacity", raw.get("config", {}).get("capacity")) == CAPACITY
        valid = valid and raw.get("problem_fingerprint") == input_record["objective_domain_fingerprint"]
        valid = valid and forbidden_fields_valid
        query_checks.append(valid)
        queries.append(query)

    forced = sorted(q["cipher_unit"] for q in queries if q["classification"] == "forced_at_certified_optimum")
    ambiguous = sorted(q["cipher_unit"] for q in queries if q["classification"] == "ambiguous")
    query_binding = {
        "query_count": len(queries),
        "forced_count": len(forced),
        "ambiguous_units": ambiguous,
        "all_query_hashes_match": query_hash_matches,
        "all_query_fields_valid": all(query_checks),
        "all_query_forbidden_fields_valid": all(
            q.get("forbidden") == {q["cipher_unit"]: [q.get("incumbent_letter")]}
            and q["raw_query"].get("forbidden") == q.get("forbidden")
            and q["raw_query"].get("constraints") == {}
            for q in queries
        ),
        "query_hashes_match_input": dict(sorted(decisions["query_sha256"].items()))
        == dict(sorted(input_record["query_hashes"].items())),
        "classification_counts_match_decisions": decisions.get("counts")
        == {"ambiguous": 1, "forced_at_certified_optimum": 45},
        "fixed_assignment_values_match_queries": all(
            input_record["fixed_assignments"].get(q["cipher_unit"]) == q["incumbent_letter"]
            for q in queries
            if q["classification"] == "forced_at_certified_optimum"
        ),
    }

    # Verify every recorded file hash and every five-artifact link.
    artifact_hashes = {name: sha256_path(RUN / name) for name in (
        "input.json", "enumeration.json", "ranking.json", "selection.json", "result.json"
    )}
    artifact_links = {
        "enumeration_input": enumeration.get("input_sha256") == artifact_hashes["input.json"],
        "ranking_input": ranking.get("input_sha256") == artifact_hashes["input.json"],
        "ranking_enumeration": ranking.get("enumeration_sha256") == artifact_hashes["enumeration.json"],
        "selection_input": selection.get("input_sha256") == artifact_hashes["input.json"],
        "selection_enumeration": selection.get("enumeration_sha256") == artifact_hashes["enumeration.json"],
        "selection_ranking": selection.get("ranking_sha256") == artifact_hashes["ranking.json"],
        "result_input": result.get("input_sha256") == artifact_hashes["input.json"],
        "result_enumeration": result.get("enumeration_sha256") == artifact_hashes["enumeration.json"],
        "result_ranking": result.get("ranking_sha256") == artifact_hashes["ranking.json"],
        "result_selection": result.get("selection_sha256") == artifact_hashes["selection.json"],
    }
    code_hash_matches = True
    code_hash_failures: list[str] = []
    for relative, expected_hash in sorted(input_record["code_hashes"].items()):
        path = ROOT / relative
        actual_hash = sha256_path(path) if path.is_file() else None
        if actual_hash != expected_hash:
            code_hash_matches = False
            code_hash_failures.append(relative)
    protocol_hash_matches = True
    protocol_hash_failures: list[str] = []
    for relative, expected_hash in sorted(input_record["protocol_hashes"].items()):
        path = ROOT / relative
        actual_hash = sha256_path(path) if path.is_file() else None
        if actual_hash != expected_hash:
            protocol_hash_matches = False
            protocol_hash_failures.append(relative)
    source_hash_matches = True
    source_hash_failures: list[str] = []
    for relative, expected_hash in sorted(input_record["source_hashes"].items()):
        path = ROOT / relative
        actual_hash = sha256_path(path) if path.is_file() else None
        if actual_hash != expected_hash:
            source_hash_matches = False
            source_hash_failures.append(relative)
    pinned_hash_matches = True
    pinned_hash_failures: list[str] = []
    for relative, expected_hash in sorted(input_record["pinned_artifacts"].items()):
        path = ROOT / relative
        actual_hash = sha256_path(path) if path.is_file() else None
        if actual_hash != expected_hash:
            pinned_hash_matches = False
            pinned_hash_failures.append(relative)

    baseline_solver = baseline_report["solver"]
    certificate = {
        "target": target,
        "score": baseline_solver.get("score"),
        "lower_bound": baseline_solver.get("lower_bound"),
        "upper_bound": baseline_solver.get("upper_bound"),
        "score_certified": baseline_solver.get("score_certified"),
        "search_exhausted": baseline_solver.get("search_exhausted"),
        "bound_engine": baseline_solver.get("config", {}).get("bound_engine"),
        "certificate_binds_reconstructed_target": baseline_solver.get("score") == target == primary_scores[baseline_index],
    }
    certificate_checks = {
        "score": certificate["score"] == target,
        "lower_bound": certificate["lower_bound"] == target,
        "upper_bound": certificate["upper_bound"] == target,
        "score_certified": certificate["score_certified"] is True,
        "bound_engine": certificate["bound_engine"] == "bitset",
        "reconstructed_target": certificate["certificate_binds_reconstructed_target"],
        "search_exhausted_field_is_boolean": isinstance(certificate["search_exhausted"], bool),
        "baseline_status": baseline_solver.get("status") == "bound_certified",
        "baseline_family": baseline_report.get("family") == "cap2",
        "baseline_seed": baseline_report.get("seed") == 7000,
        "baseline_capacity": baseline_solver.get("config", {}).get("capacity") == CAPACITY,
        "baseline_feasible": baseline_solver.get("feasible") is True,
    }

    independent_log2_ratio = math.log2(maximum.numerator) - math.log2(maximum.denominator)

    frozen_ratio_rows = []
    for row, candidate, ratio in zip(ranking["candidate_results"], candidates, ratios, strict=True):
        frozen_ratio_rows.append(
            {
                "candidate_index": row["candidate_index"],
                "c40": candidate["c40"],
                "ratio": ratio_record(ratio),
                "delta_event_count": deltas[row["candidate_index"]],
                "matches_frozen_ratio": row["likelihood_ratio"]["numerator_hex"] == hex(ratio.numerator)
                and row["likelihood_ratio"]["denominator_hex"] == hex(ratio.denominator),
            }
        )

    matches = {
        "streams": all(stream_matches.values()),
        "model_hash": model_hash == model_hash_expected,
        "data_hashes": all(data_match.values()),
        "objective_fingerprint": objective_fingerprint == input_record["objective_domain_fingerprint"],
        "candidate_set": candidate_set_hash == ranking["candidate_set_sha256"] == selection["candidate_set_sha256"],
        "primary_scores": primary_scores == [target] * len(candidates),
        "candidate_order_and_maps": candidates
        == [dict(sorted(key.items())) for key in selection["all_primary_optimal_maps"]]
        == [dict(sorted(key.items())) for key in enumeration["collected_maps"]],
        "secondary_ratios": all(row["matches_frozen_ratio"] for row in frozen_ratio_rows),
        "secondary_maximizer": maximizers == ranking["maximizer_indices"],
        "secondary_log2_ratio": abs(
            independent_log2_ratio - ranking["maximum_log2_ratio"]
        ) < 1e-12,
        "diagnostics": diagnostics == result["diagnostics"]["candidate_diagnostics"],
        "query_binding": all(query_binding.values()),
        "artifact_links": all(artifact_links.values()),
        "code_hashes": code_hash_matches,
        "protocol_hashes": protocol_hash_matches,
        "source_hashes": source_hash_matches,
        "pinned_artifacts": pinned_hash_matches,
        "certificate": all(certificate_checks.values()),
    }
    report = {
        "kind": "optimal_set_independent_audit",
        "status": "pass" if all(matches.values()) else "fail",
        "scope": "Independent verification of the frozen supplied-domain Latin optimal-set run.",
        "frozen_run": {
            "commit": "883da35809cb1a3828876f272f108ae103fdf98a",
            "directory": "results/optimal-set-secondary-v1-latin",
            "artifact_hashes": artifact_hashes,
            "input_sha256": artifact_hashes["input.json"],
            "result_sha256": artifact_hashes["result.json"],
        },
        "method": {
            "implementation": "Rebuilt streams, model counts, maps, scores, ratios, diagnostics, and links with independent code.",
            "reference_loader": "voynich.reference.load_reference_partitions",
            "secondary_module_imported": False,
            "secondary_scoring_helpers_imported": False,
            "raw_words_and_event_tables_published": False,
        },
        "reconstruction": {
            "stream_hashes_match": stream_matches,
            "model_hash": model_hash,
            "model_hash_expected": model_hash_expected,
            "model_hash_match": model_hash == model_hash_expected,
            "data_hashes": data_hashes,
            "data_hash_matches": data_match,
            "objective_domain_fingerprint": objective_fingerprint,
            "objective_domain_fingerprint_match": objective_fingerprint == input_record["objective_domain_fingerprint"],
            "training_word_count": len(train),
            "training_lexicon_type_count": len(lexicon),
            "validation_token_count": len(validation),
            "validation_type_count": len(cipher_counts),
            "validation_event_count_per_candidate": sum(
                count * (len(word) + 1) for word, count in cipher_counts.items()
            ),
        },
        "enumeration": {
            "fixed_unit_count": len(fixed),
            "free_units": ["c40"],
            "raw_product_bound": len(ALPHABET),
            "legal_completion_count": len(candidates),
            "capacity_pruned_letter_count": len(ALPHABET) - len(candidates),
            "legal_c40_values": [candidate["c40"] for candidate in candidates],
            "candidate_set_sha256": candidate_set_hash,
            "primary_target": target,
            "primary_scores_by_c40": {
                candidate["c40"]: primary_scores[index]
                for index, candidate in enumerate(candidates)
            },
            "matches_frozen": {
                "candidate_maps": matches["candidate_order_and_maps"],
                "candidate_set": matches["candidate_set"],
                "scores": matches["primary_scores"],
            },
        },
        "secondary": {
            "ratio_definition": "candidate likelihood divided by c40=j likelihood; alpha 0.1 is (10*c+1)/(10*t+28).",
            "candidates": frozen_ratio_rows,
            "maximizer_c40_values": [candidates[index]["c40"] for index in maximizers],
            "maximum_ratio": ratio_record(maximum),
            "maximum_log2_ratio": independent_log2_ratio,
            "maximum_log2_ratio_frozen": ranking["maximum_log2_ratio"],
            "matches_frozen": {
                "ratios": matches["secondary_ratios"],
                "maximizer": matches["secondary_maximizer"],
            },
        },
        "diagnostics": {
            "test_stream_hashes_match": {
                "plaintext_test": stream_matches["plaintext_test"],
                "cipher_test": stream_matches["cipher_test"],
            },
            "test_token_count": len(test),
            "test_character_count": sum(len(word) for word in test),
            "candidate_results": diagnostics,
            "matches_frozen": matches["diagnostics"],
            "uses_planted_key_for_diagnostics_only": True,
        },
        "certificate_and_queries": {
            "value_certificate": certificate,
            "checks": certificate_checks,
            "query_binding": query_binding,
        },
        "artifact_links": {
            "links": artifact_links,
            "all_links_valid": all(artifact_links.values()),
        },
        "provenance": {
            "code_source_count": len(input_record["code_hashes"]),
            "code_hashes_match": code_hash_matches,
            "code_hash_failures": code_hash_failures,
            "protocol_count": len(input_record["protocol_hashes"]),
            "protocol_hashes_match": protocol_hash_matches,
            "protocol_hash_failures": protocol_hash_failures,
            "source_count": len(input_record["source_hashes"]),
            "source_hashes_match": source_hash_matches,
            "source_hash_failures": source_hash_failures,
            "pinned_artifact_count": len(input_record["pinned_artifacts"]),
            "pinned_artifacts_match": pinned_hash_matches,
            "pinned_artifact_failures": pinned_hash_failures,
        },
        "checks": matches,
        "limitations": [
            "The check covers the supplied 45 fixed assignments and the one free c40 domain.",
            "It does not prove a map outside that domain or a manuscript solution.",
            "The test diagnostics use the planted synthetic key and are exploratory.",
        ],
    }
    return report


def write_exclusive(output: Path, report: dict[str, Any]) -> None:
    """Write one report and refuse to replace an existing file."""

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("xb") as handle:
        handle.write(canonical_bytes(report))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="repo-relative output JSON path",
    )
    args = parser.parse_args(argv)
    if args.output.is_absolute():
        parser.error("--output must be repo-relative")
    output = (ROOT / args.output).resolve()
    try:
        output.relative_to(ROOT)
    except ValueError:
        parser.error("--output must stay inside the repository")
    try:
        report = build_report()
        write_exclusive(output, report)
    except FileExistsError:
        parser.error("refuse to replace an existing output file")
    except OSError:
        parser.error("cannot read pinned inputs or write the output file")
    except Exception:
        parser.error("independent verification failed")
    print(json.dumps({"status": report["status"], "checks": report["checks"]}, sort_keys=True))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
