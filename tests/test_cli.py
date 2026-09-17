import json
from pathlib import Path
import tempfile
import unittest

from voynich.cli import main, verify_hashes


class CliTests(unittest.TestCase):
    def test_changed_source_is_detected(self):
        import hashlib
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'input.txt').write_text('known', encoding='utf-8')
            manifest = {'sources': [{'path': 'input.txt', 'sha256': hashlib.sha256(b'known').hexdigest()}]}
            self.assertTrue(verify_hashes(root, manifest)[0]['matches'])
            (root / 'input.txt').write_text('changed', encoding='utf-8')
            self.assertFalse(verify_hashes(root, manifest)[0]['matches'])

    def test_end_to_end_tiny_corpus(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'fixture.txt'
            source.write_text('#=IVTFF Eva- 2.0 M 5\n<f1r> <! $I=H $L=A>\n<f1r.1,@P0> <%>kedy.ol.ar.or<$>\n', encoding='utf-8')
            output = root / 'output'
            main(['run', '--source', str(source), '--output', str(output), '--permutations', '7', '--bootstraps', '7'])
            result = json.loads((output / 'analysis.json').read_text())
            self.assertEqual(result['structure']['inventory']['tokens'], 4)
            self.assertEqual(result['status'], 'exploratory_not_deciphered')
            self.assertTrue((output / 'REPORT.md').is_file())
            self.assertTrue((output / 'records.jsonl').is_file())
            self.assertIn('source_sha256', result['provenance'])

    def test_existing_results_are_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / 'output'
            output.mkdir()
            (output / 'keep.txt').write_text('preserve')
            with self.assertRaises(FileExistsError):
                main(['run', '--output', str(output)])
            self.assertEqual((output / 'keep.txt').read_text(), 'preserve')


if __name__ == '__main__':
    unittest.main()
