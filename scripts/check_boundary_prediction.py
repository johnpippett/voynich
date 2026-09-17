#!/usr/bin/env python3
"""Test held-out word-boundary prediction with fixed position controls."""
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'src'), str(ROOT / 'scripts')]
from run_local_memory_diagnostic import PINS, digest, write_new
from experiments.homophonic.units import units
from voynich.context import _prepare_lines
from voynich.corpus import parse_ivtff

ALPHA, TAU, REPLICATES = 0.1, 10.0, 99
SEEDS = {'tail': 408, 'same_length': 409}

def position(t, n):
    return 'second' if t == 1 else ('last' if t == n - 1 else 'interior')

def pairs(lines):
    for group, words in lines:
        for t in range(1, len(words)):
            yield group, position(t, len(words)), words[t - 1][-1], words[t][0]

def fit(lines):
    rows = list(pairs(lines))
    alphabet = tuple(sorted({row[3] for row in rows})) + ('UNK',)
    context_alphabet = {row[2] for row in rows}
    marginal, joint = defaultdict(Counter), defaultdict(Counter)
    for _, pos, previous, target in rows:
        marginal[pos][target] += 1
        joint[pos, previous][target] += 1
    def probabilities(pos, previous, target):
        target = target if target in alphabet else 'UNK'
        previous = previous if previous in context_alphabet else 'UNK'
        counts = marginal[pos]
        p0 = (counts[target] + ALPHA) / (sum(counts.values()) + ALPHA * len(alphabet))
        context = joint.get((pos, previous), {})
        p1 = (context.get(target, 0) + TAU * p0) / (sum(context.values()) + TAU)
        return p0, p1
    for pos in ('second', 'interior', 'last'):
        for previous in (*sorted(context_alphabet), 'UNK'):
            sums = [math.fsum(probabilities(pos, previous, y)[i] for y in alphabet) for i in (0, 1)]
            if any(abs(v - 1) > 1e-12 for v in sums):
                raise ValueError('Probability normalization failed.')
    return probabilities, alphabet

def score_rows(rows, probabilities, alphabet):
    baseline, conditional = [], []
    groups = defaultdict(lambda: [[], []])
    unknown = 0
    for group, pos, previous, target in rows:
        p0, p1 = probabilities(pos, previous, target)
        a, b = -math.log2(p0), -math.log2(p1)
        baseline.append(a); conditional.append(b)
        groups[group][0].append(a); groups[group][1].append(b)
        unknown += target not in alphabet
    n = len(baseline)
    if not n:
        raise ValueError('No eligible target positions.')
    return {
        'targets': n, 'unknown_initial_targets': unknown,
        'baseline_bits_per_target': math.fsum(baseline) / n,
        'conditional_bits_per_target': math.fsum(conditional) / n,
        'gain_bits_per_target': (math.fsum(baseline) - math.fsum(conditional)) / n,
        'groups': {g: {'targets': len(a), 'gain_bits_per_target': (math.fsum(a) - math.fsum(b)) / len(a)}
                   for g, (a, b) in sorted(groups.items())},
    }

def score(lines, probabilities, alphabet):
    return score_rows(pairs(lines), probabilities, alphabet)

def matched_null(lines, source_rows, probabilities, alphabet, observed_gain):
    rows, buckets = [], defaultdict(list)
    for (group, words), source_row in zip(lines, source_rows):
        for t in range(1, len(words)):
            key = (source_row.folio, t, t == len(words) - 1,
                   len(words[t - 1]), len(words[t]))
            buckets[key].append(len(rows))
            rows.append((group, position(t, len(words)), words[t - 1][-1], words[t][0]))
    active = [indices for indices in buckets.values()
              if len({rows[i][2] for i in indices}) > 1]
    rng, draws = random.Random(410), []
    for _ in range(REPLICATES):
        copy = list(rows)
        for indices in active:
            previous = [rows[i][2] for i in indices]
            rng.shuffle(previous)
            for i, value in zip(indices, previous):
                group, pos, _, target = rows[i]
                copy[i] = group, pos, value, target
        draws.append(score_rows(copy, probabilities, alphabet)['gain_bits_per_target'])
    mean = math.fsum(draws) / REPLICATES
    return {
        'seed': 410, 'gain_draws': draws, 'mean_gain': mean,
        'order_excess': observed_gain - mean,
        'upper_gain_rank_fraction': (1 + sum(v >= observed_gain for v in draws)) / (REPLICATES + 1),
        'strata': len(buckets), 'strata_with_variable_predecessor': len(active),
        'targets_in_variable_predecessor_strata': sum(map(len, active)),
        'matching': ['folio', 'target_index', 'target_is_last', 'previous_unit_length', 'target_unit_length'],
        'preserves': 'Every target unit remains fixed. Only predecessor final units move between matched pairs.',
        'limit': 'This null does not preserve each line word multiset.',
    }

