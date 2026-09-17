# Segmented cyclic emitter design

Status: future exploratory design note. Date: 2026-09-17.

This note defines a structural test for a deterministic capacity-two cyclic
emitter on incomplete or uncertain streams. It uses formal toy streams only.
It does not read the VMS, fit a key, generate a plaintext, or identify a
language. The emitter is the model under test. It is not a decipherer.

The design extends [the cyclic emitter pairing note](cyclic-emitter-pairing.md)
and [the synthetic control plan](../plans/cyclic-pairing-control-v1.md). The
full-inventory and observed/unseen rules also follow
[the observed pair quotient note](observed-pair-quotient.md).

## 1. Model and observation units

Let `U` be the complete declared set of cipher units. This model requires
exactly two distinct units per letter. It does not cover every emitter with
at most two units per letter. A capacity-two cyclic emitter
assigns each plaintext letter a pair `{u,v}`. Each occurrence of that letter
emits the next member of its pair. Its projected sequence is therefore

```text
u v u v ...
```

or the same sequence with the other start phase. Word boundaries do not reset
the cycle unless the test declares that rule.

The observed stream is split before testing. Each **gap-free segment** contains
only positions whose unit identity is known. An **unknown gap** marks an
interval that may contain deleted, unreadable, or untranscribed emissions.
The test must record segment and gap boundaries before it examines pair
compatibility. It must not create a gap after seeing a failed edge.

For a candidate pair `e = {u,v}`, let `P_e(S)` remove all units except `u` and
`v` from a gap-free segment `S`. A null marker is not `u` or `v`. It needs the
uncertainty rules in Section 5.

Give every segment `S` an explicit unknown start phase `phi(S,e)`. The phase
specifies which member would be first if `e` occurs in that segment. An empty
projection has both phases. A non-empty projection fixes its phase from its
first projected unit when pair orientation is fixed.

Keep orientation and phase as separate settings:

* `fixed orientation` uses one ordered pair for all linked segments. A known
  reset can require one shared reset phase even when its value is unknown.
* `optional orientation` permits the ordered pair to change under the stated
  segment rule. For a binary pair, reversing the order is exactly equivalent
  to changing the phase. It adds no structural evidence. Record it for
  bookkeeping or for a later emitter with more than two states.
* An unknown segment has an independent `phi(S,e)`. Repeated resets can use
  one shared unknown reset phase, or independent phases if the protocol allows
  the reset state to vary. These are different hypotheses.

Report these policy combinations as separate tests:

| Boundary or segment rule | Orientation rule | Phase rule |
| --- | --- | --- |
| Known reset, repeated state | Fixed | Use one ordered pair and one shared but unknown reset phase. |
| Known reset, variable state | Fixed | Use one ordered pair and an independent phase per reset segment. |
| Known reset, optional order | Optional | Test allowed orders. Share or vary phase as declared. |
| Unknown segment or gap | Fixed | Keep one ordered pair. Give each segment an independent phase. |
| Unknown segment or gap | Optional | Give each segment its allowed order and independent phase. |

The last row is the most permissive. It can weaken a rejection. For a binary
pair, an optional order and an independent phase are exactly redundant. The
protocol must still record which policy produced the result.

This distinction prevents a false constraint. A reset boundary can remove
continuity while leaving the start phase unknown. A known reset with a declared
shared state can impose the same phase on every non-empty reset segment.

For an unknown gap `g`, use an independent toggle `delta(e,g)` for each
candidate pair. It can be zero or one. Thus the unobserved interval can either
preserve or flip the phase for that pair. Do not force all plaintext letters to
share one unknown parity. This is a generous uncertainty model. It removes
cross-gap evidence unless the gap parity is known.

## 2. Pair compatibility for segmented streams

For each candidate pair `e`, apply these checks.

### Segment-local checks

For every gap-free segment `S` with a non-empty projection:

