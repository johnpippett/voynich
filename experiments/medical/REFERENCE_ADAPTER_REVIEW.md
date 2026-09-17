# Celsus reference adapter review

Review date: 2026-09-17.

This review uses synthetic projected paragraph records only. It does not read
XML, access Celsus data, create partitions from source files, or fit a model.

Reviewed hashes:

- `experiments/medical/reference_adapter.py`: `4c1b50b75b3e7bfda5ff2d66ee3352ef35329a1b564858041067dd36af4c3357`
- `experiments/medical/test_reference_adapter.py`: `e0c804787ac55802c5e0955bb7629cecd67934b4989cd097efec8d9bed236700`
- `docs/plans/celsus-reference-control-v1.md`: `9dbbd380c0528ea3329a4441192a958a3ae48d56224643048bc80353114557aa`

## Result

The previous review found a generic grouping defect. `_validate_records()`
accepted book IDs that contained `:`, while `_assign_splits()` grouped with
`chapter_key.split(":", 1)[0]`. This could merge separate books.

The reviewed fix passes the validated `chapter_books` mapping to
`_assign_splits()`. The function now groups directly by the validated book
value. A synthetic case with two chapters in each of `a:x` and `a:y` now gives
one train and one test chapter in each book under the 60/20/remainder rule.

The original generic finding is resolved. No remaining adapter finding is known
from this review. The source-specific Celsus data path was not processed.
The plan hash is recorded for provenance; plan updates are outside this review.

## Verified behavior

The adapter correctly implements these reviewed rules on synthetic records:

- It assigns complete chapters by source order within each book.
- It uses integer floors for the 60 percent train and 20 percent validation
  portions, with the remainder in test.
- It validates the exact record fields, chapter key, positive ordinal, source
  order, duplicate paragraph keys, and contiguous book and chapter groups.
- It extracts maximal alphabetic runs with adjacent Unicode combining marks.
- It calls `normalize_word()` without spelling repair and keeps Roman-like
  letter tokens as ordinary tokens.
- It removes exact non-empty paragraph-sequence duplicates from validation and
  test in priority order while preserving duplicates within one split.
- It keeps empty paragraphs in metadata and excludes their empty token streams.
- It keeps raw paragraph text out of the manifest and produces deterministic
  source, paragraph, and token-stream hashes.

## Verification

The focused suite passed with warnings treated as errors:

```text
PYTHONWARNINGS=error PYTHONPATH=src:. python -m unittest \
  experiments.medical.test_reference_adapter -v
Ran 10 tests ... OK
```

Independent checks passed for decomposed accents, combining marks, rejected
Greek runs, Roman-like tokens, cross-split duplicate removal, preserved
within-split duplicates, source immutability, public manifest filtering, and
the colon-containing book-ID regression case. Python bytecode compilation also
passed for the adapter and its tests.

No Celsus projection, token stream, model input, model fit, or VMS conclusion
was produced by this review.
