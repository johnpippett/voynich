"""Enumerate equal-score completions in one declared finite key domain.

This module is a bounded completeness primitive. It checks every feasible map
in the supplied fixed domain when no limit stops the depth-first search. It
does not prove that fixed assignments are forced or that the target is a
global optimum outside this domain.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping
import hashlib
import json
from typing import Any

from experiments.homophonic.solver import (
    _normalise_alphabet,
    _normalise_cipher_counts,
    _normalise_lexicon,
)


Word = str | tuple[str, ...]
Capacity = int | None

_DEFAULT_MAX_PRODUCT = 1_000_000
_DEFAULT_NODE_BUDGET = 1_000_000


def _validate_capacity(capacity: Capacity) -> Capacity:
    if capacity is None:
        return None
    if isinstance(capacity, bool) or not isinstance(capacity, int):
        raise ValueError("capacity must be 1, 2, or None")
    if capacity not in (1, 2):
        raise ValueError("capacity must be 1, 2, or None")
    return capacity


def _validate_nonnegative_integer(value: int | None, field: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{field} must be a non-negative integer or None")
    return value


def _validate_fixed_key(
    fixed_key: Mapping[str, str] | None,
    cipher_units: tuple[str, ...],
    alphabet: tuple[str, ...],
    capacity: Capacity,
) -> dict[str, str]:
    if fixed_key is None:
        return {}
    if not isinstance(fixed_key, Mapping):
        raise TypeError("fixed_key must be a mapping")

    cipher_set = set(cipher_units)
    alphabet_set = set(alphabet)
    result: dict[str, str] = {}
    for cipher_symbol, plain_symbol in fixed_key.items():
        if not isinstance(cipher_symbol, str) or not isinstance(plain_symbol, str):
            raise ValueError("fixed_key symbols must be strings")
        if cipher_symbol not in cipher_set:
            raise ValueError("fixed_key contains a symbol absent from ciphertext")
        if plain_symbol not in alphabet_set:
            raise ValueError("fixed_key values must be in plaintext_alphabet")
        result[cipher_symbol] = plain_symbol

    if capacity is not None and any(
        count > capacity for count in Counter(result.values()).values()
    ):
        raise ValueError("fixed_key exceeds plaintext-letter capacity")
    return dict(sorted(result.items()))


def _score_key(
    key: Mapping[str, str],
    ciphertext_counts: Mapping[tuple[str, ...], int],
    lexicon: set[tuple[str, ...]],
) -> int:
    score = 0
    for cipher_word, weight in ciphertext_counts.items():
        decoded = tuple(key[symbol] for symbol in cipher_word)
        if decoded in lexicon:
            score += weight
    return score


def _digest(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _objective_domain_fingerprint(
    ciphertext_counts: Mapping[tuple[str, ...], int],
    lexicon: set[tuple[str, ...]],
    alphabet: tuple[str, ...],
    capacity: Capacity,
) -> str:
    payload = {
        "ciphertext_counts": [
            [list(word), weight]
            for word, weight in sorted(ciphertext_counts.items())
        ],
        "plaintext_lexicon": [list(word) for word in sorted(lexicon)],
        "plaintext_alphabet": list(alphabet),
        "capacity": capacity,
    }
    return _digest(payload)


def _domain_fingerprint(
    ciphertext_counts: Mapping[tuple[str, ...], int],
    lexicon: set[tuple[str, ...]],
    alphabet: tuple[str, ...],
    capacity: Capacity,
    fixed_key: Mapping[str, str],
) -> str:
    payload = {
        "ciphertext_counts": [
            [list(word), weight]
            for word, weight in sorted(ciphertext_counts.items())
        ],
        "plaintext_lexicon": [list(word) for word in sorted(lexicon)],
        "plaintext_alphabet": list(alphabet),
        "capacity": capacity,
        "fixed_key": [[symbol, fixed_key[symbol]] for symbol in sorted(fixed_key)],
    }
    return _digest(payload)


def _base_result(
    *,
    objective_domain_fingerprint: str,
    domain_fingerprint: str,
    fixed_key: Mapping[str, str],
    alphabet: tuple[str, ...],
    cipher_units: tuple[str, ...],
    free_units: tuple[str, ...],
    capacity: Capacity,
    target: int,
    product_bound: int,
    max_product: int | None,
    node_budget: int | None,
    lexicon_raw_entry_count: int,
    lexicon_unique_normalized_count: int,
    lexicon_rejected_out_of_alphabet_count: int,
) -> dict[str, Any]:
    return {
        "objective_domain_fingerprint": objective_domain_fingerprint,
        "domain_fingerprint": domain_fingerprint,
        "fixed_assignments": dict(fixed_key),
        "full_alphabet": list(alphabet),
        "cipher_units": list(cipher_units),
        "free_units": list(free_units),
        "capacity": capacity,
        "target": target,
        "product_bound": product_bound,
        "max_product": max_product,
        "node_budget": node_budget,
        "lexicon_raw_entry_count": lexicon_raw_entry_count,
        "lexicon_unique_normalized_count": lexicon_unique_normalized_count,
        "lexicon_rejected_out_of_alphabet_count": (
            lexicon_rejected_out_of_alphabet_count
        ),
        "visited_nodes": 0,
        "feasible_leaves": 0,
        "capacity_prunes": 0,
        "collected_maps": [],
        "status": "not_complete",
        "reason": "not_started",
        "truncation": False,
        "complete": False,
        "claims_global_optimum": False,
        "claims_fixed_assignments_forced": False,
        "scope": "all feasible completions of the supplied fixed domain",
    }


def enumerate_equal_score_completions(
    ciphertext_counts: Mapping[Word, int],
    plaintext_lexicon: Iterable[Word],
    plaintext_alphabet: Iterable[str] | str,
    *,
    capacity: Capacity = 1,
    fixed_key: Mapping[str, str] | None = None,
    target: int = 0,
    max_product: int | None = _DEFAULT_MAX_PRODUCT,
    node_budget: int | None = _DEFAULT_NODE_BUDGET,
) -> dict[str, Any]:
    """Enumerate complete keys with score equal to ``target``.

    ``max_product`` limits the raw product of alphabet choices before search.
    ``node_budget`` limits visited depth-first states, including the root.
    Pass ``None`` to disable either limit. A complete result covers only the
    supplied fixed domain. A score above ``target`` returns a conflict.
    """

    capacity = _validate_capacity(capacity)
    max_product = _validate_nonnegative_integer(max_product, "max_product")
    node_budget = _validate_nonnegative_integer(node_budget, "node_budget")
    if isinstance(target, bool) or not isinstance(target, int) or target < 0:
        raise ValueError("target must be a non-negative integer")

    counts = _normalise_cipher_counts(ciphertext_counts)
    alphabet = _normalise_alphabet(plaintext_alphabet)
    (
        lexicon,
        lexicon_raw_entry_count,
        lexicon_unique_normalized_count,
        lexicon_rejected_out_of_alphabet_count,
    ) = _normalise_lexicon(plaintext_lexicon, alphabet)
    cipher_units = tuple(sorted({symbol for word in counts for symbol in word}))
    fixed = _validate_fixed_key(fixed_key, cipher_units, alphabet, capacity)
    free_units = tuple(symbol for symbol in cipher_units if symbol not in fixed)
    product_bound = len(alphabet) ** len(free_units)
    fingerprint = _domain_fingerprint(
        counts,
        lexicon,
        alphabet,
        capacity,
        fixed,
    )
    objective_fingerprint = _objective_domain_fingerprint(
        counts,
        lexicon,
        alphabet,
        capacity,
    )
    result = _base_result(
        objective_domain_fingerprint=objective_fingerprint,
        domain_fingerprint=fingerprint,
        fixed_key=fixed,
        alphabet=alphabet,
        cipher_units=cipher_units,
        free_units=free_units,
        capacity=capacity,
        target=target,
        product_bound=product_bound,
        max_product=max_product,
        node_budget=node_budget,
        lexicon_raw_entry_count=lexicon_raw_entry_count,
        lexicon_unique_normalized_count=lexicon_unique_normalized_count,
        lexicon_rejected_out_of_alphabet_count=(
            lexicon_rejected_out_of_alphabet_count
        ),
    )

    if capacity is not None and len(cipher_units) > len(alphabet) * capacity:
        result.update(
            status="complete",
            reason="capacity_infeasible",
            complete=True,
            capacity_prunes=1,
        )
        return result

    if max_product is not None and product_bound > max_product:
        result.update(
            status="not_complete",
            reason="product_limit",
            truncation="product_limit",
        )
        return result

    key = dict(fixed)
    usage = Counter(key.values())
    conflict_key: dict[str, str] | None = None
    conflict_score: int | None = None
    truncated = False

    def enter_node() -> bool:
        nonlocal truncated
        if node_budget is not None and result["visited_nodes"] >= node_budget:
            truncated = True
            result["truncation"] = "node_budget"
            result["reason"] = "node_budget"
            return False
        result["visited_nodes"] += 1
        return True

    def record_leaf() -> None:
        nonlocal conflict_key, conflict_score
        result["feasible_leaves"] += 1
        complete_key = dict(sorted(key.items()))
        score = _score_key(complete_key, counts, lexicon)
        if score > target:
            conflict_key = complete_key
            conflict_score = score
        elif score == target:
            result["collected_maps"].append(complete_key)

    if enter_node():
        if not free_units:
            record_leaf()
        else:
            # Each frame stores the free-unit depth and its next alphabet index.
            # The stack gives the same lexical depth-first order as recursion.
            stack: list[list[int]] = [[0, 0]]
            while stack and not truncated and conflict_key is None:
                depth, next_index = stack[-1]
                if next_index >= len(alphabet):
                    stack.pop()
                    if depth:
                        cipher_symbol = free_units[depth - 1]
                        plain_symbol = key.pop(cipher_symbol)
                        usage[plain_symbol] -= 1
                    continue

                stack[-1][1] += 1
                plain_symbol = alphabet[next_index]
                if capacity is not None and usage[plain_symbol] >= capacity:
                    result["capacity_prunes"] += 1
                    continue

                cipher_symbol = free_units[depth]
                key[cipher_symbol] = plain_symbol
                usage[plain_symbol] += 1
                child_depth = depth + 1
                if not enter_node():
                    usage[plain_symbol] -= 1
                    del key[cipher_symbol]
                    break
                if child_depth == len(free_units):
                    record_leaf()
                    usage[plain_symbol] -= 1
                    del key[cipher_symbol]
                else:
                    stack.append([child_depth, 0])

    if conflict_key is not None:
        result.update(
            status="certificate_conflict",
            reason="complete_key_above_target",
            conflict_key=conflict_key,
            conflict_score=conflict_score,
        )
        return result

    if truncated:
        result["status"] = "not_complete"
        result["complete"] = False
        return result

    result.update(
        status="complete",
        reason="all_domain_completions_checked",
        complete=True,
    )
    return result


__all__ = ["enumerate_equal_score_completions"]
