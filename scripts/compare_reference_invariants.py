#!/usr/bin/env python3
"""Compare substitution invariants with pinned historical references."""

import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from voynich.corpus import parse_ivtff
from voynich.invariants import compare_invariants, invariant_summary
from voynich.predictive import _unitize
from voynich.reference import load_reference_partitions


def main():
    references = load_reference_partitions(ROOT)
    report = {
        'status': 'exploratory_comparison_not_language_identification',
        'references': {}, 'voynich': {}, 'comparisons': {},
        'limits': [
            'A fixed injective substitution preserves these measurements for a given text.',
            'Different texts in one language need not have identical measurements.',
            'Word-pattern support uses a finite vocabulary and does not test a joint key.',
            'The comparison does not control all differences in genre, date, spelling, or segmentation.',
            'This experiment uses the complete eligible manuscript sample. It is exploratory.',
        ],
    }
    for name, data in references.items():
        report['references'][name] = {
            'metadata': data['metadata'],
            'summaries': {split: invariant_summary(words) for split, words in data['words'].items()},
            'test_against_train': compare_invariants(data['words']['test'], data['words']['train']),
        }
    for source in ['ZL3b-n.txt', 'IT2a-n.txt']:
        path = ROOT / 'data/raw' / source
        records = parse_ivtff(path)
        eligible = [r for r in records if r['kind'].startswith('P') and r['tokens']
                    and not r['excluded_tokens']
                    and not any(marker in r['text_raw'] for marker in ['<->', '<~>'])]
        for mode in ['raw_eva', 'grouped']:
            label = f'{source}:{mode}'
            words = [_unitize(word, mode) for r in eligible for word in r['tokens']]
            report['voynich'][label] = {
                'source_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                'spacing': 'split', 'records': len(eligible),
                'summary': invariant_summary(words),
            }
            report['comparisons'][label] = {
                name: compare_invariants(words, data['words']['train'])
                for name, data in references.items()
            }
    report['code_sha256'] = {
        str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in [Path(__file__), ROOT / 'src/voynich/invariants.py',
                     ROOT / 'src/voynich/reference.py', ROOT / 'src/voynich/corpus.py',
                     ROOT / 'src/voynich/predictive.py']
    }
    output = ROOT / 'reports/reference-invariants.json'
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n')
    print(output.relative_to(ROOT))


if __name__ == '__main__':
    main()