1. `P_e(S)` must have no adjacent equal members.
2. `abs(count(u) - count(v))` must be at most one.
3. Its first member must agree with the allowed phase and orientation policy.

The first check applies to projected adjacency. For example, `u x y u` gives
`P_e(S) = u u`. The other units do not make the two `u` emissions alternate.
This pair is invalid in that segment unless an uncertainty marker or a gap was
declared at one of those positions.

The count check is useful for diagnostics. For an exact binary alternating
sequence, it follows from the first check, but it gives a short certificate
when a candidate has a large count imbalance.

A repeated `u` in one gap-free segment is therefore forbidden when its mate
`v` is not observed between the two `u` positions. An unseen mate in another
segment or in an unknown gap cannot repair this local contradiction.

### Boundary checks

Apply only the boundary rule that the input declares.

* Across a known continuous boundary, test the projected last and first
  members as one sequence. Equal members reject the pair.
* Across a known gap with known **pair-specific** parity, enforce the
  corresponding phase relation. A pair count of zero modulo two preserves
  phase. A pair count of one modulo two flips it. The parity of the total
  omitted emissions is not enough because other letters can fill the gap.
* Across an unknown gap, choose `delta(e,g)` freely. Do not compare the last
  member before the gap with the first member after it.
* Across a reset with a known shared reset phase, require every non-empty
  reset segment to start with the same member under fixed orientation. If the
  reset state can vary, keep a separate unknown phase for each segment.

These checks give a candidate edge in the compatibility graph. The edge means
that at least one allowed phase, orientation, gap toggle, and uncertainty
assignment exists. It does not select a plaintext letter or a preferred
orientation.

### Compatibility proposition

For one candidate pair, the checks above are necessary and sufficient for an
exact segmented stream under the declared gap and phase policy.

Necessity follows from the emitter rule. A letter emits alternating pair
members. Its projection cannot contain equal adjacent members, and its two
counts cannot differ by more than one. A known continuous boundary keeps this
alternation. A known reset or known pair-specific gap parity keeps the
declared phase relation.

For sufficiency, choose the phase fixed by the first member of each non-empty
projection. Use either phase for an empty projection. Enforce every known
boundary relation. At an unknown gap, choose its allowed pair-specific
`delta(e,g)` and fill the unobserved interval with the required pair count
parity. The total gap length can differ because other letters can occur. The
resulting pair sequence emits every observed projection. If orientation is
optional, use the declared orientation for each segment. No condition remains
across an unknown gap.

This proposition is per pair. It does not make pairwise witnesses jointly
compatible when they share a wildcard, gap length, or cost budget.

The pair graph is exact only in the narrow mode with exact known segments
and independent unlimited unknown gaps. It has no unresolved wildcard positions,
finite gap length, or global uncertainty budget. A wildcard must have one fixed
global assignment before graph construction in this exact mode. Disjoint pair
witnesses can be combined with a perfect matching. In every other mode, the
pair graph is a necessary relaxation. A joint constraint search must reuse
each null assignment and enforce every shared limit.

Here is a small shared-wildcard counterexample. Use declared units `a`, `b`,
`c`, and `d` with these observed segments and one shared wildcard:

```text
S0 = a c ? a c
S1 = a b a b a
S2 = c d c d c
```

Segment `S0` is not gap-free because it contains the shared wildcard.
For pair `{a,b}`, `S0` projects to `a ? a`, so the wildcard must be `b`. For
pair `{c,d}`, `S0` projects to `c ? c`, so the same wildcard must be `d`.
`S1` and `S2` remove all cross-pair edges. The pair graph therefore has the
perfect matching `{a-b, c-d}`, but no one assignment satisfies both pairs.
This is why pairwise edge existence is not a full result in wildcard mode.

## 3. Full graph and open inventory

