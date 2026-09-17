# Equal-score enumerator review

Date: 2026-09-17.

Scope: `enumerate.py` and `test_enumerate.py`. This review used synthetic
finite domains only. It did not read reference data or run a corpus build.

Reviewed source hashes:

- `experiments/optimal_set/enumerate.py`: `443b53105412e28b1b00172c38776e6a9d43ef94c45a774533e2a2e0e443e5d8`
- `experiments/optimal_set/test_enumerate.py`: `d395c9fe1a6d2641e8540e118afe2d3c034dbfb085b81079f623383e588bcdd9`

## Result

No correctness defect was found.

The enumerator normalizes counts, lexicon, alphabet, capacity, and fixed
assignments with the same domain rules as `ThresholdProblem`. Its
`objective_domain_fingerprint` matches `ThresholdProblem.problem_fingerprint`
and does not include `fixed_key`. Its `domain_fingerprint` includes fixed
assignments. The result records both domains.

The iterative depth-first search visits the root and each entered child state.
It checks capacity before entering a child. A complete run checks every
feasible complete map with its exact weighted lexicon score and retains all
maps whose score equals the target. A capacity impossibility is complete
without search because no map exists.

`certificate_conflict` stops at the first complete map above the target. It
does not claim complete enumeration. The maps collected before that conflict
can be partial. `product_limit` and `node_budget` return `complete: false`.
Only `complete: true` permits the collected map set to be used as exhaustive.
The module does not claim a global optimum outside its supplied domain.

## Independent checks

I compared the output with an independent product enumeration over 250 random
small domains, five target values, capacities `1`, `2`, and `None`, and random
valid partial fixed maps. This checked 3,750 target cases. The checks included
empty words, zero weights, rejected lexicon symbols, repeated cipher units,
tuple words, target values below, equal to, and above the attainable scores,
and capacity-infeasible domains.

I also checked node budgets from zero through a complete budget and product
limits on a small domain. Every complete result matched the independent map
set and feasible-leaf count. Every partial result reported a resource stop.
Every conflict returned a valid complete map with score above the target. A
tuple-unit case matched the independent `ThresholdProblem` fingerprint.

The iterative search handled 1,100 cipher units with one alphabet symbol.
It visited 1,101 states and returned one complete map without recursion.

Focused tests passed:

```text
PYTHONPATH=. python -m unittest experiments.optimal_set.test_enumerate -v
12 tests passed
```

The test suite covers all supported capacities, random complete enumeration,
fixed domains, fingerprint scope, empty and fully fixed inputs, capacity
pruning, product limits, zero and shallow node budgets, target conflicts,
targets with no matching score, deep iterative search, and invalid inputs.

No wiki file was changed. The parent task owns the wiki update, and this review
is limited to the assigned review file.
