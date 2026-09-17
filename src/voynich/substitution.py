"""Bounded monoalphabetic substitution search over fixed word boundaries."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
import json
import math
import random
from typing import Any, Iterable, Mapping, Sequence


START_SYMBOL = "<BOS>"
END_SYMBOL = "<EOS>"
UNKNOWN_SYMBOL = "<UNK>"
DEFAULT_ORDER = 3
DEFAULT_ADD_ALPHA = 0.1
DEFAULT_SEED = 408

Token = str | tuple[str, ...]


def _context_key(context: tuple[str, ...]) -> str:
    return json.dumps(list(context), ensure_ascii=False, separators=(",", ":"))


def _normalise_token(token: Token) -> tuple[str, ...]:
    if isinstance(token, str):
        symbols = tuple(token)
    elif isinstance(token, tuple) and all(isinstance(symbol, str) for symbol in token):
        symbols = token
    else:
        raise TypeError("each token must be a string or tuple[str, ...]")
    if any(not symbol for symbol in symbols):
        raise ValueError("token symbols must be non-empty strings")
    reserved = {START_SYMBOL, END_SYMBOL, UNKNOWN_SYMBOL}
    if any(symbol in reserved for symbol in symbols):
        raise ValueError("token symbols cannot use model control symbols")
    return symbols


def _normalise_tokens(tokens: Iterable[Token]) -> list[tuple[str, ...]]:
    if isinstance(tokens, str):
        return [_normalise_token(tokens)]
    return [_normalise_token(token) for token in tokens]


def _normalise_alphabet(alphabet: Iterable[str] | str | None) -> tuple[str, ...] | None:
    if alphabet is None:
        return None
    values = tuple(alphabet) if isinstance(alphabet, str) else tuple(alphabet)
    if not all(isinstance(symbol, str) and symbol for symbol in values):
        raise ValueError("alphabet symbols must be non-empty strings")
    if len(set(values)) != len(values):
        raise ValueError("alphabet symbols must be unique")
    reserved = {START_SYMBOL, END_SYMBOL, UNKNOWN_SYMBOL}
    if reserved.intersection(values):
        raise ValueError("alphabet cannot contain model control symbols")
    return tuple(sorted(values))


def _context_for(sequence: tuple[str, ...], position: int, order: int) -> tuple[str, ...]:
    if order == 0:
        return ()
    prefix_length = max(0, order - position)
    history = sequence[max(0, position - order) : position]
    return (START_SYMBOL,) * prefix_length + history


@dataclass(frozen=True)
class LanguageModel:
    """Frozen conditional character n-gram model with fixed word boundaries."""

    order: int
    add_alpha: float
    alphabet: tuple[str, ...]
    vocabulary: tuple[str, ...]
    start_symbol: str
    end_symbol: str
    unknown_symbol: str
    context_counts: tuple[tuple[str, tuple[tuple[str, int], ...]], ...]
    context_totals: tuple[tuple[str, int], ...]
    unigram_counts: tuple[tuple[str, int], ...]
    training_word_count: int
    training_symbol_count: int
    unknown_training_symbols: int
    alphabet_source: str
    definition: str

    @property
    def context_count_map(self) -> dict[str, dict[str, int]]:
        return {key: dict(rows) for key, rows in self.context_counts}

    @property
    def context_total_map(self) -> dict[str, int]:
        return dict(self.context_totals)

    @property
    def unigram_count_map(self) -> dict[str, int]:
        return dict(self.unigram_counts)

    def probability(self, context: tuple[str, ...], target: str) -> float:
        """Return the smoothed conditional probability for one prediction."""

        if target not in self.vocabulary:
            target = self.unknown_symbol
        key = _context_key(context)
        counts = self.context_count_map.get(key, {})
        total = self.context_total_map.get(key, 0)
        return (counts.get(target, 0) + self.add_alpha) / (
            total + self.add_alpha * len(self.vocabulary)
        )

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable model description."""

        return {
            "order": self.order,
            "add_alpha": self.add_alpha,
            "alphabet": list(self.alphabet),
            "vocabulary": list(self.vocabulary),
            "start_symbol": self.start_symbol,
            "end_symbol": self.end_symbol,
            "unknown_symbol": self.unknown_symbol,
            "context_counts": {
                key: dict(rows) for key, rows in self.context_counts
            },
            "context_totals": dict(self.context_totals),
            "unigram_counts": dict(self.unigram_counts),
            "training_word_count": self.training_word_count,
            "training_symbol_count": self.training_symbol_count,
            "unknown_training_symbols": self.unknown_training_symbols,
            "alphabet_source": self.alphabet_source,
            "definition": self.definition,
        }


