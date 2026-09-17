"""Broadword upper bounds for finite lexicon candidate constraints.

The constructor accepts the normalized word counts and candidate lists made
by ``experiments.lexicon.solver``. It assigns one bit to every candidate and
one sentinel bit to every word lane. A bound call builds only a local active
mask, so a search node does not retain a large candidate bitset.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import TypeAlias


Word: TypeAlias = tuple[str, ...]
WordCounts: TypeAlias = Mapping[Word, int]
CandidateLists: TypeAlias = Mapping[Word, Iterable[Word]]


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


def _normalise_alphabet(
    plaintext_alphabet: Iterable[str] | str | None,
    candidates: Sequence[Word],
) -> tuple[str, ...]:
    if plaintext_alphabet is None:
        values = sorted({symbol for word in candidates for symbol in word})
    elif isinstance(plaintext_alphabet, str):
        values = list(plaintext_alphabet)
    else:
        values = list(plaintext_alphabet)
    if any(not isinstance(symbol, str) or not symbol for symbol in values):
        raise ValueError("plaintext_alphabet must contain non-empty symbols")
    if len(set(values)) != len(values):
        raise ValueError("plaintext_alphabet symbols must be unique")
    alphabet = tuple(values)
    alphabet_set = set(alphabet)
    if any(
        symbol not in alphabet_set
        for word in candidates
        for symbol in word
    ):
        raise ValueError("candidate words must use plaintext_alphabet symbols")
    return alphabet


def _set_bit(mask: bytearray, bit: int) -> None:
    mask[bit >> 3] |= 1 << (bit & 7)


def _as_int(mask: bytearray) -> int:
    return int.from_bytes(mask, "little")


class BitsetBound:
    """Compute the solver's compatible-candidate weighted upper bound.

    ``ciphertext_counts`` and ``candidates`` must use normalized tuple words.
    Candidate words must have the same length as their ciphertext lane and
    must describe an injective symbol mapping. The optional alphabet can
    include plaintext symbols that occur in no candidate word.
    """

    def __init__(
        self,
        ciphertext_counts: WordCounts,
        candidates: CandidateLists,
        plaintext_alphabet: Iterable[str] | str | None = None,
    ) -> None:
        counts = _normalise_counts(ciphertext_counts)
        if not isinstance(candidates, Mapping):
            raise TypeError("candidates must be a mapping")

        normalized_candidates: dict[Word, list[Word]] = {}
        for raw_cipher_word, raw_candidates in candidates.items():
            cipher_word = _normalise_word(raw_cipher_word, "candidates")
            try:
                values = tuple(raw_candidates)
            except TypeError as exc:
                raise TypeError("each candidate list must be iterable") from exc
            normalized_candidates.setdefault(cipher_word, []).extend(
                _normalise_word(value, "candidates") for value in values
            )

        if set(normalized_candidates) != set(counts):
            missing = sorted(set(counts) - set(normalized_candidates))
            extra = sorted(set(normalized_candidates) - set(counts))
            raise ValueError(
                f"candidate keys must match ciphertext keys; missing={missing!r}, "
                f"extra={extra!r}"
            )

        ordered_lanes = tuple(
            (word, counts[word], tuple(normalized_candidates[word]))
            for word in counts
        )
        all_candidates = tuple(
            candidate
            for _cipher_word, _weight, lane in ordered_lanes
            for candidate in lane
        )
        alphabet = _normalise_alphabet(plaintext_alphabet, all_candidates)

        cipher_symbols = tuple(
            sorted({symbol for word, _weight, _lane in ordered_lanes for symbol in word})
        )
        plain_symbols = tuple(alphabet)

        lane_ranges: list[tuple[Word, int, int, int]] = []
        slot_count = 0
        for cipher_word, _weight, lane in ordered_lanes:
            base = slot_count
            high = base + len(lane)
            lane_ranges.append((cipher_word, base, high, len(lane)))
            slot_count = high + 1

        byte_count = (slot_count + 7) // 8
        real_bytes = bytearray(byte_count)
        high_bytes = bytearray(byte_count)
        low_bytes = bytearray(byte_count)
        presence_bytes = {
            symbol: bytearray(byte_count) for symbol in cipher_symbols
        }
        plainuse_bytes = {
            symbol: bytearray(byte_count) for symbol in plain_symbols
        }
        mapping_bytes: dict[tuple[str, str], bytearray] = {}
        weight_bits_set: set[int] = set()
        for _word, weight, _lane in ordered_lanes:
            remaining_weight = weight
            while remaining_weight:
                lowest_bit = remaining_weight & -remaining_weight
                weight_bits_set.add(lowest_bit.bit_length() - 1)
                remaining_weight ^= lowest_bit
        weight_bits = sorted(weight_bits_set)
        weight_bytes = {
            bit: bytearray(byte_count) for bit in weight_bits
        }

        for (cipher_word, weight, lane), (_same_word, base, high, count) in zip(
            ordered_lanes, lane_ranges, strict=True
        ):
            assert count == len(lane)
            _set_bit(low_bytes, base)
            _set_bit(high_bytes, high)
            for bit, weight_mask in weight_bytes.items():
                if (weight >> bit) & 1:
                    _set_bit(weight_mask, high)

            for offset, plaintext_word in enumerate(lane):
                bit = base + offset
                _set_bit(real_bytes, bit)
                assignment: dict[str, str] = {}
                used_plain: set[str] = set()
                if len(plaintext_word) != len(cipher_word):
                    raise ValueError(
                        "candidate words must have the same length as their cipher word"
                    )
                for cipher_symbol, plain_symbol in zip(
                    cipher_word, plaintext_word, strict=True
                ):
                    previous = assignment.get(cipher_symbol)
                    if previous is not None:
                        if previous != plain_symbol:
                            raise ValueError(
                                "candidate words must define a consistent mapping"
                            )
                        continue
                    if plain_symbol in used_plain:
                        raise ValueError(
                            "candidate words must define an injective mapping"
                        )
                    assignment[cipher_symbol] = plain_symbol
                    used_plain.add(plain_symbol)

                for cipher_symbol, plain_symbol in assignment.items():
                    _set_bit(presence_bytes[cipher_symbol], bit)
                    _set_bit(plainuse_bytes[plain_symbol], bit)
                    pair = (cipher_symbol, plain_symbol)
                    mapping_mask = mapping_bytes.get(pair)
                    if mapping_mask is None:
                        mapping_mask = bytearray(byte_count)
                        mapping_bytes[pair] = mapping_mask
                    _set_bit(mapping_mask, bit)

        self._cipher_symbols = cipher_symbols
        self._plain_symbols = plain_symbols
        self._real_mask = _as_int(real_bytes)
        self._high_sentinels = _as_int(high_bytes)
        self._low_lane_bits = _as_int(low_bytes)
        self._presence_masks = {
            symbol: _as_int(mask) for symbol, mask in presence_bytes.items()
        }
        self._plainuse_masks = {
            symbol: _as_int(mask) for symbol, mask in plainuse_bytes.items()
        }
        self._mapping_masks = {
            pair: _as_int(mask) for pair, mask in mapping_bytes.items()
        }
        self._weight_bit_masks = tuple(
            (bit, _as_int(mask)) for bit, mask in weight_bytes.items()
        )
        self._metadata = {
            "lane_count": len(ordered_lanes),
            "candidate_count": sum(len(lane) for _word, _weight, lane in ordered_lanes),
            "slot_count": slot_count,
            "sentinel_count": len(ordered_lanes),
            "weight_bit_count": len(weight_bytes),
        }

    @property
    def metadata(self) -> dict[str, int]:
        """Return construction counts without exposing internal masks."""

        return dict(self._metadata)

    @property
    def root_bound(self) -> int:
        """Return the bound for an empty partial assignment."""

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
        used: set[str] = set()
        for cipher_symbol, plain_symbol in partial_key.items():
            if not isinstance(cipher_symbol, str) or not isinstance(plain_symbol, str):
                raise ValueError("partial_key symbols must be strings")
            if cipher_symbol not in cipher_set:
                raise ValueError("partial_key contains a symbol absent from ciphertext")
            if plain_symbol not in plain_set:
                raise ValueError("partial_key values must be in plaintext_alphabet")
            if plain_symbol in used:
                raise ValueError("partial_key must be injective")
            key[cipher_symbol] = plain_symbol
            used.add(plain_symbol)
        return key

    def bound(self, partial_key: Mapping[str, str] | None = None) -> int:
        """Return the weighted compatible-candidate upper bound."""

        key = self._validate_partial_key(partial_key)
        active = self._real_mask
        for cipher_symbol, plain_symbol in key.items():
            presence = self._presence_masks[cipher_symbol]
            plainuse = self._plainuse_masks[plain_symbol]
            mapping = self._mapping_masks.get((cipher_symbol, plain_symbol), 0)
            allowed = ((~presence & ~plainuse) | mapping) & self._real_mask
            active &= allowed
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
