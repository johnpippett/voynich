"""Bounded branch-and-bound search for one fixed lexicon substitution key."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
import heapq
import itertools
from typing import Any


Word = str | tuple[str, ...]


def _normalise_word(word: Word) -> tuple[str, ...]:
    if isinstance(word, str):
        symbols = tuple(word)
    elif isinstance(word, tuple) and all(isinstance(symbol, str) for symbol in word):
        symbols = word
    else:
        raise TypeError("words must be strings or tuple[str, ...]")
    if any(not symbol for symbol in symbols):
        raise ValueError("word symbols must be non-empty strings")
    return symbols


def _normalise_alphabet(alphabet: Iterable[str] | str) -> tuple[str, ...]:
    values = tuple(alphabet) if isinstance(alphabet, str) else tuple(alphabet)
    if not values or any(not isinstance(symbol, str) or not symbol for symbol in values):
        raise ValueError("plaintext_alphabet must contain non-empty symbols")
    if len(set(values)) != len(values):
        raise ValueError("plaintext_alphabet symbols must be unique")
    return tuple(sorted(values))


def _normalise_cipher_counts(
    ciphertext_counts: Mapping[Word, int],
) -> dict[tuple[str, ...], int]:
    if not isinstance(ciphertext_counts, Mapping):
        raise TypeError("ciphertext_counts must be a mapping from words to weights")
    normalised: dict[tuple[str, ...], int] = {}
    for raw_word, weight in ciphertext_counts.items():
        word = _normalise_word(raw_word)
        if not isinstance(weight, int) or isinstance(weight, bool) or weight < 0:
            raise ValueError("ciphertext weights must be non-negative integers")
        normalised[word] = normalised.get(word, 0) + weight
    return dict(sorted(normalised.items()))


def _normalise_lexicon(
    plaintext_lexicon: Iterable[Word],
    alphabet: tuple[str, ...],
) -> tuple[set[tuple[str, ...]], int, int, int]:
    raw_values = [_normalise_word(word) for word in plaintext_lexicon]
    values = set(raw_values)
    alphabet_set = set(alphabet)
    usable = {word for word in values if set(word).issubset(alphabet_set)}
    return usable, len(raw_values), len(values), len(values) - len(usable)


def _pattern(word: tuple[str, ...]) -> tuple[int, ...]:
    first_seen: dict[str, int] = {}
    result: list[int] = []
    for symbol in word:
        if symbol not in first_seen:
            first_seen[symbol] = len(first_seen)
        result.append(first_seen[symbol])
    return tuple(result)


def _candidate_lists(
    ciphertext_counts: Mapping[tuple[str, ...], int],
    lexicon: set[tuple[str, ...]],
) -> dict[tuple[str, ...], tuple[tuple[str, ...], ...]]:
    by_shape: dict[tuple[int, tuple[int, ...]], list[tuple[str, ...]]] = {}
    for word in sorted(lexicon):
        shape = (len(word), _pattern(word))
        by_shape.setdefault(shape, []).append(word)
    return {
        cipher_word: tuple(
            by_shape.get((len(cipher_word), _pattern(cipher_word)), ())
        )
        for cipher_word in ciphertext_counts
    }


def _validate_symbol_order(
    symbol_order: Sequence[str] | None,
    cipher_symbols: tuple[str, ...],
) -> tuple[str, ...]:
    if symbol_order is None:
        return cipher_symbols
    values = tuple(symbol_order)
    if len(values) != len(set(values)) or set(values) != set(cipher_symbols):
        raise ValueError("symbol_order must contain every ciphertext symbol exactly once")
    return values


def _validate_initial_key(
    initial_key: Mapping[str, str] | None,
    cipher_symbols: tuple[str, ...],
    alphabet: tuple[str, ...],
) -> dict[str, str]:
    if initial_key is None:
        return {}
    if not isinstance(initial_key, Mapping):
        raise TypeError("initial_key must be a mapping")
    cipher_set = set(cipher_symbols)
    alphabet_set = set(alphabet)
    key: dict[str, str] = {}
    for cipher_symbol, plain_symbol in initial_key.items():
        if not isinstance(cipher_symbol, str) or not isinstance(plain_symbol, str):
            raise ValueError("initial_key symbols must be strings")
        if cipher_symbol not in cipher_set:
            raise ValueError("initial_key contains a symbol absent from ciphertext")
        if plain_symbol not in alphabet_set:
            raise ValueError("initial_key values must be in plaintext_alphabet")
        if plain_symbol in key.values():
            raise ValueError("initial_key must be injective")
        key[cipher_symbol] = plain_symbol
    return key


def _candidate_compatible(
    cipher_word: tuple[str, ...],
    plaintext_word: tuple[str, ...],
    partial_key: Mapping[str, str],
) -> bool:
    used = set(partial_key.values())
    local: dict[str, str] = {}
    for cipher_symbol, plain_symbol in zip(cipher_word, plaintext_word):
        assigned = partial_key.get(cipher_symbol)
        if assigned is not None:
            if assigned != plain_symbol:
                return False
            continue
        previous = local.get(cipher_symbol)
        if previous is not None:
            if previous != plain_symbol:
                return False
            continue
        if plain_symbol in used:
            return False
        local[cipher_symbol] = plain_symbol
        used.add(plain_symbol)
    return True


def _upper_bound(
    partial_key: Mapping[str, str],
    ciphertext_counts: Mapping[tuple[str, ...], int],
    candidates: Mapping[tuple[str, ...], tuple[tuple[str, ...], ...]],
) -> int:
    bound = 0
    for cipher_word, weight in ciphertext_counts.items():
        if any(
            _candidate_compatible(cipher_word, candidate, partial_key)
            for candidate in candidates[cipher_word]
        ):
            bound += weight
    return bound


def _complete_key(
    partial_key: Mapping[str, str],
    symbol_order: tuple[str, ...],
    alphabet: tuple[str, ...],
) -> dict[str, str]:
    key = dict(partial_key)
    unused = [symbol for symbol in alphabet if symbol not in key.values()]
    for cipher_symbol in symbol_order:
        if cipher_symbol not in key:
            if not unused:
                raise ValueError("no injective completion exists")
            key[cipher_symbol] = unused.pop(0)
    return key


def _score_key(
    key: Mapping[str, str],
    ciphertext_counts: Mapping[tuple[str, ...], int],
    lexicon: set[tuple[str, ...]],
) -> tuple[int, int]:
    score = 0
    hit_types = 0
    for cipher_word, weight in ciphertext_counts.items():
        decoded = tuple(key[symbol] for symbol in cipher_word)
        if decoded in lexicon:
            score += weight
            hit_types += 1
    return score, hit_types


def _key_tie_order(key: Mapping[str, str], cipher_symbols: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(key[symbol] for symbol in cipher_symbols)


def _word_record(
    word: tuple[str, ...],
    weight: int,
    candidate_count: int,
) -> dict[str, Any]:
    return {
        "cipher_word": list(word),
        "weight": weight,
        "candidate_count": candidate_count,
    }


def solve_lexicon(
    ciphertext_counts: Mapping[Word, int],
    plaintext_lexicon: Iterable[Word],
    plaintext_alphabet: Iterable[str] | str,
    *,
    node_budget: int | None = None,
    initial_key: Mapping[str, str] | None = None,
    symbol_order: Sequence[str] | None = None,
    bound_engine: str = "reference",
) -> dict[str, Any]:
    """Search one injective key and certify its integer hit-weight bounds.

    The objective is the sum of ciphertext word weights whose complete decode
    is in the supplied finite lexicon. Pattern candidates give an admissible
    upper bound. ``initial_key`` is only a completed warm-start incumbent; it
    never restricts the empty root frontier. ``bound_engine`` selects the
    reference scan or an equivalent bitset bound implementation. A budget stop
    remains uncertified when frontier bounds exceed the best feasible score.
    """

    if node_budget is not None and (
        not isinstance(node_budget, int)
        or isinstance(node_budget, bool)
        or node_budget < 0
    ):
        raise ValueError("node_budget must be a non-negative integer or None")
    if (
        not isinstance(bound_engine, str)
        or bound_engine not in {"reference", "bitset"}
    ):
        raise ValueError("bound_engine must be 'reference' or 'bitset'")

    counts = _normalise_cipher_counts(ciphertext_counts)
    alphabet = _normalise_alphabet(plaintext_alphabet)
    (
        lexicon,
        lexicon_raw_entry_count,
        lexicon_unique_normalized_count,
        rejected_lexicon_count,
    ) = _normalise_lexicon(plaintext_lexicon, alphabet)
    cipher_symbols = tuple(
        sorted({symbol for word in counts for symbol in word})
    )
    order = _validate_symbol_order(symbol_order, cipher_symbols)
    initial = _validate_initial_key(initial_key, cipher_symbols, alphabet)
    candidates = _candidate_lists(counts, lexicon)
    candidate_records = [
        _word_record(word, counts[word], len(candidates[word]))
        for word in counts
    ]
    missing_candidate_count = sum(
        1 for word in counts if not candidates[word]
    )
    candidate_count_total = sum(len(values) for values in candidates.values())
    total_weight = sum(counts.values())
    if bound_engine == "bitset":
        from .bitset_bound import BitsetBound

        bitset_bound = BitsetBound(counts, candidates, alphabet)

        def bound_for_key(partial_key: Mapping[str, str]) -> int:
            return bitset_bound.bound(partial_key)

    else:

        def bound_for_key(partial_key: Mapping[str, str]) -> int:
            return _upper_bound(partial_key, counts, candidates)

    config = {
        "objective": "integer weighted exact lexicon word hits",
        "pattern_constraint": "equal length and first-occurrence equality pattern",
        "mapping_kind": "one fixed injective ciphertext-symbol to plaintext-symbol map",
        "tie_rule": "lexicographically smallest visited feasible key after maximum score, using sorted ciphertext-symbol order",
        "node_budget": node_budget,
        "symbol_order": list(order),
        "bound": "sum of weights with a compatible pattern candidate, maximized over unsearched frontier nodes",
        "initial_key_role": "completed warm-start incumbent only; root search has no fixed assignments",
        "bound_engine": bound_engine,
        "score_certified_definition": "true when a feasible score has equal integer lower and upper bounds",
        "search_exhausted_definition": "true when no unsearched frontier remains after expansion or valid bound pruning; it does not mean every feasible key was visited",
    }
    common = {
        "config": config,
        "cipher_alphabet": list(cipher_symbols),
        "plaintext_alphabet": list(alphabet),
        "candidate_counts": candidate_records,
        "candidate_count_total": candidate_count_total,
        "pattern_compatible_type_count": sum(
            bool(candidates[word]) for word in counts
        ),
        "missing_candidate_count": missing_candidate_count,
        "lexicon_raw_entry_count": lexicon_raw_entry_count,
        "lexicon_unique_normalized_count": lexicon_unique_normalized_count,
        "lexicon_usable_count": len(lexicon),
        "lexicon_rejected_out_of_alphabet_count": rejected_lexicon_count,
        "cipher_type_count": len(counts),
        "total_weight": total_weight,
        "infeasibility_certified": False,
        "scope_limits": [
            "The result tests only the supplied finite lexicon and ciphertext words.",
            "Word boundaries and symbol units remain fixed.",
            "The key is injective; homophones, nulls, repairs, and per-word keys are outside scope.",
            "A budget stop does not certify the optimum unless lower_bound equals upper_bound.",
        ],
        "performance_followups": [
            "Index candidate constraints before large alphabets or corpora.",
            "Add stronger joint bounds or independent components after validating this clear baseline.",
        ],
    }

    if not counts:
        return {
            **common,
            "status": "empty_input",
            "score_certified": True,
            "search_exhausted": True,
            "feasible": True,
            "nodes": 0,
            "lower_bound": 0,
            "upper_bound": 0,
            "score": 0,
            "hit_type_count": 0,
            "key": {},
        }

    if len(cipher_symbols) > len(alphabet):
        return {
            **common,
            "status": "infeasible_alphabet",
            "score_certified": False,
            "search_exhausted": True,
            "infeasibility_certified": True,
            "feasible": False,
            "nodes": 0,
            "lower_bound": None,
            "upper_bound": None,
            "score": None,
            "hit_type_count": 0,
            "key": {},
        }

    best_key = _complete_key(initial, order, alphabet)
    best_score, best_hit_types = _score_key(best_key, counts, lexicon)
    root_upper = bound_for_key({})
    if not any(candidates.values()):
        return {
            **common,
            "status": "no_candidates",
            "score_certified": True,
            "search_exhausted": True,
            "feasible": True,
            "nodes": 0,
            "lower_bound": best_score,
            "upper_bound": best_score,
            "score": best_score,
            "hit_type_count": best_hit_types,
            "key": dict(sorted(best_key.items())),
        }

    if root_upper == best_score and node_budget == 0:
        return {
            **common,
            "status": "bound_certified",
            "score_certified": True,
            "search_exhausted": False,
            "feasible": True,
            "nodes": 0,
            "frontier_node_count": 1,
            "lower_bound": best_score,
            "upper_bound": best_score,
            "score": best_score,
            "hit_type_count": best_hit_types,
            "key": dict(sorted(best_key.items())),
        }

    remaining_order = order
    frontier: list[tuple[int, tuple[str, ...], int, int, tuple[tuple[str, str], ...]]] = []
    sequence = itertools.count()

    def push_node(key: Mapping[str, str], depth: int, upper: int) -> None:
        prefix = tuple(key[symbol] for symbol in remaining_order[:depth])
        heapq.heappush(
            frontier,
            (
                -upper,
                prefix,
                next(sequence),
                depth,
                tuple(sorted(key.items())),
            ),
        )

    push_node({}, 0, root_upper)
    nodes = 0
    pruned_nodes = 0
    budget = node_budget

    while frontier and (budget is None or nodes < budget):
        neg_upper, _prefix, _sequence, depth, key_items = heapq.heappop(frontier)
        node_upper = -neg_upper
        key = dict(key_items)
        nodes += 1
        if node_upper < best_score:
            pruned_nodes += 1
            continue

        if depth == len(remaining_order):
            score, hit_types = _score_key(key, counts, lexicon)
            tie = _key_tie_order(key, cipher_symbols)
            best_tie = _key_tie_order(best_key, cipher_symbols)
            if score > best_score or (score == best_score and tie < best_tie):
                best_score = score
                best_hit_types = hit_types
                best_key = key
            continue

        completion = _complete_key(key, order, alphabet)
        completion_score, completion_hit_types = _score_key(completion, counts, lexicon)
        completion_tie = _key_tie_order(completion, cipher_symbols)
        best_tie = _key_tie_order(best_key, cipher_symbols)
        if completion_score > best_score or (
            completion_score == best_score and completion_tie < best_tie
        ):
            best_score = completion_score
            best_hit_types = completion_hit_types
            best_key = completion

        branch_symbol = remaining_order[depth]
        used = set(key.values())
        for plain_symbol in alphabet:
            if plain_symbol in used:
                continue
            child = dict(key)
            child[branch_symbol] = plain_symbol
            child_upper = bound_for_key(child)
            if child_upper < best_score:
                pruned_nodes += 1
                continue
            push_node(child, depth + 1, child_upper)

    if frontier:
        frontier_upper = -frontier[0][0]
    else:
        frontier_upper = best_score
    upper_bound = max(best_score, frontier_upper)
    certified = upper_bound == best_score
    search_exhausted = not frontier
    if search_exhausted:
        status = "search_exhausted"
    else:
        status = "budget_exhausted"
        if certified:
            status = "bound_certified"
    return {
        **common,
        "status": status,
        "score_certified": certified,
        "search_exhausted": search_exhausted,
        "feasible": True,
        "nodes": nodes,
        "pruned_nodes": pruned_nodes,
        "frontier_node_count": len(frontier),
        "lower_bound": best_score,
        "upper_bound": upper_bound,
        "score": best_score,
        "hit_type_count": best_hit_types,
        "key": dict(sorted(best_key.items())),
    }


__all__ = ["solve_lexicon"]
