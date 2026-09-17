# Conditional assessor review

Review date: 2026-09-17.

This review covers `experiments/identifiability/assess.py` and
`experiments/identifiability/test_assess.py`. It uses finite synthetic
problems only. It does not use reference or VMS data.

I read `AGENTS.md`, `wiki/README.md`, and the study protocol before this review.
The protocol is `docs/plans/optimal-key-identifiability-v1.md`.
The recorded protocol hash includes the later status change from draft to fixed settings.

## Result

I found no correctness defect in the tested finite problems.

The assessor gives a conditional result. It accepts a caller-supplied global
certificate after it checks the objective fingerprint, target, and provenance
metadata. It does not prove that the source certificate is correct. This is
an API limit by design. The reference runner must check source hashes and
certificate provenance before it calls this module.

The assessor checks every cipher unit in the problem. It does not use only
units from positive dictionary hits. A complete map and an exact score are
required for every returned witness.

## Independent checks

I compared the results with direct enumeration of every feasible map. The
checker used seed `20260917` and covered:

- 94 cases: four fixed edge cases and 90 random cases.
- Capacities `1`, `2`, and `None`.
- Node budgets `0` through `8` and `None`.
- Zero weights, an empty lexicon, repeated cipher units, and repeated words.

This produced 2,820 assessor calls and 7,920 unit records. Every witness
matched an independently enumerated optimal map. No finite-budget result
reported a false forced assignment or a false ambiguous assignment. An
unbounded query returned `ambiguous` exactly when another optimal map changed
the tested unit. It returned `forced_at_certified_optimum` otherwise.

An explicit zero-weight unit check also passed. A unit that occurred only in a
zero-weight word still received a result. Capacity made it forced in one case
and ambiguous in the other cases.

The focused assessor tests passed:

```text
PYTHONPATH=src:. python -m unittest experiments.identifiability.test_assess -v
Ran 8 tests ... OK
```

The complete identifiability test set passed 33 tests. `py_compile` also passed
for the two reviewed files.

## Checked behavior

The warm witness path changes one incumbent assignment at a time. It removes
the old letter from the capacity count before it checks the new letter. It
tries all legal alternative letters in sorted order. It recomputes the full
integer word-hit score. A score above the supplied target raises
`CertificateContradiction`.

The assessor passes a valid warm witness to the threshold query as an initial
key. The threshold API treats this key as a witness only. It does not restrict
the root search. The final witness and its score are checked again.

The assessor rejects an incomplete, over-complete, invalid, or capacity
incompatible incumbent before it runs a query. It also rejects an incumbent
whose score does not equal the supplied target.

The query status mapping is conservative:

- `feasible` with a complete alternative witness becomes `ambiguous`.
- `infeasible` becomes `forced_at_certified_optimum`.
- A live budget frontier becomes `unresolved`.

With a zero budget, a live frontier remains `unresolved`.
A direct witness or domain contradiction can resolve a query before search.
The assessor does not turn a budget stop into an exclusion.

Each unit query starts from the same incumbent and creates a new threshold
query. A prior witness does not become a constraint for a later unit. Repeated
calls produce the same records and fingerprints.

## Limits

`forced_at_certified_optimum` is valid only when the supplied source
certificate proves the global target for the same objective and domain. The
assessor records provenance but does not inspect the source proof.

The module tests one-unit alternatives. Separate alternative witnesses need
not occur together in one map. A full map is unique in the declared domain
only if every assignment is forced. These results do not establish a
historical key, a language, or a translation.

The module depends on `ThresholdProblem` for admissible bounds and query
status. The independent enumeration checked small complete domains. It did
not prove the implementation for a larger reference problem.

## Source hashes

```text
e043aa38e7e40800f5e03af4a35e5931965eecd374f38e8bcf7a799caeb868c0  experiments/identifiability/assess.py
1b2698262caada842f9a175464d134d09935205f0fe027725c7e7996b8c5448d  experiments/identifiability/test_assess.py
f4699b0a32ee383c414a8ffe155fc0a4fe1aac65ce2a2225fd9ff3a3225436c8  experiments/identifiability/threshold.py
de773c43a4dc85521697c1147bd5f683d3ee15db71baae876c8b1545aad77f79  experiments/identifiability/test_threshold.py
ba61e56ff7730531f946450ac86b910842fc313bb52b7b34b415391125d6046d  docs/plans/optimal-key-identifiability-v1.md
```

This task changed only this review file. The project wiki was not changed
because the task scope owns this file and the root agent handles the wiki.
