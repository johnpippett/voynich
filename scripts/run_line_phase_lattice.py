#!/usr/bin/env python3
"""Check fixed line phases with the unchanged training selection."""
from collections import Counter
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'src'), str(ROOT / 'scripts')]
from experiments.homophonic.units import units
from voynich.corpus import parse_ivtff
from voynich.groups import group_id, split_bucket, split_name

LOCUS = re.compile(r'^[A-Za-z][A-Za-z0-9]*\.([0-9]+),([@+*=&~/!])')
FREE_COMMENT = re.compile(r'<![^>]*>')
CONTROL = re.compile(r'<(?:%|\$|@[A-Z]=[A-Za-z0-9@])>')
WORDS = re.compile(r'[a-z]+(?:\.[a-z]+)*')
FROZEN_FILES = frozenset((
    'docs/plans/line-phase-lattice-v1.md',
    'scripts/run_line_phase_lattice.py', 'scripts/line_phase_lattice.py',
    'scripts/check_line_phase_lattice.py', 'scripts/check_line_phase_freeze.py',
    'scripts/verify_line_phase_sources.py', 'src/voynich/__init__.py',
    'src/voynich/corpus.py', 'src/voynich/groups.py',
    'experiments/homophonic/units.py', 'data/bifolio_manifest.json',
    'data/source_manifest.json', 'reports/line-triplet-boundary-certificates.json',
))
SOURCE_PATHS = {'ZL': 'data/raw/ZL3b-n.txt', 'IT': 'data/raw/IT2a-n.txt'}
TRACKS = {('A', 'visual'), ('B', 'visual'), ('A', 'raw'), ('B', 'raw')}


def object_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_new(path, value):
    with path.open('x') as handle:
        json.dump(value, handle, sort_keys=True, indent=2, allow_nan=False)
        handle.write('\n')


def select(records):
    """Apply the earlier line rules without changes."""
    selected, excluded = [], Counter()
    for index, record in enumerate(records):
        reason = None
        current = LOCUS.match(record['locus'])
        following = records[index + 1] if index + 1 < len(records) else None
        after = LOCUS.match(following['locus']) if following else None
        if record['kind'] not in {'P0', 'P1'}:
            reason = 'non_paragraph_kind'
        elif record['metadata'].get('L') not in {'A', 'B'}:
            reason = 'missing_class'
        elif current is None or current[2] not in {'+', '*'}:
            reason = 'current_locator'
        elif following is None or following['folio'] != record['folio']:
            reason = 'no_next_on_folio'
        elif after is None or int(after[1]) != int(current[1]) + 1:
            reason = 'nonconsecutive_next_locus'
        elif after[2] not in {'+', '*'}:
            reason = 'next_locator'
        elif record.get('excluded_tokens', 0):
            reason = 'parser_rejection'
        else:
            clean = CONTROL.sub('', FREE_COMMENT.sub('', record['text_raw']))
            words = tuple(clean.split('.'))
            if WORDS.fullmatch(clean) is None:
                reason = 'strict_spelling'
            elif len(words) < 3:
                reason = 'fewer_than_three_words'
            elif tuple(record['tokens']) != words:
                reason = 'parser_word_mismatch'
        if reason:
            excluded[reason] += 1
            continue
        group = group_id(record['folio'])
        selected.append(dict(words=words, L=record['metadata']['L'],
            split=split_name(split_bucket(group)), reference=dict(
                folio=record['folio'], locus=record['locus'], group=group,
                source_record_index=index, next_locus=following['locus'],
                next_kind=following['kind'], word_count=len(words),
                line_sha256=object_hash(words))))
    return selected, dict(sorted(excluded.items()))


def counts(line, representation):
    return Counter(unit for word in line['words'] for unit in units(word, representation=representation))


