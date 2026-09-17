# Cyclic quotient recovery v1

Status: stopped development draft, preserved at the research pause on 2026-09-17.
No reference-corpus fit or manuscript run occurred for this branch.

This plan defines a later plaintext-letter search after a ciphertext-only
observed pair relation is proved. It uses no manuscript data and reports no
gate result. It does not change the inspected controls or their earlier
gates.

## Fixed scope

Use the inspected Latin LLCT and Old Italian `cap2` controls with seed `7000`.
Use the validation ciphertext and the train-only reference lexicon. Keep the
26-letter lower-case alphabet and the exact capacity-two emitter: 52 declared
units form 26 pairs. Do not use a new seed, a manuscript stream, or a test
score during fitting.

Use the source, loader, and control pins from
`docs/plans/cyclic-pairing-control-v1.md`. Freeze this plan, the matching
evidence, and the solver dependencies before a result run. Use these fixed
settings:

| Setting | Value |
| --- | --- |
| Solver | `experiments.homophonic.solver.solve_lexicon` |
| Capacity | `1` over canonical quotient classes |
| Bound engine | `"bitset"` |
| Node budget | `100000` for each corpus |
| Initial key | Empty; no cold-start assignments |
| Symbol order | `branch_symbol_order(quotient_counts, weights=weights)` |
| Objective weight | `w(word) = n(word) * T + N` |
| Objective denominator | `2 * T * N` |
| CPU and wall time | One CPU; 300 seconds per corpus |
| Memory guard | 7 GiB sampled RSS, 0.25-second samples, 5-second grace |
| Tie rule | Lexicographically smallest visited feasible class key at the highest visited score |

Here `T` is the number of quotient word types and `N` is the number of
quotient word tokens. `weights` comes from the quotient validation counts.
Do not change these settings after a score is known.
Equal score bounds certify the objective value. They do not certify the globally
smallest tied key while a search frontier remains.

The loader may parse, tokenize, and hash all source partitions before fitting.
Only the train lexicon and validation ciphertext counts enter the solver.

## Evidence gate

Build the complete 52-unit compatibility graph from the validation ciphertext.
The gate must produce at least one full matching witness. Multiple known full
witnesses are acceptable; the run must not select one. A missing witness or an
infeasible graph is a gate failure.

For every observed unit, classify its observed mate relation over all feasible
full matchings:

* A closed pair `(u, v)` is valid only when `(u, v)` is forced. Removing the
  edge must have an exhaustive no-matching result.
* An open singleton `u` is valid only when every candidate edge from `u` to an
  observed unit is disproved. An absent graph edge is a negative certificate.
  A present edge needs an exhaustive edge-constrained no-matching result.
* A budget stop, an unfound witness, or an untested candidate remains unknown.
  Unknown is not a negative certificate. The protocol may abstain when an
  unknown query is required for the relation gate.

If an observed unit has a possible observed mate that is not forced, the
observed relation is not identifiable. Stop the quotient run. Do not choose a
matching witness to resolve it. A singleton is permitted only when the full
matching exists and all observed-mate alternatives are disproved. Its mate
must therefore be unseen, but its identity remains unresolved.

The gate must prove the same partial matching `R` for every full completion.
Record the forced observed-observed edges, all negative certificates, all
known full-matching witnesses used as evidence, and every unknown or skipped
query. Do not call a relation unique from one witness.

## Immutable quotient

Construct the quotient from `R`, without selecting any ambiguous unseen
completion. Use a canonical class identifier made from the sorted member
units. Pair member order has no effect on the class identifier or the lexical
search.

For each closed pair, store two members and zero open slots. For each open
singleton, store one observed member and one open slot. Keep the complete
compatibility graph and its recorded orientations as evidence.
Remove forced observed-observed pair endpoints to form the residual graph.
Its vertices contain the open singletons and all unseen units.
Its full perfect matchings represent all feasible unseen completions.
Each completion combines with the fixed observed pairs to give a full matching.
An individual residual edge is a compatibility candidate. Do not claim that
it belongs to a full matching without a separate extension certificate.
Do not assign an unseen unit to a singleton. Do not pair two unseen units for
the quotient. These choices belong to a later residual completion problem.

The quotient is admissible only when every full matching maps to the same
observed classes. A retained residual state means a full residual matching,
not an isolated candidate edge. It must extend with the fixed observed pairs.
A closed pair consumes the exact two-unit capacity of one letter.
An open singleton consumes one unit and can accept at most one unseen mate.
If no observed-observed edge exists for a unit, record that graph absence. If
all present observed-observed edges are disproved, the unit is an open
singleton. If no unseen extension then exists, the full matching gate must
fail. Never turn a missing or unknown mate into a guessed letter.

For an open singleton, its observed unit is the first cycle unit where it
appears. The unseen mate and its identity remain unknown. A wholly unseen pair
has no observed orientation. Keep cycle orientation separate from the
plaintext class.

## Injective letter search

Transform each validation ciphertext word by replacing each observed unit
with its canonical quotient class. Keep word boundaries and multiplicity.
Use only the frozen train lexicon as plaintext candidates. The fit input is
the transformed validation counts and that lexicon.

Search one injective map from observed quotient classes to the 26 lower-case
letters. A closed pair and an open singleton each represent one distinct
plaintext class. This injective map is valid because the exact capacity-two
emitter has one pair per letter; two observed classes cannot share a letter.
The unresolved unseen units are outside the fit map and receive no guesses.

Use the frozen finite-lexicon solver interface with the settings above. The
objective must use validation word counts and types only. The search must
receive no planted pair map, planted letter map, planted orientation, target
score, or selected unseen completion.

Record the quotient evidence hash, class count, open-slot count, solver
configuration, lower and upper scores, node status, and the class-to-letter
map. A budget-exhausted lower bound is not certified. Report an inconclusive
status unless the solver certifies the score. Do not repair missing classes or
unexplained symbols.

## Key and test boundary

Write the complete quotient key record with exclusive creation before any test
scoring or accuracy diagnostic. The runner may parse, tokenize, and hash all
test source before this point. It must encrypt or score the held-out test
stream only after this key record is durable. Test data cannot change the
quotient, map, objective, tie rule, or status.

On the test stream, map observed units through the saved quotient key. Count
every unseen or otherwise unmapped unit as unexplained. Do not assign a
fallback letter. Report mapped positions, unmapped positions, complete-word
coverage, and finite-lexicon hits with their denominators.

If exact control-key accuracy is measured, use the planted control mapping
only after the quotient key is saved and label that value as a post-fit
diagnostic. Do not use it to construct the quotient, search, choose a tie, or
select an orientation.

This protocol can test a finite control objective. It does not identify a
language, prove a plaintext, or support a Voynich manuscript claim.
