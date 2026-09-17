# Cyclic quotient study review

This review covers the synthetic study core and its focused tests. It uses no
corpus, manuscript stream, test stream, planted key, or real source input.

Reviewed source hashes:

- `study.py`: `69d3cd5b6d9ecf1e9f2155807e54734b4f6fc17d2d68a89fc5c21f972693ff83`
- `test_study.py`: `7c488ab322cd88b44c6a534fbbc10cdea1326b73952c96c5e8d62d829ec90a54`
- `quotient.py`: `8186751798ae74884d0071735612844ab65819e90d9e9a4aadff7b85721f249e`
- `test_quotient.py`: `13ca2f2bc3f93115607026364e2fe1ab19d5fccdf9d82c21081986ed6571b217`

Verification passed:

```text
python -m py_compile experiments/cyclic_quotient/study.py experiments/cyclic_quotient/test_study.py
PYTHONPATH=src:. python -m unittest experiments.cyclic_quotient.test_quotient experiments.cyclic_quotient.test_study -v
Ran 16 tests in 0.007s
OK
```

The study uses capacity `1`, a `100000` node budget, the `bitset` bound
engine, and no initial key. It sends the frozen integer objective weights and
the frozen weighted symbol order to the solver. It does not call the solver
when the quotient is ambiguous, infeasible, or unknown by budget.

The study writes `quotient.json` before it can call the solver. It writes and
closes `fit.keys.json` before it writes `fit.json`. The class map uses only
the proven observed relation. It does not select an unseen mate or a matching
to resolve an ambiguous relation.

Resolved finding: each successful fit and key record now stores
`quotient_evidence_sha256`, which matches the bytes of `quotient.json`. Both
records also store `open_slot_count`. Focused tests cover zero open slots and
one singleton open slot. A synthetic four-unit run independently confirmed
the hash binding and checked that serialized evidence contains counts and
maps, not raw training words or cipher word arrays.

No material blocker remains in this bounded study core. The result can test a
finite lexicon objective after a proved observed quotient. It cannot identify
a language, recover unresolved unseen mates, or prove a plaintext or a
Voynich manuscript decipherment.

## Follow-up residual evidence review

The current `quotient.json` does not yet satisfy the plan requirement to keep
the residual graph and all unseen-mate alternatives. `_quotient_evidence`
receives only `QuotientResult`. That result keeps one full witness and
selected-edge certificates. Its edge certificates cover observed-observed
candidate edges. It does not keep the complete compatibility edges or their
reset orientations.

An independent synthetic graph showed the loss. Forced edges `a-b` and `c-d`
had observed singleton `e` and unseen units `x`, `y`, and `z`. All of
`e-x`, `e-y`, and `e-z` had a full matching extension. The selected witness
used `e-x`, but the serialized evidence contained `e-x` only; it omitted
`e-y` and `e-z`.

The minimal representation should pass the validated `Compatibility` object
to the evidence writer and store all sorted graph edges and per-partition
edge orientations. It should also store residual vertices, consisting of
observed singleton units and unseen units, plus residual candidate edges after
removing endpoints of forced observed-observed pairs. Keep edge status clear:
a graph edge is a local compatibility candidate, not proof of a full matching
extension. If the protocol requires every residual edge to be called
globally feasible, run an edge-constrained full matching check for each edge
and store its status and witness. One full witness cannot prove that claim.

This follow-up is a material blocker for the outer protocol freeze until the
graph evidence is stored or the plan narrows its residual-evidence claim.

## Resolution review

The core now stores the complete compatibility graph, per-partition edge
orientations, and the residual graph. The residual vertices contain observed
singleton units and unseen units. The residual edges exclude endpoints of
forced observed-observed pairs. Each graph edge is labeled as a compatibility
candidate.

The persisted completion meaning is now explicit: all residual perfect
matchings plus the fixed forced observed-observed pairs. The record does not
call each residual edge globally extendable. This matches the clarified plan.

Current hashes:

- `study.py`: `69ee883e0d1ca92f95cb96664c018e925836244fde83cfbfd0ce43b4ed79db1d`
- `test_study.py`: `18c6940a131acb8246e11ae50d9f142d0887e6db4d6a4a357c1926291c4fa9e0`

The focused quotient and study tests pass: `17/17`. The new synthetic test
records `e-x`, `e-y`, and `e-z` in the residual graph. An independent fixture
check confirmed the same edges, the fixed observed pairs, the orientation
records, and the absence of raw training words and cipher word arrays.

The earlier residual-evidence blocker is resolved for this scope. The study
still provides a finite synthetic or controlled lexicon test; it does not
prove a language, plaintext, or manuscript decipherment.
