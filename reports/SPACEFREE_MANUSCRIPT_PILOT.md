# Substitution without spaces: manuscript result

## Result

The fixed manuscript pilot failed its rule for a later reading study.
This experiment uses the Zandbergen–Landini transcription (ZL) and the Takeshi Takahashi transcription (IT).
Its ZL test score was 4.421693, above the Latin reference score of 2.708901.
Lower scores show a better fit to this fixed character model.
The ZL score was lower than both shuffled controls and the identity score.
Those comparisons supply no word boundaries, grammar, meanings, or validated key.

The pilot stops without more search, changed settings, or a reading study.
This pilot does not show that the manuscript is not Latin.
It did not test every possible substitution method or key.
The project still has no validated Voynich key or translation.

The [fixed method](../docs/plans/spacefree-manuscript-pilot-v1.md) gives the question, inputs, search, controls, and follow-up rule.
The [aggregate record](spacefree-manuscript-pilot-v1.json) contains exact scores, experimental maps, counts, source hashes, and output hashes.
The maps are search outputs. They are not decipherment keys.

## Artificial controls

All four controls passed before the manuscript stage began.
Each recovered all 23 assignments observed during fitting and all 8,192 test characters.
No test label was absent during fitting.
The complete 26-entry permutations differ from the planted maps only among assignments absent during fitting.

| Planted seed | Correct observed assignments | Correct test characters | Complete-map differences |
| --- | ---: | ---: | ---: |
| 408 | 23 of 23 | 8,192 of 8,192 | 3 |
| 409 | 23 of 23 | 8,192 of 8,192 | 3 |
| 410 | 23 of 23 | 8,192 of 8,192 | 2 |
| 411 | 23 of 23 | 8,192 of 8,192 | 2 |

These controls share one Latin model and the same fitting and test plaintext.
They vary the planted keys, not the text samples.
The Latin training stream has 922,901 characters and 24 distinct letters; `j` and `w` are absent.
The fitting sample has 23 letters, while ZL fitting uses 24 normalized signs.
These controls supply no recovery test for all 24 manuscript fitting labels.

This method uses the complete lowercase ASCII alphabet without additional `j`, `k`, or `w` replacements.
It does not change the [earlier 23-letter control](SPACEFREE_SUBSTITUTION_CONTROL.md).

## Manuscript comparison

The search used all 73,144 eligible ZL training characters.
It saved one observed-data permutation and one permutation for each shuffled control before any manuscript held-out scoring.
It made no change to these maps after the held-out results.
The table gives mean composite cost per four-character window.
The cost is not a normalized sequence probability or a language confidence value.

| Input and map | Test characters | Test windows | Mean cost |
| --- | ---: | ---: | ---: |
| Latin reference plaintext | 8,192 | 8,189 | 2.708901 |
| ZL observed text, fitted map | 36,122 | 36,119 | 4.421693 |
| ZL shuffled characters within words, separate fitted map | 36,122 | 36,119 | 5.512663 |
| ZL shuffled word order, separate fitted map | 36,122 | 36,119 | 4.576907 |
| ZL observed text, identity map | 36,122 | 36,119 | 6.293761 |
| IT observed text, unchanged ZL map | 42,390 | 42,387 | 4.431523 |

The ZL test stream has one `v` that was absent during fitting.
Its decoding is `?`; the unused full-permutation value does not supply an assignment.
All four affected windows remain in the score with the fixed cost `log2(26)`.
Mapped character coverage is 99.997232 percent. This is assignment coverage, not reading accuracy.

The observed experimental map sends `u` to `w` and `z` to `j`.
Neither target letter occurs in the Latin training stream.
Their model scores depend on smoothing. These assignments have no empirical reference support here.

| Fixed follow-up condition | Result |
| --- | --- |
| All four artificial controls pass | Pass |
| ZL test mean is no greater than the Latin baseline | Fail |
| ZL test mean is below both controls and identity | Pass |
| At least 99 percent of ZL test characters have fitting assignments | Pass |

