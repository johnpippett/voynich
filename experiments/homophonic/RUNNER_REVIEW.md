# Homophonic runner review

Review date: 2026-09-17.

This review covers `experiments/homophonic/run_controls.py` and
`experiments/homophonic/test_runner.py`. It did not read or run reference
corpora or VMS data.

This is an internal computational review. It does not provide scholarly
validation, language validation, or evidence of a VMS decipherment.

## Result

I found no blocking defect in objective selection, oracle isolation, key
freezing, bound reporting, or recovery metrics.

The runner constructs weights as `count*T+N`, where `T` is the number of
validation word types and `N` is the number of validation tokens. The reported
denominator is `2*T*N`. The solver receives these weights. The report rebuilds
the objective from raw validation counts and checks that both scores agree.

The solver receives encrypted validation words and the unique plaintext
training lexicon. It receives no planted key, test words, or test score. The
annealing warm start receives validation ciphertext and plaintext training
words only. The exact solver receives that map as an incumbent. Its root has
no fixed assignments. The selected key record is written before the runner
first iterates the test partition.

The public solver record excludes raw candidate word arrays. It keeps aggregate
candidate counts and bitset metadata. The report keeps six aggregate plaintext
and ciphertext stream hashes, the selected key, and the synthetic planted
control key. It does not expose plaintext or candidate word lists.

The runner checks that the planted validation objective is no greater than the
reported solver upper bound. This catches an unsafe upper bound. The recovery
metrics report full positions, fit-observed positions, fully observed tokens,
and absent positions. The planted metrics use all planted units. Missing fitted
units receive no guessed assignment.

The ambiguity count is labelled as a lower bound. The runner sets
`optimal_key_count_lower_bound` only when `score_certified` is true. A budget
stop therefore cannot produce an optimal-key claim.

The cold and annealing paths use separate settings. The annealing path records
order 3, additive smoothing `0.1`, eight restarts, 2,000 iterations per
restart, seed `408`, and start temperature `0.02` when the documented command
is used. The cap2 seed `7000`, node budget `1000`, and bitset engine are
explicit in the first reference command. Code, protocol, key-record, fit
ciphertext, all six input-stream, and training-lexicon hashes are recorded for
a reference run.

The focused runner, bitset, controls, annealing, and solver tests passed:

```text
PYTHONPATH=. python -m unittest \
  experiments.homophonic.test_runner \
  experiments.homophonic.test_bitset_bound \
  experiments.homophonic.test_controls \
  experiments.homophonic.test_anneal \
  experiments.homophonic.test_solver -v
Ran 48 tests ... OK
```

## Audit resolution

The protocol says to encrypt training, validation, and test words for audit.
The report now includes hashes for the complete ordered training, validation,
and test token streams and their encrypted streams. These hashes preserve
duplicate tokens and word order without exposing raw words.

The encrypted training stream is created only while the post-fit report is
built. It is not passed to the solver or the annealing warm start. The
validation stream remains the only fitting ciphertext. The test stream remains
post-freeze scoring input.

The audit gap is resolved. This review remains an internal computational
review; it does not claim scholarly validation.
