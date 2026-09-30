# Substitution control without spaces

## Result

All four artificial controls recovered the complete planted permutation.
Each control decoded all 8,192 test characters without errors.
All 22 cipher assignments observed during fitting were correct.
The complete map has 23 entries. The unused fitting label has the only remaining plaintext assignment under the permutation model.

| Planted key seed | Correct observed fit assignments | Correct complete map entries | Test character errors |
| --- | ---: | ---: | ---: |
| 408 | 22 / 22 | 23 / 23 | 0 / 8,192 |
| 409 | 22 / 22 | 23 / 23 | 0 / 8,192 |
| 410 | 22 / 22 | 23 / 23 | 0 / 8,192 |
| 411 | 22 / 22 | 23 / 23 | 0 / 8,192 |

The fitting sample has no plaintext `y`. The test sample has neither `y` nor `z`.
No test label was absent during fitting. Thus, these corpus controls supply no direct test of recovery for an unseen fitting label.
The command's artificial fixture separately exercises that error-counting case.
No character, word, or span was removed because it was difficult to recover.

The fitted map has a total cost of `22089.86715666271` over 8,189 overlapping windows in every control.
The mean cost is `2.69750484267465` per window.
These are weighted conditional log costs. They are not normalized sequence probabilities or language confidence scores.

## Question and method

This control asks whether a weighted character-context score can recover a hidden permutation after removal of all original spaces.
The earlier [Stage 2 controls](STAGE2.md) already recovered observed assignments with original word boundaries.
This new experiment uses a different score and complete character streams.
It does not restart the stopped [Naibbe relabeling experiment](NAIBBE_RELABEL_CONTROL.md).

The [fixed method](../docs/plans/spacefree-substitution-control-v1.md) gives the complete input, score, search, acceptance, and stop rules.
The [freeze record](../docs/plans/spacefree-substitution-control-v1.freeze.json) contains the six program, method, and reference hashes.
These hashes were fixed locally before the real controls. They are not an external preregistration.
No settings, score weights, seeds, or inputs changed after the first control run.

The existing reference loader uses separate whole-charter partitions and removes later exact duplicate sentences.
The duplicate rule does not remove near duplicates.
It normalizes complete word forms, then the control maps `j` to `i`, `k` to `c`, and `w` to `uu`.
The control joins words without spaces within each partition.
These artificial streams can contain windows across document boundaries.
They are not unchanged source transcriptions.

The model uses the complete training stream of 922,901 characters.
The fitting and test samples each use the first 8,192 normalized characters from their respective partitions.
All four controls use these same samples. They vary the hidden key, not the source text.

The score uses contiguous sequences of one through four characters, with additive smoothing of `0.1`.
For each four-character window, it scores the final character with zero, one, two, and three preceding characters.
The respective weights are `0.1`, `0.2`, `0.3`, and `0.4`.
The weights are fixed heuristic choices. They have no independent calibration in this study.

Each key search has eight starts and 2,000 swap proposals per start, with search seed `408`.
The first start pairs training and ciphertext frequency ranks. The other starts use random permutations.
The search receives the training model and fitting ciphertext only.
The command writes each fitted key before it creates that key's test ciphertext.
The run completed in 29.67 seconds, within the fixed 600-second limit.

## Sources and replay

The source is [Universal Dependencies, Latin LLCT](https://github.com/UniversalDependencies/UD_Latin-LLCT/tree/df63d06c5a7788b457f50bf37526146e9225c27d), under CC BY-SA 4.0.
The [reference manifest](../data/reference_manifest.json) fixes the source versions and SHA-256 hashes.
The corpus contains early medieval legal Latin. Its genre, period, and spelling limit the result's scope.

The [public result record](spacefree-substitution-control-v1.json) contains maps, counts, scores, hashes, and verification receipts.
It contains no reference text or model counts.
Detailed local records stay in `results/spacefree-control-2026-09-29/`.

1. Use Python 3.14.7 for the recorded environment.
2. Run these commands from the repository root:

```sh
python scripts/fetch_reference_sources.py
python experiments/spacefree_substitution/check_e2e.py
timeout --signal=TERM 600s python experiments/spacefree_substitution/run_control.py \
  --freeze docs/plans/spacefree-substitution-control-v1.freeze.json \
  --output results/spacefree-control-replay
PYTHONPATH=src python -m unittest discover -s tests -v
```

3. Use a new output directory for each replay. The command refuses an existing path.
4. Compare the output file hashes with `verification.replay.file_sha256` in the public result record.

```sh
python - <<'PY'
import hashlib, json
from pathlib import Path
expected = json.loads(Path('reports/spacefree-substitution-control-v1.json').read_text())
root = Path('results/spacefree-control-replay')
actual = {
    str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
    for path in root.rglob('*') if path.is_file()
}
assert actual == expected['verification']['replay']['file_sha256']
print('All 32 output files match.')
PY
```

## Verification

The initial end-to-end fixture failed before the control command existed.
Review added fixtures for changed known truth, changed test text, missing fit labels, and a complete freeze with one incorrect hash.
The final end-to-end command passed. The required project suite passed all 85 tests.
The command also compares each restart's incremental score with a complete score calculation.
All 32 restart comparisons passed. Their largest absolute difference was below `1e-9`.

A separate candidate tree used fresh source downloads and the same frozen files.
Its replay produced all 32 output files with identical bytes. This includes model counts, inputs, fitted maps, and decoded text.
The replay uses the same samples and keys. It is a reproducibility check, not four additional independent controls.

An independent calculation rebuilt the character-sequence counts from the pinned reference words.
It used the existing reference loader for source parsing, normalization, partitions, and duplicate removal.
Its model counts, four complete keys, character recovery counts, and total scores match the saved results.
It did not import the new scorer or search code.
These project checks used separate AI tasks. They are not external scholarly validation.

## Interpretation and next gate

This result shows exact key recovery for the stated artificial permutation model on these fixed reference samples.
It does not establish a global score optimum, a false-positive rate, or recovery on other texts.
Earlier experiments used these reference data. This is a development control, not blind manuscript validation.

No manuscript file entered this experiment. The project still has no validated Voynich key, language identification, or translation.
The successful controls do not validate Naibbe inversion, a manuscript sign inventory, or historical letter assignments.
Any manuscript experiment needs a separate fixed method and the [validation protocol](../docs/research/validation-protocol.md).
The earlier stopped studies stay stopped.
