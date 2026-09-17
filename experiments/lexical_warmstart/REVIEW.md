# Lexical warm-start review

Date: 2026-09-17.

This review covers the source, tests, and step 1 of the homophonic search
design:

- [`warmstart.py`](warmstart.py), SHA-256
  `85c261e0c88e335321d0ae76b86878bc3798518c3e715295aef9d678305d36b0`
- [`test_warmstart.py`](test_warmstart.py), SHA-256
  `cb82fa1ac6ab619410c813260092c4f86a20702637a15b51c8f9fb7395cada33`
- [`homophonic-search-next.md`](../../docs/research/homophonic-search-next.md),
  step 1

## Result

The review found no correctness defect in the tested synthetic local search.
The method implements the local-search part of step 1. It uses one-unit
reassignments and two-unit swaps. It does not implement the proposed beam or
restart stages.

The method starts with a complete map. It checks the map against the plaintext
alphabet and the capacity. It checks the total capacity before the search.
Every reassign move preserves capacity. Every swap preserves the value counts.
The returned map is complete and capacity-valid in all tested cases.

The score is the sum of the supplied word-type weights for decoded words in the
supplied lexicon. The method checks each selected move against the complete
score. It sets `score_certified` to `False`. It does not claim a global optimum.

## Checks

- The incident-word calculation includes each word type once, even when a unit
  repeats in that word. A swap uses the union of both incident-word sets.
- The tests and an independent brute-force script recomputed every candidate
  score and every delta from the complete map.
- The search selects the highest positive score. It uses the smallest complete
  key in sorted cipher-symbol order for equal scores.
- The search accepts at most `move_budget` improving moves. A zero budget does
  not inspect a neighborhood. A positive budget stops after a non-improving
  neighborhood or after the accepted-move limit.
- Empty counts return an empty map and score zero. Zero-weight word types do
  not create a false improvement. Empty word types also pass the score check.

`trace_mode="summary"` keeps the final result and accepted moves unchanged. It
returns no per-neighbor records. It keeps candidate counts and score metadata
for each checked iteration. It keeps no hidden candidate-map list.

The summary keeps at most `move_budget` accepted maps. Its iteration metadata
has at most `move_budget + 1` entries. The extra entry can record a terminal
non-improving neighborhood.

The repository test command ran nine tests:

```text
python -m unittest experiments.lexical_warmstart.test_warmstart -v
```

An independent check enumerated 3,000 small map domains. It checked legal
reassignments, swaps, capacity, score deltas, tie selection, and budget halts.
A second check covered 7,500 synthetic input, capacity, and budget combinations.
It compared full and summary results and found no hidden neighbor maps.
Some cases ended at a local score below the finite global maximum. This result
confirms the stated local-search limit.

## Trace limit

Full mode stores `key_before` and `candidate_key` as complete maps for each
evaluation. Full-trace memory therefore grows with evaluations and symbols.
Summary mode removes this per-neighbor storage. It keeps selected move maps and
small iteration records. This is the intended bounded trace for later reference
integration.

I applied ASD-STE100 Issue 9 rules 3.6, 6.1, and 6.3. I also checked the
dictionary entries for `CHECK`, `COMPARE`, `RECORD`, `RESULT`, `LOCAL`, and
`CAPACITY`.

No real corpus was used. I changed only this review file. The source, tests,
and design document remain unchanged.
