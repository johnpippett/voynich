# Pivot-group bound prototype

This directory contains two upper-bound implementations for finite homophonic word-hit search.
They do not search for a key or prove an optimum.
Synthetic checks compare their bounds with complete small map domains.

`PivotGroupBound` uses the frozen helpers in
`experiments.homophonic.solver` to normalize word counts, the plaintext
lexicon, the plaintext alphabet, and capacities `1`, `2`, or `None`. It builds
all root-compatible rows for every usable lexicon word of the same length.
It does not use a row sample. `max_candidate_rows` raises
`CandidateConstructionLimit` before the object returns a bound when the
complete cache exceeds the declared limit.

Call `bound(partial_key)` to obtain:

- `independent_bound`: the existing relaxation that adds each word weight when
  at least one candidate remains compatible with the partial map;
- `group_bound`: the pivot-group relaxation;
- `groups` and `ungrouped_words`: records that make the calculation auditable;
- `claims_global_optimality: False` and scope limits.

When no groups are supplied, the prototype assigns each non-empty word type to
the group for its smallest cipher unit. A caller can supply `(pivot, words)`
pairs or mappings with `pivot` and `words`. Every group word must occur in the
ciphertext counts, each group word must contain its pivot, and word types must
occur in at most one group.

For a group `G` with pivot `c`, partial map `P`, and plaintext letter `p`, let

```text
S(G, p, P) = sum(weight(w) for w in G
                 if a compatible candidate row for w maps c to p)
```

The prototype returns

```text
group_bound = sum(max_p S(G, p, P) for each group G)
               + independent weight of every ungrouped word
```

Every complete map gives the pivot one legal letter. Each hit word in a group
therefore appears in the matching `S(G, p, P)` term. The sum is an upper bound.
The calculation ignores conflicts between groups and capacity conflicts across
groups, so it can remain loose. The groups and ungrouped words partition the word types.
Each group term is a subset of its independent terms. Therefore,
`group_bound <= independent_bound`.

Status `complete` means that the bound calculation finished. It does not certify a search optimum.

The cache stores tuples of normalized words and rows. Queries only filter this
cache. The root construction scans each usable lexicon word for each matching
cipher word length. A query scans the stored rows for each word in its group.
The scalar prototype has no bitset engine or reference-corpus path.

`BitsetPivotGroupBound` uses the frozen candidate masks for the same calculation.
It checks the frozen module hash and mask layout before use.
Its construction guards limit candidate rows and estimated mask storage.
The estimate is not an operating system memory limit.
Queries keep one temporary group mask. They do not retain a mask for each search node.

Read the [bitset design](BITSET_DESIGN.md), [scalar review](REVIEW.md), and [bitset review](BITSET_REVIEW.md).
The [development protocol](../../docs/plans/homophonic-search-development-v1.md) defines the first reference-control use.
