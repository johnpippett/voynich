# Naibbe relabeling control

## Result

None of the four artificial controls met the full-key acceptance rule.
Each search completed with program status `ok`.
It found at most two correct assignments among the observed labels in each test set.
The known key has a lower loss on the fit spans than the saved search key in every control.
Thus, none of these saved keys is an optimum for the stated objective.

The control used no manuscript input.
It does not test the manuscript's language or cipher.
No manuscript experiment follows these failures.
The project has no validated manuscript key or translation.

| Key seed | Fit characters kept | Test characters kept | Correct observed-label mappings | Test character errors |
| --- | ---: | ---: | ---: | ---: |
| 408 | 1,949 | 2,134 | 2 / 21 | 2,012 / 2,134 |
| 409 | 2,099 | 1,954 | 1 / 21 | 1,891 / 1,954 |
| 410 | 2,111 | 2,154 | 1 / 21 | 2,083 / 2,154 |
| 411 | 1,922 | 1,858 | 0 / 21 | 1,858 / 1,858 |

Each source sample has 8,192 normalized characters.
The fit selection keeps 23.46–25.77% of those characters. The test selection keeps 22.68–26.29%.
All observed test labels have fitted assignments. Every character error is a wrong map value; no test character is unmapped.
No control includes all 23 logical labels in both selected samples.
Missing labels prevent full-key acceptance, but they do not explain the incorrect observed assignments.

| Key seed | Known-key fit loss | Found-key fit loss | Fit predictions |
| --- | ---: | ---: | ---: |
| 408 | 2.655684 | 5.131249 | 2,136 |
| 409 | 2.769542 | 5.152206 | 2,301 |
| 410 | 2.755248 | 5.143985 | 2,313 |
| 411 | 2.681391 | 5.162500 | 2,115 |

Loss is negative log-base-two probability per prediction. Lower loss is better.
Each span contributes its characters and one end event to the prediction count.
The known map, restricted to observed labels, is a permitted map under the search rules.
Its lower loss shows a search failure. It does not prove the global optimum or explain the cause of failure.

## Question and limits

The question concerns a hidden permutation of the fixed Naibbe logical alphabet.
A permutation maps the logical labels to distinct reference-alphabet positions.
A fixed point is permitted. The permutation has 23 entries.
The control asks whether the existing substitution search can find this map from selected inverse outputs.

The [earlier Naibbe study](STAGE2.md) measured table compatibility and candidate ambiguity.
The tables use features of Voynich text. Compatibility with those tables is therefore not independent evidence for the cipher.
This control addresses search behavior on artificial text with a known answer.
It does not invert ambiguous tokens or restore original spaces.

The four keys use the same reference samples. They test key variation, not four independent text samples.
The reference corpus contains Latin legal charters. It does not cover every Latin genre, spelling system, or period.
Selected spans can differ in content and length from the complete reference stream.
After successful controls, a manuscript claim would still need independent historical evidence and manuscript validation.

## Fixed method

The local scope and program hashes were fixed before reference encoding or key search.
A prior review changed the acceptance rule before that execution.
It added complete alphabet coverage and full-map equality to the initial character-accuracy rule.
The input sizes, seeds, source selection, and search settings did not change.
These records are published after execution; they are not an external preregistration.

The reference loader checks the source hashes in [the reference manifest](../data/reference_manifest.json).
It uses the existing document partitions and duplicate exclusions.
The loader applies Unicode NFKD normalization and case-folding, then removes combining marks.
It accepts only complete surface forms that match `[a-z]+`.
Naibbe normalization then maps `j` to `i`, `k` to `c`, and `w` to `uu`.

Accepted words form one stream per partition, with original spaces removed.
Consecutive 64-character blocks divide each stream. These blocks can cross document boundaries within a partition.
The resulting streams are the control plaintext, not unchanged source transcriptions.

The language model uses every block from the training partition.
It uses order three, additive smoothing of 0.1, and the alphabet `abcdefghilmnopqrstuvxyz`.
The key-fit sample uses the first 8,192 normalized validation characters.
The test sample uses the first 8,192 normalized test characters.
The program saves each fitted key before it encodes that key's test sample.

For each seed, `random.Random(seed).shuffle` permutes the 23 labels.
The program applies the inverse map to reference text before Naibbe encoding.
The encoder uses the 52-card weights, respacing probability `17/36`, and `unigram` collision policy.
It removes no output spaces and applies no additional normalization.
Each block starts a new encoder call.
The encoder seed is `100000 + 1000 * key_seed + block_index`; test encoding adds `500000`.

