#!/usr/bin/env python3
"""Compare fixed edit scores with two conditional word-order controls."""
from collections import defaultdict
from functools import lru_cache
import hashlib
import json
import math
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'src'), str(ROOT / 'scripts')]
from run_local_memory_diagnostic import PINS, digest, write_new
from experiments.local_memory import model as memory
from voynich.context import _prepare_lines
from voynich.corpus import parse_ivtff

REPLICATES = 99
SEEDS = {'tail': 408, 'same_length': 409}

def run(source):
    directory = ROOT / 'results/local-memory-diagnostic-v1' / source
    frozen = json.loads((directory / 'selection.json').read_text())
    observed = json.loads((directory / 'test.json').read_text())
    assert observed['selection_sha256'] == digest(directory / 'selection.json')
    for name, expected in frozen['code_sha256'].items():
        assert digest(ROOT / name) == expected
    filename, expected = PINS[source]
    source_path = ROOT / 'data/raw' / filename
    assert digest(source_path) == expected
    parts, _ = _prepare_lines(parse_ivtff(source_path, uncertain_spaces='split'))
    convert = lambda rows: tuple(tuple(tuple(word) for word in row.tokens) for row in rows)
    fitted = memory.fit_unigram(convert(parts['train']))
    assert hashlib.sha256(json.dumps(fitted.count_items).encode()).hexdigest() == frozen['vocabulary_sha256']
    lines = convert(parts['test'])
    choice = frozen['selection']['choice']['edit']
    assert choice is not None
    window, weight = choice['window'], choice['lambda']
    p0 = fitted.p0
    real = set(fitted.real_vocabulary)
    @lru_cache(None)
    def kernel(context):
        return memory.k1_distribution(fitted, context)
    def loss(line):
        terms = []
        for t in range(1, len(line)):
            target = line[t] if line[t] in real else memory.UNK
            contexts = line[max(0, t - window):t]
            mean = math.fsum(kernel(c)[target] for c in contexts) / len(contexts)
            terms.append(-math.log2((1 - weight) * p0[target] + weight * mean))
        return math.fsum(terms)
    target_count = sum(len(line) - 1 for line in lines)
    original_bits = math.fsum(loss(line) for line in lines)
    expected_bits = observed['test_scores']['edit']['total_bits']
    assert math.isclose(original_bits, expected_bits, rel_tol=0, abs_tol=1e-8)
    baseline_bits = math.fsum(-math.log2(p0[w if w in real else memory.UNK])
                              for line in lines for w in line[1:])
    assert math.isclose(baseline_bits, observed['test_scores']['baseline']['total_bits'], rel_tol=0, abs_tol=1e-8)
    result = {
        'source': source, 'selection_sha256': digest(directory / 'selection.json'),
        'test_sha256': digest(directory / 'test.json'),
        'script_sha256': digest(Path(__file__)),
        'replicates': REPLICATES, 'seeds': SEEDS, 'choice': choice,
        'target_count': target_count, 'observed_bits_per_target': original_bits / target_count,
        'absolute_gain_bits_per_target': (baseline_bits - original_bits) / target_count,
        'nulls': {},
    }
    for mode, seed in SEEDS.items():
        rng = random.Random(seed)
        draws, changed = [], []
        for _ in range(REPLICATES):
            shuffled, changed_lines = [], 0
            for line in lines:
                copy = list(line)
                bins = defaultdict(list)
                for i in range(1, len(line)):
                    bins[len(line[i]) if mode == 'same_length' else 0].append(i)
                for positions in bins.values():
                    words = [line[i] for i in positions]
                    rng.shuffle(words)
                    for i, word in zip(positions, words):
                        copy[i] = word
                new_line = tuple(copy)
                changed_lines += new_line != line
                assert new_line[0] == line[0]
                assert sorted(new_line[1:]) == sorted(line[1:])
                if mode == 'same_length':
                    assert tuple(map(len, new_line)) == tuple(map(len, line))
                shuffled.append(new_line)
            bits = math.fsum(loss(line) for line in shuffled)
            draws.append(bits / target_count)
            changed.append(changed_lines)
        mean = math.fsum(draws) / REPLICATES
        result['nulls'][mode] = {
            'bits_per_target_draws': draws,
            'mean_bits_per_target': mean,
            'mean_order_excess_bits_per_target': mean - original_bits / target_count,
            'standard_deviation': math.sqrt(math.fsum((v - mean) ** 2 for v in draws) / REPLICATES),
            'lower_loss_rank_fraction': (1 + sum(v <= original_bits / target_count for v in draws)) / (REPLICATES + 1),
            'rank_convention': '(1 + null losses <= observed loss) / (replicates + 1)',
            'distinct_loss_count': len(set(draws)),
            'changed_line_counts': changed,
            'line_count': len(lines),
        }
        print(source, mode, {k: v for k, v in result['nulls'][mode].items()
                            if not isinstance(v, list)}, flush=True)
    result['unique_contexts'] = kernel.cache_info().currsize
    write_new(directory / 'order.json', result)

if __name__ == '__main__':
    if len(sys.argv) != 2 or sys.argv[1] not in PINS:
        raise SystemExit('Supply ZL or IT.')
    run(sys.argv[1])
