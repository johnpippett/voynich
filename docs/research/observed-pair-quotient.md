# Observed pair quotient

Status: synthetic theory note. Date: 2026-09-17.

This note describes a safe partial reduction for a capacity-two cyclic
emitter. It uses no control output, key, manuscript stream, or real data. It
does not claim that the required conditions hold in a later run.

It assumes the exact capacity-two emitter: a complete 52-unit inventory, 26
plaintext letters, and exactly one pair of cipher units for each letter. It
does not describe a generic lexical solver with an at-most-two capacity.

## Definitions

Let `G` be the compatibility graph for a complete declared unit inventory.
Every full perfect matching of `G` is a possible unit pairing. Let `O` be the
observed units and let `U` be the unseen units.

For every full matching `M`, restrict its edges to `O`. This gives a partial
matching on observed units. A unit with no observed partner is a singleton in
this restriction. The observed relation is identifiable when every feasible
full matching gives the same restricted edge set `R`.

An edge is **forced** when it occurs in every feasible full matching. An edge
is **impossible for the full problem** when no feasible full matching contains
it. These terms require evidence over the full inventory. A compatibility
edge that has not appeared in a bounded search is still possible.

Graph edge absence is a sufficient negative certificate: an absent edge
cannot occur in any matching. A present edge needs an edge-constrained full
matching check before it can be called possible or impossible for the full
problem. Failure to find a witness before the search budget ends is unknown.

## The quotient theorem

Assume all of these conditions hold:

1. A feasible full matching exists.
2. Every edge in `R` is forced.
3. Every other observed-observed edge is proved impossible for the full
   problem.
4. The forced edges in `R` are disjoint.

Then every full matching has the same observed equivalence classes: each edge
in `R` is a two-unit class, and every other observed unit is a singleton.
Unseen units can pair in different ways without changing this observed
relation.

The quotient is therefore safe for a later plaintext search. If `|O|=46` and
23 observed-observed edges are forced, the quotient has 23 classes. If
`|O|=47` and the same 23 edges are forced, it has 24 classes, including one
open singleton. In the second case, that singleton can pair with one of five
unseen units in different full completions. It is still one observed class.

The number of observed classes is

```text
|O| - number of forced observed-observed edges.
```

This count is valid only after the relation is proved identical across all
full matchings. It is not valid after selecting one convenient witness.

For the first toy case, 46 observed units form 23 forced pairs and six units
are unseen. The six unseen units can have several pair completions. The 23
observed classes remain fixed. For the second toy case, 47 observed units
consist of 46 units in 23 forced pairs and one singleton, plus five unseen
units. The 24 observed classes remain fixed. The open singleton keeps one
unresolved capacity slot. Its five observed-unseen candidate edges are not
individually forced, but every completion leaves the observed unit a
singleton in the observed relation.

## Safe capacity reduction

Represent each proved class with its used capacity:

* A forced pair uses two cipher units. It is closed and cannot accept another
  unit.
* An observed singleton uses one unit. It is open and can accept at most one
  unseen mate, subject to a feasible full matching.
* An unseen unit remains unresolved until a residual matching chooses its
  partner.

The residual graph must still have a perfect matching that covers every
unresolved unit and every open slot. A reduced plaintext search is sound only
when this residual feasibility condition is preserved for every candidate
completion that the search considers. The search must also preserve the
declared capacity of two units per plaintext letter and the available letter
count. It must not merge two observed classes because their units have a
compatible edge. Compatibility is only a possibility until all other
constraints prove the edge forced.

More generally, a partial reduction is sound when every full matching maps to
one retained quotient state, and every retained quotient state has at least
one full matching extension. The reduction can keep a disjunction of residual
states. It cannot replace that disjunction with one witness without a proof.

## Counterexamples

Use declared units `a`, `b`, `x`, and `y` with one complete partition stream
containing `a b`. Units `x` and `y` are unseen. The six edges

```text
a-b, a-x, a-y, b-x, b-y, x-y
```

are compatible: the first edge projects to `a b`, the four mixed edges
project to one observed unit, and `x-y` has an empty projection. The three
full matchings are:

```text
{a-b, x-y}
{a-x, b-y}
{a-y, b-x}
```

The observed relation on `a` and `b` differs among these completions.
Treating `a` and `b` as distinct observed classes loses the first completion.
Treating `a-b` as forced loses the other two completions. This is a direct
cyclic observation with an unseen mask, so it does not require an abstract
graph assumption.

The same distinction applies to a missing edge. If `a-b` is absent from the
compatibility graph, no completion can pair them. If `a-b` is present but a
bounded search has not found a completion containing it, the edge is not
proved absent. A later solver must retain it or prove its exclusion with an
exhaustive constrained matching check.

## Letter and orientation boundaries

The quotient identifies cipher units that must share one plaintext letter. It
does not identify the letter name. Under the exact model, all 52 units are
assigned and each of the 26 letters has exactly two units. Distinct observed
classes need distinct letters. An open singleton reserves one unit of capacity
for a possible unseen mate. Unseen-only pairs consume the remaining classes
after a completion is selected.

Pair orientation is separate from the equivalence relation. A projection can
fix which unit starts a pair in a partition, but this does not select a
plaintext letter. When its mate is unseen, an open singleton is the first
cycle unit where it appears; its mate identity remains unknown. A pair whose
two units are unseen has no observed orientation. A later fit must retain
every allowed orientation and check the complete emitter after it selects a
completion. It must not use a planted orientation to choose a pairing.

This reduction can support a later exact search when its forced-edge and
residual-feasibility certificates are recorded. It does not prove a language,
plaintext, or manuscript result.
