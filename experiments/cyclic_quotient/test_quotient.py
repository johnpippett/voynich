"""Synthetic tests for observed cyclic-pair quotients."""

from __future__ import annotations

import unittest

from experiments.cyclic_pairing.pairing import build_compatibility

from .quotient import build_observed_quotient


def _map(result):
    return dict(result.unit_to_class)


class ObservedQuotientTests(unittest.TestCase):
    def test_observed_k4_ambiguity_does_not_merge_classes(self) -> None:
        compatibility = build_compatibility(
            ("a", "b", "x", "y"),
            [[("a", "b")]],
        )
        result = build_observed_quotient(compatibility)
        self.assertEqual(result.status, "ambiguous")
        self.assertEqual(result.full_status, "multiple")
        self.assertEqual(result.classes, ())
        self.assertEqual(result.unit_to_class, ())
        self.assertEqual(result.unknown_edges, ())

    def test_forced_observed_pairs_survive_unseen_clique(self) -> None:
        compatibility = build_compatibility(
            ("a", "b", "c", "d", "x", "y", "z", "w"),
            [[("a", "b", "a", "b", "a", "c", "d", "c", "d", "c")]],
        )
        result = build_observed_quotient(compatibility)
        self.assertEqual(result.status, "proved")
        self.assertEqual(result.full_status, "multiple")
        self.assertEqual(result.forced_pairs, (("a", "b"), ("c", "d")))
        self.assertEqual(result.singleton_units, ())
        self.assertEqual(result.classes, (("a", "b"), ("c", "d")))
        self.assertEqual(_map(result)["a"], ("a", "b"))
        self.assertEqual(_map(result)["d"], ("c", "d"))

    def test_singleton_keeps_unseen_mate_unselected(self) -> None:
        compatibility = build_compatibility(
            ("a", "b", "x", "y"),
            [[("a",)]],
        )
        result = build_observed_quotient(compatibility)
        self.assertEqual(result.status, "proved")
        self.assertEqual(result.forced_pairs, ())
        self.assertEqual(result.singleton_units, ("a",))
        self.assertEqual(result.classes, (("a",),))
        self.assertEqual(_map(result), {"a": ("a",)})

    def test_forced_observed_unseen_pair_stays_observed_singleton(self) -> None:
        compatibility = build_compatibility(
            ("a", "b", "c", "x"),
            [[("b", "c", "b", "c", "a")]],
        )
        result = build_observed_quotient(compatibility)
        self.assertEqual(result.status, "proved")
        self.assertEqual(result.forced_pairs, (("b", "c"),))
        self.assertEqual(result.singleton_units, ("a",))
        self.assertEqual(result.classes, (("a",), ("b", "c")))
        self.assertEqual(set(_map(result)), {"a", "b", "c"})
        self.assertNotIn("x", _map(result))

    def test_infeasible_full_inventory_has_no_quotient(self) -> None:
        compatibility = build_compatibility(
            ("a", "b", "c", "d"),
            [[("a", "a", "b", "b")]],
        )
        result = build_observed_quotient(compatibility)
        self.assertEqual(result.status, "infeasible")
        self.assertEqual(result.classes, ())
        self.assertIsNone(result.full_witness)

    def test_budget_unknown_abstains_without_witness(self) -> None:
        compatibility = build_compatibility(
            ("a", "b", "x", "y"),
            [[("a", "b")]],
        )
        result = build_observed_quotient(compatibility, node_budget=1)
        self.assertEqual(result.status, "unknown_budget")
        self.assertEqual(result.classes, ())
        self.assertIsNone(result.full_witness)

    def test_unknown_forced_observed_edge_does_not_claim_ambiguity(self) -> None:
        compatibility = build_compatibility(
            tuple("abcdefgh"),
            [[("g", "b", "h", "f", "d", "b", "g", "h", "f")]],
        )
        result = build_observed_quotient(compatibility, node_budget=4)
        self.assertEqual(result.full_status, "unknown_budget")
        self.assertEqual(result.status, "unknown_budget")
        self.assertEqual(result.classes, ())
        self.assertIn(("b", "f"), result.unknown_edges)

    def test_quotient_mapping_preserves_word_boundaries(self) -> None:
        compatibility = build_compatibility(
            ("a", "b", "c", "d", "x", "y"),
            [[
                ("a", "b"),
                ("a", "b"),
                ("a", "c", "d", "c", "d", "c"),
            ]],
        )
        snapshot = compatibility
        result = build_observed_quotient(compatibility)
        self.assertEqual(result.status, "proved")
        mapping = _map(result)
        mapped_words = tuple(
            tuple(mapping[unit] for unit in word)
            for word in compatibility.partitions[0]
        )
        self.assertEqual(
            tuple(len(word) for word in mapped_words),
            tuple(len(word) for word in compatibility.partitions[0]),
        )
        self.assertEqual(compatibility, snapshot)
        self.assertEqual(mapped_words[0], (("a", "b"), ("a", "b")))

    def test_rejects_non_compatibility_input(self) -> None:
        with self.assertRaises(TypeError):
            build_observed_quotient(object())


if __name__ == "__main__":
    unittest.main()