def fit_language_model(
    words: Iterable[Token],
    order: int = DEFAULT_ORDER,
    add_alpha: float = DEFAULT_ADD_ALPHA,
    alphabet: Iterable[str] | str | None = None,
) -> LanguageModel:
    """Fit a fixed-boundary conditional character n-gram model.

    The model estimates ``P(next symbol | previous order symbols)`` with
    add-alpha smoothing. It is a scoring objective, not a language claim.
    """

    if not isinstance(order, int) or isinstance(order, bool) or order < 0:
        raise ValueError("order must be a non-negative integer")
    if not isinstance(add_alpha, (int, float)) or not math.isfinite(add_alpha) or add_alpha <= 0:
        raise ValueError("add_alpha must be a positive finite number")
    tokens = _normalise_tokens(words)
    declared_alphabet = _normalise_alphabet(alphabet)
    if declared_alphabet is None:
        observed = {
            symbol
            for token in tokens
            for symbol in token
        }
        model_alphabet = tuple(sorted(observed))
        alphabet_source = "training_observed"
    else:
        model_alphabet = declared_alphabet
        alphabet_source = "declared"

    vocabulary = (*model_alphabet, UNKNOWN_SYMBOL, END_SYMBOL)
    alphabet_set = set(model_alphabet)
    context_counts: defaultdict[tuple[str, ...], Counter[str]] = defaultdict(Counter)
    context_counts[(START_SYMBOL,) * order]
    unigram_counts: Counter[str] = Counter({symbol: 0 for symbol in vocabulary})
    training_symbol_count = 0
    unknown_training_symbols = 0

    for token in tokens:
        mapped: list[str] = []
        for symbol in token:
            if symbol in alphabet_set:
                mapped.append(symbol)
            else:
                mapped.append(UNKNOWN_SYMBOL)
                unknown_training_symbols += 1
        training_symbol_count += len(mapped)
        for position, target in enumerate((*mapped, END_SYMBOL)):
            context = _context_for(tuple(mapped), position, order)
            context_counts[context][target] += 1
            unigram_counts[target] += 1

    frozen_context_counts = tuple(
        (
            _context_key(context),
            tuple(sorted((symbol, int(count)) for symbol, count in counter.items())),
        )
        for context, counter in sorted(context_counts.items(), key=lambda item: _context_key(item[0]))
    )
    frozen_context_totals = tuple(
        (
            key,
            sum(count for _symbol, count in rows),
        )
        for key, rows in frozen_context_counts
    )
    frozen_unigrams = tuple(
        (symbol, int(unigram_counts[symbol])) for symbol in vocabulary
    )
    return LanguageModel(
        order=order,
        add_alpha=float(add_alpha),
        alphabet=model_alphabet,
        vocabulary=vocabulary,
        start_symbol=START_SYMBOL,
        end_symbol=END_SYMBOL,
        unknown_symbol=UNKNOWN_SYMBOL,
        context_counts=frozen_context_counts,
        context_totals=frozen_context_totals,
        unigram_counts=frozen_unigrams,
        training_word_count=len(tokens),
        training_symbol_count=training_symbol_count,
        unknown_training_symbols=unknown_training_symbols,
        alphabet_source=alphabet_source,
        definition=(
            "Fixed-boundary conditional character n-gram objective: "
            "P(next symbol | previous order symbols), with add-alpha smoothing. "
            "Scores are weighted n-gram evidence, not a composite full-probability claim."
        ),
    )


