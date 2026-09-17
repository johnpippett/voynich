# Cyclic control wrapper review

Review date: 2026-09-17.

This is a synthetic, read-only review. It does not run a reference corpus,
the control study, or a manuscript stream. No source code was edited.

This review records the initial snapshot and its 53 tests.
The later [pin-correction audit](STUDY_REVIEW.md#final-pin-correction-audit) records the corrected snapshot and 54 tests.

Reviewed initial hashes:

- `experiments/cyclic_pairing/run_controls.py`: `b45b8b5ce82a73236a691350dc7e633c2de6cd6e801d3791a5e65b6f5409772a`;
- `experiments/cyclic_pairing/test_run_controls.py`: `9b5a32fc6439cf4c223d328a49c193601d724ffcc1fe7de0517138b3bc88f2c8`;
- `experiments/cyclic_pairing/__init__.py`: `34b9b19317fdaea3e3b99f51d5c45db120c5eae6ac91068aaf7369d8df6ce00b`.

## Checks passed

The focused wrapper suite passed 20 tests:

```sh
PYTHONPATH=src:. python -m unittest experiments.cyclic_pairing.test_run_controls -v
```

The four cyclic test modules passed 53 tests:

```sh
PYTHONPATH=src:. python -m unittest \
  experiments.cyclic_pairing.test_pairing \
  experiments.cyclic_pairing.test_forced \
  experiments.cyclic_pairing.test_study \
  experiments.cyclic_pairing.test_run_controls
```

The package initializer is side-effect free. Importing
`experiments.cyclic_pairing.run_controls` loads no pairing, forced-edge, or
study module. The wrapper checks Linux, verifies the external freeze, and
preflights fixed outputs before it starts synthetic tests or a child study.

The freeze shape checks the fixed command, child command, parameters,
resources, runtime fields, output paths, and exact file allowlist. The output
preflight rejects existing files, regular parent components, final symlinks,
and symlinked parent components.

The monitor samples child RSS, applies wall and RSS limits, sends `SIGTERM`,
waits for the grace period, and then sends `SIGKILL` to the process group. A
synthetic descendant check confirms that a timed-out child does not leave its
descendant alive. The public receipt omits elapsed time, RSS values, exception
details, and private resource records.

The output validator rejects observed-scope results, missing records, wrong
stream hashes, incomplete positive diagnostics, wrong orientations, and bad
forced-edge status. It requires a full 52-unit witness with disjoint sorted
pairs. A status of `none` is not accepted for this known positive control.

## Resolution of earlier findings

The four findings from the earlier wrapper review are resolved in the current
source.

1. A `unique` result now requires exactly one matching witness, and that
   witness must equal the complete 26-pair control set. The diagnostics
   validator also requires the unique witness overlap to contain all 26 pairs.
   The focused suite includes a wrong-witness regression test.
2. The input record provenance maps now match the verified freeze and corpus:
   source-file hashes, code hashes, test hashes, frozen-file hashes, and the
   reference manifest hash. The focused suite includes a changed-provenance
   regression test.
3. `run_controls` and `launch_child` reject non-Linux systems before freeze
   work, synthetic tests, or child launch. The focused suite checks that the
   synthetic runner and child are not called on a non-Linux platform.
4. The command-line parser has no `--project-root` override. `main` parses
   the fixed command and always runs with the repository root. This preserves
   the command and path binding in the freeze.

The protocol states that Python and platform versions are descriptive
provenance. They are not exact version requirements. The current validator
therefore requires the runtime fields in the freeze record without comparing
them to a different live version.

No material blocker remains in this bounded synthetic wrapper review. The
review does not validate a real control result, source acquisition, or
manuscript inference. A complete receipt still requires both children to exit
with status zero and all three safe corpus records to pass validation.
