"""Synthetic differential tests for the incremental bitset-bound adapter."""

from __future__ import annotations

from collections import Counter
from dataclasses import FrozenInstanceError, is_dataclass
from dataclasses import replace
import itertools
import random
import unittest

from experiments.homophonic.bitset_bound import BitsetBound
from experiments.identifiability.incremental_bound import (
    BoundState,
    IncrementalBitsetBound,
)


Word = tuple[str, ...]


def _partial_maps(
    units: tuple[str, ...],
    alphabet: tuple[str, ...],
    capacity: int | None,
):
    for depth in range(len(units) + 1):
        for selected in itertools.combinations(units, depth):
            for values in itertools.product(alphabet, repeat=depth):
                if capacity is not None and any(
                    count > capacity for count in Counter(values).values()
                ):
                    continue
                yield dict(zip(selected, values, strict=True))


def _child_values(
    partial: dict[str, str],
    unit: str,
    alphabet: tuple[str, ...],
    capacity: int | None,
):
    for plain in alphabet:
        if capacity is None or (
            Counter(partial.values())[plain] < capacity
        ):
            yield plain


class IncrementalBoundTests(unittest.TestCase):
    def _engine(self, capacity: int | None) -> IncrementalBitsetBound:
        counts = {
            ("x", "x"): 3,
            ("x", "y"): 5,
            ("y", "x"): 2,
            ("y", "z"): 0,
            ("z",): 7,
        }
        candidates = {
            ("x", "x"): (("a", "a"), ("a", "b"), ("b", "b")),
            ("x", "y"): (("a", "b"), ("b", "a"), ("b", "b")),
            ("y", "x"): (("b", "a"), ("a", "b"), ("c", "c")),
            ("y", "z"): (("a", "c"), ("b", "b"), ("c", "a")),
            ("z",): (("a",), ("b",), ("c",)),
        }
        return IncrementalBitsetBound(counts, candidates, ("a", "b", "c"), capacity)

    def test_exhaustive_children_match_frozen_base_for_all_capacities(self) -> None:
        for capacity in (1, 2, None):
            engine = self._engine(capacity)
            base = BitsetBound(
                {
                    ("x", "x"): 3,
                    ("x", "y"): 5,
                    ("y", "x"): 2,
                    ("y", "z"): 0,
                    ("z",): 7,
                },
                {
                    ("x", "x"): (("a", "a"), ("a", "b"), ("b", "b")),
                    ("x", "y"): (("a", "b"), ("b", "a"), ("b", "b")),
                    ("y", "x"): (("b", "a"), ("a", "b"), ("c", "c")),
                    ("y", "z"): (("a", "c"), ("b", "b"), ("c", "a")),
                    ("z",): (("a",), ("b",), ("c",)),
                },
                ("a", "b", "c"),
                capacity,
            )
            units = ("x", "y", "z")
            self.assertEqual(engine.score_state(engine.state()), base.bound({}))
            for partial in _partial_maps(units, ("a", "b", "c"), capacity):
                state = engine.state(partial)
                self.assertEqual(
                    state.partial_key,
                    tuple(sorted(partial.items())),
                )
                self.assertEqual(engine.score_state(state), base.bound(partial))
                for unit in units:
                    if unit in partial:
                        continue
                    for plain in _child_values(
                        partial, unit, ("a", "b", "c"), capacity
                    ):
                        child = engine.child_state(state, unit, plain)
                        full = dict(partial)
                        full[unit] = plain
                        self.assertEqual(
                            engine.score_state(child),
                            base.bound(full),
                            msg=(capacity, partial, unit, plain),
                        )

    def test_random_synthetic_children_match_frozen_base(self) -> None:
        rng = random.Random(20260917)
        alphabet = ("a", "b", "c")
        units = ("x", "y", "z")
        for _case in range(30):
            capacity = rng.choice((1, 2, None))
            lane_count = rng.randrange(0, 6)
            counts: dict[Word, int] = {}
            candidates: dict[Word, list[Word]] = {}
            for _lane in range(lane_count):
                word = tuple(rng.choice(units) for _ in range(rng.randrange(0, 4)))
                counts[word] = rng.randrange(0, 8)
                rows = candidates.setdefault(word, [])
                for _row in range(rng.randrange(0, 6)):
                    rows.append(tuple(rng.choice(alphabet) for _ in word))
                if rows and rng.random() < 0.5:
                    rows.append(rows[0])
            base = BitsetBound(counts, candidates, alphabet, capacity)
            engine = IncrementalBitsetBound(counts, candidates, alphabet, capacity)
            self.assertEqual(engine.score_state(engine.state()), base.bound({}))
            observed_units = tuple(
                sorted({unit for word in counts for unit in word})
            )
            for _query in range(20):
                partial: dict[str, str] = {}
                for unit in observed_units:
                    if rng.random() >= 0.5:
                        continue
                    plain = rng.choice(alphabet)
                    partial[unit] = plain
                if capacity is not None and any(
                    count > capacity for count in Counter(partial.values()).values()
                ):
                    continue
                state = engine.state(partial)
                self.assertEqual(engine.score_state(state), base.bound(partial))
                available = [unit for unit in observed_units if unit not in partial]
                if not available:
                    continue
                unit = rng.choice(available)
                allowed = list(_child_values(partial, unit, alphabet, capacity))
                if not allowed:
                    continue
                plain = rng.choice(allowed)
                child = engine.child_state(state, unit, plain)
                full = dict(partial)
                full[unit] = plain
                self.assertEqual(engine.score_state(child), base.bound(full))

    def test_empty_zero_weight_and_overlap_cases_match(self) -> None:
        counts = {(): 0, ("x", "x"): 4, ("x", "y"): 0}
        candidates = {
            (): ((),),
            ("x", "x"): (("a", "a"), ("a", "b"), ("b", "b")),
            ("x", "y"): (("a", "b"), ("b", "a"), ("a", "a")),
        }
        for capacity in (1, 2, None):
            base = BitsetBound(counts, candidates, "ab", capacity)
            engine = IncrementalBitsetBound(counts, candidates, "ab", capacity)
            self.assertEqual(engine.score_state(engine.state()), base.bound({}))
            for partial in _partial_maps(("x", "y"), ("a", "b"), capacity):
                state = engine.state(partial)
                self.assertEqual(engine.score_state(state), base.bound(partial))

    def test_state_is_immutable_and_owner_checked(self) -> None:
        engine = self._engine(2)
        other = self._engine(2)
        state = engine.state({"x": "a"})
        self.assertTrue(is_dataclass(state))
        with self.assertRaises(TypeError):
            BoundState(  # type: ignore[call-arg]
                engine,
                state.partial_key,
                state.active_mask,
            )
        with self.assertRaises(TypeError):
            replace(state, active_mask=0)
        with self.assertRaises(FrozenInstanceError):
            state.active_mask = 0  # type: ignore[misc]
        with self.assertRaises(ValueError):
            other.score_state(state)
        with self.assertRaises(ValueError):
            other.child_state(state, "y", "b")

    def test_child_validation_checks_unit_alphabet_and_capacity(self) -> None:
        engine = self._engine(1)
        state = engine.state({"x": "a"})
        with self.assertRaises(ValueError):
            engine.child_state(state, "x", "b")
        with self.assertRaises(ValueError):
            engine.child_state(state, "missing", "b")
        with self.assertRaises(ValueError):
            engine.child_state(state, "y", "missing")
        with self.assertRaises(ValueError):
            engine.child_state(state, "y", "a")


if __name__ == "__main__":
    unittest.main()
