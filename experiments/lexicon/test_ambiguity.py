"""Check completion counts against direct finite key enumeration."""

import itertools
import unittest

from experiments.lexicon.ambiguity import preserved_hit_completions


class CompletionAmbiguityTests(unittest.TestCase):
    def test_surplus_letters_preserve_positive_hits(self):
        result = preserved_hit_completions(
            {'x': 2, 'yy': 1}, {'a'}, 'abc', {'x': 'a', 'y': 'b'})
        self.assertEqual(result['covered_symbol_count'], 1)
        self.assertEqual(result['keys_preserving_current_hits'], 2)
        self.assertEqual(result['symbols_outside_positive_hits'], ['y'])

    def test_zero_weights_do_not_constrain_score(self):
        result = preserved_hit_completions(
            {'xy': 0, 'z': 0}, {'ab', 'c'}, 'abcd',
            {'x': 'a', 'y': 'b', 'z': 'c'})
        self.assertEqual(result['incumbent_score'], 0)
        self.assertEqual(result['covered_symbol_count'], 0)
        self.assertEqual(result['keys_preserving_current_hits'], 24)

    def test_empty_word_hit_does_not_fix_any_symbol(self):
        result = preserved_hit_completions(
            {'': 3, 'x': 0}, {''}, 'abc', {'x': 'a'})
        self.assertEqual(result['incumbent_score'], 3)
        self.assertEqual(result['keys_preserving_current_hits'], 3)

    def test_count_is_sound_for_each_small_key(self):
        counts = {'xy': 2, 'xz': 1, 'xx': 0}
        lexicon = {'ab', 'ac'}
        keys = [dict(zip('xyz', values))
                for values in itertools.permutations('abcd', 3)]
        def score(key):
            return sum(weight for word, weight in counts.items()
                       if ''.join(key[symbol] for symbol in word) in lexicon)
        optimum = max(map(score, keys))
        for key in keys:
            result = preserved_hit_completions(counts, lexicon, 'abcd', key)
            self.assertEqual(result['incumbent_score'], score(key))
            at_least = sum(score(other) >= score(key) for other in keys)
            self.assertLessEqual(result['keys_preserving_current_hits'], at_least)
            if score(key) == optimum:
                optima = sum(score(other) == optimum for other in keys)
                self.assertLessEqual(result['keys_preserving_current_hits'], optima)

    def test_incomplete_or_noninjective_key_is_rejected(self):
        for key in ({'x': 'a'}, {'x': 'a', 'y': 'a'}):
            with self.assertRaises(ValueError):
                preserved_hit_completions({'xy': 1}, {'ab'}, 'abc', key)


if __name__ == '__main__':
    unittest.main()
