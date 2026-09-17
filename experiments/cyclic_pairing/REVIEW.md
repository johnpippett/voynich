# Cyclic pairing review

Review date: 2026-09-17.

This review uses synthetic unit streams only. It does not read or run a
Latin, Italian, Voynich, reference, or planted-key stream.

Reviewed hashes:

- `experiments/cyclic_pairing/pairing.py`: `da9c89b4738d0dde959a3c730111dee864c05cd3e3b20932b2b8a3f30a57da95`;
- `experiments/cyclic_pairing/test_pairing.py`: `266d49547bf361a0f2ac290c88fb29f3e9ac86d08dbd73450654d50e87c1bf3d`;
- `experiments/cyclic_pairing/forced.py`: `3f3a4fc450b5921905b8931310379d8361a6ca0b8d2989b8b8e939ddbc8d76a4`;
- `experiments/cyclic_pairing/test_forced.py`: `1f33dbd220e709446634f78ac656a01c4ad180538c1427c14049073e98eb893c`;
- `docs/plans/cyclic-pairing-control-v1.md`: `61b424e8e563981853e9ee28b56cf765eb09fbee0178fd5b5300358880515e0d`;
- `docs/research/cyclic-emitter-pairing.md`: `df15917ad990e06cf017410cfa50daa0a691439444af31d25d7f226b1bd0064b`.

## Mathematical result

For a pair `{u,v}`, project each flattened partition onto those two units.
The pair is compatible if and only if every projection alternates and all
non-empty projections have the same first unit. The count difference check is
redundant because an alternating binary sequence has counts that differ by at
most one. It remains a useful audit check.

The condition is sufficient. The common first unit gives the reset phase. The
alternating projection gives every later phase. Other plaintext letters do not
change this projected order. Word boundaries do not reset the phase. Partition
boundaries do reset it.

If `u` is observed and `v` is unseen, the pair is compatible only when each
partition contains at most one `u`, and all non-empty partitions start with
`u`. If both units are unseen, their projections are empty, so the pair is
always compatible and has no observed orientation. Therefore the unseen
subgraph is a complete graph.

A full codebook is a perfect matching of the complete declared inventory. A
matching on the observed subgraph is conditional. It assumes that every
observed unit pairs with another observed unit.

For a fixed observed matching and `k` unseen units, unseen-only extensions are
impossible when `k` is odd and number `(k-1)!!` when `k` is even. Cross edges
can add other full matchings. Observed uniqueness therefore does not prove
full uniqueness. An observed odd scope also does not prove that a full map is
impossible.

## Synthetic checks

Independent small checks gave these results:

| Declared units and stream | Observed result | Full result |
| --- | --- | --- |
| `a b c d`, `a b` | unique `ab` | multiple; three complete pairings exist |
| `a b c d`, `a b a b` | unique `ab` | unique `ab-cd` |
| `a b c d`, `a b a b c` | `not_closed` | unique `ab-cd` |
| `a b`, partitions `a b` and `b a` | none | none; reset orientations conflict |
| `a b`, partitions `a` and `a` | not closed | unique `ab`; `b` is unseen |

The first row shows that an observed unique result can have several full
maps. The third row shows that `not_closed` in the observed scope can still
have a full map. The one-item reset case shows why a singleton can have an
unseen mate.

The synthetic suite passed 12 tests:

```sh
PYTHONPATH=src python -m unittest experiments.cyclic_pairing.test_pairing -v
```

## Code review

No blocking defect exists on the `build_compatibility` path. The builder
creates distinct sorted pairs, records reset orientations, and labels unseen
units. A bounded search reports `unknown_budget` when it stops before it can
prove uniqueness or infeasibility. A fully exhausted search can certify
`unique` or `none`, even for a large inventory. A dense 52-unit graph can
still require too many search nodes, so a budget result must remain unknown.

Two input-contract issues remain:

1. `Compatibility` is an exported dataclass. A caller can construct it with a
   self-edge or inconsistent fields, and `enumerate_matchings` trusts those
   fields. For example, a manual self-edge can produce a self-pairing. Treat
   `build_compatibility` output as the supported input, or make the type
   private and validate construction.
2. The helper defaults to two witnesses, which is enough to prove
   `multiple`, but `max_results` lets a caller request more. State that the
   default cap is two; do not describe two as a hard API limit.

The `neighbors` method now rejects an unknown scope. These two issues do not
change results produced by the builder. Treat the first as a correctness defect
only if direct dataclass construction is a supported API. Otherwise document
that `Compatibility` values must come from the builder or a validated graph
restrictor. The second is a wording fix.

The final source snapshot was checked against the previously reviewed logic.
The `pairing.py` hash change is docstring-only. The `forced.py` hash change is
also docstring-only. The bounded-status fix remains present: incomplete
original or edge searches return `unknown_budget`. No pairing algorithm or
forced-edge logic changed.

## Partial grouping and protocol limits

A forced edge can reduce the graph to one pair group. It does not assign a
plaintext letter or prove the rest of the map. When the full graph is multiple,
keep the remaining matching alternatives. When it is `unknown_budget`, keep
forced evidence conditional on later exhaustive checks. Do not choose a
non-forced edge set.

Even a unique full matching leaves up to `26!` assignments of pair groups to
plaintext letters. An unseen pair has no observed orientation. A bounded or
observed result cannot resolve either ambiguity. The method can support a later
exact grouping step, but it cannot prove decipherment.

The final control plan uses `scope="full"`, a 100,000-node budget, and at most
26 edge queries. It requires a pre-run hash freeze, complete input verification,
and diagnostics after the pairing record. The plan has no runner or real-data
result in this review. It remains a synthetic protocol design for the fixed
emitter and does not test the Voynich manuscript.

## Exact larger-domain method

For a declared inventory of at most 52 units, use an exact maximum-cardinality
matching algorithm for feasibility. A perfect matching exists exactly when
its size is half the inventory. Given one perfect matching `M`, remove each
edge in `M` and test feasibility again. A surviving perfect matching proves
multiple maps. No surviving matching for every edge proves that `M` is unique,
and each failed edge deletion identifies a forced edge. This needs at most 26
feasibility checks and does not enumerate invisible pairings.

Run the same method on the observed induced graph only for the conditional
observed result. Report full feasibility and observed conditional results as
separate fields. The bounded edge-deletion extension is reviewed in
`experiments/cyclic_pairing/FORCED_REVIEW.md`; it reports `unknown_budget` when
any edge query is incomplete.

This method tests an emitter-specific control. It does not recover plaintext,
letter labels, or a Voynich decipherment.
