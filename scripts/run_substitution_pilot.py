#!/usr/bin/env python3
"""Test substitution recovery on historical text with known random keys."""

import argparse
import hashlib
import json
from pathlib import Path
import random
import string
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from voynich.reference import load_reference_partitions
from voynich.substitution import fit_language_model, search_substitution, score_heldout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--language', choices=['latin_llct', 'italian_old'], required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--iterations', type=int, default=2000)
    parser.add_argument('--restarts', type=int, default=8)
    parser.add_argument('--words', type=int, default=2000)
    parser.add_argument('--temperature', type=float, default=0.02)
    parser.add_argument('--seeds', type=int, nargs='+', default=[408, 409])
    args = parser.parse_args()
    if args.output.exists():
        parser.error('The output exists. Select a new output path.')
    if args.words <= 0:
        parser.error('--words must be positive.')
    data = load_reference_partitions(ROOT)[args.language]
    model = fit_language_model(data['words']['train'], order=3,
                               add_alpha=0.1, alphabet=string.ascii_lowercase)
    population = data['words']['validation']
    indices = sorted(random.Random(408).sample(range(len(population)), min(args.words, len(population))))
    fitting_words = [population[i] for i in indices]
    report = {
        'status': 'planted_control_pilot_not_voynich_decipherment',
        'language': args.language, 'reference_metadata': data['metadata'],
        'configuration': {'order': 3, 'add_alpha': 0.1, 'alphabet': string.ascii_lowercase,
                          'iterations': args.iterations, 'restarts': args.restarts,
                          'start_temperature_bits_per_prediction': args.temperature,
                          'planted_key_seeds': args.seeds, 'search_seed': 408,
                          'fitting_words': len(fitting_words), 'sampling_seed': 408},
        'controls': [],
        'limits': ['The search receives no planted key or held-out plaintext.',
                   'The control uses fixed word boundaries and one injective substitution.',
                   'Dante partitions are canticles of one work. Formulaic charter passages can share shorter sequences.',
                   'This small pilot does not estimate a false-positive rate.'],
    }
    for seed in args.seeds:
        rng = random.Random(seed)
        symbols = [f'c{i:02d}' for i in range(26)]
        rng.shuffle(symbols)
        encoder = dict(zip(string.ascii_lowercase, symbols))
        oracle_key = {v: k for k, v in encoder.items()}
        cipher_train = [tuple(encoder[c] for c in word) for word in fitting_words]
        cipher_test = [tuple(encoder[c] for c in word) for word in data['words']['test']]
        print(f'{args.language}: planted seed {seed}, {len(cipher_train)} fitting words', flush=True)
        start = time.monotonic()
        result = search_substitution(cipher_train, model, iterations=args.iterations,
                                     restarts=args.restarts, seed=408,
                                     start_temperature=args.temperature)
        elapsed = time.monotonic() - start
        learned = score_heldout(cipher_test, model, result['key'], reference_key=oracle_key)
        oracle = score_heldout(cipher_test, model, oracle_key, reference_key=oracle_key)
        result['key_sha256'] = hashlib.sha256(json.dumps(result['key'], sort_keys=True).encode()).hexdigest()
        report['controls'].append({'planted_seed': seed, 'search': result,
                                   'heldout': learned, 'oracle_heldout': oracle,
                                   'elapsed_seconds': elapsed})
        print(json.dumps({'seed': seed, 'seconds': round(elapsed, 2),
                          'recovery': learned['recovery_metrics']}), flush=True)
    report['code_sha256'] = {
        str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in [Path(__file__), ROOT / 'src/voynich/reference.py',
                     ROOT / 'src/voynich/substitution.py']
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n')
    print(args.output, flush=True)


if __name__ == '__main__':
    main()
