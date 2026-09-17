"""Deterministic homophonic annealing for finite warm-start keys.

The prototype maps each caller-supplied cipher unit to one plaintext letter.
The ``capacity`` argument limits how many cipher units can share a letter.
The search minimizes a character n-gram negative log probability on the
caller-supplied encrypted fit words. It has no held-out or reference-key path.

This is a heuristic lower-bound warm start for an exact solver. It makes no
decoding or language-identification claim.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping
import json
import math
import random
from typing import Any

from voynich.substitution import LanguageModel, fit_language_model


EncryptedWord = tuple[str, ...]
PlaintextToken = str | tuple[str, ...]
MODEL_CONTROL_SYMBOLS = {"<BOS>", "<EOS>", "<UNK>"}
DEFAULT_ALPHABET = "abcdefghijklmnopqrstuvwxyz"
DEFAULT_ORDER = 3
DEFAULT_ADD_ALPHA = 0.1
DEFAULT_ITERATIONS = 2_000
DEFAULT_RESTARTS = 8
DEFAULT_SEED = 408


def _validate_capacity(capacity: int | None) -> int | None:
    if capacity is None:
        return None
    if not isinstance(capacity, int) or isinstance(capacity, bool) or capacity < 1:
        raise ValueError("capacity must be a positive integer or None")
    return capacity


def _normalise_alphabet(alphabet: Iterable[str] | str | None) -> tuple[str, ...] | None:
    if alphabet is None:
        return None
    values = tuple(alphabet) if isinstance(alphabet, str) else tuple(alphabet)
    if not values or any(
        not isinstance(symbol, str) or len(symbol) != 1 for symbol in values
    ):
        raise ValueError("plaintext_alphabet must contain single-character symbols")
    if len(set(values)) != len(values):
        raise ValueError("plaintext_alphabet symbols must be unique")
    return tuple(sorted(values))


def _normalise_encrypted_words(words: Iterable[EncryptedWord]) -> tuple[EncryptedWord, ...]:
    if isinstance(words, (str, bytes)):
        raise TypeError("encrypted_fit_words must contain tuple[str, ...] words")
    normalized: list[EncryptedWord] = []
    try:
        iterator = iter(words)
    except TypeError as exc:
        raise TypeError("encrypted_fit_words must be iterable") from exc
    for word in iterator:
        if not isinstance(word, tuple):
            raise TypeError("each encrypted word must be a tuple of units")
        if any(not isinstance(unit, str) or not unit for unit in word):
            raise ValueError("cipher units must be non-empty strings")
        if MODEL_CONTROL_SYMBOLS.intersection(word):
            raise ValueError("cipher units cannot use model control symbols")
        normalized.append(word)
    return tuple(normalized)


def _cipher_units(words: tuple[EncryptedWord, ...]) -> tuple[str, ...]:
    return tuple(sorted({unit for word in words for unit in word}))


def _context_for(
    token: tuple[str, ...],
    position: int,
    order: int,
    model: LanguageModel,
) -> tuple[str, ...]:
    if order == 0:
        return ()
    prefix_length = max(0, order - position)
    history = token[max(0, position - order) : position]
    return (model.start_symbol,) * prefix_length + history


def _event_counts(
    words: tuple[EncryptedWord, ...],
    model: LanguageModel,
) -> tuple[tuple[tuple[str, ...], str | None, int], ...]:
    counts: Counter[tuple[tuple[str, ...], str | None]] = Counter()
    for word in words:
        for position in range(len(word) + 1):
            context = _context_for(word, position, model.order, model)
            target = word[position] if position < len(word) else None
            counts[(context, target)] += 1
    return tuple(
        (context, target, count)
        for (context, target), count in sorted(
            counts.items(), key=lambda item: (repr(item[0][0]), repr(item[0][1]))
        )
    )


def _validate_key(
    key: Mapping[str, str],
    cipher_units: tuple[str, ...],
    alphabet: tuple[str, ...],
    capacity: int | None,
) -> dict[str, str]:
    if not isinstance(key, Mapping):
        raise TypeError("key must map cipher units to plaintext letters")
    normalized = dict(key)
    expected = set(cipher_units)
    if set(normalized) != expected:
        missing = sorted(expected.difference(normalized))
        extra = sorted(set(normalized).difference(expected))
        raise ValueError(f"key coverage mismatch; missing={missing}, extra={extra}")
    alphabet_set = set(alphabet)
    if any(
        not isinstance(cipher_unit, str)
        or not isinstance(plain_symbol, str)
        or plain_symbol not in alphabet_set
        for cipher_unit, plain_symbol in normalized.items()
    ):
        raise ValueError("key symbols must be strings and values must be in the alphabet")
    if capacity is not None:
        counts = Counter(normalized.values())
        if any(count > capacity for count in counts.values()):
            raise ValueError("key exceeds plaintext-letter capacity")
    return dict(sorted(normalized.items()))


class _EventScorer:
    """Score events with cached public language-model tables."""

    def __init__(self, model: LanguageModel) -> None:
        self.model = model
        self.context_counts = {
            tuple(json.loads(context)): dict(rows)
            for context, rows in model.context_counts
        }
        self.context_totals = {
            tuple(json.loads(context)): total
            for context, total in model.context_totals
        }

    def event_score(
        self,
        event: tuple[tuple[str, ...], str | None, int],
        key: Mapping[str, str],
    ) -> float:
        context, target, count = event
        mapped_context = tuple(
            unit
            if unit in {self.model.start_symbol, self.model.end_symbol}
            else key[unit]
            for unit in context
        )
        mapped_target = self.model.end_symbol if target is None else key[target]
        counts = self.context_counts.get(mapped_context, {})
        total = self.context_totals.get(mapped_context, 0)
        probability = (counts.get(mapped_target, 0) + self.model.add_alpha) / (
            total + self.model.add_alpha * len(self.model.vocabulary)
        )
        return -math.log2(probability) * count


def _score_details(
    negative_log2_probability: float,
    words: tuple[EncryptedWord, ...],
    cipher_units: tuple[str, ...],
    key: Mapping[str, str],
) -> dict[str, Any]:
    predicted_symbols = sum(len(word) + 1 for word in words)
    bits_per_symbol = (
        negative_log2_probability / predicted_symbols if predicted_symbols else None
    )
    return {
        "negative_log2_probability": negative_log2_probability,
        "bits_per_symbol": bits_per_symbol,
        "perplexity": 2.0**bits_per_symbol if bits_per_symbol is not None else None,
        "word_count": len(words),
        "predicted_symbols": predicted_symbols,
        "cipher_unit_count": len(cipher_units),
        "mapped_unit_count": len(set(cipher_units).intersection(key)),
        "missing_unit_count": len(set(cipher_units).difference(key)),
        "key_coverage": (
            len(set(cipher_units).intersection(key)) / len(cipher_units)
            if cipher_units
            else 0.0
        ),
    }


def score_homophonic_key(
    encrypted_fit_words: Iterable[EncryptedWord],
    model: LanguageModel,
    key: Mapping[str, str],
    *,
    capacity: int | None = None,
) -> dict[str, Any]:
    """Score a complete homophonic key with the supplied fitted model."""

    if not isinstance(model, LanguageModel):
        raise TypeError("model must be a LanguageModel")
    capacity = _validate_capacity(capacity)
    words = _normalise_encrypted_words(encrypted_fit_words)
    cipher_units = _cipher_units(words)
    normalized_key = _validate_key(key, cipher_units, model.alphabet, capacity)
    events = _event_counts(words, model)
    event_scorer = _EventScorer(model)
    total = math.fsum(
        event_scorer.event_score(event, normalized_key) for event in events
    )
    return _score_details(total, words, cipher_units, normalized_key)


class _IncrementalScorer:
    """Update only n-gram events touched by a proposed unit assignment."""

    def __init__(
        self,
        events: tuple[tuple[tuple[str, ...], str | None, int], ...],
        model: LanguageModel,
    ) -> None:
        self.events = events
        self.model = model
        self.event_scorer = _EventScorer(model)
        self.affected: dict[str, set[int]] = defaultdict(set)
        for index, (context, target, _count) in enumerate(events):
            for unit in context:
                if unit not in {model.start_symbol, model.end_symbol}:
                    self.affected[unit].add(index)
            if target is not None:
                self.affected[target].add(index)
        self.contributions = [0.0] * len(events)
        self.total = 0.0

    def initialize(self, key: Mapping[str, str]) -> None:
        self.contributions = [
            self.event_scorer.event_score(event, key) for event in self.events
        ]
        self.total = math.fsum(self.contributions)

    def trial(
        self,
        key: Mapping[str, str],
        changed_units: Iterable[str],
    ) -> tuple[set[int], list[float], float]:
        indices: set[int] = set()
        for unit in changed_units:
            indices.update(self.affected.get(unit, ()))
        ordered = sorted(indices)
        new_contributions = [
            self.event_scorer.event_score(self.events[index], key)
            for index in ordered
        ]
        old_total = math.fsum(self.contributions[index] for index in ordered)
        delta = math.fsum(new_contributions) - old_total
        return set(ordered), new_contributions, delta

    def commit(self, indices: set[int], new_contributions: list[float]) -> None:
        ordered = sorted(indices)
        old_total = math.fsum(self.contributions[index] for index in ordered)
        for index, contribution in zip(ordered, new_contributions):
            self.contributions[index] = contribution
        self.total += math.fsum(new_contributions) - old_total


def _initial_key(
    cipher_units: tuple[str, ...],
    alphabet: tuple[str, ...],
    capacity: int | None,
    rng: random.Random,
) -> dict[str, str]:
    if capacity is None:
        return {unit: rng.choice(alphabet) for unit in cipher_units}
    slots = [letter for letter in alphabet for _ in range(capacity)]
    rng.shuffle(slots)
    return dict(zip(cipher_units, slots[: len(cipher_units)], strict=True))


def _propose_move(
    key: Mapping[str, str],
    cipher_units: tuple[str, ...],
    alphabet: tuple[str, ...],
    capacity: int | None,
    rng: random.Random,
) -> tuple[dict[str, str], tuple[str, ...]]:
    candidate = dict(key)
    if len(cipher_units) >= 2 and rng.random() < 0.5:
        first, second = rng.sample(list(cipher_units), 2)
        candidate[first], candidate[second] = candidate[second], candidate[first]
        return candidate, (first, second)

    unit = rng.choice(list(cipher_units))
    current = candidate[unit]
    counts = Counter(candidate.values())
    choices = [
        letter
        for letter in alphabet
        if letter != current and (capacity is None or counts[letter] < capacity)
    ]
    if not choices:
        return candidate, ()
    candidate[unit] = rng.choice(choices)
    return candidate, (unit,)


def _key_tie_order(key: Mapping[str, str], cipher_units: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(key[unit] for unit in cipher_units)


def anneal_homophonic(
    encrypted_fit_words: Iterable[EncryptedWord],
    train_words: Iterable[PlaintextToken],
    *,
    plaintext_alphabet: Iterable[str] | str | None = DEFAULT_ALPHABET,
    capacity: int | None = 1,
    order: int = DEFAULT_ORDER,
    add_alpha: float = DEFAULT_ADD_ALPHA,
    iterations: int = DEFAULT_ITERATIONS,
    restarts: int = DEFAULT_RESTARTS,
    seed: int = DEFAULT_SEED,
    start_temperature: float = 1.0,
) -> dict[str, Any]:
    """Fit a character model and return a deterministic heuristic key search."""

    capacity = _validate_capacity(capacity)
    if not isinstance(iterations, int) or isinstance(iterations, bool) or iterations < 0:
        raise ValueError("iterations must be a non-negative integer")
    if not isinstance(restarts, int) or isinstance(restarts, bool) or restarts < 1:
        raise ValueError("restarts must be a positive integer")
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise ValueError("seed must be an integer")
    if not math.isfinite(start_temperature) or start_temperature < 0:
        raise ValueError("start_temperature must be finite and non-negative")
    declared_alphabet = _normalise_alphabet(plaintext_alphabet)
    words = _normalise_encrypted_words(encrypted_fit_words)
    model = fit_language_model(
        train_words,
        order=order,
        add_alpha=add_alpha,
        alphabet=declared_alphabet,
    )
    alphabet = model.alphabet
    if any(len(symbol) != 1 for symbol in alphabet):
        raise ValueError("the fitted plaintext alphabet must contain single characters")
    cipher_units = _cipher_units(words)
    if not alphabet and cipher_units:
        raise ValueError("plaintext alphabet must not be empty when units are present")
    if capacity is not None and len(cipher_units) > capacity * len(alphabet):
        raise ValueError("cipher units exceed finite plaintext-letter capacity")

    config = {
        "mapping_kind": "cipher-unit_to_plaintext-letter",
        "key_direction": "cipher_unit_to_plaintext_symbol",
        "capacity": capacity,
        "order": model.order,
        "add_alpha": model.add_alpha,
        "plaintext_alphabet": list(model.alphabet),
        "alphabet_source": model.alphabet_source,
        "start_temperature": start_temperature,
        "temperature_schedule": (
            "Linear decrease to zero; temperature is scaled by predicted positions, including EOS."
        ),
        "objective": (
            "negative log2 conditional character probability with fixed word boundaries"
        ),
        "model_training": "caller-supplied train_words only",
        "fit_scoring": "caller-supplied encrypted_fit_words only",
        "word_boundaries": "preserved; no cross-word transitions",
        "initialization": "seeded deterministic random feasible maps",
        "moves": ["swap two unit assignments", "reassign one unit if capacity allows"],
        "heuristic_role": "feasible warm-start lower bound; never an exact-solver prune",
    }
    budget = {
        "iterations_per_restart": iterations,
        "restarts": restarts,
        "declared_move_budget": iterations * restarts,
        "proposed_moves": 0,
        "accepted_moves": 0,
        "completed_restarts": 0,
    }

    if not cipher_units:
        empty_details = score_homophonic_key(words, model, {})
        return {
            "status": "empty_input" if not words else "empty_units",
            "capacity": capacity,
            "seed": seed,
            "budget": budget,
            "config": config,
            "key": {},
            "score": empty_details["negative_log2_probability"],
            "score_details": empty_details,
            "search": {
                "restarts_completed": 0,
                "best_incremental_score": empty_details[
                    "negative_log2_probability"
                ],
                "full_score": empty_details["negative_log2_probability"],
                "full_score_verified": True,
            },
        }

    events = _event_counts(words, model)
    scorer = _IncrementalScorer(events, model)
    rng = random.Random(seed)
    predicted_symbols = sum(len(word) + 1 for word in words)
    temperature_scale = max(1, predicted_symbols)
    best_key: dict[str, str] | None = None
    best_score = math.inf
    best_tie: tuple[str, ...] | None = None
    restart_best_scores: list[float] = []

    for _restart in range(restarts):
        current_key = _initial_key(cipher_units, alphabet, capacity, rng)
        scorer.initialize(current_key)
        current_score = scorer.total
        restart_best = current_score
        current_tie = _key_tie_order(current_key, cipher_units)
        if (
            current_score < best_score
            or (current_score == best_score and (best_tie is None or current_tie < best_tie))
        ):
            best_score = current_score
            best_key = dict(current_key)
            best_tie = current_tie

        for iteration in range(iterations):
            candidate, changed_units = _propose_move(
                current_key,
                cipher_units,
                alphabet,
                capacity,
                rng,
            )
            if not changed_units:
                continue
            budget["proposed_moves"] += 1
            indices, new_contributions, delta = scorer.trial(candidate, changed_units)
            fraction = iteration / max(1, iterations - 1)
            temperature = start_temperature * temperature_scale * (1.0 - fraction)
            accept = delta <= 0.0
            if not accept and temperature > 0.0:
                accept = rng.random() < math.exp(-delta / temperature)
            if not accept:
                continue
            scorer.commit(indices, new_contributions)
            current_key = candidate
            current_score = scorer.total
            budget["accepted_moves"] += 1
            restart_best = min(restart_best, current_score)
            candidate_tie = _key_tie_order(current_key, cipher_units)
            if (
                current_score < best_score
                or (
                    current_score == best_score
                    and (best_tie is None or candidate_tie < best_tie)
                )
            ):
                best_score = current_score
                best_key = dict(current_key)
                best_tie = candidate_tie
        restart_best_scores.append(restart_best)
        budget["completed_restarts"] += 1

    if best_key is None:
        raise RuntimeError("annealing did not produce a feasible key")
    best_key = dict(sorted(best_key.items()))

    verification_scorer = _IncrementalScorer(events, model)
    verification_scorer.initialize(best_key)
    full_details = score_homophonic_key(
        words,
        model,
        best_key,
        capacity=capacity,
    )
    incremental_score = verification_scorer.total
    full_score = full_details["negative_log2_probability"]
    full_score_verified = math.isclose(
        incremental_score,
        full_score,
        rel_tol=0.0,
        abs_tol=1e-9,
    )
    if not full_score_verified:
        raise AssertionError("incremental and full n-gram scores differ")
    search_score_verified = math.isclose(best_score, full_score, rel_tol=1e-12, abs_tol=1e-8)
    if not search_score_verified:
        raise AssertionError("search-accumulated and full n-gram scores differ")

    return {
        "status": "ok",
        "capacity": capacity,
        "seed": seed,
        "budget": budget,
        "config": config,
        "key": best_key,
        "score": full_score,
        "score_details": full_details,
        "search": {
            "restarts_completed": restarts,
            "restart_best_scores": restart_best_scores,
            "selected_best_score": best_score,
            "best_incremental_score": incremental_score,
            "full_score": full_score,
            "full_score_verified": full_score_verified,
            "search_accumulated_score_verified": search_score_verified,
            "search_score_absolute_error": abs(best_score - full_score),
            "search_score_tolerance": {"relative": 1e-12, "absolute": 1e-8},
        },
    }


__all__ = [
    "anneal_homophonic",
    "fit_language_model",
    "score_homophonic_key",
]