@dataclass(frozen=True)
class _Event:
    context: tuple[str, ...]
    target: str
    count: int


def _corpus_events(
    tokens: list[tuple[str, ...]], order: int
) -> tuple[list[_Event], tuple[str, ...], Counter[str]]:
    event_counts: Counter[tuple[tuple[str, ...], str]] = Counter()
    symbol_counts: Counter[str] = Counter()
    for token in tokens:
        symbol_counts.update(token)
        for position, target in enumerate((*token, END_SYMBOL)):
            context = _context_for(token, position, order)
            event_counts[(context, target)] += 1
    events = [
        _Event(context=context, target=target, count=count)
        for (context, target), count in sorted(
            event_counts.items(),
            key=lambda item: (_context_key(item[0][0]), item[0][1]),
        )
    ]
    return events, tuple(sorted(symbol_counts)), symbol_counts


def _validate_key(model: LanguageModel, key: Mapping[str, str]) -> dict[str, str]:
    if not isinstance(key, Mapping):
        raise TypeError("key must be a mapping from ciphertext symbols to plaintext symbols")
    normalized: dict[str, str] = {}
    for cipher_symbol, plain_symbol in key.items():
        if not isinstance(cipher_symbol, str) or not isinstance(plain_symbol, str):
            raise ValueError("key symbols must be strings")
        if not cipher_symbol or not plain_symbol:
            raise ValueError("key symbols must be non-empty strings")
        if plain_symbol in normalized.values():
            raise ValueError("key must be injective; duplicate plaintext assignment")
        if plain_symbol not in model.alphabet:
            raise ValueError("key plaintext symbols must be in the model alphabet")
        normalized[cipher_symbol] = plain_symbol
    return normalized


def _mapped_symbol(symbol: str, key: Mapping[str, str], model: LanguageModel) -> str:
    if symbol in {START_SYMBOL, END_SYMBOL}:
        return symbol
    return key.get(symbol, model.unknown_symbol)


def _event_log_probability(
    event: _Event,
    key: Mapping[str, str],
    model: LanguageModel,
    context_counts: Mapping[tuple[str, ...], Mapping[str, int]] | None = None,
    context_totals: Mapping[tuple[str, ...], int] | None = None,
) -> float:
    mapped_context = tuple(_mapped_symbol(symbol, key, model) for symbol in event.context)
    mapped_target = _mapped_symbol(event.target, key, model)
    if context_counts is None:
        probability = model.probability(mapped_context, mapped_target)
    else:
        counts = context_counts.get(mapped_context, {})
        total = (context_totals or {}).get(mapped_context, 0)
        probability = (counts.get(mapped_target, 0) + model.add_alpha) / (
            total + model.add_alpha * len(model.vocabulary)
        )
    return -math.log2(probability) * event.count


def _model_context_maps(
    model: LanguageModel,
) -> tuple[dict[tuple[str, ...], dict[str, int]], dict[tuple[str, ...], int]]:
    """Decode frozen context tables once for repeated scoring operations."""

    counts = {
        tuple(json.loads(key)): dict(rows)
        for key, rows in model.context_counts
    }
    totals = {
        tuple(json.loads(key)): total
        for key, total in model.context_totals
    }
    return counts, totals


