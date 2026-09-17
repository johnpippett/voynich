"""Memory-conscious bitset adapter for the pivot-group upper bound.

The adapter uses the reviewed frozen homophonic bitset engine.  It stores lane
metadata and temporary group masks, not a second persistent candidate cache.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from types import MappingProxyType
from typing import Any, TypeAlias

from experiments.group_bound.pivot import (
    CandidateConstructionLimit,
    PivotGroupBound,
)
from experiments.homophonic import bitset_bound as frozen_bitset
from experiments.homophonic.solver import _normalise_alphabet


Word: TypeAlias = tuple[str, ...]
FROZEN_BITSET_SOURCE_SHA256 = (
    "8ab50b9700497cc493e0ba79a9fc6d452cf95e5b8c7d9d19d0de08b567000f76"
)


class BitsetConstructionError(ValueError):
    """The adapter cannot construct a complete safe bitset bound."""


class BitsetCompatibilityError(BitsetConstructionError):
    """The frozen bitset private layout does not match this adapter."""


@dataclass(frozen=True, slots=True)
class _Lane:
    word: Word
    weight: int
    high: int


@dataclass(frozen=True, slots=True)
class _Group:
    pivot: str
    words: tuple[Word, ...]
    highs: tuple[int, ...]
    weight: int


def _validate_limit(value: int | None, field: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{field} must be a non-negative integer or None")
    return value


def _source_sha256() -> str:
    module_path = getattr(frozen_bitset, "__file__", None)
    if not isinstance(module_path, str):
        raise BitsetCompatibilityError("frozen bitset source path is unavailable")
    try:
        return sha256(Path(module_path).read_bytes()).hexdigest()
    except OSError as exc:
        raise BitsetCompatibilityError(
            "frozen bitset source cannot be inspected"
        ) from exc


def _mask_size_upper_bound(
    cache: tuple[tuple[Word, int, tuple[Word, ...]], ...],
    cipher_symbols: tuple[str, ...],
    alphabet: tuple[str, ...],
    capacity: int | None,
) -> tuple[int, int]:
    slot_count = sum(len(rows) + 1 for _word, _weight, rows in cache)
    byte_count = (slot_count + 7) // 8
    mapping_pairs: set[tuple[str, str]] = set()
    weight_bits: set[int] = set()
    for cipher_word, weight, rows in cache:
        remaining_weight = weight
        while remaining_weight:
            lowest_bit = remaining_weight & -remaining_weight
            weight_bits.add(lowest_bit.bit_length() - 1)
            remaining_weight ^= lowest_bit
        for plaintext_word in rows:
            assignment: dict[str, str] = {}
            for cipher_symbol, plain_symbol in zip(
                cipher_word, plaintext_word, strict=True
            ):
                previous = assignment.get(cipher_symbol)
                if previous is not None and previous != plain_symbol:
                    raise BitsetCompatibilityError(
                        "candidate cache contains an inconsistent repeated unit"
                    )
                assignment[cipher_symbol] = plain_symbol
            mapping_pairs.update(assignment.items())
    mask_count = (
        3
        + len(cipher_symbols)
        + len(mapping_pairs)
        + (0 if capacity is None else len(alphabet) * (capacity + 1))
        + len(weight_bits)
    )
    return slot_count, byte_count * mask_count


def _validate_engine_layout(
    engine: object,
    *,
    expected_cipher_symbols: tuple[str, ...],
    expected_alphabet: tuple[str, ...],
    expected_capacity: int | None,
    expected_candidate_count: int,
    expected_lane_count: int,
    expected_slot_count: int,
) -> dict[str, int]:
    required = (
        "_capacity",
        "_cipher_symbols",
        "_plain_symbols",
        "_real_mask",
        "_high_sentinels",
        "_low_lane_bits",
        "_presence_masks",
        "_mapping_masks",
        "_preimage_size_masks",
        "_weight_bit_masks",
        "_capacity_mask",
    )
    for field in required:
        if not hasattr(engine, field):
            raise BitsetCompatibilityError(
                f"frozen bitset private field is missing: {field}"
            )

    try:
        metadata = engine.metadata  # type: ignore[attr-defined]
    except (AttributeError, TypeError) as exc:
        raise BitsetCompatibilityError(
            "frozen bitset metadata is unavailable"
        ) from exc
    if not isinstance(metadata, Mapping):
        raise BitsetCompatibilityError("frozen bitset metadata is not a mapping")
    metadata_keys = (
        "lane_count",
        "candidate_count",
        "slot_count",
        "sentinel_count",
        "estimated_storage_bytes",
    )
    for field in metadata_keys:
        value = metadata.get(field)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise BitsetCompatibilityError(
                f"frozen bitset metadata field is invalid: {field}"
            )
    if metadata["lane_count"] != expected_lane_count:
        raise BitsetCompatibilityError("frozen bitset lane count does not match")
    if metadata["candidate_count"] != expected_candidate_count:
        raise BitsetCompatibilityError(
            "frozen bitset candidate count does not match"
        )
    if metadata["slot_count"] != expected_slot_count:
        raise BitsetCompatibilityError("frozen bitset slot count does not match")
    if metadata["sentinel_count"] != expected_lane_count:
        raise BitsetCompatibilityError("frozen bitset sentinel count does not match")

    if engine._capacity != expected_capacity:  # type: ignore[attr-defined]
        raise BitsetCompatibilityError("frozen bitset capacity does not match")
    if tuple(engine._cipher_symbols) != expected_cipher_symbols:  # type: ignore[attr-defined]
        raise BitsetCompatibilityError("frozen bitset cipher symbols do not match")
    if tuple(engine._plain_symbols) != expected_alphabet:  # type: ignore[attr-defined]
        raise BitsetCompatibilityError("frozen bitset alphabet does not match")

    integer_fields = (
        "_real_mask",
        "_high_sentinels",
        "_low_lane_bits",
    )
    for field in integer_fields:
        value = getattr(engine, field)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise BitsetCompatibilityError(f"frozen bitset mask is invalid: {field}")
    mask_limit = (1 << expected_slot_count) - 1 if expected_slot_count else 0
    for field in integer_fields:
        if getattr(engine, field) & ~mask_limit:
            raise BitsetCompatibilityError(f"frozen bitset mask exceeds slots: {field}")

    presence_masks = engine._presence_masks  # type: ignore[attr-defined]
    if not isinstance(presence_masks, Mapping):
        raise BitsetCompatibilityError("frozen presence masks are not a mapping")
    if set(presence_masks) != set(expected_cipher_symbols):
        raise BitsetCompatibilityError("frozen presence mask keys do not match")
    for mask in presence_masks.values():
        if isinstance(mask, bool) or not isinstance(mask, int) or mask < 0:
            raise BitsetCompatibilityError("frozen presence mask is invalid")
        if mask & ~engine._real_mask:  # type: ignore[attr-defined]
            raise BitsetCompatibilityError("frozen presence mask exceeds candidates")

    mapping_masks = engine._mapping_masks  # type: ignore[attr-defined]
    if not isinstance(mapping_masks, Mapping):
        raise BitsetCompatibilityError("frozen mapping masks are not a mapping")
    for pair, mask in mapping_masks.items():
        if (
            not isinstance(pair, tuple)
            or len(pair) != 2
            or pair[0] not in expected_cipher_symbols
            or pair[1] not in expected_alphabet
        ):
            raise BitsetCompatibilityError("frozen mapping mask key is invalid")
        if isinstance(mask, bool) or not isinstance(mask, int) or mask < 0:
            raise BitsetCompatibilityError("frozen mapping mask is invalid")
        if mask & ~engine._real_mask:  # type: ignore[attr-defined]
            raise BitsetCompatibilityError("frozen mapping mask exceeds candidates")

    preimage_masks = engine._preimage_size_masks  # type: ignore[attr-defined]
    if not isinstance(preimage_masks, Mapping):
        raise BitsetCompatibilityError("frozen preimage masks are not a mapping")
    if set(preimage_masks) != set(expected_alphabet):
        raise BitsetCompatibilityError("frozen preimage mask keys do not match")
    expected_sizes = set(range((expected_capacity or 0) + 1))
    for masks in preimage_masks.values():
        if not isinstance(masks, Mapping) or set(masks) != expected_sizes:
            raise BitsetCompatibilityError("frozen preimage mask shape does not match")
        for mask in masks.values():
            if isinstance(mask, bool) or not isinstance(mask, int) or mask < 0:
                raise BitsetCompatibilityError("frozen preimage mask is invalid")
            if mask & ~engine._real_mask:  # type: ignore[attr-defined]
                raise BitsetCompatibilityError("frozen preimage mask exceeds candidates")

    weight_masks = engine._weight_bit_masks  # type: ignore[attr-defined]
    if not isinstance(weight_masks, tuple):
        raise BitsetCompatibilityError("frozen weight masks are not a tuple")
    seen_weight_bits: set[int] = set()
    for pair in weight_masks:
        if (
            not isinstance(pair, tuple)
            or len(pair) != 2
            or isinstance(pair[0], bool)
            or not isinstance(pair[0], int)
            or pair[0] < 0
            or pair[0] in seen_weight_bits
            or isinstance(pair[1], bool)
            or not isinstance(pair[1], int)
            or pair[1] < 0
            or pair[1] & ~mask_limit
        ):
            raise BitsetCompatibilityError("frozen weight mask is invalid")
        seen_weight_bits.add(pair[0])
    if not callable(engine._capacity_mask):  # type: ignore[attr-defined]
        raise BitsetCompatibilityError("frozen capacity mask helper is invalid")
    return dict(metadata)


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


class BitsetPivotGroupBound:
    """Use the frozen candidate masks for exact pivot-group queries."""

    __slots__ = (
        "_alphabet",
        "_capacity",
        "_cipher_symbols",
        "_counts",
        "_engine",
        "_feasible",
        "_groups",
        "_metadata",
        "_residual_lanes",
        "_source_sha256",
    )

    def __init__(
        self,
        ciphertext_counts: Mapping[str | Word, int],
        plaintext_lexicon: Iterable[str | Word],
        plaintext_alphabet: Iterable[str] | str,
        *,
        capacity: int | None = 1,
        groups: object | None = None,
        max_candidate_rows: int | None = None,
        max_estimated_storage_bytes: int | None = None,
    ) -> None:
        max_estimated_storage_bytes = _validate_limit(
            max_estimated_storage_bytes,
            "max_estimated_storage_bytes",
        )
        source_sha256 = _source_sha256()
        if source_sha256 != FROZEN_BITSET_SOURCE_SHA256:
            raise BitsetCompatibilityError(
                "frozen bitset source hash does not match the reviewed layout"
            )
        alphabet = _normalise_alphabet(plaintext_alphabet)
        try:
            scalar = PivotGroupBound(
                ciphertext_counts,
                plaintext_lexicon,
                alphabet,
                capacity=capacity,
                groups=groups,
                max_candidate_rows=max_candidate_rows,
            )
        except CandidateConstructionLimit as exc:
            raise BitsetConstructionError(str(exc)) from exc

        cache = scalar.candidate_cache
        counts_for_engine = {
            word: weight for word, weight, _rows in cache
        }
        candidates_for_engine = {
            word: rows for word, _weight, rows in cache
        }
        cipher_symbols = tuple(
            sorted({symbol for word in counts_for_engine for symbol in word})
        )
        slot_count, storage_upper_bound = _mask_size_upper_bound(
            cache,
            cipher_symbols,
            alphabet,
            scalar.metadata["capacity"],
        )
        if (
            max_estimated_storage_bytes is not None
            and storage_upper_bound > max_estimated_storage_bytes
        ):
            raise BitsetConstructionError(
                "declared bitset storage estimate limit exceeded"
            )

        feasible = not (
            scalar.metadata["capacity"] is not None
            and scalar.metadata["capacity"] * len(alphabet) < len(cipher_symbols)
        )
        actual_metadata: dict[str, int] | None = None
        engine: object | None = None
        if feasible:
            engine = frozen_bitset.BitsetBound(
                counts_for_engine,
                candidates_for_engine,
                alphabet,
                capacity=scalar.metadata["capacity"],
            )
            actual_metadata = _validate_engine_layout(
                engine,
                expected_cipher_symbols=cipher_symbols,
                expected_alphabet=alphabet,
                expected_capacity=scalar.metadata["capacity"],
                expected_candidate_count=scalar.metadata["candidate_count_total"],
                expected_lane_count=scalar.metadata["cipher_type_count"],
                expected_slot_count=slot_count,
            )
            if actual_metadata["estimated_storage_bytes"] > storage_upper_bound:
                raise BitsetCompatibilityError(
                    "frozen storage estimate exceeds the adapter upper estimate"
                )
            if (
                max_estimated_storage_bytes is not None
                and actual_metadata["estimated_storage_bytes"]
                > max_estimated_storage_bytes
            ):
                raise BitsetConstructionError(
                    "frozen bitset storage estimate limit exceeded"
                )

        lane_by_word: dict[Word, _Lane] = {}
        slot = 0
        for word, weight, rows in cache:
            high = slot + len(rows)
            lane_by_word[word] = _Lane(word, weight, high)
            slot = high + 1

        normalized_groups: list[_Group] = []
        grouped_words: set[Word] = set()
        for pivot, words in scalar.groups:
            highs = tuple(lane_by_word[word].high for word in words)
            normalized_groups.append(
                _Group(
                    pivot,
                    words,
                    highs,
                    sum(lane_by_word[word].weight for word in words),
                )
            )
            grouped_words.update(words)
        residual_lanes = tuple(
            lane for word, lane in lane_by_word.items() if word not in grouped_words
        )

        self._alphabet = alphabet
        self._capacity = scalar.metadata["capacity"]
        self._cipher_symbols = cipher_symbols
        self._counts = MappingProxyType(dict(counts_for_engine))
        self._engine = engine
        self._feasible = feasible
        self._groups = tuple(normalized_groups)
        self._residual_lanes = residual_lanes
        self._source_sha256 = source_sha256
        self._metadata = MappingProxyType({
            **scalar.metadata,
            "engine": "BitsetBound",
            "source_sha256": source_sha256,
            "candidate_rows_complete": True,
            "slot_count": slot_count,
            "estimated_storage_upper_bound_bytes": storage_upper_bound,
            "max_estimated_storage_bytes": max_estimated_storage_bytes,
            "storage_estimate_is_not_os_memory_limit": True,
            "frozen_estimated_storage_bytes": (
                None if actual_metadata is None
                else actual_metadata["estimated_storage_bytes"]
            ),
        })
        del candidates_for_engine
        del counts_for_engine
        del cache
        del scalar

    @property
    def metadata(self) -> dict[str, Any]:
        """Return adapter metadata without exposing the frozen engine."""

        return dict(self._metadata)

    @property
    def groups(self) -> tuple[tuple[str, tuple[Word, ...]], ...]:
        """Return immutable group specifications."""

        return tuple((group.pivot, group.words) for group in self._groups)

    def _active_mask(self, partial_key: Mapping[str, str]) -> int:
        if self._engine is None:
            return 0
        engine = self._engine
        active = engine._real_mask  # type: ignore[attr-defined]
        assigned_units: dict[str, list[str]] = {}
        for cipher_symbol, plain_symbol in partial_key.items():
            presence = engine._presence_masks[cipher_symbol]  # type: ignore[attr-defined]
            mapping = engine._mapping_masks.get(  # type: ignore[attr-defined]
                (cipher_symbol, plain_symbol),
                0,
            )
            active &= (~presence | mapping) & engine._real_mask  # type: ignore[attr-defined]
            assigned_units.setdefault(plain_symbol, []).append(cipher_symbol)
            if not active:
                return 0
        if self._capacity is not None:
            for plain_symbol, units in assigned_units.items():
                active &= engine._capacity_mask(  # type: ignore[attr-defined]
                    plain_symbol,
                    tuple(sorted(units)),
                )
                if not active:
                    return 0
        return active

    def _child_mask(
        self,
        active: int,
        partial_key: Mapping[str, str],
        cipher_symbol: str,
        plain_symbol: str,
    ) -> int:
        if self._engine is None:
            return 0
        engine = self._engine
        presence = engine._presence_masks[cipher_symbol]  # type: ignore[attr-defined]
        mapping = engine._mapping_masks.get(  # type: ignore[attr-defined]
            (cipher_symbol, plain_symbol),
            0,
        )
        child = active & (~presence | mapping) & engine._real_mask  # type: ignore[attr-defined]
        if self._capacity is not None:
            units = [
                unit
                for unit, value in partial_key.items()
                if value == plain_symbol
            ]
            units.append(cipher_symbol)
            child &= engine._capacity_mask(  # type: ignore[attr-defined]
                plain_symbol,
                tuple(sorted(units)),
            )
        return child

    def _flags(self, active: int) -> int:
        engine = self._engine
        if engine is None:
            return 0
        return (
            (active | engine._high_sentinels)  # type: ignore[attr-defined]
            - engine._low_lane_bits  # type: ignore[attr-defined]
        ) & engine._high_sentinels  # type: ignore[attr-defined]

    def _score_flags(self, flags: int) -> int:
        engine = self._engine
        if engine is None:
            return 0
        return sum(
            (flags & mask).bit_count() << bit
            for bit, mask in engine._weight_bit_masks  # type: ignore[attr-defined]
        )

    @staticmethod
    def _high_mask(highs: tuple[int, ...]) -> int:
        mask = 0
        for high in highs:
            mask |= 1 << high
        return mask

    def _validate_partial_key(
        self,
        partial_key: Mapping[str, str] | None,
    ) -> dict[str, str]:
        return _validate_partial_key(
            partial_key,
            self._cipher_symbols,
            self._alphabet,
            self._capacity,
        )

    def bound(self, partial_key: Mapping[str, str] | None = None) -> dict[str, Any]:
        """Return exact bitset-backed group and independent upper bounds."""

        normalized_key = self._validate_partial_key(partial_key)
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
            "metadata": self.metadata,
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

        active = self._active_mask(normalized_key)
        flags = self._flags(active)
        independent_bound = self._score_flags(flags)
        residual_highs = tuple(lane.high for lane in self._residual_lanes)
        residual_mask = self._high_mask(residual_highs)
        residual_bound = self._score_flags(flags & residual_mask)
        group_records: list[dict[str, Any]] = []
        group_bound = residual_bound
        usage = Counter(normalized_key.values())

        for group in self._groups:
            group_mask = self._high_mask(group.highs)
            active_word_count = (flags & group_mask).bit_count()
            if group.pivot in normalized_key:
                legal_values = (normalized_key[group.pivot],)
            else:
                legal_values = tuple(
                    symbol
                    for symbol in self._alphabet
                    if self._capacity is None or usage[symbol] < self._capacity
                )
            pivot_value_scores: dict[str, int] = {}
            for value in legal_values:
                if group.pivot in normalized_key:
                    child_active = active
                else:
                    child_active = self._child_mask(
                        active,
                        normalized_key,
                        group.pivot,
                        value,
                    )
                child_flags = self._flags(child_active)
                pivot_value_scores[value] = self._score_flags(
                    child_flags & group_mask
                )
            contribution = max(pivot_value_scores.values(), default=0)
            group_bound += contribution
            group_records.append({
                "pivot": group.pivot,
                "words": [list(word) for word in group.words],
                "weight": group.weight,
                "active_word_count": active_word_count,
                "pivot_value_scores": pivot_value_scores,
                "bound": contribution,
            })
            del group_mask

        if group_bound > independent_bound:
            raise BitsetCompatibilityError(
                "bitset pivot-group bound exceeded independent bound"
            )
        return {
            **base,
            "group_bound": group_bound,
            "independent_bound": independent_bound,
            "bound": group_bound,
            "groups": group_records,
            "ungrouped_words": [
                list(lane.word) for lane in self._residual_lanes
            ],
        }


def bitset_pivot_group_bound(
    ciphertext_counts: Mapping[str | Word, int],
    plaintext_lexicon: Iterable[str | Word],
    plaintext_alphabet: Iterable[str] | str,
    *,
    capacity: int | None = 1,
    partial_key: Mapping[str, str] | None = None,
    groups: object | None = None,
    max_candidate_rows: int | None = None,
    max_estimated_storage_bytes: int | None = None,
) -> dict[str, Any]:
    """Build the adapter and return one bitset-backed bound query."""

    return BitsetPivotGroupBound(
        ciphertext_counts,
        plaintext_lexicon,
        plaintext_alphabet,
        capacity=capacity,
        groups=groups,
        max_candidate_rows=max_candidate_rows,
        max_estimated_storage_bytes=max_estimated_storage_bytes,
    ).bound(partial_key)


__all__ = [
    "BitsetCompatibilityError",
    "BitsetConstructionError",
    "BitsetPivotGroupBound",
    "FROZEN_BITSET_SOURCE_SHA256",
    "bitset_pivot_group_bound",
]
