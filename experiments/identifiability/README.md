# Assignment identifiability prototype

This prototype asks whether a constrained map can reach a fixed dictionary score.
It distinguishes a complete witness, a proved exclusion, and an unresolved search.
It currently has synthetic tests only.

The [study protocol](../../docs/plans/optimal-key-identifiability-v1.md) defines the reference follow-up.
The earlier [homophonic model](../homophonic/README.md) defines the map domain and score.

## Components

- `threshold.py` caches one finite problem and answers independent threshold queries.
- `incremental_bound.py` reuses one parent mask for temporary child-bound calculations.
- `assess.py` compares each selected assignment with all alternative values.
- `run_assessment.py` checks the fixed Latin certificate and records the proposed reference study.

The incremental adapter is separate from the threshold search until integration passes review.
Keep active masks out of the search frontier. Each mask can require substantial memory.
The four published homophonic controls use their original frozen implementation.

## Verification

Run the synthetic tests from the repository root:

```sh
PYTHONPATH=src:. python -m unittest discover -s experiments/identifiability -p 'test_*.py' -v
```

A feasible threshold result is not an optimum certificate.
Conditional identifiability requires a certified target for the same objective and domain.
The runner checks hashes and scope. It uses the source certificate without independently proving it.
The proposed reference study will record that certificate's provenance.
No component establishes a manuscript language, key, or translation.