def run(freeze_path, output):
    freeze = json.loads(freeze_path.read_text())
    if not isinstance(freeze.get('files'), dict) or set(freeze['files']) != FROZEN_FILES:
        raise ValueError('Incomplete or unexpected freeze file set')
    if freeze.get('schema') != 'line-phase-lattice-freeze-v1':
        raise ValueError('Unexpected freeze schema')
    if not isinstance(freeze.get('sources'), dict) or set(freeze['sources']) != set(SOURCE_PATHS):
        raise ValueError('Incomplete or unexpected frozen sources')
    for name, path in SOURCE_PATHS.items():
        if freeze['sources'][name].get('path') != path:
            raise ValueError('Unexpected source path')
    for name, expected in freeze['files'].items():
        if file_hash(ROOT / name) != expected:
            raise ValueError('Frozen file differs: ' + name)
    for pin in freeze['sources'].values():
        if file_hash(ROOT / pin['path']) != pin['sha256']:
            raise ValueError('Source hash differs: ' + pin['path'])
    baseline = json.loads((ROOT / 'reports/line-triplet-boundary-certificates.json').read_text())
    if len(baseline['sources']) != 2 or {s['source'] for s in baseline['sources']} != set(SOURCE_PATHS):
        raise ValueError('Incomplete baseline sources')
    for prior in baseline['sources']:
        if len(prior['tracks']) != 4 or {(t['L'], t['representation']) for t in prior['tracks']} != TRACKS:
            raise ValueError('Incomplete baseline tracks')
    output.mkdir(parents=True, exist_ok=False)
    result = dict(schema='line-phase-lattice-study-v1', freeze_sha256=file_hash(freeze_path), sources=[])
    for source, pin in freeze['sources'].items():
        prior = next(s for s in baseline['sources'] if s['source'] == source)
        if prior['source_sha256'] != pin['sha256']:
            raise ValueError('Baseline source differs')
        selected, excluded = select(parse_ivtff(ROOT / pin['path'], uncertain_spaces='split'))
        if len(selected) != prior['selected_lines'] or excluded != prior['exclusion_counts']:
            raise ValueError('Baseline line selection differs')
        source_result = dict(source=source, source_sha256=pin['sha256'],
                             selected_lines=len(selected), exclusion_counts=excluded, tracks=[])
        for previous in prior['tracks']:
            label, representation = previous['L'], previous['representation']
            lines = [x for x in selected if x['L'] == label and x['split'] == 'train']
            references = [line['reference'] for line in lines]
            unit_counts = [counts(line, representation) for line in lines]
            alphabet = sorted({unit for row in unit_counts for unit in row})
            rows = [[row[unit] for unit in alphabet] + [len(line['words']) - 1, 1]
                    for row, line in zip(unit_counts, lines)]
            reduced = sorted({tuple(value % 3 for value in row) for row in rows})
            old = previous['stages']['train']
            if (alphabet != previous['alphabet'] or len(lines) != old['selected_lines']
                    or object_hash(references) != old['selection_sha256']
                    or object_hash(reduced) != old['matrix_sha256']):
                raise ValueError('Baseline training track differs')
            from line_phase_lattice import build_certificate
            certificate = build_certificate(rows)
            support = certificate.get('support_indices', [])
            certificate['source_references'] = [references[i] for i in support]
            certificate['source'] = source
            certificate['source_sha256'] = pin['sha256']
            certificate['L'] = label
            certificate['representation'] = representation
            certificate['alphabet'] = alphabet
            certificate['space_column'] = len(alphabet)
            certificate['line_contribution_column'] = len(alphabet) + 1
            name = f'{source}-{label}-{representation}.json'
            write_new(output / name, certificate)
            track = dict(L=label, representation=representation, alphabet=alphabet,
                         training_lines=len(lines), columns=len(alphabet) + 2,
                         selection_sha256=object_hash(references),
                         integer_matrix_sha256=object_hash(rows),
                         prior_modulo_three_matrix_sha256=object_hash(reduced),
                         status=certificate['status'], support_rows=len(support),
                         certificate_file=name, certificate_sha256=file_hash(output / name))
            source_result['tracks'].append(track)
            print(source, label, representation, certificate['status'], flush=True)
        result['sources'].append(source_result)
    write_new(output / 'result.json', result)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--freeze', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    run(args.freeze, args.output)
