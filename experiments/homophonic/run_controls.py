#!/usr/bin/env python3
"""Fit synthetic cipher controls and score each frozen map."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys
from typing import Any, Callable, Iterable, Mapping

ROOT = Path(__file__).resolve().parents[2]
for path in (ROOT, ROOT / 'src'):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from experiments.homophonic.controls import (
    FAMILY_NAMES, encrypt_words, recovery_metrics, seeded_control_key,
)
from experiments.homophonic.solver import solve_lexicon
from experiments.homophonic.ambiguity import preserved_hit_completions
from experiments.lexicon.run_pilot import (
    ALPHABET, LANGUAGES, branch_symbol_order, canonical_bytes, canonical_hash,
    objective_summary, objective_weights, reference_metadata, sha256_path,
)
from voynich.reference import load_reference_partitions


CAPACITIES = {'injective': 1, 'cap2': 2, 'unlimited': None}
PUBLIC_SOLVER_FIELDS = (
    'status', 'feasible', 'score_certified', 'search_exhausted', 'nodes',
    'pruned_nodes', 'frontier_node_count', 'lower_bound', 'upper_bound',
    'score', 'hit_type_count', 'candidate_count_total', 'candidate_type_count',
    'missing_candidate_count', 'cipher_type_count', 'total_weight', 'config',
    'lexicon_raw_entry_count', 'lexicon_unique_normalized_count',
    'lexicon_usable_count', 'lexicon_rejected_out_of_alphabet_count',
    'bound_metadata',
)


def code_hashes() -> dict[str, str]:
    paths = [
        'experiments/homophonic/run_controls.py',
        'experiments/homophonic/controls.py',
        'experiments/homophonic/solver.py',
        'experiments/lexicon/run_pilot.py',
        'src/voynich/reference.py', 'src/voynich/corpus.py', 'src/voynich/groups.py',
        'src/voynich/substitution.py',
    ]
    for optional in ('bitset_bound', 'ambiguity', 'anneal'):
        name = f'experiments/homophonic/{optional}.py'
        if (ROOT / name).is_file():
            paths.append(name)
    return {name: sha256_path(ROOT / name) for name in paths}


def _write_new(path: Path, value: Any) -> None:
    with path.open('xb') as handle:
        handle.write(canonical_bytes(value))


def _accuracy_gate(metrics: Mapping[str, Any]) -> dict[str, Any]:
    observed_total = metrics['observed_position_total']
    token_total = metrics['fully_observed_token_total']
    return {
        'observed_positions_pass': (
            metrics['observed_position_correct'] == observed_total
            if observed_total else None
        ),
        'fully_observed_tokens_pass': (
            metrics['fully_observed_token_correct'] == token_total
            if token_total else None
        ),
        'full_decoding_pass': (
            metrics['full_char_correct'] == metrics['full_char_total']
            and metrics['full_token_correct'] == metrics['full_token_total']
            if metrics['full_char_total'] and metrics['full_token_total'] else None
        ),
    }


def run_control(
    partitions: Mapping[str, Iterable[str]],
    *,
    family: str,
    seed: int,
    node_budget: int,
    output_path: Path,
    bound_engine: str = 'reference',
    fitter: Callable[..., dict[str, Any]] = solve_lexicon,
    metadata: Mapping[str, Any] | None = None,
    warm_start: str = 'none',
    anneal_options: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Fit validation ciphertext without an oracle or held-out score."""
    if family not in CAPACITIES:
        raise ValueError('unknown control family')
    if not isinstance(node_budget, int) or isinstance(node_budget, bool) or node_budget < 0:
        raise ValueError('node_budget must be a non-negative integer')
    if bound_engine not in ('reference', 'bitset'):
        raise ValueError('unknown bound engine')
    if warm_start not in ('none', 'anneal'):
        raise ValueError('warm_start must be none or anneal')
    options = dict(anneal_options or {})
    if set(options) - {'seed', 'iterations', 'restarts', 'order', 'add_alpha', 'start_temperature'}:
        raise ValueError('unsupported annealing option')
    if options and warm_start == 'none':
        raise ValueError('annealing options require an anneal warm start')
    output_path = Path(output_path)
    key_path = output_path.with_suffix('.keys.json')
    if output_path == key_path:
        raise ValueError('result and key paths must differ')
    if output_path.exists() or key_path.exists():
        raise FileExistsError('A result or key file exists. Select a new output path.')
    train_words = list(partitions['train'])
    validation_words = list(partitions['validation'])
    if not train_words or not validation_words:
        raise ValueError('training and validation words must be nonempty')
    planted = seeded_control_key(family, seed)
    cipher_validation = encrypt_words(validation_words, planted)
    lexicon = set(train_words)
    counts = Counter(cipher_validation)
    weights, tokens, types, denominator = objective_weights(counts)
    fit_symbols = {unit for word in counts for unit in word}
    kwargs = {
        'capacity': CAPACITIES[family], 'node_budget': node_budget,
        'symbol_order': branch_symbol_order(counts, weights=weights),
    }
    if bound_engine != 'reference':
        kwargs['bound_engine'] = bound_engine
    heuristic = None
    if warm_start == 'anneal':
        from experiments.homophonic.anneal import anneal_homophonic
        heuristic = anneal_homophonic(
            cipher_validation, train_words, plaintext_alphabet=ALPHABET,
            capacity=CAPACITIES[family], **options,
        )
        kwargs['initial_key'] = heuristic['key']
    result = fitter(weights, lexicon, ALPHABET, **kwargs)
    key = dict(result['key'])
    if not result.get('feasible') or set(key) != fit_symbols:
        raise AssertionError('control solver must return a feasible total fitted map')
    if any(letter not in ALPHABET for letter in key.values()):
        raise AssertionError('control map contains an invalid plaintext letter')
    cap = CAPACITIES[family]
    if cap is not None and any(n > cap for n in Counter(key.values()).values()):
        raise AssertionError('control map exceeds its declared capacity')

    key_record = {
        'kind': 'synthetic_reference_control', 'family': family, 'seed': seed,
        'node_budget': node_budget, 'bound_engine': bound_engine,
        'fit_scope': 'encrypted validation words and plaintext training lexicon',
        'solver_status': result['status'], 'key': dict(sorted(key.items())),
        'warm_start': warm_start,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    _write_new(key_path, key_record)

    # The test stream is first iterated after the fitted key file exists.
    test_words = list(partitions['test'])
    if not test_words:
        raise ValueError('test words must be nonempty')
    cipher_test = encrypt_words(test_words, planted)
    objective = objective_summary(counts, key, lexicon)
    planted_objective = objective_summary(counts, planted['cipher_to_plain'], lexicon)
    if objective['score_from_key'] != result['score']:
        raise AssertionError('frozen map score does not match solver score')
    if not result['lower_bound'] <= result['score'] <= result['upper_bound']:
        raise AssertionError('solver score is outside its reported bounds')
    if planted_objective['score_from_key'] > result['upper_bound']:
        raise AssertionError('solver upper bound excludes the feasible planted map')

    accuracy = {
        'validation': recovery_metrics(cipher_validation, validation_words, key, fit_symbols),
        'test': recovery_metrics(cipher_test, test_words, key, fit_symbols),
    }
    oracle = {
        'objective': planted_objective,
        'validation': recovery_metrics(cipher_validation, validation_words,
                                       planted['cipher_to_plain'], planted['units']),
        'test': recovery_metrics(cipher_test, test_words,
                                planted['cipher_to_plain'], planted['units']),
    }
    heuristic_diagnostics = None
    if heuristic is not None:
        warm_key = heuristic['key']
        warm_objective = objective_summary(counts, warm_key, lexicon)
        if result['score'] < warm_objective['score_from_key']:
            raise AssertionError('exact search discarded its warm-start lower bound')
        heuristic_diagnostics = {
            'objective': warm_objective,
            'validation': recovery_metrics(cipher_validation, validation_words, warm_key, fit_symbols),
            'test': recovery_metrics(cipher_test, test_words, warm_key, fit_symbols),
        }
    ambiguity = preserved_hit_completions(weights, lexicon, ALPHABET, key, capacity=cap)
    ambiguity['optimal_key_count_lower_bound'] = (
        ambiguity['completion_count'] if result['score_certified'] else None
    )
    covered = {unit for word in counts if ''.join(key[u] for u in word) in lexicon
               for unit in word}
    hit_coverage = {}
    for split, cipher_words, plain_words in (
        ('validation', cipher_validation, validation_words), ('test', cipher_test, test_words),
    ):
        category = {'hit_used_positions': 0, 'hit_used_correct': 0,
                    'observed_outside_hits_positions': 0, 'observed_outside_hits_correct': 0,
                    'unobserved_positions': 0}
        for cipher_word, plain_word in zip(cipher_words, plain_words, strict=True):
            for unit, letter in zip(cipher_word, plain_word, strict=True):
                if unit in covered:
                    category['hit_used_positions'] += 1
                    category['hit_used_correct'] += key.get(unit) == letter
                elif unit in fit_symbols:
                    category['observed_outside_hits_positions'] += 1
                    category['observed_outside_hits_correct'] += key.get(unit) == letter
                else:
                    category['unobserved_positions'] += 1
        hit_coverage[split] = category
    public_result = {name: result[name] for name in PUBLIC_SOLVER_FIELDS if name in result}
    report = {
        'kind': 'synthetic_reference_control', 'family': family, 'seed': seed,
        'node_budget': node_budget, 'bound_engine': bound_engine,
        'warm_start': warm_start, 'heuristic': heuristic,
        'heuristic_diagnostics': heuristic_diagnostics,
        'metadata': dict(metadata or {}),
        'encryption': planted,
        'planted_preimage_size_distribution': dict(sorted(Counter(
            sum(value == letter for value in planted['cipher_to_plain'].values())
            for letter in ALPHABET
        ).items())),
        'fitted_preimage_size_distribution': dict(sorted(Counter(
            sum(value == letter for value in key.values()) for letter in ALPHABET
        ).items())),
        'emission': 'per-letter cycles, reset at each partition',
        'fit_input': {'token_count': tokens, 'type_count': types,
                      'unit_count': len(fit_symbols),
                      'sha256': canonical_hash(cipher_validation)},
        'stream_sha256': {
            'plaintext_train': canonical_hash(train_words),
            'plaintext_validation': canonical_hash(validation_words),
            'plaintext_test': canonical_hash(test_words),
            'cipher_train': canonical_hash(encrypt_words(train_words, planted)),
            'cipher_validation': canonical_hash(cipher_validation),
            'cipher_test': canonical_hash(cipher_test),
        },
        'train_lexicon': {'type_count': len(lexicon), 'sha256': canonical_hash(sorted(lexicon))},
        'solver': public_result, 'objective': objective, 'oracle': oracle,
        'ambiguity': ambiguity,
        'positive_hit_unit_coverage': {
            'used_unit_count': len(covered), 'outside_unit_count': len(fit_symbols - covered),
            'partitions': hit_coverage,
            'limit': 'Use in an incumbent hit does not establish key identifiability.',
        },
        'accuracy': accuracy,
        'gates': {split: _accuracy_gate(value) for split, value in accuracy.items()},
        'test_fully_observed': accuracy['test']['unobserved_position_count'] == 0,
        'fitted_key_accuracy': {
            'correct': sum(key[unit] == planted['cipher_to_plain'][unit] for unit in fit_symbols),
            'total': len(fit_symbols),
        },
        'key_record_sha256': sha256_path(key_path), 'code_sha256': code_hashes(),
        'protocol_sha256': sha256_path(ROOT / 'docs/plans/visual-homophonic-pilot.md'),
        'limits': [
            'These are known-cipher controls. They contain no manuscript measurement.',
            'The planted key enters encryption and post-search scoring only.',
            'Validation accuracy is a fit diagnostic. Test accuracy uses the frozen map.',
            'A dictionary optimum does not imply a unique key or correct plaintext.',
            'Missing fitting units receive no repaired assignment.',
        ],
    }
    report = json.loads(canonical_bytes(report))
    _write_new(output_path, report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--language', choices=LANGUAGES, required=True)
    parser.add_argument('--family', choices=FAMILY_NAMES, required=True)
    parser.add_argument('--seed', type=int, required=True)
    parser.add_argument('--nodes', type=int, required=True)
    parser.add_argument('--bound-engine', choices=('reference', 'bitset'), default='reference')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--warm-start', choices=('none', 'anneal'), default='none')
    parser.add_argument('--anneal-seed', type=int, default=408)
    parser.add_argument('--iterations', type=int, default=2000)
    parser.add_argument('--restarts', type=int, default=8)
    parser.add_argument('--temperature', type=float, default=0.02)
    args = parser.parse_args()
    data = load_reference_partitions(ROOT)[args.language]
    report = run_control(
        data['words'], family=args.family, seed=args.seed, node_budget=args.nodes,
        output_path=args.output, bound_engine=args.bound_engine,
        metadata={'language': args.language, 'reference': reference_metadata(data)},
        warm_start=args.warm_start,
        anneal_options=({'seed': args.anneal_seed, 'iterations': args.iterations,
                        'restarts': args.restarts, 'start_temperature': args.temperature}
                       if args.warm_start == 'anneal' else None),
    )
    print(json.dumps({'status': report['solver']['status'], 'family': args.family,
                      'language': args.language, 'gates': report['gates']}, sort_keys=True))


if __name__ == '__main__':
    main()
