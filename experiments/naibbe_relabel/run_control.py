"""Check known keys on spans from the fixed Naibbe inverse.

The command uses no manuscript input. It keeps source text and detailed
control records in the selected output directory.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import random
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
from voynich.naibbe import (ForwardConfig, WEIGHTS_52, encrypt_fixed,
                           load_table_csv, normalize_plaintext)
from voynich.reference import load_reference_partitions
from voynich.substitution import (fit_language_model, score_with_key,
                                  search_substitution)

TABLE_SHA256 = '4e7cfd54b7ec66515d39a51e11ec97e8e19b643b0b189124eebc3982e707dcec'
REFERENCE_MANIFEST_SHA256 = 'f261b781f150991e3305aae5057a94dc91afd8e59c58bb22ff199347f5ce3e6d'
ALPHABET = 'abcdefghilmnopqrstuvxyz'
KEY_SEEDS = (408, 409, 410, 411)


def save(path, value):
    """Write one new JSON record."""
    with Path(path).open('x', encoding='utf-8') as handle:
        json.dump(value, handle, indent=2, ensure_ascii=False)
        handle.write('\n')


def blocks(text):
    return [text[start:start + 64] for start in range(0, len(text), 64)]


def extract_spans(token_blocks, book, minimum=8):
    """Keep unique candidate runs without connections across exclusions."""
    spans, rows = [], []
    excluded = {'ambiguous': 0, 'no_parse': 0}
    short_runs = 0
    for block_index, tokens in enumerate(token_blocks):
        run = ''
        for token_index, token in enumerate(tokens):
            candidates = book.candidates(token)
            rows.append({'block': block_index, 'token_index': token_index,
                         **candidates.to_dict()})
            if len(candidates.plaintexts) == 1:
                run += candidates.plaintexts[0]
                continue
            excluded['no_parse' if not candidates.plaintexts else 'ambiguous'] += 1
            if len(run) >= minimum:
                spans.append(run)
            elif run:
                short_runs += 1
            run = ''
        if len(run) >= minimum:
            spans.append(run)
        elif run:
            short_runs += 1
    return {'spans': spans, 'excluded_tokens': excluded, 'short_runs': short_runs,
            'kept_characters': sum(map(len, spans)), 'blocks': len(token_blocks),
            'candidate_records': rows}


def encode_blocks(text_blocks, book, known_key, key_seed, test=False):
    inverse = {plain: logical for logical, plain in known_key.items()}
    config = ForwardConfig(weights=WEIGHTS_52, respacing_numerator=17,
                           respacing_denominator=36,
                           collision_policy='unigram', normalize=False)
    outputs = []
    for index, text in enumerate(text_blocks):
        logical = ''.join(inverse[char] for char in text)
        seed = 100000 + 1000 * key_seed + index + (500000 if test else 0)
        encoded = encrypt_fixed(logical, book, config=config, seed=seed)
        assert encoded.normalized_text == logical
        for emission in encoded.emissions:
            assert emission.plaintext_unit in book.candidates(emission.token).plaintexts
        outputs.append(encoded.to_dict())
    return outputs


def recovery(spans, fitted, known):
    observed = sorted(set(''.join(spans)))
    unmapped = sum(char not in fitted for span in spans for char in span)
    errors = sum(fitted.get(char) != known[char] for span in spans for char in span)
    total = sum(map(len, spans))
    return {'characters': total, 'errors': errors, 'unmapped_characters': unmapped,
            'observed_symbols': observed,
            'correct_observed_assignments': sum(fitted.get(c) == known[c] for c in observed),
            'observed_assignment_count': len(observed),
            'exact': total > 0 and errors == 0 and unmapped == 0}


def run_controls(output, book):
    digest = hashlib.sha256((ROOT / 'data/reference_manifest.json').read_bytes()).hexdigest()
    if digest != REFERENCE_MANIFEST_SHA256:
        raise ValueError('Reference manifest SHA-256 mismatch.')
    output.mkdir(parents=True, exist_ok=False)
    reference = load_reference_partitions(ROOT)['latin_llct']
    streams = {split: ''.join(normalize_plaintext(word) for word in words)
               for split, words in reference['words'].items()}
    assert all(set(text) <= set(ALPHABET) for text in streams.values())
    save(output / 'source-record.json', {
        'reference': reference['metadata'], 'table_sha256': TABLE_SHA256,
        'stream_sha256': {k: hashlib.sha256(v.encode()).hexdigest() for k, v in streams.items()},
        'stream_characters': {k: len(v) for k, v in streams.items()},
        'limit': 'These are normalized reference streams with original spaces removed.',
    })
    model = fit_language_model(blocks(streams['train']), order=3, add_alpha=0.1,
                               alphabet=ALPHABET)
    save(output / 'language-model.json', model.to_dict())
    summaries = []
    for key_seed in KEY_SEEDS:
        started = time.monotonic()
        shuffled = list(ALPHABET)
        random.Random(key_seed).shuffle(shuffled)
        known = dict(zip(ALPHABET, shuffled))
        encoded_fit = encode_blocks(blocks(streams['validation'][:8192]), book, known, key_seed)
        fit_inputs = extract_spans([row['tokens'] for row in encoded_fit], book)
        save(output / f'fit-inputs-{key_seed}.json',
             {'encoded': encoded_fit, 'extraction': fit_inputs})
        symbols = set(''.join(fit_inputs['spans']))
        if fit_inputs['kept_characters'] < 1024 or len(symbols) < 15:
            summary = {'key_seed': key_seed, 'status': 'insufficient_input',
                       'fit_characters': fit_inputs['kept_characters'],
                       'fit_symbols': len(symbols), 'passes': False}
            save(output / f'result-{key_seed}.json', summary)
            summaries.append(summary)
            print(json.dumps(summary), flush=True)
            continue
        fitted = search_substitution(
            fit_inputs['spans'], model, iterations=2000, restarts=8, seed=408,
            start_temperature=0.02, reference_key=None,
        )
        save(output / f'frozen-fit-{key_seed}.json', fitted)
        encoded_test = encode_blocks(blocks(streams['test'][:8192]), book, known, key_seed, test=True)
        test_inputs = extract_spans([row['tokens'] for row in encoded_test], book)
        save(output / f'test-inputs-{key_seed}.json',
             {'encoded': encoded_test, 'extraction': test_inputs})
        result = {
            'key_seed': key_seed, 'status': fitted['status'],
            'known_logical_to_real_key': known, 'fitted_key': fitted['key'],
            'fit_input_characters': fit_inputs['kept_characters'],
            'test_input_characters': test_inputs['kept_characters'],
            'fit_source_characters': sum(len(row['normalized_text']) for row in encoded_fit),
            'test_source_characters': sum(len(row['normalized_text']) for row in encoded_test),
            'fit_excluded_tokens': fit_inputs['excluded_tokens'],
            'test_excluded_tokens': test_inputs['excluded_tokens'],
            'fit_short_runs': fit_inputs['short_runs'],
            'test_short_runs': test_inputs['short_runs'],
            'fit_span_lengths': dict(sorted(Counter(map(len, fit_inputs['spans'])).items())),
            'test_span_lengths': dict(sorted(Counter(map(len, test_inputs['spans'])).items())),
            'fit_recovery': recovery(fit_inputs['spans'], fitted['key'], known),
            'test_recovery': recovery(test_inputs['spans'], fitted['key'], known),
            'fit_known_key_score': score_with_key(fit_inputs['spans'], model, known),
            'fit_found_key_score': score_with_key(fit_inputs['spans'], model, fitted['key']),
            'test_known_key_score': score_with_key(test_inputs['spans'], model, known),
            'test_found_key_score': score_with_key(test_inputs['spans'], model, fitted['key']),
            'elapsed_seconds': time.monotonic() - started,
            'analysis_boundary': 'The scorer token boundaries are selected spans, not original word boundaries.',
        }
        result['fit_selected_fraction'] = result['fit_input_characters'] / result['fit_source_characters']
        result['test_selected_fraction'] = result['test_input_characters'] / result['test_source_characters']
        result['full_label_coverage'] = (
            set(result['fit_recovery']['observed_symbols']) == set(ALPHABET)
            and set(result['test_recovery']['observed_symbols']) == set(ALPHABET)
        )
        result['complete_key_equal'] = fitted['key'] == known
        result['passes'] = (result['full_label_coverage']
                            and result['complete_key_equal']
                            and result['test_recovery']['exact'])
        save(output / f'result-{key_seed}.json', result)
        summary = {k: result[k] for k in ('key_seed', 'status', 'fit_input_characters',
                   'test_input_characters', 'fit_source_characters', 'test_source_characters',
                   'fit_selected_fraction', 'test_selected_fraction',
                   'fit_recovery', 'test_recovery', 'full_label_coverage',
                   'complete_key_equal', 'passes')}
        summaries.append(summary)
        print(json.dumps(summary), flush=True)
    save(output / 'summary.json', {
        'controls': summaries, 'all_pass': all(row['passes'] for row in summaries),
        'manuscript_inputs_read': False,
        'limit': 'These controls cannot validate a manuscript key or translation.',
    })


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixture', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('The output path exists.')
    book = load_table_csv(ROOT / 'data/raw/naibbe/naibbe-cipher/references/naibbe_tables.csv',
                          expected_sha256=TABLE_SHA256)
    assert ''.join(book.alphabet) == ALPHABET
    if args.fixture:
        fixture = json.loads(args.fixture.read_text())
        result = extract_spans(fixture['blocks'], book, fixture['minimum_characters'])
        save(args.output, result)
    else:
        run_controls(args.output, book)


if __name__ == '__main__':
    main()
