# Candidate audit reproduction

This audit uses Python standard-library code and the repository parser.
It imports one reviewed, pinned decoder. It does not call that decoder's main program.
The fixed plan limits the check to four guide examples and one f88r sequence.

## Setup

1. Use the repository revision that contains these artifacts.
2. Run `python scripts/fetch_sources.py` to get the two pinned transcriptions.
3. Review the decoder at the commit in the source manifest.
4. Run the following setup command from the repository root.

The command checks hashes before it saves source bytes.
It keeps existing files when their bytes agree and stops when they differ.

```sh
python - <<'PY'
import hashlib
import json
import urllib.request
from pathlib import Path

base = Path('results/key-candidate-search-2026-09-29')
audit = base / 'zfd-replication'
external = base / 'source-refresh'

def save(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != content:
            raise ValueError('Existing file differs: ' + str(path))
    else:
        with path.open('xb') as handle:
            handle.write(content)

for source, target in [
    ('docs/plans/zfd-candidate-audit-v1.md', audit / 'plan.md'),
    ('docs/plans/zfd-candidate-audit-v1-version.md', audit / 'version-addendum.md'),
    ('reports/zfd-candidate-audit-v1/e2e-expectations.json', audit / 'e2e-expectations.json'),
    ('reports/zfd-candidate-audit-v1/source-manifest.json', external / 'source-manifest.json'),
]:
    save(target, Path(source).read_bytes())

manifest = json.loads(Path('docs/research/candidate-key-audit-2026-09-29.sources.json').read_text())
required = {
    'README.md', 'GETTING_STARTED.md', '06_Pipelines/zfd_decoder_v2.py',
    '08_Final_Proofs/Master_Key/unified_lexicon_v3.json',
    '06_Pipelines/regenerate_corpus.py',
}
for source in manifest['zfd']['files']:
    if source['path'] not in required:
        continue
    with urllib.request.urlopen(source['url'], timeout=60) as response:
        content = response.read()
    if hashlib.sha256(content).hexdigest() != source['sha256']:
        raise ValueError('Source hash differs: ' + source['path'])
    prefix = external / 'canonical' if source['path'].endswith('/regenerate_corpus.py') else external
    save(prefix / source['path'], content)
PY
```

## Run and compare

Run the audit with a new output path:

```sh
python scripts/check_zfd_candidate.py --output results/key-candidate-search-2026-09-29/zfd-replication/replay.json
```

The receipt records source hashes, the script hash, each fixed check, exclusions, and failure reasons.
The guide comparisons can fail while the audit completes all checks.
A guide disagreement is an observed result. A wrong source hash or an import error invalidates the run.
The command refuses an existing output path.

Exit code 0 means that the audit completed, including any recorded guide disagreements.
Exit code 1 means an execution failure. Exit code 2 means an invalid argument or an existing output path.

Compare the scientific fields with `result.json` in this directory.
The command string and Python version can differ between runs.
Do not change the key, examples, spelling, source files, or selection rules to get a different result.
The [report](../../docs/research/candidate-key-audit-2026-09-29.md) gives the interpretation and its limits.
