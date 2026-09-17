# Homophonic anneal review

Review date: 2026-09-17.

This internal computational review covers `experiments/homophonic/anneal.py` and
`experiments/homophonic/test_anneal.py`. It uses the core model in
`src/voynich/substitution.py` as an independent comparison. It does not read
reference or manuscript data.

## Result

The current annealer passes this review. It returns a complete key that
respects the declared capacity. Its score is a fixed-boundary character
n-gram score. It does not calculate the exact lexical objective.

The returned key is a feasible warm start for the exact lexical solver. The
runner must score that key again with the lexical objective. No anneal field
claims a decipherment, a language result, or an exact lexical optimum.

## Mathematical checks

The event builder creates one event for every cipher unit and one end-of-word
event for every word. It adds the required beginning-of-word symbols and does
not create transitions between words. The event scorer maps cipher units in
both contexts and targets, then applies the fitted model's add-alpha formula.

I compared the score with the core `fit_language_model`,
`score_with_key`, and `score_with_key_incremental` functions. The independent
check used synthetic words, empty words, orders zero through four, and
add-alpha `0.1`. All five injective score comparisons matched to less than
`1e-12`.

I also decoded each synthetic word with duplicate maps and summed the model
probabilities directly. The check covered 15 cases: capacities two, three,
and unlimited, across the five orders. Every result matched.

Empty words produce one end-of-word event. The empty-word check matched the
direct beginning-of-word to end-of-word probability for all five orders.

## Incremental search checks

The incremental scorer marks every event that contains a changed unit in its
context or target. Random trial and commit checks covered capacities one,
two, and unlimited. They performed 507 feasible commits across synthetic
words, including an empty word. Each trial delta and each committed total
matched a fresh full score within `1e-9`.

Finite-capacity initialization fills bounded slots. Swap moves preserve the
counts. Reassignment moves use only letters below capacity. The independent
checks found no capacity violation, and the focused tests cover full key
coverage for finite capacities.

The same seed and inputs produced identical complete results. The result
records `iterations * restarts` as the declared move budget and records
proposed and accepted moves separately. This defines a fixed search budget,
including runs with zero iterations.

The annealer has no oracle key, reference key, test split, or held-out input
parameter. It fits the model from `train_words` and scores only
`encrypted_fit_words`. The result contains no oracle or reference-key field.

## Resolved findings

The earlier final check compared a fresh incremental score with the full
score, but it did not check the accumulated `best_score` used by the search.
An injected commit fault produced different selected and full scores while
the old `full_score_verified` field remained true.

The current code compares the selected accumulated score with the full score.
It uses relative tolerance `1e-12` and absolute tolerance `1e-8`, reports the
absolute error and tolerance, and raises an assertion on drift. The regression
test `test_search_accumulation_drift_is_detected` covers this fault.

The earlier result configuration omitted the start temperature and the
effective plaintext alphabet. The current configuration records
`start_temperature`, the temperature schedule, `plaintext_alphabet`, and
`alphabet_source`. These fields make the declared search settings visible.

The focused command passed 12 tests:

```text
PYTHONPATH=src:. python -m unittest experiments.homophonic.test_anneal -v
Ran 12 tests ... OK
```

No unresolved correctness defect remains in this review scope. The anneal
score remains a character-model search score. Exact lexical scoring and any
certificate remain the responsibility of the downstream solver.
