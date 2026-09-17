import unittest

from voynich.groups import group_id, split_bucket, split_name, grouping_config


class GroupTests(unittest.TestCase):
    def test_confirmed_foldout_stays_together(self):
        self.assertEqual(group_id('f85r1'), group_id('f86v3'))
        self.assertEqual(group_id('f85v2'), '85')

    def test_rosettes_alias_joins_the_confirmed_foldout(self):
        self.assertEqual(group_id('fRos'), '85')

    def test_candidate_connected_components_are_conservative(self):
        for numbers in [(69,70),(71,72),(88,89,90),(94,95),(100,101,102)]:
            self.assertEqual({group_id(f'f{n}r') for n in numbers}, {str(min(numbers))})

    def test_other_folios_keep_original_hash_rule(self):
        self.assertEqual(group_id('f12r'), group_id('f12v'))
        self.assertEqual(group_id('f12v'), '12')
        self.assertEqual(split_name(split_bucket('7')), 'test')
        self.assertEqual(split_name(split_bucket('2')), 'validation')

    def test_unsupported_folio_is_rejected(self):
        for value in ['', 'unknown', None, 'abc85r']:
            with self.assertRaises(ValueError):
                group_id(value)

    def test_config_separates_evidence_and_assumption(self):
        config = grouping_config()
        self.assertEqual(config['confirmed_cross_number_foldout'], [85,86])
        self.assertEqual(len(config['conservative_components']),6)


if __name__ == '__main__':
    unittest.main()
