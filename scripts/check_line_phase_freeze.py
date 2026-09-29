#!/usr/bin/env python3
"""Check that an incomplete freeze cannot start the source study."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    if len(sys.argv) != 2:
        raise SystemExit('Supply a new receipt path.')
    receipt_path = Path(sys.argv[1])
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        freeze = root / 'empty-freeze.json'
        freeze.write_text('{"files": {}, "sources": {}}\n')
        output = root / 'output'
        run = subprocess.run([sys.executable, 'scripts/run_line_phase_lattice.py',
                              '--freeze', str(freeze), '--output', str(output)],
                             cwd=ROOT, capture_output=True, text=True, timeout=30)
        passed = run.returncode != 0 and not output.exists() and 'freeze file set' in run.stderr
        receipt = dict(schema='line-phase-freeze-e2e-v1', passed=passed,
                       setup='Empty files and sources in a temporary freeze.',
                       steps=['Run the source command with a new output directory.',
                              'Require rejection before output creation.'],
                       expected='Nonzero exit, freeze file set error, no output directory.',
                       actual=dict(returncode=run.returncode, output_exists=output.exists(),
                                   freeze_file_set_error='freeze file set' in run.stderr),
                       runner_sha256=hashlib.sha256((ROOT / 'scripts/run_line_phase_lattice.py').read_bytes()).hexdigest(),
                       rerun='python scripts/check_line_phase_freeze.py NEW_RECEIPT.json')
    with receipt_path.open('x') as handle:
        json.dump(receipt, handle, sort_keys=True, indent=2)
        handle.write('\n')
    print('PASS' if passed else 'FAIL')
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