Build the compatibility graph over the full declared inventory `U`. Add an
edge for every pair that passes all segment and boundary checks. If `U` is
complete, a perfect matching is necessary for a full pairing in this exact
two-units-per-letter model. It is sufficient
only in the narrow independent-witness mode in Section 2. With shared nulls,
finite gaps, or a shared cost budget, it is only a necessary relaxation. An
observed-only matching has a narrower meaning. It assumes that every observed
unit has an observed mate.

Let `O` be observed units and let `U - O` be declared but unseen units. An
observed unit can have an unseen mate. This creates an open singleton in the
observed relation. Keep it unresolved. Do not turn it into a plaintext letter.

An open inventory must have a fixed rule for units outside `U`. One possible
future mode adds `m` named external unit slots. It declares whether external
slots can pair with observed units, with declared unseen units, and with one
another. The matching must cover every declared unit and every used slot.
The value `m` and these edge rules must be fixed before testing.

An unlimited external inventory weakens rejection for every unmatched observed
singleton that passes its segment-local checks. It cannot explain two `u`
observations in one gap-free segment when no `v` occurs between them. Report
the closed-inventory result and each bounded open-inventory result separately.

For an observed unit `u` with no observed mate, one observation in a segment
can remain compatible with an unseen partner. Two `u` observations in the same
gap-free segment produce `u u` in `P_e(S)` and reject every pair using `u`.
An unknown gap can hide a partner between observations in different segments,
subject to the declared gap and open-slot budget.

## 4. Reject certificates

Use the smallest exact certificate that matches the failure.

* **Local edge certificate.** For a candidate pair, record one segment whose
  projected stream has equal adjacent members or a count difference above one.
  This removes one graph edge. It does not reject the full inventory by itself.
* **Isolated-unit certificate.** In the full graph, record a unit with degree
  zero after all allowed phases, orientations, gaps, and uncertainty cases.
  This directly proves that no perfect matching exists in the closed graph.
* **Tutte obstruction.** The unit-pair graph is a general undirected graph.
  For a vertex set `X`, let `odd(G-X)` be the number of odd connected
  components after removing `X`. A set with `odd(G-X) > |X|` is a certificate
  that the graph has no perfect matching. Record `X` and those components.
  This is the general criterion. A neighborhood deficiency can also prove
  failure, but it is not a complete criterion for general graphs.
  Hall's complete characterization requires a bipartite graph.
* **Perfect-matching certificate.** If an exhaustive matching search returns
  no perfect matching, retain its status and any valid Tutte obstruction. A
  negative result need not have a Hall witness. A node-budget stop is
  `unknown_budget`, not `none`.

For a repeated unit conflict, first remove all candidate edges that fail the
local check. Claim model rejection only when the full graph has no completion.
Do not report one failed pair, one selected witness, or an observed-only
matching as a global reject certificate. In a joint wildcard or finite-gap
mode, also require an exact bounded search or a separate unsatisfiability
certificate for the shared assignments. A Tutte obstruction for the relaxed
pair graph does not describe every joint constraint mode.

For a bounded open inventory, compute certificates on the augmented graph.
An obstruction in the closed graph is not a rejection if an allowed external
slot can repair it. The obstruction remains valid only when every allowed
external completion fails.

## 5. Null units and uncertainty cost

Treat an unreadable or uncertain position as an explicit null marker `?`. Do
not silently delete it. Predeclare one of these policies:

* `mask`: `?` breaks exact local checks and the affected pair edge becomes
  conditional;
* `wildcard`: assign `?` to a declared unit and charge one assignment;
* `gap`: convert a declared uncertain interval to an unknown gap and charge
  one gap operation.

For a simple cost ledger, use

```text
cost = c_null * null_count
     + c_gap * gap_count
     + c_wild * wildcard_count.
```

Set the costs and maximum total cost before the test. A null can conceal a
missing mate. For example, `u ? u` can become `u v u` under `wildcard`, but it
must pay for that assignment. An unknown interval can change phase, but it
must be a predeclared gap.

