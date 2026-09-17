# Optimal-key identifiability study

Date: 2026-09-17.
Status: settings fixed before the first reference query.

## Question

The Latin homophonic control has a certified dictionary score and an incorrect selected map.
At least four maps attain this score.
This study asks which assignments are necessary to attain that score.
It does not change the failed exact-recovery result.

An assignment is conditionally identifiable here only if every optimal map contains it.
This definition concerns the specified finite dictionary objective.
Its target comes from the published source certificate.
It does not establish a historical reading or a probability of correctness.

## Fixed problem

Use the Latin `cap2` control with seed `7000` from the homophonic feasibility pilot.
Use its encrypted validation words and plaintext training lexicon.
Keep its 26-letter plaintext alphabet, observed cipher units, word boundaries, and capacity of two units per letter.

For each cipher word type, use weight `n*T + N`.
Here, `n` is its count, `T` is the cipher type count, and `N` is the token count.
The total denominator is `2*T*N`.
The certified target is `370396722`.

Use the selected map in `reports/homophonic-feasibility-v1/latin-cold.keys.json`.
Check its SHA-256 against the matching result record.
The baseline report SHA-256 is `923dba00df53ff05ca88e91362ea44c693d66b8f0824071d85cc5b0d984ba77e`.
Check the input, lexicon, source, and protocol hashes against that record.
Recompute the selected map's score before any query.
Bind the reconstructed objective and domain to one canonical SHA-256 fingerprint.

The existing optimum certificate comes from the published bounded solver.
The new query code does not independently prove that source certificate.
Record its provenance and public-source reproduction separately.

## Queries

For each observed cipher unit `c`, let `p` be its selected plaintext letter.
Ask whether a complete feasible map can reach the target with `c != p`.
Process units in lexical order. Keep all queries independent.
Do not carry assignments from an earlier witness into a later query.

First, try each alternative letter for `c` in lexical order.
Keep every other selected assignment fixed for these initial witness attempts.
Reject a changed map if it exceeds the capacity.
Score each remaining map with the same exact objective.
These attempts can supply a witness. Their failure proves no exclusion.

If no initial witness reaches the target, run the constrained threshold search.
Use a budget of 1,000 popped nodes for each query.
Branch by descending summed word weights for each unit, with lexical ties.
Count each word weight once per unit, even when the unit repeats within that word.
Generate every legal child before the next node-budget check.

The threshold remains fixed throughout the search.
Prune a branch only when its admissible upper bound is below the target.
A bound may ignore forbidden values for unassigned units. This can only weaken the bound.
Keep the bound for the live search frontier separate from any global score bound.
This study uses full bound recomputation in `threshold.py`.
The separate incremental adapter is not used in this run.

Use three outcomes:

- `ambiguous`: a complete alternative map reaches the target.
- `forced_at_certified_optimum`: the alternative domain cannot reach the target.
- `unresolved`: the node budget ends with a live possible branch.

A witness above the certified target contradicts the input certificate.
Stop and report the contradiction. Do not change the target silently.

## Output and checks

Write one result for each completed query, then write the aggregate result.
Refuse existing output files. Preserve incomplete runs and resource failures.
Record source hashes, the problem fingerprint, constraints, target, budget, nodes, status, and any witness.
Validate each witness against the complete domain and exact score.

After all query outputs are fixed, compare assignments with the known planted map.
Report forced, ambiguous, and unresolved unit counts separately.
Also report the test positions covered by each category and errors among forced assignments.
Do not repair ambiguous or unresolved assignments with the planted map.

Use exhaustive tiny problems to check each outcome before reference use.
Include positive dictionary hits that still permit alternative optimal maps.
Check zero budgets, capacity conflicts, forbidden values, repeated queries, and infeasible domains.
Compare incremental bounds with full recomputation before any accelerated run.

## Limits

This is a follow-up to an inspected control failure, not an unseen validation set.
One control does not establish general recovery performance.
An unresolved query does not prove ambiguity or exclusion.
An ambiguous assignment requires at least two concrete optimal maps, including the selected map.
Separate marginal witnesses need not occur together in one map.
The test contains no new Voynich measurement.

## Reproduction

Use Python 3.11 or later and the pinned reference inputs.
Run this command from the repository root with a new output directory:

```sh
python experiments/identifiability/run_assessment.py --output-dir results/identifiability-v1-latin
```

The command uses the fixed baseline report and a budget of 1,000 nodes per query.
It saves `run.json`, one file per unit, `decisions.json`, and `assessment.json`.
The final file includes diagnostics from the known control.
The source loader can read test files before queries. Test scoring follows the saved decisions.
