# Voynich research implementation plan

**Goal:** Run a reproducible first research stage.

**Architecture:** Separate source ingestion, analysis, and reporting. Keep original files unchanged.

**Technology:** Python 3.11 or later, standard library, and unittest.

**Design:** `docs/plans/design.md`.

## Work allocation

- [x] Corpus worker: source acquisition, parser, parser tests, and source documentation.
- [x] Scholarship worker: original research review and source registry.
- [x] Folio worker: image identification against the Yale record.
- [x] Methodology worker: validation protocol and hypothesis registry.
- [x] Prediction worker: grouped data split, models, null model, and tests.
- [x] Primary: structural metrics, permutation tests, run records, report, and integration tests.
- [x] Review worker: separate AI-agent review of code and scientific claims.

These completed tasks cover the first research stage. The decipherment objective remains unresolved.
The code reviews do not constitute external scholarly validation.

## Interfaces

`parse_ivtff(path, uncertain_spaces='split')` returns a list of line records.
Each record contains `folio`, `locus`, `kind`, `transcriber`, `text_raw`, `tokens`, `metadata`, and `excluded_tokens`.
The records keep paragraph boundary flags when available.

`run_predictive(records, seed=408)` returns model settings, split assignments, counts, and prediction scores.

The predictive split uses the canonical `folio_group` mapping. It keeps
`69/70`, `71/72`, `85/86`, `88/89/90`, `94/95`, and `100/101/102` together.
These unions are conservative and do not identify every physical sheet.

`run_structure(records, permutations=499, seed=408)` returns descriptive statistics and word-order test results.

The command `python -m voynich run` reads saved source files and writes a report directory.
It must reject mixed transcriber records unless the user selects one transcriber.
The command `python -m voynich verify-sources` checks downloaded file hashes.

## Verification sequence

1. Write tests that specify known parser and mathematical behavior.
2. Run tests before implementation and inspect the failure.
3. Implement each component and run its tests.
4. Run the full corpus analysis.
5. Run the analysis again and compare numerical outputs.
6. Run the other transcription and uncertain-space policies.
7. Review the source files, code, and interpretation independently.
8. Correct confirmed defects and run the affected checks again.
