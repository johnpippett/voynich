# Bitset pivot-group bound design

Status: implemented and reviewed on synthetic inputs. No corpus or reference run has used this adapter.
The reviewed bitset engine remains unchanged.

## Purpose

The scalar `PivotGroupBound` computes a tighter upper bound than the
independent word bound. A future adapter can use the frozen
`experiments.homophonic.bitset_bound.BitsetBound` masks for the same
calculation.

The adapter must produce the same result as the scalar implementation for:

- capacities `1`, `2`, and `None`;
- every valid partial map;
- every disjoint group and residual word partition;
- repeated cipher units, empty words, empty candidate lanes, and duplicate
  candidate rows.

The adapter must fail closed when it cannot construct the complete candidate
domain or when the frozen mask contract changes. It must never use a partial
candidate cache as an upper bound.

## Frozen mask contract

The reviewed engine assigns one bit to each root-compatible candidate row and
one high sentinel bit to each word lane. It stores these private fields:

```text
_real_mask
_high_sentinels
_low_lane_bits
_presence_masks[cipher_unit]
_mapping_masks[(cipher_unit, plaintext_letter)]
_preimage_size_masks[plaintext_letter][size]  # capacity 1 or 2
_weight_bit_masks[(weight_bit, mask)]
_cipher_symbols
_plain_symbols
_capacity
```

For a valid partial map `P`, the engine computes an active candidate mask
`A(P)`. Presence and mapping masks enforce the assigned cipher units. The
preimage masks enforce the capacity rules for each assigned plaintext letter.
The expression below converts active candidate bits into one high bit for each
lane that has at least one active row:

```text
flags(A) = ((A | _high_sentinels) - _low_lane_bits) & _high_sentinels
```

The weight masks then convert those lane bits into the independent weighted
bound. A duplicate row can set a lane flag only once. A zero-candidate lane
has no active row and produces no flag.

The adapter must treat these names as a private compatibility contract. It
must check their presence, types, and metadata values at construction. It must
record the reviewed engine source hash in its configuration. A missing field,
unexpected mask shape, or metadata mismatch must raise a compatibility error
or return `status: "abstain"`. It must not guess a new layout.

The existing `IncrementalBitsetBound` can provide an active state and child
states. It still depends on the same private masks. The future adapter can use
that class, or it can reproduce its active-mask expression. Both choices need
the same compatibility checks. A public `active_mask(partial)` and
`child_active(parent, unit, letter)` interface would remove this private-field
risk, but this design does not edit the frozen engine.

## Candidate and lane construction

Use the same frozen normalizers and candidate builder as the scalar prototype.
Normalize counts, lexicon words, alphabet, capacity, and candidate rows before
the bitset engine is built. Keep every usable equal-length lexicon word that
passes repeated-unit and root-capacity checks.

The adapter must not retain a second candidate-row cache. It can use a concrete
sequence of normalized rows to construct `BitsetBound`, then retain only this
lane metadata:

```text
word -> (weight, lane_high_bit, group_id or residual)
```

The metadata builder must use the same sorted normalized word order and the
same row lengths that the frozen constructor uses:

```text
base = slot_count
high = base + len(candidate_rows_for_word)
slot_count = high + 1
```

It must check the resulting lane count, candidate count, sentinel count, and
slot count against `BitsetBound.metadata`. If the input rows are one-shot
iterators, materialize them once for the engine and delete that temporary map
after construction. Prefer reusable sequences so the adapter does not create
a second persistent tuple set. Do not regenerate offsets from a heuristic
sample.

The candidate cache construction limit must fail before a bound is returned.
An estimated bitset size above a declared memory limit must also return
`status: "abstain"` or raise a construction error. The adapter must preserve
the scalar path as the caller's explicit fallback. It must not prune with an
incomplete bitset.

Validate groups before queries. A group has one pivot cipher unit, and every
word in the group must contain that pivot. Group word types must be unique
across groups. The group words plus residual words must partition the
normalized word lanes. Store group lane high-bit positions and pivot units.
Do not store a candidate row or a per-group candidate mask.

Check total capacity before a query. If
`capacity * len(plaintext_alphabet) < len(cipher_symbols)` for capacity `1` or
`2`, no total map exists and the result must report infeasibility with no
numeric bound. For capacity `None`, no global capacity check is needed.

## Query algorithm

For a valid partial map `P`, first validate the cipher units, plaintext
letters, and capacity use. Construct the active mask `A(P)` with the frozen
capacity rules. Compute `flags(P)` once for the residual lanes.

For each group `G` with pivot `c`:

1. If `c` is assigned in `P`, use its assigned letter `p` and `A(P)`.
2. If `c` is unassigned, enumerate each legal plaintext letter `p`. A letter
   is legal when it does not exceed the current partial preimage capacity.
   Construct `A(P + {c: p})` with the same child capacity mask as the frozen
   engine.
3. Convert the active mask to lane flags. Restrict the flags to the lanes in
   `G`. Sum the weights of those lanes. This is `S(G, p, P)`.
4. Use the maximum score across legal `p` as the group contribution.

The residual contribution is the independent weighted score of `flags(P)` on
residual lanes. The result is:

```text
group_bound(P) = sum(max_p S(G, p, P) for each group G)
                  + residual_independent_bound(P)
```

Cache child flags only during the current query. If several groups use the
same pivot, reuse the `(pivot, p)` flags for that query. Do not retain a
frontier-node mask or a cross-query active-mask cache.

