#!/usr/bin/env python3
"""Run the exploratory local-word diagnostic with the existing model."""
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
from experiments.local_memory import model as memory
from voynich.context import _prepare_lines
from voynich.corpus import parse_ivtff

PINS = {
    'ZL': ('ZL3b-n.txt', 'bf5b6d4ac1e3a51b1847a9c388318d609020441ccd56984c901c32b09beccafc'),
    'IT': ('IT2a-n.txt', '7f27a8b0feed8f6de0a99900df6bf912dd1d295c38e5f830bac8b41c3f536fb5'),
}
DEPENDENCIES = (
    'scripts/run_local_memory_diagnostic.py', 'experiments/local_memory/model.py',
    'src/voynich/corpus.py', 'src/voynich/context.py', 'src/voynich/groups.py',
)

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def write_new(path, value):
    with path.open('x') as handle:
        json.dump(value, handle, sort_keys=True, indent=2, allow_nan=False)
        handle.write('\n')

def run(source):
    filename, expected = PINS[source]
    source_path = ROOT / 'data/raw' / filename
    assert digest(source_path) == expected
    rows = parse_ivtff(source_path, uncertain_spaces='split')
    parts, excluded = _prepare_lines(rows)
    lines = {split: tuple(tuple(tuple(word) for word in row.tokens) for row in records)
             for split, records in parts.items()}
    fitted = memory.fit_unigram(lines['train'])
    original_k0, original_k1 = memory.k0_distribution, memory.k1_distribution
    cached_k0 = lru_cache(None)(lambda context: original_k0(fitted, context))
    cached_k1 = lru_cache(None)(lambda context: original_k1(fitted, context))
    def k0(model, context):
        assert model is fitted
        return cached_k0(context)
    def k1(model, context):
        assert model is fitted
        return cached_k1(context)
    memory.k0_distribution, memory.k1_distribution = k0, k1
    output = ROOT / 'results/local-memory-diagnostic-v1' / source
    output.mkdir(parents=True, exist_ok=True)
    selection = memory.select_settings(fitted, lines['validation'])
    frozen = {
        'source': source, 'source_sha256': expected, 'unitization': 'raw_eva',
        'spacing': 'split', 'exploratory': True,
        'code_sha256': {name: digest(ROOT / name) for name in DEPENDENCIES},
        'excluded_lines': dict(excluded),
        'counts': {s: {'lines': len(rs), 'words': sum(len(r.tokens) for r in rs),
                       'groups': len({r.group for r in rs})} for s, rs in parts.items()},
        'group_assignments': {s: sorted({r.group for r in rs}) for s, rs in parts.items()},
        'vocabulary_sha256': hashlib.sha256(json.dumps(fitted.count_items).encode()).hexdigest(),
        'real_vocabulary_types': len(fitted.real_vocabulary),
        'selection': selection,
    }
    write_new(output / 'selection.json', frozen)
    print(source, 'validation', selection['choice'], flush=True)
    scores = {'baseline': memory.score_lines(fitted, lines['test'], family='baseline', window=1, lambda_=0)}
    for family, choice in selection['choice'].items():
        if choice is not None:
            scores[family] = memory.score_lines(fitted, lines['test'], family=family,
                                               window=choice['window'], lambda_=choice['lambda'])
    result = {'source': source, 'selection_sha256': digest(output / 'selection.json'),
              'test_scores': scores,
              'groups': {}}
    for group in sorted({row.group for row in parts['test']}):
        group_lines = tuple(line for row, line in zip(parts['test'], lines['test']) if row.group == group)
        group_scores = {'baseline': memory.score_lines(fitted, group_lines, family='baseline', window=1, lambda_=0)}
        for family, choice in selection['choice'].items():
            if choice is not None:
                group_scores[family] = memory.score_lines(fitted, group_lines, family=family,
                                                         window=choice['window'], lambda_=choice['lambda'])
        result['groups'][group] = group_scores
    write_new(output / 'test.json', result)
    print(source, 'test', {name: row['bits_per_target'] for name, row in scores.items()}, flush=True)
    memory.k0_distribution, memory.k1_distribution = original_k0, original_k1

if __name__ == '__main__':
    if len(sys.argv) != 2 or sys.argv[1] not in PINS:
        raise SystemExit('Supply ZL or IT.')
    run(sys.argv[1])
