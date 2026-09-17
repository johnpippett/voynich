# Independent model review

Review date: 2026-09-16.

This review covers `src/voynich/predictive.py`, `src/voynich/context.py`, the
model tests, and the command-line call sites. It uses small independent
fixtures. It does not repeat the full test suite.

## Confirmed finding

### `unseen_target_*` includes seen training singletons

`context._fit_model` keeps only words with at least two training occurrences in
`known_words`. `_score` then increments `unknown_targets` when a target is not
in `known_words`. The result copies this value into both
`unknown_target_count` and `unseen_target_count`.

This combines two cases:

* a target type that never occurs in training;
* a target type that occurs once in training and is pruned by the minimum-count
  vocabulary rule.

The second case is unknown to the fitted model, but it is not unseen in the
training data. A fixture with training tokens `singleton common common` and a
test target `singleton` returned `unknown_target_count = 1` and
`unseen_target_count = 1`, although `singleton` occurs in training.

Keep `unknown_target_count` for the model out-of-vocabulary count. Add the raw
training type set to `_Model`, count `raw_target not in training_types` for
`unseen_target_count`, and compute its rate with the same scored-target
denominator. Add a summary field such as `observed_training_words` so the two
definitions are inspectable. Keep per-leaf fields aligned if unseen counts are
reported there.

## Required reporting correction

The predictive null shuffles the unit sequence returned by `_unitize`.
Therefore:

* `raw_eva` shuffles Unicode code points within each token;
* `grouped` shuffles the declared grouped units within each token and keeps the
  characters inside each declared unit in their original order.

The current result config says that the null preserves character multisets,
which is true, but it does not say which units are shuffled. The research
documents call this a character shuffle. That description is false for the
grouped run.

Keep the current unit-level algorithm if the intended null is an order null for
each reported unitization. Add explicit fields for the shuffled unitization,
for example `raw_eva: code_points` and `grouped: declared_units`, and state
that grouped compound units retain internal order. Update the method and
validation documents and add a test that checks the grouped label. If the
intended null is a raw character shuffle for both outputs, shuffle raw token
characters before grouped unitization and document the resulting change in
group counts and vocabulary.

## Physical grouping and split review

For numeric folios, both modules use the same salt, SHA-256 digest prefix,
big-endian conversion, and modulo-10 buckets. Recto and verso records with the
same numeric folio therefore receive the same split. The manifest and seed
outputs are deterministic for an ordered input record list.

The grouping key remains a numeric folio proxy. It does not identify the
physical folded sheet when panels have different folio numbers. The current
`split_group` text that labels the numeric prefix as a physical leaf is too
strong for a confirmatory result. Use wording such as `numeric folio proxy;
foldout manifest not applied`, and retain the existing caution. A foldout
manifest is required before any physical-leaf claim.

The fallback behavior for missing or non-numeric folios is outside the normal
parser corpus. Keep a test or validation rule that rejects such records before
calling the split a physical grouping.

## CLI sample boundary

The CLI passes all paragraph records to `run_predictive`. This excludes labels,
but it does not remove records with a positive `excluded_tokens` count. The
character model then uses the accepted tokens from an incomplete locus. The
context model removes the whole locus because its line filter requires zero
excluded tokens.

This is a sample-definition difference. Choose one declared rule before
publication. For a complete-line comparison, filter `excluded_tokens == 0`
before `run_predictive`. If accepted tokens from incomplete loci are retained,
report that rule and its count in the predictive result.

## Checks that passed

* The predictive alphabet and both model vocabularies are fitted from training
  data. Test-only symbols map to `<UNK>`.
* EOS is scored once per token. BOS padding and mapped `<UNK>` histories are
  used at every fixed order. A direct order-two fixture produced the expected
  BOS, symbol, `<UNK>`, and EOS histories.
* Add-alpha rows in the predictive model and unigram/interpolated bigram rows
  in the context model normalize to one, including empty training rows.
* Context baselines score the same target positions. The explicit
  `target_positions_match` result is true on the independent fixtures.
* Leaf bootstrap differences use one resampled leaf list for both paired
  models. The estimate and each draw use a ratio of summed bit differences to
  summed target counts. This is a weighted, paired cluster bootstrap.
* Empty test or validation splits return zero target counts and null score
  intervals without a division error.
* Repeated runs with the same seed are equal and do not mutate input records.

The calculations remain exploratory structural measurements. They do not
identify a language, meaning, authorship, or translation.

## Scoped re-review of the current fix set

Review date: 2026-09-16.

The latest fix set resolves the two reporting findings above.

* `context._Model.training_types` now records every raw training type. The
  score separates vocabulary-unknown targets from true training-unseen
  targets. The model summary and per-group results expose both counts. The
  singleton fixture now reports `unknown_target_count = 2` and
  `unseen_target_count = 1`.
* The predictive result now identifies the null units for each unitization.
  Raw EVA shuffles single characters. The grouped run shuffles declared
  grouped units and records that it does not match the raw-character
  permutation distribution. The method documents and CLI report use the same
  terms.
* `groups.py` is now the shared split authority. Its conservative components,
  direct `85/86` union, and `fRos -> 85` alias are included in both manifests.
  Direct API checks assign `f85r`, `f86v`, and `fRos` to group `85`, bucket `1`,
  and `test` in both predictive and context runs. The grouping configuration
  states that candidate unions are assumptions and that the map is incomplete.
* The CLI configuration and report now state that character prediction keeps
  accepted tokens from incomplete lines while word-context scoring removes the
  whole line. This resolves the earlier undeclared sample difference.

The strict grouping path is now shared. Both predictive and context runs reject
an unsupported folio with the same `ValueError`. The method text now hashes
`group_id` and names the canonical `folio_group` key.

The scoped re-review has no remaining known model findings. The implementer
reports that the targeted fix tests pass, and an independent check confirmed
the strict rejection behavior. Results remain exploratory structural
measurements.
