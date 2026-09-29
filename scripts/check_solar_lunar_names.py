"""Measure exact word intersections in five fixed image regions."""
import hashlib
import json
from pathlib import Path
import re
import sys

from voynich.corpus import parse_ivtff

BASE = Path('results/solar-lunar-name-check-v1')
SOURCES = {
    'ZL': ('data/raw/ZL3b-n.txt', 'bf5b6d4ac1e3a51b1847a9c388318d609020441ccd56984c901c32b09beccafc'),
    'IT': ('data/raw/IT2a-n.txt', '7f27a8b0feed8f6de0a99900df6bf912dd1d295c38e5f830bac8b41c3f536fb5'),
}
REGIONS = {
    'sun1': ['f68r1.5,@Pb', 'f68r1.6,+Pb', 'f68r1.7,+Pb'],
    'sun2': ['f68r2.31,@Cc'],
    'moon1': ['f68r1.37,@Cc'],
    'moon2': ['f68r2.6,@Cc'],
    'moon3': ['f68r3.22,@Cc'],
}
COMPARISONS = {'sun': ['sun1', 'sun2'], 'moon_pair': ['moon1', 'moon2'], 'moon_all': ['moon1', 'moon2', 'moon3']}
PINS = {
    BASE / 'plan.md': '2b1f6afd73f266aedfe40fafe601e334142029313602b071ffb33a6c8b91e8a6',
    Path('src/voynich/corpus.py'): '064c45794d523b5c07ea10621752e325d35709f619e0763ac6ba1561f0fa1dc2',
}

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

if len(sys.argv) != 2:
    raise SystemExit('Supply one new output path.')
out = Path(sys.argv[1])
if out.exists():
    raise SystemExit('Output already exists.')
for path, expected in list(PINS.items()) + [v for v in SOURCES.values()]:
    if digest(path) != expected:
        raise SystemExit('Source hash mismatch: ' + str(path))
result = {'schema_version': 1, 'plan_sha256': PINS[BASE / 'plan.md'], 'parser_sha256': PINS[Path('src/voynich/corpus.py')], 'script_sha256': digest(__file__), 'tracks': {}}
for source, (path, expected) in SOURCES.items():
    for mode in ('split', 'join'):
        records = parse_ivtff(path, uncertain_spaces=mode)
        selected = {}
        for region, loci in REGIONS.items():
            selected[region] = []
            for locus in loci:
                rows = [r for r in records if r['locus'] == locus]
                if len(rows) != 1:
                    raise SystemExit('Locus count differs from one: ' + locus)
                r = rows[0]
                selected[region].append({
                    'locus': locus, 'raw': r['text_raw'], 'tokens': r['tokens'],
                    'excluded_tokens': r['excluded_tokens'],
                    'uncertain_space': ',' in re.sub(r'<!.*?>', '', r['text_raw']),
                })
        sets = {k: set(t for r in rows for t in r['tokens']) for k, rows in selected.items()}
        comparisons = {}
        for name, regions in COMPARISONS.items():
            common = set.intersection(*(sets[r] for r in regions))
            comparisons[name] = {
                'regions': regions, 'candidates': sorted(common),
                'occurs_in': {w: [r for r in REGIONS if w in sets[r]] for w in sorted(common)},
            }
        result['tracks'][source + '-' + mode] = {
            'source_sha256': expected, 'regions': selected,
            'region_type_counts': {k: len(v) for k, v in sets.items()},
            'comparisons': comparisons,
        }
out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({k: {'region_type_counts': v['region_type_counts'], 'candidate_counts': {c: len(x['candidates']) for c, x in v['comparisons'].items()}, 'exclusions': {r: sum(x['excluded_tokens'] for x in rows) for r, rows in v['regions'].items()}} for k, v in result['tracks'].items()}, indent=2))
