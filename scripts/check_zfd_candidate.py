#!/usr/bin/env python3
"""Run the fixed ZFD example and source audit."""

import argparse
import copy
import hashlib
import json
import re
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = Path('results/key-candidate-search-2026-09-29')
AUDIT = BASE / 'zfd-replication'
EXTERNAL = BASE / 'source-refresh'
PLAN_HASH = '2331bb8c7a5dc6df26771ec06bc33558fa34315875105e436d1dc2e09ce85b24'
PINS = {
    AUDIT / 'plan.md': PLAN_HASH,
    AUDIT / 'version-addendum.md': 'd64d337d7a379ac3e4e1ad4beada5206e8f12ef0edbca7c0a453ceb53b12381a',
    AUDIT / 'e2e-expectations.json': '408e7fc99d083431805e5149937af076d815b57b39e1bf84784ae18bc814082e',
    EXTERNAL / 'source-manifest.json': '6d62052b0ceb50246d32b2e912195e38ce1f0edaee41443515e5195b5f1958b8',
    Path('data/source_manifest.json'): '77c9f755ed47c19ccfe3ef92b7699953d5d5e9ada729492662c94154d3d2f4f1',
    Path('src/voynich/corpus.py'): '064c45794d523b5c07ea10621752e325d35709f619e0763ac6ba1561f0fa1dc2',
    EXTERNAL / 'README.md': 'e6de15a20da1496e5271b5039290dca4c2dedc617fa97647733ac03a525e6057',
    EXTERNAL / 'GETTING_STARTED.md': 'fcf7c0bf7ff3d5c4671a95278f6910d65767cbf890ebe5acb3e1ca9ef4a69dbe',
    EXTERNAL / '06_Pipelines/zfd_decoder_v2.py': 'ec2e252a9c4c8f92a2ce4af12fd8c7689857be15d27fc5efd2e82bdfc16b5f39',
    EXTERNAL / '08_Final_Proofs/Master_Key/unified_lexicon_v3.json': 'd8fbb8487806c3f9ba648f83b235a12c4e2cae78faa4e70449cc6c140ec063d2',
    EXTERNAL / 'canonical/06_Pipelines/regenerate_corpus.py': 'ebf24d65d9a4909d5954f2e5fa0725752d074119a15c2c80108f39510f276f46',
    Path('data/raw/ZL3b-n.txt'): 'bf5b6d4ac1e3a51b1847a9c388318d609020441ccd56984c901c32b09beccafc',
    Path('data/raw/IT2a-n.txt'): '7f27a8b0feed8f6de0a99900df6bf912dd1d295c38e5f830bac8b41c3f536fb5',
}
EXAMPLES = [('qokeedy', 'kostedi'), ('chedy', 'hedi'), ('shol', 'šol'), ('daiin', 'dain')]
SEQUENCE = ['qokeedy', 'dal', 'chol', 'ar', 'shedy']
SEMANTIC = {'meaning_en', 'meaning_hr', 'latin', 'latin_full', 'grammatical_function'}
COMPONENTS = ('operator', 'state', 'stem', 'suffix', 'latin_match')
UNREADABLE = re.compile(r'\?+|@[0-9]{3};')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def check(receipt, name, passed):
    receipt['checks'].append({'name': name, 'passed': bool(passed)})
    if not passed:
        raise ValueError(name)


def replace_semantics(value, labels, masked=False):
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            if key in SEMANTIC and isinstance(item, str):
                label = '<semantic>' if masked else f'OPAQUE_{len(labels) + 1:06d}'
                labels.append(label)
                result[key] = label
            else:
                result[key] = replace_semantics(item, labels, masked)
        return result
    if isinstance(value, list):
        return [replace_semantics(item, labels, masked) for item in value]
    return value


def view(word, output):
    forms = {name: word[name]['form'] if word[name] else None for name in COMPONENTS}
    exact_latin = forms['latin_match'] == output
    matched = len(output) if exact_latin else sum(len(forms[name] or '') for name in COMPONENTS[:-1])
    confidence = word['confidence']
    expected = 0.95 if exact_latin else round(matched / len(output), 2)
    if confidence != expected or matched > len(output):
        raise ValueError('Recognized-character accounting differs from decoder')
    return {'components': forms, 'residue': word['residue'], 'confidence': confidence,
            'classification': 'fully_resolved' if confidence >= 0.7 else 'partially_resolved' if confidence >= 0.3 else 'unknown',
            'code_score': {'matched_characters': matched, 'token_characters': len(output),
                           'fraction': matched / len(output), 'exact_latin_special_score': exact_latin}}


