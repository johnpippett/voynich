"""Examine fixed decoder rules and the target data in a word prompt."""
import ast
import hashlib
import json
from pathlib import Path
import re
import sys

PINS = {
    'full_decode.py': 'c20f552a83ca8b6b619a182bedd43bafbc982cdc627bbbba9152c24552fbe3d6',
    'crib_attack.py': 'd3b3453689178064d91a49f06f102ac76c331c81f2293e8ff7e8884542de2d15',
}
PLAN_SHA = 'f27fffdd3a4c385817142ef7083fa2d46256e07944d5c45a5a6659cc1a71a7da'
CASES = [('qoa', 'y', 0), ('qa', 'y', 0), ('oa', 'yw', 0),
         ('an', 'by', 0), ('ar', 'sy', 0), ('aii', 'sy', 0),
         ('aiii', 'rhy', 0), ('ach', 'ky', 0), ('az', '?y', 1),
         ('q', '?', 1), ('qo', '', 0)]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def literals(tree, names):
    found = {}
    for node in tree.body:
        target = None
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
        elif isinstance(node, ast.AnnAssign):
            target = node.target
        if isinstance(target, ast.Name) and target.id in names:
            if target.id in found:
                raise ValueError('Duplicate constant: ' + target.id)
            found[target.id] = ast.literal_eval(node.value)
    if set(found) != set(names):
        raise ValueError('Missing selected constant')
    return found


def functions(tree, names, namespace):
    selected = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
    if len(selected) != len(names) or {n.name for n in selected} != set(names):
        raise ValueError('Missing or duplicate selected function')
    if any(n.decorator_list for n in selected):
        raise ValueError('Unexpected decorator')
    code = compile(ast.Module(body=selected, type_ignores=[]), '<selected-source>', 'exec')
    exec(code, namespace)


def main():
    if len(sys.argv) != 4:
        raise SystemExit('Supply source directory, plan, and new output path.')
    source_dir, plan, output = map(Path, sys.argv[1:])
    if output.exists():
        raise SystemExit('Output already exists.')
    if digest(plan.read_bytes()) != PLAN_SHA:
        raise SystemExit('Plan hash mismatch.')
    raw = {name: (source_dir / name).read_bytes() for name in PINS}
    for name, data in raw.items():
        if digest(data) != PINS[name]:
            raise SystemExit('Source hash mismatch: ' + name)
    trees = {name: ast.parse(data) for name, data in raw.items()}
    constants = ['FULL_MAPPING', 'II_HEBREW', 'I_HEBREW', 'CH_HEBREW',
                 'INITIAL_D_HEBREW', 'INITIAL_H_HEBREW', 'DIRECTION']
    decoder = literals(trees['full_decode.py'], constants)
    decoder.update({'re': re, 'HEBREW_TO_ITALIAN': {}})
    functions(trees['full_decode.py'], ['preprocess_eva', 'decode_word'], decoder)
    cases = []
    for word, expected, unknown in CASES:
        _, actual, actual_unknown = decoder['decode_word'](word)
        cases.append({'input': word, 'expected': expected, 'actual': actual,
                      'expected_unknown': unknown, 'actual_unknown': actual_unknown,
                      'passed': (actual, actual_unknown) == (expected, unknown)})
    prompt_env = literals(trees['crib_attack.py'], ['SECTION_NAMES', 'SECTION_PROMPTS'])
    prompt_env['_DEFAULT_SECTION'] = prompt_env['SECTION_PROMPTS']['H']
    functions(trees['crib_attack.py'], ['build_wordlevel_prompt'], prompt_env)
    target = {'position': 7, 'eva': 'an', 'hebrew': 'by', 'length': 2,
              'context_str': 'context-alpha'}
    render = lambda t: prompt_env['build_wordlevel_prompt']([t], 'herbal', n_candidates=2)
    prompt = render(target)
    changed_word = render(dict(target, hebrew='sy'))
    changed_context = render(dict(target, context_str='context-beta'))
    checks = {
        'target_decode_in_prompt': "Current decode: 'by'" in prompt,
        'target_position_and_length_in_prompt': 'WORD 7 — 2 Hebrew consonants' in prompt,
        'context_in_prompt': 'context-alpha' in prompt,
        'target_only_change_matches': changed_word == prompt.replace("Current decode: 'by'", "Current decode: 'sy'"),
        'context_only_change_matches': changed_context == prompt.replace('context-alpha', 'context-beta'),
    }
    result = {'schema_version': 1, 'plan_sha256': PLAN_SHA,
              'script_sha256': digest(Path(__file__).read_bytes()), 'source_sha256': PINS,
              'decoder_cases': cases, 'prompt_checks': checks,
              'prompt_sha256': digest(prompt.encode()),
              'changed_word_prompt_sha256': digest(changed_word.encode()),
              'changed_context_prompt_sha256': digest(changed_context.encode()),
              'scope': 'Artificial inputs; Hebrew output and prompt construction only. No manuscript, API, generated candidate, or translation test.'}
    result['passed'] = all(c['passed'] for c in cases) and all(checks.values())
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'passed': result['passed'], 'decoder_cases': len(cases), 'prompt_checks': len(checks)}))
    if not result['passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