A token is one encoded group between output spaces.
The complete table inverse supplies every candidate for each token.
A token qualifies only when its distinct plaintext strings have size one.
A span is a maximal run of qualifying tokens within one block.
An ambiguous token, unsupported token, or block ending breaks the run.
Only spans with at least eight logical characters enter the search.

At least 1,024 selected fit characters and 15 observed labels are necessary to start a diagnostic search.
All four controls pass this input threshold.
The unchanged `search_substitution` uses 2,000 iterations, eight restarts, seed 408, and start temperature 0.02.
The search receives no known-key argument.
Its start and end markers mark analysis spans, not original word boundaries.
No parameters or seeds changed after the results.

Full acceptance needs all 23 labels in both fit and test, the complete known map, and no test character errors.
All four controls must pass before a manuscript experiment can start.
Every selected test character enters the error count, including any character with no assignment.
The complete command had a 600-second limit. It completed without a timeout.

## Sources and reproducibility

The implementation reuses the fixed Naibbe tables from Michael A. Greshko's published cipher.
The source is [Greshko (2025), *The Naibbe Cipher: A Substitution Cipher That Encrypts Latin and Italian as Voynich Manuscript-Like Ciphertext*, Cryptologia](https://doi.org/10.1080/01611194.2025.2566408).
The [table repository](https://github.com/greshko/naibbe-cipher/tree/f2675ec5dd275268bc64dd48ea64fc0e0e9827a2) is fixed at commit `f2675ec5dd275268bc64dd48ea64fc0e0e9827a2`.
The table SHA-256 is `4e7cfd54b7ec66515d39a51e11ec97e8e19b643b0b189124eebc3982e707dcec`.

The Latin source is [Universal Dependencies, Latin LLCT](https://github.com/UniversalDependencies/UD_Latin-LLCT/tree/df63d06c5a7788b457f50bf37526146e9225c27d), under CC BY-SA 4.0.
The reference manifest fixes the source versions and file hashes.
The [public result record](naibbe-relabel-control-v1.json) contains counts, maps, losses, span lengths, and source and program hashes.
It contains no reference text or model counts.
Detailed local records stay in `results/naibbe-relabel-control-2026-09-29/`.

### Replay procedure

1. Use Python 3.14.7 for the recorded environment.
2. Run these commands from the repository root:

```sh
python scripts/fetch_reference_sources.py
python scripts/fetch_naibbe_table.py
python experiments/naibbe_relabel/check_e2e.py
timeout --signal=TERM 600s python experiments/naibbe_relabel/run_control.py --output results/naibbe-relabel-replay
PYTHONPATH=src python -m unittest discover -s tests -v
```

3. Use a new output directory for each replay. The command refuses an existing path.
4. Compare the summary and result fields with the public record. Do not include `elapsed_seconds` in equality checks.
5. Keep the output files and source hashes with the replay record.

```sh
python - <<'PY'
import json
from pathlib import Path
expected = json.loads(Path('reports/naibbe-relabel-control-v1.json').read_text())
output = Path('results/naibbe-relabel-replay')
assert json.loads((output / 'summary.json').read_text()) == expected['summary']
for row in expected['results']:
    actual = json.loads((output / f"result-{row['key_seed']}.json").read_text())
    actual.pop('elapsed_seconds')
    assert actual == row
print('All four controls match the public record.')
PY
```

## Verification

The end-to-end fixture failed before the control command existed.
After implementation, it passed the span, exclusion, block-boundary, minimum-length, and existing-output checks.
Its output SHA-256 is `acb076f4f0af382a7d43ad5bd7ab94424cc2d2fe306a8d22b111b0c905e0ce25`.
The required project suite passed all 85 tests.
These software checks do not validate a manuscript reading.

A clean tree with fresh source downloads produced the same 19 JSON files, except for elapsed time.
This comparison includes encoded inputs, inverse candidates, spans, fitted maps, the language model, and result records.
The replay used the same seeds and settings. It is a reproducibility check, not four additional independent controls.

A separate calculation built the inverse directly from the CSV, without the primary harness or project calculation functions.
It checked every stored candidate set and each encoded truth unit.
Its selected spans, character errors, and likelihoods agree with the saved results.
It used the saved language model; it did not independently build that model from raw reference text.

The first audit had incorrect assumptions about encoder-input fields, list counts, end events, and source paths.
Corrected checks keep the first failed receipt. No control input or result changed.
The primary agent compared the independent error counts with the public result and checked the permitted-map condition.
These project checks used separate AI tasks. They are not external scholarly validation.

## Decision

This attempt stops after the four failures. No manuscript fit follows.
A future search study needs a new fixed question, method, and known-key acceptance rule before execution.
The earlier stopped studies stay stopped.
These results provide a software limit, with no new manuscript sign value or plaintext.
