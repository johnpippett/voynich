# Identifiability runner review

Date: 2026-09-17.

Scope: `run_assessment.py` and `test_runner.py`. This review used synthetic
fixtures only. It did not build Latin data or read VMS input for a run.

Reviewed source hashes:

- `experiments/identifiability/run_assessment.py`: `84351d57aff0676a07da97618ff9736c4a50071a3a9b69934cd71e0fa0c0a762`
- `experiments/identifiability/test_runner.py`: `6e5595579821f08bd58dcff080ca9838898382a930186eb1ed82c9a5fe376ae6`
- `experiments/identifiability/assess.py`: `e043aa38e7e40800f5e03af4a35e5931965eecd374f38e8bcf7a799caeb868c0`
- `experiments/identifiability/threshold.py`: `f4699b0a32ee383c414a8ffe155fc0a4fe1aac65ce2a2225fd9ff3a3225436c8`

## Result

No open blocking defect remains in the current runner.

The command pins the published cold report with `BASELINE_SHA256`. It then
checks the report-linked key, source, and original protocol hashes before use.
The CLI records the current identifiability protocol and current source hashes
in the run provenance. The certificate record states that the runner checks
scope and hashes, but does not prove the global optimum. This limitation is
clear and correct.

`prepare_problem()` rebuilds the train and validation streams, the training
lexicon, the fit hash, token and type counts, unit count, objective denominator,
selected-map score, capacity, and problem fingerprint. It does not iterate the
test stream. The query API receives the finite problem, selected incumbent,
target, and certificate. It receives no planted key or test words.

The runner writes `run.json`, one file for each fitted unit, and
`decisions.json` before it reads the test iterator or uses planted assignments for diagnostics.
Existing output directories are rejected. New files use exclusive creation.
An omitted query or a test hash failure leaves the partial run and does not
write `assessment.json`.

## Resolved finding

The first review found that the `unobserved` diagnostic always reported zero
units. The code now derives this set from test units that are absent from the
fitted key. It counts each such unit once and counts every occurrence in
`test_positions`. The regression test uses a test-only unit and checks the
unit and position counts. Unknown positions remain unassigned. Their
`test_errors` value is the number of positions without a decoded letter; it
must not be read as an error rate for a fitted assignment.

## Verification

The following synthetic checks passed:

```text
PYTHONPATH=. python -m unittest experiments.identifiability.test_runner -v
7 tests passed

PYTHONPATH=. python -m unittest experiments.identifiability.test_assess experiments.identifiability.test_threshold -q
21 tests passed

PYTHONPATH=. python -m unittest discover -s experiments/identifiability -p 'test_*.py' -q
33 tests passed

python -m py_compile experiments/identifiability/run_assessment.py experiments/identifiability/test_runner.py
```

The tests cover fit-only preparation, changed fit inputs, exact baseline source
checks, the decision-before-test boundary, missing queries, changed test
streams, no-overwrite behavior, and unobserved test units. The study remains a
finite synthetic control assessment. Its certificate check is computational
and depends on the published external certificate; it is not a formal proof.
