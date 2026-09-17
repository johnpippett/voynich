# Homophonic search development

The new static root bound is `892,887,632` for the pinned Italian control objective.
The complete independent root bound is `896,647,414`.
The earlier frontier bound is `815,036,950` for the same pinned objective.
The earlier frontier bound remains stronger than the new root bound.

This report describes finite optimization on an inspected Old Italian control.
It does not apply a model to the Voynich Manuscript.
It does not produce a translation, decipherment, or historical reading.

## Run and scope

The supervised run used commit `46798173ee9efe96d00c480d8aabf75540211d42`.
CI run [35211177386](https://github.com/johnpippett/voynich/actions/runs/35211177386) passed before the run.
The run began at `2026-09-17T10:35:59.552720Z`.
The public supervision receipt reports valid numeric outputs and a 29-file freeze.
The resource receipt remains private.
The manifest records the protocol and source hashes.
The protocol SHA-256 is `d44a1a2208d4b90a5d8e1ce13ff9d090ba88b24fa35184328c76dc84caf91821`.
The freeze manifest SHA-256 is `eb880ec0efaa31b500cd540e886b82090963b624f97f609ad3e8f010ea0afed7`.
The builder checks the prior frontier report bytes before it reads JSON values.
The [fixed protocol](../docs/plans/homophonic-search-development-v1.md) defines the inputs, bounds, and limits.

The run used capacity `2`, encryption seed `7000`, and a total map over fitted cipher units.
The search used the training lexicon, validation ciphertext, and two saved start maps.
The source loader may read all source partitions, but the search did not score test data.
The score uses integer weights `count(word) * T + N` and denominator `2*T*N`.

| Input | Value |
| --- | ---: |
| Validation tokens `N` | `31,681` |
| Validation word types `T` | `14,170` |
| Training lexicon types | `6,273` |
| Fitted cipher units | `47` |
| Objective denominator `2*T*N` | `897,839,540` |
| Weighted counts SHA-256 | `664b6498a147b5430695ec0f0ee276c654fabd6a9e567b4960eb7d1f56fad944` |
| Training lexicon SHA-256 | `29d94e0de2a154071c15a9c524a1bb0b73ba2c3a618935be8716e8d3a32824ef` |
| Validation stream SHA-256 | `d7e9c6e0b716cf7ea1c7deb4f135ca2692ea70b4f927548e99668ab0c1428492` |

## Bounds

The current root bounds use the same weighted counts, lexicon, stream hash, capacity, and alphabet.
The static pivot-group bound relaxes conflicts between groups.
The two current root bounds differ by `3,759,782`.

| Bound | Value | Scope |
| --- | ---: | --- |
| Independent root upper bound | `896,647,414` | Complete independent root |
| Static pivot-group root upper bound | `892,887,632` | Current relaxed root |
| Earlier frontier upper bound | `815,036,950` | Earlier 1,000-node frontier |

The current static root gap above the best lower bound is `327,672,618`.
The earlier frontier gap above that lower bound is `249,821,936`.
The earlier frontier value comes from the [reference control report](HOMOPHONIC.md).
It does not become a root bound because it came from a different search stage.

## Local-search results

Both starts used eight accepted improving moves and reached the move budget.
Neither result certifies a local optimum or a global optimum.
Neither result certifies recovery of the planted key.

| Start | Initial score | Final lower bound | Gain | Moves | Evaluations | Stop |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `cold_selected` | `90,866,594` | `166,057,138` | `75,190,544` | `8` | `9,584` | move budget |
| `assisted_selected` | `222,253,278` | `565,215,014` | `342,961,736` | `8` | `9,584` | move budget |

The best complete-map lower bound is `565,215,014`.
The root comparison does not certify the finite objective value.

## Interpretation limits

The [reference control report](HOMOPHONIC.md) records failed recovery gates for the inspected controls.
These development results do not change those gates.
The controls do not estimate a false-positive rate.
They do not reject all keys, all languages, or all cipher models.
They provide no manuscript decipherment or translation.

Independent replay matched all five public outputs and reported a clean, valid run. See the [replay record](homophonic-search-development-v1/replay-verification.json) (SHA-256 `1ccdc907e8fe43635190d45a22fc4c0242e15eb8e22dbf797e35dc4d965f326c`).

## Public artifacts

The builder verifies each output hash before it reads JSON values.
It checks status fields, cross-record hashes, bound ordering, and score arithmetic.

| File | SHA-256 |
| --- | --- |
| [Aggregate report](homophonic-search-development-v1/aggregate.json) | `1a7c224f08e2e0483edc5be851c69cf13ca198b2e19889d4535929a717511ce7` |
| [Manifest](homophonic-search-development-v1/manifest.json) | `4985b91f18a3d6b81ec7de3c63d349ad979217b7c25b041c7bedfde5cc55d190` |
| [Cold key record](homophonic-search-development-v1/cold_selected.key.json) | `91ffd14f8bc5b6dc94b2cf31cbc1e63488bafdbf5b8618d79b429ce816167de8` |
| [Assisted key record](homophonic-search-development-v1/assisted_selected.key.json) | `d77a7fb931ebf1222c496afcb38a5dd5fe887c19e5eea9f368c5af8fb4a90251` |
| [Supervision receipt](homophonic-search-development-v1/supervision.json) | `0c856c39cf0bf2b223908048cc80b9912f534f5176b305f3fbec9e46e0d83446` |
| [Replay receipt](homophonic-search-development-v1/replay-verification.json) | `1ccdc907e8fe43635190d45a22fc4c0242e15eb8e22dbf797e35dc4d965f326c` |
| [Prior cold control](homophonic-feasibility-v1/italian-cold.json) | `4209022e13399bb7347b8f1d098f43c4d0922ae1b9c6df72382ed5553b44b0b3` |
| [Prior assisted control](homophonic-feasibility-v1/italian-assisted.json) | `461ddb0d5f097227d7d521436a3a6ebb459b8d53de973ed2e1e913af3be42f31` |

The [runner review](../experiments/search_development/RUNNER_REVIEW.md) records synthetic checks and input safeguards.
The [freeze review](../experiments/search_development/FREEZE_REVIEW.md) records the external manifest checks.

## Reproduction

Run the summary check from the repository root:

```text
python scripts/build_search_development_summary.py
```
The fixed run command and resource limits are in the [protocol](../docs/plans/homophonic-search-development-v1.md).
The frozen output path refuses existing files.
