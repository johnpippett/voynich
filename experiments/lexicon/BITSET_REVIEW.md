# Bitset bound review

Review date: 2026-09-16.

Scope: read-only review of `experiments/lexicon/bitset_bound.py` and its focused tests.
The review covers the proposed broadword bound and its implementation.
It does not read or run manuscript data.
It does not verify solver integration.
This is an internal AI-agent review.
It is not external scholarly validation or formal program verification.

## Result

The implementation matches the proposed algorithm. I found no correctness defect in the bound.

The bound is an upper bound for the fixed candidate lists.
The checks below show the same value as direct candidate compatibility enumeration.
For a complete injective key, it returns the weighted lexicon hit score.
This applies when the candidate lists come from the exact lexicon pattern index.

## Algorithm check

The constructor creates one real bit for each candidate. It creates one high sentinel after each word lane. It also stores one low bit at each lane start.

For a partial assignment `c -> p`, the implementation uses:

```text
allowed = ((~presence[c] & ~plaintext_use[p]) | mapping[c,p]) & real_mask
```

This has the required cases.

- A candidate with no `c` assignment is allowed when it does not use `p`.
- A candidate with `c -> p` is allowed by `mapping[c,p]`.
- A candidate with another assignment for `c` is rejected.
- A candidate that uses `p` for another cipher symbol is rejected.

The code intersects one `allowed` mask for every assigned pair.
The partial key validator rejects repeated plaintext values.
Therefore, the intersection represents all candidates that match the full injective partial key.

For a lane with `n` candidate bits, the packed lane is:

```text
candidate bits:  base ... base+n-1
high sentinel:               base+n
```

The non-empty lane operation is:

```text
flags = ((active | high_sentinels) - low_lane_bits) & high_sentinels
```

If a lane has no active candidate, its numerator contains only the high sentinel. Subtracting the low bit removes the sentinel. If a lane has any active candidate, subtracting the low bit borrows within that lane. The high sentinel remains set. A zero-length lane has the same low and high bit, so its empty result is zero.

No borrow crosses a lane boundary. Each lane numerator is at least its own high sentinel. Its subtraction of one is therefore non-negative within the lane. This also holds for a lane with zero candidates, where the numerator and low bit are equal.

The implementation stores a mask for each weight bit at the lane sentinel. `bit_count()` on `flags & weight_mask` counts non-empty compatible lanes with that weight bit. The weighted sum reconstructs each lane weight exactly. Duplicate candidate entries receive separate candidate bits, but they set one lane sentinel only once.

## Edge cases

The constructor and tests cover these cases.

- Empty input and empty candidate maps.
- Empty word lanes.
- Lanes with no candidates.
- Zero weights and no weight-bit masks.
- Repeated cipher symbols.
- Repeated plaintext symbols required by a repeated cipher symbol.
- Rejected non-injective candidate mappings.
- Plaintext alphabet symbols absent from every candidate.
- Tuple symbols such as `("ka", "kb")`.
- Large integer weights.
- Duplicate candidate entries.
- Invalid candidate lengths, mappings, alphabets, and partial keys.

Absent plaintext alphabet symbols remain valid completion values. They do not appear in `plaintext_use` until a candidate uses them. This is correct for the compatibility bound.

## Independent checks

The focused test command passed all 10 tests:

```text
PYTHONPATH=. python -m unittest discover -s experiments/lexicon -p 'test_bitset_bound.py' -v
Ran 10 tests ... OK
```

I also ran an independent Python check. It used a separate compatibility function. It did not call the bitset masks to compute the expected value. For 300 random cases with seed `20260916`, it checked 143,958 partial keys. Every bitset result matched the direct weighted compatibility sum.

I checked the sentinel operation separately. I enumerated four packed lanes with every lane length from 0 through 4 and every active candidate mask. This covered 923,521 lane and active-mask combinations. Every result matched the per-lane reference. No interlane borrow occurred.

I checked complete keys against direct lexicon scores. The check used 500 random cases with seed `20260916` and 5,063 complete injective keys. Every result matched the direct score.

These checks include duplicate normalized words, empty lanes, zero weights, repeated symbols, absent alphabet symbols, and tuple symbols. The focused tests also check the root bound and metadata.

## Limits and follow-up

This review checks the bound class against the supplied candidate lists. It does not prove that a caller built the candidate lists from the intended lexicon. It does not test runtime or memory use on a full lexicon. It does not verify use of this class in `solver.py`.

The broadword state has one bit per candidate and one sentinel per lane. Weight masks also scale with the largest weight bit. Measure construction cost and bound cost before replacing the existing scalar bound in a large search.

No unresolved algorithmic finding appeared in the reviewed checks.
