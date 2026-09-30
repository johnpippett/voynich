# Substitution control without spaces

Status: fixed control method; no manuscript input.
Date: 2026-09-29.

## Question

Can a score with four context lengths recover a hidden letter permutation after all original spaces are removed?
This control uses a new score. It does not restart the stopped Naibbe experiment.
The earlier Stage 2 controls already recovered observed assignments with original word boundaries.

## Fixed input

Use the pinned Latin LLCT source and the existing reference loader.
Before loading sources, compare the reference manifest SHA-256 with this value:
`f261b781f150991e3305aae5057a94dc91afd8e59c58bb22ff199347f5ce3e6d`.
The loader rejects source hash mismatches, keeps whole-charter partitions, and removes later exact duplicate sentences.
Its existing normalization accepts complete ASCII word forms after case folding and accent removal.

Map `j` to `i`, `k` to `c`, and `w` to `uu`.
Use the alphabet `abcdefghilmnopqrstuvxyz` in that order.
Join the normalized words without spaces within each partition.
The resulting artificial stream can cross source document boundaries within its partition.
It is not an unchanged transcription of the reference text.

Use the complete training stream for model counts.
Use the first 8,192 validation characters for fitting.
Use the first 8,192 test characters for recovery with the frozen key.
Use every selected character. Do not select words, spans, or symbols by recoverability.
Record stream hashes, lengths, symbol counts, and source exclusions.

## Fixed score

Count contiguous sequences of lengths one through four in the training stream.
For each length, count a context only when a following target character exists at that length.
For length one, the context is empty.
Use additive smoothing `alpha = 0.1` over the 23-letter alphabet.

For each four-character window, score its final character with context lengths zero, one, two, and three.
The respective weights are `0.1`, `0.2`, `0.3`, and `0.4`.
The window cost is the weighted sum of negative base-two logarithms of the four conditional probabilities.
The objective is the sum of all window costs in the selected ciphertext after substitution.
The report also gives the mean cost per window.
This composite score is not a normalized sequence probability or evidence of language identity.

Use overlapping windows. Introduce no word boundary, start marker, end marker, or padding.
The first three characters do not receive separate score terms. They still enter every recovery count.

## Fixed search

The key is a permutation of all 23 alphabet positions.
For each planted seed `408`, `409`, `410`, and `411`, shuffle the plaintext alphabet with `random.Random(seed).shuffle`.
Zip the cipher alphabet with that shuffled alphabet to define the decoding key.
Encode the selected reference text with the inverse key.

The search receives only the training model and fitting ciphertext.
It receives no planted key, plaintext sample, or test ciphertext.
Use search seed `408`, eight restarts, and 2,000 pair-swap proposals per restart.
Create a new `random.Random(408)` generator for each control. Use that generator across all eight restarts.

The first start pairs frequency ranks from the complete training plaintext and the fitting ciphertext.
Descending character count and then ascending alphabet position determine each rank.
For each remaining start, use `rng.shuffle(list(range(alphabet_size)))` to create a permutation.
For each proposed swap, select two distinct cipher positions with `rng.sample(range(alphabet_size), 2)`.

Use the sum objective for simulated annealing.
The starting temperature is `0.02` times the number of fitting windows.
For zero-based proposal index `i`, use temperature `start_temperature * (1 - i / 1999)`.
Accept every non-increasing move without a random draw.
At positive temperature, accept an increasing move when `rng.random() < exp(-cost_change / temperature)`.
At zero temperature, reject every increasing move without a random draw.
Keep the lowest-cost key across all starts and proposals. Keep the earlier key when costs are equal.
Recalculate each restart's final score without incremental updates and compare it with the incremental score.
Use `math.isclose` with relative tolerance `1e-12` and absolute tolerance `1e-8` for the comparison.
Stop on a failed comparison. Apply the same comparison to the final best key.

Write the fitted key before generating its test ciphertext or computing test recovery.
Do not change inputs, settings, seeds, or score weights after a real control result.
Use a 600-second limit for the complete four-control command.
A timeout ends this method without a larger run.

## Acceptance and limits

Each control must recover every cipher assignment observed in the fitting sample.
It must also decode every test character exactly, including characters whose cipher labels were absent during fitting.
Report missing fit labels and all errors. Do not exclude difficult positions.
Report complete 23-entry key equality separately from observed-label and character recovery.
Unobserved labels do not support a claim of recovered assignments.

All four controls must pass. Failure stops this method before a manuscript experiment.
Success supports only recovery under this artificial permutation model and this reference sample.
It supplies no Voynich key, no language identification, and no false-positive estimate.
Any later manuscript experiment needs a separate fixed method and the project validation gates.
The four controls share text. They vary keys, not language samples.
The reference contains early medieval legal Latin; its genre and spelling do not identify the manuscript language.

## Failure modes and checks

- A reversed key can produce incorrect ciphertext. Compare literal small examples before the real controls.
- Repeated symbols can cause duplicate incremental updates. Compare complete and incremental scores.
- A context denominator can include terminal contexts without targets. Compare short training strings with an independent count calculation.
- Model or key fitting can read test data. Keep search arguments separate and write the key before test encoding.
- Missing labels can hide errors. Count every fitting and test character, with observed and complete key results separately.
- Changed source files can change the experiment. Refuse a source or program hash mismatch before creating output.
- A rerun can overwrite evidence. Refuse an existing output directory.
- An interrupted command can leave partial work. Keep the partial directory and report the timeout or failure.
- Green software tests can be mistaken for decipherment. Report control recovery separately from manuscript validation.

Write the end-to-end check before the implementation.
Its receipt must record the fixture, commands, expected outputs, score comparison, output protection, and results.
Use paired fixtures with unchanged fitting ciphertext and training text, but changed known truth or test plaintext.
Their fitted keys and costs must be equal.
Run the required project suite after implementation.
Freeze the protocol, command, score code, check code, and reference manifest hashes before the real controls.
Keep raw source text, model counts, ciphertext, and decoded text in the ignored result directory.

## Execution record

Use Python 3.14.7 for the recorded run.
The freeze JSON has `schema_version: 1` and a `files` object with these six paths:

- `docs/plans/spacefree-substitution-control-v1.md`
- `experiments/spacefree_substitution/score.py`
- `experiments/spacefree_substitution/run_control.py`
- `experiments/spacefree_substitution/check_e2e.py`
- `src/voynich/reference.py`
- `data/reference_manifest.json`

Each value is the file's lowercase SHA-256.
Save this record as `docs/plans/spacefree-substitution-control-v1.freeze.json` before execution.
The record is a local freeze, not an external preregistration.
Use this command from the repository root:

```sh
timeout --signal=TERM 600s python experiments/spacefree_substitution/run_control.py \
  --freeze docs/plans/spacefree-substitution-control-v1.freeze.json \
  --output results/spacefree-control-2026-09-29/run
```

Use a new output directory for a replay with unchanged inputs and settings.
A completed control failure is a research result. It must not cause a program-error exit status.
