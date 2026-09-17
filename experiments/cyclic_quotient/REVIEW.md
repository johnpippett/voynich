# Observed quotient helper review

Review date: 2026-09-17.

This is a synthetic, read-only review. It uses no corpus stream, planted
key, runner, or source data. No source code was edited by this review.

Reviewed final snapshot hashes:

- `experiments/cyclic_quotient/quotient.py`: `8186751798ae74884d0071735612844ab65819e90d9e9a4aadff7b85721f249e`;
- `experiments/cyclic_quotient/test_quotient.py`: `13ca2f2bc3f93115607026364e2fe1ab19d5fccdf9d82c21081986ed6571b217`;
- `experiments/cyclic_quotient/__init__.py`: `4652ee63c036a252655728795e5ff6a3feeb3f96f26ad78cd94074e8a96f4f5e`.

## Verification

The focused suite passed 9 tests:

```sh
PYTHONPATH=src:. python -m unittest experiments.cyclic_quotient.test_quotient -v
```

An independent exact checker ran 8,000 deterministic factory cases with 2,
4, 6, or 8 declared units. It enumerated every full perfect matching and
compared the observed-edge signature with the helper result. It found zero
mismatches.

The fixtures cover these cases:

- three full matchings with different observed relations;
- fixed observed pairs with several unseen completions;
- an observed singleton with an unresolved unseen mate;
- a forced observed-to-unseen edge;
- no full matching;
- a budget stop without a witness; and
- preservation of word boundaries and the input compatibility value.

## Correctness checks

`forced_edges` and every edge-constrained query use `scope="full"`. The helper
therefore tests the complete declared inventory. It does not use an observed
scope to infer unseen mates.

The helper compares the observed-edge signature of each available witness.
A different signature returns `ambiguous`. A present observed-observed edge
must have a full edge-constrained witness. A missing graph edge is a safe
negative certificate. A budget stop without a witness returns `unknown_budget`.
These rules do not turn one witness into a unique observed relation.

The quotient contains only forced observed-observed pairs and observed
singletons. The result keeps one full witness as evidence, but it does not add
its unseen pairs to `classes` or `unit_to_class`. The observed-to-unseen
singleton fixture confirms that no unseen unit enters the quotient.

## Resolved finding

The first snapshot reviewed used all forced-edge members to form the singleton
set. In this case, a forced observed-to-unseen edge removed its observed unit
from the quotient. For example, units `a`, `b`, `c`, and `x` with the stream
`b c b c a` have edges `a-x` and `b-c`. The correct classes are `("a",)` and
`("b", "c")`; the earlier snapshot returned only `("b", "c")`.

The current helper derives singleton units from observed units that are not in
forced observed-observed pairs. The added regression test
`test_forced_observed_unseen_pair_stays_observed_singleton` passes. This issue
is resolved in the reviewed snapshot.

## Conservative budget behavior

The helper can abstain when a positive edge query finds a witness but also
returns `query_status="unknown_budget"`. It records that edge as unknown even
when the edge has an unseen endpoint and the observed relation cannot change.
It also abstains when the original full search has `unknown_budget`.

A synthetic example uses units `a`, `b`, `w`, `x`, `y`, and `z`, with separate
streams `a` and `b`. No observed-observed edge exists. At node budget 3, the
helper returns `unknown_budget`; with the default budget it returns the proved
classes `("a",)` and `("b",)`. This is a conservative abstention, not a false
quotient. It can reduce coverage when only unseen mate alternatives remain.
The current behavior is safe. A later protocol may separate unresolved unseen
completion evidence from evidence required for the observed relation.

No material blocker remains in the reviewed snapshot. This helper does not
prove a language, plaintext, or manuscript result.
