"""Ephemeral child states for the frozen homophonic bitset bound.

The base bound stores candidate masks for one problem. This adapter stores one
active mask for a caller's parent node and derives each child mask without
rebuilding the parent mask.
It keeps no frontier-node cache and does not change the score or bound rules.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import TypeAlias

from experiments.homophonic.bitset_bound import BitsetBound


PartialKey: TypeAlias = tuple[tuple[str, str], ...]


@dataclass(frozen=True, slots=True, init=False)
class BoundState:
    """Immutable active-mask state for one partial key and one engine."""

    owner: object
    partial_key: PartialKey
    active_mask: int

    def __init__(self, *args: object, **kwargs: object) -> None:
        """Reject direct construction; engines create trusted states."""

        raise TypeError(
            "BoundState instances are created by IncrementalBitsetBound"
        )


def _make_state(
    owner: object,
    partial_key: PartialKey,
    active_mask: int,
) -> BoundState:
    """Create a state through the adapter's trusted internal factory.

    This factory is an implementation contract, not a security boundary.
    Callers must use ``IncrementalBitsetBound.state`` and ``child_state``.
    """

    state = object.__new__(BoundState)
    object.__setattr__(state, "owner", owner)
    object.__setattr__(state, "partial_key", partial_key)
    object.__setattr__(state, "active_mask", active_mask)
    return state


class IncrementalBitsetBound(BitsetBound):
    """Reuse one parent active mask for ephemeral child-bound queries."""

    def _canonical_key(self, partial_key: Mapping[str, str] | None) -> PartialKey:
        validated = self._validate_partial_key(partial_key)
        return tuple(sorted(validated.items()))

    def _active_for_key(self, partial_key: PartialKey) -> int:
        active = self._real_mask
        assigned_units: dict[str, list[str]] = {}
        for cipher_symbol, plain_symbol in partial_key:
            presence = self._presence_masks[cipher_symbol]
            mapping = self._mapping_masks.get((cipher_symbol, plain_symbol), 0)
            active &= (~presence | mapping) & self._real_mask
            assigned_units.setdefault(plain_symbol, []).append(cipher_symbol)
            if not active:
                return 0

        for plain_symbol, units in assigned_units.items():
            active &= self._capacity_mask(plain_symbol, tuple(units))
            if not active:
                return 0
        return active

    def state(self, partial_key: Mapping[str, str] | None = None) -> BoundState:
        """Build one immutable parent state from a validated partial key."""

        key = self._canonical_key(partial_key)
        return _make_state(self, key, self._active_for_key(key))

    def _check_state(self, state: BoundState) -> None:
        if not isinstance(state, BoundState):
            raise TypeError("state must be a BoundState")
        if state.owner is not self:
            raise ValueError("state belongs to another bound engine")
        if (
            not isinstance(state.active_mask, int)
            or isinstance(state.active_mask, bool)
            or state.active_mask < 0
            or state.active_mask & ~self._real_mask
        ):
            raise ValueError("state active_mask is invalid for this engine")

    def _state_key(self, state: BoundState) -> dict[str, str]:
        self._check_state(state)
        if not isinstance(state.partial_key, tuple):
            raise ValueError("state partial_key must be an immutable tuple")
        if tuple(sorted(state.partial_key)) != state.partial_key:
            raise ValueError("state partial_key must be sorted")
        key: dict[str, str] = {}
        usage: dict[str, int] = {}
        for item in state.partial_key:
            if (
                not isinstance(item, tuple)
                or len(item) != 2
                or not isinstance(item[0], str)
                or not isinstance(item[1], str)
                or item[0] not in self._cipher_symbols
                or item[1] not in self._plain_symbols
                or item[0] in key
            ):
                raise ValueError("state partial_key is not valid for this engine")
            key[item[0]] = item[1]
            usage[item[1]] = usage.get(item[1], 0) + 1
        if self._capacity is not None and any(
            count > self._capacity for count in usage.values()
        ):
            raise ValueError("state partial_key exceeds plaintext-letter capacity")
        return key

    def child_state(
        self,
        state: BoundState,
        new_unit: str,
        plain_symbol: str,
    ) -> BoundState:
        """Derive one child state without rebuilding the parent mask."""

        key = self._state_key(state)
        if not isinstance(new_unit, str) or new_unit not in self._cipher_symbols:
            raise ValueError("new_unit must be a ciphertext unit in this engine")
        if new_unit in key:
            raise ValueError("new_unit is already assigned in the parent state")
        if not isinstance(plain_symbol, str) or plain_symbol not in self._plain_symbols:
            raise ValueError("plain_symbol must be in plaintext_alphabet")

        units_for_plain = [
            unit for unit, value in key.items() if value == plain_symbol
        ]
        if self._capacity is not None and len(units_for_plain) >= self._capacity:
            raise ValueError("child assignment exceeds plaintext-letter capacity")

        presence = self._presence_masks[new_unit]
        mapping = self._mapping_masks.get((new_unit, plain_symbol), 0)
        active = state.active_mask & (~presence | mapping) & self._real_mask
        units_for_plain.append(new_unit)
        active &= self._capacity_mask(
            plain_symbol,
            tuple(sorted(units_for_plain)),
        )
        child_key = tuple(sorted((*state.partial_key, (new_unit, plain_symbol))))
        return _make_state(self, child_key, active)

    def score_state(self, state: BoundState) -> int:
        """Score an active state with the frozen guarded lane expression."""

        self._check_state(state)
        active = state.active_mask
        flags = ((active | self._high_sentinels) - self._low_lane_bits) & (
            self._high_sentinels
        )
        return sum(
            (flags & mask).bit_count() << bit
            for bit, mask in self._weight_bit_masks
        )


__all__ = ["BoundState", "IncrementalBitsetBound"]
