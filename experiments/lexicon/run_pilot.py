#!/usr/bin/env python3
"""Run a bounded finite-lexicon pilot on reference or manuscript words."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import random
import string
import sys
from typing import Any, Callable, Iterable, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from experiments.lexicon.ambiguity import preserved_hit_completions
from experiments.lexicon.solver import solve_lexicon
from voynich.corpus import parse_ivtff
from voynich.groups import group_id, grouping_config, split_bucket, split_name
from voynich.reference import load_reference_partitions


ALPHABET = string.ascii_lowercase
CIPHER_SYMBOLS = tuple(f"c{index:02d}" for index in range(26))
SOURCE_NAMES = ("ZL3b-n.txt", "IT2a-n.txt")
LANGUAGES = ("latin_llct", "italian_old")
KINDS = ("reference", "manuscript")
FILTER_REASONS = (
    "not_paragraph",
    "no_accepted_tokens",
    "excluded_tokens",
    "diagram_interruption",
    "eligible",
)


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


def non_negative_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("must be a non-negative integer") from error
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be a non-negative integer")
    return parsed


def count_words(words: Iterable[str | Sequence[str]]) -> Counter[tuple[str, ...]]:
    return Counter(
        tuple(word) if not isinstance(word, str) else tuple(word)
        for word in words
    )


def encrypt_words(
    words: Iterable[str],
    plaintext_to_cipher: Mapping[str, str],
) -> list[tuple[str, ...]]:
    return [
        tuple(plaintext_to_cipher[symbol] for symbol in word)
        for word in words
    ]


def seeded_encryption_key(seed: int) -> dict[str, str]:
    """Create the planted plaintext-to-ciphertext permutation."""

    plaintext_symbols = list(ALPHABET)
    random.Random(seed).shuffle(plaintext_symbols)
    cipher_to_plain = dict(zip(CIPHER_SYMBOLS, plaintext_symbols))
    return {
        plaintext: cipher
        for cipher, plaintext in cipher_to_plain.items()
    }


def objective_weights(
    counts: Mapping[tuple[str, ...], int],
) -> tuple[dict[tuple[str, ...], int], int, int, int | None]:
    """Return count*T+N weights and the 2*T*N denominator.

    ``T`` is the number of word types and ``N`` is the number of word
    tokens. The weight sum equals the denominator when the input is nonempty.
    """

    token_count = sum(counts.values())
    type_count = len(counts)
    weights = {
        word: count * type_count + token_count
        for word, count in counts.items()
    }
    denominator = 2 * token_count * type_count if token_count and type_count else None
    if denominator is not None and sum(weights.values()) != denominator:
        raise AssertionError("integer objective weights do not match denominator")
    return weights, token_count, type_count, denominator


def branch_symbol_order(
    counts: Mapping[tuple[str, ...], int],
    *,
    weights: Mapping[tuple[str, ...], int] | None = None,
) -> tuple[str, ...]:
    """Order symbols by descending weight of the word types that contain them."""

    if weights is None:
        weights, _tokens, _types, _denominator = objective_weights(counts)
    symbols = sorted({symbol for word in counts for symbol in word})
    symbol_weight = {
        symbol: sum(weight for word, weight in weights.items() if symbol in word)
        for symbol in symbols
    }
    return tuple(sorted(symbols, key=lambda symbol: (-symbol_weight[symbol], symbol)))


def safe_rate(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def lexicon_hits(
    words: Sequence[tuple[str, ...]],
    key: Mapping[str, str],
    lexicon: set[str],
) -> dict[str, Any]:
    """Score token and type hits without repairing missing key units."""

    counts = Counter(words)
    token_count = len(words)
    type_count = len(counts)
    token_hits = 0
    type_hits = 0
    mapped_token_count = 0
    mapped_type_count = 0
    unmapped_token_count = 0
    unmapped_type_count = 0
    unmapped_symbol_occurrences = 0
    for word, count in counts.items():
        missing = sum(symbol not in key for symbol in word)
        if missing:
            unmapped_token_count += count
            unmapped_type_count += 1
            unmapped_symbol_occurrences += missing * count
            continue
        mapped_token_count += count
        mapped_type_count += 1
        decoded = "".join(key[symbol] for symbol in word)
        if decoded in lexicon:
            token_hits += count
            type_hits += 1
    return {
        "token_count": token_count,
        "type_count": type_count,
        "token_hits": token_hits,
        "type_hits": type_hits,
        "token_hit_rate": safe_rate(token_hits, token_count),
        "type_hit_rate": safe_rate(type_hits, type_count),
        "mapped_token_count": mapped_token_count,
        "mapped_type_count": mapped_type_count,
        "unmapped_token_count": unmapped_token_count,
        "unmapped_type_count": unmapped_type_count,
        "unmapped_symbol_occurrences": unmapped_symbol_occurrences,
    }


def exact_reference_test_score(
    plaintext_words: Sequence[str],
    plaintext_to_cipher: Mapping[str, str],
    fitted_key: Mapping[str, str],
    lexicon: set[str],
) -> dict[str, Any]:
    """Score every encrypted reference test word and compare known plaintext."""

    encrypted = encrypt_words(plaintext_words, plaintext_to_cipher)
    hits = lexicon_hits(encrypted, fitted_key, lexicon)
    exact_character_correct = 0
    total_character_units = 0
    exact_word_correct = 0
    fully_mapped_token_count = 0
    unmapped_token_count = 0
    unmapped_types: set[tuple[str, ...]] = set()
    unmapped_symbol_occurrences = 0
    for plaintext, cipher_word in zip(plaintext_words, encrypted):
        missing = sum(symbol not in fitted_key for symbol in cipher_word)
        total_character_units += len(cipher_word)
        unmapped_symbol_occurrences += missing
        if missing:
            unmapped_token_count += 1
            unmapped_types.add(cipher_word)
        else:
            fully_mapped_token_count += 1
        word_exact = missing == 0
        for cipher_symbol, plaintext_symbol in zip(cipher_word, plaintext):
            decoded_symbol = fitted_key.get(cipher_symbol)
            if decoded_symbol is None:
                word_exact = False
            elif decoded_symbol == plaintext_symbol:
                exact_character_correct += 1
            else:
                word_exact = False
        if word_exact:
            exact_word_correct += 1
    oracle_inverse = {cipher: plain for plain, cipher in plaintext_to_cipher.items()}
    key_symbols = set(fitted_key)
    exact_key_correct = sum(
        fitted_key[symbol] == oracle_inverse[symbol]
        for symbol in key_symbols
        if symbol in oracle_inverse
    )
    return {
        "lexicon_hits": hits,
        "exact_character_correct": exact_character_correct,
        "total_character_units": total_character_units,
        "exact_character_accuracy": safe_rate(
            exact_character_correct, total_character_units
        ),
        "exact_word_correct": exact_word_correct,
        "total_word_count": len(plaintext_words),
        "exact_word_accuracy": safe_rate(exact_word_correct, len(plaintext_words)),
        "fully_mapped_token_count": fully_mapped_token_count,
        "unmapped_token_count": unmapped_token_count,
        "unmapped_type_count": len(unmapped_types),
        "unmapped_symbol_occurrences": unmapped_symbol_occurrences,
        "key_exact_correct": exact_key_correct,
        "key_exact_total": len(key_symbols),
        "key_exact_accuracy": safe_rate(exact_key_correct, len(key_symbols)),
        "key_recovery_scope": "reference test plaintext and fitted key symbols only",
    }


def verify_pinned_source(project_root: Path, source: str) -> dict[str, str]:
    manifest_path = project_root / "data" / "source_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected = next(
        entry["sha256"]
        for entry in manifest["sources"]
        if entry["path"] == f"data/raw/{source}"
    )
    source_path = project_root / "data" / "raw" / source
    actual = sha256_path(source_path)
    if actual != expected:
        raise ValueError("The manuscript source does not match its pinned hash.")
    return {
        "source_sha256": actual,
        "source_manifest_sha256": sha256_path(manifest_path),
    }


def reference_metadata(data: Mapping[str, Any]) -> dict[str, Any]:
    """Return reference extraction metadata without the extracted word lists."""

    metadata = data["metadata"]
    return {
        "reference_manifest_sha256": metadata["reference_manifest_sha256"],
        "normalization": metadata["normalization"],
        "source_files": metadata["source_files"],
        "document_split": metadata["document_split"],
        "split_counts": metadata["split_counts"],
        "duplicate_or_empty_exclusions": metadata["duplicate_or_empty_exclusions"],
        "limit": metadata["limit"],
    }


def _empty_filter_counts() -> dict[str, dict[str, int]]:
    return {
        reason: {"records": 0, "accepted_words": 0, "excluded_tokens": 0}
        for reason in FILTER_REASONS
    }


def load_manuscript_partitions(
    project_root: Path,
    source: str,
) -> dict[str, Any]:
    """Load the complete v3 P-record filter used by the manuscript pilot."""

    hashes = verify_pinned_source(project_root, source)
    source_path = project_root / "data" / "raw" / source
    partitions: dict[str, list[str]] = {split: [] for split in ("train", "validation", "test")}
    groups_by_split: dict[str, set[str]] = {
        split: set() for split in partitions
    }
    filter_counts = _empty_filter_counts()
    for record in parse_ivtff(source_path, uncertain_spaces="split"):
        if not record["kind"].startswith("P"):
            reason = "not_paragraph"
        elif not record["tokens"]:
            reason = "no_accepted_tokens"
        elif record["excluded_tokens"]:
            reason = "excluded_tokens"
        elif any(marker in record["text_raw"] for marker in ("<->", "<~>")):
            reason = "diagram_interruption"
        else:
            reason = "eligible"
        filter_counts[reason]["records"] += 1
        filter_counts[reason]["accepted_words"] += len(record["tokens"])
        filter_counts[reason]["excluded_tokens"] += record["excluded_tokens"]
        if reason != "eligible":
            continue
        group = group_id(record["folio"])
        split = split_name(split_bucket(group))
        partitions[split].extend(record["tokens"])
        groups_by_split[split].add(group)
    if any(not words for words in partitions.values()):
        raise ValueError("Every manuscript partition must contain eligible words.")
    grouping = grouping_config()
    manifest_path = project_root / grouping["manifest_path"]
    actual_manifest_sha256 = sha256_path(manifest_path)
    if actual_manifest_sha256 != grouping["manifest_sha256"]:
        raise ValueError("The bifolio manifest does not match the v3 grouping hash.")
    expected_source = grouping["source_sha256"][f"data/raw/{source}"]
    if hashes["source_sha256"] != expected_source:
        raise ValueError("The manuscript source does not match the v3 grouping hash.")
    return {
        "partitions": partitions,
        "groups_by_split": groups_by_split,
        "filter_counts": filter_counts,
        "hashes": hashes,
        "bifolio_manifest_sha256": actual_manifest_sha256,
        "grouping": grouping,
    }


def fit_ciphertext(
    ciphertext_counts: Mapping[tuple[str, ...], int],
    lexicon: Iterable[str],
    *,
    node_budget: int,
    bound_engine: str = "bitset",
) -> dict[str, Any]:
    """Fit the baseline solver without an oracle key or warm start."""

    counts = dict(ciphertext_counts)
    weights, _tokens, _types, _denominator = objective_weights(counts)
    order = branch_symbol_order(counts, weights=weights)
    return solve_lexicon(
        weights,
        lexicon,
        ALPHABET,
        node_budget=node_budget,
        symbol_order=order,
        bound_engine=bound_engine,
    )


def solver_public_result(result: Mapping[str, Any]) -> dict[str, Any]:
    fields = (
        "status",
        "score_certified",
        "search_exhausted",
        "feasible",
        "nodes",
        "pruned_nodes",
        "frontier_node_count",
        "lower_bound",
        "upper_bound",
        "score",
        "hit_type_count",
        "cipher_alphabet",
        "plaintext_alphabet",
        "candidate_count_total",
        "pattern_compatible_type_count",
        "missing_candidate_count",
        "lexicon_raw_entry_count",
        "lexicon_unique_normalized_count",
        "lexicon_usable_count",
        "lexicon_rejected_out_of_alphabet_count",
        "cipher_type_count",
        "total_weight",
        "infeasibility_certified",
    )
    public = {field: result.get(field) for field in fields}
    public["config"] = dict(result.get("config", {}))
    public["config"].pop("initial_key_role", None)
    return public


def score_proof(
    solver_result: Mapping[str, Any],
    objective: Mapping[str, Any],
) -> dict[str, Any]:
    feasible = solver_result.get("feasible")
    derived_score = objective.get("score_from_key")
    solver_score = solver_result.get("score")
    if feasible and solver_score != derived_score:
        raise AssertionError(
            "solver score does not match the score of the frozen fitted key"
        )
    return {
        "solver_score": solver_score,
        "lower_bound": solver_result.get("lower_bound"),
        "upper_bound": solver_result.get("upper_bound"),
        "score_certified": solver_result.get("score_certified"),
        "derived_score_from_key": derived_score,
        "derived_score_matches_solver": (
            solver_score == derived_score
            if feasible
            else None
        ),
        "interpretation": (
            "Bounds prove the optimum objective score only when score_certified is true."
        ),
    }


def objective_summary(
    counts: Mapping[tuple[str, ...], int],
    key: Mapping[str, str],
    lexicon: set[str],
) -> dict[str, Any]:
    weights, token_count, type_count, denominator = objective_weights(counts)
    hits = lexicon_hits(list(Counter(counts).elements()), key, lexicon)
    hit_weight_sum = sum(
        weights[word]
        for word in counts
        if set(word).issubset(key)
        and "".join(key[symbol] for symbol in word) in lexicon
    )
    score_from_key = hits["token_hits"] * type_count + hits["type_hits"] * token_count
    if hit_weight_sum != score_from_key:
        raise AssertionError("derived objective score does not match hit weights")
    return {
        "weight_formula": "count*T+N",
        "normalization_formula": "2*T*N",
        "T_type_count": type_count,
        "N_token_count": token_count,
        "denominator": denominator,
        "weights_total": sum(weights.values()),
        "weights_match_denominator": (
            sum(weights.values()) == denominator if denominator is not None else None
        ),
        "score_from_key": score_from_key,
        "normalized_score": (
            score_from_key / denominator if denominator is not None else None
        ),
        "fit_hits": {
            "token_hits": hits["token_hits"],
            "type_hits": hits["type_hits"],
            "token_hit_rate": hits["token_hit_rate"],
            "type_hit_rate": hits["type_hit_rate"],
        },
    }


def ambiguity_summary(
    counts: Mapping[tuple[str, ...], int],
    lexicon: set[str],
    key: Mapping[str, str],
    solver_result: Mapping[str, Any],
) -> dict[str, Any] | None:
    if not solver_result.get("feasible"):
        return None
    weights, _tokens, _types, _denominator = objective_weights(counts)
    ambiguity = preserved_hit_completions(weights, lexicon, ALPHABET, key)
    ambiguity["optimal_key_count_lower_bound"] = (
        ambiguity["keys_preserving_current_hits"]
        if solver_result.get("score_certified")
        else None
    )
    ambiguity["interpretation"] = (
        "A count of one does not prove a unique key. The count is a lower bound "
        "on keys that preserve the current positive-weight hits."
    )
    return ambiguity


def code_hashes(project_root: Path) -> dict[str, str]:
    paths = [
        project_root / "experiments/lexicon/run_pilot.py",
        project_root / "experiments/lexicon/solver.py",
        project_root / "experiments/lexicon/ambiguity.py",
        project_root / "experiments/lexicon/bitset_bound.py",
        project_root / "src/voynich/corpus.py",
        project_root / "src/voynich/reference.py",
        project_root / "src/voynich/groups.py",
    ]
    return {
        str(path.relative_to(project_root)): sha256_path(path)
        for path in paths
    }


def freeze_key_then_score(
    key_path: Path,
    key_record: Mapping[str, Any],
    scorer: Callable[[], dict[str, Any]],
) -> tuple[str, dict[str, Any]]:
    """Write the key record before calling the validation or test scorer."""

    key_bytes = canonical_bytes(key_record)
    key_path.write_bytes(key_bytes)
    return sha256_bytes(key_bytes), scorer()


def output_key_path(output_path: Path) -> Path:
    return output_path.with_suffix(".keys.json")


def refuse_existing_outputs(output_path: Path, key_path: Path) -> None:
    if output_path.exists() or key_path.exists():
        raise FileExistsError(
            "A result or key file exists. Select a new output path."
        )


def reference_counts_metadata(data: Mapping[str, Any]) -> dict[str, Any]:
    return {
        split: {
            "token_count": len(data["words"][split]),
            "type_count": len(set(data["words"][split])),
        }
        for split in ("train", "validation", "test")
    }


def run_reference(
    project_root: Path,
    language: str,
    source: str,
    node_budget: int,
    seed: int,
    output_path: Path,
    bound_engine: str = "bitset",
) -> dict[str, Any]:
    data = load_reference_partitions(project_root)[language]
    lexicon = set(data["words"]["train"])
    plaintext_to_cipher = seeded_encryption_key(seed)
    validation_cipher = encrypt_words(data["words"]["validation"], plaintext_to_cipher)
    fit_counts = count_words(validation_cipher)
    solver_result = fit_ciphertext(
        fit_counts,
        lexicon,
        node_budget=node_budget,
        bound_engine=bound_engine,
    )
    key = solver_result.get("key", {})
    if solver_result.get("feasible") and set(key) != set(solver_result["cipher_alphabet"]):
        raise ValueError("The solver returned an incomplete fitted key.")
    key_record = {
        "kind": "reference",
        "language": language,
        "source": None,
        "seed": seed,
        "encryption_seed": seed,
        "bound_engine": bound_engine,
        "fit_scope": "all reference validation words encrypted with a seeded c00..c25 permutation",
        "solver_status": solver_result["status"],
        "key": dict(sorted(key.items())),
    }

    def score() -> dict[str, Any]:
        fit_objective = objective_summary(fit_counts, key, lexicon)
        test_score = exact_reference_test_score(
            data["words"]["test"], plaintext_to_cipher, key, lexicon
        )
        return {
            "fit_objective": fit_objective,
            "test_score": test_score,
        }

    key_path = output_key_path(output_path)
    key_hash, scores = freeze_key_then_score(key_path, key_record, score)
    oracle_key_hash = canonical_hash(plaintext_to_cipher)
    source_hashes = {
        name: metadata["sha256"]
        for name, metadata in data["metadata"]["source_files"].items()
    }
    objective = scores["fit_objective"]
    return {
        "status": "reference_pilot",
        "kind": "reference",
        "language": language,
        "source": None,
        "seed": seed,
        "encryption_seed": seed,
        "node_budget": node_budget,
        "bound_engine": bound_engine,
        "fit_scope": "All reference validation words are encrypted. The train words form the lexicon.",
        "reference_partitions": reference_counts_metadata(data),
        "reference_metadata": reference_metadata(data),
        "encryption": {
            "plaintext_alphabet": ALPHABET,
            "cipher_symbols": list(CIPHER_SYMBOLS),
            "method": "seeded permutation from plaintext symbols to tuple c00..c25",
            "seed": seed,
            "oracle_key_sha256": oracle_key_hash,
            "oracle_key_role": "encryption and post-search reference accuracy only",
        },
        "fit_input": {
            "token_count": len(validation_cipher),
            "type_count": len(fit_counts),
            "cipher_unit": "tuple of c00..c25 symbols",
        },
        "solver": solver_public_result(solver_result),
        "score_proof": score_proof(solver_result, objective),
        "objective": objective,
        "ambiguity": ambiguity_summary(fit_counts, lexicon, key, solver_result),
        "reference_accuracy": scores["test_score"],
        "key_record_sha256": key_hash,
        "input_sha256": {
            "reference_manifest": data["metadata"]["reference_manifest_sha256"],
            "reference_sources": source_hashes,
        },
        "code_sha256": code_hashes(project_root),
        "limits": [
            "The solver receives encrypted validation counts and the train-only lexicon.",
            "The planted key is not a solver argument, branch-order input, or tuning value.",
            "Reference accuracy is a known-control measure and does not describe manuscript evidence.",
            "Unmapped units are counted. The runner does not repair a key.",
        ],
    }


def run_manuscript(
    project_root: Path,
    language: str,
    source: str,
    node_budget: int,
    seed: int,
    output_path: Path,
    bound_engine: str = "bitset",
) -> dict[str, Any]:
    reference = load_reference_partitions(project_root)[language]
    lexicon = set(reference["words"]["train"])
    manuscript = load_manuscript_partitions(project_root, source)
    partitions = manuscript["partitions"]
    fit_counts = count_words(partitions["train"])
    solver_result = fit_ciphertext(
        fit_counts,
        lexicon,
        node_budget=node_budget,
        bound_engine=bound_engine,
    )
    key = solver_result.get("key", {})
    if solver_result.get("feasible") and set(key) != set(solver_result["cipher_alphabet"]):
        raise ValueError("The solver returned an incomplete fitted key.")
    key_record = {
        "kind": "manuscript",
        "language": language,
        "source": source,
        "seed": None,
        "encryption_seed": None,
        "bound_engine": bound_engine,
        "fit_scope": "all eligible v3 manuscript TRAIN words",
        "solver_status": solver_result["status"],
        "key": dict(sorted(key.items())),
    }

    def score() -> dict[str, Any]:
        return {
            split: lexicon_hits(
                [tuple(word) for word in partitions[split]], key, lexicon
            )
            for split in ("train", "validation", "test")
        }

    key_path = output_key_path(output_path)
    key_hash, scores = freeze_key_then_score(key_path, key_record, score)
    objective = objective_summary(fit_counts, key, lexicon)
    grouping = manuscript["grouping"]
    group_counts = {
        split: len(manuscript["groups_by_split"][split])
        for split in ("train", "validation", "test")
    }
    partition_counts = {
        split: {
            "token_count": len(partitions[split]),
            "type_count": len(set(partitions[split])),
            "group_count": group_counts[split],
        }
        for split in ("train", "validation", "test")
    }
    source_key = f"data/raw/{source}"
    return {
        "status": "manuscript_pilot_not_decipherment",
        "kind": "manuscript",
        "language": language,
        "source": source,
        "seed": None,
        "encryption_seed": None,
        "node_budget": node_budget,
        "bound_engine": bound_engine,
        "fit_scope": "All eligible v3 manuscript TRAIN words. The reference train words form the lexicon.",
        "reference_lexicon": {
            "language": language,
            "partition": "train",
            "token_count": len(reference["words"]["train"]),
            "type_count": len(lexicon),
            "reference_manifest_sha256": reference["metadata"]["reference_manifest_sha256"],
        },
        "reference_metadata": reference_metadata(reference),
        "manuscript_partitions": partition_counts,
        "sample_filter": {
            "sequential_categories": list(FILTER_REASONS),
            "counts": manuscript["filter_counts"],
            "policy": "Complete nonempty P records without excluded tokens or <-> and <~> diagram interruptions.",
            "parser": {
                "function": "voynich.corpus.parse_ivtff",
                "uncertain_spaces": "split",
                "record_scope": "records whose kind starts with P",
                "diagram_interruption_markers": ["<->", "<~>"],
                "split_assignment": "group_id -> split_bucket -> split_name",
            },
        },
        "grouping": {
            "version": grouping["version"],
            "manifest_sha256": grouping["manifest_sha256"],
            "split_hash_salt": grouping["split_hash_salt"],
            "group_count": grouping["group_count"],
            "split_group_counts": group_counts,
            "observed_eligible_group_count": len(
                set().union(*manuscript["groups_by_split"].values())
            ),
            "groups_without_eligible_paragraphs": sorted(
                set(grouping["folio_map"].values())
                - set().union(*manuscript["groups_by_split"].values()),
                key=int,
            ),
            "group_key": grouping["group_key"],
            "independent_conservation_verification": grouping[
                "independent_conservation_verification"
            ],
        },
        "solver": solver_public_result(solver_result),
        "score_proof": score_proof(solver_result, objective),
        "objective": objective,
        "ambiguity": ambiguity_summary(fit_counts, lexicon, key, solver_result),
        "scores": scores,
        "key_record_sha256": key_hash,
        "input_sha256": {
            "source": manuscript["hashes"]["source_sha256"],
            "source_manifest": manuscript["hashes"]["source_manifest_sha256"],
            "bifolio_manifest": manuscript["bifolio_manifest_sha256"],
            "source_manifest_entry": grouping["source_sha256"][source_key],
            "reference_manifest": reference["metadata"]["reference_manifest_sha256"],
        },
        "code_sha256": code_hashes(project_root),
        "limits": [
            "This run tests one fixed injective key, raw symbol units, and fixed word boundaries.",
            "The report gives lexicon score evidence. It does not claim key recovery, language identification, or decipherment.",
            "Unmapped units are counted. The runner does not repair a key.",
            "A budget stop does not certify the optimum unless the solver reports equal bounds.",
        ],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kind", choices=KINDS, required=True)
    parser.add_argument("--language", choices=LANGUAGES, required=True)
    parser.add_argument(
        "--source",
        choices=SOURCE_NAMES,
        default=SOURCE_NAMES[0],
        help="Pinned IVTFF source for manuscript runs; default: ZL3b-n.txt; ignored for reference runs.",
    )
    parser.add_argument(
        "--node-budget",
        type=non_negative_int,
        required=True,
        help="Maximum solver nodes for both run kinds.",
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--seed",
        type=int,
        default=500,
        help="Reference encryption seed (ignored for deterministic manuscript runs).",
    )
    parser.add_argument(
        "--bound-engine",
        choices=("reference", "bitset"),
        default="bitset",
        help="Solver bound implementation; default: bitset.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    output_path = args.output if args.output.is_absolute() else ROOT / args.output
    key_path = output_key_path(output_path)
    refuse_existing_outputs(output_path, key_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if args.kind == "reference":
        report = run_reference(
            ROOT,
            args.language,
            args.source,
            args.node_budget,
            args.seed,
            output_path,
            args.bound_engine,
        )
    else:
        report = run_manuscript(
            ROOT,
            args.language,
            args.source,
            args.node_budget,
            args.seed,
            output_path,
            args.bound_engine,
        )
    output_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    try:
        display_path = output_path.relative_to(ROOT)
    except ValueError:
        display_path = output_path
    print(display_path)


if __name__ == "__main__":
    main()
