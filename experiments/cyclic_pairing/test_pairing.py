"""Synthetic tests for the cyclic emitter pairing checks."""

from __future__ import annotations

import unittest

from .pairing import build_compatibility, enumerate_matchings


class CyclicPairingTests(unittest.TestCase):
    def test_unique_matching_and_partition_orientations(self) -> None:
        compatibility = build_compatibility(
            ("a", "b", "c", "d"),
            [[("a", "b", "a", "b", "a", "c", "d", "c", "d", "c")]],
        )
        result = enumerate_matchings(compatibility)
        self.assertEqual(result.status, "unique")
        self.assertEqual(result.matchings, ((("a", "b"), ("c", "d")),))
        self.assertEqual(compatibility.orientation_for(("a", "b")), ("a",))
        self.assertEqual(compatibility.orientation_for(("c", "d")), ("c",))

    def test_singleton_can_have_an_unseen_mate(self) -> None:
        compatibility = build_compatibility(
            ("a", "b", "c", "d"),
            [[("a", "b", "a", "b", "a", "c")]],
        )
        result = enumerate_matchings(compatibility)
        self.assertEqual(result.status, "unique")
        self.assertEqual(result.matchings, ((("a", "b"), ("c", "d")),))
        self.assertEqual(compatibility.unseen_units, ("d",))
        self.assertEqual(dict(compatibility.unit_counts), {"a": 3, "b": 2, "c": 1, "d": 0})
        self.assertEqual(compatibility.orientation_for(("c", "d")), ("c",))

    def test_observed_scope_and_full_inventory_can_differ(self) -> None:
        compatibility = build_compatibility(
            ("a", "b", "c", "d"),
            [[("a", "b")]],
        )
        observed = enumerate_matchings(compatibility, scope="observed")
        full = enumerate_matchings(compatibility, scope="full")
        self.assertEqual(observed.status, "unique")
        self.assertEqual(observed.matchings, ((("a", "b"),),))
        self.assertEqual(full.status, "multiple")
        self.assertGreaterEqual(len(full.matchings), 2)

    def test_multiple_matchings_do_not_choose_a_tie(self) -> None:
        compatibility = build_compatibility(
            ("a", "b", "c", "d"),
            [[("a", "b", "c", "d")]],
        )
        result = enumerate_matchings(compatibility)
        self.assertEqual(result.status, "multiple")
        self.assertGreaterEqual(len(result.matchings), 2)

    def test_no_perfect_matching_is_certified(self) -> None:
        compatibility = build_compatibility(
            ("a", "b", "c", "d"),
            [[("a", "a", "b", "b")]],
        )
        result = enumerate_matchings(compatibility)
        self.assertEqual(result.status, "none")
        self.assertEqual(result.matchings, ())

    def test_partition_reset_is_required(self) -> None:
        valid = build_compatibility(
            ("a", "b"),
            [[("a", "b", "a")], [("a", "b")]],
        )
        self.assertEqual(enumerate_matchings(valid).status, "unique")
        invalid_if_concatenated = build_compatibility(
            ("a", "b"),
            [[("a", "b", "a", "a", "b")]],
        )
        self.assertEqual(enumerate_matchings(invalid_if_concatenated).status, "none")

    def test_partition_start_orientation_must_agree(self) -> None:
        compatibility = build_compatibility(
            ("a", "b"),
            [[("a", "b")], [("b", "a")]],
        )
        self.assertEqual(enumerate_matchings(compatibility).status, "none")

    def test_reset_partitions_can_hide_an_unseen_mate_repeatedly(self) -> None:
        compatibility = build_compatibility(
            ("a", "b"),
            [[("a",)], [("a",)]],
        )
        self.assertEqual(dict(compatibility.unit_counts), {"a": 2, "b": 0})
        self.assertEqual(enumerate_matchings(compatibility).status, "unique")

    def test_budget_stop_is_unknown_not_multiple(self) -> None:
        compatibility = build_compatibility(
            ("a", "b", "c", "d"),
            [[("a", "b", "c", "d")]],
        )
        result = enumerate_matchings(compatibility, node_budget=1)
        self.assertEqual(result.status, "unknown_budget")
        self.assertEqual(result.matchings, ())

    def test_budget_stop_after_one_witness_is_still_unknown(self) -> None:
        compatibility = build_compatibility(
            ("a", "b", "c", "d", "e", "f"),
            [[("a", "b", "c", "d", "e", "f")]],
        )
        result = enumerate_matchings(compatibility, node_budget=3)
        self.assertEqual(result.status, "unknown_budget")
        self.assertEqual(len(result.matchings), 1)

    def test_empty_and_odd_observed_scopes_are_explicit(self) -> None:
        empty = build_compatibility(("a", "b"), [[]])
        self.assertEqual(enumerate_matchings(empty, scope="observed").status, "empty_scope")
        odd_observed = build_compatibility(
            ("a", "b", "c", "d"),
            [[("a", "b", "c")]],
        )
        self.assertEqual(enumerate_matchings(odd_observed, scope="observed").status, "not_closed")

    def test_unknown_stream_units_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            build_compatibility(("a", "b"), [[("a", "x")]])


if __name__ == "__main__":
    unittest.main()
