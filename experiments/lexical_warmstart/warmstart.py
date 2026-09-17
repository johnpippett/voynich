"""Synthetic exact lexical local search for a complete homophonic key.

This module starts from a caller-supplied total map. It improves the integer
weighted lexicon word-hit score with single-unit reassignments and two-unit
swaps. It does not search for a global optimum or use test or planted data.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping
from itertools import combinations
from typing import Any, TypeAlias

from experiments.homophonic.solver import (
    _normalise_alphabet,
    _normalise_cipher_counts,
    _normalise_lexicon,
    _score_key,
    _validate_capacity,
    _validate_initial_key,
)


Word: TypeAlias = str | tuple[str, ...]


def _validate_move_budget(move_budget: int) -> int:
    if (
        not isinstance(move_budget, int)
        or isinstance(move_budget, bool)
        or move_budget < 0
    ):
        raise ValueError("move_budget must be a non-negative integer")
    return move_budget


def _validate_trace_mode(trace_mode: str) -> str:
    if not isinstance(trace_mode, str):
        raise TypeError("trace_mode must be 'full' or 'summary'")
    if trace_mode not in ("full", "summary"):
        raise ValueError("trace_mode must be 'full' or 'summary'")
    return trace_mode


def _score_words(
    key: Mapping[str, str],
    words: Iterable[tuple[str, ...]],
    counts: Mapping[tuple[str, ...], int],
    lexicon: set[tuple[str, ...]],
) -> int:
    return sum(
        counts[word]
        for word in words
        if tuple(key[symbol] for symbol in word) in lexicon
    )


def _move_specs(
    key: Mapping[str, str],
    symbols: tuple[str, ...],
    alphabet: tuple[str, ...],
    capacity: int | None,
):
    usage = Counter(key.values())
    for symbol in symbols:
        old_value = key[symbol]
        for new_value in alphabet:
            if new_value == old_value:
                continue
            if capacity is not None and usage[new_value] >= capacity:
                continue
            candidate = dict(key)
            candidate[symbol] = new_value
            yield (
                "reassign",
                (symbol,),
                (old_value,),
                (new_value,),
                candidate,
            )
    for left, right in combinations(symbols, 2):
        left_value = key[left]
        right_value = key[right]
        if left_value == right_value:
            continue
        candidate = dict(key)
        candidate[left] = right_value
        candidate[right] = left_value
        yield (
            "swap",
            (left, right),
            (left_value, right_value),
            (right_value, left_value),
            candidate,
        )


def _move_delta(
    current_key: Mapping[str, str],
    candidate: Mapping[str, str],
    units: tuple[str, ...],
    incident: Mapping[str, tuple[tuple[str, ...], ...]],
    counts: Mapping[tuple[str, ...], int],
    lexicon: set[tuple[str, ...]],
) -> int:
    affected_words = tuple(
        sorted({
            word
            for unit in units
            for word in incident[unit]
        })
    )
    old_local = _score_words(current_key, affected_words, counts, lexicon)
    new_local = _score_words(candidate, affected_words, counts, lexicon)
    return new_local - old_local


def _move_record(
    iteration: int,
    key_before: Mapping[str, str],
    score_before: int,
    spec: tuple[str, tuple[str, ...], tuple[str, ...], tuple[str, ...], dict[str, str]],
    delta: int,
    *,
    selected: bool,
) -> dict[str, Any]:
    kind, units, from_values, to_values, candidate = spec
    return {
        "iteration": iteration,
        "kind": kind,
        "units": list(units),
        "from_values": list(from_values),
        "to_values": list(to_values),
        "key_before": dict(key_before),
        "candidate_key": dict(sorted(candidate.items())),
        "score_before": score_before,
        "score_after": score_before + delta,
        "delta": delta,
        "selected": selected,
    }


def lexical_local_search(
    ciphertext_counts: Mapping[Word, int],
    plaintext_lexicon: Iterable[Word],
    plaintext_alphabet: Iterable[str] | str,
    *,
    capacity: int | None = 1,
    initial_key: Mapping[str, str],
    move_budget: int = 0,
    trace_mode: str = "full",
) -> dict[str, Any]:
    """Improve one complete capacity-valid map with exact lexical moves.

    ``move_budget`` limits accepted improving moves. Each iteration evaluates
    every legal single reassignment and two-unit swap, then accepts one move
    with maximum positive score gain. Equal gains use the smallest complete
    key in sorted cipher-symbol order. The returned score is never certified
    as a global optimum. ``trace_mode='summary'`` keeps only aggregate
    candidate counts and accepted move records. The default ``'full'`` mode
    keeps every neighbor record.
    """

    capacity = _validate_capacity(capacity)
    if capacity not in (1, 2, None):
        raise ValueError("capacity must be 1, 2, or None")
    move_budget = _validate_move_budget(move_budget)
    trace_mode = _validate_trace_mode(trace_mode)
    if initial_key is None:
        raise TypeError("initial_key must be a total mapping")

    counts = _normalise_cipher_counts(ciphertext_counts)
    alphabet = _normalise_alphabet(plaintext_alphabet)
    lexicon, raw_count, unique_count, rejected_count = _normalise_lexicon(
        plaintext_lexicon,
        alphabet,
    )
    cipher_symbols = tuple(sorted({symbol for word in counts for symbol in word}))
    if capacity is not None and capacity * len(alphabet) < len(cipher_symbols):
        raise ValueError("capacity cannot support a total map for all cipher symbols")
    initial = _validate_initial_key(
        initial_key,
        cipher_symbols,
        alphabet,
        capacity,
    )
    if set(initial) != set(cipher_symbols):
        raise ValueError("initial_key must assign every ciphertext symbol exactly once")

    current_key = dict(sorted(initial.items()))
    current_score, current_hit_types = _score_key(current_key, counts, lexicon)
    initial_score = current_score

    common = {
        "config": {
            "objective": "integer weighted exact lexicon word hits",
            "mapping_kind": "one total cipher-unit to plaintext-letter map",
            "capacity": capacity,
            "move_budget": move_budget,
            "move_kinds": ["single_unit_reassignment", "two_unit_swap"],
            "selection": (
                "maximum positive score gain, then lexicographically smallest "
                "complete key"
            ),
            "tie_order": "sorted ciphertext-symbol order",
            "budget_definition": "maximum number of accepted improving moves",
            "initial_key_role": "caller-supplied complete warm-start map",
        },
        "cipher_alphabet": list(cipher_symbols),
        "plaintext_alphabet": list(alphabet),
        "initial_key": dict(current_key),
        "initial_score": initial_score,
        "capacity": capacity,
        "move_budget": move_budget,
        "trace_mode": trace_mode,
        "lexicon_raw_entry_count": raw_count,
        "lexicon_unique_normalized_count": unique_count,
        "lexicon_usable_count": len(lexicon),
        "lexicon_rejected_out_of_alphabet_count": rejected_count,
        "cipher_type_count": len(counts),
        "cipher_symbol_count": len(cipher_symbols),
        "scope_limits": [
            "The result uses only the supplied finite lexicon and ciphertext words.",
            "Word boundaries and cipher-unit symbols remain fixed.",
            "The map has no nulls, abbreviations, context, or per-word exceptions.",
            "The local search does not certify a global optimum.",
        ],
    }

    if not counts:
        return {
            **common,
            "status": "empty_input",
            "score_certified": False,
            "local_neighborhood_checked": False,
            "accepted_move_count": 0,
            "evaluation_count": 0,
            "hit_type_count": 0,
            "score": 0,
            "key": {},
            "accepted_moves": [],
            "evaluations": [],
            "trace_summary": {
                "iteration_count": 0,
                "candidate_count_total": 0,
                "accepted_map_count": 0,
                "selected_move_count": 0,
                "iterations": [],
            },
        }

    incident: dict[str, tuple[tuple[str, ...], ...]] = {}
    for symbol in cipher_symbols:
        incident[symbol] = tuple(
            word for word in counts if symbol in word
        )

    evaluations: list[dict[str, Any]] = []
    accepted_moves: list[dict[str, Any]] = []
    trace_iterations: list[dict[str, Any]] = []
    local_neighborhood_checked = False
    status = "move_budget_exhausted" if move_budget == 0 else "no_improving_move"

    for iteration in range(move_budget):
        key_before = dict(current_key)
        iteration_records: list[dict[str, Any]] = []
        best_record: dict[str, Any] | None = None
        best_spec = None
        best_score: int | None = None
        candidate_count = 0
        positive_candidate_count = 0

        for spec in _move_specs(
            current_key,
            cipher_symbols,
            alphabet,
            capacity,
        ):
            candidate = spec[4]
            delta = _move_delta(
                current_key,
                candidate,
                spec[1],
                incident,
                counts,
                lexicon,
            )
            candidate_count += 1
            if delta > 0:
                positive_candidate_count += 1
            if trace_mode == "full":
                iteration_records.append(
                    _move_record(
                        iteration,
                        key_before,
                        current_score,
                        spec,
                        delta,
                        selected=False,
                    )
                )
            score_after = current_score + delta
            if best_score is None or score_after > best_score:
                best_score = score_after
                best_spec = spec
            elif score_after == best_score:
                assert best_spec is not None
                candidate_order = tuple(
                    candidate[symbol] for symbol in cipher_symbols
                )
                best_order = tuple(
                    best_spec[4][symbol] for symbol in cipher_symbols
                )
                if candidate_order < best_order:
                    best_spec = spec

        if trace_mode == "full":
            evaluations.extend(iteration_records)
            if iteration_records:
                best_record = min(
                    (
                        record
                        for record in iteration_records
                        if record["score_after"] == best_score
                    ),
                    key=lambda record: tuple(
                        record["candidate_key"][symbol]
                        for symbol in cipher_symbols
                    ),
                )
        elif best_spec is not None:
            assert best_score is not None
            best_record = _move_record(
                iteration,
                key_before,
                current_score,
                best_spec,
                best_score - current_score,
                selected=False,
            )

        iteration_summary = {
            "iteration": iteration,
            "candidate_count": candidate_count,
            "positive_candidate_count": positive_candidate_count,
            "best_delta": (
                None if best_score is None else best_score - current_score
            ),
            "best_score_after": best_score,
            "selected": False,
        }
        if best_record is None:
            trace_iterations.append(iteration_summary)
            local_neighborhood_checked = True
            status = "no_improving_move"
            break
        assert best_score is not None
        if best_score <= current_score:
            trace_iterations.append(iteration_summary)
            local_neighborhood_checked = True
            status = "no_improving_move"
            break

        best_record["selected"] = True
        iteration_summary["selected"] = True
        trace_iterations.append(iteration_summary)
        accepted = dict(best_record)
        accepted_moves.append(accepted)
        current_key = dict(best_record["candidate_key"])
        current_score, current_hit_types = _score_key(current_key, counts, lexicon)
        if current_score != best_score:
            raise RuntimeError("incident delta disagrees with complete score")
        if len(accepted_moves) >= move_budget:
            status = "move_budget_exhausted"
            break
    else:
        if move_budget:
            status = "move_budget_exhausted"

    return {
        **common,
        "status": status,
        "score_certified": False,
        "local_neighborhood_checked": local_neighborhood_checked,
        "accepted_move_count": len(accepted_moves),
        "evaluation_count": sum(
            item["candidate_count"] for item in trace_iterations
        ),
        "hit_type_count": current_hit_types,
        "score": current_score,
        "key": dict(sorted(current_key.items())),
        "accepted_moves": accepted_moves,
        "evaluations": evaluations if trace_mode == "full" else [],
        "trace_summary": {
            "iteration_count": len(trace_iterations),
            "candidate_count_total": sum(
                item["candidate_count"] for item in trace_iterations
            ),
            "accepted_map_count": len(accepted_moves),
            "selected_move_count": sum(
                item["selected"] for item in trace_iterations
            ),
            "iterations": trace_iterations,
        },
    }


__all__ = ["lexical_local_search"]
