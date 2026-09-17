"""Synthetic proof helper for a safe observed-unit quotient.

The helper examines only a validated cyclic-pair compatibility graph.  It
does not read corpus files, select unseen mates, assign letters, or score
plaintext.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, replace
from typing import Literal

from experiments.cyclic_pairing.forced import EdgeEvidence, forced_edges
from experiments.cyclic_pairing.pairing import (
    Compatibility,
    DEFAULT_NODE_BUDGET,
    Pair,
    enumerate_matchings,
)


EdgeStatus = Literal["forced", "impossible", "possible", "unknown"]
QuotientStatus = Literal["proved", "ambiguous", "unknown_budget", "infeasible"]


@dataclass(frozen=True, slots=True)
class EdgeCertificate:
    """Source-free evidence for one candidate edge."""

    edge: Pair
    status: EdgeStatus
    query_status: str
    nodes_visited: int
    witness: tuple[Pair, ...] | None
    certificate: str


@dataclass(frozen=True, slots=True)
class QuotientResult:
    """Evidence and a quotient of observed units, when the evidence is safe."""

    status: QuotientStatus
    full_status: str
    full_witness: tuple[Pair, ...] | None
    observed_units: tuple[str, ...]
    unseen_units: tuple[str, ...]
    forced_pairs: tuple[Pair, ...]
    singleton_units: tuple[str, ...]
    classes: tuple[tuple[str, ...], ...]
    unit_to_class: tuple[tuple[str, tuple[str, ...]], ...]
    forced_certificates: tuple[EdgeCertificate, ...]
    edge_certificates: tuple[EdgeCertificate, ...]
    unknown_edges: tuple[Pair, ...]
    evidence_counts: tuple[tuple[str, int], ...]
    certificate: str


def _signature(matching: tuple[Pair, ...], observed: frozenset[str]) -> tuple[Pair, ...]:
    return tuple(edge for edge in matching if set(edge) <= observed)


def _restrict_to_edge(compatibility: Compatibility, edge: Pair) -> Compatibility:
    left, right = edge
    kept = tuple(
        candidate
        for candidate in compatibility.edges
        if candidate == edge or (left not in candidate and right not in candidate)
    )
    orientations = tuple(item for item in compatibility.edge_orientations if item[0] in kept)
    return replace(compatibility, edges=kept, edge_orientations=orientations)


def _query_edge(compatibility: Compatibility, edge: Pair, node_budget: int) -> EdgeCertificate:
    query = enumerate_matchings(
        _restrict_to_edge(compatibility, edge),
        scope="full",
        node_budget=node_budget,
        max_results=2,
    )
    witness = query.matchings[0] if query.matchings else None
    if witness is not None:
        return EdgeCertificate(
            edge, "possible", query.status, query.nodes_visited, witness,
            "an edge-constrained full matching witness exists",
        )
    status: EdgeStatus = "impossible" if query.status == "none" else "unknown"
    certificate = (
        "edge-constrained search exhausted without a full matching"
        if status == "impossible"
        else "edge-constrained search stopped without a witness"
    )
    return EdgeCertificate(
        edge, status, query.status, query.nodes_visited, None, certificate
    )


def _from_forced(item: EdgeEvidence) -> EdgeCertificate:
    status: EdgeStatus = "possible" if item.status == "not_forced" else item.status
    return EdgeCertificate(
        item.edge,
        status,
        item.query_status,
        item.nodes_visited,
        item.alternative_witness,
        item.certificate,
    )


def _empty_result(
    compatibility: Compatibility,
    *,
    status: QuotientStatus,
    full_status: str,
    certificate: str,
) -> QuotientResult:
    return QuotientResult(
        status, full_status, None, compatibility.observed_units,
        compatibility.unseen_units, (), (), (), (), (), (), (), (), certificate,
    )


def _evidence_counts(certificates: tuple[EdgeCertificate, ...]) -> tuple[tuple[str, int], ...]:
    return tuple(sorted(Counter(item.status for item in certificates).items()))


def build_observed_quotient(
    compatibility: Compatibility,
    *,
    node_budget: int = DEFAULT_NODE_BUDGET,
) -> QuotientResult:
    """Prove equal observed classes over every matching found by full queries.

    The result is ``ambiguous`` only after two full witnesses have different
    observed-edge signatures. Any unresolved query returns ``unknown_budget``.
    """

    if not isinstance(compatibility, Compatibility):
        raise TypeError("compatibility must be a Compatibility instance")
    forced = forced_edges(compatibility, node_budget=node_budget)
    selected = forced.selected_witness
    if selected is None:
        status: QuotientStatus = (
            "infeasible" if forced.original_status == "none" else "unknown_budget"
        )
        return _empty_result(
            compatibility,
            status=status,
            full_status=forced.original_status,
            certificate=forced.certificate,
        )

    observed = frozenset(compatibility.observed_units)
    base_signature = _signature(selected, observed)
    evidence_by_edge = {item.edge: item for item in forced.edge_evidence}
    forced_selected = {
        item.edge for item in forced.edge_evidence if item.status == "forced"
    }
    forced_members = {unit for edge in forced_selected for unit in edge}
    forced_pairs = {edge for edge in forced_selected if set(edge) <= observed}
    flat_members = [unit for edge in forced_pairs for unit in edge]
    if len(flat_members) != len(set(flat_members)):
        raise RuntimeError("forced observed pairs are not disjoint")

    forced_certificates = tuple(_from_forced(item) for item in forced.edge_evidence)
    certificates: list[EdgeCertificate] = []
    unknown_edges: set[Pair] = set()
    alternative_signatures: set[tuple[Pair, ...]] = set()

    # An observed-to-unseen forced edge also occupies its observed endpoint.
    # An alternative witness can change the observed relation, so inspect all
    # forced-edge queries, including pairs that are not both observed.
    for item in forced.edge_evidence:
        if item.status == "unknown" or item.query_status == "unknown_budget":
            unknown_edges.add(item.edge)
        if item.alternative_witness is not None:
            signature = _signature(item.alternative_witness, observed)
            if signature != base_signature:
                alternative_signatures.add(signature)

    for edge in compatibility.edges:
        if not set(edge) <= observed:
            continue
        evidence = evidence_by_edge.get(edge)
        if evidence is not None:
            certificate = _from_forced(evidence)
        elif set(edge) & forced_members:
            certificate = EdgeCertificate(
                edge, "impossible", "derived", 0, None,
                "a certified forced edge already uses one endpoint",
            )
        else:
            certificate = _query_edge(compatibility, edge, node_budget)
        certificates.append(certificate)
        if certificate.status == "unknown" or certificate.query_status == "unknown_budget":
            unknown_edges.add(edge)
        if certificate.witness is not None:
            signature = _signature(certificate.witness, observed)
            if signature != base_signature:
                alternative_signatures.add(signature)

    edge_certificates = tuple(certificates)
    common = dict(
        full_status=forced.original_status,
        full_witness=selected,
        observed_units=compatibility.observed_units,
        unseen_units=compatibility.unseen_units,
        forced_pairs=tuple(sorted(forced_pairs)),
        forced_certificates=forced_certificates,
        edge_certificates=edge_certificates,
        unknown_edges=tuple(sorted(unknown_edges)),
        evidence_counts=_evidence_counts(edge_certificates),
    )
    if alternative_signatures:
        return QuotientResult(
            status="ambiguous", singleton_units=(), classes=(), unit_to_class=(),
            certificate="two full witnesses have different observed relations",
            **common,
        )
    if forced.status == "unknown_budget" or unknown_edges:
        return QuotientResult(
            status="unknown_budget", singleton_units=(), classes=(), unit_to_class=(),
            certificate="observed relation has unproved edge evidence",
            **common,
        )

    class_members = {unit for pair in forced_pairs for unit in pair}
    singleton_units = tuple(
        unit for unit in compatibility.observed_units if unit not in class_members
    )
    class_list = [tuple(sorted(pair)) for pair in forced_pairs]
    class_list.extend((unit,) for unit in singleton_units)
    classes = tuple(sorted(class_list))
    unit_to_class = tuple(sorted((unit, group) for group in classes for unit in group))
    return QuotientResult(
        status="proved", singleton_units=singleton_units, classes=classes,
        unit_to_class=unit_to_class,
        certificate="all observed-observed candidate edges have fixed relation evidence",
        **common,
    )


__all__ = ["EdgeCertificate", "QuotientResult", "build_observed_quotient"]
