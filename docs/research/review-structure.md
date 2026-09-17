# Structure review

Review date: 2026-09-16.

Scope: `src/voynich/structure.py`, `tests/test_structure.py`, and
`docs/plans/design.md`.

## Result

The main structure calculations are mathematically correct for the stated
exploratory design.

* `within_word_entropy` counts character marginals over all tokens. Its
  conditional entropy uses only within-token transitions. It does not cross
  word boundaries.
* `edit_distance_at_most_one` agrees with ordinary Levenshtein distance at
  threshold one. Exhaustive checks over binary strings of lengths zero through
  four found zero mismatches.
* The null sampler shuffles indices within each selected line. It preserves
  each line's token multiset, token count, and token lengths. It does not
  mutate the input records.
* Exhaustive enumeration of all index permutations matched `_expectation` for
  single and mixed line sets, including unequal line lengths.
* The enrichment tails and the absolute tail for word length use the stated
  statistics. The plus-one Monte Carlo estimate is `(extreme + 1) /
  (permutations + 1)`.
* `holm_adjust` returns the standard Holm adjusted values. The known-value
  test returns `[0.03, 0.06, 0.06]`.

The 13 focused tests in `tests/test_structure.py` pass.

## Findings

### P1: An explicit `None` seed breaks reproducibility

`random.Random(None)` uses system entropy. Two calls with the same records,
`permutations`, and `seed=None` return different null samples. For example,
two seven-permutation calls returned initial-gallows null means `0.0` and
`0.14285714285714285`.

The design requires identical inputs and settings to produce identical
results. Reject `None` and require an explicit integer seed, or resolve a seed
once and record that concrete value in the configuration.

### P2: Empty accepted tokens cause an uncaught exception

`run_structure` accepts a record with three empty tokens, then raises
`IndexError: string index out of range` at `t[0]` in `_prepared_lines`.
The current parser does not emit empty tokens, so this is an API edge case.
Guard empty tokens before indexing or reject malformed records with a clear
error.

### P2: The H2 output name reports the wrong unit

`h2_bits_per_eva_character` is the empirical conditional entropy of the next
character given the current character, averaged over observed transitions.
Its denominator is `within_word_transitions`, not the total number of EVA
characters. For `['aab']`, the value is one bit per transition, while only
two of three character positions have a next-character observation.

Rename the field to `h2_bits_per_transition`, or report a separate
per-character quantity with an explicit boundary convention. This affects
interpretation across corpora with different word lengths.

## Null and selection limits

The initial word-length null is often asymmetric. For word lengths
`[1, 1, 10]`, its exact values are `[-4.5, -4.5, 9.0]`. The code uses
`Pr(abs(T_null) >= abs(T_observed))` around the analytical null expectation
zero. This is a valid radial two-sided randomization tail, but it is not an
equal-tailed test. Keep this choice explicit. Use a predeclared equal-tail
rule if that is the intended alternative.

The selection predicate includes `P*` records with at least three tokens, no
excluded tokens, and no `<->` diagram interruption. It excludes label and
other non-paragraph kinds. It does not inspect `paragraph_start` or
`paragraph_end`; this is consistent with line-level selection, but the design
should state this boundary rule clearly if those flags are later required.

All effects and p-values remain exploratory. A small p-value rejects only the
stated within-line exchangeability model. It cannot establish a language,
meaning, or decipherment.

## Resolution follow-up

Review update: 2026-09-16.

The three findings above are resolved in the current implementation.

* `run_structure` rejects a non-integer seed with `ValueError`. This prevents
  the nondeterministic `seed=None` case.
* `run_structure` rejects empty or non-string tokens with `ValueError` before
  `_prepared_lines` indexes a token.
* The conditional entropy field is now named
  `h2_bits_per_within_word_transition`. The CLI and focused tests use this
  name.

The focused validation run reports 13 passing structure tests. This review
does not make a current full-suite status claim.
