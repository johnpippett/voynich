# Common visual units without spaces: manuscript result

## Result

The fixed common-unit pilot failed its condition for a later reading study.
It used 23 common analysis units from the Extensible Voynich Alphabet (EVA).
Each mapped unit received a different Latin letter. Every other unit stayed unknown.

The Zandbergen–Landini (ZL) test mean was 4.616742, above the Latin reference mean of 2.708901.
Lower scores show a better fit to this fixed model.
The observed ZL score was below both shuffled controls. That comparison does not identify word boundaries, grammar, meanings, or a key that has passed validation.
The pilot stops without further search, changed settings, or a reading study.

This result does not show that the manuscript is not Latin.
It does not test every possible substitution method or prove that no better key exists.
The project still has no validated Voynich key or translation.

The [fixed method](../docs/plans/common-visual-pilot-v1.md) defines the inputs, representation, unknown values, search, controls, and follow-up conditions.
The [aggregate record](common-visual-pilot-v1.json) gives exact scores, experimental partial maps, counts, source hashes, and output hashes.
These maps are search outputs, not decipherment keys.

## Artificial controls

All four controls passed before manuscript loading.
Each control used a full 26-position permutation and recovered all 23 assignments observed during fitting.
Each also recovered all 8,192 test characters. No test label was absent during fitting.
The three missing fitting labels were a property of the fixed Latin sample. The method did not filter letters to obtain that count.

| Planted seed | Correct observed assignments | Correct test characters | Unobserved assignment errors |
| --- | ---: | ---: | ---: |
| 408 | 23 of 23 | 8,192 of 8,192 | 3 |
| 409 | 23 of 23 | 8,192 of 8,192 | 3 |
| 410 | 23 of 23 | 8,192 of 8,192 | 2 |
| 411 | 23 of 23 | 8,192 of 8,192 | 2 |

These controls share one Latin model and the same text samples.
They vary the planted keys. They do not test the manuscript's shape representation or establish its language.
The Latin training stream contains 922,901 characters. The method uses all 26 lowercase ASCII letters without additional replacements.

## Manuscript comparison

The search used all 65,561 eligible ZL training units, including 129 unknown units.
It saved the observed-data map and both control maps before any manuscript validation or test scoring.
The controls shuffle units inside words or shuffle word order. They keep compounds and unknown units intact.
The unchanged observed ZL map also applies to the Takeshi Takahashi (IT) transcription without another fit.

The table gives mean composite cost per four-unit window.
The Latin baseline uses four-character windows. These costs are not normalized sequence probabilities or language confidence values.

| Input and map | Test positions | Test windows | Mean cost |
| --- | ---: | ---: | ---: |
| Latin reference plaintext | 8,192 | 8,189 | 2.708901 |
| ZL observed units, fitted map | 32,458 | 32,455 | 4.616742 |
| ZL units shuffled inside words, separate fitted map | 32,458 | 32,455 | 5.494285 |
| ZL shuffled word order, separate fitted map | 32,458 | 32,455 | 4.624615 |
| IT observed units, unchanged ZL map | 38,101 | 38,098 | 4.638206 |

The observed ZL test stream has 47 unknown units. They affect 187 overlapping windows.
Every affected window stays in the total with constant cost `log2(26)`.
No unknown unit receives an unused permutation value. No language-model window joins positions across an unknown unit.

| ZL test coverage measure | Mapped positions | All positions | Coverage |
| --- | ---: | ---: | ---: |
| Analysis units | 32,411 | 32,458 | 99.855197 percent |
| Normalized EVA code points | 36,075 | 36,122 | 99.869885 percent |

These denominators include every unknown position. Coverage measures assignment availability, not reading accuracy.

| Fixed follow-up condition | Result |
| --- | --- |
| All four artificial controls pass | Pass |
| All 23 common units occur in ZL training, and all projections pass | Pass |
| Observed ZL test mean is no greater than the Latin baseline | Fail |
| Observed ZL test mean is below both shuffled test means | Pass |
| Both ZL test coverage measures reach 99 percent | Pass |

The failed Latin-baseline condition stops this version.
The study fixed this threshold before execution. It does not decide whether the manuscript is Latin.
The difference from the word-order control is small. One shuffle of each type is not enough for a significance test or a false-positive estimate.

## Representation and source limits

