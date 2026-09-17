#!/usr/bin/env python3
"""Build the public findings document from aggregate result files."""

import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from voynich.agreement import compare_transcriptions
from voynich.corpus import parse_ivtff


def main():
    reports = ROOT / 'reports'
    names = ['zl-split', 'zl-join', 'it-split']
    runs = {name: json.loads((reports / f'{name}.json').read_text()) for name in names}
    raw_paths = [ROOT / 'data/raw/ZL3b-n.txt', ROOT / 'data/raw/IT2a-n.txt']
    agreement = compare_transcriptions(*(parse_ivtff(p) for p in raw_paths))
    public_agreement = {key: agreement[key] for key in [
        'status', 'alignment', 'counts', 'eligibility', 'agreement', 'interpretation_limits']}
    public_agreement['source_sha256'] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in raw_paths}
    public_agreement['code_sha256'] = {
        str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted((ROOT / 'src').rglob('*.py'))
    }
    public_agreement['focus_folio'] = agreement['focus']['folio']
    public_agreement['focus_rows'] = len(agreement['focus']['rows'])
    (reports / 'agreement.json').write_text(json.dumps(public_agreement, indent=2) + '\n')

    text = [
        '# Initial findings', '',
        '**The project does not show a decipherment.**', '',
        'These experiments measure features of two existing transcriptions.',
        'They do not produce plaintext or identify a language.',
        'All results are exploratory.', '',
        'The [run protocol snapshot](../docs/plans/run-design-v2.md) preserves the exact design used for these experiments.',
        'The [verification record](verification.json) records source checks, code checks, and the exact comparison of two runs.', '',
        '## Inputs and coverage', '',
        '| Run | Locations | Accepted tokens | Excluded tokens | Word-order lines |',
        '| --- | ---: | ---: | ---: | ---: |',
    ]
    for name, result in runs.items():
        inv = result['structure']['inventory']
        text.append(f"| {name} | {inv['records']:,} | {inv['tokens']:,} | {inv['excluded_tokens']:,} | {result['structure']['word_order_sample']['lines']:,} |")
    text.extend([
        '', '`split` treats an uncertain space as a word boundary. `join` removes that uncertain boundary.',
        'The IT input has no uncertain-space commas. Its two spacing policies give the same tokens.',
        'Accepted tokens contain basic EVA characters after the declared normalization.',
        'EVA represents written shapes. It does not identify linguistic letters.', '',
        '## Word-order controls', '',
        'The control permutes words within each eligible line, using 499 samples and seed 408.',
        'The tests exclude incomplete lines, `<->` and `<~>` diagram interruptions, labels, and lines with fewer than three words.', '',
        '| Run | Statistic | Observed | Null expectation | Holm-adjusted p |',
        '| --- | --- | ---: | ---: | ---: |',
    ])
    for name, result in runs.items():
        for metric, row in result['structure']['word_order_tests'].items():
            text.append(f"| {name} | {metric} | {row['observed']:.5f} | {row['null_expectation']:.5f} | {row['holm_p_value']:.3f} |")
    text.extend([
        '', '`initial_gallows` measures initial EVA `k`, `t`, `p`, or `f`.',
        '`initial_length_difference` compares the first word with the mean length of the other words.',
        '`adjacent_near` measures word pairs with edit distance at most one, including equal words.',
        '`adjacent_equal` measures exact repetitions.',
        '`initial_gallows`, `initial_length_difference`, and `adjacent_near` have positive effects in all three runs.',
        'Exact repetition does not pass the 0.01 corrected threshold in these runs.',
        'The smallest possible unadjusted p-value is 0.002. Values at this limit do not measure the full evidence strength.',
        'The correction covers four tests within each run. The sensitivity runs are not independent confirmations.', '',
        '## Character prediction', '',
        'Prediction loss measures surprise in bits per predicted unit. Lower values indicate better prediction.',
        'The table uses raw EVA characters and includes the end-of-word symbol in the denominator.',
        'Order zero uses no preceding character. Order three uses up to three preceding characters.', '',
        '| Run | Order 0 | Order 1 | Order 2 | Order 3 | Shuffled training, order 3 |',
        '| --- | ---: | ---: | ---: | ---: | ---: |',
    ])
    for name, result in runs.items():
        scores = result['predictive']['scores']
        values = [scores['observed']['raw_eva'][f'order_{i}']['bits_per_symbol'] for i in range(4)]
        values.append(scores['shuffled_null']['raw_eva']['order_3']['bits_per_symbol'])
        text.append(f"| {name} | " + ' | '.join(f'{v:.4f}' for v in values) + ' |')
    text.extend([
        '', 'Character order supplies predictive information on the selected test groups.',
        'The aggregate JSON files also contain all compound-unit results.',
        'Those controls shuffle compound units after segmentation. They do not shuffle characters before segmentation.',
        'Bit rates from different symbol units are not directly comparable.',
        'No historical-language comparison corpus was used. These scores cannot identify a language.', '',
        '## Word prediction', '',
        'The fixed bigram model uses the preceding word. The unigram model uses training word frequencies.',
        'Both models score the same target positions. The bigram uses interpolation strength 10.', '',
        'Loss values are bits per scored target.', '',
        '| Run | Test targets | Unigram loss | Bigram loss | Shuffled-training loss | Unknown targets | Truly unseen targets |',
        '| --- | ---: | ---: | ---: | ---: | ---: | ---: |',
    ])
    for name, result in runs.items():
        scores = result['context']['scores']['test']
        uni = scores['unigram']
        text.append(f"| {name} | {uni['scored_words']:,} | {uni['bits_per_word']:.4f} | {scores['bigram_original']['bits_per_word']:.4f} | {scores['bigram_shuffled_train']['bits_per_word']:.4f} | {uni['unknown_target_rate']:.1%} | {uni['unseen_target_rate']:.1%} |")
    text.extend([
        '', 'Unknown targets include rare training words omitted from the model vocabulary.',
        'Truly unseen targets did not occur in the training lines.',
        'Loss values refer to this reduced vocabulary, which combines unknown words into one symbol.',
        'The fixed bigram performs worse than the unigram in these runs.',
        'Original-order training performs better than shuffled training.',
        'This result does not show that word order lacks information or that the manuscript lacks language.',
        'Sparse counts, tokenization, and the fixed smoothing rule can affect this comparison.',
        'The aggregate files include paired group-bootstrap intervals and every group score.', '',
        '## Transcription agreement', '',
        f"The comparison aligns {agreement['counts']['aligned']:,} locations.",
        f"It retains {agreement['counts']['eligible']:,} pairs after the stated exclusion rules.",
        f"Accepted token sequences agree exactly in {agreement['agreement']['tokens']['identical']:,} eligible pairs ({agreement['agreement']['tokens']['coverage']:.1%}).",
        f"The comparison contains {len(agreement['focus']['rows'])} locations on folio 84r.",
        'Agreement does not show accuracy or independence. The transcriptions can share sources and conventions.',
        'The public report contains aggregate counts. Complete text comparisons remain local.', '',
        '## Review corrections and limits', '',
        'The initial exploratory split used numeric folio numbers alone.',
        'That split separated folios 85 and 86, which Yale identifies as one foldout.',
        'The reported runs use `conservative-foldout-groups-v2` and join the declared candidate groups.',
        'The `fRos` identifier also joins group 85.',
        'Candidate unions prevent possible overlap. They do not prove physical identity.',
        'The [physical-group report](../docs/research/physical-groups.md) separates direct evidence from these assumptions.',
        'A complete physical-sheet map is not available.',
        'Character models retain certain words from incomplete lines. Word-context models exclude those lines to preserve adjacency.',
        'This difference in samples prevents a direct comparison of their loss values.', '',
        '## Further work', '',
        '1. Complete the image-based map of physical sheets and uncertain transcription locations.',
        '2. Add historical-language reference texts and known ciphers with recoverable solutions.',
        '3. Compare fixed cipher and text-generation models on new evaluation groups.',
        '4. Require a deterministic reading method before testing a proposed translation.', '',
        'No candidate key, plaintext language, or translation has passed those tests.',
        'The [literature review](../docs/research/literature.md) records relevant sources and competing explanations.', '',
    ])
    (reports / 'FINDINGS.md').write_text('\n'.join(text), encoding='utf-8')
    print(reports / 'FINDINGS.md')


if __name__ == '__main__':
    main()
