# Threshold query review

Review date: 2026-09-17.

This review covers `experiments/identifiability/threshold.py` and
`experiments/identifiability/test_threshold.py`. It uses small synthetic
finite maps only. It does not read reference or manuscript data.

## Result

The final snapshot passes the threshold review. Query status, witnesses,
capacity rules, hard domains, fingerprints, and cached bounds are sound in the
tested finite cases.

The query tests one fixed integer target. It does not certify a global optimum
unless the caller supplies a separately certified target. It does not prove a
unique key or a historical reading.

## Independent checks

I compared each result with a direct product over all plaintext assignments.
The check covered 180 random problems, capacities one, two, and unlimited,
zero and positive weights, arbitrary targets, repeated units, constraints,
forbidden values, and Hall failures.

It ran 8,640 unbounded queries. Every feasible result had a valid complete key
with the required score. Every infeasible result had no matching brute-force
key. It ran 34,560 bounded queries with node budgets zero, one, two, and five.
No budget result reported a false witness or a false infeasibility result.

The same audit checked 1,641 explicit branch orders. It checked 2,160 repeated
queries after other queries on the same problem object. Results and fingerprints
remained identical. A warm start improved a witness only; it did not restrict
the root search.

The audit also checked every reported `upper_bound` against the true maximum
for each non-empty constrained domain. The final result never under-reported
that maximum.

## Bound and status rules

The candidate-wise bitset bound can count incompatible candidates from
different word lanes. This can only increase the bound, so pruning below the
target is safe. Forbidden values for unassigned units are ignored by the bound,
which makes it loose but safe.

The result uses three search states. `feasible` includes a complete witness.
`infeasible` means domain impossibility, an exhausted search, or an upper bound
below the target. `unknown` means that a live frontier remains after the
declared node budget.

`frontier_upper` reports the live frontier only. The final `upper_bound` also
includes the incumbent and the largest pruned-node bound. This distinction
preserves a valid upper interval after exhaustive pruning.

## Resolved findings

The first implementation exposed mutable domain fields while caching a bound
and a fingerprint. A caller could change `ciphertext_counts`, `capacity`, or
the alphabet after construction. Queries could then combine new scoring data
with an old bound and fingerprint.

The final implementation keeps normalized state in private fields. It exposes
read-only properties, mapping proxies, tuples, and a frozen lexicon. Input
mutation after construction has no effect. Bound metadata returns a copy.
The test `test_problem_state_is_read_only_and_input_mutation_isolated` covers
this contract.

The first bound result also lost scores from branches pruned below a high
target. For example, counts `{'x': 1, 'xy': 1}`, lexicon `{'b', 'ab'}`,
alphabet `ab`, capacity two, and target two have a true maximum of one. The
old result reported an upper bound of zero after it pruned both branches.

The final implementation records the largest pruned bound. The regression
test `test_upper_bound_keeps_pruned_branch_certificates` covers this class.

The default branch order is now descending summed ciphertext weight, with a
lexical tie rule. An explicit order is validated and recorded. The objective
and domain fingerprint stays separate from the search-settings fingerprint.

## Verification

The focused threshold tests passed:

```text
PYTHONPATH=src:. python -m unittest experiments.identifiability.test_threshold -v
Ran 13 tests ... OK
```

At this review checkpoint, the identifiability directory contained 26 passing tests:

```text
PYTHONPATH=src:. python -m unittest discover -s experiments/identifiability -p 'test_*.py' -v
Ran 26 tests ... OK
```

Final source hashes:

```text
f4699b0a32ee383c414a8ffe155fc0a4fe1aac65ce2a2225fd9ff3a3225436c8  experiments/identifiability/threshold.py
de773c43a4dc85521697c1147bd5f683d3ee15db71baae876c8b1545aad77f79  experiments/identifiability/test_threshold.py
```

No unresolved correctness defect remains in this review scope. The review did
not change implementation files. The project wiki was not changed because
this bounded task owns only this review file; the root agent handles the wiki
update.
