# Search-development runner review

Review date: 2026-09-17.

This review covers [`run_study.py`](run_study.py), its synthetic tests, and
the protocol in
[`homophonic-search-development-v1.md`](../../docs/plans/homophonic-search-development-v1.md).
It does not run the Italian root bound or an Italian local search.

Reviewed hashes:

- `run_study.py`: `71f75841d3873746a0ba05124ce27350617d3743d21d480b66385ca41811ab7a`
- `test_run_study.py`: `7cc1085484e5b9e5b2f57be6f56c97480d8ec03eb4611f1e7106e907ad03b419`
- `homophonic-search-development-v1.md`: `d44a1a2208d4b90a5d8e1ce13ff9d090ba88b24fa35184328c76dc84caf91821`

## Result

The fixed runner path has no blocking issue in the synthetic review. The
tests cover the JSON decoder, exact local-search checks, pinned hashes, and
public output filters.

The fixed input loader was used only to recompute its input metadata. It
reported the counts and hashes in the protocol. The review did not construct
the root bound or fit a local search.

## Earlier findings now fixed

### JSON compound-unit rows

Before the fix, this private input failed because JSON arrays decode as lists:

```json
{"validation_counts":[{"word":["x","y"],"count":2}]}
```

The decoder now converts arrays to tuples and validates every unit. It rejects
duplicate normalized rows with `ValueError` instead of overwriting a row.
The test `test_json_word_arrays_are_normalized_and_duplicates_rejected` covers
both cases.

### Local-search result checks

The runner now rescored the returned map and checks that the final score is at
least the initial score. It accepts only the three statuses returned by the
frozen primitive: `empty_input`, `move_budget_exhausted`, and
`no_improving_move`.

It also requires a Boolean neighborhood flag. A `no_improving_move` result
must report a checked neighborhood. The other two statuses must report an
unchecked neighborhood. The regression test supplies invalid result records.

### Pinned input provenance

The runner now hashes the normalized training lexicon with the frozen string
word format. It recomputes the weighted-count hash before any fitting stage.
The fixed loader builds weights from raw counts and checks this digest:

| Item | Value |
| --- | --- |
| Validation tokens | `31681` |
| Validation word types | `14170` |
| Training lexicon types | `6273` |
| Cipher units | `47` |
| Weighted-count SHA-256 | `664b6498a147b5430695ec0f0ee276c654fabd6a9e567b4960eb7d1f56fad944` |
| Training-lexicon SHA-256 | `29d94e0de2a154071c15a9c524a1bb0b73ba2c3a618935be8716e8d3a32824ef` |
| Validation-stream SHA-256 | `d7e9c6e0b716cf7ea1c7deb4f135ca2692ea70b4f927548e99668ab0c1428492` |

No second lexicon digest is needed. The recomputed digest uses the same
canonical string-word serialization as the frozen control.

### Control-generation metadata

The manifest, aggregate report, and fit-key records now record these fixed
generation values:

| Field | Value |
| --- | --- |
| Control family | `cap2` |
| Encryption seed | `7000` |

The configuration rejects another family or seed. This prevents a new control
from using the old output path and the current protocol name.

## Remaining boundaries

`source_hash_receipts()` records the protocol, runner, and test hashes. A
direct `run_study()` call does not compare its own runner and test hashes with
embedded expected values. The `run_frozen.py` entry point performs that
comparison through its external 29-file freeze manifest before it starts a
child.

The direct `from_weighted_counts()` constructor accepts caller-supplied
weights when raw counts are absent. It cannot verify each weight against
`count * T + N`. The fixed loader uses raw counts and the pinned weighted
digest. A caller must use that loader for the frozen Italian input.

The direct input object also accepts a caller-supplied validation-stream hash.
The fixed loader computes the hash from the generated validation ciphertext.
This is a trusted-input API boundary, not a substitute for the fixed loader.

## Checks

The focused suite passed 15 tests:

```text
python -m unittest experiments.search_development.test_run_study -v
```

The complete search-development suite passed 43 tests:

```text
python -m unittest discover -s experiments/search_development -p 'test_*.py' -v
```

The tests use small synthetic inputs. The fixed loader check did not construct
the Italian root bound, run local search, or score a result.

I reviewed ASD-STE100 Issue 9 Rules 3.6, 6.1, and 6.3. I also checked the
dictionary entries for `CHECK`, `COMPARE`, `RECORD`, `RESULT`, `LOCAL`, and
`CAPACITY`. These checks support this review; they do not claim full standard
certification.