Smith and Ponzi's published list defines the 23 common forms. It gives no letter values.
The [inventory report](../docs/research/visual-unit-inventory-2026-09-30.md) gives its source and all six partition counts.
The tokenizer treats `cth`, `ckh`, `cph`, `cfh`, `ch`, and `sh` as compounds inside accepted words.
These normalized analysis units need not be linguistic letters or indivisible physical signs.

The private projection keeps each full logical record, original case, accepted character position, and compound membership.
Its offsets address logical transcription records, not image positions or raw-file byte positions.
Lowercase normalization does not preserve every physical distinction. We did not examine each analysis unit in a manuscript image.

The six normalized source stream hashes match the earlier raw-EVA pilot.
The eligible cohort contains full, nonempty paragraph records without excluded tokens or diagram interruption markers.
This selection can change the text distribution. The joined streams cross recorded word, locus, folio, and group boundaries within each partition.

The [source manifest](../data/source_manifest.json) fixes ZL3b and IT2a.
The [reference manifest](../data/reference_manifest.json) fixes the Latin charter source version and hashes.
The [reference documentation](../docs/research/reference-corpora.md) gives attribution, source terms, and extraction rules.
This early medieval legal text does not identify the manuscript's language, date, or genre. Near duplicates remain after exact duplicate removal.

The research team had seen the manuscript, reference samples, and earlier results before this exploratory study.
An independent conservation audit of the source groups remains unfinished.
IT measures sensitivity to transcription changes. It is not independent historical replication.
The raw-EVA pilot has another representation and another window count. Do not use its mean cost to compare representations.

## Verification

The method and 15 dependency hashes were published before the first real calibration.
The freeze is in commit `2051d5cbe12cb302d09307b415f30d4eebb2fc78`.
All 85 required project tests passed. The earlier substitution check, earlier manuscript check, and new synthetic command checks also passed.
The [CI run](https://github.com/johnpippett/voynich/actions/runs/36696347578) passed on Python 3.11 and 3.13.

The first command completed in 129.98 seconds. The isolated replay completed in 116.35 seconds.
Both stayed below the fixed 1,800-second limit. The replay used the published commit and separate copies of the pinned input files.
All 20 deterministic output files matched byte-for-byte, with no missing or extra files.
Only `execution.json` was excluded from byte comparison. Its stable fields matched; its start time and elapsed time differed.
All 15 frozen dependency hashes remained unchanged.

All 56 saved restart drift comparisons and seven best-score comparisons passed their fixed limits.
The limits are relative `1e-12` and absolute `1e-8` under `math.isclose`.
The maximum absolute difference was `1.1589145287871361e-07`. It passes through the relative tolerance at that total score.
This comparison reads saved score fields. It does not independently calculate the model scores.

A separate direct-count audit passed with zero mismatches.
It rebuilt 6,315 logical source records and 267,220 accepted character positions.
It compared all six cohorts, all six shuffle partitions, both coverage measures, 12 score records, and the follow-up decisions.
It also independently scored all 56 saved restart keys and seven best keys.
All 360 numerical comparisons passed the same relative and absolute tolerances.

The audit uses separate model counts, source projection, and position-order scoring code.
It shares the pinned corpus parser, group loader, and reference loader. It is not an independent transcription or source-parser implementation.
The frozen runner and synthetic command checks establish the required write order. The direct-count audit compares the final saved files.
These software checks do not establish manuscript meanings. The aggregate record gives the verifier and evidence hashes.

## Repeat the result

Use Python 3.14.7 on Linux for the recorded experiment.
Fetch the pinned sources and run the command from the repository root:

```sh
python scripts/fetch_reference_sources.py
python scripts/fetch_sources.py
timeout --signal=TERM 1800s python experiments/common_visual/run.py \
  --freeze docs/plans/common-visual-pilot-v1.freeze.json \
  --output results/common-visual-repeat-v1
```

Select a new output directory. The command refuses an existing directory or a changed frozen file.
Compare the 20 deterministic output hashes with `output_sha256` in the aggregate record.
The separate `execution.json` file contains clock data. Exclude that file from byte comparison and compare its stable fields separately.
Keep source text, source positions, decoded text, and full model counts in ignored storage.

The [freeze record](../docs/plans/common-visual-pilot-v1.freeze.json) has SHA-256:
`d9e25743fed6aabdcf2b6c8b391695592b9f464086ee6f900db5d24376e732cd`.

Keep this method and result unchanged. Record corrections in a new commit.
Changed inputs, scoring, search settings, or acceptance conditions require a new method version.
