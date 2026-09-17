#!/usr/bin/env python3
"""Test endpoint association within exact target-remainder strata."""
from collections import defaultdict
import json
import math
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'src'), str(ROOT / 'scripts')]
from check_boundary_prediction import fit, position, score, score_rows
from run_local_memory_diagnostic import PINS, digest, write_new
from experiments.homophonic.units import units
from voynich.context import _prepare_lines
from voynich.corpus import parse_ivtff

REPLICATES, SEED = 99, 411

def arrange(lines, records):
    rows, buckets, excluded = [], defaultdict(list), 0
    for (group, words), record in zip(lines, records):
        for t in range(1, len(words)):
            tail = words[t][1:]
            if not tail:
                excluded += 1
                continue
            key = (record.folio, t, t == len(words) - 1, len(words[t - 1]), tail)
            buckets[key].append(len(rows))
            rows.append((group, position(t, len(words)), words[t - 1][-1], words[t][0]))
    active = [indices for indices in buckets.values()
              if len({rows[i][2] for i in indices}) > 1 and len({rows[i][3] for i in indices}) > 1]
    return rows, buckets, active, excluded

def run(source):
    filename, expected = PINS[source]
    path = ROOT / 'data/raw' / filename
    old_path = ROOT / 'results/boundary-prediction-v1' / (source + '.json')
    old = json.loads(old_path.read_text())
    if digest(path) != expected or old['script_sha256'] != digest(ROOT / 'scripts/check_boundary_prediction.py'):
        raise ValueError('Source or preceding script hash mismatch.')
    for name, value in old['dependency_sha256'].items():
        if digest(ROOT / name) != value:
            raise ValueError('Dependency hash mismatch.')
    parts, _ = _prepare_lines(parse_ivtff(path, uncertain_spaces='split'))
    result = {'source': source, 'source_sha256': expected, 'script_sha256': digest(Path(__file__)),
              'preceding_result_sha256': digest(old_path), 'replicates': REPLICATES, 'seed': SEED,
              'exploratory': True, 'matching': ['folio', 'exact_target_index', 'target_is_last',
                                              'previous_unit_length', 'exact_nonempty_target_tail'],
              'limit': 'Conditional association after observing the target remainder; no complete-word prediction or causal inference.',
              'representations': {}}
    for representation in ('visual', 'raw'):
        convert = lambda rs: [(r.group, tuple(units(w, representation=representation) for w in r.tokens)) for r in rs]
        train, test = convert(parts['train']), convert(parts['test'])
        rows, buckets, active, excluded = arrange(test, parts['test'])
        indices = [i for cell in active for i in cell]
        record = {'status': 'scored' if indices else 'abstain_no_variable_strata',
                  'eligible_targets': len(rows), 'excluded_empty_target_tail': excluded,
                  'strata': len(buckets), 'strata_variable_in_both_endpoints': len(active),
                  'variable_targets': len(indices), 'variable_groups': sorted({rows[i][0] for i in indices})}
        if indices:
            probabilities, alphabet = fit(train)
            full = score(test, probabilities, alphabet)
            expected_gain = old['representations'][representation]['observed']['gain_bits_per_target']
            if abs(full['gain_bits_per_target'] - expected_gain) > 1e-10:
                raise ValueError('Original score did not reproduce.')
            observed = score_rows([rows[i] for i in indices], probabilities, alphabet)
            rng, draws = random.Random(SEED), []
            for _ in range(REPLICATES):
                copy = list(rows)
                for cell in active:
                    previous = [rows[i][2] for i in cell]
                    rng.shuffle(previous)
                    for i, value in zip(cell, previous):
                        group, pos, _, target = rows[i]
                        copy[i] = group, pos, value, target
                draws.append(score_rows([copy[i] for i in indices], probabilities, alphabet)['gain_bits_per_target'])
            mean = math.fsum(draws) / REPLICATES
            record.update({'observed_variable_subset': observed, 'null_gain_draws': draws,
                           'mean_null_gain': mean, 'excess_per_variable_target': observed['gain_bits_per_target'] - mean,
                           'upper_gain_rank_fraction': (1 + sum(v >= observed['gain_bits_per_target'] for v in draws)) / (REPLICATES + 1),
                           'distinct_null_scores_rounded_12_places': len({round(v, 12) for v in draws})})
        result['representations'][representation] = record
        print(source, representation, {k: v for k, v in record.items()
                                       if k not in ('observed_variable_subset', 'null_gain_draws')}, flush=True)
    return result

if __name__ == '__main__':
    output = ROOT / 'results/boundary-prediction-v1/same-tail.json'
    if output.exists():
        raise ValueError('Output exists.')
    write_new(output, {'schema': 'boundary-same-tail-v1', 'sources': [run('ZL'), run('IT')]})