def _finalize_score(
    negative_log2_probability: float,
    word_count: int,
    predicted_symbols: int,
    eos_count: int,
    unknown_cipher_symbols: int,
    missing_key_types: set[str],
    cipher_symbols: tuple[str, ...],
    key: Mapping[str, str],
) -> dict[str, Any]:
    if predicted_symbols:
        bits_per_symbol = negative_log2_probability / predicted_symbols
        perplexity = 2.0**bits_per_symbol
    else:
        bits_per_symbol = None
        perplexity = None
    coverage = (
        len(set(cipher_symbols).intersection(key)) / len(cipher_symbols)
        if cipher_symbols
        else 0.0
    )
    return {
        "negative_log2_probability": negative_log2_probability,
        "bits_per_symbol": bits_per_symbol,
        "perplexity": perplexity,
        "word_count": word_count,
        "predicted_symbols": predicted_symbols,
        "eos_count": eos_count,
        "unknown_cipher_symbols": unknown_cipher_symbols,
        "missing_key_types": len(missing_key_types),
        "missing_key_symbols": sorted(missing_key_types),
        "cipher_alphabet_size": len(cipher_symbols),
        "key_coverage": coverage,
    }


def score_with_key(
    cipher_tokens: Iterable[Token],
    model: LanguageModel,
    key: Mapping[str, str],
) -> dict[str, Any]:
    """Score cipher words directly under one validated partial injection key."""

    tokens = _normalise_tokens(cipher_tokens)
    normalized_key = _validate_key(model, key)
    events, cipher_symbols, _symbol_counts = _corpus_events(tokens, model.order)
    context_counts, context_totals = _model_context_maps(model)
    negative_log2_probability = 0.0
    unknown_cipher_symbols = 0
    missing_key_types: set[str] = set()
    for token in tokens:
        for position, target in enumerate((*token, END_SYMBOL)):
            event = _Event(_context_for(token, position, model.order), target, 1)
            negative_log2_probability += _event_log_probability(
                event,
                normalized_key,
                model,
                context_counts,
                context_totals,
            )
            if target != END_SYMBOL and target not in normalized_key:
                unknown_cipher_symbols += 1
                missing_key_types.add(target)
    return _finalize_score(
        negative_log2_probability,
        len(tokens),
        sum(event.count for event in events),
        len(tokens),
        unknown_cipher_symbols,
        missing_key_types,
        cipher_symbols,
        normalized_key,
    )


def score_with_key_incremental(
    cipher_tokens: Iterable[Token],
    model: LanguageModel,
    key: Mapping[str, str],
) -> dict[str, Any]:
    """Score compressed n-gram events under a key.

    Search uses the same event contributions to update only events touched by
    a proposed key move. This public helper provides a direct equality check.
    """

    tokens = _normalise_tokens(cipher_tokens)
    normalized_key = _validate_key(model, key)
    events, cipher_symbols, symbol_counts = _corpus_events(tokens, model.order)
    context_counts, context_totals = _model_context_maps(model)
    negative_log2_probability = sum(
        _event_log_probability(
            event,
            normalized_key,
            model,
            context_counts,
            context_totals,
        )
        for event in events
    )
    missing_key_types = set(symbol_counts).difference(normalized_key)
    unknown_cipher_symbols = sum(
        count for symbol, count in symbol_counts.items() if symbol not in normalized_key
    )
    return _finalize_score(
        negative_log2_probability,
        len(tokens),
        sum(event.count for event in events),
        len(tokens),
        unknown_cipher_symbols,
        missing_key_types,
        cipher_symbols,
        normalized_key,
    )


