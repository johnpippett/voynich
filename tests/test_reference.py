"""Check reference normalization and orthographic word extraction."""

import unittest

from voynich.reference import normalize_word, parse_conllu, reference_document, remove_cross_partition_duplicates


class ReferenceTests(unittest.TestCase):
    def test_normalization_is_fixed_and_does_not_invent_boundaries(self):
        self.assertEqual(normalize_word('ĀMŌ'), 'amo')
        self.assertEqual(normalize_word('ſum'), 'sum')
        self.assertEqual(normalize_word('Vita'), 'vita')
        self.assertEqual(normalize_word('𝐀'), 'a')
        for value in ["l'amore", 'res-publica', '12', 'æ', '', 'two words']:
            self.assertIsNone(normalize_word(value))

    def test_multiword_surface_replaces_components_and_ignores_empty_nodes(self):
        source = '''# newdoc id = work1
# sent_id = s1
# reference = document_id='36:1047'-span='1'
1\tVita\t_\t_\t_\t_\t0\t_\t_\t_
2-3\tdella\t_\t_\t_\t_\t_\t_\t_\t_
2\tdi\t_\t_\t_\t_\t1\t_\t_\t_
3\tla\t_\t_\t_\t_\t1\t_\t_\t_
3.1\tomitted\t_\t_\t_\t_\t_\t_\t_\t_
4\t.\t_\t_\t_\t_\t1\t_\t_\t_

# sent_id = s2
1\tĀmō\t_\t_\t_\t_\t0\t_\t_\t_
'''
        result = parse_conllu(source)
        self.assertEqual([s['words'] for s in result['sentences']], [['vita', 'della'], ['amo']])
        self.assertEqual([s['document'] for s in result['sentences']], ['work1', 'work1'])
        self.assertEqual(result['sentences'][0]['reference'], "document_id='36:1047'-span='1'")
        self.assertIsNone(result['sentences'][1]['reference'])
        self.assertEqual(result['stats']['accepted_words'], 3)
        self.assertEqual(result['stats']['excluded_surface_tokens'], 1)
        self.assertEqual(result['stats']['skipped_component_rows'], 2)
        self.assertEqual(result['stats']['empty_nodes'], 1)

    def test_rejected_multiword_does_not_restore_its_components(self):
        source = "1-2\tl'amore\t_\t_\t_\t_\t_\t_\t_\t_\n1\tl\t_\t_\t_\t_\t0\t_\t_\t_\n2\tamore\t_\t_\t_\t_\t1\t_\t_\t_\n"
        result = parse_conllu(source)
        self.assertEqual(result['sentences'][0]['words'], [])
        self.assertEqual(result['stats']['excluded_surface_tokens'], 1)

    def test_bad_token_rows_fail_instead_of_silent_truncation(self):
        with self.assertRaises(ValueError):
            parse_conllu('1\tword\n')
        with self.assertRaises(ValueError):
            parse_conllu('x\tword\t_\t_\t_\t_\t_\t_\t_\t_\n')

    def test_document_identifiers_and_duplicate_exclusions(self):
        self.assertEqual(reference_document('latin_llct', {'reference': "document_id='36:1047'-span='1'"}), '36:1047')
        self.assertEqual(reference_document('italian_old', {'id': 'OldItalian_Dante_Paradiso-2'}), 'Paradiso')
        with self.assertRaises(ValueError):
            reference_document('italian_old', {'id': 'unknown'})
        same = {'words': ['common', 'phrase']}
        distinct = {'words': ['new']}
        clean, exclusions = remove_cross_partition_duplicates({
            'train': [same, same], 'validation': [same, distinct],
            'test': [same, distinct, {'words': ['final']}],
        })
        self.assertEqual(len(clean['train']), 2)
        self.assertEqual(clean['validation'], [distinct])
        self.assertEqual(clean['test'], [{'words': ['final']}])
        self.assertEqual(exclusions['test'], {'sentences': 2, 'words': 3})


if __name__ == '__main__':
    unittest.main()
