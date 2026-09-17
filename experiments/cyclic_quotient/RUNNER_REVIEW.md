# Cyclic quotient outer runner review

Review date: 2026-09-17.

This is a synthetic, read-only review. It did not read reference source
partitions, start a real child study, or run a model fit. It owns this file
only.

## Findings

### Blocker: output validation confuses absent and invalid files

`_read_json()` returns `None` for a missing file, a symlink, invalid JSON, and
a JSON value that is not an object. `validate_corpus_outputs()` then treats
all these cases as absence. A malformed `fit.json` beside an abstained
`quotient.json` therefore passes as a valid abstention. A proved fit and key
also pass when `diagnostics.json` is missing or malformed.

The same validator ignores extra files in the corpus directory. The plan says
that an unexpected output is a failure.

An independent temporary fixture produced these results:

```text
malformed fit under abstention: numeric_valid=True
proved key missing diagnostics: numeric_valid=True
proved malformed diagnostics: numeric_valid=True
extra file: numeric_valid=True
```

Use a tri-state file reader. Distinguish absent, valid, and invalid files.
Reject invalid present files, symlink files, and names outside the four fixed
output names. Apply one explicit output matrix:

- an abstained quotient has only its valid quotient record;
- a proved feasible fit has valid fit, key, and diagnostics records;
- a proved infeasible fit has a valid fit and no key or diagnostics;
- each record has the required protocol, status, links, and count fields.

### Blocker: bounds do not validate the feasible objective or full key record

`_validate_fit()` checks only that integer `lower_bound` and `upper_bound`
exist and that lower is not greater than upper. It does not require a solver
score, feasible flag, certification flag, or status consistency. A temporary
fit with `lower_bound=1`, `upper_bound=2`, and `score=99` passed validation.
An `fit_infeasible` record with a solver marked feasible also passed.

`_validate_key()` accepts only `class_key` as a required key field. It allows
missing `class_names`, `class_members`, `observed_unit_key`, `coverage`, and
`open_slot_count`. This does not prove the saved map covers the quotient
classes and observed units.

Require a non-negative integer score with
`lower_bound <= score <= upper_bound`, and require the solver status,
`feasible`, and `score_certified` fields to agree with those values. Require
the complete saved key schema. Recompute the induced observed-unit map from
the quotient classes and compare it with `observed_unit_key`; check class
capacity, coverage, open slots, quotient hash, and fit status. Keep the pure
core output contract in mind: the child records do not need direct corpus or
freeze fields because the outer receipt binds the freeze and every output
hash.

### Finding: execution completion is not fit certification

`_corpus_status()` returns `complete` when a child exits with code zero and
the current weak schema passes. `run_controls()` then publishes only
`status`, `numeric_outputs_valid`, and output hashes for each corpus. It does
not publish quotient status, fit status, `score_certified`, or the bounds.
Thus an abstained quotient and a budget-exhausted fit can look like a
completed certified search in the public receipt.

Keep execution status, numeric-output validity, quotient abstention, and fit
certification as separate public fields. Include safe fit status and bound
fields when a fit exists. Do not call a budget-exhausted fit certified.

`main()` also maps every `FreezeFailure` to `input_mismatch`. The default
synthetic test runner raises this exception when its tests fail. A disposable
call with `run_controls()` raising `FreezeFailure("synthetic tests failed")`
returned `status="input_mismatch"`. Use a separate failure type or preserve
the failure kind so a synthetic test failure is `implementation_failure`.

### Finding: normal child failure can leave a process-group descendant

`monitor_process()` kills the process group after a wall or RSS stop. If the
leader exits first, the normal path only waits for the leader. An independent
child that spawned a one-second descendant and exited with code `3` left that
descendant alive after `monitor_process()` returned. The frozen child does not
spawn subprocesses, but this does not satisfy a general process-group cleanup
contract.

After the leader exits, close the owned group or document and test the fixed
no-descendant assumption. Keep the SIGTERM, five-second grace, and SIGKILL
path for resource stops.

## Verified controls

The wrapper source imports only standard-library modules before the freeze
check. The package `__init__.py` contains a docstring and no project import.
The local import closure of `control_study.py` includes the quotient, pairing,
solver, lexicon, loader, and control modules, and all these paths are in the
53-file `FREEZE_FILES` list. The list also includes the frozen reference
manifest, six known pairing records, two feasibility records, and all six
reference partition files. The current checkout has all 53 files, but it does
not yet contain `experiments/cyclic_quotient/freeze-v1.json`; therefore the
real manifest hash and a real freeze verification remain pending.

The focused synthetic tests passed 14/14 after the child metadata change:

```text
PYTHONPATH=src:. python -m unittest \
  experiments.cyclic_quotient.test_run_frozen \
  experiments.cyclic_quotient.test_control_study -v
```

The wrapper's source-free test command passed 43 tests. The quotient, study,
pairing, and forced-edge suites passed 51 tests. The disposable no-argument
CLI fixture completed with exit code zero and wrote its safe receipt. Separate
monitor probes gave correct normal, wall-time, and RSS-unsupported results.
No real reference or manuscript data was used in these checks.

## Reviewed hashes

- `experiments/cyclic_quotient/run_frozen.py`: `0dfff592d77fe0d810124d5fc39d390ca9f888b6e3843d0d1744a11a27a542d2`
- `experiments/cyclic_quotient/test_run_frozen.py`: `886251c815a3cc3505a4bf961a3c5ef9aef73a718a19c2302850634e5ab784b9`
- `experiments/cyclic_quotient/control_study.py`: `231f0488eb97d809d898dc6ece3e0bd8bdc166849b5531d42b1885f98ad61bc5`
- `experiments/cyclic_quotient/test_control_study.py`: `df3e22ccc2a18d5fcd96b09820aed9fd1112d3a8a74c1520fbf0836cbbe6a9ee`
- `experiments/cyclic_quotient/study.py`: `69ee883e0d1ca92f95cb96664c018e925836244fde83cfbfd0ce43b4ed79db1d`
- `experiments/cyclic_quotient/quotient.py`: `8186751798ae74884d0071735612844ab65819e90d9e9a4aadff7b85721f249e`
- `docs/plans/cyclic-quotient-run-v1.md`: `20329ef2d1f8a765e8cde9d76ed37cb08627f59850c39a4197f30d4775bbc9a4`

The wrapper is not ready for a public run until the output-validation and
receipt-status findings are fixed, the process-group decision is explicit,
and the final 53-file freeze manifest is present and verified.
