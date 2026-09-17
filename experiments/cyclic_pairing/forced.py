"""Bounded forced-edge checks for synthetic cyclic pair graphs.

The module removes one edge from a validated graph and tests for a remaining
perfect matching. It does not assign plaintext letters or read source files.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Literal

from .pairing import (
    DEFAULT_NODE_BUDGET,
    Compatibility,
    MatchingResult,
    Pair,
    enumerate_matchings,
)


MAX_EDGE_QUERIES = 32
EdgeStatus = Literal["forced", "not_forced", "unknown"]
OverallStatus = Literal["analyzed", "infeasible", "unknown_budget"]


@dataclass(frozen=True, slots=True)
class EdgeEvidence:
    """The bounded result for one edge in the selected witness."""

    edge: Pair
    status: EdgeStatus
    query_status: str
    witness_count: int
    nodes_visited: int
    node_budget: int
    alternative_witness: tuple[Pair, ...] | None
    certificate: str


@dataclass(frozen=True, slots=True)
class ForcedEdgeResult:
    """Forced-edge evidence with the original search state preserved."""

    status: OverallStatus
    original_status: str
    original_witness_count: int
    original_nodes_visited: int
    original_node_budget: int
    selected_witness: tuple[Pair, ...] | None
    edge_evidence: tuple[EdgeEvidence, ...]
    queries_run: int
    queries_skipped: int
    max_edge_queries: int
    certificate: str


def _remove_edge(compatibility: Compatibility, edge: Pair) -> Compatibility:
    normalised = tuple(sorted(edge))
    if normalised not in compatibility.edges:
        raise ValueError("edge is not in the compatibility graph")
    edges = tuple(candidate for candidate in compatibility.edges if candidate != normalised)
    orientations = tuple(
        item
        for item in compatibility.edge_orientations
        if item[0] != normalised
    )
    return replace(
        compatibility,
        edges=edges,
        edge_orientations=orientations,
    )


def _edge_evidence(
    edge: Pair,
    query: MatchingResult,
) -> EdgeEvidence:
    witnesses = query.matchings
    if witnesses:
        return EdgeEvidence(
            edge=edge,
            status="not_forced",
            query_status=query.status,
            witness_count=len(witnesses),
            nodes_visited=query.nodes_visited,
            node_budget=query.node_budget,
            alternative_witness=witnesses[0],
            certificate="an edge-removed graph has a complete alternative matching",
        )
    if query.status == "none":
        return EdgeEvidence(
            edge=edge,
            status="forced",
            query_status=query.status,
            witness_count=0,
            nodes_visited=query.nodes_visited,
            node_budget=query.node_budget,
            alternative_witness=None,
            certificate="edge removal has no complete matching after exhaustive search",
        )
    return EdgeEvidence(
        edge=edge,
        status="unknown",
        query_status=query.status,
        witness_count=0,
        nodes_visited=query.nodes_visited,
        node_budget=query.node_budget,
        alternative_witness=None,
        certificate="edge removal found no witness before its budget ended",
    )


def forced_edges(
    compatibility: Compatibility,
    *,
    node_budget: int = DEFAULT_NODE_BUDGET,
) -> ForcedEdgeResult:
    """Classify edges in one bounded full matching witness.

    An edge is forced when the original graph has a matching and the graph
    without that edge has no matching. A valid alternative witness makes an
    edge ``not_forced``, even when its query also reaches the budget. A query
    with no witness and an incomplete search returns ``unknown``. Each edge
    query receives the same node budget as the original search.
    """

    if not isinstance(compatibility, Compatibility):
        raise TypeError("compatibility must be a Compatibility instance")
    original = enumerate_matchings(
        compatibility,
        scope="full",
        node_budget=node_budget,
        max_results=2,
    )
    selected = original.matchings[0] if original.matchings else None
    if selected is None:
        if original.status == "none":
            status: OverallStatus = "infeasible"
            certificate = "the original declared graph has no full matching"
        else:
            status = "unknown_budget"
            certificate = "the original search ended without a matching witness"
        return ForcedEdgeResult(
            status=status,
            original_status=original.status,
            original_witness_count=0,
            original_nodes_visited=original.nodes_visited,
            original_node_budget=original.node_budget,
            selected_witness=None,
            edge_evidence=(),
            queries_run=0,
            queries_skipped=0,
            max_edge_queries=MAX_EDGE_QUERIES,
            certificate=certificate,
        )

    evidence: list[EdgeEvidence] = []
    query_edges = selected[:MAX_EDGE_QUERIES]
    for edge in query_edges:
        query_compatibility = _remove_edge(compatibility, edge)
        query = enumerate_matchings(
            query_compatibility,
            scope="full",
            node_budget=node_budget,
            max_results=2,
        )
        evidence.append(_edge_evidence(edge, query))
    skipped = len(selected) - len(query_edges)
    if original.status not in ("unique", "multiple"):
        status = "unknown_budget"
        certificate = (
            "edge queries ran for one witness, but the original matching search was incomplete"
        )
    elif skipped or any(item.status == "unknown" for item in evidence):
        status = "unknown_budget"
        certificate = (
            "at least one edge query stopped before exhaustive forced-edge evidence"
        )
    else:
        status = "analyzed"
        certificate = (
            "edge queries classify the selected witness; original matching status is preserved"
        )
    return ForcedEdgeResult(
        status=status,
        original_status=original.status,
        original_witness_count=len(original.matchings),
        original_nodes_visited=original.nodes_visited,
        original_node_budget=original.node_budget,
        selected_witness=selected,
        edge_evidence=tuple(evidence),
        queries_run=len(evidence),
        queries_skipped=skipped,
        max_edge_queries=MAX_EDGE_QUERIES,
        certificate=certificate,
    )


__all__ = [
    "EdgeEvidence",
    "ForcedEdgeResult",
    "MAX_EDGE_QUERIES",
    "forced_edges",
]