def decoder_checks(receipt, source):
    module = types.ModuleType('pinned_zfd_candidate')
    module.__file__ = str(ROOT / EXTERNAL / '06_Pipelines/zfd_decoder_v2.py')
    sys.dont_write_bytecode = True
    exec(compile(source, module.__file__, 'exec'), module.__dict__)
    check(receipt, 'source_import_without_main', module.__name__ != '__main__')
    original = module.ZFDDecoder(ROOT / EXTERNAL / '08_Final_Proofs/Master_Key/unified_lexicon_v3.json')
    labels = []
    synthetic = replace_semantics(original.lexicon, labels)
    check(receipt, 'unique_semantic_labels', len(labels) > 0 and len(labels) == len(set(labels)))
    before = json.dumps(replace_semantics(original.lexicon, [], True), ensure_ascii=False)
    after = json.dumps(replace_semantics(synthetic, [], True), ensure_ascii=False)
    check(receipt, 'only_semantic_strings_changed', before == after)
    control = copy.copy(original)
    control.lexicon = synthetic
    for attribute, key in [('operators', 'operators'), ('stems', 'stems'), ('suffixes', 'suffixes'),
                           ('latin_terms', 'latin_terms'), ('state_markers', 'state_markers')]:
        setattr(control, attribute, synthetic.get(key, {}))
    control.stats = {key: 0 for key in original.stats}
    tokens = [word for word, _ in EXAMPLES]
    results = [decoder.decode_eva_tokens(tokens) for decoder in (original, control)]
    outputs = [original.eva_to_croatian(word) for word in tokens]
    check(receipt, 'token_decoder_transliteration', results[0]['cro'].split() == outputs)
    views = [[view(word, output) for word, output in zip(result['words'], outputs)] for result in results]
    check(receipt, 'four_decompositions_per_decoder', all(len(result['words']) == 4 for result in results))
    for (token, expected), output, decomposition in zip(EXAMPLES, outputs, views[0]):
        equal = output == expected
        receipt['guide_examples'].append({'input': token, 'guide_output': expected,
                                         'observed_output': output, 'exact_match': equal, **decomposition})
        receipt['checks'].append({'name': 'guide_output:' + token, 'passed': equal})
    glosses = [[decoder.gloss_word(word) for word in result['words']]
              for decoder, result in zip((original, control), results)]
    receipt['decomposition_metrics'] = {'resolution_counters': original.stats}
    receipt['counterfactual'] = {
        'semantic_string_values_replaced': len(labels), 'semantic_label_count_unique': len(set(labels)),
        'only_semantic_strings_changed': before == after, 'all_metrics_equal': views[0] == views[1],
        'resolution_counters_equal': original.stats == control.stats,
        'transliteration_equal': results[0]['cro'] == results[1]['cro'],
        'glosses_changed_count': sum(a != b for a, b in zip(*glosses)),
        'gloss_changed': any(a != b for a, b in zip(*glosses)),
        'control_resolution_counters': control.stats,
    }
    check(receipt, 'counterfactual_metrics_equal', views[0] == views[1])
    check(receipt, 'counterfactual_counters_equal', original.stats == control.stats)


