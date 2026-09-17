# Incremental bound review

Review date: 2026-09-17.

This is an internal computational review. It uses synthetic inputs only. It
does not run reference or VMS data, and it does not claim scholarly validation.

The review covers `incremental_bound.py` and `test_incremental_bound.py`. I
read `AGENTS.md`, `wiki/README.md`, and `21.01 Homophonic Controls` before the
review. I did not edit the frozen homophonic modules or the wiki.

## Result

The incremental child mask matches the base bound for capacities `1`, `2`, and
`None` under the state-construction API. I found no arithmetic defect in the
trusted state path. The state API hardening also resolves the earlier direct
constructor hazard.

Let `P` be the active candidate mask for a parent state. For a child
assignment `c -> p`, the code applies:

```text
P_child = P & (~presence[c] | mapping[c,p]) & real_mask
```

This keeps a candidate when it does not contain `c`, or when it maps `c` to
`p`. The parent mask already contains all earlier assignment filters.

The code then updates only the capacity mask for `p`. Other plaintext letters
keep their parent constraints. For capacity one, the candidate preimage must
have size zero or contain the assigned unit. For capacity two, one assigned
unit permits size zero or one and requires a size-two preimage to contain that
unit. With two assigned units, the candidate preimage must be a subset of those units.
The empty set and singleton subsets remain valid.
For unlimited capacity, no capacity mask changes. These rules match the base
engine's capacity mask and also handle repeated plaintext assignments.

`child_state()` rejects a repeated cipher unit, an unknown unit, an unknown
plaintext symbol, and a capacity overflow. `state()` canonicalizes and checks
the complete partial key. The owner check uses object identity. The dataclass
is frozen. Empty lanes, empty input, zero weights, repeated cipher units,
duplicate candidates, and complete assignments remain covered by the tests.

The sentinel score expression is unchanged from the base engine. It therefore
counts each active lane once and applies the lane weight once. The child mask
does not alter score or bound rules.

## Independent checks

The focused tests passed:

```text
PYTHONPATH=. python -m unittest \
  experiments.identifiability.test_incremental_bound \
  experiments.homophonic.test_bitset_bound -v
Ran 13 tests ... OK
```

An independent scalar checker used a separate root filter and compatibility
implementation. With seed `20260917`, it checked 120 random synthetic cases,
2,996 parent states, and 2,010 child states across capacities `1`, `2`, and
`None`. All weighted results matched. The cases included empty lanes,
duplicate candidates, zero weights, repeated cipher units, and repeated
plaintext assignments.

`py_compile` passed for both reviewed files.

## Constructor boundary resolution

`BoundState` now rejects direct construction. `dataclasses.replace()` also
fails because the dataclass has no public initializer. Field assignment remains
blocked by the frozen dataclass. The owner check rejects a state from another
engine.

The adapter creates states through its private factory after it validates the
partial key and derives the active mask. Direct construction and replacement
therefore cannot forge a state through the supported API.

The private factory uses `object.__new__`. It declares that it is an
implementation contract, not a security boundary. Reflection can still create
an invalid object, but this internal prototype does not expose that operation
as a supported API.

The earlier one-lane check demonstrated the pre-hardening failure:

```text
root score: 1
forged partial key with root mask: 1
forged zero mask: 0
```

The hardening tests now reject this route through direct construction,
`dataclasses.replace()`, field mutation, and foreign-owner use. The previous
correctness finding is resolved for the supported API. Keep the trusted private
factory contract when integrating this adapter into certified search.

## Source hashes

```text
2f1e1dce34fec1b069b1a9adb83cc785681167542ca2232e7bff95f7e4e0e6ce  experiments/identifiability/incremental_bound.py
506016fbb2f93ce174b5e0f0a76ee9552b6bf3430ed088791e6a4b298f65782a  experiments/identifiability/test_incremental_bound.py
8ab50b9700497cc493e0ba79a9fc6d452cf95e5b8c7d9d19d0de08b567000f76  experiments/homophonic/bitset_bound.py
c07744794d3772c36b7f40a09e9e0c5597ec2ff0776b99354d7c48ae9bb559e8  experiments/homophonic/test_bitset_bound.py
```

This review changed only this review file. The task scope prohibited a wiki
update, so no wiki file changed.