For capacity `1`, the child capacity mask allows only an empty candidate
preimage or a candidate row that contains the assigned pivot unit. For
capacity `2`, use the frozen rules:

- zero partial units for a letter add no extra restriction;
- one partial unit allows candidate preimage size zero or one, or an
  overlapping mapping for that unit;
- two partial units require the candidate preimage to be a subset of those two
  units.

When `c` is assigned already, do not apply the child assignment twice. The
active mask already includes the mapping and capacity restriction for `c`.
For capacity `None`, only the presence and mapping masks apply.

## Group sentinel masks and memory

The frozen high sentinels include all word lanes. The adapter has two safe
ways to restrict them to a group:

1. Store only each group's tuple of lane high positions. During one group
   query, OR those positions into one temporary `group_high_mask`, apply
   `flags & group_high_mask`, score with the frozen weight masks, and delete
   the temporary integer.
2. Avoid the temporary mask. Iterate the group's high positions and add the
   word weight when `flags & (1 << high)` is non-zero.

The first method can use the frozen broadword `bit_count` path. The second
method uses less temporary memory and can be better for small groups. Neither
method stores a second candidate bitset. A persistent group mask for every
group would cost approximately one Python integer per group with the full
slot width. Do not allocate those masks by default.

The residual lanes use the same lane-position method. The adapter can build
one residual mask for a query, or sum residual lane positions directly. Store
weight values in the lane metadata so the direct method does not need a second
weight-mask table.

## Admissibility

Let `C_w(P)` be the rows in the complete root cache that remain compatible with
`P`. A complete extension of `P` that hits word `w` uses a row in `C_w(P)`.

For group `G`, every word contains pivot `c`. A complete extension assigns one
letter `p` to `c`. If the extension hits `w`, its active row maps `c` to `p`.
The row is therefore counted by `S(G, p, P)`. The hit weight for `G` is at
most `S(G, p, P)`, and therefore at most the maximum group score. The groups
are disjoint, so their maxima can be added. Residual words use the independent
feasible weight. This proves:

```text
true completion score(P) <= group_bound(P)
```

For each group and each `p`, `S(G, p, P)` counts only active words. The group
term is therefore no greater than the independent weight of that group. The
residual terms are equal. This proves:

```text
group_bound(P) <= independent_bound(P)
```

Ignoring conflicts between groups is intentional. It can make the group
bound loose, but it cannot make the bound low. A capacity conflict inside a
candidate row is not ignored: root filtering and the active child masks must
apply it exactly.

## Cost and limits

The bitset construction has the frozen mask cost plus `O(number_of_word_lanes)`
lane metadata. It does not add a persistent row cache. A query computes one
active mask and then can compute up to `number_of_groups × alphabet_size`
child masks. Each child uses Python large-integer operations over the full
candidate bit width. Group flag restriction adds either one temporary large
integer or one scan of the group lanes.

This method can reduce the cost of candidate-row scans, but it does not promise
a speedup. The expected query cost is group by alphabet by large-integer mask
work. Measure node count, query time, peak memory, temporary mask size, and
bound equality against the scalar prototype before any solver integration.

## Required synthetic checks before implementation

The future implementation must compare the bitset and scalar results for all
partial maps in small domains. Include capacities `1`, `2`, and `None`, the
strict `x`, `xy` fixture, duplicate rows, repeated pivots, repeated cipher
units, empty words, zero weights, empty candidate lanes, Unicode tuple units,
explicit groups, residual words, and capacity-infeasible alphabets.

For every case, require exact equality of `group_bound` and
`independent_bound`. Also verify the direct completion score is no greater than
the group bound. Test the lane-offset metadata against the frozen engine's
metadata. Test that a construction limit or private-contract mismatch returns
no numeric bound.

## Synthetic implementation snapshot

`experiments.group_bound.bitset.BitsetPivotGroupBound` now implements this
adapter for synthetic inputs. It uses `PivotGroupBound` only while it builds
the complete normalized row source. After the frozen engine is constructed,
the adapter keeps lane weights, sentinel positions, groups, and the frozen
masks. It keeps no candidate-row cache.

The constructor accepts `max_candidate_rows` and
`max_estimated_storage_bytes`. A limit raises `BitsetConstructionError` before
the adapter returns an object. The storage value is a conservative mask-size
estimate. It is not an operating-system memory limit. The adapter records both
the conservative estimate and the frozen engine estimate in `metadata`.

The adapter records and checks the reviewed frozen source hash:

```text
8ab50b9700497cc493e0ba79a9fc6d452cf95e5b8c7d9d19d0de08b567000f76
```

It validates the private mask fields, metadata counts, lane slot count, mask
shapes, and capacity helper before it accepts the engine. A mismatch raises
`BitsetCompatibilityError` and returns no bound.

The focused synthetic suites pass together:

```text
PYTHONPATH=src:. python -m unittest \
  experiments.group_bound.test_pivot \
  experiments.group_bound.test_bitset -v
Ran 13 tests ... OK
```

The checks compare every partial map in a small domain with the scalar bound
and with direct completion enumeration for capacities `1`, `2`, and `None`.
They include explicit residual groups, repeated pivots, duplicate normalized
inputs, repeated units, zero and empty lanes, Unicode tuple units, total
capacity infeasibility, construction limits, and a simulated private-layout
mismatch. Additional deterministic random sweeps covered 100 static and 100
explicit-group instances with direct completion checks.
