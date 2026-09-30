# Common visual units without spaces

Status: fixed method; a file-hash freeze must precede any real fitting run.
Date: 2026-09-30.

## Question and limits

Can one injective map from 23 common analysis units to Latin letters pass a fixed comparison without recorded spaces?
An injective map gives different letters to different units.
Every other unit stays in the stream with an unknown value.
This is a new representation and partial-map model. It does not extend the stopped raw-EVA pilot.

The Extensible Voynich Alphabet (EVA) records written shapes without letter values.
The [source review](../research/glyph-unit-evidence.md) separates written shapes from linguistic units.
Smith and Ponzi list 23 common forms on page 2 of their July 2018 preprint.
Their list is an analysis choice. It supplies no letter values or historical cipher identification.
Their Takahashi source omits the Rosettes. This does not establish the same omission in this project's pinned sources.

The source PDF has SHA-256 `6bb5e9103da8da403d847fa7df979b64b23690dc71b13121788fe1b21aa3f6d2`.
Its URL is <https://agnosticvoynich.files.wordpress.com/2019/06/glyph-combinations-across-word-breaks-in-the-voynich-manuscript-preprint.pdf>.
The [inventory probe](../research/visual-unit-inventory-2026-09-30.md) found 30 normalized ZL training units under the six-compound rule.
A total injective map from those 30 units to 26 letters is impossible.
The source-defined common list covers about 99.8 percent of the training units in each transcription.
This coverage is a count from data examined in this project. It does not measure prediction on unseen text or reading accuracy.

This method has prior exposure to the manuscript, reference samples, and earlier results.
It is exploratory. This project has no independent conservation audit of the group map.
This plan tests Latin as a hypothesis. It gives no historical evidence that identifies Latin as the manuscript language.

## Fixed inventory and source record

Use this ordered list of lowercase analysis labels:

```text
o y a e ch sh k t f p ckh cth cfh cph d s r l i n m g q
```

The final period in the source paragraph is punctuation. It is not a 24th unit.
Use the unchanged six-compound longest-match tokenizer separately inside each accepted word.
Its compounds are `cth`, `ckh`, `cph`, `cfh`, `ch`, and `sh`.
Keep all other accepted code points as separate units. Do not merge `in`, `iin`, `qo`, or rare forms.

Use the pinned Zandbergen-Landini (ZL3b) and Takeshi Takahashi (IT2a) transcriptions.
Keep the parser, source groups, and complete-record selection from the stopped raw-EVA pilot.
Use `uncertain_spaces='split'` and `ivtff-bifolio-metadata-v3`.
Apply the same first-match categories: non-paragraph, empty, excluded-token, interrupted, eligible.
An interrupted record has `<->` or `<~>`. Keep every eligible word and every partition.
Compare the six normalized stream hashes with the published raw-EVA pilot aggregate before manuscript fitting.

Keep each eligible record's complete `text_raw`, source order, source hash, folio, locus, group, and partition privately.
Build an ordered source-character projection for every accepted word before unitization.
It must reproduce the parser's accepted lowercase token exactly.
Keep each projected character's original spelling and offset into `text_raw`.
Keep comments, braces, and connectivity notation in the complete original logical record.
These offsets address a logical locus, not image coordinates or raw-file byte positions.
No image review supplies evidence for each analysis unit.

The analysis uses lowercase canonical labels, including `Sh` to `sh` and capitalized gallows forms to their lowercase labels.
This is an explicit normalization choice. Keep original case and source positions in the evidence.
Do not claim that the normalized labels keep every physical distinction.
Refuse an unsupported source control or a projection mismatch. Do not repair it during fitting.

Each visual unit keeps its normalized label and the ordered source positions for its constituent EVA code points.
Require ordered, complete coverage of every accepted token and exact reconstruction from those positions.
Never join code points across a recorded word boundary to form a compound.

## Model, unknowns, and calibration

