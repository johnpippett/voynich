"""Check control isolation, frozen keys, and reported score arithmetic."""

from collections import Counter
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from experiments.homophonic.controls import encrypt_words, seeded_control_key
from experiments.homophonic.run_controls import run_control


class RunnerTests(unittest.TestCase):
    def test_warm_start_is_fitted_without_oracle_and_passed_only_as_incumbent(self):
        calls = []

        def annealer(cipher_words, train_words, **kwargs):
            calls.append((cipher_words, train_words, kwargs))
            symbols = sorted({unit for word in cipher_words for unit in word})
            return {'key': dict(zip(symbols, 'abcdefghijklmnopqrstuvwxyz')), 'status': 'fixture'}

        with tempfile.TemporaryDirectory() as directory, patch(
            'experiments.homophonic.anneal.anneal_homophonic', side_effect=annealer,
        ):
            result = run_control(
                {'train': ['a', 'b', 'ab', 'ba'], 'validation': ['ab', 'ba'], 'test': ['a']},
                family='cap2', seed=7000, node_budget=0, warm_start='anneal',
                anneal_options={'iterations': 3, 'restarts': 1, 'seed': 42},
                output_path=Path(directory) / 'result.json', bound_engine='bitset',
            )
            self.assertEqual(calls[0][1], ['a', 'b', 'ab', 'ba'])
            self.assertEqual(set(calls[0][2]),
                             {'plaintext_alphabet', 'capacity', 'iterations', 'restarts', 'seed'})
            self.assertEqual(result['warm_start'], 'anneal')
            self.assertIn('root search has no fixed assignments',
                          result['solver']['config']['initial_key_role'])

    def test_fit_inputs_exclude_oracle_and_test_and_key_precedes_test(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'result.json'
            key_path = output.with_suffix('.keys.json')

            class TestWords:
                def __iter__(self):
                    self_seen.append(key_path.exists())
                    return iter(['ab', 'ba'])

            self_seen = []
            seen = []

            def fitter(counts, lexicon, alphabet, **kwargs):
                seen.append((dict(counts), set(lexicon), alphabet, kwargs))
                symbols = sorted({unit for word in counts for unit in word})
                key = dict(zip(symbols, 'abcdefghijklmnopqrstuvwxyz'))
                score = sum(weight for word, weight in counts.items()
                            if ''.join(key[unit] for unit in word) in lexicon)
                return {'key': key, 'score': score, 'lower_bound': score,
                        'upper_bound': sum(counts.values()), 'feasible': True,
                        'score_certified': False, 'status': 'budget_exhausted',
                        'config': {}, 'candidate_counts': [{'private': 'word'}]}

            report = run_control(
                {'train': ['ab', 'ba', 'ab'], 'validation': ['ab', 'ab', 'ba'],
                 'test': TestWords()},
                family='injective', seed=6000, node_budget=0,
                output_path=output, fitter=fitter,
            )
            planted = seeded_control_key('injective', 6000)
            raw_counts = Counter(encrypt_words(['ab', 'ab', 'ba'], planted))
            self.assertEqual(seen[0][0], {word: n * 2 + 3 for word, n in raw_counts.items()})
            self.assertEqual(seen[0][1], {'ab', 'ba'})
            self.assertNotIn('initial_key', seen[0][3])
            self.assertNotIn('reference_key', seen[0][3])
            self.assertTrue(self_seen and all(self_seen))
            self.assertEqual(report['objective']['denominator'], 12)
            self.assertNotIn('candidate_counts', report['solver'])
            self.assertTrue(output.is_file())
            self.assertEqual(json.loads(output.read_text()), report)

    def test_existing_output_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'result.json'
            output.write_text('preserve')
            with self.assertRaises(FileExistsError):
                run_control({'train': ['a'], 'validation': ['a'], 'test': ['a']},
                            family='injective', seed=6000, node_budget=0,
                            output_path=output)
            self.assertEqual(output.read_text(), 'preserve')

    def test_real_small_control_records_arithmetic_and_oracle_bound(self):
        with tempfile.TemporaryDirectory() as directory:
            result = run_control(
                {'train': ['a', 'b', 'ab', 'ba'], 'validation': ['ab', 'ba'],
                 'test': ['ab', 'a']},
                family='cap2', seed=7000, node_budget=100,
                output_path=Path(directory) / 'result.json',
            )
            self.assertEqual(result['solver']['score'], result['objective']['score_from_key'])
            self.assertLessEqual(result['oracle']['objective']['score_from_key'],
                                 result['solver']['upper_bound'])
            self.assertEqual(result['oracle']['validation']['full_char_accuracy'], 1)
            self.assertEqual(result['oracle']['test']['full_char_accuracy'], 1)
            self.assertNotIn('words', result)


if __name__ == '__main__':
    unittest.main()
