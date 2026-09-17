#!/usr/bin/env python3
"""Run bounded known-key lexicon controls."""

from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
import random
import signal
import string
import sys
import time
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[2]
LANGUAGES = ("latin_llct", "italian_old")
TOP_KS = (64, 256)
INITIAL_BUDGETS = (0, 1, 10)
ORDER_TUNING_BUDGET = 1000
ORDER_FALLBACK_BUDGET = 100
ORDER_TIME_CAP_SECONDS = 60.0
KEY_SEED = 500
PLAINTEXT_ALPHABET = string.ascii_lowercase
CIPHER_SYMBOLS = tuple(f"c{index:02d}" for index in range(26))
DEFAULT_OUTPUT = ROOT / "results" / "lexicon-controls" / "benchmark_controls.json"

for _path in (ROOT, ROOT / "src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))


class SearchTimeCap(Exception):
    """Stop one time-capped search case."""


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_json(value: object) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return _sha256_bytes(encoded)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _planted_key() -> tuple[dict[str, str], dict[str, str]]:
    letters = list(PLAINTEXT_ALPHABET)
    random.Random(KEY_SEED).shuffle(letters)
    cipher_to_plain = dict(zip(CIPHER_SYMBOLS, letters))
    plain_to_cipher = {plain: cipher for cipher, plain in cipher_to_plain.items()}
    return cipher_to_plain, plain_to_cipher


def _rank_types(words: list[str], top_k: int | None = None) -> list[tuple[str, int]]:
    counts = Counter(words)
    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return ranked if top_k is None else ranked[:top_k]


def _encrypt_counts(
    ranked_types: list[tuple[str, int]],
    plain_to_cipher: Mapping[str, str],
) -> dict[tuple[str, ...], int]:
    return {
        tuple(plain_to_cipher[letter] for letter in word): count
        for word, count in ranked_types
    }


def _objective_counts(
    cipher_counts: Mapping[tuple[str, ...], int],
) -> tuple[dict[tuple[str, ...], int], int, int, int]:
    num_types = len(cipher_counts)
    total_tokens = sum(cipher_counts.values())
    weighted = {
        word: count * num_types + total_tokens
        for word, count in cipher_counts.items()
    }
    denominator = 2 * num_types * total_tokens
    if num_types <= 0 or total_tokens <= 0:
        raise ValueError("selected validation types must contain at least one token")
    if sum(weighted.values()) != denominator:
        raise AssertionError("integer objective weights do not match denominator")
    return weighted, num_types, total_tokens, denominator


def _symbol_order(
    cipher_counts: Mapping[tuple[str, ...], int],
    weighted_counts: Mapping[tuple[str, ...], int],
    order_name: str,
) -> tuple[str, ...]:
    symbols = sorted({symbol for word in cipher_counts for symbol in word})
    if order_name == "lexical":
        return tuple(symbols)
    if order_name != "occurrence_weight":
        raise ValueError(f"unknown symbol order: {order_name}")
    occurrence_weight = {
        symbol: sum(
            weight for word, weight in weighted_counts.items() if symbol in word
        )
        for symbol in symbols
    }
    return tuple(sorted(symbols, key=lambda symbol: (-occurrence_weight[symbol], symbol)))


def _score_key(
    key: Mapping[str, str],
    cipher_counts: Mapping[tuple[str, ...], int],
    weighted_counts: Mapping[tuple[str, ...], int],
    lexicon: set[str],
) -> dict[str, int | float]:
    hit_types = 0
    hit_tokens = 0
    objective_score = 0
    for cipher_word, count in cipher_counts.items():
        decoded = "".join(key[symbol] for symbol in cipher_word)
        if decoded in lexicon:
            hit_types += 1
            hit_tokens += count
            objective_score += weighted_counts[cipher_word]
    return {
        "objective_score": objective_score,
        "hit_type_count": hit_types,
        "hit_token_count": hit_tokens,
    }


def _reference_test_accuracy(
    key: Mapping[str, str],
    test_types: list[tuple[str, int]],
    plain_to_cipher: Mapping[str, str],
) -> dict[str, int | float | None]:
    character_count = 0
    character_hits = 0
    unmapped_character_count = 0
    token_count = 0
    token_hits = 0
    unmapped_token_count = 0
    for plaintext, count in test_types:
        cipher_word = tuple(plain_to_cipher[letter] for letter in plaintext)
        decoded_symbols = [key.get(symbol) for symbol in cipher_word]
        unmapped_symbols = sum(symbol is None for symbol in decoded_symbols)
        token_count += count
        token_hits += count * (
            unmapped_symbols == 0
            and all(
                decoded == plaintext_symbol
                for decoded, plaintext_symbol in zip(decoded_symbols, plaintext)
            )
        )
        unmapped_token_count += count * (unmapped_symbols > 0)
        character_count += count * len(plaintext)
        unmapped_character_count += count * unmapped_symbols
        character_hits += count * sum(
            decoded_letter is not None and decoded_letter == plaintext_letter
            for decoded_letter, plaintext_letter in zip(decoded_symbols, plaintext)
        )
    return {
        "character_count": character_count,
        "character_hit_count": character_hits,
        "unmapped_character_count": unmapped_character_count,
        "mapped_character_count": character_count - unmapped_character_count,
        "character_accuracy": character_hits / character_count if character_count else None,
        "token_count": token_count,
        "token_hit_count": token_hits,
        "unmapped_token_count": unmapped_token_count,
        "fully_mapped_token_count": token_count - unmapped_token_count,
        "token_accuracy": token_hits / token_count if token_count else None,
    }


def _time_cap_handler(_signum: int, _frame: object) -> None:
    raise SearchTimeCap


def _solve_case(
    weighted_counts: Mapping[tuple[str, ...], int],
    lexicon: set[str],
    symbol_order: tuple[str, ...],
    node_budget: int,
    *,
    time_cap_seconds: float | None = None,
    fallback_on_timeout: bool = False,
) -> tuple[dict[str, Any] | None, float, int, bool, float | None]:
    started = time.perf_counter()
    timed_out = False
    fallback_seconds: float | None = None
    used_budget = node_budget
    result: dict[str, Any] | None

    if time_cap_seconds is not None and hasattr(signal, "setitimer"):
        previous_handler = signal.getsignal(signal.SIGALRM)
        signal.signal(signal.SIGALRM, _time_cap_handler)
        signal.setitimer(signal.ITIMER_REAL, time_cap_seconds)
    else:
        previous_handler = None

    try:
        try:
            result = _solve(
                weighted_counts,
                lexicon,
                symbol_order,
                node_budget,
            )
        except SearchTimeCap:
            timed_out = True
            if fallback_on_timeout:
                used_budget = ORDER_FALLBACK_BUDGET
                fallback_started = time.perf_counter()
                result = _solve(
                    weighted_counts,
                    lexicon,
                    symbol_order,
                    used_budget,
                )
                fallback_seconds = time.perf_counter() - fallback_started
            else:
                result = None
    finally:
        if time_cap_seconds is not None and hasattr(signal, "setitimer"):
            signal.setitimer(signal.ITIMER_REAL, 0.0)
            signal.signal(signal.SIGALRM, previous_handler)

    return result, time.perf_counter() - started, used_budget, timed_out, fallback_seconds


def _solve(
    weighted_counts: Mapping[tuple[str, ...], int],
    lexicon: set[str],
    symbol_order: tuple[str, ...],
    node_budget: int,
) -> dict[str, Any]:
    from experiments.lexicon.solver import solve_lexicon

    return solve_lexicon(
        weighted_counts,
        lexicon,
        PLAINTEXT_ALPHABET,
        node_budget=node_budget,
        symbol_order=symbol_order,
        bound_engine="reference",
    )


def _case_report(
    language: str,
    track: str,
    selected_type_count: int,
    order_name: str,
    node_budget: int,
    lexicon: set[str],
    cipher_counts: Mapping[tuple[str, ...], int],
    weighted_counts: Mapping[tuple[str, ...], int],
    denominator: int,
    planted_key: Mapping[str, str],
    reference_validation_types: list[tuple[str, int]],
    reference_test_types: list[tuple[str, int]],
    plain_to_cipher: Mapping[str, str],
    *,
    time_cap_seconds: float | None = None,
    fallback_on_timeout: bool = False,
) -> dict[str, object]:
    symbol_order = _symbol_order(cipher_counts, weighted_counts, order_name)
    result, runtime, used_budget, timed_out, fallback_seconds = _solve_case(
        weighted_counts,
        lexicon,
        symbol_order,
        node_budget,
        time_cap_seconds=time_cap_seconds,
        fallback_on_timeout=fallback_on_timeout,
    )

    base_report: dict[str, object] = {
        "language": language,
        "track": track,
        "selected_type_count": selected_type_count,
        "branch_order": order_name,
        "requested_node_budget": node_budget,
        "used_node_budget": used_budget,
        "time_cap_seconds": time_cap_seconds,
        "time_cap_hit": timed_out,
        "fallback_runtime_seconds": fallback_seconds,
        "runtime_seconds": runtime,
        "objective_denominator": denominator,
        "symbol_order_sha256": _sha256_json(symbol_order),
    }
    if result is None:
        base_report.update(
            {
                "status": "time_cap",
                "score_certified": None,
                "search_exhausted": None,
                "bound_engine": "reference",
                "nodes": None,
                "lower_bound": None,
                "upper_bound": None,
                "solver_score": None,
                "solver_hit_type_count": None,
                "true_planted_key_score": None,
                "true_planted_key_hit_type_count": None,
                "true_planted_key_hit_token_count": None,
                "returned_key_used_symbol_recovery": None,
                "returned_key_reference_validation_accuracy": None,
                "returned_key_reference_test_accuracy": None,
                "bounds_valid": False,
            }
        )
        return base_report

    # Evaluate the planted key only after the solver returns.
    planted = _score_key(planted_key, cipher_counts, weighted_counts, lexicon)
    returned = _score_key(result["key"], cipher_counts, weighted_counts, lexicon)
    used_symbols = {symbol for word in cipher_counts for symbol in word}
    recovered_symbols = sum(
        result["key"].get(symbol) == planted_key[symbol] for symbol in used_symbols
    )
    returned_key_recovery = {
        "used_symbol_count": len(used_symbols),
        "correct_symbol_count": recovered_symbols,
        "accuracy": recovered_symbols / len(used_symbols) if used_symbols else None,
    }
    returned_test_accuracy = _reference_test_accuracy(
        result["key"],
        reference_test_types,
        plain_to_cipher,
    )
    returned_validation_accuracy = _reference_test_accuracy(
        result["key"],
        reference_validation_types,
        plain_to_cipher,
    )
    lower_bound = result["lower_bound"]
    upper_bound = result["upper_bound"]
    if not isinstance(lower_bound, int) or not isinstance(upper_bound, int):
        raise AssertionError("solver bounds must be integers")
    if lower_bound > upper_bound:
        raise AssertionError("solver lower bound exceeds upper bound")
    if int(planted["objective_score"]) > upper_bound:
        raise AssertionError("solver upper bound excludes the planted key")

    base_report.update(
        {
            "status": result["status"],
            "score_certified": result["score_certified"],
            "search_exhausted": result["search_exhausted"],
            "bound_engine": result["config"]["bound_engine"],
            "nodes": result["nodes"],
            "lower_bound": lower_bound,
            "upper_bound": upper_bound,
            "solver_score": result["score"],
            "solver_hit_type_count": result["hit_type_count"],
            "true_planted_key_score": planted["objective_score"],
            "true_planted_key_hit_type_count": planted["hit_type_count"],
            "true_planted_key_hit_token_count": planted["hit_token_count"],
            "returned_key_used_symbol_recovery": returned_key_recovery,
            "returned_key_reference_validation_accuracy": returned_validation_accuracy,
            "returned_key_reference_test_accuracy": returned_test_accuracy,
            "returned_key_score": returned["objective_score"],
            "bounds_valid": {
                "lower_bound_le_upper_bound": lower_bound <= upper_bound,
                "planted_score_le_upper_bound": int(planted["objective_score"]) <= upper_bound,
            },
        }
    )
    return base_report


def _corpus_report(
    language: str,
    data: Mapping[str, object],
    planted_key: Mapping[str, str],
    plain_to_cipher: Mapping[str, str],
) -> tuple[dict[str, object], list[dict[str, object]]]:
    words = data["words"]
    if not isinstance(words, dict):
        raise ValueError(f"reference data for {language} has no words mapping")
    train_words = words["train"]
    validation_words = words["validation"]
    test_words = words["test"]
    if not all(isinstance(partition, list) for partition in (train_words, validation_words, test_words)):
        raise ValueError(f"reference data for {language} has invalid partitions")
    train_lexicon = set(train_words)
    validation_counter = Counter(validation_words)
    validation_types = sorted(validation_counter.items(), key=lambda item: (-item[1], item[0]))
    test_counter = Counter(test_words)
    test_types = sorted(test_counter.items(), key=lambda item: (-item[1], item[0]))
    expected_test_types = {"latin_llct": 1820, "italian_old": 6196}
    if len(validation_counter) != expected_test_types[language]:
        raise ValueError(
            f"unexpected {language} reference-validation type count: "
            f"expected {expected_test_types[language]}, got {len(validation_counter)}"
        )
    metadata = data["metadata"]
    if not isinstance(metadata, dict):
        raise ValueError(f"reference data for {language} has no metadata")
    source_files = metadata.get("source_files")
    if not isinstance(source_files, dict):
        raise ValueError(f"reference data for {language} has no source hashes")

    corpus = {
        "train_token_count": len(train_words),
        "train_type_count": len(train_lexicon),
        "validation_token_count": len(validation_words),
        "validation_type_count": len(validation_counter),
        "test_token_count": len(test_words),
        "test_type_count": len(test_counter),
        "train_lexicon_sha256": _sha256_json(sorted(train_lexicon)),
        "validation_counts_sha256": _sha256_json(sorted(validation_counter.items())),
        "test_counts_sha256": _sha256_json(sorted(test_counter.items())),
        "source_file_sha256": {
            name: details["sha256"]
            for name, details in sorted(source_files.items())
            if isinstance(details, dict) and isinstance(details.get("sha256"), str)
        },
    }
    cases: list[dict[str, object]] = []
    tracks: dict[str, list[tuple[str, int]]] = {
        f"validation_top{top_k}": _rank_types(validation_words, top_k)
        for top_k in TOP_KS
    }
    tracks["reference_validation_full"] = validation_types
    corpus["tracks"] = {}
    for track, ranked in tracks.items():
        cipher_counts = _encrypt_counts(ranked, plain_to_cipher)
        weighted_counts, num_types, total_tokens, denominator = _objective_counts(cipher_counts)
        track_record = {
            "source_partition": "validation",
            "selected_type_count": num_types,
            "selected_token_count": total_tokens,
            "cipher_symbol_count": len({symbol for word in cipher_counts for symbol in word}),
            "cipher_counts_sha256": _sha256_json(
                sorted((list(word), count) for word, count in cipher_counts.items())
            ),
            "objective_denominator": denominator,
        }
        corpus_tracks = corpus["tracks"]
        if not isinstance(corpus_tracks, dict):
            raise AssertionError("corpus tracks must be a mapping")
        corpus_tracks[track] = track_record

        top_track = track.startswith("validation_top")
        for budget in INITIAL_BUDGETS:
            cases.append(
                _case_report(
                    language,
                    track,
                    num_types,
                    "lexical",
                    budget,
                    train_lexicon,
                    cipher_counts,
                    weighted_counts,
                    denominator,
                    planted_key,
                    validation_types,
                    test_types,
                    plain_to_cipher,
                    time_cap_seconds=ORDER_TIME_CAP_SECONDS if not top_track else None,
                )
            )
        if top_track:
            for order_name in ("lexical", "occurrence_weight"):
                cases.append(
                    _case_report(
                        language,
                        track,
                        num_types,
                        order_name,
                        ORDER_TUNING_BUDGET,
                        train_lexicon,
                        cipher_counts,
                        weighted_counts,
                        denominator,
                        planted_key,
                        validation_types,
                        test_types,
                        plain_to_cipher,
                        time_cap_seconds=ORDER_TIME_CAP_SECONDS,
                        fallback_on_timeout=True,
                    )
                )
    return corpus, cases


def run_benchmark() -> dict[str, object]:
    from voynich.reference import load_reference_partitions

    planted_key, plain_to_cipher = _planted_key()
    data = load_reference_partitions(ROOT)
    manifest_path = ROOT / "data" / "reference_manifest.json"
    solver_path = ROOT / "experiments" / "lexicon" / "solver.py"
    reference_path = ROOT / "src" / "voynich" / "reference.py"
    script_path = Path(__file__).resolve()
    corpora: dict[str, object] = {}
    cases: list[dict[str, object]] = []
    for language in LANGUAGES:
        corpus, language_cases = _corpus_report(
            language,
            data[language],
            planted_key,
            plain_to_cipher,
        )
        corpora[language] = corpus
        cases.extend(language_cases)

    return {
        "status": "bounded_known_key_lexicon_control",
        "configuration": {
            "languages": list(LANGUAGES),
            "plaintext_alphabet": "a-z",
            "cipher_symbol_format": "c00..c25",
            "cipher_symbol_count": len(CIPHER_SYMBOLS),
            "planted_key_seed": KEY_SEED,
            "selection": "validation word types ranked by descending count, then lexical order",
            "top_k": list(TOP_KS),
            "initial_node_budgets": list(INITIAL_BUDGETS),
            "full_reference_test_type_counts": {
                "latin_llct": 1820,
                "italian_old": 6196,
            },
            "full_reference_test_source_partition": "validation",
            "returned_key_test_accuracy_source_partition": "test",
            "full_reference_test_node_budgets": list(INITIAL_BUDGETS),
            "full_reference_test_time_cap_seconds": ORDER_TIME_CAP_SECONDS,
            "order_tuning_node_budget": ORDER_TUNING_BUDGET,
            "order_fallback_node_budget": ORDER_FALLBACK_BUDGET,
            "order_time_cap_seconds": ORDER_TIME_CAP_SECONDS,
            "branch_orders": {
                "lexical": "sorted ciphertext symbols",
                "occurrence_weight": "descending sum of objective weights for types containing the symbol, then symbol",
            },
            "objective": "equal token and type hit rates",
            "integer_weight_formula": "count*num_types+total_tokens",
            "integer_denominator": "2*num_types*total_tokens",
            "search_mode": "cold start",
            "bound_engine": "reference",
            "initial_key_passed_to_solver": False,
            "planted_key_used_for_search_order": False,
        },
        "inputs": {
            "reference_manifest_sha256": _sha256_file(manifest_path),
            "solver_sha256": _sha256_file(solver_path),
            "reference_api_sha256": _sha256_file(reference_path),
            "benchmark_script_sha256": _sha256_file(script_path),
        },
        "corpora": corpora,
        "cases": cases,
        "limits": [
            "The solver sees only the finite training lexicon and encrypted validation word counts.",
            "The planted key is scored after each search and is never passed to the solver.",
            "The run does not start an unbounded 26-symbol search.",
            "A finite positive control does not validate a Voynich key or language.",
            "Source corpora and word arrays are not written to this result.",
        ],
    }


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    report = run_benchmark()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    try:
        display_output = str(args.output.resolve().relative_to(ROOT))
    except ValueError:
        display_output = str(args.output)
    print(json.dumps({"status": report["status"], "output": display_output}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
