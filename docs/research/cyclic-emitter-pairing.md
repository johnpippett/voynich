# Cyclic emitter pairing

Status: synthetic design note. Date: 2026-09-17.

This note studies the fixed capacity-two control emitter. It uses no Latin,
Italian, Voynich, manuscript, reference, or test stream. It does not report a
decipherment.

The frozen control maps each cipher unit to one lower-case letter. In the
capacity-two family, each letter has two cipher units. The emitter stores an
ordered cycle for each letter. It uses the next unit in that cycle for each
occurrence of the letter. It carries the offset across word boundaries. It
resets all offsets at each partition boundary.

The reviewed control implementation is
`experiments/homophonic/controls.py`, SHA-256
`4845d1de4e766c5d63b23919bab2715db24b431ba502112494e477a1740fd896`.

## Pair compatibility

Let `U` be the declared cipher-unit inventory. For one partition, flatten the
words in their input order. Word boundaries do not reset a cycle.

For two distinct units `u` and `v`, project the flattened stream by removing
every unit except `u` and `v`. Call the result `P(u,v)`. The pair is locally
compatible when these conditions hold:

1. Adjacent items in `P(u,v)` are different.
2. The counts of `u` and `v` differ by at most one.
3. Across partitions, every non-empty projection starts with the same unit.

The second condition follows from the first for a complete binary projection.
Keep it as an explicit audit check. It makes a count error visible.

An empty projection gives no orientation. A one-item projection gives the
cycle start. A unit can have an unseen mate only when it occurs at most once
in every partition. It can occur once in several reset partitions and still
have a total count greater than one. A unit that occurs more than once in one
partition cannot have an unseen mate in that partition.

Apply the first two conditions separately to every partition. Apply the third
condition because the cycle order is fixed while the offset resets. Do not
concatenate partitions before this check. A pooled count can differ by more
than one even when every partition is valid.

Build an undirected graph with one vertex for each declared unit. Add an edge
for each compatible pair. Store the first projected unit for each partition as
the candidate cycle orientation. A unit with zero total occurrences is an
`unseen_unit`. This term describes the observation. It does not identify its
mate.

## Exact matching condition

For a complete capacity-two inventory, a valid emitter pairing is a perfect
matching of this graph. The condition is necessary and sufficient when the
declared inventory is complete and the only input is the ciphertext stream.

For necessity, a true pair emits its two units in alternating order. Its counts
differ by at most one. Its first unit is the first item in the fixed cycle for
every partition where it occurs.

For sufficiency, take a perfect matching. Give each matched pair a different
plaintext letter. Use its first observed unit as the cycle start. Decode every
cipher unit to the letter of its pair. The alternating projection then emits
the observed units in the observed order. A pair with no observation can use
either orientation.

This construction proves emitter consistency. It does not identify the
plaintext letter assigned to a pair. Any permutation of the pair labels gives
the same ciphertext. For 26 pairs, the ciphertext-only label symmetry has up
to `26!` assignments.

The exact result has four useful cases:

* `none`: no perfect matching exists in the declared inventory.
* `unique`: one perfect matching exists, so the unit pairing is fixed.
* `multiple`: at least two complete matchings exist. Keep both witnesses and
  keep the pairing ambiguous.
* `unknown_budget`: the search stopped before it proved one of the cases.

A budget stop never means `multiple`. It can hide a unique matching or no
matching. An exhausted full search can certify a unique matching, including
for a 52-unit inventory. An odd full inventory is not a complete capacity-two
domain. An odd observed subset is not evidence that the emitter failed; its
mate can be unseen.

## Observed units and the full inventory

Run a matching check on the full declared inventory. Also record the observed
and unseen unit sets. A matching on the observed-unit subgraph has a narrower
meaning: it assumes that every observed unit pairs with another observed unit.
It says nothing about an unseen mate.

For example, use the declared inventory `a b c d` and the stream `a b`.
The observed subgraph has one pairing, `a-b`. The full graph has three
pairings, because `c` and `d` are unseen and all four one-item projections are
compatible. The observed result is conditional. It cannot justify grouping
`a-b` in the full inventory.

If the declared inventory contains only observed units, a missing mate lies
outside the search domain. Report the incomplete domain. Do not invent a new
unit or call the observed unit a singleton plaintext letter.

## Synthetic counterexamples

These short streams show why alternation is a constraint, not a general key
recovery method.

| Declared units | Partition stream(s) | Result |
| --- | --- | --- |
| `a b c d` | `a b c d` | Three perfect matchings: `ab-cd`, `ac-bd`, and `ad-bc`. |
| `a b c d` | `a b a b a c d c d c` | One matching: `ab-cd`. Cross-pairs have adjacent equal items in their projections. |
| `a b c d` | `a b a b a c` | One full matching: `ab-cd`; `c` occurs once and `d` is unseen. |
| `a b` | partitions `a b a` and `a b` | One matching with cycle start `a`. Resetting at the second partition is required. |
| `a b` | partitions `a b` and `b a` | No matching. The two partitions require opposite fixed cycle starts. |
| `a b c d` | `a a b b` | No full matching. The observed units have no compatible pair, and unseen `c-d` cannot cover them. |

