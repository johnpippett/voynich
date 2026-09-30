# Exact color-word count outside discovery groups

Date: 2026-09-29.
This count examines the proposed relation between EVA `key` and blue.
It does not establish a word meaning or a translation.
The [source audit](../docs/research/plant-input-and-color-audit-2026-09-29.md) records how the candidate was selected.

## Fixed method

The [plan](../docs/plans/blue-word-transfer-v1.md) fixes the operation before the new counts.
The [input manifest](../docs/plans/blue-word-transfer-v1.sources.json) fixes three files from commit `860d278a6fa72a39605a11513716e56298411d47`.
The count excludes every group represented in `PLANT_FEATURES`, across all features.
It then uses the released color tags and exact word strings from `voynich_nlp.json`.
Missing metadata, nonherbal metadata, and absent text have explicit exclusion reasons.

The current group map uses provider quire and bifolio metadata.
It does not represent a new examination of manuscript construction.
A group can supply pages to both tag categories. Group counts cannot be added as if those sets were disjoint.
The count uses no fitted cutoff, word selection, significance test, or image interpretation.

The original paint-color analysis used the remaining pages too.
Thus, these pages are outside the plant-feature groups, but not outside all discovery material.
The test uses the author's color tags. A missing `B` tag does not establish that blue paint is absent.
The transcription is also the same source used by both earlier analyses.

## Result and verification

The discovery map has 78 folios in 24 groups.
Group exclusion removes 91 of the 126 color-tagged folios. One further folio has no text.
The count keeps 34 folios in nine groups.

| Released tag category | Folios | Groups represented | Words | Exact `key` count |
| --- | ---: | ---: | ---: | ---: |
| Has `B` | 3 | 2 | 289 | 0 |
| No `B` entry | 31 | 9 | 2,711 | 2 |

The three blue-tagged folios are f56v, f94r, and f95v1.
The two occurrences are on f50v and f96v, with one on each page.
This subset supplies no positive support for `key`→blue.
The small sample and unverified tags prevent a general rejection of that proposed meaning.
No changed candidate, additional source, or weaker comparison followed the count.

The public [result](blue-word-transfer-v1.json) records each kept folio, its counts, and all exclusions.
It contains source hashes and no raw page text.
The [E2E receipt](blue-word-transfer-v1.e2e.json) records six successful cases through the same command interface.
They cover exact counts, group exclusion, deterministic output, ignored foreign code, source changes, dynamic maps, existing output, and malformed text.
Fresh downloads of all three source files produced an identical count result.
The required project suite passed all 85 tests.

A separate AI task calculated the same result without reading the primary script or output.
The [comparison receipt](blue-word-transfer-v1.verification.json) records agreement for all 78 discovery pairs, 126 folio decisions, and both category totals.
The two calculations use the same project group map. They do not supply another transcription or a separate semantic test.

The first artificial fixture used an incorrect source schema.
Before implementation, the corrected fixture used the actual sentence list and folio metadata map.
That command failed because the implementation did not yet exist.
A later harness error still referred to the old schema in one malformed-input case.
The correction changed that reference only. Both failure records are kept; no manuscript count ran before the corrections.

## Reproduce the count

Start from the repository root. Use a new output directory for each run.
Download the three fixed source files:

```sh
python - <<'PY'
import hashlib
import json
from pathlib import Path
import urllib.request

root = Path('results/blue-word-replay/source')
root.mkdir(parents=True, exist_ok=False)
manifest = json.loads(Path('docs/plans/blue-word-transfer-v1.sources.json').read_text())
for source in manifest['sources'].values():
    with urllib.request.urlopen(source['url'], timeout=30) as response:
        data = response.read()
    if hashlib.sha256(data).hexdigest() != source['sha256']:
        raise SystemExit('Source hash mismatch.')
    path = root / source['path']
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as output:
        output.write(data)
PY
python scripts/check_blue_word_transfer.py \
  docs/plans/blue-word-transfer-v1.sources.json \
  results/blue-word-replay/source \
  results/blue-word-replay/result.json
cmp reports/blue-word-transfer-v1.json results/blue-word-replay/result.json
```

Run the artificial-input test and the required project suite:

```sh
python scripts/test_blue_word_transfer_e2e.py results/blue-word-transfer-v1/e2e/replay
PYTHONPATH=src python -m unittest discover -s tests -v
```

The E2E test does not need source downloads.
Its artifact records setup, commands, expected counts, and pass or fail results.
An existing output path must fail without changing the earlier result.
