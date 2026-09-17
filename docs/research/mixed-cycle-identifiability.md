# Mixed singleton and pair cycle identifiability

Status: theory note. Date: 2026-09-17.

This note studies a structural model with singleton and pair cipher units. It
uses finite symbolic examples only. It does not use a transcription or a
reference corpus.

## Model

Let `U` be the declared atomic unit inventory. A plaintext class has either
one unit or two units. Classes are disjoint. A singleton class emits its unit
for every occurrence. A pair class `{u,v}` emits `u,v,u,v,...` or
`v,u,v,u,...` for successive occurrences of its plaintext symbol.

Each word has an unknown initial phase for every pair class.
Phases can differ by word and by pair class. This note calls
this the **independent-word phase** model. A **shared-phase** model carries a
pair phase across several words in one declared stream. The phase rule is part
of the model contract.

The model has no missing emissions and no hidden unit boundaries. A plaintext
alphabet has `L` available symbols. Unused symbols are allowed unless the
protocol states that all `L` symbols must occur.

## Compatibility graph

For a candidate pair `{u,v}`, project every word onto `u` and `v`. Under
independent word phase, the pair is compatible when every non-empty projection
alternates. An alternating projection has counts that differ by at most one.
Let `G=(U,E)` contain one edge for every compatible pair.

The graph gives an exact finite characterization under these assumptions:

* A matching `M` in `G` selects the pair classes.
* Every unit outside `M` is a singleton class.
* The number of plaintext classes is `|U| - |M|`.
* The model is feasible with unused plaintext symbols when some matching has
  `|U| - |M| <= L`.

The result is necessary and sufficient for independent word phase. Necessity
follows because disjoint pair classes give a matching and each pair projection
must alternate. For sufficiency, assign one plaintext symbol to each matching
edge and each unmatched unit. Choose the initial phase of each pair from its
first observed unit in each word. The alternating projection then reproduces
all pair units. Assign the singleton class symbol at every singleton position.

For a closed inventory with exactly two units per plaintext class, every unit
must be covered by `M`. The condition is a perfect matching. A model with
singleton or pair classes permits unmatched vertices and needs only the class
count bound.

Let `O` be the observed inventory. The declared inventory `U` can also contain unseen units.
write `M_OO` for matching edges with both endpoints in `O`. The number of
classes that contain observed units is

```text
c_observed(M) = |O| - |M_OO|.
```

An observed-to-unseen pair does not merge two observed classes. An
unseen-to-unseen pair does not change `c_observed`. Let `A_L(G,U)` be the set
of all matchings `M` on `U` that satisfy

```text
|U| - |M| <= L
```

and any other declared pair or coverage requirements.
If `A_L(G,U)` is empty, the model is infeasible and the minimum below is undefined.
Otherwise, the exact minimum is

```text
min c_observed(M), over M in A_L(G,U).
```

If the protocol imposes no global class bound and no other extension
requirement, every matching in `G[O]` extends by leaving unseen vertices
unmatched. Therefore the exact observed-class minimum is `|O| - nu(G[O])`,
where `nu` is maximum matching size. Unseen inventory does not erase this
finite bound. With a class bound on `U` or another inventory requirement, an
observed matching needs an admissible extension. Perfect coverage is required
only for an exact pair-only contract.

For a closed observed inventory, the minimum total class count is
`|O| - nu(G)`. If all `L` plaintext symbols must occur, require exactly `L`
classes. If symbols may be unused, require at most `L` classes.

## Repeats and forced singletons

Suppose a word contains adjacent equal atomic units `u,u`. For every other
unit `v`, the projection onto `{u,v}` contains `u,u`. It cannot alternate.
Therefore `u` has degree zero in the compatibility graph.
It is a singleton in every feasible admissible mixed model.
This statement does not assert that an admissible model exists.

This conclusion needs all of these conditions:

* the two marks are two equal atomic units under the fixed unitization;
* both marks belong to one uninterrupted segment;
* no unit emission is missing between the marks;
* the pair class advances on every occurrence of its plaintext symbol.

A repeat across two independently phased words gives no such certificate. A
hidden ligature or a changed unitization also changes the graph. Thus a repeat
forces a singleton only for the stated atomic model.

