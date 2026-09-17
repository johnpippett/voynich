"""A pair-conflict upper bound for finite-lexicon substitution hits.

For each conflict clique, one injective key can hit at most one type. The
largest type weight is therefore an upper bound for that clique. The sum of
these maxima, plus the full weight of omitted candidate types, is global.
Types with no candidate have zero possible contribution.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from .solver import (
    Word,
    _candidate_lists,
    _normalise_alphabet,
    _normalise_cipher_counts,
    _normalise_lexicon,
)


def _pair_is_compatible(
    left_cipher: tuple[str, ...],
    left_plain: tuple[str, ...],
    right_cipher: tuple[str, ...],
    right_plain: tuple[str, ...],
) -> bool:
    """Return whether two candidate readings share one injective assignment."""

    assignment: dict[str, str] = {}
    reverse: dict[str, str] = {}
    for cipher_word, plain_word in (
        (left_cipher, left_plain),
        (right_cipher, right_plain),
    ):
        for cipher_symbol, plain_symbol in zip(cipher_word, plain_word):
            previous = assignment.get(cipher_symbol)
            if previous is not None:
                if previous != plain_symbol:
                    return False
                continue
            previous_cipher = reverse.get(plain_symbol)
            if previous_cipher is not None and previous_cipher != cipher_symbol:
                return False
            assignment[cipher_symbol] = plain_symbol
            reverse[plain_symbol] = cipher_symbol
    return True


def _conflict_graph(
    words: tuple[tuple[str, ...], ...],
    candidates: Mapping[tuple[str, ...], tuple[tuple[str, ...], ...]],
) -> tuple[dict[tuple[str, ...], set[tuple[str, ...]]], int]:
    """Build the pairwise conflict graph for candidate-bearing word types."""

    graph = {word: set() for word in words}
    edge_count = 0
    for index, left in enumerate(words):
        for right in words[index + 1 :]:
            compatible = any(
                _pair_is_compatible(left, left_candidate, right, right_candidate)
                for left_candidate in candidates[left]
                for right_candidate in candidates[right]
            )
            if not compatible:
                graph[left].add(right)
                graph[right].add(left)
                edge_count += 1
    return graph, edge_count


def _greedy_clique_partition(
    words: tuple[tuple[str, ...], ...],
    weights: Mapping[tuple[str, ...], int],
    graph: Mapping[tuple[str, ...], set[tuple[str, ...]]],
) -> list[list[tuple[str, ...]]]:
    """Partition a graph into cliques by deterministic first-fit placement."""

    order = sorted(
        words,
        key=lambda word: (-len(graph[word]), -weights[word], word),
    )
    cliques: list[list[tuple[str, ...]]] = []
    for word in order:
        for clique in cliques:
            if all(member in graph[word] for member in clique):
                clique.append(word)
                break
        else:
            cliques.append([word])
    return cliques


def _word_list(word: tuple[str, ...]) -> list[str]:
    return list(word)


def pair_conflict_upper_bound(
    ciphertext_counts: Mapping[Word, int],
    plaintext_lexicon: Iterable[Word],
    plaintext_alphabet: Iterable[str] | str,
    *,
    top_k: int | None = 64,
) -> dict[str, Any]:
    """Return a sound global upper bound for weighted lexical hits.

    The objective is the sum of normalized ciphertext word weights whose
    decode is one word in the finite lexicon under one injective key. A type
    is absent from the conflict graph when it has no pattern candidate. For
    each remaining selected type pair, the function checks whether any pair
    of candidates can share one injective assignment. It puts conflicting
    types into deterministic cliques and adds the largest weight per clique.
    Candidate-bearing types outside ``top_k`` add their full weight. This
    keeps the result a global upper bound when the pair graph is truncated.

    The proof is local to each clique: two types in one clique have no
    compatible candidate pair, so one injective key cannot hit both. The
    returned ``cliques`` field records selected type membership for audit and
    later branch-bound integration. It does not expose plaintext candidates.
    """

    if top_k is not None and (
        not isinstance(top_k, int) or isinstance(top_k, bool) or top_k < 0
    ):
        raise ValueError("top_k must be a non-negative integer or None")

    counts = _normalise_cipher_counts(ciphertext_counts)
    alphabet = _normalise_alphabet(plaintext_alphabet)
    (
        lexicon,
        lexicon_raw_entry_count,
        lexicon_unique_normalized_count,
        rejected_lexicon_count,
    ) = _normalise_lexicon(plaintext_lexicon, alphabet)
    cipher_symbols = tuple(sorted({symbol for word in counts for symbol in word}))
    candidates = _candidate_lists(counts, lexicon)
    candidate_words = tuple(word for word in counts if candidates[word])
    missing_words = tuple(word for word in counts if not candidates[word])
    candidate_count_rows = [
        {
            "cipher_word": _word_list(word),
            "weight": counts[word],
            "candidate_count": len(candidates[word]),
        }
        for word in counts
    ]
    total_weight = sum(counts.values())
    candidate_weight = sum(counts[word] for word in candidate_words)
    missing_weight = sum(counts[word] for word in missing_words)
    common: dict[str, Any] = {
        "config": {
            "objective": "integer weighted exact lexicon word hits",
            "pair_rule": "conflict when no candidate pair shares one injective assignment",
            "partition": "deterministic greedy first-fit clique partition",
            "top_k": top_k,
            "omitted_candidate_rule": "add omitted candidate-bearing type weights in full",
        },
        "cipher_alphabet": list(cipher_symbols),
        "plaintext_alphabet": list(alphabet),
        "candidate_counts": candidate_count_rows,
        "cipher_type_count": len(counts),
        "candidate_type_count": len(candidate_words),
        "missing_candidate_count": len(missing_words),
        "missing_candidate_weight": missing_weight,
        "total_weight": total_weight,
        "candidate_weight": candidate_weight,
        "lexicon_raw_entry_count": lexicon_raw_entry_count,
        "lexicon_unique_normalized_count": lexicon_unique_normalized_count,
        "lexicon_usable_count": len(lexicon),
        "lexicon_rejected_out_of_alphabet_count": rejected_lexicon_count,
        "performance_limits": [
            "The pair graph uses at most top_k candidate-bearing types by weight.",
            "Pair construction is quadratic in the selected type count and checks every candidate pair.",
            "The result uses fixed word boundaries, symbol units, and one injective key.",
        ],
        "infeasibility_certified": False,
    }

    if not counts:
        return {
            **common,
            "status": "empty_input",
            "feasible": True,
            "selected_type_count": 0,
            "omitted_type_count": 0,
            "selected_weight": 0,
            "omitted_weight": 0,
            "conflict_pair_count": 0,
            "clique_bound": 0,
            "upper_bound": 0,
            "cliques": [],
        }

    if len(cipher_symbols) > len(alphabet):
        return {
            **common,
            "status": "infeasible_alphabet",
            "feasible": False,
            "infeasibility_certified": True,
            "selected_type_count": 0,
            "omitted_type_count": 0,
            "selected_weight": 0,
            "omitted_weight": 0,
            "conflict_pair_count": 0,
            "clique_bound": None,
            "upper_bound": None,
            "cliques": [],
        }

    ranked = sorted(candidate_words, key=lambda word: (-counts[word], word))
    if top_k is None:
        selected = ranked
        omitted: list[tuple[str, ...]] = []
    else:
        selected = ranked[:top_k]
        omitted = ranked[top_k:]
    selected_tuple = tuple(selected)
    graph, edge_count = _conflict_graph(selected_tuple, candidates)
    cliques = _greedy_clique_partition(selected_tuple, counts, graph)
    clique_rows: list[dict[str, Any]] = []
    clique_bound = 0
    for clique in cliques:
        max_weight = max(counts[word] for word in clique)
        clique_bound += max_weight
        clique_rows.append(
            {
                "types": [_word_list(word) for word in clique],
                "max_weight": max_weight,
                "bound": max_weight,
            }
        )
    omitted_weight = sum(counts[word] for word in omitted)
    selected_weight = sum(counts[word] for word in selected)
    return {
        **common,
        "status": "no_candidates" if not candidate_words else "ok",
        "feasible": True,
        "selected_type_count": len(selected),
        "omitted_type_count": len(omitted),
        "selected_weight": selected_weight,
        "omitted_weight": omitted_weight,
        "conflict_pair_count": edge_count,
        "clique_bound": clique_bound,
        "upper_bound": clique_bound + omitted_weight,
        "cliques": clique_rows,
    }


pair_bound = pair_conflict_upper_bound


__all__ = ["pair_conflict_upper_bound", "pair_bound"]
