# Word-context experiment

Status: exploratory method, version 1, 2026-09-16.

This experiment asks whether a preceding token helps predict the next token in
held-out paragraph lines. It compares a smoothed unigram with a smoothed word
bigram. It does not test a translation and does not establish language or
meaning.

## Input filter

`run_context(records, seed=408, bootstraps=499)` accepts the line records from
the corpus parser. It uses records with all of these properties:

* `kind` starts with `P`.
* `excluded_tokens` is zero.
* `text_raw` does not contain `<->` or `<~>`. These markers show diagram interruptions.
* `tokens` contains at least three non-empty strings.

The first token in each eligible line supplies context only. The score contains
the targets at positions 1 through `n-1`. The code does not join two lines.
This gives the unigram and both bigrams the same target positions.

## Folio-group split

The split unit is the conservative folio group from `voynich.groups`.
For example, `f85r`, `f86v`, and the `fRos` alias share group `85`.
The bucket is:

```text
sha256("voynich-408-v1:" + group_id)[:8] as big-endian integer modulo 10
```

Buckets 0 and 1 are `test`. Bucket 2 is `validation`. Buckets 3 through 9
are `train`. The result contains the complete group and folio manifests, the
full grouping configuration, and a SHA-256 manifest hash.

The grouping joins confirmed `85/86` and conservative candidate components.
The candidate unions are assumptions for leakage control. They are not a
complete codicology map.

## Models

The training vocabulary contains all word types with at least two training
occurrences. Every other type maps to `<UNK>`. The unigram uses add-alpha
smoothing with `alpha = 0.1`:

```text
P_uni(w) = (count(w) + 0.1) / (training_tokens + 0.1 * vocabulary_size)
```

The bigram uses `tau = 10`:

```text
P(w | previous) =
    (count(previous, w) + 10 * P_uni(w)) / (count(previous) + 10)
```

Counts include only adjacent tokens within one training line. The result
contains counts and probability-sum checks for reproducibility.

The original model uses the training lines in source order. A second model
uses a fixed-seed shuffle of tokens within each training line. It preserves
line length and token counts. Both models score the original validation and
test lines. The held-out lines are never shuffled.

## Scores and uncertainty

Scores report total negative log likelihood in bits, bits per scored target,
unknown target count, unknown target rate, and per-group values. Unknown means
that the raw target is outside the fitted count-at-least-two vocabulary.
Unseen means that the raw target never occurs in training. A training singleton
is unknown after vocabulary pruning, but it is not unseen.
The main test
differences are:

* `unigram total bits - original bigram total bits`: positive values favor the
  preceding-token model.
* `shuffled-training total bits - original-training total bits`: positive
  values favor the original training order.

The default uncertainty procedure draws the test groups with replacement 499
times using seed 408. Each draw reports the difference in total bits divided
by the total number of scored targets. The reported interval is the discrete
2.5th to 97.5th percentile interval. The result also reports the exact
per-leaf score sums used for the draws.

The experiment does not include a held-out word permutation null. That control
can be added as a separately named exploratory analysis.

## Limits

The result is conditional on paragraph selection, tokenization, transcription,
and folio grouping. A lower held-out NLL can result from repeated forms,
section or scribal structure, or other regularity. It cannot establish a
language, meaning, authorship, or translation. The `<->` and `<~>` filters
remove unclean adjacencies, but they can also change the population that the
score describes.

The character model uses accepted tokens from records with excluded tokens.
The context model excludes the whole paragraph line in that case. These
filters answer different questions and must not be treated as one corpus.