Use the unchanged Latin reference extraction and 26-letter model from `experiments/spacefree_substitution/score.py`.
Use all accepted reference training words, joined without spaces.
Use the first 8,192 validation characters for control fitting and the first 8,192 test characters for recovery.
Keep the complete lowercase ASCII alphabet, without additional letter replacements.
Keep context lengths zero through three, weights 0.1, 0.2, 0.3, 0.4, and additive smoothing 0.1.
Count contexts only when their targets follow. Score overlapping four-letter windows without padding or boundary markers.
The first three positions have no separate score terms. Keep them in all recovery and coverage counts.
The score is a composite cost, not a normalized sequence probability or language confidence.

Implement a separate unknown-aware search without changing the earlier scorer or runner.
Represent each common unit by its position in the ordered list, zero through 22.
The 23 common labels and three extra internal cipher slots form a 26-position permutation. Manuscript data never emit those slots.
Every unit outside the common list has an unknown value and keeps its source label in private storage.
Do not give an outside unit an unused permutation value.

A window that contains any unknown unit has constant cost `log2(26)`.
Include every unknown window in the total, mean, temperature scale, and reported window count.
Unknown windows have no key-dependent score contribution. Do not join the positions on either side of an unknown unit.
Every completely mapped window uses the unchanged model table.
Refuse scoring or fitting inputs shorter than four units.
The scorer accepts an all-unknown stream. Refuse a search input with no completely mapped four-unit window.
Such an input supplies no key-dependent score term.
Report the completely mapped window count for every search.

Use the earlier eight-restart, 2,000-proposal search with a fresh `Random(408)` for each fit.
Keep its frequency start, later random starts, swap draws, tie rule, cooling schedule, and acceptance draws.
Ignore unknown positions when ranking cipher-symbol frequencies.
The initial temperature is `0.02 * total_window_count`, including unknown windows.
Keep the earlier drift limits: relative `1e-12` and absolute `1e-8` under `math.isclose`.
The finite search proves no global optimum.

Before manuscript source loading, run the same four artificial permutations with seeds 408 through 411.
These controls use abstract cipher labels from the full 26-position alphabet.
The 23 observed fitting labels are a property of the fixed Latin sample, not an encoding limit.
Use the full planted permutation to encode every test character. Do not filter or replace reference letters.
For the real run, refuse a fitting sample whose distinct-label count is not 23.
They test the search with 23 observed fitting labels, rather than the manuscript shape projection.
Write each fitted control key before encoding or scoring its test stream.
Require every observed fitting assignment and every test character to be correct in all four controls.
Report full-map equality and unobserved assignments separately.
The four controls share one model and the same text samples. They are not independent text samples.
If any control fails, stop before manuscript source loading. Do not tune the settings.

## Manuscript fits and comparisons

Require every common-list unit to occur in ZL training before any manuscript fit.
Join complete tokenized words in source order inside each existing partition.
The joined streams introduce transitions across word, locus, folio, and group boundaries.

Fit three ZL training streams with the same settings:

1. The observed visual-unit stream.
2. Visual units shuffled inside each recorded word, with word order unchanged.
3. Complete recorded words shuffled, with internal unit order unchanged.

Use within-word partition seeds 508, 509, and 510 for train, validation, and test.
Use word-order seeds 608, 609, and 610 in the same partition order.
Use one fresh generator per partition. Make each shuffle independently from the original unitized words.
Move unknown units with all other units. Do not delete them from a shuffle.

Write all three fitted maps before manuscript validation or test scoring.
Apply each map to its matching held-out stream.
Apply the observed ZL map to all IT partitions without another fit or assignment change.
IT is a transcription sensitivity check, not independent historical replication.

Report every stream's unit count, normalized EVA code-point count, mapped counts, outside-label counts, costs, means, and unknown-window counts.
Report both unit-position coverage and EVA code-point coverage.
For EVA code-point coverage, count each constituent normalized source code point in a mapped unit.
Do not include punctuation, metadata, comments, or layout whitespace in this denominator.
Keep every outside unit and its constituent code points in the respective total denominators.
Coverage shows assignment availability. It is not reading accuracy.

There is no identity map for compound labels such as `ch`.
Do not invent one. The earlier raw-EVA identity score is not a matched control here.

## Fixed follow-up rule

