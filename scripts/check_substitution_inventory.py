#!/usr/bin/env python3
"""Check the alphabet-size constraint for a declared substitution model."""

from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from voynich.corpus import parse_ivtff
from voynich.predictive import _unitize, DECLARED_GROUPED_UNITS


def main():
    report = {
        'status': 'conditional_inventory_constraint_not_decipherment',
        'plaintext_alphabet': 'abcdefghijklmnopqrstuvwxyz',
        'compound_units': list(DECLARED_GROUPED_UNITS),
        'space_policy': 'split',
        'source_runs': {},
        'limit': 'The cardinality result assumes distinct transcription units require distinct plaintext letters. It does not test other segmentations or encoding families.',
    }
    for source in ['ZL3b-n.txt', 'IT2a-n.txt']:
        path = ROOT / 'data/raw' / source
        records = [r for r in parse_ivtff(path) if r['kind'].startswith('P')]
        complete = [r for r in records if r['tokens'] and not r['excluded_tokens']
                    and not any(m in r['text_raw'] for m in ['<->', '<~>'])]
        row = {'source_sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'samples': {}}
        for label, sample in [('accepted_paragraph_tokens', records),
                              ('complete_uninterrupted_lines', complete)]:
            sample_row = {'records': len(sample),
                          'words': sum(len(r['tokens']) for r in sample),
                          'unitizations': {}}
            for unit in ['raw_eva', 'grouped']:
                counts = Counter(s for r in sample for w in r['tokens']
                                 for s in _unitize(w, unit))
                sample_row['unitizations'][unit] = {
                    'alphabet_size': len(counts),
                    'unit_counts': dict(sorted(counts.items())),
                    'injective_map_to_ascii_lowercase_feasible': len(counts) <= 26,
                }
            row['samples'][label] = sample_row
        report['source_runs'][source] = row
    report['code_sha256'] = {
        str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in [Path(__file__), ROOT / 'src/voynich/corpus.py',
                  ROOT / 'src/voynich/predictive.py']
    }
    output = ROOT / 'reports/substitution-inventory.json'
    output.write_text(json.dumps(report, indent=2) + '\n')
    print(output.relative_to(ROOT))


if __name__ == '__main__':
    main()