The failed Latin-baseline condition stops this pilot.
That threshold is an operational choice fixed before execution. It is not a language-rejection threshold.
The finite heuristic search did not examine every permutation or prove a global optimum.

## Representation and source limits

EVA is the Extensible Voynich Alphabet. It records written shapes.
This experiment uses individual code points from the existing parser's accepted lowercase tokens.
The parser lowercases uppercase connection notation. This loses that case distinction.
The runner then removes recorded spaces. It does not test a complete physical-sign inventory.

The eligible stream contains complete, nonempty paragraph records without excluded tokens or diagram interruption markers.
Complete-record selection can change the distribution of accepted text.
The [source manifest](../data/source_manifest.json) identifies Zandbergen–Landini ZL3b and Takeshi Takahashi IT2a.
The [reference manifest](../data/reference_manifest.json) fixes the Latin charter corpus version and source hashes.
The existing [reference documentation](../docs/research/reference-corpora.md) gives attribution, source terms, and extraction rules.

The Latin reference contains early medieval legal text. Near duplicates remain after exact duplicate removal.
It does not independently identify the manuscript's language, date, or genre.
Joined streams introduce transitions across word, line, folio, group, or reference-document boundaries within a partition.
The manuscript and reference data had prior exposure. This is an exploratory study.

The source groups use transcription metadata. An independent conservation audit remains unfinished.
IT receives the ZL map without another fit. Its different source coverage limits direct comparison.
This is transcription sensitivity, not independent replication.
One shuffle of each type cannot estimate a false-positive rate or supply a permutation significance test.

## Verification

The required project suite passed all 85 tests.
The existing substitution check and the new end-to-end command check passed.
The new check covers scores, missing labels, IT map use, gate decisions, delayed source loading, output protection, and hash refusal.
The test harness preceded the implementation. Its initial failure receipt remains in the private record.

All 56 restart comparisons passed the fixed `math.isclose` rule: relative tolerance `1e-12` and absolute tolerance `1e-8`.
The maximum absolute restart difference was `1.1658994480967522e-07`.
That value passes through the relative tolerance at the corresponding total score.

A separate candidate tree used fresh, hash-verified reference and manuscript downloads.
Its unchanged replay produced all 14 output files with identical bytes. No file or field was excluded.
The first command completed in 115.11 seconds; the replay completed in 115.85 seconds.
Both stayed below the fixed 1,800-second limit. All frozen files remained unchanged.

A separate direct-count audit passed.
It compared the source hashes, streams, shuffles, maps, score tables, and failed follow-up condition.
It independently scored all 56 saved restart keys without imports from the runner, scorer, or search code.
Those scores matched within relative tolerance `1e-10` and absolute tolerance `1e-9`.
All 56 saved restart drift comparisons and seven best-score drift comparisons passed their fixed limits.

The audit shares the pinned reference, corpus, and group loaders. It is not an independent transcription or source-parser implementation.
The aggregate record gives its verifier and receipt hashes.

These software checks and this replay do not supply independent evidence for manuscript meanings.

## Repeat the result

Use Python 3.14.7 on Linux for the recorded replay.
Fetch the pinned sources and run the frozen command from the repository root:

```sh
python scripts/fetch_reference_sources.py
python scripts/fetch_sources.py
timeout --signal=TERM 1800s python experiments/spacefree_manuscript/run.py \
  --freeze docs/plans/spacefree-manuscript-pilot-v1.freeze.json \
  --output results/spacefree-manuscript-repeat-v1
```

Select a new output directory. The command refuses an existing directory.
Compare all output hashes with the aggregate record's `output_sha256` object.
Keep original sources in ignored data directories. Keep decoded text and detailed run files in the ignored result directory.
The public record contains no source passages, decoded text, or model counts.

The [freeze record](../docs/plans/spacefree-manuscript-pilot-v1.freeze.json) has SHA-256:
`e498dcf648109a6371ba3d76faadb654360e6d8daaa2a7205409efddea8334b9`.
The local freeze preceded the first calibration command. It was not an external preregistration.

Record corrections in a new commit. Keep this method and result unchanged.
Use a new method version for different inputs, score rules, search settings, or acceptance conditions.
