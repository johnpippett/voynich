# Local cyclic model test

Both transcriptions contain adjacent equal units under both fixed unitizations.
These repeats contradict the exact cyclic emitter defined below.
The result applies to the selected transcription units. It does not establish historical sign boundaries or a manuscript reading.
Both fixed image checks remain uncertain.

## Model and test

Each plaintext symbol has a disjoint cycle of at least two distinct output units.
Each occurrence emits the next unit in that cycle.
No unit is hidden or omitted. No reset occurs inside an accepted word.
Each word can start at an arbitrary cycle phase.

Adjacent equal output units are impossible under these assumptions.
Their common unit would identify one plaintext symbol, but its next occurrence must emit a different unit.
The test needs no plaintext dictionary, guessed key, or language assignment.

The [protocol](../docs/plans/vms-local-cyclic-falsification-v1.md) fixes two tracks:

- `raw_eva`: each lowercase EVA character is one unit.
- `visual_six`: longest-match grouping of `cth`, `ckh`, `cph`, `cfh`, `ch`, and `sh`; other characters remain separate.

EVA is a transcription notation. Neither track is an established inventory of historical linguistic units.
The term `visual_six` is a code identifier, not evidence that all its boundaries are visually confirmed.

The extractor preserves accepted source spelling and offsets.
It rejects candidates with uncertain boundaries, excluded transcription constructs, or interior whitespace.
It does not recover smaller accepted words from a rejected candidate.
Adjacency never crosses a word or source-record boundary.
The [core review](../experiments/local_cyclic/REVIEW.md) records extraction and counting checks.

## Result

All four records have status `falsified_for_fixed_track`.
A certificate is one adjacent equal pair. Overlapping pairs are counted separately.
An affected word contains at least one such pair.

| Source | Track | Eligible words | Units | Adjacent pairs | Certificates | Affected words |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| IT2a-n | raw_eva | 34,674 | 175,013 | 140,339 | 9,383 | 8,722 |
| IT2a-n | visual_six | 34,674 | 157,012 | 122,338 | 9,306 | 8,649 |
| ZL3b-n | raw_eva | 29,331 | 151,359 | 122,028 | 8,228 | 7,649 |
| ZL3b-n | visual_six | 29,331 | 135,642 | 106,311 | 8,215 | 7,637 |

The source files contain 5,215 IT records and 5,385 ZL records.
Different transcription constructs and exclusions produce different eligible-word counts.
These are two transcriptions of the same manuscript, not independent historical samples.

The largest repeat counts concern `e` and `i`.
IT has 4,903 `e` pairs and 4,241 `i` pairs in each track.
ZL has 4,370 `e` pairs and 3,741 `i` pairs in each track.
These are counts of transcription units. They do not determine whether repeated strokes form separate signs.

The public records preserve all ordered certificate locations and exclusion counts:

- [IT raw units](vms-local-cyclic-falsification-v1/IT2a-n-raw_eva.json)
- [IT six-compound units](vms-local-cyclic-falsification-v1/IT2a-n-visual_six.json)
- [ZL raw units](vms-local-cyclic-falsification-v1/ZL3b-n-raw_eva.json)
- [ZL six-compound units](vms-local-cyclic-falsification-v1/ZL3b-n-visual_six.json)

Record, candidate-word, and unit indexes start at zero.
The optional `unit_span` is the first equal unit's half-open character interval within the accepted word.
Candidate indexes include excluded nonempty candidates. Raw source words are not included in the public records.

## Fixed image checks

After counting, the first `visual_six` certificate on f84r was selected separately for each source.
The selection used source order, before image inspection. No easier replacement was selected.

| Source | Record index | Locus | Candidate index | Unit index | Unit | Image result |
| --- | ---: | --- | ---: | ---: | --- | --- |
| ZL | 3213 | `f84r.13,@P0` | 2 | 3 | `e` | Uncertain |
| IT | 3200 | `f84r.6,@Ln` | 0 | 2 | `i` | Uncertain |

The [image audit](../docs/research/f84r-local-repeat-image-audit.md) records Yale image coordinates, source hashes, and uncertainty.
The ZL candidate region was located, but the selected atomic boundary remains unconfirmed.
The IT label region was inspected, but its target span was not uniquely isolated.
Neither check provides an image-verified atomic repeat. The data-level certificates remain unchanged.

## Verification and reproduction

The primary command used public commit `8782e06b44237b08588cafb1927f3f57da72f12b`.
Its [13-file freeze](../experiments/local_cyclic/freeze-v1.json) has SHA-256:

```text
6514e43c78bccd5c6b26b8f68aaa973beb6181926d4135d8553c9d6501c0d79a
```

The freeze includes the protocol, implementation, tests, source manifest, and both raw transcription hashes.
The command completed successfully. A fresh public checkout reproduced all four output files byte for byte.
The [replay receipt](vms-local-cyclic-falsification-v1/replay-verification.json) records their hashes.

A [separate calculation](../scripts/verify_local_cyclic_independently.py) checked every pinned file before parsing source text.
It independently implemented unitization and adjacent-pair counting.
It uses the same frozen parser and strict extractor for eligibility.
It confirmed every ordered location, count, exclusion, and status.
The [audit receipt](vms-local-cyclic-falsification-v1/independent-audit.json) states this shared eligibility dependency.
This is an independent arithmetic check, not an independent transcription or eligibility audit.

The [runner review](../experiments/local_cyclic/RUNNER_REVIEW.md) covers the command and synthetic tests.
The focused suite contains 15 core tests, eight runner tests, and six unitizer tests.

Use a fresh checkout of the primary commit. Run:

```sh
python scripts/fetch_sources.py
python -m experiments.local_cyclic.run_frozen
```

Do not refresh the source manifest. The runner refuses changed input bytes and existing output files.
Keep source files outside the public repository.

## Interpretation limits

The result rejects the stated cyclic model on these two fixed unitizations.
It does not reject a different unitization, hidden emissions, or resets inside words.
It also does not reject a general homophonic map that permits a symbol to have only one output unit.
The earlier artificial controls use a narrower exact two-unit cycle than that general model.

No language, plaintext, key, or semantic claim follows from these counts.
A later alternative unitization needs independent justification and a separate recorded test.
