# Cyclic quotient run v1

Status: development design only. Date: 2026-09-17.
Research is paused. This unfinished design has no final input freeze and no authorized result run.
The commands below describe the intended interface. They are not instructions to resume research.

This plan defines the fixed outer runner for the cyclic quotient control.
It does not define the quotient fit itself.

## Fixed command

Run:

`python -m experiments.cyclic_quotient.run_frozen`

The command accepts no options. It runs these children in this order:

1. `python -m experiments.cyclic_quotient.control_study --corpus latin --output-dir results/cyclic-quotient-recovery-v1/latin`
2. `python -m experiments.cyclic_quotient.control_study --corpus italian --output-dir results/cyclic-quotient-recovery-v1/italian`

The runner starts the second child after the first child stops.
It does not retry a child.
It does not use the network.

## External freeze

The runner reads `experiments/cyclic_quotient/freeze-v1.json`.
The manifest excludes itself.

The runner checks the manifest schema, protocol, command, child command, parameters, limits, output paths, runtime record, and exact file allowlist.
It hashes every listed regular file before synthetic tests, source loading, or child launch.
It rejects missing files, changed bytes, duplicate entries, path traversal, absolute paths, and symlinks.

The freeze covers the plan, the quotient and pairing code, tests, loader, solver dependencies, reference manifest, known pairing results, and reference source files.
The final manifest records the Python implementation and platform used to create it.
The runner does not require an exact runtime match before execution.

Root creates and reviews the final manifest before a result run.
A changed frozen byte requires a new manifest and a new protocol version.

## Fixed settings

| Setting | Value |
| --- | --- |
| Corpora | `latin`, `italian` |
| Reference family | `cap2` |
| Seed | `7000` |
| Declared units | 52 |
| Fit capacity | 1 per quotient class |
| Quotient bound engine | `bitset` |
| Quotient node budget | 100000 per corpus |
| Solver node budget | 100000 per corpus |
| Initial key | Empty |
| Test score order | No test score during fitting |
| Child CPU workers | 1 |
| Retry count | 0 |

The child controls use the validation ciphertext and the train lexicon.
They must save `quotient.json` before any fit output.
A proved quotient can write `fit.keys.json`, `fit.json`, and `diagnostics.json`.
An abstained quotient can stop after `quotient.json`.

## Outputs

Each corpus directory may contain these fixed files:

- `quotient.json`
- `fit.keys.json`
- `fit.json`
- `diagnostics.json`

The runner refuses an existing output file, output directory symlink, or symlinked output parent before it starts.
The child uses exclusive output creation.

The runner checks protocol, corpus, freeze binding, unit inventory, class coverage, class capacity, quotient status, fit bounds, key maps, and diagnostic links.
The runner does not require result values that the protocol does not fix.

The runner accepts a numeric result when the child exits with code 0 and the output schema is valid.
For an abstained quotient, missing fit, key, and diagnostic files are valid.
For a proved quotient, fit is required; the key is required unless the fit records infeasibility.
A missing quotient, an invalid record, or an unexpected output is a failure.

## Resource limits

Run only on Linux because the RSS monitor reads `/proc/<pid>/status`.
Use one child process at a time.

| Limit | Value |
| --- | --- |
| Wall time per corpus | 300 seconds |
| RSS sample interval | 0.25 seconds |
| RSS limit | 7 GiB |
| Termination grace | 5 seconds |
| Address-space limit | None |

Start each child in a new process group.
Discard child standard output and standard error.
Send `SIGTERM` at a wall or RSS limit.
Send `SIGKILL` after the grace period.
Record resource-stop status in the safe public supervision receipt.

## Receipts and limits

Write `reports/cyclic-quotient-recovery-v1/supervision.json` with the freeze hash, fixed settings, synthetic-test count, per-corpus status, output hashes, and safe supervision fields.
Write private resource details separately.

The public receipt does not contain raw words, keys, plaintext, source paths, process identifiers, durations, or RSS samples.
A complete receipt means that both children exited with code 0 and passed output validation.
An abstained quotient is a valid numeric control result when its abstention record is complete.

This control tests a finite reference-corpus procedure.
It does not identify a language, prove a plaintext, or support a Voynich manuscript claim.

## Checks before a result run

Run the wrapper tests with:

`python -m unittest experiments.cyclic_quotient.test_run_frozen -v`

Run the core tests with:

`python -m unittest experiments.cyclic_quotient.test_quotient experiments.cyclic_quotient.test_study experiments.cyclic_quotient.test_control_study -v`

Do not run the real corpora until the final freeze contains the wrapper, child interface, tests, and all pinned inputs.
