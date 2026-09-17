# Finite-window word-similarity test

Status: exploratory design. The full proposed pipeline has not run.
The [lean diagnostic](../../reports/LOCAL_MEMORY.md) is complete and this model branch is stopped.
It used 99 shuffles for each control. The optional synthetic suite and bootstrap were not run.
The manuscript data were inspected during earlier work. These results are exploratory, not blind confirmation.

## Question and data contract

Test whether a word is easier to predict when a recent word in the same line
is equal or one unit edit away. This tests local surface memory. It does not
test translation, language, meaning, or a historical copying process.

Represent each non-empty word as an immutable sequence of declared units. Keep
the source hash, parser policy, unitization, line identifiers, and group
manifest in the run record. Split by the pinned group manifest into disjoint
train, validation, and test groups. Keep both sides of every declared group
together. Never use a word from another line as context. Existing groups were
already inspected, so a new hash or split does not create previously unseen
evidence.

For every line with words `x[0] ... x[n-1]`, score only positions `t >= 1`.
Use these positions for the unigram baseline and every memory model. The first
word is used in training counts and as context, but is not an evaluation
target. A line with fewer than two words has no evaluation target.

Fit the target vocabulary from train only. Let `V*` contain train word types
with at least two occurrences. Let `V = V*` plus one sentinel `UNK`. Map every
train token of a singleton type to `UNK` for the frequency model. Map every
validation or test target to its member of `V*`, or to `UNK` when it is absent.
Keep the raw unit sequence of the previous word as context, even when it is
outside `V*`. Do not map that context to `UNK` before distance calculation.

With `alpha = 0.1`, let `n(w)` be the mapped train count for every `w` in `V`.
The singleton counts contribute to `n(UNK)`. Count all train positions,
including first words, and define

```text
P0(w) = (n(w) + alpha) / (N_train + alpha * |V|).
```

If train is empty, use `V={UNK}`, `N_train=0`, and `P0(UNK)=1`. Record the
vocabulary and all mapped counts. If `V*` is empty, set status
`degenerate_no_real_vocabulary`. Keep the mathematical score, but report it as
mapped-target loss, not complete-word identity. A high `UNK` rate can hide
errors on real word types. Validation must not add words, counts, or
parameters.

## Kernels and scores

Use exact Levenshtein distance on unit sequences. The distance-one test means
exactly one insertion, deletion, or substitution under the standard dynamic
program. Do not compare strings after an unrecorded normalization. Do not
assign a distance to `UNK`.

For a raw context sequence `c`, define the exact kernel

```text
K0(w | c) = point mass at c, if c is in V*
            P0(w),             otherwise.
```

The edit kernel uses only real vocabulary words:

```text
Z(c) = sum(P0(v) for v in V* if distance(v, c) == 1)
K1(w | c) = P0(w) / Z(c), if Z(c) > 0 and w is a V* neighbor
            0,            if Z(c) > 0 and w is not a V* neighbor (including UNK)
            P0(w),        if Z(c) == 0.
```

`K1` uses an open-vocabulary `c` when it has any exact distance-one neighbor.
It falls back only when `Z(c)==0`. `UNK` receives no edit distance. A neighbor
cache may accelerate this calculation, but it must return the same neighbor
set and probabilities as uncached dynamic programming. A cache miss must not
silently change a fallback.

At target position `t`, average the kernels for the available previous words
`x[t-r]`, where `r=1 ... min(W,t)`. Use a uniform average. Do not pad a short
line and do not cross a line boundary. For family `q` in `{0,1}`, use

```text
Pq(w | history) = (1-lambda) * P0(w)
                   + lambda * mean(Kq(w | x[t-r])).
```

The baseline is `P0`. Use `W` in `{1,4,16}` and `lambda` in
`{0, .1, .25, .5, .75}`. Because `lambda <= .75` and `P0` is positive, every
model has positive probability for every mapped target, including `UNK`.
The edit family tests edit context against the exact-cache family. Neither is
a claim that the family is a complete memory model.

For each model, report total target bits, bits per target, target count,
`UNK` target count and rate, context out-of-vocabulary rate, line count, and
group count. Break out targets and contexts by vocabulary membership. Use
`-log2(P)` in a fixed target order and `math.fsum` or an equivalent stable sum.
The absolute baseline contrast is

```text
delta_abs = baseline bits per target - model bits per target.
```

Positive `delta_abs` means lower loss than `P0`. It is not an order result:
`UNK` mapping, smoothing, and finite line vocabulary can produce this gain on
an independent-IID source. For a frozen model, also report the excess over the
tail-shuffle null:

```text
delta_order = delta_abs(observed) - delta_abs(tail_shuffle)
             = model bits(tail_shuffle) - model bits(observed).
```

Positive `delta_order` measures local order association after the line word
multiset is held fixed. Also report the selected exact and edit models as a
paired contrast. Do not choose the better family from test results. When `V*`
is empty, label this as mapped-target loss and report the
`degenerate_no_real_vocabulary` status with the score.

For the optional same-length null, use the analogous
`delta_order_length = delta_abs(observed) - delta_abs(same_length_shuffle)`.

## Freeze and evaluation

Fit `V`, `n`, and `P0` on train. For each fixed family `q`, select `W` and
`lambda` by validation total bits. Break equal-bit ties by smaller `lambda`,
then smaller `W`. Do not round before comparison. Save the complete validation
grid, the selected settings, vocabulary hash, and source and split hashes.

