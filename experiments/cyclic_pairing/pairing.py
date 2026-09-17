"""Bounded pairing checks for the frozen cyclic capacity-two emitter.

This module accepts only declared synthetic unit streams. It does not read a
corpus, assign plaintext letters, or claim a historical decipherment.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from itertools import combinations
from typing import Literal, TypeAlias


Unit: TypeAlias = str
Word: TypeAlias = tuple[Unit, ...]
Partition: TypeAlias = tuple[Word, ...]
Pair: TypeAlias = tuple[Unit, Unit]
Scope = Literal["full", "observed"]

MAX_UNITS = 64
DEFAULT_NODE_BUDGET = 100_000
DEFAULT_MAX_RESULTS = 2


def _normalise_units(values: Iterable[str]) -> tuple[Unit, ...]:
    if isinstance(values, (str, bytes)):
        raise ValueError("units must be a sequence of unit strings")
    result = tuple(values)
    if any(not isinstance(value, str) or not value for value in result):
        raise ValueError("units must contain non-empty strings")
    if len(set(result)) != len(result):
        raise ValueError("units must not contain duplicates")
    result = tuple(sorted(result))
    if len(result) > MAX_UNITS:
        raise ValueError(f"unit inventory exceeds the {MAX_UNITS}-unit limit")
    return result


def _normalise_partitions(
    partitions: Iterable[Iterable[Iterable[str]]],
    units: frozenset[Unit],
) -> tuple[Partition, ...]:
    if isinstance(partitions, (str, bytes)):
        raise ValueError("partitions must be a sequence of word sequences")
    raw_partitions = tuple(partitions)
    if not raw_partitions:
        raise ValueError("at least one partition is required")
    normalised: list[Partition] = []
    for partition in raw_partitions:
        if isinstance(partition, (str, bytes)):
            raise ValueError("each partition must contain word sequences")
        words: list[Word] = []
        for word in partition:
            if isinstance(word, (str, bytes)):
                raise ValueError("each word must preserve atomic unit boundaries")
            word_tuple = tuple(word)
            if any(
                not isinstance(unit, str) or not unit or unit not in units
                for unit in word_tuple
            ):
                raise ValueError("cipher words contain an undeclared unit")
            words.append(word_tuple)
        normalised.append(tuple(words))
    return tuple(normalised)


def _flatten(partition: Partition) -> tuple[Unit, ...]:
    return tuple(unit for word in partition for unit in word)


def _alternates(sequence: Sequence[Unit]) -> bool:
    return all(left != right for left, right in zip(sequence, sequence[1:]))


def _pair_diagnostics(
    left: Unit,
    right: Unit,
    streams: tuple[tuple[Unit, ...], ...],
) -> tuple[bool, tuple[Unit | None, ...]]:
    orientations: list[Unit | None] = []
    for stream in streams:
        projected = tuple(unit for unit in stream if unit == left or unit == right)
        left_count = projected.count(left)
        right_count = projected.count(right)
        if abs(left_count - right_count) > 1 or not _alternates(projected):
            return False, tuple(orientations)
        orientations.append(projected[0] if projected else None)
    nonempty_orientations = {value for value in orientations if value is not None}
    if len(nonempty_orientations) > 1:
        return False, tuple(orientations)
    return True, tuple(orientations)


@dataclass(frozen=True, slots=True)
class Compatibility:
    """A validated pair graph for one declared unit inventory.

    Construct this value with ``build_compatibility``. An internal edge
    restrictor may create a derived value only when it preserves the unit,
    count, and orientation invariants. Matching search assumes those
    invariants and does not validate a forged dataclass instance.
    """

    units: tuple[Unit, ...]
    partitions: tuple[Partition, ...]
    partition_unit_counts: tuple[tuple[tuple[Unit, int], ...], ...]
    unit_counts: tuple[tuple[Unit, int], ...]
    observed_units: tuple[Unit, ...]
    unseen_units: tuple[Unit, ...]
    edges: tuple[Pair, ...]
    edge_orientations: tuple[tuple[Pair, tuple[Unit | None, ...]], ...]

    def orientation_for(self, pair: Pair) -> tuple[Unit | None, ...]:
        """Return the fixed-cycle start unit for each partition."""

        normalised = tuple(sorted(pair))
        for candidate, orientations in self.edge_orientations:
            if candidate == normalised:
                return orientations
        raise KeyError(pair)

    def neighbors(self, unit: Unit, *, scope: Scope = "full") -> tuple[Unit, ...]:
        """Return compatible neighbors under the selected matching scope."""

        if unit not in self.units:
            raise KeyError(unit)
        if scope not in ("full", "observed"):
            raise ValueError("scope must be 'full' or 'observed'")
        allowed = set(self.observed_units if scope == "observed" else self.units)
        return tuple(
            sorted(
                right if left == unit else left
                for left, right in self.edges
                if unit in (left, right)
                and (right if left == unit else left) in allowed
            )
        )


@dataclass(frozen=True, slots=True)
class MatchingResult:
    """A bounded exact result for one matching scope."""

    scope: Scope
    status: Literal[
        "unique",
        "multiple",
        "none",
        "unknown_budget",
        "not_closed",
        "empty_scope",
    ]
    matchings: tuple[tuple[Pair, ...], ...]
    nodes_visited: int
    node_budget: int
    scope_units: tuple[Unit, ...]
    unseen_units: tuple[Unit, ...]
    certificate: str


def build_compatibility(
    units: Iterable[str],
    partitions: Iterable[Iterable[Iterable[str]]],
) -> Compatibility:
    """Build the exact compatibility graph for one or more partitions.

    A partition is flattened in word order. Word boundaries do not reset the
    emitter. Partition boundaries do reset the emitter.
    """

    normalised_units = _normalise_units(units)
    normalised_partitions = _normalise_partitions(
        partitions, frozenset(normalised_units)
    )
    streams = tuple(_flatten(partition) for partition in normalised_partitions)
    partition_counts = tuple(
        tuple((unit, stream.count(unit)) for unit in normalised_units)
        for stream in streams
    )
    counts = {
        unit: sum(stream.count(unit) for stream in streams)
        for unit in normalised_units
    }
    edges: list[Pair] = []
    orientations: list[tuple[Pair, tuple[Unit | None, ...]]] = []
    for left, right in combinations(normalised_units, 2):
        compatible, starts = _pair_diagnostics(left, right, streams)
        if compatible:
            pair = (left, right)
            edges.append(pair)
            orientations.append((pair, starts))
    observed = tuple(unit for unit in normalised_units if counts[unit] > 0)
    unseen = tuple(unit for unit in normalised_units if counts[unit] == 0)
    return Compatibility(
        units=normalised_units,
        partitions=normalised_partitions,
        partition_unit_counts=partition_counts,
        unit_counts=tuple((unit, counts[unit]) for unit in normalised_units),
        observed_units=observed,
        unseen_units=unseen,
        edges=tuple(edges),
        edge_orientations=tuple(orientations),
    )


def _validate_matching_options(node_budget: int, max_results: int) -> None:
    if isinstance(node_budget, bool) or not isinstance(node_budget, int):
        raise ValueError("node_budget must be a non-negative integer")
    if node_budget < 0:
        raise ValueError("node_budget must be a non-negative integer")
    if isinstance(max_results, bool) or not isinstance(max_results, int):
        raise ValueError("max_results must be an integer of at least two")
    if max_results < 2:
        raise ValueError("max_results must be at least two")


def enumerate_matchings(
    compatibility: Compatibility,
    *,
    scope: Scope = "full",
    node_budget: int = DEFAULT_NODE_BUDGET,
    max_results: int = DEFAULT_MAX_RESULTS,
) -> MatchingResult:
    """Enumerate zero, one, or multiple pairings under a bounded search.

    ``multiple`` needs two complete witnesses. A budget stop before that
    evidence returns ``unknown_budget`` and never claims multiple pairings.
    The observed scope is conditional on every observed unit pairing another
    observed unit. It does not describe unseen mates in the full inventory.
    """

    _validate_matching_options(node_budget, max_results)
    if scope not in ("full", "observed"):
        raise ValueError("scope must be 'full' or 'observed'")
    scope_units = compatibility.units if scope == "full" else compatibility.observed_units
    unseen_units = compatibility.unseen_units
    if scope == "observed" and not scope_units:
        return MatchingResult(
            scope=scope,
            status="empty_scope",
            matchings=(),
            nodes_visited=0,
            node_budget=node_budget,
            scope_units=scope_units,
            unseen_units=unseen_units,
            certificate="no observed units",
        )
    if scope == "observed" and len(scope_units) % 2:
        return MatchingResult(
            scope=scope,
            status="not_closed",
            matchings=(),
            nodes_visited=0,
            node_budget=node_budget,
            scope_units=scope_units,
            unseen_units=unseen_units,
            certificate="observed scope has an odd number of units",
        )
    if scope == "full" and len(scope_units) % 2:
        return MatchingResult(
            scope=scope,
            status="none",
            matchings=(),
            nodes_visited=0,
            node_budget=node_budget,
            scope_units=scope_units,
            unseen_units=unseen_units,
            certificate="full declared inventory has an odd number of units",
        )

    allowed = set(scope_units)
    neighbors = {
        unit: {
            right if left == unit else left
            for left, right in compatibility.edges
            if unit in (left, right)
            and (right if left == unit else left) in allowed
        }
        for unit in scope_units
    }
    if any(not values for values in neighbors.values()):
        return MatchingResult(
            scope=scope,
            status="none",
            matchings=(),
            nodes_visited=0,
            node_budget=node_budget,
            scope_units=scope_units,
            unseen_units=unseen_units,
            certificate="a scope unit has no compatible neighbor",
        )

    remaining = frozenset(scope_units)
    found: list[tuple[Pair, ...]] = []
    nodes_visited = 0
    budget_exhausted = False

    def search(left_units: frozenset[Unit], pairs: tuple[Pair, ...]) -> None:
        nonlocal nodes_visited, budget_exhausted
        if len(found) >= max_results:
            return
        if not left_units:
            found.append(tuple(sorted(pairs)))
            return
        if nodes_visited >= node_budget:
            budget_exhausted = True
            return
        nodes_visited += 1
        pivot = min(
            left_units,
            key=lambda unit: (len(neighbors[unit] & left_units), unit),
        )
        candidates = sorted(neighbors[pivot] & left_units)
        if not candidates:
            return
        for partner in candidates:
            if nodes_visited >= node_budget and not left_units == frozenset((pivot, partner)):
                budget_exhausted = True
                return
            next_units = left_units - {pivot, partner}
            search(next_units, pairs + (tuple(sorted((pivot, partner))),))
            if len(found) >= max_results:
                return
            if budget_exhausted:
                return

    search(remaining, ())
    unique_found = tuple(sorted(set(found)))
    if len(unique_found) >= 2:
        status: Literal["unique", "multiple", "none", "unknown_budget", "not_closed", "empty_scope"] = "multiple"
        certificate = "at least two complete pairings were found"
    elif budget_exhausted:
        status = "unknown_budget"
        certificate = "enumeration stopped before uniqueness or infeasibility was proved"
    elif unique_found:
        status = "unique"
        certificate = "search exhausted with one complete pairing"
    else:
        status = "none"
        certificate = "search exhausted without a complete pairing"
    return MatchingResult(
        scope=scope,
        status=status,
        matchings=unique_found,
        nodes_visited=nodes_visited,
        node_budget=node_budget,
        scope_units=scope_units,
        unseen_units=unseen_units,
        certificate=certificate,
    )
