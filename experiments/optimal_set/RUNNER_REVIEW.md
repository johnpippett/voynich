# Optimal-set runner review

Review date: 2026-09-17.

This review covers `experiments/optimal_set/run_study.py`,
`experiments/optimal_set/test_runner.py`,
`docs/plans/optimal-set-secondary-v1.md`, and `METHOD_REVIEW.md`.
It uses small synthetic fixtures only. It does not run the reference
enumeration or ranking.

The focused runner tests pass:

```text
PYTHONPATH=src:. python -m unittest experiments.optimal_set.test_runner -v
Ran 16 tests in 0.007s
OK
```

Reviewed source hashes are:

```text
experiments/optimal_set/run_study.py   225ed29bf5ad72733fd7282bcb1f5794a137a1c1ecd9d455cd67b9e020233448
experiments/optimal_set/test_runner.py 70a46cac2df94389d88983bc7306124c04109bbb210e3bd65cbe7351f1f4a822
experiments/optimal_set/enumerate.py  443b53105412e28b1b00172c38776e6a9d43ef94c45a774533e2a2e0e443e5d8
experiments/optimal_set/secondary.py  367d4ed3bd88a7601183a5870d978c19a50b0a2c7ccdd28127185aae559cdc85
```

The reviewed protocol hash is
`17abf949562b5152c104b8fb8c6987079b22514d87bb93aa155236b2d8c6867c`.

I found no current blocking error in the final snapshot. The runner now
checks the following points:

- It verifies the fixed manifest, baseline, assignment records, 46 query
  hashes, source records, data streams, protocols, and reconstructed objective
  fingerprint before the run.
- It verifies the fixed secondary protocol SHA-256 value. It records the three
  optimal-set module hashes in source and code provenance. A freeze commit and
  replay receipt can bind these current implementation hashes.
- It uses strict proof checks for query records in `run_study()` and the
  reference loader. It rejects unknown or non-integer node budgets and rejects
  boolean frontier counts. It checks the raw query unit against the outer unit.
- It derives forced assignments from validated records. It leaves ambiguous and
  unresolved units outside the forced map. It checks the full alphabet, fixed
  assignments, free units, capacity, product limit, node limit, and domain
  fingerprints.
- It checks complete enumeration metadata, unique complete maps, exact target
  scores, and baseline-map inclusion. It stops before ranking for incomplete or
  conflicting enumeration.
- It checks model settings, exact rational ratios, the ratio definition, the
  canonical candidate and its `1/1` ratio, all exact maximizers, and the lexical
  display tie. It preserves a ranker-provided `candidate_count` and stores the
  runner count separately.
- It writes selection before test scoring. Input loading verifies test-source hashes earlier.
  Test diagnostics include total,
  observed, and unseen positions. The synthetic unseen-unit test counts the
  unseen position as an error.
- It rejects absolute, parent, and backslash provenance paths. It does not
  publish model count tables or test word arrays.

The standalone `validate_query_records()` helper keeps an opt-in
`require_exhausted_proof=False` mode for structural checks. The study runner
and reference loader pass `True`; callers must not use the permissive mode as a
proof of forced exclusions.

The result remains a finite-domain control. Complete enumeration covers only
the supplied alphabet, capacity, lexicon, weighted ciphertext, and validated
forced domain. Exact ratios and a selected display map do not prove a unique
key, a manuscript reading, or a decipherment. No reference run or ranking was
performed during this review.
