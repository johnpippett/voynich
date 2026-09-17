"""Exact secondary ranking for supplied substitution maps.

This module ranks only the candidate maps supplied by the caller.  It does not
check primary-score optimality or claim that the candidate set is complete.
The frozen character model is used as a deterministic secondary score.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping
from fractions import Fraction
import json
import math
from typing import Any

from voynich.substitution import (
    END_SYMBOL,
    START_SYMBOL,
    UNKNOWN_SYMBOL,
    LanguageModel,
    _context_for,
    _normalise_token,
)


Word = str | tuple[str, ...]
Capacity = int | None
Event = tuple[tuple[str, ...], str]


def _validate_capacity(capacity: Capacity) -> Capacity:
    if capacity is None:
        return None
    if isinstance(capacity, bool) or not isinstance(capacity, int):
        raise ValueError("capacity must be 1, 2, or None")
    if capacity not in (1, 2):
        raise ValueError("capacity must be 1, 2, or None")
    return capacity


def _validate_limit(value: int, field: str, *, allow_zero: bool) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field} must be an integer")
    minimum = 0 if allow_zero else 1
    if value < minimum:
        adjective = "non-negative" if allow_zero else "positive"
        raise ValueError(f"{field} must be a {adjective} integer")
    return value


def _validate_model(model: LanguageModel) -> None:
    if not isinstance(model, LanguageModel):
        raise TypeError("model must be a frozen substitution LanguageModel")
    if model.add_alpha != 0.1:
        raise ValueError("model.add_alpha must be exactly 0.1")
    if isinstance(model.order, bool) or not isinstance(model.order, int) or model.order < 0:
        raise ValueError("model.order must be a non-negative integer")
    controls = (model.start_symbol, model.end_symbol, model.unknown_symbol)
    if any(not isinstance(symbol, str) or not symbol for symbol in controls):
        raise ValueError("model control symbols must be non-empty strings")
    if len(set(controls)) != len(controls):
        raise ValueError("model control symbols must be unique")
    if model.start_symbol != START_SYMBOL or model.end_symbol != END_SYMBOL:
        raise ValueError("model control symbols do not match substitution semantics")
    if model.unknown_symbol != UNKNOWN_SYMBOL:
        raise ValueError("model unknown symbol does not match substitution semantics")
    if any(not isinstance(symbol, str) or not symbol for symbol in model.alphabet):
        raise ValueError("model.alphabet must contain non-empty strings")
    if len(set(model.alphabet)) != len(model.alphabet):
        raise ValueError("model.alphabet symbols must be unique")
    if set(model.alphabet).intersection({START_SYMBOL, END_SYMBOL, model.unknown_symbol}):
        raise ValueError("model.alphabet cannot contain model control symbols")
    expected_vocabulary = (
        *model.alphabet,
        model.unknown_symbol,
        model.end_symbol,
    )
    if tuple(model.vocabulary) != expected_vocabulary:
        raise ValueError("model.vocabulary does not match its alphabet and controls")
    if len(set(model.vocabulary)) != len(model.vocabulary):
        raise ValueError("model.vocabulary symbols must be unique")


def _normalise_counts(
    counts: Mapping[Word, int],
) -> dict[tuple[str, ...], int]:
    if not isinstance(counts, Mapping):
        raise TypeError("cipher_counts must be a mapping from words to counts")
    normalized: dict[tuple[str, ...], int] = {}
    for raw_word, weight in counts.items():
        word = _normalise_token(raw_word)
        if isinstance(weight, bool) or not isinstance(weight, int) or weight < 0:
            raise ValueError("cipher_counts values must be non-negative integers")
        normalized[word] = normalized.get(word, 0) + weight
    return dict(sorted(normalized.items()))


def _normalise_candidate_keys(
    candidate_keys: Iterable[Mapping[str, str]],
    cipher_symbols: tuple[str, ...],
    model: LanguageModel,
    capacity: Capacity,
) -> list[dict[str, str]]:
    try:
        raw_candidates = list(candidate_keys)
    except TypeError as exc:
        raise TypeError("candidate_keys must be an iterable of mappings") from exc
    cipher_set = set(cipher_symbols)
    alphabet_set = set(model.alphabet)
    normalized: list[dict[str, str]] = []
    for raw_key in raw_candidates:
        if not isinstance(raw_key, Mapping):
            raise TypeError("each candidate key must be a mapping")
        if set(raw_key) != cipher_set:
            raise ValueError(
                "each candidate key must contain every ciphertext symbol exactly once"
            )
        key: dict[str, str] = {}
        for cipher_symbol, plain_symbol in raw_key.items():
            if not isinstance(cipher_symbol, str) or not cipher_symbol:
                raise ValueError("candidate key symbols must be non-empty strings")
            if not isinstance(plain_symbol, str) or not plain_symbol:
                raise ValueError("candidate key values must be non-empty strings")
            if plain_symbol not in alphabet_set:
                raise ValueError("candidate key values must be in model.alphabet")
            key[cipher_symbol] = plain_symbol
        usage = Counter(key.values())
        if capacity is not None and any(
            count > capacity for count in usage.values()
        ):
            raise ValueError("candidate key exceeds plaintext preimage capacity")
        normalized.append(dict(sorted(key.items())))
    return normalized


def _model_context_maps(
    model: LanguageModel,
) -> tuple[dict[tuple[str, ...], dict[str, int]], dict[tuple[str, ...], int]]:
    legal_context_symbols = set(model.alphabet) | {
        model.start_symbol,
        model.unknown_symbol,
    }

    def decode_context(encoded_context: object, field: str, index: int) -> tuple[str, ...]:
        if not isinstance(encoded_context, str):
            raise ValueError(f"{field}[{index}] context must be a JSON array string")
        try:
            context_value = json.loads(encoded_context)
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ValueError(f"{field}[{index}] context is not valid JSON") from exc
        if type(context_value) is not list or not all(
            isinstance(symbol, str) for symbol in context_value
        ):
            raise ValueError(f"{field}[{index}] context must be a JSON array of strings")
        context = tuple(context_value)
        if len(context) != model.order:
            raise ValueError(
                f"{field}[{index}] context length must equal model.order"
            )
        for symbol in context:
            if symbol not in legal_context_symbols:
                raise ValueError(
                    f"{field}[{index}] context symbol is outside the model alphabet"
                )
        seen_history = False
        for symbol in context:
            if symbol == model.start_symbol:
                if seen_history:
                    raise ValueError(
                        f"{field}[{index}] START must be a context-prefix symbol"
                    )
            else:
                seen_history = True
        return context

    def pair_entry(entry: object, field: str, index: int) -> tuple[object, object]:
        if type(entry) not in (tuple, list) or len(entry) != 2:
            raise ValueError(f"{field}[{index}] must contain two fields")
        return entry[0], entry[1]

    counts: dict[tuple[str, ...], dict[str, int]] = {}
    try:
        count_rows = iter(model.context_counts)
    except TypeError as exc:
        raise ValueError("model.context_counts must be an iterable of rows") from exc
    for index, entry in enumerate(count_rows):
        encoded_context, rows = pair_entry(entry, "model.context_counts", index)
        context = decode_context(encoded_context, "model.context_counts", index)
        if context in counts:
            raise ValueError("model.context_counts contains a duplicate context")
        if isinstance(rows, (str, bytes, Mapping)):
            raise ValueError("model.context_counts rows must be arrays")
        try:
            row_entries = iter(rows)
        except TypeError as exc:
            raise ValueError("model.context_counts rows must be arrays") from exc
        row_map: dict[str, int] = {}
        for row_index, row in enumerate(row_entries):
            symbol, count = pair_entry(row, "model.context_counts row", row_index)
            if not isinstance(symbol, str) or symbol not in model.vocabulary:
                raise ValueError("model.context_counts contains an invalid target")
            if symbol in row_map:
                raise ValueError("model.context_counts contains a duplicate target")
            if isinstance(count, bool) or not isinstance(count, int) or count < 0:
                raise ValueError("model.context_counts contains an invalid count")
            row_map[symbol] = count
        counts[context] = row_map

    totals: dict[tuple[str, ...], int] = {}
    try:
        total_rows = iter(model.context_totals)
    except TypeError as exc:
        raise ValueError("model.context_totals must be an iterable of rows") from exc
    for index, entry in enumerate(total_rows):
        encoded_context, total = pair_entry(entry, "model.context_totals", index)
        context = decode_context(encoded_context, "model.context_totals", index)
        if context in totals:
            raise ValueError("model.context_totals contains a duplicate context")
        if isinstance(total, bool) or not isinstance(total, int) or total < 0:
            raise ValueError("model.context_totals contains an invalid total")
        totals[context] = total

    if set(counts) != set(totals):
        raise ValueError("model context count and total tables must have the same contexts")
    for context, rows in counts.items():
        if totals[context] != sum(rows.values()):
            raise ValueError("model context totals do not match context counts")

    metadata = (
        "training_word_count",
        "training_symbol_count",
        "unknown_training_symbols",
    )
    for field in metadata:
        value = getattr(model, field)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f"model.{field} must be a non-negative integer")
    if model.unknown_training_symbols > model.training_symbol_count:
        raise ValueError("model.unknown_training_symbols exceeds training symbols")
    if sum(totals.values()) != model.training_symbol_count + model.training_word_count:
        raise ValueError("model context totals do not match training counts")
    return counts, totals


def _event_histogram(
    counts: Mapping[tuple[str, ...], int],
    key: Mapping[str, str],
    model: LanguageModel,
) -> Counter[Event]:
    histogram: Counter[Event] = Counter()
    for word, weight in counts.items():
        mapped_word = tuple(key[symbol] for symbol in word)
        for position, target in enumerate((*mapped_word, END_SYMBOL)):
            context = _context_for(mapped_word, position, model.order)
            histogram[(context, target)] += weight
    return histogram


def _event_probability(
    event: Event,
    model: LanguageModel,
    context_counts: Mapping[tuple[str, ...], Mapping[str, int]],
    context_totals: Mapping[tuple[str, ...], int],
) -> Fraction:
    context, target = event
    event_count = context_counts.get(context, {}).get(target, 0)
    context_total = context_totals.get(context, 0)
    numerator = 10 * event_count + 1
    denominator = 10 * context_total + len(model.vocabulary)
    return Fraction(numerator, denominator)


def _fraction_bit_size(value: Fraction) -> int:
    return max(value.numerator.bit_length(), value.denominator.bit_length())


class _RatioLimitExceeded(Exception):
    pass


def _ratio_for_delta(
    delta: Mapping[Event, int],
    model: LanguageModel,
    context_counts: Mapping[tuple[str, ...], Mapping[str, int]],
    context_totals: Mapping[tuple[str, ...], int],
    max_ratio_bits: int,
) -> Fraction:
    ratio = Fraction(1, 1)
    for event in sorted(delta):
        amount = delta[event]
        if not amount:
            continue
        factor = _event_probability(
            event, model, context_counts, context_totals
        )
        if amount < 0:
            factor = 1 / factor
            amount = -amount
        for _ in range(amount):
            ratio *= factor
            if _fraction_bit_size(ratio) > max_ratio_bits:
                raise _RatioLimitExceeded
    return ratio


def _log2_fraction(value: Fraction) -> float:
    def log2_integer(integer: int) -> float:
        bit_length = integer.bit_length()
        shift = max(0, bit_length - 53)
        mantissa = integer >> shift
        return math.log2(mantissa) + shift

    return log2_integer(value.numerator) - log2_integer(value.denominator)


def _fraction_record(value: Fraction) -> dict[str, Any]:
    return {
        "numerator_hex": hex(value.numerator),
        "denominator_hex": hex(value.denominator),
        "numerator_bits": value.numerator.bit_length(),
        "denominator_bits": value.denominator.bit_length(),
    }


def _config(model: LanguageModel, capacity: Capacity, max_delta_events: int, max_ratio_bits: int) -> dict[str, Any]:
    return {
        "objective": "token-count-weighted frozen conditional character likelihood",
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
        "ratio_definition": (
            "candidate likelihood divided by the canonical first-candidate "
            "likelihood; alpha 0.1 is represented as (10*c+1)/(10*t+V)"
        ),
        "claims_global_optimality": False,
        "claims_candidate_set_complete": False,
    }


def _not_complete(
    config: dict[str, Any],
    candidate_results: list[dict[str, Any]],
    candidate_count: int,
    canonical_index: int | None,
    reason: str,
    failed_candidate_index: int | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "status": "not_complete",
        "reason": reason,
        "candidate_count": candidate_count,
        "canonical_candidate_index": canonical_index,
        "candidate_results": candidate_results,
        "maximizer_indices": [],
        "display_index": None,
        "display_key": None,
        "config": config,
        "claims_global_optimality": False,
        "claims_candidate_set_complete": False,
    }
    if failed_candidate_index is not None:
        result["failed_candidate_index"] = failed_candidate_index
    return result


def rank_secondary(
    model: LanguageModel,
    cipher_counts: Mapping[Word, int],
    candidate_keys: Iterable[Mapping[str, str]],
    *,
    capacity: Capacity = 1,
    max_delta_events: int = 4096,
    max_ratio_bits: int = 1_000_000,
) -> dict[str, Any]:
    """Rank supplied complete maps with exact frozen-model likelihood ratios."""

    _validate_model(model)
    context_counts, context_totals = _model_context_maps(model)
    capacity = _validate_capacity(capacity)
    max_delta_events = _validate_limit(
        max_delta_events, "max_delta_events", allow_zero=True
    )
    max_ratio_bits = _validate_limit(
        max_ratio_bits, "max_ratio_bits", allow_zero=False
    )
    normalized_counts = _normalise_counts(cipher_counts)
    cipher_symbols = tuple(
        sorted({symbol for word in normalized_counts for symbol in word})
    )
    normalized_keys = _normalise_candidate_keys(
        candidate_keys, cipher_symbols, model, capacity
    )
    config = _config(model, capacity, max_delta_events, max_ratio_bits)
    if not normalized_keys:
        return _not_complete(config, [], 0, None, "no_candidate_maps")

    canonical_index = min(
        range(len(normalized_keys)),
        key=lambda index: (
            tuple(normalized_keys[index][symbol] for symbol in cipher_symbols),
            index,
        ),
    )
    baseline_histogram = _event_histogram(
        normalized_counts,
        normalized_keys[canonical_index],
        model,
    )
    candidate_results: list[dict[str, Any]] = []
    ratios: dict[int, Fraction] = {}

    for index, key in enumerate(normalized_keys):
        histogram = _event_histogram(normalized_counts, key, model)
        delta = {
            event: histogram.get(event, 0) - baseline_histogram.get(event, 0)
            for event in set(histogram).union(baseline_histogram)
            if histogram.get(event, 0) != baseline_histogram.get(event, 0)
        }
        delta_event_count = sum(abs(amount) for amount in delta.values())
        if delta_event_count > max_delta_events:
            return _not_complete(
                config,
                candidate_results,
                len(normalized_keys),
                canonical_index,
                "max_delta_events",
                index,
            )
        try:
            ratio = _ratio_for_delta(
                delta,
                model,
                context_counts,
                context_totals,
                max_ratio_bits,
            )
        except _RatioLimitExceeded:
            return _not_complete(
                config,
                candidate_results,
                len(normalized_keys),
                canonical_index,
                "max_ratio_bits",
                index,
            )
        ratios[index] = ratio
        candidate_results.append(
            {
                "candidate_index": index,
                "key": dict(key),
                "event_count": sum(histogram.values()),
                "delta_event_count": delta_event_count,
                "likelihood_ratio": _fraction_record(ratio),
                "log2_ratio": _log2_fraction(ratio),
            }
        )

    maximum = max(ratios.values())
    maximizer_indices = [
        index for index in range(len(normalized_keys)) if ratios[index] == maximum
    ]
    display_index = min(
        maximizer_indices,
        key=lambda index: (
            tuple(normalized_keys[index][symbol] for symbol in cipher_symbols),
            index,
        ),
    )
    return {
        "status": "complete",
        "reason": "all_candidate_maps_scored",
        "candidate_count": len(normalized_keys),
        "canonical_candidate_index": canonical_index,
        "candidate_results": candidate_results,
        "maximizer_indices": maximizer_indices,
        "display_index": display_index,
        "display_key": dict(normalized_keys[display_index]),
        "maximum_likelihood_ratio": _fraction_record(maximum),
        "maximum_log2_ratio": _log2_fraction(maximum),
        "config": config,
        "claims_global_optimality": False,
        "claims_candidate_set_complete": False,
    }


__all__ = ["rank_secondary"]
