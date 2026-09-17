# Homophonic solver review

Review date: 2026-09-16.

This review covers `experiments/homophonic/solver.py` and
`experiments/homophonic/test_solver.py`. It checks the bound, capacity rules,
search state, edge cases, and result fields. It does not run reference or
manuscript experiments.

## Result

The search bound is mathematically safe. The capacity checks and warm-start
root are correct. The candidate metadata defect from the first review is
resolved. No unresolved correctness or reporting defect remains in this scope.

## Resolved finding: candidate counts included impossible candidates

The first review found that `_candidate_lists()` grouped lexicon entries by
word length only. It counted entries that violated repeated-unit equality or
root capacity.

The current `_candidate_lists()` filters each lane with
`_candidate_compatible(..., {}, capacity)`. The candidate fields now describe
root-compatible entries.

For example:

```python
solve_lexicon(
    {("x", "x"): 1},
    {("a", "b")},
    ("a", "b"),
    capacity=1,
    node_budget=0,
)
```

The current result reports zero candidates and one missing candidate. The same
holds for `("x", "y")`, candidate `("a", "a")`, and capacity one.

The new regression test covers repeated-unit, capacity, and three-unit root
conflicts. The `no_candidates` fast path now handles these cases.

The score and bound values were already correct because `_upper_bound()` checks
each candidate against the partial map and capacity.

## Bound and capacity checks

For a partial map, `_candidate_compatible()` checks three independent rules:

* An assigned cipher unit must keep its assigned plaintext letter.
* Repeated unassigned cipher units must use one plaintext letter.
* Distinct cipher units must not exceed a plaintext-letter capacity.

`_upper_bound()` adds a type weight when at least one candidate passes those
checks. It may count candidates from different word types that require
conflicting assignments. This only increases the bound, so it remains
admissible.

The global capacity test rejects a total map when
`capacity * alphabet_size < cipher_symbol_count`. `_complete_key()` then
fills every remaining cipher unit without exceeding each capacity. This is
feasible whenever the global test passes.

Capacity one matches the injective solver on the tested tiny cases. Unlimited
capacity permits multiple cipher units to map to one plaintext letter.

## Search state and edge cases

The search pushes an empty root even when an initial key is supplied. The
initial key supplies only a lower-bound completion. It does not remove root
branches. The frontier stores every child whose bound is at least the current
score. At a budget stop, the maximum frontier bound becomes `upper_bound`.

The empty input, no-candidate, zero-weight, infeasible-capacity, repeated-unit,
tuple-unit, duplicate-entry, and invalid-input cases have focused tests.
The no-candidate and zero-budget bound paths report a certified score with no
frontier traversal. They set `search_exhausted` to `False`. The result config
now defines this field as an empty frontier after traversal or valid pruning.
It states that the field does not mean that every key was enumerated.

## Independent checks

I ran an independent exhaustive checker. It used direct products of plaintext
assignments and did not use the solver bound. It checked 1,080 random cases,
4,320 budget results, and 402 valid warm starts. It checked capacities one,
two, and unlimited, zero weights, empty words, repeated units, and invalid
total capacities.

I also checked 4,820 valid random partial candidate cases against a separate
compatibility function. Every result matched. A second run used 13,976 random
cases with custom symbol orders and valid partial warm starts. Every certified
score matched the direct optimum, and every direct optimum remained inside the
reported bounds.

The focused solver and unit test command passed:

```text
PYTHONPATH=src:. python -m unittest experiments.homophonic.test_solver experiments.homophonic.test_units -v
Ran 20 tests ... OK
```

No reference or manuscript data were read or used.

The solver remains a finite synthetic prototype. It does not validate a
tokenizer, a historical homophonic system, a language, or a decipherment.

No unresolved finding remains in this review.
