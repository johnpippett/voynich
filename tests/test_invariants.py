"""Tests for statistics that a bijective symbol substitution preserves."""

import math
import unittest

from voynich.invariants import compare_invariants, invariant_summary, word_pattern


class InvariantTests(unittest.TestCase):
    def test_patterns_record_equality_and_order(self):
        self.assertEqual(word_pattern('noon'), (0, 1, 1, 0))
        self.assertEqual(word_pattern(('ch', 'a', 'ch')), (0, 1, 0))
        self.assertNotEqual(word_pattern('abba'), word_pattern('abab'))

    def test_known_entropy_and_lengths(self):
        result = invariant_summary(['ab', 'aa'])
        self.assertEqual(result['tokens'], 2)
        self.assertEqual(result['types'], 2)
        self.assertEqual(result['mean_units_per_token'], 2)
        self.assertEqual(result['length_counts'], {'2': 2})
        expected = -.75 * math.log2(.75) - .25 * math.log2(.25)
        self.assertAlmostEqual(result['unit_entropy_bits'], expected)
        self.assertAlmostEqual(result['within_word_conditional_entropy_bits'], 1)

    def test_bijection_preserves_every_summary_value(self):
        words = ['ababa', 'abb', 'c', 'abb', 'cabc', 'ababa']
        key = {'a': 'z', 'b': 'x', 'c': 'q'}
        encrypted = [tuple(key[c] for c in w) for w in words]
        self.assertEqual(invariant_summary(words), invariant_summary(encrypted))
        comparison = compare_invariants(encrypted, words)
        self.assertEqual(comparison['pattern_supported_token_rate'], 1)
        self.assertAlmostEqual(comparison['length_js_bits'], 0)
        self.assertAlmostEqual(comparison['pattern_js_bits'], 0)

    def test_pattern_support_is_an_upper_bound_not_a_key(self):
        comparison = compare_invariants(['noon', 'deed', 'abc'], ['toot'])
        self.assertEqual(comparison['pattern_supported_tokens'], 2)
        self.assertAlmostEqual(comparison['pattern_supported_token_rate'], 2 / 3)
        self.assertEqual(comparison['cipher_tokens'], 3)
        self.assertEqual(comparison['reference_tokens'], 1)
        self.assertEqual(comparison['joint_key_consistency_tested'], False)

    def test_disjoint_lengths_have_maximal_js(self):
        comparison = compare_invariants(['a'], ['bbb'])
        self.assertAlmostEqual(comparison['length_js_bits'], 1)
        self.assertEqual(comparison['pattern_supported_token_rate'], 0)

    def test_empty_inputs_and_invalid_symbols_are_explicit(self):
        self.assertEqual(invariant_summary([])['tokens'], 0)
        self.assertIsNone(invariant_summary([])['unit_entropy_bits'])
        with self.assertRaises(ValueError):
            compare_invariants(['a'], [])
        for bad in ['', ('a', ''), ('a', 3)]:
            with self.assertRaises(ValueError):
                word_pattern(bad)
        with self.assertRaises(TypeError):
            invariant_summary('abc')


if __name__ == '__main__':
    unittest.main()
