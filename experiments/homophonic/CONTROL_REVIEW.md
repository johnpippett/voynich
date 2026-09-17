# Synthetic control review

Review date: 2026-09-16.

This review covers `experiments/homophonic/controls.py`,
`experiments/homophonic/ambiguity.py`, and their focused tests. It uses no VMS
data and no reference corpus.

## Result

I found no blocking correctness defect in these two modules.

The three seeded families are fixed positive strata:

* `injective` has 26 units and maps each plaintext letter once.
* `cap2` has 52 units and maps each plaintext letter twice.
* `unlimited` has 52 units and maps every plaintext letter at least once.

The unlimited generator assigns distinct letters to one shuffled block of 26
units. The remaining units receive deterministic random letters. This is a
surjective fixture. It is not the full unrestricted map class.

`encrypt_words()` advances each letter cycle across word boundaries and resets
all cycles at the call boundary. `decode_words()` round-trips the output. An
experiment must call the function once for each partition. Splitting one
partition across calls changes the emission sequence.

The recovery metrics use these denominators:

* Full character metrics include every scored position.
* Full token metrics include every scored token.
* Observed-position metrics include positions whose unit is in `fit_symbols`.
* Fully observed token metrics include tokens whose units are all in
  `fit_symbols`.

An absent unit remains in the full denominators. A mapping outside
`fit_symbols` is ignored. This prevents a planted key from filling a missing
unit. Zero observed denominators return `None`. The fit set may contain units
that do not occur in the scored partition.

The ambiguity dynamic program counts assignments of labeled free units under
the supplied capacity. It fixes units used by positive lexical hits. It does
not change those hits, so every counted assignment has a score at least equal
to `incumbent_score`. The result separates that score from the completion
count. The count is an optimal-key lower bound only when the supplied score is
certified optimal.

An ambiguity count of one does not prove key uniqueness. For example, with
`{x: 1, y: 0}`, lexicon `{a, b}`, capacity one, and key `x -> a, y -> b`, the
reported completion count is one. The distinct key `x -> b, y -> a` has the
same optimal score. The module's `limit` field states this lower-bound limit.

## Actionable precision points

1. Keep the map class in public output. The planted `cap2` and `unlimited`
   keys are surjective fixtures. `preserved_hit_completions()` with capacity
   two or `None` counts the solver's at-most-capacity class, including maps
   outside those fixtures. Label these as separate classes.
2. Keep the partition reset contract beside every caller. The API resets at a
   call boundary, not at a named partition boundary.
3. Preserve lower-bound wording for `completion_count`. Do not call a count of
   one unique or report it as a complete optimum count.

## Checks

Focused tests passed:

```text
PYTHONPATH=src:. python -m unittest experiments.homophonic.test_controls experiments.homophonic.test_ambiguity -v
Ran 13 tests ... OK
```

An independent enumerator checked 540 random cases across capacities one, two,
and unlimited. It matched completion counts, covered-unit counts, and supplied
scores. All 96 seeded keys also passed independent encryption/decryption
round trips.
