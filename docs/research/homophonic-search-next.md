# Next homophonic search design

Date: 2026-09-17.

This note reviews the fixed Old Italian `cap2` reference search.
It proposes development steps for synthetic controls.
These proposals have not been tested on reference data.
They do not change the published result or use the planted map for selection.

Reviewed hashes:

- `experiments/homophonic/anneal.py`: `acc88067d1350180d7704db39b1d7f70070dd5a703dc07b27b98b090d6294ea5`
- `experiments/homophonic/solver.py`: `5e5b0d1bd21dcdf850d9154c088065d2cd6174671083dc6b5b935282da0c2760`
- `experiments/homophonic/bitset_bound.py`: `8ab50b9700497cc493e0ba79a9fc6d452cf95e5b8c7d9d19d0de08b567000f76`
- `reports/homophonic-feasibility-v1/italian-cold.json`: `4209022e13399bb7347b8f1d098f43c4d0922ae1b9c6df72382ed5553b44b0b3`
- `reports/homophonic-feasibility-v1/italian-assisted.json`: `461ddb0d5f097227d7d521436a3a6ebb459b8d53de973ed2e1e913af3be42f31`

## Current diagnosis

The published Italian runs use 47 fitted cipher units, 14,170 cipher word
types, and 12,549,021 root-compatible candidate rows. The bitset metadata
estimates 1,759,288,862 bytes for its masks. With 1,000 nodes, the cold run
has lower bound `90866594`, and the annealing run has lower bound `222253278`.
Both runs have upper bound `815036950`, zero pruned nodes, and 24,429 frontier
nodes. The assisted lower bound is higher by `131386684`, but its gap to the
recorded planted-map diagnostic score `703681524` is `481428246`.

The planted score is a post-fit diagnostic and a feasible lower bound for this
finite objective. The true optimum is at least this score and may be higher.
The score is not a target, fixing, or search input. The fitting code must not
receive the planted map or a fixing derived from it.

The annealer optimizes a smoothed character negative log probability. The
exact solver optimizes weighted word hits with weight `n*T+N`. The two scores
measure different properties. The annealing map therefore supplies a valid
incumbent, but it need not supply a strong lexical incumbent. The Italian
assisted run kept the annealing score after its 1,000 exact nodes.

The current upper bound adds the weight of every word type with one compatible
candidate. It checks repeated units and capacity against assigned units. It
does not require compatible candidates for different word types to occur under
one unassigned map. This independent-candidate relaxation explains why the
upper bound remains loose while no node is pruned.

The current branch order uses summed word weight for each unit. It does not
measure candidate-domain certainty or child-bound reduction. A unit with few
legal values can support minimum-remaining-values branching. A unit with more
values can still split the upper bound well. Candidate-value agreement alone
does not prove weak branching because wrong-letter children may prune. Treat
candidate-disagreement and constraint-based orders as unproven heuristics, not
as a diagnosis of this frontier. Compare them on locked synthetic controls.
Increasing the node budget alone will spend more work in this broad frontier.
The 1.76 GB mask estimate also makes a per-frontier active mask unsafe.

The current control family uses deterministic per-letter cyclic emission for a
fixed `cap2` key. It does not calibrate arbitrary random homophone selection.
The language and reference chunks are fixed. An objective-aligned method must
first pass a tiny `cap2` cyclic-emitter gate. Predeclare new seeds and text
sources before any later control family. A noncyclic emitter requires its own
calibration and report.

## Ranked development steps

### 1. Build a lexical incumbent before exact search

Add a separate warm-start method that uses the exact integer word-hit score.
Keep the existing character annealer as a separate diagnostic.
Use the complete map's exact score as a lower bound.
Do not fix assignments from the warm start.

Use the candidate rows already defined by equal word length, repeated-unit
equality, and capacity. Select high-weight cipher word types in a fixed order.
For each partial map, add compatible candidate-row assignments, complete the
remaining units with a capacity-valid map, and score the complete map with the
exact lexical objective. Keep a fixed-width beam and several deterministic
restarts. A candidate row may be sampled only for this heuristic. The exact
solver must retain its complete domain.

After each seed, run exact lexical local search. Use single-unit reassignment
and two-unit swaps first. Track only word types containing a changed unit, so a
move score costs the incident word types rather than all 14,170 types. Add
small blocks of two to four linked units when single moves reach a plateau.
Bound every block by a declared product or move budget. A complete map with an
exact score is always a valid lower bound, even when the heuristic finds no
global optimum.

This method should give the exact search a map that directly rewards the
objective it must improve. It can overfit the finite training lexicon. That
is an expected limitation of a lower bound, not a certificate. Record the
method, seed, move budget, selected score, and full map. Do not use test words
or the planted key. A strong incumbent inferred from the planted score is not
available to fitting.

### 2. Reuse one active bitset while expanding a node

The current `BitsetBound.bound(partial_key)` rebuilds the active candidate mask
from the root for each child. Add an internal development path that computes a
parent active mask once, applies one new unit assignment, computes the child
bound, and discards the child mask after it is pushed.

