# Forced-edge review

Review date: 2026-09-17.

This review uses synthetic graphs only. It does not read or run a Latin,
Italian, Voynich, reference, or planted-key stream.

Reviewed hashes:

- `experiments/cyclic_pairing/forced.py`: `3f3a4fc450b5921905b8931310379d8361a6ca0b8d2989b8b8e939ddbc8d76a4`;
- `experiments/cyclic_pairing/test_forced.py`: `1f33dbd220e709446634f78ac656a01c4ad180538c1427c14049073e98eb893c`;
- pairing base `experiments/cyclic_pairing/pairing.py`: `da9c89b4738d0dde959a3c730111dee864c05cd3e3b20932b2b8a3f30a57da95`;
- plan `docs/plans/cyclic-pairing-control-v1.md`: `61b424e8e563981853e9ee28b56cf765eb09fbee0178fd5b5300358880515e0d`;
- research note `docs/research/cyclic-emitter-pairing.md`: `df15917ad990e06cf017410cfa50daa0a691439444af31d25d7f226b1bd0064b`.

## Exhaustive check

I built a six-unit complete compatibility graph from one synthetic stream. I
then restricted its simple edge set with `dataclasses.replace`. For every one
of the `2^15 = 32,768` edge sets, an independent recursive enumerator produced
the complete set of perfect matchings.

At `node_budget=100000`, `forced_edges` matched the independent result for
all 32,768 graphs:

- infeasible graphs returned `infeasible` with no selected witness;
- one-matching graphs returned `unique` and marked every witness edge
  `forced`;
- multi-matching graphs returned `multiple` and marked each selected witness
  edge `not_forced` when an alternative omitted it;
- every reported alternative witness was in the independent matching set.

The focused suites passed 20 tests: 8 forced-edge tests and 12 pairing tests.
The six-unit budget-4 regression also passed alone:

```sh
PYTHONPATH=src:. python -m unittest experiments.cyclic_pairing.test_forced experiments.cyclic_pairing.test_pairing -v
PYTHONPATH=src:. python -m unittest experiments.cyclic_pairing.test_forced.ForcedEdgeTests.test_unknown_edge_query_makes_overall_status_unknown -v
```

## Resolved bounded-status finding

The previous review found that `forced_edges` could return
`status="analyzed"` when an edge query returned `unknown_budget`. The fix now
sets the overall status to `unknown_budget` when any selected edge query is
unknown or skipped. Its certificate states that forced-edge evidence is
incomplete.

The six-unit graph with edges `ac, ad, ae, af, bd, be, bf, cd, ce` and
`node_budget=4` now returns `unknown_budget`. The original search still
returns `multiple` with witness `af, bd, ce`; the `ce` query still returns
`unknown_budget` with no witness; and that edge evidence still has status
`unknown`.

A selected original witness remains valid. An alternative witness returned by
an edge query remains valid even when that query status is
`unknown_budget`; its existence proves `not_forced` for that edge. The fixed
aggregate status no longer implies complete classification when evidence is
limited.

The final source snapshot was checked against the previously reviewed logic.
The `forced.py` hash change is docstring-only. The `pairing.py` hash change is
also docstring-only. The status fix and edge-query behavior are unchanged.
The focused 20-test result and the six-unit regression therefore apply to the
final source snapshot. The 32,768-graph exhaustive result was not rerun because
the final source delta does not change executable logic.

## Partial grouping and protocol limits

An edge marked `forced` is safe as one pair group only after exhaustive original
and edge-removal searches. It does not identify a plaintext letter. If the full
matching is `multiple`, retain its disjunction and do not select a non-forced
edge set. If any search is `unknown_budget`, treat unproved classifications as
conditional. A unique full matching still leaves the pair-to-letter permutation
unresolved, up to `26!` assignments. Unseen pair orientation is also unresolved.

The final protocol method is a full-inventory search with a 100,000-node budget,
followed by at most 26 edge-removal queries with the same budget. It records
forced, not-forced, and unknown evidence before any planted-key diagnostic. A
pre-run hash freeze and complete source-input verification are required. The
plan has no runner or real-data result yet. It remains a synthetic control for
the fixed emitter and cannot support a decipherment claim.

## Contract scope

The review assumes a `Compatibility` value from `build_compatibility` or a
validated simple graph restrictor. The earlier pairing review records that a
manually constructed dataclass can bypass the no-self-edge invariant. That
input issue is outside this forced-edge result; the budget regression uses
only distinct, sorted edges.

No forced-edge implementation was edited in this review. The method remains
an emitter-specific control check. It does not recover plaintext, letter
labels, or a Voynich decipherment.
