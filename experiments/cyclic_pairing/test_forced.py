"""Synthetic tests for bounded forced-edge queries."""

from __future__ import annotations

import unittest
from dataclasses import replace

from .forced import forced_edges
from .pairing import Pair, build_compatibility


def _all_matchings(units: tuple[str, ...], edges: tuple[Pair, ...]) -> set[tuple[Pair, ...]]:
    adjacency = {
        unit: {
            right if left == unit else left
            for left, right in edges
            if unit in (left, right)
        }
        for unit in units
    }

    def visit(remaining: tuple[str, ...]) -> set[tuple[Pair, ...]]:
        if not remaining:
            return {()}
        pivot = remaining[0]
        result: set[tuple[Pair, ...]] = set()
        for partner in sorted(set(remaining[1:]) & adjacency[pivot]):
            rest = tuple(unit for unit in remaining if unit not in (pivot, partner))
            pair = tuple(sorted((pivot, partner)))
            for suffix in visit(rest):
                result.add(tuple(sorted((pair,) + suffix)))
        return result

    return visit(tuple(sorted(units)))


class ForcedEdgeTests(unittest.TestCase):
    def test_unique_matching_makes_each_witness_edge_forced(self) -> None:
        compatibility = build_compatibility(
            ("a", "b", "c", "d"),
            [[("a", "b", "a", "b", "a", "c", "d", "c", "d", "c")]],
        )
        result = forced_edges(compatibility)
        self.assertEqual(result.status, "analyzed")
        self.assertEqual(result.original_status, "unique")
        self.assertEqual(result.queries_run, 2)
        self.assertEqual([item.status for item in result.edge_evidence], ["forced", "forced"])
        self.assertTrue(all(item.witness_count == 0 for item in result.edge_evidence))

    def test_multiple_matching_makes_witness_edges_not_forced(self) -> None:
        compatibility = build_compatibility(
            ("a", "b", "c", "d"),
            [[("a", "b", "c", "d")]],
        )
        result = forced_edges(compatibility)
        self.assertEqual(result.status, "analyzed")
        self.assertEqual(result.original_status, "multiple")
        self.assertEqual(result.queries_run, 2)
        self.assertTrue(all(item.status == "not_forced" for item in result.edge_evidence))
        self.assertTrue(all(item.witness_count > 0 for item in result.edge_evidence))
        self.assertTrue(all(item.alternative_witness for item in result.edge_evidence))

    def test_unseen_only_extensions_are_tested_in_full_scope(self) -> None:
        compatibility = build_compatibility(
            ("a", "b", "c", "d"),
            [[("a", "b")]],
        )
        result = forced_edges(compatibility)
        self.assertEqual(result.original_status, "multiple")
        self.assertTrue(all(item.status == "not_forced" for item in result.edge_evidence))

    def test_original_infeasibility_skips_edge_queries(self) -> None:
        compatibility = build_compatibility(
            ("a", "b", "c", "d"),
            [[("a", "a", "b", "b")]],
        )
        result = forced_edges(compatibility)
        self.assertEqual(result.status, "infeasible")
        self.assertEqual(result.original_status, "none")
        self.assertIsNone(result.selected_witness)
        self.assertEqual(result.edge_evidence, ())

    def test_original_budget_unknown_without_witness_is_preserved(self) -> None:
        compatibility = build_compatibility(
            ("a", "b", "c", "d"),
            [[("a", "b", "c", "d")]],
        )
        result = forced_edges(compatibility, node_budget=1)
        self.assertEqual(result.status, "unknown_budget")
        self.assertEqual(result.original_status, "unknown_budget")
        self.assertIsNone(result.selected_witness)
        self.assertEqual(result.queries_run, 0)

    def test_original_budget_unknown_with_witness_keeps_edge_evidence(self) -> None:
        compatibility = build_compatibility(
            ("a", "b", "c", "d", "e", "f"),
            [[("a", "b", "c", "d", "e", "f")]],
        )
        result = forced_edges(compatibility, node_budget=3)
        self.assertEqual(result.status, "unknown_budget")
        self.assertEqual(result.original_status, "unknown_budget")
        self.assertIsNotNone(result.selected_witness)
        self.assertEqual(result.queries_run, 3)
        self.assertTrue(all(item.status == "not_forced" for item in result.edge_evidence))

    def test_unknown_edge_query_makes_overall_status_unknown(self) -> None:
        base = build_compatibility(tuple("abcdef"), [[]])
        edges = tuple(tuple(edge) for edge in ("ac", "ad", "ae", "af", "bd", "be", "bf", "cd", "ce"))
        compatibility = replace(base, edges=edges)
        result = forced_edges(compatibility, node_budget=4)
        self.assertEqual(result.original_status, "multiple")
        self.assertEqual(result.status, "unknown_budget")
        self.assertEqual(result.queries_run, 3)
        self.assertEqual(result.queries_skipped, 0)
        self.assertEqual(result.edge_evidence[-1].edge, ("c", "e"))
        self.assertEqual(result.edge_evidence[-1].status, "unknown")
        self.assertEqual(result.edge_evidence[-1].query_status, "unknown_budget")

    def test_exhaustive_synthetic_crosscheck(self) -> None:
        cases = (
            (
                ("a", "b", "c", "d"),
                [[("a", "b", "a", "b", "a", "c", "d", "c", "d", "c")]],
            ),
            (("a", "b", "c", "d"), [[("a", "b", "c", "d")]]),
            (("a", "b", "c", "d"), [[("a", "b")]]),
        )
        for units, partitions in cases:
            with self.subTest(units=units, partitions=partitions):
                compatibility = build_compatibility(units, partitions)
                matchings = _all_matchings(compatibility.units, compatibility.edges)
                result = forced_edges(compatibility)
                self.assertTrue(matchings)
                self.assertIsNotNone(result.selected_witness)
                for item in result.edge_evidence:
                    without = {matching for matching in matchings if item.edge not in matching}
                    expected = "forced" if not without else "not_forced"
                    self.assertEqual(item.status, expected)


if __name__ == "__main__":
    unittest.main()