The first row is a non-identifiability example. The third row is an
unobserved-mate example. The fourth and fifth rows test the partition reset
rule. None of these rows uses a language corpus.

The check also needs a complete stream for each declared partition. Removing
uncertain words or symbols can remove one side of a pair and change its phase.
A rejection on a filtered or discontinuous transcript does not reject the
historical emitter. A manuscript use would need an explicit gap model and an
unknown start phase for every gap. This helper has no such model.

## Bounded primitive

The optional synthetic helper is in
`experiments/cyclic_pairing/pairing.py`. It exposes:

* `build_compatibility(units, partitions)`, which validates the declared
  inventory and builds the graph;
* `enumerate_matchings(compatibility, scope=..., node_budget=...)`, which
  returns deterministic witnesses and a bounded status.

The helper accepts at most 64 declared units and uses a default node budget of
100,000. Its default `max_results=2` returns two witnesses at most, but a
caller can request a larger limit. The second witness proves `multiple`; a
budget stop before the required witness evidence returns `unknown_budget`.
The `observed` scope is labelled as conditional in its API documentation.
The full scope is the only scope that can support a full-inventory claim.

The helper records per-partition counts, orientations, and the unseen-unit
list. It does not assign plaintext letters. It does not read files or import
the reference loader.

The forced-edge helper is in `experiments/cyclic_pairing/forced.py`. It runs
the bounded full-matching search again, records that original evidence, and
then removes each edge in one selected witness. An edge is `not_forced` when
the edge-removed query returns a valid alternative witness, even if the query
also stops at its budget. It is `unknown` only when no witness is found before
an exhaustive result. It is `forced` only after an exhaustive no-witness
result. The overall result is `unknown_budget` when the repeated original
search is incomplete, an edge is unknown, or an edge query is skipped.

The synthetic test file is
`experiments/cyclic_pairing/test_pairing.py`. It checks unique, multiple, and
impossible graphs; unseen mates; partition reset; orientation conflicts;
observed versus full scope; input rejection; and budget uncertainty.

Verification command:

```sh
PYTHONPATH=src python -m unittest experiments.cyclic_pairing.test_pairing -v
```

The bounded test run passes 12 tests. Current helper hashes are:

* `experiments/cyclic_pairing/pairing.py`: `da9c89b4738d0dde959a3c730111dee864c05cd3e3b20932b2b8a3f30a57da95`
* `experiments/cyclic_pairing/forced.py`: `3f3a4fc450b5921905b8931310379d8361a6ca0b8d2989b8b8e939ddbc8d76a4`
* `experiments/cyclic_pairing/test_pairing.py`: `266d49547bf361a0f2ac290c88fb29f3e9ac86d08dbd73450654d50e87c1bf3d`
* `experiments/cyclic_pairing/test_forced.py`: `1f33dbd220e709446634f78ac656a01c4ad180538c1427c14049073e98eb893c`

## Use in substitution search

Use a certified forced edge as a pair group when the original full matching
search is exhaustive, even when that search found multiple matchings. Keep
the remaining matching disjunction. Replace every pair only after a unique
full-inventory matching, or after a later exact method proves each remaining
edge.

Keep the group-to-letter assignment unknown. Enforce the declared capacity
and the same lexical objective.

If the full matching is multiple, do not choose one non-forced edge set.
Branch over complete matching witnesses when the budget allows, or retain the
pairing disjunction in a later exact method. If the result is unknown, do not
use its apparent forced edges. A unique observed-subgraph matching is not
enough.

This grouping can reduce 52 unit variables to 26 pair variables. It does not
recover letter names, plaintext, or a historical writing system. The method
also applies only to this deterministic cyclic emitter. A random or
position-dependent homophone emitter needs a separate model.

## Next fixed experiment

Before any reference run, freeze a synthetic gate with these cases:

1. A complete four-unit stream with one unique matching.
2. Four one-item units with three matching witnesses.
3. One observed singleton with one declared unseen mate.
4. Two partitions with the same cycle start.
5. Two partitions with conflicting cycle starts.
6. A tampered stream with no perfect matching.

Use only declared synthetic unit arrays. Check the graph, matching status,
orientation, observed and unseen sets, and the exact source pair for every
known synthetic control. Run a validation stream first. Do not use a test
stream until the validation-only gate passes. Do not use a planted key to
select a pairing or to set a solver target.

For a larger complete inventory, do not enumerate every matching. Use the
forced-edge helper to remove a witness edge and ask if a perfect matching
still exists. Keep an alternative witness as `not_forced`, even when the
query budget stops. Return `unknown` only when no witness is found before an
exhaustive result. Use an explicit budget and retain the original matching
evidence. The future reference-control procedure is specified in
`docs/plans/cyclic-pairing-control-v1.md`; it remains separate from this
synthetic note.

This design is an emitter-specific control baseline. It makes no claim about
the Voynich manuscript and does not replace the general homophonic solver.
