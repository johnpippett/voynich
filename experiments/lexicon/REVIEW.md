# Lexicon solver review

Review date: 2026-09-16

This record describes the initial review and later corrections.
The current focused test file has 14 tests, including reference and bitset engine comparisons.

Scope: read-only review of `solver.py` and `test_solver.py`.
The review covers the integer branch-and-bound objective, input validation,
budget stops, and small adversarial cases.
It does not support a manuscript result or a decipherment claim.
This is an internal AI-agent review.
It is not external scholarly validation or formal program verification.

## Evidence

The initial review recorded 9 focused tests and this result:

```text
PYTHONPATH=. python -m unittest discover -s experiments/lexicon -p 'test_solver.py' -v
Ran 9 tests ... OK
```

The current focused test file contains 14 tests.

I also compared the solver with direct permutation search. The checks used
these inputs:

- Random alphabets of sizes 1 through 4.
- Random word weights, including zero.
- Random lexicons.
- Custom symbol orders.
- Valid partial `initial_key` values.
- Every node budget from zero through certification.

The checks also included these cases:

- Duplicate normalized ciphertext words and duplicate lexicon entries.
- Multi-symbol tuple units and absent plaintext letters.
- Invalid weights and keys.
- Tie cases.

After the warm-start fix, no bound counterexample occurred. For every budget,
the unrestricted direct optimum was within `lower_bound` and `upper_bound`,
including runs with partial and complete `initial_key` values.
When the solver reported certification, its score, bounds, and selected key
matched the direct optimum and the specified tie order.

## Checks that passed

- `_upper_bound` adds a type weight only when at least one pattern candidate
  is compatible with the partial injective key. Since weights are
  non-negative and each type can contribute at most once, this is an
  admissible integer upper bound.
- The solver keeps the maximum bound over every unsearched frontier node at a
  budget stop. It generates all children of an expanded node before the next
  budget check. It retains or prunes each child after its bound calculation.
- `_complete_key` supplies a feasible injective warm-start incumbent before
  search and at each expanded partial node. The search root is empty, so the
  incumbent does not restrict the feasible key space. Letters that occur in
  no candidate word remain valid completion values and do not change bound
  soundness.
- Ciphertext counts aggregate duplicate normalized words. Duplicate lexicon
  entries collapse to one set member, so they do not inflate candidate counts
  or scores.
- Invalid negative, boolean, and non-integer weights; duplicate alphabet
  symbols; invalid initial keys; duplicate or incomplete symbol orders; and
  invalid budgets are rejected.
- Empty input and a lexicon with no candidates return certified zero scores.
  An infeasible alphabet returns no score and no numeric bounds.
- Search order and tie comparison are deterministic. The selected key uses
  the lexicographically smallest values in sorted ciphertext-symbol order
  after the maximum score.

## Findings and API semantics

### Resolved finding: `initial_key` changed the feasible search space

The earlier implementation used `initial_key` as a fixed partial assignment.
The frontier started at that assignment.
It computed `root_upper` from that assignment and excluded its symbols from
`remaining_order`.
This was mathematically sound only for a hard-constraint API.

The intended API uses `initial_key` as a warm-start incumbent. The smallest
counterexample to the earlier implementation was:

```python
solve_lexicon(
    {"xy": 1}, {"ba"}, "ab",
    initial_key={"x": "a"}, node_budget=0,
)
```

The earlier result was `status="bound_certified"`, with bounds and score
equal to `0`. The unrestricted optimum is `1` with `x -> b, y -> a`. The
partial assignment rejected the only matching candidate before the bound was
computed.

The working tree now fixes the search root to an empty key.
It keeps the completed `initial_key` only as the feasible lower-bound key.
It computes the root bound and all branches from the empty key for every
ciphertext symbol.
The new regression test passes. The example now reports an uncertified upper
bound of `1` at zero budget and reaches score `1` with exhaustive search.

The initial `exhaustive` field combined score certification and traversal status.
The current API reports `score_certified` and `search_exhausted` separately.
`search_exhausted` includes valid bound pruning.
It does not mean that the solver visited every feasible key.
A regression test covers this distinction.

The initial `lexicon_input_count` field counted unique normalized entries.
The current API reports raw, unique normalized, and usable entry counts separately.
It also reports entries rejected for alphabet coverage.

No unresolved algorithmic defect appeared in the reviewed checks.
