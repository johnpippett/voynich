# Group bitset bound review

Review date: 2026-09-17.

This review covers `experiments/group_bound/bitset.py`, its focused tests, the
bitset design, the reviewed scalar pivot bound, and the frozen
`experiments/homophonic/bitset_bound.py`. It uses synthetic data only. It does
not run a corpus search or solver integration.

Reviewed hashes:

```text
experiments/group_bound/bitset.py          9587d8cfa67a8e174b24a23d83a4f392c54587efe1bdb5553c5d8352efb2693b
experiments/group_bound/test_bitset.py     be465e6bb796eff1a451d71e818dc03abe763f6b49ce04b805a8dd0e835badee
experiments/group_bound/BITSET_DESIGN.md   85d5a8aed275b6baa84e67d50db63b85d848a3146b550d18a8bcacb61b8870fb
experiments/group_bound/pivot.py           8573d5d620c474ef24b5c5c875d26442ff8c7dcfbfd97fef98650d520d479d8b
experiments/homophonic/bitset_bound.py    8ab50b9700497cc493e0ba79a9fc6d452cf95e5b8c7d9d19d0de08b567000f76
```

## Result

I found no mathematical or implementation defect in the checked scope.

The adapter builds its complete candidate rows through the reviewed scalar
constructor. It passes the same normalized counts and rows to the frozen bitset
engine. It computes lane highs as `base + row_count`, then advances by one
sentinel slot. It checks lane, candidate, sentinel, and slot counts against the
frozen metadata.

The active mask applies presence, mapping, and capacity masks. The capacity
rules for one and two preimage units match the frozen engine. Unlimited
capacity applies no preimage mask. The flags expression counts each active lane
once. Weight masks produce the same independent bound as the frozen engine.

Each group stores pivot, word lanes, high-bit positions, and weight. A query
creates only temporary group and residual masks. It enumerates legal pivot
letters and applies the child capacity mask. Residual lanes use the independent
bound. The group and residual lanes partition the scalar word types. Repeated
pivots and repeated cipher units remain separate and safe.

Total capacity infeasibility returns no numeric bound. Candidate-row and
storage-estimate limits fail before the adapter returns an object. The storage
value is an estimate, and metadata states that it is not an operating-system
memory limit. The source hash and private-field checks fail closed when the
frozen layout changes.

## Independent checks

The focused scalar and bitset suites pass:

```text
PYTHONPATH=src:. python -m unittest experiments.group_bound.test_pivot experiments.group_bound.test_bitset -v
Ran 13 tests ... OK
```

An independent deterministic sweep covered 120 small random instances and
1,091 valid partial maps. It compared bitset and scalar status, group bound,
and independent bound for capacities `1`, `2`, and `None`. It also compared
true completion scores by direct enumeration. Every case satisfied:

```text
true completion score <= group bound <= independent bound
```

The sweep included repeated units, empty words, zero weights, empty candidate
lanes, Unicode tuple units, explicit residual groups, repeated pivots, and
capacity-infeasible domains.

Additional malformed probes passed. An inconsistent repeated-unit cache was
rejected. A missing private mask was rejected. A metadata candidate-count
mismatch was rejected. A frozen-source hash mismatch, row limit, and storage
estimate limit were rejected before a bound was returned.

No corpus data, reference search, or global optimum claim was used. The result
is a finite synthetic upper-bound primitive. It does not prove a key or a
historical reading.
