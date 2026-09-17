# Optimal-set method review

Review date: 2026-09-17.

This review covers `docs/plans/optimal-set-secondary-v1.md`,
`experiments/optimal_set/enumerate.py`,
`experiments/optimal_set/secondary.py`, and `README.md`.
It uses no reference fit, ranking, or enumeration.

## Result

The composition is sound for one declared finite domain if the runner enforces
all gates below. The current modules support these gates. They do not prove
them by themselves.

The result is a conditional finite-domain statement. It is not a language,
translation, or historical-authorship result.

## Complete-set condition

Let `D` be every complete ciphertext-unit map that uses the declared alphabet
and satisfies the declared plaintext capacity. Let `S(K)` be the exact integer
dictionary score. Let `K0` be the baseline map and let `T = S(K0)`.

A complete optimal-set claim needs these conditions:

1. An independent certificate proves `max(S(K) for K in D) = T`.
2. Each forced query excludes only `K0[c]` for one unit `c`, uses the same
   objective domain, and proves that no map at or above `T` remains.
3. The forced queries cover every unit that the runner fixes. Ambiguous,
   unresolved, and unobserved units remain free.
4. Enumeration checks every capacity-valid completion of those fixed values,
   with the full declared alphabet, and stops with `complete: true`.
5. The retained maps are exactly the maps with score `T`, and `K0` is present.

Under these conditions, every global maximizer must obey every forced value.
It is therefore in the enumerated domain. Exhaustive enumeration finds every
map with score `T`. The certificate shows that no map has a higher score.
The retained set is then the complete optimal set for `D`.

The proof does not use the planted key or a test score. It applies only to the
recorded finite objective, alphabet, capacity, lexicon, and word boundaries.

## Required runner gates

### Value certificate

Require `score_certified: true`, `lower_bound == upper_bound == target`, and a
feasible baseline key whose exact score is `target`.

Check the objective fingerprint, ciphertext counts, lexicon normalization,
alphabet, capacity, weight formula, and source hashes against the baseline.
Record the report hash and key-record hash. A numeric equality without a valid
bound certificate is insufficient.

The baseline may have `search_exhausted: false`. A valid upper bound can certify
the value while the search has a live frontier. Record `search_exhausted`,
frontier size, bound engine, and bound metadata. Do not treat that frontier as
a key-set enumeration.

### Forced exclusions

For each forced unit, require all of the following:

- The query forbids only that unit's selected baseline letter.
- The query has no other fixed or hidden constraint.
- Target, capacity, alphabet, objective fingerprint, settings, and provenance
  match the value certificate.
- The query reports an exhausted, valid infeasibility proof with an upper bound
  below `target` and no witness.

An unexhausted search with no witness is not an exclusion proof. Accept it only
if its record contains a separate valid global upper-bound certificate.

Derive fixed assignments from the validated query records and the baseline
map. Do not trust a separately supplied fixed map. Require an exact partition
of the observed ciphertext units. Reject duplicate, missing, extra, unknown,
and contradictory unit records.

The known primary result has 45 forced units and one ambiguous unit, `c40`.
The free unit must receive the full alphabet before capacity pruning. The known
residual capacity facts may reduce its feasible values, but they must not be
used as a hand-written candidate list.

### Complete enumeration

Require the enumerator to record the full alphabet, fixed assignments, free
units, capacity, target, product bound, node limit, visited nodes, feasible
leaves, truncation state, and domain fingerprints.

Treat `product_limit`, `node_budget`, and `certificate_conflict` as incomplete
or contradictory outcomes. Never rank maps collected before a stop or conflict.

Require these checks before secondary scoring:

- The enumeration has `complete: true` and no conflict.
- The baseline map is complete, feasible, and retained.
- Every retained map is complete, capacity-valid, unique, and scores `target`.
- The retained-map count and a canonical map-set hash are recorded.
- The full retained maps remain available for secondary scoring.

If the baseline map is absent, report a contradiction. Do not repair it with
the planted map or with a test result.

### Secondary model

Fit the model from plaintext training words only. Score the encrypted
validation words with their token counts. Do not pass validation plaintext,
test words, test scores, or the planted inverse map to the ranking function.

Record the model hash, training stream hash, order, alphabet, boundary symbols,
unknown-symbol rule, vocabulary size, and event convention. Record smoothing
as the exact rational `alpha = 1/10`, with probability
`(10*c + 1) / (10*t + V)`. Do not rank with the binary-float likelihood or
with approximate logarithms. Approximate base-two log values are display values only.

Require every retained primary map to receive an exact `Fraction` score. A
delta or ratio limit must produce `not_complete` and no selection. Record the
canonical ratio-baseline map and the exact numerator and denominator for each
candidate.

Keep every exact secondary maximizer. A lexical display map is a presentation
choice, not a unique solution. Record the maximizer map identifiers, tie count,
display identifier, and baseline identifier separately.

## Selection and diagnostics

Write the selection record before the test iterator or planted-key comparison
runs. Include the hashes of all input, enumeration, and ranking records.
Record the selection hash before test access when possible.

Run diagnostics after selection. Report assignment, character, and word
agreement for each selected or tied map. Report unseen test units separately.
Keep these diagnostics outside the candidate-generation, ranking, and tie rule.

The study follows an inspected development failure. Mark it as post-hoc
development and not blind validation. A clean replay proves reproducibility,
not blindness. Do not present a display map, test score, or planted-key match
as a manuscript reading.

## Record requirements

The input record should contain relative paths and hashes for the baseline
report, key record, assignment run, decision record, every query record, source
files, protocol files, reference partitions, model inputs, and validation
ciphertext. It should contain the objective and search fingerprints, target,
alphabet, capacity, unit partition, and limits.
The public verification record must identify the published implementation commit.

The enumeration record should contain the complete map set or a reproducible
map-set artifact hash. It should preserve all limit exits, conflict details,
baseline inclusion, map count, and score checks.

The ranking record should contain model settings and hash, candidate-set hash,
candidate count, exact ratios, exact maximizer identifiers, and display choice.
The selection record must show that the primary set was complete before it
names any display map.

## Tests required before freeze

Add or retain synthetic tests for these composition failures:

- A value certificate with a live frontier is accepted only for value, not for
  key-set completeness.
- A certificate with unequal bounds or an invalid fingerprint is rejected.
- A missing, duplicate, extra, constrained, or unexhausted forced query is
  rejected.
- A free unit receives the full alphabet and capacity supplies the pruning.
- A partial enumeration, score conflict, missing baseline map, duplicate map,
  or empty retained set blocks ranking.
- Exact secondary ties retain all maximizers and choose a separate display map.
- The guarded test iterator runs only after the selection record exists.

No current record supports an exact count or ranking of all manuscript keys.
The planned result can certify only the fixed Latin control domain described by
the recorded inputs.
