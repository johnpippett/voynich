# Secondary ranking review

Review date: 2026-09-17.

This review covers `experiments/optimal_set/secondary.py` and its synthetic tests. It uses no manuscript or reference data.

## Result

The exact secondary score passes the review for its stated scope. It ranks the supplied complete maps with a frozen conditional character model. It does not claim global optimality or a complete candidate set.

The validator checks the model fields used in scoring.
It rejects malformed control symbols, vocabulary values, context rows, targets, counts, totals, metadata, and table coverage.

## Checks

- `PYTHONPATH=src:. python -m unittest experiments.optimal_set.test_secondary -v`: 6 tests passed.
- `PYTHONPATH=src:. python -m unittest discover -s experiments/optimal_set -p 'test_*.py' -v`: 18 tests passed.
- An independent `Fraction` implementation checked 150 fitted synthetic models for orders 0 through 4.
- The independent check covered 450 capacity runs for capacities 1, 2, and `None`.
- It checked 3,150 candidate scores, weighted event counts, exact ratios, ties, display indices, and JSON serialization.
- The independent check used seed `20260917`. It included unknown training symbols and empty or zero-count cipher words.
- Nine additional malformed model probes all raised validation errors.

The model uses alpha `0.1` as `(10*c + 1) / (10*t + V)`. The vocabulary size includes alphabet symbols, `<UNK>`, and `<EOS>`. Each cipher token contributes its count to each character event and to one end-of-word event.

Candidate maps must cover every cipher symbol. Capacity checks enforce one or two plaintext preimages, or no limit for `None`. Exact `Fraction` values retain all equal maximizers. The display key is a separate deterministic tie choice.

The `max_delta_events` and `max_ratio_bits` settings limit exact arithmetic.
A limit exit returns `not_complete` with no maximizer or display winner.

## Original defect and fix

The first audit found that `LanguageModel` construction itself did not validate its frozen fields. A tampered model could therefore reach the scorer through `dataclasses.replace`.

Before the fix, the scorer accepted duplicate contexts, duplicate targets, Boolean counts, and targets outside the vocabulary.
It also accepted invalid context lengths, missing count rows, and extra totals.
A missing count row changed a two-map tie into a false winner with ratio `11:1`.

The final validator checks control identity, uniqueness, context length, legal context symbols, and `<BOS>` prefix placement.
It checks row and total uniqueness, integer types, target membership, equal context-key sets, and matching totals.
It also checks training-total consistency. The regression suite covers these cases.

## Limits

The score does not validate unused descriptive fields such as `unigram_counts`, `alphabet_source`, or `definition`. These fields do not affect this score.

The result supports ranking of the supplied maps under the validated frozen model. It does not provide a plaintext reading, a primary-score claim, or a global search result.

## Reproducibility

Final source SHA-256: `367d4ed3bd88a7601183a5870d978c19a50b0a2c7ccdd28127185aae559cdc85`.

Final focused-test SHA-256: `4ca25c81880638ebb2ba3dca4ade67d17b2a732be297b1baf4e2d5a8fbfe99a6`.
