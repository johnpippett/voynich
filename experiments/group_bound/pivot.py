"""Scalar pivot-group upper bounds for finite word-hit search.

The bound is a safe relaxation of the independent candidate bound.  It does
not search for a key, certify an optimum, or use a candidate sample.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, TypeAlias

from experiments.homophonic.solver import (
    _candidate_compatible,
    _normalise_alphabet,
    _normalise_cipher_counts,
    _normalise_lexicon,
    _normalise_word,
)


Word: TypeAlias = tuple[str, ...]
GroupInput: TypeAlias = (
    Mapping[str, Iterable[str | Word]]
    | Iterable[tuple[str, Iterable[str | Word]]]
    | Iterable[Mapping[str, object]]
)


class CandidateConstructionLimit(ValueError):
    """The complete root candidate cache exceeds its declared row limit."""


@dataclass(frozen=True)
class _Group:
    pivot: str
    words: tuple[Word, ...]


def _validate_capacity(capacity: int | None) -> int | None:
    if capacity is None:
        return None
    if isinstance(capacity, bool) or not isinstance(capacity, int):
        raise ValueError("capacity must be 1, 2, or None")
    if capacity not in (1, 2):
        raise ValueError("capacity must be 1, 2, or None")
    return capacity


def _validate_row_limit(limit: int | None) -> int | None:
    if limit is None:
        return None
    if isinstance(limit, bool) or not isinstance(limit, int) or limit < 0:
        raise ValueError("max_candidate_rows must be a non-negative integer or None")
    return limit


def _build_candidate_cache(
    counts: Mapping[Word, int],
    lexicon: set[Word],
    capacity: int | None,
    max_candidate_rows: int | None,
) -> tuple[tuple[Word, int, tuple[Word, ...]], ...]:
    by_length: dict[int, tuple[Word, ...]] = {}
    length_buckets: dict[int, list[Word]] = {}
    for word in sorted(lexicon):
        length_buckets.setdefault(len(word), []).append(word)
    by_length = {
        length: tuple(words) for length, words in length_buckets.items()
    }

    lanes: list[tuple[Word, int, tuple[Word, ...]]] = []
    candidate_count = 0
    for cipher_word, weight in counts.items():
        lane_values: list[Word] = []
        for candidate in by_length.get(len(cipher_word), ()):
            if not _candidate_compatible(cipher_word, candidate, {}, capacity):
                continue
            candidate_count += 1
            if max_candidate_rows is not None and candidate_count > max_candidate_rows:
                raise CandidateConstructionLimit(
                    "complete root candidate cache exceeds max_candidate_rows"
                )
            lane_values.append(candidate)
        lanes.append((cipher_word, weight, tuple(lane_values)))
    return tuple(lanes)


def _validate_partial_key(
    partial_key: Mapping[str, str] | None,
    cipher_symbols: tuple[str, ...],
    alphabet: tuple[str, ...],
    capacity: int | None,
) -> dict[str, str]:
    if partial_key is None:
        return {}
    if not isinstance(partial_key, Mapping):
        raise TypeError("partial_key must be a mapping")
    cipher_set = set(cipher_symbols)
    alphabet_set = set(alphabet)
    normalized: dict[str, str] = {}
    for cipher_symbol, plain_symbol in partial_key.items():
        if not isinstance(cipher_symbol, str) or not cipher_symbol:
            raise ValueError("partial_key symbols must be non-empty strings")
        if not isinstance(plain_symbol, str) or not plain_symbol:
            raise ValueError("partial_key values must be non-empty strings")
        if cipher_symbol not in cipher_set:
            raise ValueError("partial_key contains a symbol absent from ciphertext")
        if plain_symbol not in alphabet_set:
            raise ValueError("partial_key values must be in plaintext_alphabet")
        normalized[cipher_symbol] = plain_symbol
    if capacity is not None and any(
        count > capacity for count in Counter(normalized.values()).values()
    ):
        raise ValueError("partial_key exceeds plaintext-letter capacity")
    return dict(sorted(normalized.items()))


def _parse_group_spec(spec: object, index: int) -> tuple[object, object]:
    if isinstance(spec, Mapping):
        if set(spec) != {"pivot", "words"}:
            raise ValueError(
                f"group {index} mapping must contain only pivot and words"
            )
        return spec["pivot"], spec["words"]
    if type(spec) not in (tuple, list) or len(spec) != 2:
        raise ValueError(f"group {index} must be a (pivot, words) pair")
    return spec[0], spec[1]


def _normalise_groups(
    groups: GroupInput | None,
    counts: Mapping[Word, int],
    cipher_symbols: tuple[str, ...],
) -> tuple[_Group, ...]:
    if groups is None:
        return _static_groups(counts)

    if isinstance(groups, Mapping):
        raw_specs = list(groups.items())
    else:
        if isinstance(groups, (str, bytes)):
            raise ValueError("groups must contain group specifications")
        try:
            raw_specs = list(groups)
        except TypeError as exc:
            raise TypeError("groups must be an iterable of group specifications") from exc

    cipher_set = set(cipher_symbols)
    count_words = set(counts)
    seen_words: set[Word] = set()
    normalized: list[_Group] = []
    for index, raw_spec in enumerate(raw_specs):
        raw_pivot, raw_words = _parse_group_spec(raw_spec, index)
        if not isinstance(raw_pivot, str) or not raw_pivot:
            raise ValueError(f"group {index} pivot must be a non-empty symbol")
        if raw_pivot not in cipher_set:
            raise ValueError(f"group {index} pivot is absent from ciphertext")
        if isinstance(raw_words, (str, bytes, Mapping)):
            raise ValueError(f"group {index} words must be an iterable of words")
        try:
            word_values = list(raw_words)
        except TypeError as exc:
            raise ValueError(f"group {index} words must be an iterable of words") from exc
        if not word_values:
            raise ValueError(f"group {index} must contain at least one word")

        words: list[Word] = []
        local_words: set[Word] = set()
        for raw_word in word_values:
            word = _normalise_word(raw_word)
            if word not in count_words:
                raise ValueError(f"group {index} contains an unknown ciphertext word")
            if word in local_words or word in seen_words:
                raise ValueError("group word types must be unique across groups")
            if raw_pivot not in word:
                raise ValueError(f"group {index} pivot must occur in every word")
            local_words.add(word)
            words.append(word)
        seen_words.update(local_words)
        normalized.append(_Group(raw_pivot, tuple(sorted(words))))

    return tuple(sorted(normalized, key=lambda group: (group.pivot, group.words)))


def _static_groups(
    counts: Mapping[Word, int],
) -> tuple[_Group, ...]:
    """Group every non-empty candidate lane by its smallest cipher unit.

    Empty candidate lanes remain valid zero-contribution groups.
    """

    by_pivot: dict[str, list[Word]] = {}
    for word in counts:
        if not word:
            continue
        pivot = min(set(word))
        by_pivot.setdefault(pivot, []).append(word)
    return tuple(
        _Group(pivot, tuple(sorted(words)))
        for pivot, words in sorted(by_pivot.items())
    )


class PivotGroupBound:
    """Reusable scalar independent and pivot-group upper-bound cache.

    The constructor builds every root-compatible lexicon row.  A query filters
    those rows against one partial map and returns two integer upper bounds.
    """

    __slots__ = (
        "_alphabet",
        "_capacity",
        "_candidate_map",
        "_cipher_symbols",
        "_counts",
        "_feasible",
        "_groups",
        "_metadata",
        "_ungrouped",
    )

    def __init__(
        self,
        ciphertext_counts: Mapping[str | Word, int],
        plaintext_lexicon: Iterable[str | Word],
        plaintext_alphabet: Iterable[str] | str,
        *,
        capacity: int | None = 1,
        groups: GroupInput | None = None,
        max_candidate_rows: int | None = None,
    ) -> None:
        capacity = _validate_capacity(capacity)
        max_candidate_rows = _validate_row_limit(max_candidate_rows)
        counts = _normalise_cipher_counts(ciphertext_counts)
        alphabet = _normalise_alphabet(plaintext_alphabet)
        lexicon, raw_count, unique_count, rejected_count = _normalise_lexicon(
            plaintext_lexicon,
            alphabet,
        )
        cipher_symbols = tuple(
            sorted({symbol for word in counts for symbol in word})
        )
        lanes = _build_candidate_cache(
            counts,
            lexicon,
            capacity,
            max_candidate_rows,
        )
        candidate_map = MappingProxyType({
            word: lane for word, _weight, lane in lanes
        })
        normalized_groups = _normalise_groups(groups, counts, cipher_symbols)
        grouped_words = {
            word for group in normalized_groups for word in group.words
        }
        ungrouped = tuple(
            word for word in counts if word not in grouped_words
        )
        self._counts = MappingProxyType(dict(counts))
        self._alphabet = alphabet
        self._capacity = capacity
        self._cipher_symbols = cipher_symbols
        self._candidate_map = candidate_map
        self._groups = normalized_groups
        self._ungrouped = ungrouped
        self._feasible = not (
            capacity is not None
            and capacity * len(alphabet) < len(cipher_symbols)
        )
        candidate_count_total = sum(len(lane) for _word, _weight, lane in lanes)
        self._metadata = MappingProxyType({
            "capacity": capacity,
            "cipher_type_count": len(counts),
            "cipher_symbol_count": len(cipher_symbols),
            "candidate_count_total": candidate_count_total,
            "candidate_type_count": sum(bool(lane) for _word, _weight, lane in lanes),
            "missing_candidate_count": sum(
                not lane for _word, _weight, lane in lanes
            ),
            "group_count": len(normalized_groups),
            "ungrouped_type_count": len(ungrouped),
            "grouping": "explicit" if groups is not None else "static_min_symbol",
            "max_candidate_rows": max_candidate_rows,
            "lexicon_raw_entry_count": raw_count,
            "lexicon_unique_normalized_count": unique_count,
            "lexicon_usable_count": len(lexicon),
            "lexicon_rejected_out_of_alphabet_count": rejected_count,
            "candidate_rows_complete": True,
        })

    @property
    def metadata(self) -> dict[str, Any]:
        """Return construction metadata without exposing mutable cache state."""

        return dict(self._metadata)

    @property
    def candidate_cache(self) -> tuple[tuple[Word, int, tuple[Word, ...]], ...]:
        """Return an immutable snapshot of all root-compatible candidate rows."""

        return tuple(
            (word, self._counts[word], self._candidate_map[word])
            for word in self._counts
        )

    @property
    def groups(self) -> tuple[tuple[str, tuple[Word, ...]], ...]:
        """Return immutable pivot and word-type group specifications."""

        return tuple((group.pivot, group.words) for group in self._groups)

    def _active_candidates(
        self,
        word: Word,
        partial_key: Mapping[str, str],
    ) -> tuple[Word, ...]:
        return tuple(
            candidate
            for candidate in self._candidate_map[word]
            if _candidate_compatible(
                word,
                candidate,
                partial_key,
                self._capacity,
            )
        )

    def _independent_bound(self, partial_key: Mapping[str, str]) -> int:
        return sum(
            self._counts[word]
            for word in self._counts
            if self._active_candidates(word, partial_key)
        )

    def _group_result(
        self,
        group: _Group,
        partial_key: Mapping[str, str],
    ) -> tuple[int, dict[str, Any]]:
        usage = Counter(partial_key.values())
        if group.pivot in partial_key:
            legal_values = (partial_key[group.pivot],)
        else:
            legal_values = tuple(
                symbol
                for symbol in self._alphabet
                if self._capacity is None or usage[symbol] < self._capacity
            )
        value_scores = {symbol: 0 for symbol in legal_values}
        active_word_count = 0
        pivot_positions = {
            word: word.index(group.pivot) for word in group.words
        }
        for word in group.words:
            active = self._active_candidates(word, partial_key)
            if active:
                active_word_count += 1
            position = pivot_positions[word]
            for value in legal_values:
                if any(candidate[position] == value for candidate in active):
                    value_scores[value] += self._counts[word]
        group_bound = max(value_scores.values(), default=0)
        record = {
            "pivot": group.pivot,
            "words": [list(word) for word in group.words],
            "weight": sum(self._counts[word] for word in group.words),
            "active_word_count": active_word_count,
            "pivot_value_scores": dict(value_scores),
            "bound": group_bound,
        }
        return group_bound, record

    def bound(self, partial_key: Mapping[str, str] | None = None) -> dict[str, Any]:
        """Return the safe group and independent bounds for one partial map."""

        normalized_key = _validate_partial_key(
            partial_key,
            self._cipher_symbols,
            self._alphabet,
            self._capacity,
        )
        base: dict[str, Any] = {
            "partial_key": dict(normalized_key),
            "capacity": self._capacity,
            "status": "complete" if self._feasible else "infeasible_capacity",
            "feasible": self._feasible,
            "infeasibility_reason": None if self._feasible else "capacity",
            "candidate_rows_complete": True,
            "candidate_count_total": self._metadata["candidate_count_total"],
            "group_count": len(self._groups),
            "claims_global_optimality": False,
            "scope_limits": [
                "The result is an upper bound for the supplied finite lexicon and word counts.",
                "It uses fixed word boundaries and one total cipher-unit map.",
                "Group conflicts and cross-group capacity conflicts are relaxed.",
                "It does not certify an optimum or enumerate feasible maps.",
            ],
        }
        if not self._feasible:
            base.update({
                "group_bound": None,
                "independent_bound": None,
                "bound": None,
                "groups": [],
                "ungrouped_words": [],
            })
            return base

        independent_bound = self._independent_bound(normalized_key)
        group_records: list[dict[str, Any]] = []
        group_bound = 0
        for group in self._groups:
            value, record = self._group_result(group, normalized_key)
            group_bound += value
            group_records.append(record)
        ungrouped_bound = 0
        for word in self._ungrouped:
            if self._active_candidates(word, normalized_key):
                ungrouped_bound += self._counts[word]
        group_bound += ungrouped_bound
        if group_bound > independent_bound:
            raise RuntimeError("pivot-group bound exceeded independent bound")

        base.update({
            "group_bound": group_bound,
            "independent_bound": independent_bound,
            "bound": group_bound,
            "groups": group_records,
            "ungrouped_words": [list(word) for word in self._ungrouped],
        })
        return base


def pivot_group_bound(
    ciphertext_counts: Mapping[str | Word, int],
    plaintext_lexicon: Iterable[str | Word],
    plaintext_alphabet: Iterable[str] | str,
    *,
    capacity: int | None = 1,
    partial_key: Mapping[str, str] | None = None,
    groups: GroupInput | None = None,
    max_candidate_rows: int | None = None,
) -> dict[str, Any]:
    """Build a complete cache and return one pivot-group bound query."""

    return PivotGroupBound(
        ciphertext_counts,
        plaintext_lexicon,
        plaintext_alphabet,
        capacity=capacity,
        groups=groups,
        max_candidate_rows=max_candidate_rows,
    ).bound(partial_key)


__all__ = [
    "CandidateConstructionLimit",
    "PivotGroupBound",
    "pivot_group_bound",
]