Keep active masks out of frontier nodes. One active mask is about 1.6 MB for
the Italian slot count. A mask per 24,429 frontier nodes would require tens of
GB before Python object overhead. Reconstruct a parent mask when the node is
popped, or keep only one temporary search path. This changes search cost and
does not change the bound value.

For every capacity, compare the incremental result with the existing scalar
bound on exhaustive tiny maps. Include one and two units assigned to the same
letter. If any incremental calculation fails, use the existing full
recomputation. Never use a failed or incomplete incremental calculation to
prune a branch.

This step has low method risk. It can support a larger exact node budget, but
it does not by itself tighten the upper bound or establish a better map.

### 3. Replace weight-only order with candidate-disagreement order

First test a cheap static order. For each unit and each cipher word type,
compute the set of plaintext letters used by its root-compatible candidates.
Rank units by a fixed weighted disagreement measure, such as

```text
sum(weight(word) * (1 - 1 / number_of_candidate_letters))
```

over word types that contain the unit. Use current summed weight and lexical
order as tie breakers. This measure favors units that can split many weighted
candidate rows. It needs one candidate scan and small per-unit counters.

Only after this passes synthetic tests, test dynamic order at a node. Consider
the few highest static candidates and choose the unit with the largest
predicted reduction in the child upper bound. Evaluate all legal plaintext
letters. Branch order alone is admissible because it visits every legal
assignment.

The current heap tie key assumes one fixed `symbol_order`. A dynamic order must
store an explicit branch path or canonical assignment key. It must not reuse
the current prefix expression with a different order at each node. Record the
order strategy and tie rule in the result.

Dynamic order can cost more bitset operations than it saves. Measure nodes,
child bounds, wall time, and peak memory. Keep the static order when the
dynamic method does not reduce work on locked synthetic controls.

### 4. Add a guarded weighted candidate-consistency bound

The strongest likely upper-bound improvement is a safe grouping relaxation.
Partition selected cipher word types into groups. Assign each group to a pivot
cipher unit that occurs in every word in that group. For a partial map `P`, let
`C_w(P)` be the active candidate rows for word type `w`. For plaintext letter
`p`, compute the weight of group words with at least one row in `C_w(P)` that
maps its pivot to `p`. The group upper bound is the maximum of those weights
over legal `p`. Add the weights of ungrouped word types in full.

Every complete map assigns one letter to the pivot. Therefore the hit weight
in a group cannot exceed its maximum pivot-letter weight. Capacity and
conflicts between groups are ignored, so this is an upper bound. Combine it
with the current bound only after differential tests prove the inequality.

Use all candidate rows for a group. If a heuristic sample omits rows, add the
whole word weight to the residual instead of treating the sample as complete.
Otherwise the result can understate the bound and prune a valid optimum.

Do not allocate a full mask for every unit and letter by default. The Italian
run already uses about 1.76 GB of mask storage. Start with a small, fixed set
of high-weight groups and sparse or on-demand masks. Stop using the new bound
when its construction exceeds the declared memory budget or its subsearch is
not complete. Fall back to the existing admissible bound.

If grouping is not strong enough, test an exact component bound on small
candidate-overlap components. A component bound may ignore capacity links to
other components, which keeps it admissible. A resource-limited component
search must fall back to the current bound and must not report a guessed value.

## Synthetic gate before any reference revision

Freeze one algorithm version, parameter tuple, random seed policy, and output
schema before reading a new reference result. Use the existing synthetic
families and reserved seeds. Keep separate development and locked confirmation
seeds. The algorithm may receive only encrypted validation words and the
plaintext training lexicon. It must not receive the planted map, plaintext
validation words, test words, or a fixing derived from them.

For each locked control, record:

- exact lexical lower bound before and after each warm-start stage;
- nodes, pruned children, frontier size, and upper-bound gap;
- wall time, peak memory, and candidate-mask storage;
- whether the exact result is certified;
- the heuristic seed, budget, map hash, and objective hash.

Use the planted map only after selection to measure the control diagnostic. Do
not tune a method to the planted score. A change that changes the frozen
objective or weakens bound soundness fails. For the same objective and domain,
the certified optimum is exact and must not change. A changed certified score
is a correctness failure. A different finite-budget incumbent is not itself a
correctness failure.
Compare every candidate bound with direct products on tiny domains for
capacities `1`, `2`, and `None`. Include repeated units, empty candidate lanes,
zero weights, fixed capacity conflicts, and target scores above and below the
true optimum.

The current frozen synthetic checks pass: 35 tests cover the solver, bitset
bound, and annealer. They do not validate any of the proposed new methods.

## Limits

These steps improve search over one finite homophonic map and one finite
surface lexicon. They do not establish a language, a historical reading, or a
decipherment. A stronger incumbent is still only a lower bound. A tighter
bound is valid only after an independent proof and exhaustive tiny tests.
Original Italian search uncertainty and the failed control gates remain.
