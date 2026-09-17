# Celsus control study review

Review date: 2026-09-17.

This review uses synthetic fixtures only. It does not read Celsus source or
partition data and does not run the control solver.

Reviewed hashes:

- `experiments/medical/control_study.py`: `cb1e3a8eac052903f7f5b4c77668b1a339d362bbe4035134ccdd38d7f11371e6`
- `experiments/medical/test_control_study.py`: `030d5e07e0d0e0bbe0a2e4956a72a3b24deb08a30ab9125d20128904cdbc7884`
- `docs/plans/celsus-reference-control-v1.md`: `cccbf455dc8ec98b040beec13786f212d741219e58f68354601eccca18169dbe`

## Result

No remaining control-study finding is known from this review.

The wrapper reads and hashes the fixed partition and manifest before it parses
either input or calls the frozen runner. It checks the protocol, public-safe
scope, and private partition hashes. The partition manifest hash transitively
pins the adapter, source, and projection hashes. Metadata uses repository
relative paths and records the partition and manifest hashes.

The wrapper calls the unchanged `experiments/homophonic/run_controls.py` with
`cap2`, seed `7000`, node budget `1000`, bitset bounds, and no warm start. The
frozen runner writes the key record before it first reads or encrypts the test
stream. Its current SHA-256 is
`65f81693336a3c705281ed711b45881a19a0adc34b715a29188dc1361d86be63`.

The no-argument CLI calls `run_celsus_control()`. Success prints only family
and solver status. Fixed failures print a safe kind; unexpected failures print
only the exception type. The outer wrapper owns parent-path preflight and
public output filtering. The study core keeps the detailed runner report and
key record in the fixed private output paths.

## Verification

The focused synthetic suite passed with warnings treated as errors:

```text
PYTHONWARNINGS=error PYTHONPATH=src:. python -m unittest \
  experiments.medical.test_control_study -v
Ran 7 tests ... OK
```

Python bytecode compilation passed for the study and its tests. No source
partition, Celsus model fit, or solver run was performed.
