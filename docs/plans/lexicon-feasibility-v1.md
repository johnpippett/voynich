# Finite lexicon feasibility pilot

Version 1.0, fixed before the first manuscript lexicon search.
Date: 2026-09-16.

This pilot measures bounds for one fixed injective substitution key.
It does not implement the full [identification study](next-identification-experiment.md).
All manuscript results are exploratory. The manuscript text has already been examined.

## Fixed inputs

Use the existing pinned ZL and IT transcriptions with raw EVA code points.
Use the `split` spacing policy and the complete paragraph filter from Stage 2.
Reject empty loci, loci with excluded tokens, and loci with diagram interruptions.
Use the existing version 3 quire/bifolio assignments.
Fit keys only on the manuscript training partition.

Use both existing reference corpora: `latin_llct` and `italian_old`.
Build each lexicon from its normalized reference training partition only.
Keep surface forms and the existing normalization rules.
Do not add lemmas, word repairs, or additional dictionary entries.
The plaintext alphabet is the 26 lowercase ASCII letters.

## Fixed search

Use the global integer objective in the [experiment description](../../experiments/lexicon/README.md).
For word count `n`, assign weight `n*T + N`.
Here, `T` counts types and `N` counts tokens.
Divide the final score by `2*T*N`.
This equals the mean of the token hit rate and the type hit rate.

Use the tested bitset bound engine and a limit of 10,000 expanded nodes.
The reference engine supplies a separate implementation for small differential tests.
Keep every pattern candidate. Do not use a candidate limit.
Use a cold start with no external key.
Order ciphertext symbols by descending total weight of types that contain them.
Use symbol order to resolve equal weights.
For equal visited key scores, use the solver's declared lexical order.

Record the feasible score and the maximum remaining branch bound.
Equal integer bounds certify the optimum score for this finite problem.
Record search exhaustion separately from score certification.
Report the key-completion ambiguity count and its conditions.

## Controls and sequence

The preliminary controls used 64 types, 256 types, and complete validation partitions.
Their budgets were 0, 1, 10, and 1,000 nodes.
These controls informed the search order and computational budget.
They were computational calibration, not a confirmatory study.

Run one complete known-key control per reference corpus with the final runner.
Use seed 500 and the same 10,000-node limit as the manuscript searches.
Encrypt every reference validation word with synthetic units `c00` through `c25`.
Construct the permutation by shuffling plaintext letters and pairing them with ordered synthetic units.
The planted key is available only for encryption and subsequent accuracy measurement.
The solver receives encrypted counts and the training lexicon.
Freeze its returned key before test scoring.
Measure exact character and token recovery on the complete reference test partition.
Count unmapped positions without key repairs.

Run four manuscript searches: both transcriptions against both reference lexica.
Freeze each returned key before validation and test scoring.
Report every run. Do not select a language from the test scores.
Keep code hashes, source hashes, counts, filters, bounds, and key-file hashes.
Publish aggregate results and keys. Exclude source corpora and candidate-word arrays.

## Interpretation

This pilot estimates no false-positive rate.
It does not run 32 positive controls or 1,000 replicates per null family.
It supplies no semantic or historical validation.

A certified score is a result for the declared finite lexicon and key domain.
It does not apply to all Latin, all Italian, or all manuscript encodings.
Unequal bounds indicate remaining uncertainty about that finite optimum.
A key with lexical matches is not a decipherment.
Test-set matches and proven score bounds must remain distinct in the report.

The pair-conflict prototype is outside this pilot.
Changes to these settings require a separate version and an explicit comparison.
