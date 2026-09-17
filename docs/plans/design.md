# Voynich research design

The objective is a reproducible explanation of the manuscript's writing system and content.
A plausible translation is not sufficient evidence.

The first stage tests structural properties with a research system.
It does not assume that the text records a natural language.

## Components

1. Keep original transcriptions, source URLs, dates, and hashes.
2. Parse location identifiers, page metadata, uncertain text, and alternate readings.
3. Record corpus counts and exclusions for each analysis.
4. Compare observed text with controlled changes to character order and word order.
5. Test character prediction on separate `folio_group` values.
6. Record hypotheses, evidence, limits, and future experiments.

The system uses Python and its standard library.
Source files remain separate from generated results.
Each run records its configuration, input hashes, code hashes, and output files.
Tests use small examples with known results.

## Initial experiments

Corpus summaries include token counts, word lengths, and character entropy.
These summaries describe the selected transcription.
They do not identify the language.

Word-order tests use complete paragraph lines with at least three tokens, no dropped tokens, and no `<->` or `<~>` diagram interruption.
Each null sample changes the word order within each line.
This keeps each line's vocabulary and token count.
Tests measure initial gallows characters, initial word length, adjacent repetitions, and adjacent words with edit distance at most one.
The test suite uses 499 permutations and seed 408.
One-sided tests apply to enrichment statistics.
The word-length test uses a two-sided statistic.
Holm correction applies to the four tests within each run.
Alternative transcription and spacing runs are sensitivity analyses, not independent confirmations.

Character models use orders zero through three and additive smoothing of 0.1.
The split uses a canonical `folio_group` key. It keeps these numeric groups together:
`69/70`, `71/72`, `85/86`, `88/89/90`, `94/95`, and `100/101/102`.
The `85/86` union has direct Yale support. The other cross-number unions are
candidate relations. These unions are conservative. They do not identify every
physical sheet. The versioned mapping uses the smallest numeric folio as each
group representative. The composite source alias `fRos` maps to `85`.
It is not a new physical leaf. The mapping version is
`conservative-foldout-groups-v2`.
The split hash uses `voynich-408-v1:` followed by the canonical `folio_group` key.
Hash buckets zero and one form the test set. Bucket two forms the validation set.
The other buckets form the training set.
The model compares raw EVA characters with one declared grouping of compound forms.
The raw-EVA null shuffles code points within each token.
The grouped null shuffles declared grouped units within each token and keeps each unit's internal order.

These are exploratory structural experiments.
Previous Voynich research includes related structural observations.
Prediction scores cannot prove semantic content or historical authorship.
Future decoding experiments must use a separate, frozen protocol.

## Acceptance criteria

The source parser must keep location and exclusion information.
The statistics must pass tests with analytically known results.
Independent review must check parsing, sampling, and interpretation.
The same inputs and settings must produce identical numerical results.
No result can be called a decipherment without broad, independent evidence.
