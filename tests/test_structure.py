import math
import unittest

from voynich.structure import entropy, within_word_entropy, edit_distance_at_most_one, holm_adjust, run_structure


def line(tokens, folio='f1r', locus='1', **kwargs):
    return dict(folio=folio, locus=locus, kind='P0', tokens=tokens,
                metadata={'I': 'H', 'L': 'A'}, excluded_tokens=0, **kwargs)


class EntropyTests(unittest.TestCase):
    def test_known_distributions(self):
        self.assertEqual(entropy({'a': 3}), 0)
        self.assertAlmostEqual(entropy({'a': 5, 'b': 5}), 1)
        self.assertEqual(entropy({}), 0)

    def test_conditioning_does_not_cross_words(self):
        out = within_word_entropy(['ab', 'ab', 'ab'])
        self.assertAlmostEqual(out['h1_bits_per_eva_character'], 1)
        self.assertEqual(out['h2_bits_per_within_word_transition'], 0)
        self.assertEqual(out['within_word_transitions'], 3)

    def test_substitution_preserves_entropy(self):
        a = within_word_entropy(['abba', 'bab', 'aaa'])
        b = within_word_entropy(['xyyx', 'yxy', 'xxx'])
        self.assertEqual(a, b)


class DistanceTests(unittest.TestCase):
    def test_edit_operations(self):
        for a, b in [('', ''), ('a', ''), ('abc', 'abc'), ('abc', 'axc'),
                     ('abc', 'ab'), ('abc', 'zabc'), ('abc', 'abdc')]:
            self.assertTrue(edit_distance_at_most_one(a, b), (a, b))
            self.assertTrue(edit_distance_at_most_one(b, a), (b, a))
        for a, b in [('ab', 'ba'), ('abc', 'a'), ('abc', 'axy'), ('', 'ab')]:
            self.assertFalse(edit_distance_at_most_one(a, b), (a, b))


class PermutationTests(unittest.TestCase):
    def test_holm_known_values(self):
        out = holm_adjust([0.01, 0.04, 0.03])
        for actual, expected in zip(out, [0.03, 0.06, 0.06]):
            self.assertAlmostEqual(actual, expected)

    def test_identical_words_have_no_order_signal(self):
        result = run_structure([line(['qokedy'] * 4)], permutations=19)
        for test in result['word_order_tests'].values():
            self.assertEqual(test['p_value'], 1.0)
        self.assertEqual(result['word_order_tests']['adjacent_equal']['observed'], 1)

    def test_controlled_line_initial_effect(self):
        records = [line(['kedy', 'ol', 'ar', 'or'], locus=str(i)) for i in range(80)]
        result = run_structure(records, permutations=199)
        test = result['word_order_tests']['initial_gallows']
        self.assertEqual(test['observed'], 1)
        self.assertAlmostEqual(test['null_expectation'], 0.25)
        self.assertLess(test['p_value'], 0.02)

    def test_reproducible_and_does_not_mutate_inputs(self):
        records = [line(['kedy', 'ol', 'ar', 'or'])]
        a = run_structure(records, permutations=7, seed=9)
        b = run_structure(records, permutations=7, seed=9)
        self.assertEqual(a, b)
        self.assertEqual(records[0]['tokens'], ['kedy', 'ol', 'ar', 'or'])

    def test_excludes_incomplete_lines_and_labels_from_order_test(self):
        records = [line(['kedy', 'ol', 'ar'])]
        rejected = line(['kedy', 'ol', 'ar'])
        rejected['excluded_tokens'] = 1
        label = line(['kedy', 'ol', 'ar'])
        label['kind'] = 'L0'
        out = run_structure(records + [rejected, label], permutations=5)
        self.assertEqual(out['word_order_sample']['lines'], 1)
        self.assertEqual(out['inventory']['records'], 3)

    def test_rejects_invalid_permutation_count(self):
        with self.assertRaises(ValueError):
            run_structure([], permutations=0)

    def test_diagram_interruptions_are_excluded_from_order_tests(self):
        for marker in ['<->','<~>']:
            record = line(['kedy', 'ol', 'ar'])
            record['text_raw'] = f'kedy.ol{marker}ar'
            self.assertEqual(run_structure([record], permutations=3)['word_order_sample']['lines'], 0)

    def test_nondeterministic_seed_is_rejected(self):
        with self.assertRaises(ValueError):
            run_structure([line(['a', 'b', 'c'])], seed=None)

    def test_empty_token_is_rejected_with_clear_error(self):
        with self.assertRaises(ValueError):
            run_structure([line(['', 'a', 'b'])])


if __name__ == '__main__':
    unittest.main()
