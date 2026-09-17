"""Check reversible visual unitization without manuscript data."""

import random
import string
import unittest

from experiments.homophonic.units import tokenize_word, units, tokenizer_config


class UnitTests(unittest.TestCase):
    def test_visual_compounds_and_exact_spans(self):
        word = 'cthchshckhcphcfh'
        spans = tokenize_word(word, representation='visual')
        self.assertEqual(tuple(span.unit for span in spans),
                         ('cth', 'ch', 'sh', 'ckh', 'cph', 'cfh'))
        self.assertEqual([(s.start, s.end) for s in spans],
                         [(0, 3), (3, 5), (5, 7), (7, 10), (10, 13), (13, 16)])
        self.assertEqual(''.join(s.raw for s in spans), word)

    def test_raw_representation_preserves_singletons(self):
        self.assertEqual(units('cthch', representation='raw'), tuple('cthch'))

    def test_other_sequences_and_unmatched_letters_remain_separate(self):
        word = 'iniinii ii qo xyz'.replace(' ', '')
        self.assertEqual(units(word, representation='visual'), tuple(word))
        self.assertEqual(units('cch', representation='visual'), ('c', 'ch'))

    def test_reconstruction_and_contiguous_spans(self):
        rng = random.Random(1701)
        chunks = list(string.ascii_lowercase) + ['cth', 'ckh', 'cph', 'cfh', 'ch', 'sh']
        for _ in range(200):
            word = ''.join(rng.choices(chunks, k=rng.randrange(30)))
            for representation in ['raw', 'visual']:
                spans = tokenize_word(word, representation=representation)
                cursor = 0
                for span in spans:
                    self.assertEqual(span.start, cursor)
                    self.assertGreater(span.end, span.start)
                    self.assertEqual(span.raw, word[span.start:span.end])
                    self.assertEqual(span.unit, span.raw)
                    cursor = span.end
                self.assertEqual(cursor, len(word))
                self.assertEqual(''.join(s.raw for s in spans), word)

    def test_boundaries_and_noncanonical_input_are_rejected(self):
        for word in ['ch sh', 'ch.sh', 'Ch', '{ch}', 'ch\n', 'é', 'a1']:
            with self.assertRaises(ValueError):
                tokenize_word(word, representation='visual')
        with self.assertRaises(TypeError):
            tokenize_word(['ch'], representation='visual')
        with self.assertRaises(ValueError):
            tokenize_word('ch', representation='guessed')

    def test_config_defines_visual_choice_without_letter_values(self):
        config = tokenizer_config('visual')
        self.assertEqual(set(config['compounds']), {'ch', 'sh', 'cth', 'ckh', 'cph', 'cfh'})
        self.assertEqual(config['word_boundaries'], 'Caller supplies one word; internal separators are rejected.')
        self.assertEqual(tokenizer_config('raw')['compounds'], [])


if __name__ == '__main__':
    unittest.main()
