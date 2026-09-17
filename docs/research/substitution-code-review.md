# Substitution search code review

Review date: 2026-09-16.

This review covers `src/voynich/substitution.py`,
`tests/test_substitution.py`, and `scripts/run_substitution_pilot.py`.
It covers scoring, key moves, held-out metrics, and run records.

The focused test file passes all six tests. An independent check also passed
for model orders zero through four. It checked 60 complete injective keys and
random swaps and unused-letter replacements. Direct event scores and trial
deltas agreed within `1e-9`. Conditional probabilities summed to one for
observed and unseen contexts. The pilot script also completed a five-word
smoke run without an oracle key in its search call.

## Checks that passed

* `fit_language_model` uses the vocabulary
  `alphabet + <UNK> + <EOS>`. Each row uses
  `total + add_alpha * vocabulary_size`. The probability rows normalized to
  one in the independent check.
* Direct scoring and compressed scoring use the same events. EOS contributes
  one prediction for each word. Unknown source symbols contribute their raw
  occurrence count and their distinct type count.
* `_IncrementalState.trial` included every event that contains either symbol
  in a swap. Its delta matched a fresh direct score for swaps and moves to an
  unused plaintext symbol. The final search score is recomputed from the
  returned key.
* `_propose_move` preserved injectivity. With three source symbols and five
  target symbols, the independent run produced both two-symbol swaps and
  one-symbol unused-letter moves.
* The pilot call to `search_substitution` has no `reference_key` argument.
  The pilot passes the planted key only to `score_heldout` after the search.
  The reference key does not affect initialization, proposals, acceptance,
  or the selected score. The same search result was produced with and without
  that optional argument.
* Held-out character accuracy weights occurrences. Held-out word accuracy
  counts eligible word positions. Both denominators exclude symbols or words
  that the supplied reference key cannot evaluate. The output reports each
  denominator.
* The temperature code converts bits per predicted symbol to total objective
  bits with `predicted_symbol_count`. Its acceptance exponent is therefore
  equivalent to a per-prediction temperature. The schedule reaches zero on
  the final iteration.
* The result records the seed, iteration count, restart count, restart-best
  objectives, and selected restart. The pilot records the planted seed, search
  seed, key hash, and source hashes. Repeated calls with the same inputs and
  seed returned identical results.

## Finding: undefined accuracy is emitted as zero

Severity: minor, but relevant to publication output.

`_recovery_metrics` returns `0.0` when an accuracy denominator is zero
(`src/voynich/substitution.py:695-720`). This occurs when the held-out text is
empty or when it has no symbol covered by the reference key. For example, the
current code reports `exact_word_total: 0` and
`exact_word_accuracy: 0.0`. Zero is a failure rate, while no eligible case is
undefined. A reader can mistake an undefined result for measured zero
recovery.

Keep the correct count fields. Return `None` for each rate whose denominator
is zero, or document and test the zero sentinel before publication. Add empty
and no-reference-overlap cases to the focused tests. The non-empty pilot
controls have positive denominators, so this does not change those controls.

## Advisory: keep the oracle boundary out of the search API

`search_substitution` still accepts `reference_key` and passes it to
`_recovery_metrics` (`src/voynich/substitution.py:739-879`). The current
implementation does not use it in the objective, and the pilot does not pass
it during search. The known-cipher unit test does pass it to search only to
obtain recovery metrics.

This is not an observed oracle leak. It is an API footgun. Remove the optional
argument from `search_substitution` and calculate recovery metrics with
`score_heldout` after search, or add a clear test that the key cannot affect
search state. Keep the pilot call pattern unchanged: search first, then score
the held-out ciphertext with the planted key supplied only for evaluation.

No other correctness finding was identified in this scoped review. The search
remains an exploratory optimizer over a fixed n-gram objective. Its output is
not evidence of a Voynich decipherment without the planned planted controls,
negative controls, and held-out evaluation.
