"""Command-line entry points for saved research runs."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import tempfile

from . import __version__


ROOT = Path(__file__).resolve().parents[2]


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify_hashes(root, manifest):
    checks = []
    for entry in manifest['sources']:
        path = Path(root) / entry['path']
        actual = sha256(path) if path.is_file() else None
        checks.append({'path': entry['path'], 'expected': entry['sha256'],
                       'actual': actual, 'matches': actual == entry['sha256']})
    return checks


def _report(result):
    inv = result['structure']['inventory']
    text = [
        '# Voynich structural analysis', '',
        '**Status: exploratory research. The manuscript is not deciphered by this project.**', '',
        f"Source: `{result['provenance']['source_path']}`.",
        f"SHA-256: `{result['provenance']['source_sha256']}`.", '',
        f"Spacing policy: `{result['config']['uncertain_spaces']}`.",
        f"Accepted tokens: {inv['tokens']:,}. Excluded tokens: {inv['excluded_tokens']:,}.",
        f"Locations: {inv['records']:,}. Folio surfaces: {inv['folios']}.", '',
        '## Descriptive results', '',
        '| Measure | Value |', '| --- | ---: |',
        f"| Distinct accepted tokens | {inv['types']:,} |",
        f"| Character entropy | {inv['h1_bits_per_eva_character']:.4f} bits |",
        f"| Conditional entropy per within-word transition | {inv['h2_bits_per_within_word_transition']:.4f} bits |", '',
        'These estimates use EVA characters. EVA characters are not established linguistic units.',
        'These measurements do not identify a language or establish meaning.', '',
        '## Word-order tests', '',
        f"Eligible lines: {result['structure']['word_order_sample']['lines']:,}.",
        'Each null sample permutes words within each eligible line.',
        'The sample excludes uncertain tokens, diagram interruptions, labels, and lines with fewer than three words.', '',
        '| Measure | Observed | Null expectation | Effect | p | Holm p |',
        '| --- | ---: | ---: | ---: | ---: | ---: |',
    ]
    for name, row in result['structure']['word_order_tests'].items():
        text.append(f"| {name} | {row['observed']:.6f} | {row['null_expectation']:.6f} | {row['effect']:.6f} | {row['p_value']:.5f} | {row['holm_p_value']:.5f} |")
    text.extend([
        '', 'Initial gallows means an initial EVA character from `k`, `t`, `p`, or `f`.',
        'Initial length difference compares the first word with the mean of other words in each line.',
        'Adjacent near words have Levenshtein edit distance at most one, including equal words.',
        'A small p-value rejects only the specified null model.',
        'Language, encoding rules, and copying procedures can all produce structured text.', '',
        '## Character and word prediction', '',
        'The machine-readable results contain all model scores, sample counts, and split assignments.',
        'Models train on separate, conservative folio groups.',
        'The grouping joins the confirmed 85/86 foldout and the declared candidate groups.',
        'A complete physical-sheet map has not been established.',
        'The alphabet and vocabulary come from the training partition.',
        'Character models compare raw EVA with a declared compound grouping.',
        'Character nulls shuffle characters. Compound-unit nulls shuffle the declared units.',
        'Bit rates for different symbol units are not directly comparable.',
        'Character models retain certain words from lines that also contain rejected words.',
        'Word-context models exclude those incomplete lines to preserve adjacency.',
        'Word models compare the previous-word model with a unigram and a shuffled-training control.',
        'A lower prediction loss measures statistical structure. It does not verify a translation.', '',
        '## Reproduction', '',
        'The run configuration and code hashes are in `analysis.json`.',
        'The parsed source records are in `records.jsonl`.',
        'The output file hashes are in `SHA256SUMS`.',
        'Source documentation and research limitations are in the project `docs/research` directory.', '',
    ])
    return '\n'.join(text)


def run(args):
    output = Path(args.output).resolve()
    if output.exists():
        raise FileExistsError(f'Result directory already exists: {output}. Select a new directory.')
    from .corpus import parse_ivtff
    from .predictive import run_predictive
    from .context import run_context
    from .structure import run_structure

    source = Path(args.source).resolve()
    records = parse_ivtff(source, uncertain_spaces=args.uncertain_spaces)
    if args.transcriber:
        records = [r for r in records if r['transcriber'] == args.transcriber]
    if len({r['transcriber'] for r in records}) > 1:
        raise ValueError('Multiple transcribers found. Select one with --transcriber.')
    if not records:
        raise ValueError('No records remain for this source and transcriber.')
    paragraphs = [r for r in records if r['kind'].startswith('P')]
    result = {
        'status': 'exploratory_not_deciphered',
        'provenance': {
            'source_path': str(source), 'source_sha256': sha256(source),
            'created_utc': datetime.now(timezone.utc).isoformat(),
            'python': platform.python_version(), 'package_version': __version__,
            'code_sha256': {str(p.relative_to(ROOT)): sha256(p) for p in sorted((ROOT / 'src').rglob('*.py'))},
            'design_sha256': sha256(ROOT / 'docs/plans/design.md'),
        },
        'config': {'seed': args.seed, 'permutations': args.permutations, 'bootstraps': args.bootstraps,
                   'uncertain_spaces': args.uncertain_spaces, 'transcriber': args.transcriber,
                   'predictive_sample': 'Accepted tokens from paragraph loci; labels excluded; certain words from incomplete lines retained.'},
        'structure': run_structure(records, permutations=args.permutations, seed=args.seed),
        'predictive': run_predictive(paragraphs, seed=args.seed),
        'context': run_context(records, seed=args.seed, bootstraps=args.bootstraps),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.voynich-run-', dir=output.parent) as temporary:
        staging = Path(temporary) / 'payload'
        staging.mkdir()
        (staging / 'analysis.json').write_text(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + '\n', encoding='utf-8')
        (staging / 'records.jsonl').write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in records), encoding='utf-8')
        (staging / 'REPORT.md').write_text(_report(result), encoding='utf-8')
        (staging / 'SHA256SUMS').write_text(''.join(f'{sha256(p)}  {p.name}\n' for p in sorted(staging.iterdir())), encoding='utf-8')
        if output.exists():
            raise FileExistsError(f'Result directory appeared during analysis: {output}')
        os.rename(staging, output)
    print(f'Research results: {output}')
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description='Reproducible Voynich structural research. No translation is assumed.')
    commands = parser.add_subparsers(dest='command', required=True)
    analysis = commands.add_parser('run', help='Run the fixed structural experiments.')
    analysis.add_argument('--source', default=str(ROOT / 'data/raw/ZL3b-n.txt'))
    analysis.add_argument('--output', default=str(ROOT / 'results' / datetime.now(timezone.utc).strftime('run-%Y%m%dT%H%M%S%fZ')))
    analysis.add_argument('--uncertain-spaces', choices=['split', 'join'], default='split')
    analysis.add_argument('--transcriber')
    analysis.add_argument('--seed', type=int, default=408)
    analysis.add_argument('--permutations', type=int, default=499)
    analysis.add_argument('--bootstraps', type=int, default=499)
    verification = commands.add_parser('verify-sources', help='Check downloaded corpus hashes.')
    verification.add_argument('--manifest', default=str(ROOT / 'data/source_manifest.json'))
    args = parser.parse_args(argv)
    if args.command == 'run':
        return run(args)
    checks = verify_hashes(ROOT, json.loads(Path(args.manifest).read_text(encoding='utf-8')))
    print(json.dumps(checks, indent=2))
    return 0 if checks and all(c['matches'] for c in checks) else 1


if __name__ == '__main__':
    raise SystemExit(main())
