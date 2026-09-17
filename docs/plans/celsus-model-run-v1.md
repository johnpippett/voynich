# Celsus model control run v1

Status: fixed operational run plan. This plan does not change the statistical
settings in `celsus-reference-control-v1`.

## Purpose

Run one known-cipher Celsus control after the partition freeze passes. The run
tests the fixed lexical solver and its resource boundary. It does not score the
Voynich Manuscript and it does not select a model.

## Fixed command and child

Run this command from the repository root:

```sh
python -m experiments.medical.run_control
```

The command takes no options. The wrapper uses the repository root and the
fixed output paths below.

The wrapper verifies `experiments/medical/control-freeze-v1.json`. It then
starts one child with this command:

```sh
python -m experiments.medical.control_study
```

The wrapper does not import the child module before freeze verification. It does
not retry a child, use a network, or apply an address-space limit.

## Fixed settings

The child uses the settings in the frozen reference plan:

* family: `cap2`;
* seed: `7000`;
* capacity: `2`;
* units: `c00` through `c51`;
* solver: exact integer lexical objective with the bitset bound;
* node budget: `1000`;
* warm start: `none`.

The child writes `cold.keys.json` before it reads the test partition for test
diagnostics. The wrapper validates the key-file hash in `cold.json`.

## Fixed outputs

The run uses this output directory:

`results/celsus-reference-control-v1/model/`

The child writes:

* `cold.json`;
* `cold.keys.json`.

The wrapper writes:

* `supervision.json`;
* `resources.private.json`.

The wrapper refuses an existing output or a symlink in an output path. It writes
each receipt with exclusive creation. It writes no source arrays, token arrays,
paragraph text, or complete key to either wrapper receipt.

## Resource boundary

Use one child CPU process. Allow `1500` seconds of wall time. Sample Linux
resident memory every `0.25` seconds. Use a `7 GiB` resident-memory limit. Send
`SIGTERM` at a limit, wait `5` seconds, then send `SIGKILL` to the child
process group. A host without Linux resident-memory sampling receives
`resource_abstain` and does not start the child.

## Save and validation order

1. Verify the freeze manifest and every listed byte.
2. Verify Linux resident-memory support and preflight all output paths.
3. Start the one child process in a new process group.
4. Apply the fixed wall and resident-memory limits.
5. Check both child JSON records and the key-record hash.
6. Check the partition manifest and both private partition hashes.
7. Write aggregate supervision and private resource receipts.

The outer validator checks the fixed records, score bounds, planted objective
bound, key count, provenance hashes, and safe aggregate fields. The frozen
child already checks that its key covers every fitted symbol before it writes
the key record. The outer validator relies on that frozen check and does not
recompute source ciphertext.

The wrapper reports `completed` only when the child exits successfully and the
solver score is certified. It reports `incomplete_search` for a valid child
record without score certification. It reports `resource_abstain` after a
resource stop, `input_mismatch` after a frozen-input failure, and
`implementation_failure` after another child or validation failure.

The inherited exact-recovery gate remains unchanged. A recovery error does not
change the solver status. It remains a control result and does not authorize
Voynich scoring.

## Freeze scope

The external control freeze excludes itself. It includes this plan, the frozen
reference plan, the wrapper and child source and tests, the partition manifest
and its two private outputs, the partition freeze and its pinned files, the
homophonic runner and its imported solver dependencies, and the frozen
comparator records. A changed or missing byte stops the run before child
launch.

## Entry-point correction after attempt 1

Commit `dc71f118122becccc009f6c8859915e310bc47e2` contains the initial control freeze.
The first command stopped before child launch because an output-path constant was not yet defined.
Import-based tests did not expose the command-line execution order.

The correction binds the constant before the entry point.
A subprocess regression uses the actual wrapper command and a synthetic child.
It checks that child exit code 2 produces an input-mismatch status and both receipts.
The test reads no reference text and runs no model.

The initial manifest remains in `experiments/medical/control-freeze-v1-initial.json`.
Its SHA-256 is `5620f2fc15489d361dcd03d64b9144daa931f85b2abbb90929e33dab7997bf7a`.
The failed launch record remains in `reports/celsus-model-control-v1/attempt-1/launch.json`.
Publish the corrected freeze before another command attempt.
All statistical settings and source partitions remain unchanged.
