# Search development integration review

Review date: 2026-09-17.

This review covers the synthetic development runner, its supervisor, and the
freeze wrapper. It uses synthetic inputs and child fixtures only. It does not
load the fixed Italian input or run the root bound or local fit.

Reviewed source hashes:

- `experiments/search_development/run_study.py`: `71f75841d3873746a0ba05124ce27350617d3743d21d480b66385ca41811ab7a`
- `experiments/search_development/test_run_study.py`: `7016049fc6bdfae9e140708266e0e5bf42c4f99e07fc4fb307007089cdcf07cd`
- `experiments/search_development/supervise.py`: `86750f93a39f7ef4916b29ced7ee088bb047a86cd9015b798fce17d3e8044926`
- `experiments/search_development/test_supervise.py`: `4aadfeb35005f7167fcbcf822ebdfa5fb800b97d4631545cd696a13a6190a447`
- `experiments/search_development/run_frozen.py`: `c938a056896d128f5bac403a8bb49ad4dfb4329ae916a7c2e514399d7861d2fd`
- `experiments/search_development/test_run_frozen.py`: `34d4e77b6d4035511622dff1a71e4d03cb25c21c9ce986aee87a34c34c10c07a`

## Result

The earlier error mapping defect is resolved. The supervisor now accepts only
these child error kinds: `resource_abstain`, `input_mismatch`,
`implementation_failure`, and `output_exists`.

The supervisor maps child errors as follows:

- `resource_abstain` -> `resource_abstain` with reason `child_resource_abstain`.
- `input_mismatch` -> `input_mismatch` with reason `child_input_mismatch`.
- `implementation_failure` -> `implementation_failure` with reason
  `child_implementation_failure`.
- `output_exists` -> `implementation_failure` with reason
  `child_output_exists`.

The supervisor checks the child error before it checks a non-zero exit code.
This preserves a child resource request and separates it from a supervisor
wall-time, RSS, or interrupt stop.

Unknown or malformed error records fail closed. Duplicate error records and
every stdout record after the terminal record also fail closed. The public
result contains aggregate counters only. It does not contain error messages,
error kinds from rejected records, scores, bounds, or child paths.

The freeze wrapper accepts the four safe status values that the supervisor can
return. It preserves `input_mismatch` and `output_exists` status values in its
safe receipt. It publishes numeric outputs only for a completed
`development_only` child with all required child files.

No blocking integration defect remains in the reviewed files.

## Verified behavior

The child emits five supervisor records in this order:

1. `root_bound/running`
2. `root_bound/complete`
3. `local_search/running`
4. `local_search/complete`
5. `complete/development_only`

The supervisor accepts this sequence and uses the fixed no-argument child
command, one CPU worker, a 1,200 second stage limit, a 1,500 second total
limit, and a 7 GiB sampled RSS guard. It uses a monotonic wall clock and
sampled `/proc` RSS. It kills and reaps the owned process group on a limit.

The runner validates the weighted objective, input counts, capacity, training
lexicon, validation stream hash, source hashes, map hashes, and report hashes.
It writes the manifest first, each complete key record after exact rescoring,
and the aggregate last. A resource stop does not publish an aggregate.

The wrapper verifies the exact source freeze and fixed parameters before it
imports the supervisor or starts the child. It rejects existing output files
and symlinks. It writes safe public and private receipts after supervision.

## Verification

The following synthetic suites passed with warnings treated as errors:

```text
PYTHONWARNINGS=error PYTHONPATH=src:. python -m unittest \
  experiments.search_development.test_run_study \
  experiments.search_development.test_supervise \
  experiments.search_development.test_run_frozen -v
Ran 43 tests ... OK
```

The tests cover each allowed child error kind, unknown and missing kinds,
duplicate errors, out-of-order progress, progress and error records after the
terminal record, resource limits, RSS sampling, process-group cleanup,
output privacy, output preflight, freeze checks, and safe status receipts.

No Italian result, VMS result, decipherment, or language conclusion follows
from this review.