Use the selected Latin test plaintext's mean score as the reference baseline.
A later reading study is eligible only if all conditions pass:

1. All four artificial controls pass.
2. All 23 common units occur in ZL training, and every source projection passes.
3. The observed ZL test mean is no greater than the Latin test mean.
4. The observed ZL test mean is strictly below both shuffled test means.
5. Both ZL test coverage measures are at least 99 percent.

These thresholds are fixed operational choices. The two shuffles supply no false-positive estimate or significance test.
Any failed condition stops this version without additional search, new signs, homophony, selected passages, languages, or reading claims.
A passing pilot would permit only a separately fixed reading study under the project validation protocol.
It would not supply a full key, language identification, grammar, meanings, or translation.

## Software checks and execution

Write end-to-end fixtures before implementation. Keep the initial failure receipt.
Include exact source-projection examples with uppercase letters, braces, comments, layout whitespace, and both accepted boundary markers.
Compare normalized tokens with the existing parser, source positions with literal expected positions, and complete record reconstruction with kept input.
Reject unsupported syntax and projection disagreement.

Compare all unknown-window sums with a separate direct calculation.
Include unknowns at the first, middle, and final positions, overlapping unknown windows, and an all-unknown stream.
Run the search on a mixed known-and-unknown fixture. Compare its fitted score with an independent literal window sum.
Refuse a search with no completely mapped window, and make sure outside manuscript units receive no spare permutation value.
Keep unknown units during both shuffles. Compare word and unit multisets and deterministic order.
With no unknowns, require the new search to reproduce the old search's full result on a fixed artificial fixture.
Require failed calibration to prevent opening an unavailable manuscript fixture.
Change test data only and require every fitted manuscript map and fitting score to remain unchanged.
Compare IT output with direct application of the saved ZL map.
Compare every follow-up Boolean with a separate literal calculation.
Stop before output creation if its path exists or a frozen file hash differs.

Run the required project suite and relevant old and new end-to-end checks before freezing.
Record reviewed plan, code, data-manifest, prior-aggregate, and dependency hashes before the first real control run.
The freeze uses `schema_version: 1` and a `files` object with these exact paths:

```text
docs/plans/common-visual-pilot-v1.md
experiments/common_visual/check_e2e.py
experiments/common_visual/projection.py
experiments/common_visual/search.py
experiments/common_visual/run.py
experiments/spacefree_manuscript/run.py
experiments/spacefree_substitution/score.py
experiments/homophonic/units.py
src/voynich/reference.py
src/voynich/corpus.py
src/voynich/groups.py
data/reference_manifest.json
data/source_manifest.json
data/bifolio_manifest.json
reports/spacefree-manuscript-pilot-v1.json
```

Compare every frozen hash before any corpus loading or output creation.
Keep the inventory unchanged after freezing. A change to its units or normalization needs a new method version.
Use a fixed 1,800-second limit with a POSIX alarm and the external timeout command.
Stop this version after a timeout or real-run error. Keep partial evidence.

After execution, independently compare source projections, counts, keys, scores, and decisions.
Any failed audit or replay comparison stops this version. Keep the failure receipt and original result.
Do not tune a replacement run or describe an unverified result as verified.
Replay the frozen command in a separate output directory. Compare every deterministic output byte.
Keep elapsed times and wall-clock timestamps in separate execution receipts, outside deterministic result files.
The `execution.json` file is this separate receipt. Exclude it from byte comparison and identify that exclusion in the replay record.
Keep output-directory paths out of deterministic result files.
Keep source text, source-position records, decoded text, and model counts in ignored storage.
Publish only aggregate results, experimental partial maps, configuration, source attribution, and hashes.

Use this command from the repository root:

```sh
timeout --signal=TERM 1800s python experiments/common_visual/run.py \
  --freeze docs/plans/common-visual-pilot-v1.freeze.json \
  --output NEW_DIRECTORY
```

Use Python 3.14.7 for the recorded run and replay. Record its complete version string.
For software fixtures only, use `--fixture FIXTURE_JSON` instead of `--freeze`.
No real research setting is a command-line tuning option.
