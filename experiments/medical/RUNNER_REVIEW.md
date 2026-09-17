# Celsus projection runner review

Review date: 2026-09-17.

This review covers `run_projection.py`, its synthetic tests, the fixed
protocol, the freeze manifest, and the medical README. It uses synthetic XML
only. No pinned Celsus source was fetched or projected.

The reviewed hashes are:

- protocol `docs/plans/celsus-projection-v1.md`: `3f9dcb864c9302d220d0fe1cafbc869ef9422724221fe38860f9481e3ff28efa`;
- projector `experiments/medical/tei_projection.py`: `d736f77a172854de0ada730d1775d36ae02691e5e0ee547931e8208120dfbadc`;
- runner `experiments/medical/run_projection.py`: `810f9083c1f38ddae272e38e68b494295527c0bed95dd7be2e6f93dfb18f6581`;
- projector tests `experiments/medical/test_tei_projection.py`: `c190fe6a748a4df77a2d1e55faf21f0232c0fb64a68ee41d2d752cdcb2f937ed`;
- runner tests `experiments/medical/test_run_projection.py`: `09e54635b7c2fe618e874661548b426b9b2698f1e7c5f98d1fb35e7dfcb3a4ff`;
- freeze manifest `experiments/medical/freeze-v1.json`: `5c48648f0098f1d303ddfc5309aa42d58899cd44b2b118a7cc55811f266f5631`.

## Result

No blocking defect remains in the runner contract.

The independent traversal uses its own standard-library visitor and state. It
does not import projector visitor functions or projector state. It compares
records and aggregate fields with the reviewed projector. It reports the first
record location and keeps differing record data in ignored private output.
Counter mismatches report a safe counter key and keep both values private.

The runner verifies the source URL, commit, byte count, SHA-256, audit receipt,
and exact eight-book structural targets before a pinned run. The freeze loader
requires the exact five-file path set and verifies every hash. `run_validation`
rechecks the manifest itself; it has no caller-supplied freeze object. A
missing or changed manifest stops before source verification and projection.

Both traversals use `empty_policy="include"`. The runner compares total,
per-book, and per-chapter counts, source and selected counters, exclusion
paths, boundary status, and canonical records. JSON Lines output uses UTF-8,
sorted keys, compact separators, source order, and a final newline. Full
paragraph text stays in ignored private files. The public receipt contains
aggregate metadata and hashes only. Exclusive writes refuse changed existing
files.

Manual locations and feature checks remain `PENDING`. A successful automated
run therefore returns `PENDING_MANUAL_REVIEW`; it cannot claim final
acceptance. The failure receipt records the source pins and freeze metadata
without source text.

The final synthetic regression suite passed 35 tests:

```text
PYTHONPATH=src:. python -m unittest experiments.medical.test_tei_projection experiments.medical.test_run_projection -v
```

## Optional diagnostics

`_assert_source_targets` fails closed but reports only the aggregate failure
kind. A future diagnostic can include the failed target names and observed
values. This does not permit a false pass.

The runner supports `require_source_shape=False` for labelled synthetic tests.
The receipt marks this scope as `synthetic_unchecked`, and the command-line
path always uses the pinned shape. This test hook does not establish a source
result.

## Limits

No pinned-source projection has run. Synthetic agreement cannot prove that the
source meets the audited counts, that the extraction is historically complete,
or that the procedure identifies or deciphers the Voynich Manuscript.
