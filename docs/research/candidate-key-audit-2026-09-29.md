# Published key audit

Date: 2026-09-29.
The objective is a key or translation with independent verification.
This source review does not meet that objective.

## ZFD version and scope

The review fixes [ZFD commit `3f030a9`](https://github.com/denoflore/ZFD/tree/3f030a9293b8db15dc2c7b0d0e7c703e71711f62).
The corpus command in its README calls `06_Pipelines/regenerate_corpus.py`.
That command imports `ZFDDecoder` from `zfd_decoder_v2.py` and uses the v3 master lexicon.
The decoder filename does not indicate an obsolete corpus path.

The separate `run_test_v3.py` command uses `ZFDPipeline` with two CSV lexicons and separate settings.
Results from that statistical test do not directly validate the corpus decoder and its v3 master lexicon.

The [corpus check](https://github.com/denoflore/ZFD/blob/3f030a9293b8db15dc2c7b0d0e7c703e71711f62/06_Pipelines/regenerate_corpus.py) renders each input twice.
It checks equality between those two outputs.
Its `--check` mode does not compare them with the committed recipe pages or an independently checked translation.
This code review does not reproduce all corpus outputs or the separate statistical test.

## Fixed decoder checks

The four numbered guide examples give the following outputs under the current corpus decoder.

| Guide input | Guide output | Decoder output | Exact agreement |
| --- | --- | --- | --- |
| `qokeedy` | `kostedi` | `kosteedy` | No |
| `chedy` | `hedi` | `hedy` | No |
| `shol` | `šol` | `šol` | Yes |
| `daiin` | `dain` | `daiin` | No |

Three examples disagree. No spelling repair or alternative decoder followed.
This result concerns the [guide](https://github.com/denoflore/ZFD/blob/3f030a9293b8db15dc2c7b0d0e7c703e71711f62/GETTING_STARTED.md) and the pinned corpus decoder.
It does not reject every version or Croatian.

The decoder classifies all four examples as `fully_resolved`.
Its rounded confidence values are 0.88, 0.75, 1.00, and 0.80, respectively.
Three examples keep one unrecognized character each.
The recognized-character fractions are 7/8, 3/4, 3/3, and 4/5.
These values are code scores, not probabilities of correct meanings.

A fixed control replaced 1,019 semantic strings with 1,019 distinct labels without linguistic meanings.
All forms, keys, order, and other values stayed unchanged.
The component forms, residues, confidence values, classifications, and counters stayed equal.
All four generated glosses changed.
Thus these confidence scores cannot show that the replaced meanings are correct.
The result does not show that any particular meaning is false.

## Fixed sample-line check

The guide attributes the sequence `qokeedy dal chol ar shedy` to f88r.
The exact sequence occurs in no selected paragraph line.
The exact dot-separated string also occurs in none of the 31 physical f88r records in either source.

| Source | Paragraph lines before exclusions | Eligible lines | Eligible tokens | Excluded paragraph lines | Exact sequence occurrences |
| --- | ---: | ---: | ---: | ---: | ---: |
| ZL | 16 | 11 | 84 | 5 | 0 |
| IT | 16 | 16 | 134 | 0 | 0 |

The paragraph check uses records with kind `P0`, as specified in the pre-implementation contract.
Each source has 15 other f88r records, all with label kinds `Lc` or `Lf`.
The raw string check includes all 31 records. It does not join physical source lines.

ZL has four paragraph lines with uncertain separators and two with uncertain readings; these categories overlap.
Its parser excludes two tokens before line selection. No selected line has excluded tokens.
IT has no paragraph exclusions under these rules.
This result is conditional on the two pinned transcriptions, exact spelling, word order, and folio.
It does not show absence in every transcription or identify a replacement line.

## Historical ingredient comparison

The [V27 report](https://github.com/denoflore/ZFD/blob/3f030a9293b8db15dc2c7b0d0e7c703e71711f62/validation/corpus_comparison/V27_TRIPLE_PROVENANCE_LOCK_REPORT.md) compares Latin ingredient roots in historical sources with fields in the proposed lexicon.
It reports eleven ingredients in all three collections.
Section 12.2 limits this result to vocabulary agreement. It does not claim independent verification of sentence meanings.

The following limitation follows from the comparison method.
Let `D` be the set of meanings in a lexicon, and let `H1` and `H2` be two historical ingredient sets.
The three-set intersection is `D ∩ H1 ∩ H2`.
A permutation of the meanings among lexical forms leaves `D`, and thus that intersection, unchanged.
The comparison cannot select those form-to-meaning pairs by itself.
The age of the historical records does not remove this limitation.

This argument concerns the ingredient-set comparison.
It does not show equal manuscript frequencies after a permutation or reject every historical claim in the proposal.
We did not reproduce the historical extractions, ingredient counts, or source dates.

## Recent unit study

The [study by Rozanova and Temerev, version 1](https://arxiv.org/abs/2608.17096v1) examines possible text units and separators.
The paper supplies no Voynich key or translation.
Its ancillary files contain the attack code and calibration results.

Each learned unit covers a span of input symbols. Each class groups learned units.
The calibration selects the most common underlying letter in each unit span, then the most common letter in each class.
The reported agreement compares the inferred class letter with that class-majority letter.
The measure weights learned unit occurrences with input word frequencies.
It does not compare the complete decoded stream with the original plaintext.

The ancillary synthetic calibration gives agreements from 0.736505 to 0.926244 under the Latin model.
These measures do not show recovery of an exact key or complete test plaintext.

The source remains relevant to possible sign units.
A new manuscript attack needs a justified unit model and a recovery test on complete known text.
This review did not run the downloaded attack code.

## Sources and verification

The [source manifest](candidate-key-audit-2026-09-29.sources.json) records immutable URLs and SHA-256 hashes.
The primary agent checked the cited code and reports against those saved bytes.
Separate AI tasks checked the current decoder paths and the ingredient comparison.
These checks are part of this project. They are not external scholarly validation.

The [fixed plan](../plans/zfd-candidate-audit-v1.md) contains the criteria recorded before decoder execution.
The [version addendum](../plans/zfd-candidate-audit-v1-version.md) records the execution-path check before the worker continued.
The public plan is a verbatim copy of the pre-execution record. Its text and hash remain unchanged.

The [result receipt](../../reports/zfd-candidate-audit-v1/result.json) records all fixed outputs and exclusions.
A second run reproduced every field except the command string.
A separate calculation used the literal character table and direct source records, without importing the decoder.
It confirmed all four outputs and both raw absence counts. It did not reproduce the paragraph eligibility filters independently.

The [E2E receipt](../../reports/zfd-candidate-audit-v1/verification.json) records the end-to-end checks and artifact hashes.
An altered source copy failed its hash check before decoder import.
An existing output path failed without a change to its contents.
A [clean replay](../../reports/zfd-candidate-audit-v1/clean-replay.json) used the public setup command in a temporary tree.
Five fresh external downloads and the pinned transcriptions gave the same result fields, except the command string.
The existing project suite passed all 85 tests.
The [reproduction instructions](../../reports/zfd-candidate-audit-v1/README.md) specify setup, commands, and comparison rules.

## Decision

We do not accept this candidate as a manuscript key or translation.
The fixed check stops without changed examples, source selection, lexical meanings, or decoder parameters.
The source review also supplies no complete recovery method from the recent sign-unit study.
The project objective remains unresolved and active.
