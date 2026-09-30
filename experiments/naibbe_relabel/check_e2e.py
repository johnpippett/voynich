"""Check span selection through the control command."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
RUNNER = Path(__file__).with_name('run_control.py')
fixture = {
    'blocks': [
        ['aleeor', 'aiiinaiin', 'aleeor', 'aiiinaiin', '!',
         'aleeor', 'aiiinaiin', 'aleeor', 'aiiinaiin'],
        ['aleeor', 'aiiinaiin'],
        ['aleeor', 'aiiinaiin'],
        ['aleeor', 'aiiinaiin', 'shor', 'aleeor', 'aiiinaiin'],
    ],
    'minimum_characters': 8,
}
expected = ['armaarma', 'armaarma']
assert RUNNER.exists(), 'Missing control command'
with tempfile.TemporaryDirectory() as directory:
    base = Path(directory)
    source = base / 'fixture.json'
    output = base / 'result.json'
    source.write_text(json.dumps(fixture) + '\n')
    result = subprocess.run(
        [sys.executable, str(RUNNER), '--fixture', str(source), '--output', str(output)],
        cwd=base, text=True, capture_output=True,
    )
    assert result.returncode == 0, result.stderr
    record = json.loads(output.read_text())
    assert record['spans'] == expected, record
    assert record['excluded_tokens'] == {'ambiguous': 1, 'no_parse': 1}, record
    assert record['short_runs'] == 4, record
    assert record['kept_characters'] == 16, record
    assert record['blocks'] == 4, record
    second = subprocess.run(
        [sys.executable, str(RUNNER), '--fixture', str(source), '--output', str(output)],
        cwd=base, text=True, capture_output=True,
    )
    assert second.returncode != 0, 'Existing output was overwritten'
    receipt = {
        'setup': 'Use pinned Naibbe CSV and Python. Run this command from any directory.',
        'command': 'python experiments/naibbe_relabel/check_e2e.py',
        'fixture': fixture,
        'expected_spans': expected,
        'checks': ['Do not join across an unsupported token.',
                   'Do not join across an ambiguous token.',
                   'Do not join across blocks.',
                   'Keep only runs of at least eight characters.',
                   'Reject an existing output file.'],
        'result': record,
        'output_sha256': hashlib.sha256(output.read_bytes()).hexdigest(),
        'status': 'passed',
    }
    print(json.dumps(receipt, indent=2))
