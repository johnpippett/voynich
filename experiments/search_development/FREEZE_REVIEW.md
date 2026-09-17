# Freeze wrapper review

Review date: 2026-09-17.

This review covers the fixed freeze wrapper and its synthetic tests. It uses
fixture manifests only. It does not run the Italian study or any root bound or
local search.

Reviewed hashes:

- `experiments/search_development/freeze-v1.json`: `eb880ec0efaa31b500cd540e886b82090963b624f97f609ad3e8f010ea0afed7`
- `experiments/search_development/run_frozen.py`: `c938a056896d128f5bac403a8bb49ad4dfb4329ae916a7c2e514399d7861d2fd`
- `experiments/search_development/test_run_frozen.py`: `34d4e77b6d4035511622dff1a71e4d03cb25c21c9ce986aee87a34c34c10c07a`
- `docs/plans/homophonic-search-development-v1.md`: `d44a1a2208d4b90a5d8e1ce13ff9d090ba88b24fa35184328c76dc84caf91821`

## Result

The wrapper has no blocking defect in this review.

The real draft manifest passed `verify_freeze_manifest`. It contains the exact
29 paths in `FREEZE_FILES`, with one valid SHA-256 value for each path. It does
not hash itself. It rejects missing files, symlinks, duplicate paths, unsafe
paths, invalid digests, and changed file content.

The wrapper validates the fixed command, all expected parameter values, and all
expected resource values before it starts the supervisor. The effective
supervisor limits must match the freeze values for stage time, total time, RSS,
poll interval, termination grace, address-space limit, and worker count.

The wrapper imports the supervisor only after freeze and output checks. An
independent tampered-fixture check rejected the source before it imported the
supervisor or the study runner.

The output preflight covers six paths: four child reports, one public receipt,
and one private receipt. It rejects an existing file, directory, or symlink at
each path or any parent component. It does not overwrite an earlier attempt.

The safe status set includes `development_only`, `resource_abstain`,
`input_mismatch`, `implementation_failure`, and `output_exists`. The wrapper
preserves these statuses and filters supervisor fields to an aggregate allow-list.
It sets `numeric_outputs_valid` to true only when the status is
`development_only` and all four child reports exist as regular files. Failure
statuses set `numeric_outputs_valid` to false in post-supervision receipts.

The public receipt contains source and output hashes, status, counts, and scope
metadata. It excludes child scores, bounds, raw words, ciphertext, and local
paths. A resource failure can leave partial child files, but it cannot publish
them as valid numeric output.

## Verification

The focused synthetic suite passed with warnings treated as errors:

```text
PYTHONWARNINGS=error PYTHONPATH=src:. python -m unittest \
  experiments.search_development.test_run_frozen -v
Ran 9 tests ... OK
```

The focused tests cover exact manifest paths and hashes, source tamper, missing
files, manifest parameter tamper, effective limit mismatch, all safe status
classes, partial child output, symlink preflight, receipt privacy, and exit
status mapping. Independent checks also verified all 29 file hashes, all six
output preflight paths, all 19 fixed parameter and resource fields, and the
pre-import rejection path.

The manifest SHA-256 is `eb880ec0efaa31b500cd540e886b82090963b624f97f609ad3e8f010ea0afed7`.
The manifest is a selected reviewed file set. A clean published checkout must
bind this manifest and the remaining transitive source dependencies before a
study run.

No Italian result, VMS result, decipherment, or language conclusion follows
from this review.
