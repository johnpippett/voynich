"""Bitset upper bounds for the synthetic homophonic lexicon solver.

The bound keeps one bit per root-compatible candidate and one sentinel bit per
word lane. A partial map filters the active candidate bits. Sentinel bits make
the final weighted bit count include each word lane at most once.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping
from typing import TypeAlias


Word: TypeAlias = tuple[str, ...]
WordCounts: TypeAlias = Mapping[Word, int]
CandidateLists: TypeAlias = Mapping[Word, Iterable[Word]]
Capacity: TypeAlias = int | None


def _normalise_word(value: object, field: str) -> Word:
    if isinstance(value, str):
        return tuple(value)
    if isinstance(value, tuple) and all(
        isinstance(symbol, str) and symbol for symbol in value
    ):
        return value
    raise TypeError(f"{field} must contain strings or tuple[str, ...] words")


def _normalise_counts(ciphertext_counts: WordCounts) -> dict[Word, int]:
    if not isinstance(ciphertext_counts, Mapping):
        raise TypeError("ciphertext_counts must be a mapping")
    counts: dict[Word, int] = {}
    for raw_word, weight in ciphertext_counts.items():
        word = _normalise_word(raw_word, "ciphertext_counts")
        if not isinstance(weight, int) or isinstance(weight, bool) or weight < 0:
            raise ValueError("ciphertext weights must be non-negative integers")
        counts[word] = counts.get(word, 0) + weight
    return dict(sorted(counts.items()))


def _normalise_alphabet(alphabet: Iterable[str] | str) -> tuple[str, ...]:
    values = tuple(alphabet) if isinstance(alphabet, str) else tuple(alphabet)
    if not values or any(not isinstance(symbol, str) or not symbol for symbol in values):
        raise ValueError("plaintext_alphabet must contain non-empty symbols")
    if len(set(values)) != len(values):
        raise ValueError("plaintext_alphabet symbols must be unique")
    return values


def _normalise_capacity(capacity: Capacity) -> Capacity:
    if capacity is None:
        return None
    if isinstance(capacity, bool) or not isinstance(capacity, int):
        raise ValueError("capacity must be 1, 2, or None")
    if capacity not in (1, 2):
        raise ValueError("capacity must be 1, 2, or None")
    return capacity


def _set_byte_bit(mask: bytearray, bit: int) -> None:
    mask[bit >> 3] |= 1 << (bit & 7)


def _mask_size(mask: int) -> int:
    return (mask.bit_length() + 7) // 8


class BitsetBound:
    """Compute the scalar homophonic compatible-candidate upper bound.

    Candidate rows with inconsistent repeated cipher units or an over-capacity
    plaintext preimage are removed at construction. Capacity supports ``1``,
    ``2``, and ``None``. For capacity two, one partial preimage unit permits
    candidate preimages of size zero or one, or an overlapping candidate map. Two
    partial preimage units require the candidate preimage to be their subset.
    A bound call does not retain per-node bitsets.
    """

    def __init__(
        self,
        ciphertext_counts: WordCounts,
        candidates: CandidateLists,
        plaintext_alphabet: Iterable[str] | str,
        capacity: Capacity = 1,
    ) -> None:
        capacity = _normalise_capacity(capacity)
        counts = _normalise_counts(ciphertext_counts)
        alphabet = _normalise_alphabet(plaintext_alphabet)
        if not isinstance(candidates, Mapping):
            raise TypeError("candidates must be a mapping")

        raw_candidates: dict[Word, list[Word]] = {}
        for raw_cipher_word, raw_values in candidates.items():
            cipher_word = _normalise_word(raw_cipher_word, "candidates")
            try:
                values = tuple(raw_values)
            except TypeError as exc:
                raise TypeError("each candidate list must be iterable") from exc
            raw_candidates.setdefault(cipher_word, []).extend(
                _normalise_word(value, "candidates") for value in values
            )

        if set(raw_candidates) != set(counts):
            missing = sorted(set(counts) - set(raw_candidates))
            extra = sorted(set(raw_candidates) - set(counts))
            raise ValueError(
                f"candidate keys must match ciphertext keys; missing={missing!r}, "
                f"extra={extra!r}"
            )

        alphabet_set = set(alphabet)
        # Keep only candidate word references after root filtering. Do not
        # retain one assignment dictionary for each candidate.
        filtered: dict[Word, list[Word]] = {}
        raw_candidate_count = 0
        for cipher_word in counts:
            rows: list[Word] = []
            for plaintext_word in raw_candidates[cipher_word]:
                raw_candidate_count += 1
                if len(cipher_word) != len(plaintext_word):
                    continue
                assignment: dict[str, str] = {}
                consistent = True
                for cipher_symbol, plain_symbol in zip(
                    cipher_word, plaintext_word, strict=True
                ):
                    previous = assignment.get(cipher_symbol)
                    if previous is not None and previous != plain_symbol:
                        consistent = False
                        break
                    assignment[cipher_symbol] = plain_symbol
                if not consistent:
                    continue
                if any(symbol not in alphabet_set for symbol in plaintext_word):
                    raise ValueError(
                        "candidate words must use plaintext_alphabet symbols"
                    )
                if capacity is not None and any(
                    count > capacity for count in Counter(assignment.values()).values()
                ):
                    continue
                rows.append(plaintext_word)
            filtered[cipher_word] = rows

        lane_list: list[tuple[Word, int, tuple[Word, ...], int, int]] = []
        slot_count = 0
        sentinel_count = len(counts)
        root_compatible_candidate_count = 0
        root_compatible_distinct_candidate_count = 0
        for word in counts:
            rows = tuple(filtered[word])
            base = slot_count
            high = base + len(rows)
            lane_list.append((word, counts[word], rows, base, high))
            slot_count = high + 1
            root_compatible_candidate_count += len(rows)
            root_compatible_distinct_candidate_count += len(set(rows))
        lanes = tuple(lane_list)
        del lane_list
        del filtered
        del raw_candidates

        cipher_symbols = tuple(
            sorted(
                {
                    symbol
                    for word, _weight, _rows, _base, _high in lanes
                    for symbol in word
                }
            )
        )

        byte_count = (slot_count + 7) // 8
        real_bytes = bytearray(byte_count)
        high_bytes = bytearray(byte_count)
        low_bytes = bytearray(byte_count)
        presence_bytes = {
            symbol: bytearray(byte_count) for symbol in cipher_symbols
        }
        mapping_bytes: dict[tuple[str, str], bytearray] = {}
        preimage_size_bytes: dict[str, dict[int, bytearray]] = {
            symbol: {
                size: bytearray(byte_count)
                for size in range((capacity or 0) + 1)
            }
            for symbol in alphabet
        }
        weight_bits: set[int] = set()
        for _word, weight, _rows, _base, _high in lanes:
            remaining_weight = weight
            while remaining_weight:
                lowest_bit = remaining_weight & -remaining_weight
                weight_bits.add(lowest_bit.bit_length() - 1)
                remaining_weight ^= lowest_bit
        weight_bytes = {
            bit: bytearray(byte_count) for bit in sorted(weight_bits)
        }

        # Recompute assignments only while setting byte masks. The candidate
        # word remains in the lane, but its assignment does not.
        for cipher_word, weight, rows, base, high in lanes:
            _set_byte_bit(low_bytes, base)
            _set_byte_bit(high_bytes, high)
            for bit, weight_mask in weight_bytes.items():
                if (weight >> bit) & 1:
                    _set_byte_bit(weight_mask, high)
            for offset, plaintext_word in enumerate(rows):
                bit = base + offset
                _set_byte_bit(real_bytes, bit)
                assignment: dict[str, str] = {}
                for cipher_symbol, plain_symbol in zip(
                    cipher_word, plaintext_word, strict=True
                ):
                    assignment[cipher_symbol] = plain_symbol
                plain_units: dict[str, set[str]] = {}
                for cipher_symbol, plain_symbol in assignment.items():
                    _set_byte_bit(presence_bytes[cipher_symbol], bit)
                    pair = (cipher_symbol, plain_symbol)
                    mapping_mask = mapping_bytes.get(pair)
                    if mapping_mask is None:
                        mapping_mask = bytearray(byte_count)
                        mapping_bytes[pair] = mapping_mask
                    _set_byte_bit(mapping_mask, bit)
                    plain_units.setdefault(plain_symbol, set()).add(cipher_symbol)
                if capacity is not None:
                    for plain_symbol, units in plain_units.items():
                        _set_byte_bit(
                            preimage_size_bytes[plain_symbol][len(units)], bit
                        )

        real_mask = int.from_bytes(real_bytes, "little")
        del real_bytes
        high_sentinels = int.from_bytes(high_bytes, "little")
        del high_bytes
        low_lane_bits = int.from_bytes(low_bytes, "little")
        del low_bytes

        presence_masks: dict[str, int] = {}
        while presence_bytes:
            symbol, mask = presence_bytes.popitem()
            presence_masks[symbol] = int.from_bytes(mask, "little")

        mapping_masks: dict[tuple[str, str], int] = {}
        while mapping_bytes:
            pair, mask = mapping_bytes.popitem()
            mapping_masks[pair] = int.from_bytes(mask, "little")

        preimage_size_masks: dict[str, dict[int, int]] = {}
        while preimage_size_bytes:
            plain_symbol, size_bytes = preimage_size_bytes.popitem()
            size_masks: dict[int, int] = {}
            while size_bytes:
                size, mask = size_bytes.popitem()
                size_masks[size] = int.from_bytes(mask, "little")
            preimage_size_masks[plain_symbol] = size_masks

        weight_masks: dict[int, int] = {}
        while weight_bytes:
            bit, mask = weight_bytes.popitem()
            weight_masks[bit] = int.from_bytes(mask, "little")

        if capacity is not None:
            for plain_symbol in alphabet:
                mapped = 0
                for cipher_symbol in cipher_symbols:
                    mapped |= mapping_masks.get((cipher_symbol, plain_symbol), 0)
                preimage_size_masks[plain_symbol][0] = real_mask & ~mapped

        self._capacity = capacity
        self._cipher_symbols = cipher_symbols
        self._plain_symbols = alphabet
        self._real_mask = real_mask
        self._high_sentinels = high_sentinels
        self._low_lane_bits = low_lane_bits
        self._presence_masks = presence_masks
        self._mapping_masks = mapping_masks
        self._preimage_size_masks = preimage_size_masks
        self._weight_bit_masks = tuple(sorted(weight_masks.items()))
        mask_count = (
            3
            + len(presence_masks)
            + len(mapping_masks)
            + sum(len(values) for values in preimage_size_masks.values())
            + len(weight_masks)
        )
        estimated_storage_bytes = sum(
            _mask_size(mask)
            for mask in (
                real_mask,
                high_sentinels,
                low_lane_bits,
                *presence_masks.values(),
                *mapping_masks.values(),
                *(
                    mask
                    for values in preimage_size_masks.values()
                    for mask in values.values()
                ),
                *weight_masks.values(),
            )
        )
        self._metadata = {
            "lane_count": len(lanes),
            "candidate_count": root_compatible_candidate_count,
            "raw_candidate_count": raw_candidate_count,
            "root_compatible_candidate_count": root_compatible_candidate_count,
            "distinct_candidate_count": root_compatible_distinct_candidate_count,
            "root_compatible_distinct_candidate_count": (
                root_compatible_distinct_candidate_count
            ),
            "slot_count": slot_count,
            "sentinel_count": sentinel_count,
            "mask_count": mask_count,
            "estimated_storage_bytes": estimated_storage_bytes,
            "weight_bit_count": len(weight_masks),
        }

    @property
    def metadata(self) -> dict[str, int]:
        """Return construction counts and synthetic storage estimates."""

        return dict(self._metadata)

    @property
    def root_bound(self) -> int:
        """Return the bound for an empty partial map."""

        return self.bound({})

    def _validate_partial_key(
        self,
        partial_key: Mapping[str, str] | None,
    ) -> dict[str, str]:
        if partial_key is None:
            return {}
        if not isinstance(partial_key, Mapping):
            raise TypeError("partial_key must be a mapping")
        cipher_set = set(self._cipher_symbols)
        plain_set = set(self._plain_symbols)
        key: dict[str, str] = {}
        usage: Counter[str] = Counter()
        for cipher_symbol, plain_symbol in partial_key.items():
            if not isinstance(cipher_symbol, str) or not isinstance(plain_symbol, str):
                raise ValueError("partial_key symbols must be strings")
            if cipher_symbol not in cipher_set:
                raise ValueError("partial_key contains a symbol absent from ciphertext")
            if plain_symbol not in plain_set:
                raise ValueError("partial_key values must be in plaintext_alphabet")
            key[cipher_symbol] = plain_symbol
            usage[plain_symbol] += 1
        if self._capacity is not None and any(
            count > self._capacity for count in usage.values()
        ):
            raise ValueError("partial_key exceeds plaintext-letter capacity")
        return key

    def _capacity_mask(
        self,
        plain_symbol: str,
        units: tuple[str, ...],
    ) -> int:
        if self._capacity is None or not units:
            return self._real_mask
        sizes = self._preimage_size_masks[plain_symbol]
        if self._capacity == 1:
            # The union has size at most one when the candidate has no unit,
            # or when its only unit is the already assigned partial unit.
            return sizes[0] | self._mapping_masks.get((units[0], plain_symbol), 0)
        if len(units) == 1:
            # A one-unit partial preimage allows candidate size zero or one.
            # A size-two candidate is valid only when it contains that unit.
            return (
                sizes[0]
                | sizes[1]
                | self._mapping_masks.get((units[0], plain_symbol), 0)
            )
        first, second = units
        first_mask = self._mapping_masks.get((first, plain_symbol), 0)
        second_mask = self._mapping_masks.get((second, plain_symbol), 0)
        # A two-unit partial preimage allows only size-zero, the matching
        # size-one rows, and the exact matching size-two rows.
        return (
            sizes[0]
            | (sizes[1] & (first_mask | second_mask))
            | (sizes[2] & first_mask & second_mask)
        )

    def bound(self, partial_key: Mapping[str, str] | None = None) -> int:
        """Return the weighted compatible-candidate upper bound."""

        key = self._validate_partial_key(partial_key)
        active = self._real_mask
        assigned_units: dict[str, list[str]] = {}
        for cipher_symbol, plain_symbol in key.items():
            presence = self._presence_masks[cipher_symbol]
            mapping = self._mapping_masks.get((cipher_symbol, plain_symbol), 0)
            active &= (~presence | mapping) & self._real_mask
            assigned_units.setdefault(plain_symbol, []).append(cipher_symbol)
            if not active:
                return 0

        for plain_symbol, units in assigned_units.items():
            active &= self._capacity_mask(plain_symbol, tuple(sorted(units)))
            if not active:
                return 0

        flags = (
            (active | self._high_sentinels) - self._low_lane_bits
        ) & self._high_sentinels
        return sum(
            (flags & mask).bit_count() << bit
            for bit, mask in self._weight_bit_masks
        )


__all__ = ["BitsetBound"]
