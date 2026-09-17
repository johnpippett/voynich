# Celsus partition wrapper review

Review date: 2026-09-17.

This review uses temporary synthetic fixtures only. It does not parse the
Celsus XML, read source projection output, or create a Celsus result.

Reviewed hashes:

- `experiments/medical/run_partition.py`: `3ca15135530e266eb7c973e161532a36d72c8b04f1215c035827e78c37ef39eb`
- `experiments/medical/test_run_partition.py`: `fb4215524296e3a2df506157b41206d3ebe5d267347a142b99bee25de5cdc75f`
- `docs/plans/celsus-reference-control-v1.md`: `cccbf455dc8ec98b040beec13786f212d741219e58f68354601eccca18169dbe`

## Result

The previous review found that `_prepare_output_dir()` accepted `..` path
components. The wrapper now rejects parent traversal before it creates a
directory, and a regression test confirms that it creates no path component.
This finding is resolved.

The plan now states that removed-node counts come from the accepted projection
receipt and that this stage does not measure affected paragraph count. It also
states that the fixed control encrypts and scores test words only after it
saves the fitted key. These earlier plan ambiguities are resolved.

No remaining partition-wrapper finding is known from this review.

## Verified behavior

The wrapper correctly:

- checks the exact allowlist and each byte hash before module parsing or
  adapter import;
- rejects a changed fixed acceptance receipt before acceptance parsing;
- requires the accepted receipt identities and fixed source and projection
  hashes;
- reads the module JSONL from the verified byte cache once and calls the
  adapter once;
- keeps source bytes unchanged during preflight;
- rejects existing outputs, output files, symlink components, and parent
  traversal;
- writes a deterministic public manifest without paragraph text or token
  arrays.

The public manifest carries acceptance, source, projection, adapter, and
private-output hashes. The plan records projection exclusion counts through the
accepted upstream receipt and does not claim an affected-paragraph count.

## Verification

The adapter and wrapper suites passed with warnings treated as errors:

```text
PYTHONWARNINGS=error PYTHONPATH=src:. python -m unittest \
  experiments.medical.test_reference_adapter \
  experiments.medical.test_run_partition -v
Ran 19 tests ... OK
```

Python bytecode compilation passed for both modules and their tests.

No source mutation, source parsing, adapter run on Celsus records, or output
publication was performed.
