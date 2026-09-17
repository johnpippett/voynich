#!/usr/bin/env python3
"""Run a bounded fixed-substitution pilot with a unit-shuffle control."""

import argparse
import hashlib
import json
from pathlib import Path
import random
import string
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from voynich.corpus import parse_ivtff
from voynich.groups import group_id, grouping_config, split_bucket, split_name
from voynich.reference import load_reference_partitions
from voynich.substitution import fit_language_model, search_substitution, score_heldout


def lexical_coverage(words, key, lexicon):
    mapped = [''.join(key.get(c, '?') for c in word) for word in words]
    matches = sum(word in lexicon for word in mapped)
    complete = sum('?' not in word for word in mapped)
    return {'tokens': len(words), 'fully_mapped_tokens': complete,
            'reference_vocabulary_hits': matches,
            'reference_vocabulary_hit_rate': matches / len(words) if words else None}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--language', choices=['latin_llct', 'italian_old'], required=True)
    parser.add_argument('--source', choices=['ZL3b-n.txt', 'IT2a-n.txt'], default='ZL3b-n.txt')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--iterations', type=int, default=2000)
    parser.add_argument('--restarts', type=int, default=8)
    args = parser.parse_args()
    key_path = args.output.with_suffix('.keys.json')
    if args.output.exists() or key_path.exists():
        parser.error('A result or key file exists. Select a new output path.')
    data = load_reference_partitions(ROOT)[args.language]
    model = fit_language_model(data['words']['train'], order=3,
                               add_alpha=0.1, alphabet=string.ascii_lowercase)
    lexicon = set(data['words']['train'])
    source_path = ROOT / 'data/raw' / args.source
    manifest_path = ROOT / 'data/source_manifest.json'
    source_manifest = json.loads(manifest_path.read_text())
    expected_source = next(entry['sha256'] for entry in source_manifest['sources']
                           if entry['path'] == f'data/raw/{args.source}')
    source_hash = hashlib.sha256(source_path.read_bytes()).hexdigest()
    if source_hash != expected_source:
        raise ValueError('The manuscript source does not match its pinned hash.')
    partitions = {split: [] for split in ['train', 'validation', 'test']}
    group_manifest = {}
    reasons = ['not_paragraph', 'no_accepted_tokens', 'excluded_tokens',
               'diagram_interruption', 'eligible']
    filter_counts = {reason: {'records': 0, 'accepted_words': 0,
                             'excluded_tokens': 0} for reason in reasons}
    for record in parse_ivtff(source_path, uncertain_spaces='split'):
        if not record['kind'].startswith('P'):
            reason = 'not_paragraph'
        elif not record['tokens']:
            reason = 'no_accepted_tokens'
        elif record['excluded_tokens']:
            reason = 'excluded_tokens'
        elif any(marker in record['text_raw'] for marker in ['<->', '<~>']):
            reason = 'diagram_interruption'
        else:
            reason = 'eligible'
        filter_counts[reason]['records'] += 1
        filter_counts[reason]['accepted_words'] += len(record['tokens'])
        filter_counts[reason]['excluded_tokens'] += record['excluded_tokens']
        if reason != 'eligible':
            continue
        group = group_id(record['folio'])
        split = split_name(split_bucket(group))
        group_manifest[group] = split
        partitions[split].extend(record['tokens'])
    if any(not words for words in partitions.values()):
        raise ValueError('Every partition must contain eligible words.')
    shuffled = {}
    for index, (split, words) in enumerate(partitions.items()):
        rng = random.Random(408 + index)
        shuffled[split] = []
        for word in words:
            units = list(word)
            rng.shuffle(units)
            shuffled[split].append(''.join(units))
    config = {'iterations': args.iterations, 'restarts': args.restarts,
              'seed': 408, 'start_temperature': 0.02}
    fits = {}
    for name, sample in [('observed', partitions), ('within_word_shuffle', shuffled)]:
        print(f'{args.language}/{args.source}: fit {name}', flush=True)
        fits[name] = search_substitution(sample['train'], model, **config)
    key_record = {'selection': 'Lowest training objective only; no validation or test key selection.',
                  'keys': {name: fit['key'] for name, fit in fits.items()}}
    key_bytes = (json.dumps(key_record, sort_keys=True, indent=2) + '\n').encode()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    key_path.write_bytes(key_bytes)
    report = {
        'status': 'exploratory_search_not_a_translation',
        'language': args.language, 'source': args.source,
        'source_sha256': source_hash,
        'source_manifest_sha256': hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        'parser': {'uncertain_spaces': 'split', 'paragraph_kind_prefix': 'P',
                   'policy': 'Complete nonempty paragraph loci without excluded tokens or diagram interruptions.'},
        'sample_filter': {'sequential_categories': reasons, 'counts': filter_counts,
                          'limit': 'Complete-line selection can change the distribution of accepted words.'},
        'reference_metadata': data['metadata'], 'grouping': grouping_config(),
        'shuffle': {'unit': 'raw EVA code point', 'within_word': True,
                    'preserves': ['word count', 'word order', 'word lengths', 'character multiset per word'],
                    'partition_seeds': {'train': 408, 'validation': 409, 'test': 410},
                    'generator': 'Python random.Random, one sequential shuffle per word'},
        'group_manifest': dict(sorted(group_manifest.items())),
        'sample_words': {split: len(words) for split, words in partitions.items()},
        'key_record_sha256': hashlib.sha256(key_bytes).hexdigest(),
        'key_frozen_before_test_scoring': True, 'fits': fits, 'scores': {},
        'limits': [
            'This search uses raw EVA units and fixed split-policy word boundaries.',
            'The language model uses within-word characters only. Word permutation leaves its objective unchanged.',
            'The known-cipher trials calibrate search power. They do not establish the manuscript encoding or language.',
            'One unit-shuffle trial is not a false-positive-rate estimate.',
            'A failed heuristic search does not exhaust all possible keys.',
            'These manuscript data have been inspected in prior exploratory analyses.',
        ],
    }
    domain = sorted({c for word in partitions['train'] for c in word})
    identity = {c: c for c in domain}
    for split, words in partitions.items():
        report['scores'][split] = {
            'observed': score_heldout(words, model, fits['observed']['key']),
            'observed_lexicon': lexical_coverage(words, fits['observed']['key'], lexicon),
            'shuffled': score_heldout(shuffled[split], model, fits['within_word_shuffle']['key']),
            'shuffled_lexicon': lexical_coverage(shuffled[split], fits['within_word_shuffle']['key'], lexicon),
            'identity': score_heldout(words, model, identity),
        }
        for name in ['observed', 'shuffled', 'identity']:
            report['scores'][split][name]['evaluation_split'] = split
    random_scores = []
    rng = random.Random(409)
    for _ in range(32):
        letters = list(string.ascii_lowercase)
        rng.shuffle(letters)
        key = dict(zip(domain, letters))
        random_scores.append(score_heldout(partitions['test'], model, key)['bits_per_symbol'])
    report['random_key_test_baseline'] = {'seed': 409, 'scores_bits_per_symbol': random_scores,
                                         'minimum': min(random_scores), 'maximum': max(random_scores)}
    report['code_sha256'] = {
        str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in [Path(__file__), *(ROOT / 'src/voynich' / name for name in
                     ['corpus.py', 'reference.py', 'substitution.py', 'groups.py'])]
    }
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps(report['scores']['test'], indent=2), flush=True)
    print(args.output, flush=True)


if __name__ == '__main__':
    main()