def shuffled(lines, mode, rng):
    result, changed = [], 0
    for group, words in lines:
        copy = list(words)
        bins = defaultdict(list)
        for t in range(1, len(words)):
            bins[len(words[t]) if mode == 'same_length' else 0].append(t)
        for indices in bins.values():
            values = [words[t] for t in indices]
            rng.shuffle(values)
            for t, value in zip(indices, values):
                copy[t] = value
        if sorted(copy[1:]) != sorted(words[1:]) or copy[0] != words[0]:
            raise ValueError('Shuffle changed the target multiset or first word.')
        if mode == 'same_length' and list(map(len, copy)) != list(map(len, words)):
            raise ValueError('Shuffle changed length at a position.')
        changed += tuple(copy) != words
        result.append((group, tuple(copy)))
    return result, changed

def run(source):
    filename, expected = PINS[source]
    path = ROOT / 'data/raw' / filename
    if digest(path) != expected:
        raise ValueError('Source hash mismatch.')
    parts, excluded = _prepare_lines(parse_ivtff(path, uncertain_spaces='split'))
    output = {
        'source': source, 'source_sha256': expected, 'spacing': 'split', 'exploratory': True,
        'script_sha256': digest(Path(__file__)),
        'dependency_sha256': {name: digest(ROOT / name) for name in (
            'scripts/run_local_memory_diagnostic.py', 'src/voynich/context.py',
            'src/voynich/corpus.py', 'src/voynich/groups.py', 'experiments/homophonic/units.py')},
        'alpha': ALPHA, 'tau': TAU, 'replicates': REPLICATES, 'seeds': SEEDS,
        'position_categories': ['second', 'interior', 'last'],
        'excluded_lines': dict(excluded), 'validation_used': False, 'representations': {},
        'comparison': 'Gain is position-baseline loss minus boundary-conditional loss. Recompute both losses for each shuffle.',
        'rank': '(1 + shuffled gains >= observed gain) / (replicates + 1)',
    }
    for representation in ('visual', 'raw'):
        converted = {s: [(r.group, tuple(units(w, representation=representation) for w in r.tokens)) for r in rows]
                     for s, rows in parts.items()}
        probabilities, alphabet = fit(converted['train'])
        observed = score(converted['test'], probabilities, alphabet)
        record = {'train_lines': len(converted['train']), 'test_lines': len(converted['test']),
                  'target_alphabet': alphabet, 'observed': observed, 'nulls': {}}
        for mode, seed in SEEDS.items():
            rng = random.Random(seed)
            draws, changed = [], []
            for _ in range(REPLICATES):
                permuted, count = shuffled(converted['test'], mode, rng)
                draws.append(score(permuted, probabilities, alphabet)['gain_bits_per_target'])
                changed.append(count)
            mean = math.fsum(draws) / REPLICATES
            record['nulls'][mode] = {
                'gain_draws': draws, 'mean_gain': mean,
                'order_excess': observed['gain_bits_per_target'] - mean,
                'upper_gain_rank_fraction': (1 + sum(v >= observed['gain_bits_per_target'] for v in draws)) / (REPLICATES + 1),
                'changed_line_counts': changed,
            }
        record['nulls']['matched_predecessor'] = matched_null(
            converted['test'], parts['test'], probabilities, alphabet, observed['gain_bits_per_target'])
        output['representations'][representation] = record
        print(source, representation, 'gain', observed['gain_bits_per_target'],
              {mode: {key: values[key] for key in ('mean_gain', 'order_excess', 'upper_gain_rank_fraction')}
               for mode, values in record['nulls'].items()}, flush=True)
    directory = ROOT / 'results/boundary-prediction-v1'
    directory.mkdir(parents=True, exist_ok=True)
    write_new(directory / (source + '.json'), output)

if __name__ == '__main__':
    if len(sys.argv) != 2 or sys.argv[1] not in PINS:
        raise SystemExit('Supply ZL or IT.')
    run(sys.argv[1])
