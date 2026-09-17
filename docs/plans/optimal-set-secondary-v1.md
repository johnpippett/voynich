# Complete optimal set in a fixed domain

## Status and question

This document defines a development study before its first reference run.
Publish this protocol and the reviewed implementation before that run.
The Latin control failure and its assignment results are already known.
This study is exploratory. It is not blind validation.

Can complete enumeration retain all dictionary-optimal maps within this control's fixed finite domain?
Can a fixed character model distinguish those maps without test scores or the planted key?
Report both answers, including ties and incomplete calculations.
Do not change the earlier failed recovery checks.

## Fixed inputs

Use the Latin LLCT reference partitions in the existing reference manifest.
Use the `cap2` synthetic control with seed `7000` and its cyclic emission rule.
Use the same validation ciphertext, training lexicon, alphabet, and capacity as the published Latin cold run.

| Input | SHA-256 |
| --- | --- |
| Reference manifest | `f261b781f150991e3305aae5057a94dc91afd8e59c58bb22ff199347f5ce3e6d` |
| Baseline report | `923dba00df53ff05ca88e91362ea44c693d66b8f0824071d85cc5b0d984ba77e` |
| Assignment run | `7345c627c7ec66d95f1b261963336d6e86ae0671d11558f54a246f91b536dc6d` |
| Assignment decisions | `607585729d72be0e3bbaaaadabc74225b774b66540ea08f061d0d0459edcfa3d` |
| Assignment assessment | `0f6401ee435f5bb6c71a8c4172b3c1ea44eaca440637ebc1b1d68c48979e3fbb` |

The fixed primary target is `370396722`.
Its objective and domain fingerprint is `05df3d40e478d73cebac63f282d17f897d013f8337111ab5533c2233d5eb6190`.
The fingerprint includes weighted ciphertext counts, the usable lexicon, the alphabet, and capacity `2`.

Check the baseline report, key record, source files, protocols, and stream hashes.
Check all 46 query hashes against the assignment decision record.
Reconstruct the objective from the source corpus. Do not trust a matching label alone.
Keep every earlier source file unchanged.

## Complete enumeration

The primary objective is the existing integer dictionary score.
For each ciphertext word type, its weight is `n*T + N`.
Here, `n` is its token count, `T` is the ciphertext type count, and `N` is the token count.

Fix only assignments classified as `forced_at_certified_optimum` by the published queries.
Each such query must forbid only that unit's selected letter and have no other fixed assignments.
It must have status `infeasible` and an upper bound below the target.
Its problem fingerprint, capacity, target, and source hashes must match this study.

Leave ambiguous and unresolved assignments free. Keep these two categories distinct in the record.
Give each free unit the full plaintext alphabet before capacity checks.
Do not restrict a free unit to letters found in earlier witnesses.

Enumerate complete maps in lexical unit and letter order.
Apply capacity `2` to the full map, including fixed assignments.
Score each feasible map with the exact primary objective.
Retain every map whose score equals the target.
A score above the target is a certificate conflict. Stop and retain the conflict record.

Set the raw Cartesian product limit to `1000000`.
Set the enumeration node limit to `1000000`, including the root.
If either limit stops enumeration, report an incomplete set. Do not rank that partial set.
Require the original selected map to occur in the complete retained set.
An empty complete set contradicts that required baseline witness.

The enumerator alone proves completeness only within its supplied fixed domain.
The complete optimal set for this fixed domain also requires the published score certificate and the forced-assignment exclusions.
Equal lower and upper bounds certify the score even when an earlier search has a live frontier.
That score certificate alone does not enumerate all optimal maps.

## Secondary score

Fit the existing conditional character model on the training plaintext only.
Use order `3`, additive smoothing `0.1`, and the fixed 26-letter ASCII alphabet.
Keep the frozen start, end, unknown-symbol, and word-boundary conventions.
The model vocabulary has 28 predicted symbols: 26 letters, the unknown symbol, and the end symbol.

Score decoded validation words with their token counts.
Do not use the primary objective weights for this score.
Use the exact rational event probability `(10*c + 1) / (10*t + V)`.
Here, `c` is the event count, `t` is its context total, and `V` is the vocabulary size.
This defines smoothing as the exact rational number `1/10`.

Compare likelihood ratios after common event counts cancel.
Use the lexically first candidate as the ratio baseline.
Use exact integer arithmetic for comparisons and ties.
Approximate base-two logarithms are display values only.

Set the remaining event-count limit to `4096` per candidate ratio.
Set the ratio size limit to `1000000` bits per numerator or denominator.
If any candidate exceeds a limit, report an incomplete ranking with no selected map.
Keep all exact maximizers. Use lexical order only to select a display map among ties.

The secondary score applies only within the complete primary-optimal set.
It cannot compensate for a lower primary score.
It does not prove historical truth, even when it selects one map.

## Output order and diagnostics

Use a new output directory. Never overwrite an existing run.
Write the input record, complete enumeration, and secondary ranking in that order.
Write the selection record before test scoring or planted-assignment diagnostics.
Record file hashes, source hashes, protocol hashes, settings, and every limit exit.
Preserve partial records when a later step fails.

Only after selection, compare all retained maps and secondary maximizers with the planted control map.
Then score each selected or tied map on the test partition.
Report exact assignment, character, and word agreement. Report unseen test units separately.
Do not use these diagnostics to change the model, candidate set, or tie rule.

The corpus loader can read test source files during input loading.
The ranking code must not receive test tokens, test scores, or the planted inverse map.
Use a guarded test iterator in synthetic tests to verify the output order.
Record the training model hash without publishing its full corpus-derived count tables.
Publish maps, aggregate results, exact ratios, and verification records only.

## Checks and interpretation

Compare each primitive with a separate exhaustive reference calculation.
Record the fixtures, expected results, and source hashes.
Test capacities `1`, `2`, and unlimited, empty results, ties, and limit exits.
Test malformed records, source changes, false exclusions, and certificate conflicts.
Run the existing core and experiment tests before publication.
Use a clean checkout at the recorded commit to rerun the fixed command.
Compare output hashes before reporting reproducibility.

A unique correct result would repair this inspected development control only.
A tie, incorrect map, or limit exit remains a result to report.
Neither outcome establishes a manuscript language or translation.
New seeds and text sources require a separate fixed calibration study.
