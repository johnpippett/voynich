# Bitset bound review

Review date: 2026-09-17.

This internal review covers `experiments/homophonic/bitset_bound.py`, its
integration in `solver.py`, and the focused tests. It uses synthetic inputs
only. It reads no VMS or reference data.

## Result

I found no blocking correctness defect.

The bound uses one real bit for each root-compatible candidate and one high
sentinel per word lane. The sentinel expression counts a lane at most once.
The weight masks then sum each active lane weight. Duplicate candidate rows do
not increase a lane score. Zero-weight lanes contribute zero.

The root filter removes length conflicts, inconsistent repeated cipher units,
and over-capacity candidate preimages. Empty lanes and empty input return a
zero bound. Large integer weights use the same weighted-bit path.

The capacity masks are correct for capacities one and two. For capacity two,
an empty partial preimage adds no restriction beyond the root filter.
One assigned unit allows candidate preimages of size zero or one.
A size-two candidate must contain that assigned unit.
Two assigned units require the candidate preimage to be their subset.
The partial-key validator rejects unknown symbols, unknown plaintext letters,
and capacity violations. It keeps no byte arrays after construction; stored
masks are integers.

The solver selects this bound only for capacities one, two, and `None`. It
builds the same candidate lanes as the scalar engine. The bitset path and the
reference path returned equal keys, scores, bounds, node counts, statuses, and
pruning results in the checks below.

## Documentation check

The earlier class docstring omitted the allowed size-zero candidate preimage
for one assigned unit. The current docstring includes this case.
The documentation change did not alter the code or tests.

The partition of candidate bits into lanes is a score bound, not a count of
candidate rows. Keep this distinction in metadata and result descriptions.

## Checks

The scoped tests passed:

```text
PYTHONPATH=src:. python -m unittest experiments.homophonic.test_bitset_bound experiments.homophonic.test_solver -v
Ran 23 tests ... OK
```

An independent scalar implementation checked 24,046 partial maps across 240
random cases and capacities one, two, and unlimited. Every weighted bound
matched.

An independent solver comparison checked 2,160 combinations of random cases,
capacities, and node budgets `0`, `1`, `3`, and `None`. The reference and
bitset engines matched on all compared result fields.

The direct capacity-two mask fixture covered size-zero, size-one, and size-two
preimage unions. A separate inspection found no retained `bytearray` state in
the constructed engine.

These finite checks are internal behavioral evidence. They are not a formal
proof of the implementation.

## Source hashes

SHA-256 hashes for the reviewed snapshot:

```text
8ab50b9700497cc493e0ba79a9fc6d452cf95e5b8c7d9d19d0de08b567000f76  experiments/homophonic/bitset_bound.py
5e5b0d1bd21dcdf850d9154c088065d2cd6174671083dc6b5b935282da0c2760  experiments/homophonic/solver.py
c07744794d3772c36b7f40a09e9e0c5597ec2ff0776b99354d7c48ae9bb559e8  experiments/homophonic/test_bitset_bound.py
ca453ea178336d9dec0e685a7ddca0eec63daf1426f1f419adb24a9aad5ecde4  experiments/homophonic/test_solver.py
```
