# Celsus control wrapper review

Review date: 2026-09-17.

This review covers the outer wrapper, its synthetic tests, and the model-run
plan. It does not parse source data, encrypt text, or run the model.

Reviewed files and hashes:

* `experiments/medical/run_control.py`  
  `568211501343e9096248cfb4483ca83120534d3a34cc1174a20a69a1172c36ae`
* `experiments/medical/test_run_control.py`  
  `e2bbb4a445d56179f297579f32be0001ce8b3cfd44aca968d4e0a3e0b37fd2d0`
* `experiments/medical/control_study.py`  
  `cb1e3a8eac052903f7f5b4c77668b1a339d362bbe4035134ccdd38d7f11371e6`
* `experiments/medical/test_control_study.py`  
  `030d5e07e0d0e0bbe0a2e4956a72a3b24deb08a30ab9125d20128904cdbc7884`
* `docs/plans/celsus-model-run-v1.md`  
  `fd83af0db1f717e56bc335f4b88c67ea2b603ab0e0d956da0d9cc826c4c4bd36`
* `docs/plans/celsus-reference-control-v1.md`  
  `cccbf455dc8ec98b040beec13786f212d741219e58f68354601eccca18169dbe`

## Findings

1. **Publication blocker: a normal child exit can become `resource_abstain`.**

   `monitor_process()` checks `poll()`, then reads `/proc/<pid>/status`. If the
   child exits in this interval, the RSS read returns `None`. The wrapper then
   sets `termination_reason` to `rss_unsupported`, even when the return code is
   zero. An independent fake-process check produced:

   ```text
   {'returncode': 0, 'termination_reason': 'rss_unsupported', ...}
   ```

   This violates the resource status contract and can mislabel a completed
   control. Recheck `poll()` after a missing RSS sample and before a wall or RSS
   stop. Treat an already exited child as a normal completed or child-failure
   result. Add a regression test for this race.

2. **Publication blocker: the outer solver gate does not check the planted objective.**

   `_valid_child()` checks the score and its bounds but does not inspect
   `oracle.objective.score_from_key`. The frozen reference plan requires a
   certified score to be at least the feasible planted-key score. The child
   runner performs this check, but the outer validator can accept a modified
   `cold.json` without it. Require the oracle objective score, require it to be
   an integer, and reject `upper_bound` below that score. When the result is
   certified, also reject `score` below that score. Classify this as
   `implementation_failure`.

3. **Publication blocker: the outer solver gate does not prove a total fitted map.**

   `_valid_child()` accepts any non-empty `c00` through `c51` map that respects
   capacity. It does not compare the map keys with the fitted-unit set. The
   report contains only `fit_input.unit_count`, so a map with the wrong units
   can pass with a matching key hash. The reference plan requires a map total
   over fitted units. Add a deterministic fitted-unit set hash to the child
   record and require an exact key-set match in the wrapper. Add a test with the
   same map size and a wrong fitted-unit set.

4. **The code-hash output accepts an incomplete map.**

   `validate_child_outputs()` checks every reported `code_sha256` entry, but it
   does not require all expected child code entries. An empty or partial map can
   therefore pass. Require the exact expected code-path set and each matching
   digest. Add a test that removes one required entry. The pre-launch freeze
   still checks every listed file, so this finding affects output provenance.

5. **The public command contract is wider than the plan.**

   The plan fixes `python -m experiments.medical.run_control` with no options,
   but `main()` also accepts `--project-root`. It then reports the same fixed
   command for a different root. Reject this option in the public entry point,
   or add it to the documented and frozen command contract as a test-only
   interface.

## Verified controls

The wrapper verifies the external freeze allowlist and every listed byte before
it starts the child. It checks fixed parameters, resources, partition hashes,
key-record hash, output paths, process-group limits, and safe receipt contents.
The core checks pinned partition bytes before parsing and passes the fixed
`cap2`, seed `7000`, node budget `1000`, bitset, and no-warm-start settings to
the unchanged runner. The key file is written before test diagnostics.

The combined synthetic suite ran 17 tests: 7 core tests and 10 wrapper tests.
All passed with:

```text
PYTHONWARNINGS=error PYTHONPATH=src:. python -m unittest \
  experiments.medical.test_control_study experiments.medical.test_run_control -v
```

Both reviewed wrapper files pass `py_compile`. No source, encryption, or model
run was performed.

## Resolution review

The following source patch was reviewed after the initial findings:

* `experiments/medical/run_control.py`  
  `bf60c09c96580d0be130d7923294d4b83a86fca45bf86867f9bcda1bb152ff63`
* `experiments/medical/test_run_control.py`  
  `195d295cd4ca0446baa4cde9d089a972ee88a53cedaec7ba187bafcd574127cf`
* `docs/plans/celsus-model-run-v1.md`  
  `c7d62e3ec39fa568d8e216b3965d773ef1d7f3c020e8d0e663fb14fd8610a91c`

The RSS race is fixed. The monitor rechecks the child state after a missing
RSS sample and before a limit stop. The independent fake-process check now
returns a zero return code with no termination reason.

The outer validator now requires the planted objective, checks its upper-bound
relation, and checks the certified-score relation. It also requires the key
count to equal `fit_input.unit_count`. The new tests cover missing and invalid
oracle records, the bound violation, and the count mismatch.

The code-hash check now requires the exact code-path set emitted by the frozen
inner runner. The test removes that set and receives `code_hashes_invalid`.
The public entry point now rejects every argument. This matches the fixed
no-option command in the plan.

The total-map concern is resolved by scope clarification. The frozen inner
runner at `experiments/homophonic/run_controls.py` checks
`set(key) == fit_symbols` before it writes the key record. Its source hash is
covered by the pre-launch freeze, and the wrapper checks the key-record hash,
key schema, capacity, and fitted-unit count. The wrapper does not independently
recompute the fitted-unit set. The updated model-run plan states this reliance.
This is acceptable for this frozen control and must not be described as an
independent outer recomputation.

The final focused suite ran 23 tests: 7 core tests and 16 wrapper tests. All
passed with the command above, and both wrapper files passed `py_compile`.
No source, encryption, or model run was performed.