def score_heldout(
    cipher_tokens: Iterable[Token],
    model: LanguageModel,
    key: Mapping[str, str],
    reference_key: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Score a separate held-out word list and report missing-key coverage.

    If ``reference_key`` is supplied, the result also contains recovery
    metrics computed on comparable held-out words and observed symbols.
    """

    tokens = _normalise_tokens(cipher_tokens)
    normalized_key = _validate_key(model, key)
    score = score_with_key(tokens, model, normalized_key)
    score["evaluation_split"] = "heldout"
    score["partial_key_coverage"] = score["key_coverage"] < 1.0
    if reference_key is not None:
        _validate_key(model, reference_key)
        score["recovery_metrics"] = _recovery_metrics(
            tokens,
            normalized_key,
            reference_key,
        )
    return score


def _frequency_key(
    cipher_symbols: tuple[str, ...],
    symbol_counts: Counter[str],
    model: LanguageModel,
) -> dict[str, str]:
    cipher_order = sorted(cipher_symbols, key=lambda symbol: (-symbol_counts[symbol], symbol))
    unigram_counts = model.unigram_count_map
    plain_order = sorted(model.alphabet, key=lambda symbol: (-unigram_counts.get(symbol, 0), symbol))
    return dict(zip(cipher_order, plain_order[: len(cipher_order)]))


def _random_key(
    cipher_symbols: tuple[str, ...], model: LanguageModel, rng: random.Random
) -> dict[str, str]:
    values = rng.sample(list(model.alphabet), len(cipher_symbols))
    return dict(zip(cipher_symbols, values))


class _FastScorer:
    """Score encoded events without rebuilding string contexts for each move."""

    def __init__(
        self,
        events: list[_Event],
        model: LanguageModel,
        cipher_symbols: tuple[str, ...],
    ) -> None:
        self.model = model
        self.cipher_symbols = cipher_symbols
        self.cipher_indices = {
            symbol: index for index, symbol in enumerate(cipher_symbols)
        }
        self.plain_ids = {
            symbol: index + 1 for index, symbol in enumerate(model.alphabet)
        }
        self.unknown_id = len(model.alphabet) + 1
        self.end_id = len(model.alphabet) + 2
        self.bos_id = len(model.alphabet) + 3
        self.base = self.bos_id + 2
        self.vocabulary_size = len(model.vocabulary)
        self.row_costs: dict[int, tuple[float, ...]] = {}
        for context_key, rows in model.context_counts:
            context = tuple(json.loads(context_key))
            code = self._model_context_code(context)
            total = sum(count for _symbol, count in rows)
            self.row_costs[code] = self._cost_row(dict(rows), total)
        self.default_costs = self._cost_row({}, 0)
        self.events = [self._encode_event(event) for event in events]

    def _model_symbol_id(self, symbol: str) -> int:
        if symbol == START_SYMBOL:
            return self.bos_id
        if symbol == END_SYMBOL:
            return self.end_id
        if symbol == UNKNOWN_SYMBOL:
            return self.unknown_id
        return self.plain_ids[symbol]

    def _model_context_code(self, context: tuple[str, ...]) -> int:
        code = 0
        for symbol in context:
            code = code * self.base + self._model_symbol_id(symbol) + 1
        return code

    def _cost_row(self, counts: Mapping[str, int], total: int) -> tuple[float, ...]:
        denominator = total + self.model.add_alpha * self.vocabulary_size
        return tuple(
            -math.log2(
                (counts.get(symbol, 0) + self.model.add_alpha) / denominator
            )
            for symbol in self.model.vocabulary
        )

    def _encode_event(self, event: _Event) -> tuple[tuple[int, ...], int, int]:
        context = tuple(
            0 if symbol == START_SYMBOL else self.cipher_indices[symbol] + 1
            for symbol in event.context
        )
        target = 0 if event.target == END_SYMBOL else self.cipher_indices[event.target] + 1
        return context, target, event.count

    def assignment(self, key: Mapping[str, str]) -> list[int]:
        return [
            self.plain_ids.get(key.get(symbol, ""), self.unknown_id)
            for symbol in self.cipher_symbols
        ]

    def event_score(
        self,
        event: tuple[tuple[int, ...], int, int],
        assignment: list[int],
    ) -> float:
        context, target, count = event
        context_code = 0
        for raw_symbol in context:
            mapped = self.bos_id if raw_symbol == 0 else assignment[raw_symbol - 1]
            context_code = context_code * self.base + mapped + 1
        mapped_target = self.end_id if target == 0 else assignment[target - 1]
        costs = self.row_costs.get(context_code, self.default_costs)
        return costs[mapped_target - 1] * count


class _IncrementalState:
    """Track a key score and update only events touched by a key move."""

    def __init__(
        self,
        events: list[_Event],
        model: LanguageModel,
        cipher_symbols: tuple[str, ...] | None = None,
    ) -> None:
        self.events = events
        if cipher_symbols is None:
            cipher_symbols = tuple(
                sorted(
                    symbol
                    for event in events
                    for symbol in event.context + (event.target,)
                    if symbol not in {START_SYMBOL, END_SYMBOL}
                )
            )
        self.scorer = _FastScorer(events, model, cipher_symbols)
        self.affected: dict[str, set[int]] = defaultdict(set)
        for index, event in enumerate(events):
            for symbol in set(event.context + (event.target,)):
                if symbol not in {START_SYMBOL, END_SYMBOL}:
                    self.affected[symbol].add(index)
        self.contributions = [0.0] * len(events)
        self.total = 0.0

    def initialize(self, key: Mapping[str, str]) -> None:
        assignment = self.scorer.assignment(key)
        self.contributions = [
            self.scorer.event_score(event, assignment)
            for event in self.scorer.events
        ]
        self.total = math.fsum(self.contributions)

    def changed_indices(self, changed_symbols: Iterable[str]) -> set[int]:
        indices: set[int] = set()
        for symbol in changed_symbols:
            indices.update(self.affected.get(symbol, ()))
        return indices

    def trial(self, key: Mapping[str, str], indices: set[int]) -> tuple[float, list[float]]:
        ordered_indices = sorted(indices)
        assignment = self.scorer.assignment(key)
        new_contributions = [
            self.scorer.event_score(self.scorer.events[index], assignment)
            for index in ordered_indices
        ]
        old_total = math.fsum(self.contributions[index] for index in ordered_indices)
        new_total = math.fsum(new_contributions)
        return new_total - old_total, new_contributions

    def commit(self, indices: set[int], new_contributions: list[float]) -> None:
        ordered_indices = sorted(indices)
        old_total = math.fsum(self.contributions[index] for index in ordered_indices)
        for index, contribution in zip(ordered_indices, new_contributions):
            self.contributions[index] = contribution
        self.total += math.fsum(new_contributions) - old_total


def _commit_state(
    state: _IncrementalState,
    indices: set[int],
    new_contributions: list[float],
    old_contributions: dict[int, float],
) -> None:
    ordered_indices = sorted(indices)
    for index, contribution in zip(ordered_indices, new_contributions):
        state.contributions[index] = contribution
    state.total += sum(new_contributions) - sum(old_contributions.values())


def _propose_move(
    key: dict[str, str],
    cipher_symbols: tuple[str, ...],
    model: LanguageModel,
    rng: random.Random,
) -> tuple[dict[str, str], set[str]]:
    candidate = dict(key)
    if not cipher_symbols:
        return candidate, set()
    unused = [symbol for symbol in model.alphabet if symbol not in candidate.values()]
    if unused and (len(cipher_symbols) == 1 or rng.random() < 0.25):
        cipher_symbol = rng.choice(list(cipher_symbols))
        candidate[cipher_symbol] = rng.choice(unused)
        return candidate, {cipher_symbol}
    if len(cipher_symbols) >= 2:
        first, second = rng.sample(list(cipher_symbols), 2)
        candidate[first], candidate[second] = candidate[second], candidate[first]
        return candidate, {first, second}
    if unused:
        cipher_symbol = cipher_symbols[0]
        candidate[cipher_symbol] = unused[0]
        return candidate, {cipher_symbol}
    return candidate, set()


def _recovery_metrics(
    cipher_tokens: list[tuple[str, ...]],
    key: Mapping[str, str],
    reference_key: Mapping[str, str] | None,
) -> dict[str, Any]:
    cipher_counts: Counter[str] = Counter(symbol for token in cipher_tokens for symbol in token)
    cipher_symbols = set(cipher_counts)
    assigned = cipher_symbols.intersection(key)
    key_coverage = len(assigned) / len(cipher_symbols) if cipher_symbols else 0.0
    if reference_key is None:
        return {
            "key_coverage": key_coverage,
            "key_coverage_assigned_types": len(assigned),
            "key_coverage_total_types": len(cipher_symbols),
            "key_assignment_accuracy": None,
            "key_assignment_correct": None,
            "key_assignment_total": None,
            "exact_character_accuracy": None,
            "exact_character_correct": None,
            "exact_character_total": None,
            "exact_word_accuracy": None,
            "exact_word_correct": None,
            "exact_word_total": None,
            "reference_key_provided": False,
        }

    reference = dict(reference_key)
    if len(set(reference.values())) != len(reference):
        raise ValueError("reference_key must be injective")
    reference_symbols = cipher_symbols.intersection(reference)
    key_assignment_total = len(reference_symbols)
    key_assignment_correct = sum(
        1
        for symbol in reference_symbols
        if key.get(symbol) == reference[symbol]
    )
    key_assignment_accuracy = (
        key_assignment_correct / key_assignment_total
        if key_assignment_total
        else 0.0
    )
    exact_character_total = sum(cipher_counts[symbol] for symbol in reference_symbols)
    exact_character_correct = sum(
        cipher_counts[symbol]
        for symbol in reference_symbols
        if key.get(symbol) == reference[symbol]
    )
    exact_character_accuracy = (
        exact_character_correct / exact_character_total
        if exact_character_total
        else 0.0
    )
    exact_word_total = 0
    exact_word_correct = 0
    for token in cipher_tokens:
        if not token or not all(symbol in reference for symbol in token):
            continue
        exact_word_total += 1
        if all(key.get(symbol) == reference[symbol] for symbol in token):
            exact_word_correct += 1
    exact_word_accuracy = (
        exact_word_correct / exact_word_total if exact_word_total else 0.0
    )
    return {
        "key_coverage": key_coverage,
        "key_coverage_assigned_types": len(assigned),
        "key_coverage_total_types": len(cipher_symbols),
        "key_assignment_accuracy": key_assignment_accuracy,
        "key_assignment_correct": key_assignment_correct,
        "key_assignment_total": key_assignment_total,
        "exact_character_accuracy": exact_character_accuracy,
        "exact_character_correct": exact_character_correct,
        "exact_character_total": exact_character_total,
        "exact_word_accuracy": exact_word_accuracy,
        "exact_word_correct": exact_word_correct,
        "exact_word_total": exact_word_total,
        "reference_key_provided": True,
    }


def search_substitution(
    cipher_tokens: Iterable[Token],
    model: LanguageModel,
    iterations: int = 2000,
    restarts: int = 8,
    seed: int = DEFAULT_SEED,
    reference_key: Mapping[str, str] | None = None,
    start_temperature: float = 1.0,
) -> dict[str, Any]:
    """Search an injective ciphertext-symbol to plaintext-symbol key."""

    if not isinstance(iterations, int) or isinstance(iterations, bool) or iterations < 0:
        raise ValueError("iterations must be a non-negative integer")
    if not isinstance(restarts, int) or isinstance(restarts, bool) or restarts < 1:
        raise ValueError("restarts must be a positive integer")
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise ValueError("seed must be an integer")
    if not math.isfinite(start_temperature) or start_temperature < 0:
        raise ValueError("start_temperature must be finite and non-negative")

    tokens = _normalise_tokens(cipher_tokens)
    events, cipher_symbols, symbol_counts = _corpus_events(tokens, model.order)
    config = {
        "seed": seed,
        "iterations": iterations,
        "restarts": restarts,
        "start_temperature": start_temperature,
        "order": model.order,
        "add_alpha": model.add_alpha,
        "mapping_kind": "injective",
        "key_direction": "ciphertext_symbol_to_plaintext_symbol",
        "word_boundaries": "preserved; no cross-word transitions",
        "initialization": "frequency-ranked first start plus randomized starts",
        "objective": model.definition,
        "temperature_units": "total objective bits, scaled from bits per predicted symbol",
        "temperature_schedule": "linear decay to zero over each restart",
        "train_only_model": True,
    }

    if reference_key is not None:
        _validate_key(model, reference_key)

    if not tokens or not cipher_symbols:
        empty_score = score_with_key_incremental(tokens, model, {})
        return {
            "status": "empty_input",
            "config": config,
            "alphabet": {
                "cipher_size": len(cipher_symbols),
                "plaintext_size": len(model.alphabet),
                "cipher_symbols": list(cipher_symbols),
            },
            "key": {},
            "score": empty_score,
            "recovery_metrics": _recovery_metrics(tokens, {}, reference_key),
        }

    if len(cipher_symbols) > len(model.alphabet):
        mismatch_score = score_with_key_incremental(tokens, model, {})
        return {
            "status": "alphabet_mismatch",
            "config": config,
            "alphabet": {
                "cipher_size": len(cipher_symbols),
                "plaintext_size": len(model.alphabet),
                "cipher_symbols": list(cipher_symbols),
                "plaintext_symbols": list(model.alphabet),
                "unmappable_cipher_symbols": list(cipher_symbols),
            },
            "key": {},
            "score": mismatch_score,
            "recovery_metrics": _recovery_metrics(tokens, {}, reference_key),
        }

    rng = random.Random(seed)
    state = _IncrementalState(events, model, cipher_symbols)
    best_key: dict[str, str] = {}
    best_score = math.inf
    accepted_moves = 0
    proposed_moves = 0
    frequency_key = _frequency_key(cipher_symbols, symbol_counts, model)
    predicted_symbol_count = sum(event.count for event in events)
    temperature_scale = max(1, predicted_symbol_count)
    restart_best_scores: list[float] = []
    selected_restart = 0

    for restart in range(restarts):
        current_key = (
            dict(frequency_key)
            if restart == 0
            else _random_key(cipher_symbols, model, rng)
        )
        state.initialize(current_key)
        restart_best_score = state.total
        if state.total < best_score:
            best_score = state.total
            best_key = dict(current_key)
            selected_restart = restart
        for iteration in range(iterations):
            candidate, changed_symbols = _propose_move(
                current_key, cipher_symbols, model, rng
            )
            if not changed_symbols:
                continue
            proposed_moves += 1
            indices = state.changed_indices(changed_symbols)
            old_contributions = {
                index: state.contributions[index] for index in indices
            }
            delta, new_contributions = state.trial(candidate, indices)
            fraction = iteration / max(1, iterations - 1)
            temperature = start_temperature * temperature_scale * (1.0 - fraction)
            accept = delta <= 0.0
            if not accept and temperature > 0.0:
                accept = rng.random() < math.exp(-delta / temperature)
            if accept:
                _commit_state(state, indices, new_contributions, old_contributions)
                current_key = candidate
                accepted_moves += 1
                if state.total < restart_best_score:
                    restart_best_score = state.total
                if state.total < best_score:
                    best_score = state.total
                    best_key = dict(current_key)
                    selected_restart = restart
        restart_best_scores.append(restart_best_score)

    best_key = dict(sorted(best_key.items()))
    best_score_result = score_with_key_incremental(tokens, model, best_key)
    return {
        "status": "ok",
        "config": config,
        "alphabet": {
            "cipher_size": len(cipher_symbols),
            "plaintext_size": len(model.alphabet),
            "cipher_symbols": list(cipher_symbols),
            "plaintext_symbols": list(model.alphabet),
        },
        "key": best_key,
        "score": best_score_result,
        "recovery_metrics": _recovery_metrics(tokens, best_key, reference_key),
        "search": {
            "restarts_completed": restarts,
            "proposed_moves": proposed_moves,
            "accepted_moves": accepted_moves,
            "best_objective": best_score,
            "restart_best_objectives": restart_best_scores,
            "selected_restart": selected_restart,
        },
    }


__all__ = [
    "LanguageModel",
    "fit_language_model",
    "score_heldout",
    "score_with_key",
    "score_with_key_incremental",
    "search_substitution",
]