Accept a pairwise edge only when a valid assignment exists within the fixed
per-edge budget. If one null, gap, or total cost is shared by several pairs,
keep the assignment in the joint state. Separate pairwise repairs can conflict
even when every edge passes alone. Report `compatible_under_budget`,
`rejected_over_budget`, or `undecided` when the search is incomplete. A
minimum-cost repair above the declared joint budget is a reject under that
model. It is not a claim about the manuscript.

Unlimited nulls, free post-hoc gaps, or unbounded wildcard assignments erase
the test. Run strict, segmented, and costed modes as separate hypotheses. A
mode that gives every pair an edge provides no useful falsification.

## 6. Why word filtering breaks global alternation

Filtering words changes the observed event sequence. It can remove one member
of a pair and change the apparent phase of every later retained occurrence.
If the retained words are concatenated, the join can create a false `u u`
adjacency. If each retained word starts a new cycle, the test removes valid
cross-word constraints and can create false compatibility.

For example, a continuous `u v` interval can become `u` after filtering the
word that contains `v`. A later retained `u` is then not evidence against the
emitter. The omitted interval is an unknown gap.

Use these rules:

1. Mark every omitted interval as a predeclared gap.
2. Keep each uninterrupted known run as its own segment.
3. Keep word boundaries outside the unit stream unless the model declares a
   reset at each word.
4. Do not use a filtered, concatenated stream for global alternation claims.

The same rule applies to parser exclusions and diagram interruptions. The
current corpus notes treat `<->` and `<~>` as interruptions and warn that
filters change the measured population. This design makes the missing interval
explicit instead of treating the retained text as continuous.

## 7. Synthetic controls

Run the following controls before any future manuscript application.

| Control | Expected result | Failure meaning |
| --- | --- | --- |
| Complete positive stream from a known pair inventory | The planted pair edges remain compatible. | Local rule, phase, or parser error. |
| Random predeclared segment cuts | The positive pair survives with free segment phases. | The test imposed an unlisted cross-segment constraint. |
| Known pair-specific gap parity versus unknown gap parity | Only the known pair parity can reject a phase conflict. | Gap handling is too strict or too weak. |
| Same unit twice in one gap-free segment | The pair edge is removed, including with an unseen mate. | The local projection rule is unsound. |
| Closed four-unit negative stream with no perfect matching | The full graph returns `none`; it may also give an isolated-unit or Tutte certificate. | Matching or certificate code is wrong. |
| Singleton with an unseen partner | Closed and bounded-open reports remain distinct. | The inventory scope is hidden. |
| One null that repairs one conflict | It passes only within the declared null budget. | The uncertainty ledger is not enforced. |
| Filtered stream with a known omitted interval | Gap-aware mode keeps the positive pair. | Filtering creates an artificial rejection. |
| Naive concatenation and naive word reset | Results differ from the predeclared gap mode. | The control does not expose word-filter bias. |

Use tiny exhaustive graphs to check isolated-unit and Tutte certificates.
Do not assume that every general-graph failure has a Hall deficiency. Record the
graph, phase policy, orientation policy, gap manifest, cost budget, matching
status, and certificate. Keep all controls synthetic and independent of VMS
text or images.

## 8. Use and limits

Apply this design only after the known synthetic control-pairing gate passes.
It can then test whether one fixed capacity-two emitter remains structurally
possible under an explicit incomplete-stream model.

A pass means that the declared observations do not reject that emitter. It does
not identify pairs, plaintext letters, a language, or a decipherment. A failure
rejects only the tested emitter, unit inventory, boundary rules, and
uncertainty budget together.

If free gaps, external partners, or nulls make the graph nearly complete,
report `uninformative` instead of treating compatibility as support. A future
application must freeze the unitization, segment manifest, reset claims,
orientation policy, open-inventory budget, uncertainty costs, shared-resource
rules, and matching budget before it reads any manuscript stream. It must use
a joint solver for every mode where pairwise witnesses share resources.
