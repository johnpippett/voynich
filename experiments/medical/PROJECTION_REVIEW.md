# Synthetic TEI projection review

Review date: 2026-09-17.

This review covers the projector, its tests, and the medical experiment
README. It uses synthetic XML only. No Celsus source was fetched or projected.

The reviewed file hashes are:

- `experiments/medical/tei_projection.py`: `d736f77a172854de0ada730d1775d36ae02691e5e0ee547931e8208120dfbadc`;
- `experiments/medical/test_tei_projection.py`: `c190fe6a748a4df77a2d1e55faf21f0232c0fb64a68ee41d2d752cdcb2f937ed`;
- `experiments/medical/README.md`: `ff30534987760701312f2ac10df4bd2650f8baf49596ebff500e429dabd62efa`.

## Result

No blocking defect remains in the synthetic projector contract. The projector
validates the complete body before it selects paragraph text. Invalid input
raises `ProjectionError` before it returns records.

The tests cover mixed content, nested `hi`, transparent `pb` and `milestone`,
element tails, correction choices, excluded subtrees, Greek language tags,
stable locations, empty records, namespace errors, and retained-letter joins.
The projector preserves the `sic` tail and the correction tail in their source
order. It applies the same boundary rule after an empty correction.

One earlier review finding is resolved. The nested choice content helper did
not retain the `sic` tail while it checked correction content. The helper now
mirrors the visitor order, and
`test_nested_choice_projected_content_keeps_sic_tail` checks the regression.

The projector keeps source spelling. It collapses only XML whitespace. It does
not repair words, change case, or apply Unicode normalization. Excluded roots
and descendants are counted separately from retained elements. The optional
`include` and `drop` policies keep source ordinals explicit.

## Limits

The source audit boundary scan is a diagnostic. It does not simulate all
adjacent excluded nodes. The projector performs the final retained-stream
check, so this audit limit does not open an acceptance path.

The synthetic suite passed 13 tests:

```text
PYTHONPATH=src:. python -m unittest experiments.medical.test_tei_projection -v
```

This result does not show that the pinned Celsus file passes the fixed source
targets. It also does not support a Voynich language claim or decipherment.
