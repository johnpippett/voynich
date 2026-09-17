"""Count capacity-feasible completions that preserve positive lexical hits."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from math import comb
from typing import Any

from experiments.homophonic.solver import (
    _normalise_alphabet,
    _normalise_cipher_counts,
    _normalise_lexicon,
    _validate_capacity,
    _validate_initial_key,
)


def _completion_count(
    free_cipher_count: int,
    residual_capacities: tuple[int, ...],
) -> int:
    """Count assignments of labeled units under finite letter capacities."""

    ways = [0] * (free_cipher_count + 1)
    ways[0] = 1
    for capacity in residual_capacities:
        updated = [0] * (free_cipher_count + 1)
        for assigned in range(free_cipher_count + 1):
            updated[assigned] = sum(
                comb(assigned, added) * ways[assigned - added]
                for added in range(min(capacity, assigned) + 1)
            )
        ways = updated
    return ways[free_cipher_count]


def preserved_hit_completions(
    ciphertext_counts: Mapping[Any, int],
    plaintext_lexicon: Iterable[Any],
    plaintext_alphabet: Iterable[str] | str,
    key: Mapping[str, str] | None,
    *,
    capacity: int | None = 1,
) -> dict[str, Any]:
    """Count feasible key completions that cannot lower the supplied score.

    The supplied key must cover every cipher unit in ``ciphertext_counts``.
    Assignments used by positive-weight lexical hits remain fixed. All other
    labeled cipher units may receive any remaining capacity-feasible letters.
    A certified global optimum is required before this count is an optimal-key
    lower bound.
    """

    capacity = _validate_capacity(capacity)
    counts = _normalise_cipher_counts(ciphertext_counts)
    alphabet = _normalise_alphabet(plaintext_alphabet)
    lexicon, *_ = _normalise_lexicon(plaintext_lexicon, alphabet)
    domain = tuple(sorted({symbol for word in counts for symbol in word}))
    validated = _validate_initial_key(key, domain, alphabet, capacity)
    if set(validated) != set(domain):
        raise ValueError("The key must cover every ciphertext symbol.")

    covered: set[str] = set()
    incumbent_score = 0
    for word, weight in counts.items():
        decoded = tuple(validated[symbol] for symbol in word)
        if weight > 0 and decoded in lexicon:
            covered.update(word)
            incumbent_score += weight

    free_cipher_count = len(domain) - len(covered)
    covered_usage = {
        plain_symbol: sum(
            1
            for cipher_symbol in covered
            if validated[cipher_symbol] == plain_symbol
        )
        for plain_symbol in alphabet
    }

    if capacity is None:
        completion_count = len(alphabet) ** free_cipher_count
        free_plain_capacity = None
    else:
        residual_capacities = tuple(
            capacity - covered_usage[plain_symbol] for plain_symbol in alphabet
        )
        completion_count = _completion_count(
            free_cipher_count, residual_capacities
        )
        free_plain_capacity = sum(residual_capacities)

    return {
        "incumbent_score": incumbent_score,
        "cipher_symbol_count": len(domain),
        "plaintext_symbol_count": len(alphabet),
        "capacity": capacity,
        "covered_symbol_count": len(covered),
        "free_cipher_symbol_count": free_cipher_count,
        "free_plain_capacity": free_plain_capacity,
        "completion_count": completion_count,
        # Keep the lexical helper's field for callers that compare both APIs.
        "keys_preserving_current_hits": completion_count,
        "guarantee": (
            "Every counted key scores at least as high as the supplied key."
        ),
        "optimum_condition": (
            "If the supplied score is certified optimal, every counted key is "
            "also optimal."
        ),
        "limit": (
            "This count can omit other keys with equal or higher scores. It "
            "does not identify a historical key."
        ),
    }


__all__ = ["preserved_hit_completions"]