def f88r_checks(receipt, inputs):
    sys.path.insert(0, str(ROOT / 'src'))
    from voynich.corpus import parse_ivtff
    sources = []
    for name in ('ZL3b-n.txt', 'IT2a-n.txt'):
        relative = Path('data/raw') / name
        records = [row for row in parse_ivtff(ROOT / relative, uncertain_spaces='split') if row['folio'] == 'f88r']
        paragraph = [row for row in records if row['kind'] == 'P0']
        flags = [(row, ',' in row['text_raw'], bool(UNREADABLE.search(row['text_raw'])),
                  '[' in row['text_raw'] or ']' in row['text_raw'], row['excluded_tokens']) for row in paragraph]
        eligible = [row for row, *reasons in flags if not any(reasons)]
        token_loci = []
        for row in eligible:
            count = sum(row['tokens'][i:i+5] == SEQUENCE for i in range(len(row['tokens']) - 4))
            if count:
                token_loci.append({'locus': row['locus'], 'occurrences': count})
        raw_rows = [line for line in inputs[relative].decode('utf-8').splitlines() if re.match(r'^<f88r\.', line)]
        raw_loci = [{'locus': line[1:line.index('>')], 'occurrences': line.count('.'.join(SEQUENCE))}
                    for line in raw_rows if '.'.join(SEQUENCE) in line]
        sources.append({'source': name, 'f88r_records': len(records), 'raw_records': len(raw_rows),
                        'p0_lines': len(paragraph), 'eligible_p0_lines': len(eligible),
                        'eligible_tokens': sum(len(row['tokens']) for row in eligible),
                        'excluded_lines': len(paragraph) - len(eligible),
                        'excluded_tokens': sum(row['excluded_tokens'] for row in paragraph),
                        'comma_lines': sum(flag[1] for flag in flags),
                        'unreadable_marker_lines': sum(flag[2] for flag in flags),
                        'uncertain_reading_lines': sum(flag[3] for flag in flags),
                        'token_sequence_occurrences': sum(row['occurrences'] for row in token_loci),
                        'token_sequence_loci': token_loci,
                        'raw_literal_occurrences': sum(row['occurrences'] for row in raw_loci),
                        'raw_literal_loci': raw_loci})
    receipt['f88r'] = {'sources': sources,
                      'token_scope': 'Unambiguous P0 lines on f88r only, zero excluded tokens.',
                      'raw_scope': 'Direct physical f88r source records, all locus kinds, no line joining.'}
    for field in sources[0]:
        if isinstance(sources[0][field], int):
            receipt['f88r'][field] = sum(row[field] for row in sources)
    for field in ('token_sequence_loci', 'raw_literal_loci'):
        receipt['f88r'][field] = [{**item, 'source': row['source']} for row in sources for item in row[field]]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    target = ROOT / args.output
    if Path(args.output).is_absolute() or target.parent.resolve() != (ROOT / AUDIT).resolve() or target.suffix != '.json':
        parser.error('Use a repository-relative JSON path in the fixed audit directory.')
    if target.exists():
        parser.error('Output exists. Use a new output path.')
    receipt = {'schema': 'zfd-candidate-audit-v1', 'status': 'failed',
               'setup': {'runtime': sys.version.split()[0], 'decoder_main_called': False,
                         'bytecode_writes_disabled': True, 'corpus_regeneration': False},
               'command': 'python scripts/check_zfd_candidate.py --output ' + args.output,
               'plan_sha256': PLAN_HASH, 'script_sha256': digest(Path(__file__).read_bytes()),
               'source_hashes': {}, 'checks': [], 'guide_examples': [], 'decomposition_metrics': {},
               'counterfactual': {}, 'f88r': {}, 'failures': [],
               'claim_limits': ['Known guide examples are not blind validation.',
                                'Code scores do not measure translation correctness.',
                                'Equal scores do not show that meaning labels are false.',
                                'The source check uses one fixed sequence on f88r in two transcriptions.',
                                'No manuscript key, language, or translation is validated.']}
    try:
        inputs = {}
        for relative, expected in PINS.items():
            data = (ROOT / relative).read_bytes()
            actual = digest(data)
            receipt['source_hashes'][str(relative)] = actual
            check(receipt, 'hash:' + str(relative), actual == expected)
            inputs[relative] = data
        manifest = json.loads(inputs[EXTERNAL / 'source-manifest.json'])
        check(receipt, 'pinned_external_commit', manifest['commit'] == '3f030a9293b8db15dc2c7b0d0e7c703e71711f62')
        decoder_checks(receipt, inputs[EXTERNAL / '06_Pipelines/zfd_decoder_v2.py'])
        f88r_checks(receipt, inputs)
        receipt['status'] = 'completed_with_mismatch' if any(not row['exact_match'] for row in receipt['guide_examples']) else 'complete'
    except Exception as error:
        receipt['failures'].append(type(error).__name__ + ': ' + str(error).replace(str(ROOT), '<repo>'))
    with target.open('x', encoding='utf-8') as handle:
        json.dump(receipt, handle, indent=2, ensure_ascii=False)
        handle.write('\n')
    print(json.dumps({'status': receipt['status'], 'failures': receipt['failures'],
                      'receipt': args.output, 'sha256': digest(target.read_bytes())}))
    return 1 if receipt['failures'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
