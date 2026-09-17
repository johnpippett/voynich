# Review of the pivot-group bound

Date: 2026-09-17.

This is an independent review of the synthetic-only scalar bound in
`experiments/group_bound/pivot.py`. It covers `test_pivot.py` and `README.md`.
It does not use reference data, VMS data, or the bitset engine.

## Source record

- `pivot.py`: `8573d5d620c474ef24b5c5c875d26442ff8c7dcfbfd97fef98650d520d479d8b`
- `test_pivot.py`: `14ca0bb0a903ffddd91636717eb6ed66d314eca87b4958b4527cc60cd9176b17`
- `README.md`: `f33926273e01bea5b64bfcdd050e7b47c31fe76b4c9c5f4cb3f660c5affd620c`

## Result

I found no mathematical or implementation defect in the checked scope.

For a group `G` with pivot `c`, every word in `G` contains `c`. Let `P` be a
valid partial map. For any valid complete extension, let `p` be the value of
`c`. Every hit word in `G` has an active candidate row whose pivot position is
`p`. Its weight is included in `S(G, p, P)`. Therefore the hit weight in `G`
is at most `max_p S(G, p, P)`. The ungrouped words use the independent bound.
Summing these terms proves that the returned `group_bound` is an upper bound.

For each group and each `p`, `S(G, p, P)` contains only active word types.
The group term is therefore no greater than the independent weight for that
group. The ungrouped terms are equal in both bounds. This proves
`true_score <= group_bound <= independent_bound` for every feasible partial
map. Ignoring cross-group conflicts and capacity conflicts can make the bound
loose, but cannot make it low.

The proof still holds for capacities `1`, `2`, and `None`, repeated cipher
units, repeated pivot units, zero weights, empty words, empty candidate lanes,
tuple units, and Unicode atomic units. A complete root candidate cache is
required. `CandidateConstructionLimit` raises before the object returns a
bound, so a resource limit cannot produce an under-bound result.

## Independent checks

The focused suite passed:

```text
PYTHONPATH=src:. python -m unittest experiments.group_bound.test_pivot -v
Ran 6 tests ... OK
```

Private standard-library checks also passed:

- Seed `20260917`: 160 random instances, all feasible capacities, all partial
  maps, and both static and explicit groups. Every case satisfied
  `true_score <= group_bound <= independent_bound`.
- Seed `771`: 200 random instances and all feasible partial maps. The returned
  independent bound matched frozen `solver._upper_bound` in every case.
- Unicode tuple units, empty words, zero weights, no-candidate lanes, explicit
  mapping groups, duplicate and invalid group specifications, total-capacity
  infeasibility, input mutation, and candidate-row limits passed.

The result reports `claims_global_optimality: False` and states that it does
not certify an optimum or enumerate maps. Infeasible total capacity returns
`None` for both bounds. A partial map remains queryable when candidate rows
become empty. The normalized cache and group properties do not expose mutable
construction state.

## Minor documentation correction

`README.md` says that “the groups partition the word types.” Explicit groups
can leave word types in `ungrouped_words`. The text should say that the groups
and the ungrouped word types partition the word types. This does not affect the
calculation or the proof.

The result field `status: "complete"` can also be read as search completion,
although it means that the capacity domain is feasible and the candidate cache
is complete. The existing `claims_global_optimality: False` field and scope
limits prevent a certification claim. A future public caller should document
the meaning of this status explicitly.

No source or README files were changed during this review.
