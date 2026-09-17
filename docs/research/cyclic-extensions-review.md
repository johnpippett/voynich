# Segmented cyclic emitter review

Review date: 2026-09-17.

This is a read-only review of two synthetic theory notes. It uses no corpus,
manuscript, source stream, key, or implementation. It does not claim a result
for the Voynich manuscript.

Reviewed hashes:

- `docs/research/segmented-cyclic-emitter-design.md`: `8c545aede1cd1a03413bce8d2f76ce6b84d69ea03ff28df8ce740d10db406eea`;
- `docs/research/observed-pair-quotient.md`: `440091127cead6e04b2a9b0184c3231859eedefd258c6f9aec4d8fbe80ba2c08`.

## Result

The segmented note is mathematically sound under its stated narrow model:
exactly two distinct units per letter, a complete declared inventory, exact
segment boundaries, independent unbounded gap choices, no unresolved
wildcards, and no shared uncertainty resource. A wildcard is exact only after
one fixed global assignment is made before graph construction. The note
correctly changes the pair graph from an exact result to a necessary
relaxation when wildcards, finite gaps, or a shared cost limit couple pair
witnesses.

The reset and phase rules are separate and correct. A shared reset phase gives
cross-segment evidence. Independent phases remove that evidence. An unknown
gap can choose a pair-specific phase toggle only when the gap policy permits an
unbounded omitted sequence. A repeated unit inside one known segment cannot be
repaired by an unseen mate or an external slot.

The note uses the general undirected perfect-matching obstruction correctly:
`odd(G-X) > |X|` is a valid Tutte obstruction. A valid Hall deficiency is a
sufficient nonexistence certificate when its neighborhood relation matches the
stated matching formulation. Hall's theorem is a complete characterization
only for bipartite graphs. The baseline unit-pair graph is general and uses
Tutte or an exhaustive search for complete status.

## Synthetic wildcard check

For the supplied toy streams, `S0` is an observed segment with one shared
wildcard. It is not a gap-free segment. `S1` and `S2` are exact gap-free
segments:

```text
S0 = a c ? a c
S1 = a b a b a
S2 = c d c d c
```

The local pair checks give these conditional wildcard assignments:

- pair `a-b`: only `? = b`;
- pair `c-d`: only `? = d`;
- every cross pair: rejected by a repeated projected unit in `S1` or `S2`.

The relaxed graph therefore has the perfect matching `{a-b, c-d}`. The two
edge witnesses require different values for the same wildcard, so no joint
assignment exists. This confirms the note's necessary-only warning.

## Resolved precision checks

1. The exact graph mode now states that it has no unresolved wildcard
   positions. A shared wildcard needs one fixed global assignment before graph
   construction. Independent per-edge assignments remain a relaxation.
2. The wildcard example now labels `S0` as a segment with a null marker. The
   note keeps gap-free segments restricted to known unit identities.
3. The full-graph section now states that perfect-matching sufficiency applies
   to exactly two distinct units per letter and a complete inventory. A generic
   at-most-two solver has different feasibility rules.

These checks guard against applying the theorem to a broader solver. They do
not invalidate the segmented theory under its narrow assumptions.

## Observed quotient note

The final observed quotient note is consistent with the exact model. Its
`a,b` observed stream with unseen `x,y` gives all three full matchings, so an
observed-only pairing cannot identify the full relation. Its open-singleton
wording now states that the observed unit is the first cycle unit where it
appears, while the unseen mate remains unknown. The corrected `47`-observed
unit example also has the required total of 52 units.

No real-data run or implementation follows from these notes. Before a future
run, freeze the segment manifest, null and gap policy, reset and phase policy,
external-slot rules, shared-resource budget, and joint-solver method. Report a
pass only as compatibility with the tested emitter and uncertainty model.
