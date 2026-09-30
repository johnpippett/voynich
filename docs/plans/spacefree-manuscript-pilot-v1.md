# Substitution without spaces: manuscript pilot

Status: method specified; program review and hash freeze are required before execution.
Date: 2026-09-30.

## Question and limits

Can one fixed substitution of normalized EVA code points produce a Latin-like stream without recorded spaces?
Use the ZL transcription with the four-context score from the successful artificial control.
Apply its observed-data key to IT without fitting another key.
EVA code points describe written shapes. This hypothesis does not show that each code point represents a letter.

This is a new experiment. It does not change or restart the stopped Stage 2, Naibbe, or homophonic methods.
The manuscript data and reference samples have prior exposure. This experiment is exploratory, not blind confirmation.
The physical groups use transcription metadata; their independent conservation audit remains unfinished.
Latin is a test hypothesis without an independent historical identification here.

## Inputs and calibration limit

Use the existing pinned Latin LLCT reference and `load_reference_partitions`.
Use its existing complete-word normalization without additional letter replacements.
Join all accepted training words without spaces to make the model stream.
Use the first 8,192 validation characters for artificial fitting and the first 8,192 test characters for recovery.
Use the complete lowercase ASCII alphabet `abcdefghijklmnopqrstuvwxyz`, in that order.

Keep `j`, `k`, and `w` distinct. Do not insert absent letters into natural reference text.

The reference training stream contains 24 letters; `j` and `w` are absent.
The selected fitting sample contains 23 letters. The selected test sample contains 22 letters.

The ZL training sample contains 24 normalized signs. Its test sample adds `v`, which is absent during fitting.
Thus, calibration cannot show recovery for every manuscript sign or the full target alphabet.
The fixed smoothing rule defines scores for absent reference letters. This mathematical rule supplies no historical support for their assignments.
Keep these limits in the result even if every artificial control passes.

For each seed 408 through 411, shuffle all 26 letters with `random.Random(seed).shuffle`.
Zip the cipher alphabet with the shuffled plaintext alphabet to make a decoding permutation.
Encode fitting plaintext with the inverse permutation.
Search with only the reference model and fitting ciphertext.

Write its fitted key before encoding or scoring test ciphertext.
Require every observed fitting assignment and every test character to be correct in all four controls.
Report full-map equality separately. Unused assignments are not recovered evidence.

For each seed, report missing fitting labels and test labels absent from fitting.
Count errors at all test positions, including positions with labels absent during fitting.
Correct unused assignments still supply no fitting evidence.
All four permutations share one model and the same fitting and test plaintext samples.
They are controls with different keys, not independent text samples.

Run all four controls.
If any control fails, stop before loading or fitting manuscript text.
Do not adjust the method after seeing a real control result.

## Fixed model and search

Reuse the unchanged `experiments/spacefree_substitution/score.py` implementation.
Use additive smoothing 0.1 over the 26-letter alphabet.
Use context lengths zero through three and respective weights 0.1, 0.2, 0.3, and 0.4.
Count a context only when its target follows. Score overlapping four-character windows without boundary markers or padding.
The first three characters have no separate score terms but remain in recovery and coverage counts.

The composite score is not a normalized sequence probability or language confidence.

Use eight restarts, 2,000 proposals per restart, and a fresh search generator with seed 408 for each fit.
Use the existing frequency start, later random permutations, swap draws, cooling rule, tie rule, and drift comparisons unchanged.
The starting temperature is 0.02 times the complete fitting window count.
The finite search does not prove a global optimum.

## Manuscript sample

Use `data/raw/ZL3b-n.txt` and `data/raw/IT2a-n.txt` with their pinned source hashes.
Use `parse_ivtff(..., uncertain_spaces='split')` and the existing `ivtff-bifolio-metadata-v3` groups.

Use individual code points from the parser's accepted lowercase EVA tokens.
The parser lowercases uppercase EVA connection notation. This representation discards that case distinction.
It does not keep every code point from the original source spelling.

Use the existing train, validation, and test split without a new salt.
Keep complete, nonempty paragraph loci whose kind starts with `P`.
Exclude a complete locus if it has any excluded token or either interruption marker, `<->` or `<~>`.

Record sequential exclusion counts for non-paragraph, empty, excluded-token, interrupted, and eligible loci.
Apply those categories in that order. Assign each record to the first applicable category.

Here, a complete locus means a transcription record without excluded tokens or either interruption marker.
This selection does not prove that the physical manuscript text is complete.

Keep every accepted normalized code point in each eligible locus. Do not add further merges or drop rare signs.
Join the accepted words in file order within each partition, without spaces.
Use the complete ZL training stream for fitting. Do not select a prefix or easy passage.

Streams can cross word, line, folio, and group boundaries within a partition. Record this artificial boundary policy.

Keep private locus offsets, folio, group, partition, and token counts for each eligible source record.
Keep stream hashes, lengths, code-point counts, and all source and program hashes.

Fit three complete ZL training samples with the same fixed Latin model and search settings:

1. The observed text in file order.
2. A shuffle of characters within each recorded word, with word order unchanged.
3. A shuffle of complete recorded words, with each word's internal order unchanged.

For the within-word control, use partition seeds 508, 509, and 510 for train, validation, and test.
For the word-order control, use partition seeds 608, 609, and 610 in that order.
Use one `random.Random(seed)` generator per partition.
For the within-word control, call `shuffle` once on each word's character list in original order.
For the word-order control, call `shuffle` once on the complete partition word list.
Generate each control independently from the original words.

These two controls are descriptive comparisons, not a false-positive estimate or a permutation significance test.

## Frozen keys and held-out scores

The search represents a full 26-position permutation.
Save the full permutation for replay, but publish a manuscript key only for signs observed in its training sample.
Write all three fitted keys before scoring manuscript validation or test data.
Apply each key to its corresponding held-out sample. Do not select a key by held-out scores.

Apply the observed ZL key to all IT partitions without refitting or changing assignments.
Different source coverage limits direct score comparisons. IT supplies transcription sensitivity, not independent confirmation.

Represent any sign absent from the fitting sample as `?` in decoded manuscript text.
Count every unmapped character and its sign. Do not use a full-permutation assignment for an unseen sign.
For a four-character window with any unmapped sign, use the fixed cost `log2(26)`.
Include every such window in the total and mean; also report its count separately.

For a completely mapped window, use the fixed model cost.
Report training, validation, and test lengths, costs, means, mapped coverage, and unknown-window counts.
Also score the raw ZL streams with identity values only for signs observed during ZL training.

## Follow-up rule

Compute the Latin baseline by scoring the selected test plaintext with the same model.
The observed ZL key is eligible for a separately fixed reading study only if all these conditions hold:

1. All four artificial controls pass.
2. The observed ZL test mean cost is no greater than the Latin test baseline.
3. It is strictly lower than both shuffled-control test means and the identity test mean.
4. At least 99 percent of ZL test characters have assignments observed during fitting.

These thresholds are fixed operational choices. They are not calibrated probabilities or proof of Latin text.
Failure ends this pilot without more restarts, changed weights, different samples, or a reading claim.
Passing permits only a new reading study under the project validation protocol.
It does not supply word boundaries, grammar, meanings, a key, or a translation.
Keep the observed permutation as an experimental map, not a decipherment key.

## Failure modes and verification

Write the end-to-end fixtures before the command implementation.
Use small artificial alphabets to compare key orientation, control recovery, and source-to-partition handling.
For these fixtures only, replace the unknown-window cost with `log2(alphabet_size)`.
Compare unknown-sign counts and window penalties with a literal example and an independent sum.

Change test text while keeping fitting input fixed. The saved fitting keys and scores must remain equal.
Make a calibration fixture fail. The command must save its failure and create no manuscript-stage artifacts.
Use an unavailable manuscript fixture file to demonstrate that the failed control prevents its opening.

Compare shuffle invariants, including per-word counts, word multiset, total lengths, and deterministic seeds.
Refuse an existing output directory and invalid fixture or freeze input before creating output.
Make sure that a hash mismatch stops the command before corpus loading. Keep partial output after an interrupted run.

Run the required project suite and the existing substitution end-to-end check.
Review the new command and fixtures before making the freeze file.
Keep the prior scorer, runner, test, protocol, and freeze record unchanged.

Use a 1,800-second limit for the complete new command. A timeout ends this version without a larger run.

After the real run, independently compare counts, key orientation, held-out scores, and gate decisions.
Replay the unchanged method in a separate output directory and compare every deterministic output byte.
Publish only aggregate results, experimental maps, configuration, and hashes.
Keep original source files in the ignored `data/raw/` directories.
Keep decoded streams, detailed loci, and model counts in the ignored result directory.

## Command and freeze

Use Python 3.14.7 for the recorded run and replay. Record its full version string.
Use this command from the repository root:

```sh
timeout --signal=TERM 1800s python experiments/spacefree_manuscript/run.py \
  --freeze docs/plans/spacefree-manuscript-pilot-v1.freeze.json \
  --output NEW_DIRECTORY
```
For synthetic fixtures, replace `--freeze` with `--fixture FIXTURE_JSON`.
Do not change a result's exit status to failure merely because its scientific gate fails.

The freeze file contains `schema_version: 1` and a `files` object with SHA-256 values for these paths:

- This plan, `docs/plans/spacefree-manuscript-pilot-v1.md`.
- `experiments/spacefree_manuscript/run.py`.
- `experiments/spacefree_manuscript/check_e2e.py`.
- `experiments/spacefree_substitution/score.py`.
- `src/voynich/reference.py`.
- `src/voynich/corpus.py`.
- `src/voynich/groups.py`.
- `data/reference_manifest.json`.
- `data/source_manifest.json`.
- `data/bifolio_manifest.json`.

Compare every frozen hash before loading any corpus. Compare raw manuscript hashes before manuscript parsing.
The existing reference loader compares its raw source hashes.
Record the freeze timestamp before execution. This is a local freeze, not an external preregistration.