The 15 settings within a family are a predeclared selection grid, not 15
independent confirmatory tests. Report the full grid and one frozen test score
per selected family. Adding distances, windows, splits, or strata after test
inspection creates a new exploratory analysis.

If validation has no eligible target positions, return status
`abstain_no_validation_targets`. Do not select settings or treat zero bits as
a valid selection result.

After this freeze, score test once for `P0`, the selected `q=0` model, and the
selected `q=1` model. Test scoring cannot change vocabulary, counts, distance
rules, windows, smoothing, or tie rules. A model that has no eligible test
targets returns a missing score and a reason, not zero bits.

## Lean first diagnostic

Use the existing model and data for the first diagnostic. Fit train, select on
validation, and record `delta_abs` and `delta_order` for the frozen choice. If
the selected diagnostic model has `lambda=0`, stop the branch. Do not run the
optional synthetic suite or bootstrap. A positive absolute gain without
positive order excess is also a lead only; it can reflect line vocabulary,
`UNK`, or smoothing.

The wider synthetic controls, 499-permutation distribution, and group
bootstrap below are optional follow-up work. Run them only when the initial
manuscript diagnostic has a positive frozen `lambda` and an informative order
contrast. They do not change the probability contract above.

## Word-order null

The primary null keeps each line and its first word fixed. Independently
permute only positions `1 ... n-1` within that line. This preserves the exact
multiset of scored target words, their mapped `V/UNK` labels, line length, and
the train frequency model. It changes local order. Shuffling the first word
would change which target is excluded and would invalidate this comparison.
The `P0` total loss must be invariant, apart from summation round-off.

Use the same frozen model settings for every null replicate. The present
kernels have no order-dependent fit, so the primary conditional null shuffles
evaluation lines and does not refit the train model. If later code learns an
order-dependent parameter, define and freeze a separate null contract before
using it.

As a predeclared sensitivity null, partition each line's tail by unit length
and permute words only within equal-length positions. This preserves length at
every position as well as the tail multiset. Do not select between nulls after
seeing the VMS result. Lines with zero eligible targets have no score. Lines
with one eligible target have an identity permutation and no permutation
power. Report these counts and group them by eligible-target count. For a line
with two words, the only scored target and its context are fixed, so every
null permutation is identical. Longer lines can change only after the fixed
first context; report effective history lengths for each `W`.

For the lean stage, one fixed tail shuffle is sufficient to compute
`delta_order`. For the optional follow-up, use a fixed permutation count and
seed, proposed as 499 and seed 408. Use a separate predeclared seed stream for
the sensitivity null. Report the complete null distribution, its quantiles,
and the observed rank. Call the rank a conditional permutation summary, not a
normal-theory p-value.

For the optional follow-up, aggregate bits and target counts by held-out group.
For uncertainty, resample whole groups with replacement and use the same
sampled group list for paired models. Report a ratio of summed bits to summed
targets for each draw. Do not treat tokens or lines as independent
observations. Use a predeclared finite bootstrap count, proposed as 499, and
report the number of eligible groups.

## Optional synthetic controls and edge checks

If the initial manuscript diagnostic is informative, run the complete frozen
pipeline on separate synthetic data. Do not run this suite in the lean stage:

* An independent-IID source samples each word independently from a fixed
  lexicon and frequency distribution. It should not show a persistent
  `delta_order` beyond its calibrated null fluctuation. A positive `delta_abs`
  alone is not evidence of local memory.
* An exact-copy source copies a uniformly chosen word from the previous four
  positions with a predeclared probability, and otherwise samples normally.
  An edit-memory source makes one declared unit edit to such a word. Use a
  closed synthetic lexicon so the intended edit targets occur in `V*`.
  These controls should make the corresponding family detectable when power
  is adequate, without supplying hidden generator choices or held-out targets
  to fitting.
* Use hard cases with no repeated train type, no edit neighbor, an open or
  disjoint test alphabet, raw OOV contexts, duplicate words, empty contexts at
  line starts, empty lines, and one-word lines. Check finite probabilities,
  exact fallback, zero-target reporting, and equality of cached and uncached
  scores.

## Outcome meanings

Low counts of eligible tail words, open-vocabulary targets, and disjoint test
units can make this test weak. Report these strata before interpreting a
delta.

* Positive `delta_abs` with near-zero `delta_order` means that frequency,
  `UNK`, smoothing, or line vocabulary can explain the model gain. It is not
  evidence of local order.
* Positive `delta_order` against the uniform tail null but near-zero excess
  against the same-length null can reflect word-length position effects. The
  uniform null holds the line word multiset fixed. The same-length null also
  holds unit length at each position fixed.
* Positive excess against both nulls supports local within-line exact or edit
  association under this contract. It does not identify semantics, copying,
  morphology, a language, or a writing system.
* A selected `lambda=0`, or no positive order excess, gives no support for
  this finite kernel. A negative result rejects only this vocabulary, edit
  rule, window set, and split.

A persistent `delta_order` in the independent-IID control beyond calibrated
null fluctuation indicates a metric or layout problem. A similar result in
ordinary historical controls weakens a VMS-specific claim. The earlier
exploratory VMS inspection remains a limit on any later interpretation.
