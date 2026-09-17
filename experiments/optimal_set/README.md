# Complete optimal sets

This experiment separates three questions:

1. Which maps attain the certified dictionary score in a fixed finite domain?
2. Does a training-only character model distinguish those maps?
3. How do the retained maps compare with the known control solution?

The [protocol](../../docs/plans/optimal-set-secondary-v1.md) fixes the next Latin development study.
The [first result](../../reports/OPTIMAL_SET.md) retains four primary-optimal maps and selects the correct observed map with the secondary score.
The original homophonic controls remain failed exact-recovery tests.
This experiment does not provide a manuscript reading.

## Components

`enumerate.py` checks every capacity-legal completion of a supplied partial map, within declared resource limits.
It retains all complete maps at the exact integer target score.
A map above that target produces a certificate-conflict result.
A resource stop leaves the candidate set incomplete.

This primitive does not prove that the fixed assignments are necessary or that the target is globally optimal.
Those claims require the separate score certificate and assignment-query records.
The [enumerator review](ENUMERATOR_REVIEW.md) records tests against exhaustive finite calculations.

`secondary.py` ranks supplied complete maps with exact conditional character likelihood ratios.
It uses the frozen model's word boundaries, start padding, end symbol, and unknown symbol.
It represents smoothing `0.1` as the exact rational number `1/10`.
It weights validation words by token count, without the primary dictionary weights.

The ranking retains every exact maximizer. A lexical rule selects one display map when several maps tie.
The display choice does not establish a unique solution.
The [secondary review](SECONDARY_REVIEW.md) records exact arithmetic checks and a corrected model-validation defect.

`run_study.py` checks the pinned Latin source records and reconstructs the primary objective.
It checks all 46 assignment queries before it fixes any assignments.
It saves the complete candidate set and exact ranking before selection and test diagnostics.
The [method review](METHOD_REVIEW.md) gives the conditions for combining these records.

## Completion rules

Use a candidate set only when enumeration completes within its full declared domain.
Never rank a partial set as if it were complete.
Require the baseline selected map to occur in the completed set.
Check the problem fingerprint before combining certificates, queries, and enumeration results.

Use a ranking only when every supplied candidate has an exact score.
If a resource limit stops ranking, report no selected map.
Keep exact ties and all failure records.

The study runner must save its selection before test scoring or planted-map diagnostics.
The planted key must not repair a selected map.
The study follows an inspected failure and is not blind validation.

## Checks

Run the tests from the repository root:

```sh
PYTHONPATH=src:. python -m unittest discover -s experiments/optimal_set -p 'test_*.py' -v
```

The tests use finite synthetic inputs and independent exact calculations.
They cover capacity constraints, complete and partial sets, score conflicts, ties, malformed models, and arithmetic limits.
The corpus loader verifies test input hashes before fitting. Test scoring occurs only after the selection record exists.
The ranking function receives the training model, validation ciphertext counts, and candidate maps.
It receives no test text, test scores, or planted map.

Use the published implementation commit named in the report. Run the fixed study with a new output directory:

```sh
python experiments/optimal_set/run_study.py --output-dir results/optimal-set-secondary-v1-latin
```

The runner records the three new source hashes and checks the earlier source hashes.
Its JSON records contain maps, aggregate measurements, exact ratios, and provenance hashes.
They do not contain corpus text or full language-model tables.
