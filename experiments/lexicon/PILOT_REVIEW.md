# Lexicon pilot review

Review date: 2026-09-16.

This review covers `experiments/lexicon/run_pilot.py` and
`experiments/lexicon/test_pilot.py`. It also reads the solver, reference
loader, group map, and bitset bound that the runner calls. It does not read or
search the raw manuscript source.

## Result

The current runner implements the declared finite objective and fit sequence.
I found no additional correctness defect in this scope after the author fixes.

The runner now has these correct properties:

* `objective_weights()` uses `count*T+N` and `2*T*N`.
* `fit_ciphertext()` sends those weights to the solver.
* `score_proof()` compares the solver score with the score of the returned key.
* `solver_public_result()` records `search_exhausted`.
* Partial key coverage counts mapped character positions and unmapped positions.
* The reference source argument is ignored and is recorded as `null`.
* A manuscript seed is ignored and is recorded as `null`.
* The key record is written before validation or test scoring.

The focused and solver tests passed:

```text
PYTHONPATH=src:. python -m unittest discover -s experiments/lexicon -p 'test_*.py' -v
Ran 52 tests ... OK
```

## Input and grouping checks

`load_manuscript_partitions()` uses the selected source hash from the source
manifest. It also compares the source hash with the hardcoded v3 source hash.
It now hashes `data/bifolio_manifest.json` and compares the result with the
embedded grouping hash. This prevents a stale local grouping file from being
reported as the active manifest.

The report records the parser mode, filter order, filter counts, observed
eligible groups, and groups without eligible paragraph records. The group map
assigns one deterministic split to each `(Q,B)` representative. This keeps
the split decision separate from word content.

The report does not emit raw manuscript words. It emits aggregate counts,
source metadata, extraction statistics, document identifiers, hashes, and a
hash for the separate fitted-key file. That file contains the fitted key
by design. The reference metadata does not include extracted word lists.

## Fit objective and score proof

`fit_ciphertext()` computes the weights once from the raw fit counts. It uses
the same weights for symbol order and for the solver objective. The objective
summary recomputes the weighted hit sum from the frozen key and checks it
against `token_hits*T + type_hits*N`.

The focused integration test fits a small real solver case. It checks that the
solver score equals the derived objective score and that the weight total
equals the declared denominator. The solver tests also compare the reference
and bitset bounds against direct enumeration.

`score_proof()` does not call a second optimizer. It records the solver bounds
and the independent score calculation. It states that equal bounds certify an
optimum only when `score_certified` is true.

## Held-out isolation

The reference fit receives only the encrypted validation counts and the
training lexicon. The reference test words enter only the scorer after the
key record is frozen.

The manuscript fit receives only training-partition counts. Validation and
test words enter only the scorer after the key record is frozen. Group
assignment uses group identifiers, not word content.

I ran synthetic checks that changed held-out words while keeping fit words
fixed. In both run kinds, the solver result, fit objective, ambiguity result,
and key-record hash remained equal. The held-out score changed as expected.
Held-out words did not select or alter the fitted key in these checks.

Held-out parsing still occurs before fitting. A malformed held-out input can
abort the run before fitting. This is an input validation dependency, not
score leakage.

## Reference control and metadata

`run_reference()` selects the reference corpus from `language`. It does not
pretend that a manuscript source name selects reference data. The output
records reference normalization, source-file hashes and extraction counts,
document splits, duplicate exclusions, and the reference manifest hash.

The oracle key is used for encryption and post-search accuracy only. The
solver receives no oracle key. The output labels the oracle key hash as a
known-control value.

## Remaining review limits

The test file still has no full fixture test for `run_reference()` or
`run_manuscript()` with the real corpus loaders. The synthetic isolation
checks and helper tests cover the fit boundary, but a small pinned fixture
would give stronger protection for report assembly and hash checks.

The runner records local manifest hashes. The declared input version still
depends on the checked-in files and tracked Git revision. This is a workflow
provenance limit, not a defect in the current runner.

No additional correctness finding remains in this scoped review. The pilot
remains a finite lexicon experiment. Its scores do not establish a language,
a historical key, a translation, or a Voynich decipherment.
