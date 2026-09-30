"""Check the complete substitution command with small artificial inputs."""
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
RUNNER = Path(__file__).with_name('run_control.py')
FIXTURE = {
    'alphabet': 'ab',
    'train': 'aaab',
    'fit_plaintext': 'aaabaaab',
    'test_plaintext': 'aabb',
    'known_key': {'a': 'b', 'b': 'a'},
}


def direct_cost(text):
    """Calculate the fixture score independently with string counts."""
    costs = []
    for end in range(3, len(text)):
        terms = []
        for size, weight in enumerate((0.1, 0.2, 0.3, 0.4), 1):
            samples = [FIXTURE['train'][i:i + size]
                       for i in range(len(FIXTURE['train']) - size + 1)]
            counts = Counter(samples)
            gram = text[end - size + 1:end + 1]
            total = sum(value for key, value in counts.items()
                        if key[:-1] == gram[:-1])
            probability = (counts[gram] + 0.1) / (total + 0.2)
            terms.append(-weight * math.log2(probability))
        costs.append(sum(terms))
    return sum(costs)


def main():
    assert RUNNER.exists(), 'Missing space-free control command'
    with tempfile.TemporaryDirectory() as directory:
        base = Path(directory)
        fixture = base / 'fixture.json'
        fixture.write_text(json.dumps(FIXTURE) + '\n')
        output = base / 'output'
        command = [sys.executable, str(RUNNER), '--fixture', str(fixture),
                   '--output', str(output)]
        run = subprocess.run(command, cwd=base, capture_output=True, text=True)
        assert run.returncode == 0, run.stderr
        result = json.loads((output / 'result.json').read_text())
        assert result['fit_ciphertext'] == 'bbbabbba', result
        assert result['test_ciphertext'] == 'bbaa', result
        assert result['fitted_key'] == {'a': 'b', 'b': 'a'}, result
        assert result['decoded_test'] == 'aabb', result
        assert result['fit_errors'] == result['test_errors'] == 0, result
        assert result['fit_window_count'] == 5, result
        assert math.isclose(result['temperature_start'], 0.1, abs_tol=1e-15), result
        assert math.isclose(result['search']['settings']['temperature_start'], 0.1, abs_tol=1e-15), result
        expected = direct_cost('aaabaaab')
        other = direct_cost('bbbabbba')
        assert expected < other, (expected, other)
        assert math.isclose(result['fit_cost'], expected, abs_tol=1e-10), result
        frozen = json.loads((output / 'frozen-key.json').read_text())
        assert frozen['key'] == result['fitted_key'], frozen
        paired_hashes = {}
        variants = {
            'different-test': dict(FIXTURE, test_plaintext='bbbbaaaa'),
            'different-truth': dict(FIXTURE, fit_plaintext='bbbabbba',
                                   test_plaintext='bbaa',
                                   known_key={'a': 'a', 'b': 'b'}),
            'missing-fit-labels': dict(FIXTURE, alphabet='abcd',
                                      test_plaintext='aabbccdd',
                                      known_key={'a': 'b', 'b': 'a', 'c': 'd', 'd': 'c'}),
        }
        for label, variant in variants.items():
            variant_source = base / f'{label}.json'
            variant_source.write_text(json.dumps(variant) + '\n')
            variant_output = base / label
            variant_run = subprocess.run(
                [sys.executable, str(RUNNER), '--fixture', str(variant_source),
                 '--output', str(variant_output)], cwd=base, capture_output=True, text=True)
            assert variant_run.returncode == 0, variant_run.stderr
            variant_result = json.loads((variant_output / 'result.json').read_text())
            assert variant_result['fit_ciphertext'] == result['fit_ciphertext'], variant_result
            if label == 'missing-fit-labels':
                assert variant_result['missing_fit_labels'] == ['c', 'd'], variant_result
                assert variant_result['test_labels_absent_from_fit'] == ['c', 'd'], variant_result
                assert variant_result['fit_errors'] == 0, variant_result
                assert variant_result['test_ciphertext'] == 'bbaaddcc', variant_result
                predicted = ''.join(variant_result['fitted_key'][char]
                                    for char in 'bbaaddcc')
                assert variant_result['decoded_test'] == predicted, variant_result
                errors = sum(left != right for left, right in zip(predicted, 'aabbccdd', strict=True))
                assert variant_result['test_errors'] == errors, variant_result
                assert variant_result['accepted'] is (errors == 0), variant_result
            else:
                assert variant_result['fitted_key'] == result['fitted_key'], variant_result
                assert variant_result['fit_cost'] == result['fit_cost'], variant_result
            if label == 'different-truth':
                assert variant_result['fit_errors'] > 0, variant_result
                assert variant_result['test_errors'] > 0, variant_result
            paired_hashes[label] = {
                p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                for p in variant_output.iterdir() if p.is_file()}
        before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in output.iterdir() if p.is_file()}
        second = subprocess.run(command, cwd=base, capture_output=True, text=True)
        assert second.returncode != 0, 'Existing output was overwritten'
        after = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in output.iterdir() if p.is_file()}
        assert before == after, 'Existing evidence changed'
        bad = dict(FIXTURE, known_key={'a': 'a', 'b': 'a'})
        bad_source = base / 'invalid.json'
        bad_source.write_text(json.dumps(bad) + '\n')
        bad_output = base / 'invalid-output'
        invalid = subprocess.run(
            [sys.executable, str(RUNNER), '--fixture', str(bad_source),
             '--output', str(bad_output)], cwd=base, capture_output=True, text=True)
        assert invalid.returncode != 0 and not bad_output.exists(), 'Invalid permutation accepted'
        bad_freeze = base / 'bad-freeze.json'
        freeze_paths = [
            'docs/plans/spacefree-substitution-control-v1.md',
            'experiments/spacefree_substitution/score.py',
            'experiments/spacefree_substitution/run_control.py',
            'experiments/spacefree_substitution/check_e2e.py',
            'src/voynich/reference.py',
            'data/reference_manifest.json',
        ]
        hashes = {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
                  for path in freeze_paths}
        hashes['experiments/spacefree_substitution/run_control.py'] = '0' * 64
        bad_freeze.write_text(json.dumps({'schema_version': 1, 'files': hashes}) + '\n')
        freeze_output = base / 'freeze-output'
        mismatch = subprocess.run(
            [sys.executable, str(RUNNER), '--freeze', str(bad_freeze),
             '--output', str(freeze_output)], cwd=base, capture_output=True, text=True)
        assert mismatch.returncode != 0 and not freeze_output.exists(), 'Invalid freeze accepted'
        assert 'hash' in mismatch.stderr.lower() or 'mismatch' in mismatch.stderr.lower(), mismatch.stderr
        receipt = {
            'setup': 'Python standard library; run the command from any directory.',
            'command': 'python experiments/spacefree_substitution/check_e2e.py',
            'fixture': FIXTURE,
            'expected_ciphertext': ['bbbabbba', 'bbaa'],
            'expected_decoded_test': 'aabb',
            'independent_fit_cost': expected,
            'alternative_key_fit_cost': other,
            'checks': ['Known permutation and held-out plaintext are recovered.',
                       'Repeated symbols and overlapping windows give the direct score.',
                       'Context totals count only contexts with a target.',
                       'Different test plaintext leaves the fitted key and score unchanged.',
                       'Different known truth for the same ciphertext leaves the fit unchanged.',
                       'All test characters enter recovery counts, including labels absent during fitting.',
                       'Existing output is refused and unchanged.',
                       'An invalid permutation and a bad freeze create no output.'],
            'output_hashes': before,
            'paired_fixtures': variants,
            'paired_output_hashes': paired_hashes,
            'status': 'passed',
        }
        print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