A forced singleton is weaker than a forced plaintext letter. Its unit can map
to any unused plaintext symbol allowed by later language constraints.

## What matching proves

A maximum matching proves the largest number of disjoint pair classes under
the tested graph. It gives the smallest possible class count for a closed
inventory. It can prove that an exact pair-only model is infeasible when no
perfect matching exists. It can also prove that a mixed model needs more than
`L` classes when `nu(G) < |U| - L`.

A maximum matching does not prove that its edges are the true pairs. Another
maximum matching can give a different partition. It does not assign letters,
select a cycle orientation, or identify a language.

A minimum vertex cover is a different quantity. It intersects every graph
edge, but it does not count plaintext classes and does not make every vertex
outside the cover a singleton. A selected matching's unmatched vertex is also
not a forced singleton. To prove that a unit is singleton, show that all its
candidate edges are absent or that no admissible matching contains an
incident edge.

A minimum edge cover is unsuitable here. Edge-cover edges may share a unit,
while disjoint plaintext preimages require a matching. The relevant class
count is obtained from a matching, not from a general cover.

## Finite examples

These examples use symbolic units and have no manuscript meaning.

### Pair ambiguity

Let `U={a,b,c,d}` and let every pair be compatible. The graph has maximum
matching size two and minimum class count two. The three perfect matchings

```text
{a,b}/{c,d},  {a,c}/{b,d},  {a,d}/{b,c}
```

all reproduce the structural observations. A perfect matching proves
feasibility, not pair identification.

### Unseen mates

Let observed units be `{a,b,c}` and let the only observed edge be `{a,b}`.
The observed lower bound is two classes: `{a,b}` and `{c}`. If an unseen unit
`x` can pair with `c`, the class containing `c` becomes `{c,x}`, but the
number of observed classes remains two. A full inventory and extension rule
are required to decide whether that edge is available.

### Phase policy

For pair units `{a,b}`, two separate words with projections `[a]` and `[a]`
are compatible under independent word phase. Their concatenation `[a,a]` is
incompatible under one shared phase. The same visible words therefore define
different graphs under the two phase policies.

### Forced singleton

The segment `[a,a]` removes every edge incident to `a`. The mixed model can
still reproduce the segment by assigning `a` to a singleton plaintext class.
The observation rejects a pair-only model, but it does not reject the mixed
model.

## Alphabet capacity and unfalsifiability

For a closed observed inventory, let `m <= L`. Assign each unit to a distinct
singleton plaintext class. This assignment reproduces every finite unit stream,
including all adjacent repeats. Under independent word phase, the mixed model
is therefore structurally unfalsifiable for `m <= L`, unless a protocol also
requires pair classes or imposes language, frequency, or semantic constraints.

For `m > L` in a closed observed inventory, a mixed model is feasible exactly
when `nu(G) >= m-L`, provided unused plaintext symbols are allowed. The
matching must merge enough visible units into pair classes. This is a capacity
test. It does not recover the matching when several matchings meet the bound.

An incomplete inventory changes the condition to an admissible-matching
extension problem when the protocol adds a class bound or another inventory
requirement. Unknown unseen units can add pair classes and can satisfy a
closed-inventory requirement. If neither the inventory nor the class count is bounded,
the total class count has no finite upper bound. The observed-class bounds remain finite.
When `L` is fixed, every feasible model still has at most `L` classes.

## Value of a next test

The mixed singleton and pair test adds a useful feasibility result when the
visible unit count exceeds the plaintext alphabet, when pair classes are
required, or when the full inventory and phase policy are fixed. In those
cases, a matching certificate can show that the required number of merges is
possible or impossible.

For at most 26 visible units with singleton fallback and no further inventory requirements,
the test permits one distinct plaintext symbol for each visible unit.
A maximum matching then selects one optional
pairing among many feasible singleton assignments. It does not improve
identification of plaintext letters or provide a decipherment result.

The next protocol should therefore predeclare the visible-unit count, the full
inventory, the phase policy, and whether singleton classes are allowed. It
should report matching feasibility and forced edges as structural evidence.
It should not call a selected matching a key or use it as semantic evidence.
