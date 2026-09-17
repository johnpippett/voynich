# Homophonic search development v1

Status: development design only. Date: 2026-09-17.

This plan tests two search improvements on the inspected Old Italian `cap2`
control with encryption seed `7000`. It does not change the frozen pilot, its
gates, or its published results. It does not apply a model to the Voynich
Manuscript.

The development run has two parts:

1. Measure the static pivot-group root upper bound against the independent root
   upper bound.
2. Run exact lexical local search from the published cold and assisted maps.

The run can compare complete lower bounds with the root group bound. It does
not add the group bound to the exact tree search.

## Fixed input

Use the same validation ciphertext counts, training lexicon, alphabet, and
capacity as the Italian `cap2` controls. Use the integer objective from the
frozen runner:

```text
weight(word) = count(word) * T + N
```

Here `T` is the number of validation word types and `N` is the number of
validation tokens. Keep capacity `2`, plaintext alphabet `a` through `z`, and
the one total map model.

The current pinned aggregate input is:

| Item | Value |
| --- | ---: |
| Validation tokens `N` | 31,681 |
| Validation word types `T` | 14,170 |
| Training lexicon types | 6,273 |
| Fitted cipher units | 47 |
| Complete root candidate rows | 12,549,021 |
| Bitset storage estimate | 1,759,288,862 bytes |
| Validation stream hash | `d7e9c6e0b716cf7ea1c7deb4f135ca2692ea70b4f927548e99668ab0c1428492` |
| Training lexicon hash | `29d94e0de2a154071c15a9c524a1bb0b73ba2c3a618935be8716e8d3a32824ef` |
| Objective denominator `2*T*N` | 897,839,540 |

The run may recreate the fixed encrypted validation stream with the existing
control generator and seed. That step creates the pinned control input. The
planted map must not enter local search, the group bound, a target score, a
fixed assignment, or a tie rule.

Use the planted key only inside that fixed input-generation step. Pass only the
weighted ciphertext counts and training lexicon to the two new APIs.

The pinned source files mix all three canticles. Source verification and parsing therefore read bytes assigned to all partitions.
Use the frozen loader, then pass only training and validation data to fitting. Do not score the test partition.
Keep raw words and ciphertext in local input storage. Write only hashes and aggregate values to the public report.

## Pinned artifacts

Verify these files before the run. A hash mismatch stops the run before model
construction.

| Artifact | SHA-256 |
| --- | --- |
| `data/reference_manifest.json` | `f261b781f150991e3305aae5057a94dc91afd8e59c58bb22ff199347f5ce3e6d` |
| `docs/plans/visual-homophonic-pilot.md` | `0e6a6edf5e0172f5e7a0f1fbf2f7ede8b9b181c7180aa616de58f44ae04d1249` |
| `reports/homophonic-feasibility-v1/italian-cold.json` | `4209022e13399bb7347b8f1d098f43c4d0922ae1b9c6df72382ed5553b44b0b3` |
| `reports/homophonic-feasibility-v1/italian-cold.keys.json` | `08a3b0b6cf76e013efb8175bd6fa1251fd1ae9ae1911a96420d123ae81198e50` |
| `reports/homophonic-feasibility-v1/italian-assisted.json` | `461ddb0d5f097227d7d521436a3a6ebb459b8d53de973ed2e1e913af3be42f31` |
| `reports/homophonic-feasibility-v1/italian-assisted.keys.json` | `df35fb2e7d1df309f60030d984e01a22837c92af37c72d0bf8d9c5a765b097fe` |

The two selected maps are inputs. Their current exact lexical scores are
`90,866,594` for cold and `222,253,278` for assisted. Both published searches
stopped at 1,000 nodes and remain uncertified. The published frontier bound
`815,036,950` is not a root bound and is not the independent baseline for this
plan.

Treat these modules as frozen inputs:

| Module | SHA-256 |
| --- | --- |
| `experiments/homophonic/solver.py` | `5e5b0d1bd21dcdf850d9154c088065d2cd6174671083dc6b5b935282da0c2760` |
| `experiments/homophonic/bitset_bound.py` | `8ab50b9700497cc493e0ba79a9fc6d452cf95e5b8c7d9d19d0de08b567000f76` |
| `experiments/homophonic/controls.py` | `4845d1de4e766c5d63b23919bab2715db24b431ba502112494e477a1740fd896` |
| `experiments/homophonic/run_controls.py` | `65f81693336a3c705281ed711b45881a19a0adc34b715a29188dc1361d86be63` |
| `experiments/lexicon/run_pilot.py` | `2eb25cdeb4fdf8ef167a3f10c2463b1ef61c23b1dd7e34a3aea9368c6edf69e5` |
| `src/voynich/corpus.py` | `064c45794d523b5c07ea10621752e325d35709f619e0763ac6ba1561f0fa1dc2` |
| `src/voynich/groups.py` | `15b77e967ce296634a36a3deacba660c14a4d4615c99597949b5586d682bdef0` |
| `src/voynich/substitution.py` | `3c246844b9adcd003d593eff97b53c6a3d1f54bc1fd76bc8e5145345aadf3332` |
| `src/voynich/reference.py` | `97e173c761b137d3653a827315b62a68af3e96abd189afdecc46e9759d2b94d9` |
| `experiments/group_bound/pivot.py` | `8573d5d620c474ef24b5c5c875d26442ff8c7dcfbfd97fef98650d520d479d8b` |
| `experiments/group_bound/bitset.py` | `9587d8cfa67a8e174b24a23d83a4f392c54587efe1bdb5553c5d8352efb2693b` |
| `experiments/lexical_warmstart/warmstart.py` | `85c261e0c88e335321d0ae76b86878bc3798518c3e715295aef9d678305d36b0` |

The new runner and its tests must be hashed in the freeze manifest. Do not
run a result until those hashes exist. The manifest must also record the
command, Python version, platform, resource limits, and output paths.

## Part 1: static root bound

Construct `BitsetPivotGroupBound` with:

```text
ciphertext_counts       = frozen weighted validation counts
plaintext_lexicon       = frozen training lexicon
plaintext_alphabet      = "abcdefghijklmnopqrstuvwxyz"
capacity                = 2
groups                  = None
partial_key             = {}
```

With `groups=None`, the scalar API assigns every non-empty word type to the
group for its smallest sorted cipher unit. This is the fixed
`static_min_symbol` rule. It is not selected from the result.

Use the complete candidate cache. Set these guards:

```text
max_candidate_rows          = 12,600,000
max_estimated_storage_bytes = 2,000,000,000
```

The expected complete cache has 12,549,021 rows. A different count stops the
run. The bitset estimate is a construction guard. It is not an operating
system memory limit.

At the empty root, record only:

* complete or failed construction status;
* candidate row, lane, group, and residual type counts;
* independent root bound;
* static pivot-group root bound;
* the integer gap `independent_root_bound - group_root_bound`;
* the frozen bitset source hash and storage estimates.

The API also returns group word arrays and residual word arrays. Do not place
these fields in the public report. They contain normalized ciphertext word
types. Keep only counts and hashes.

Require the admissibility checks:

```text
0 <= group_root_bound <= independent_root_bound
```

The lower-bound comparison in Part 2 must also satisfy:

```text
best_complete_map_score <= group_root_bound
```

If either check fails, classify the run as an implementation failure. Do not
publish a numeric bound from a failed or incomplete construction.

## Part 2: exact lexical local search

Call `lexical_local_search` twice. Use the same weighted validation counts and
training lexicon as Part 1. Start from the complete maps in the pinned key
records:

| Start | Input key record | Move budget |
| --- | --- | ---: |
| `cold_selected` | `italian-cold.keys.json` | 8 accepted improving moves |
| `assisted_selected` | `italian-assisted.keys.json` | 8 accepted improving moves |

The API evaluates all legal single-unit reassignments and two-unit swaps at
each step. It accepts the largest positive exact score gain. Equal gains use
the smallest complete key in sorted cipher-unit order. No random seed is
used.

Use these fixed arguments:

```text
capacity       = 2
move_budget    = 8
initial_key    = the selected key for this start
trace_mode     = "summary"
```

The runner must verify that each initial score equals its pinned report score.
It must verify that each returned map is total, capacity-valid, and scored by
the same integer objective. The local search result is a feasible lower bound.
It is not a global optimum and it does not recover the planted key by itself.

Use the API's `trace_mode="summary"` setting. It keeps per-iteration counts
without retaining every neighbor map. Keep accepted move records local and
discard them from the public report after recording:

* initial and final exact scores;
* score improvement;
* accepted move count;
* evaluation count;
* stop status and local-neighborhood status;
* final map hash and key-record hash.

With 47 units and capacity 2, eight iterations stay below a declared
per-start limit of 11,000 move evaluations. Abort if the API exceeds that
limit or if its map validation fails. The two starts have a total trace limit
of 22,000 evaluations.

Save each complete fit output in a new key record before any later diagnostic.
The key record may contain the complete fitted map and aggregate score. It
must not contain raw reference words, candidate rows, or ciphertext streams.

## Combined root comparison

After both key records exist, set

```text
best_lower_bound = max(cold_final_score, assisted_final_score)
```

The root group bound is an admissible upper bound for the same finite problem.
Report its gap to `best_lower_bound`. If the values are equal, the complete
root bound gives a certificate for the finite objective value. This does not
prove key uniqueness, language, translation, or a manuscript result.

Do not pass the local maps into the group-bound construction as fixed
assignments. The root query must remain `partial_key={}`. Do not use a local
map to change group membership, candidate rows, or branch rules.

Do not integrate the group bound into `solve_lexicon` in this experiment. Do
not run a new exact tree search. This experiment measures a root relaxation
and lower-bound improvement only.

## Resource limits

Run one process at a time. Use one CPU worker. Apply these limits:

| Resource | Limit |
| --- | ---: |
| Root bound wall time | 1,200 seconds |
| Full development run wall time | 1,500 seconds |
| Root candidate rows | 12,600,000 |
| Estimated bitset storage | 2,000,000,000 bytes |
| Sampled child resident memory | 7 GiB |
| Resource polling interval | 0.25 seconds |
| Termination grace period | 5 seconds |
| Local-search evaluations per start | 11,000 |

The previous Italian bitset run reached 5,622,080 KiB resident memory.
The supervisor samples the child process through Linux `/proc` every 0.25 seconds.
The 7 GiB guard is not a kernel memory limit. Memory use can exceed it between samples.
No virtual address-space limit applies in this run.
The supervisor measures root completion from child launch, including input loading.
Wall-time checks can exceed their limits by the polling interval and termination time.
On a limit, send termination to the owned process group. Send a kill signal after the five-second grace period.
Record `resource_abstain`; do not use a partial cache or partial bound.
Keep incomplete output local. Publish numeric results only after the supervisor confirms a complete run.

## Freeze and output

Use the fixed supervised entry point from the published freeze revision:

```sh
python -m experiments.search_development.run_frozen
```

The entry point verifies `experiments/search_development/freeze-v1.json` before child launch.
The manifest must contain the exact 29-file set declared in `run_frozen.py`.
That set includes the protocol, new modules, tests, frozen dependencies, and input reports.
The manifest does not contain its own hash. The public revision binds the manifest bytes.

The child writes `manifest.json`, `cold_selected.key.json`, `assisted_selected.key.json`, and `aggregate.json` under
`reports/homophonic-search-development-v1/`.
The supervisor writes `supervision.json` in the same directory.
Its full resource receipt is private at `results/search-development-v1/resources.json`.
Refuse existing output files and symlinks. Do not overwrite a previous attempt.
Local files do not become public until they pass result review and are committed.

Before the run, publish this plan and freeze one manifest. The manifest must
include:

* all input paths and hashes in this plan;
* the reference manifest hash and validation stream hash;
* the two input key hashes and report hashes;
* all frozen module hashes;
* hashes for the new runner and tests;
* the exact command and parameter values;
* resource limits and output paths.

The run has one deterministic configuration. Do not add seeds, move budgets,
groups, candidate limits, or retry settings after inspecting its result. A
new setting is a new development run with a new manifest.

Write the fit key records before the aggregate diagnostic report. The public
diagnostic report may contain only hashes, counts, scores, bounds, gaps,
statuses, resource data, and scope limits. Exclude raw reference text,
ciphertext arrays, candidate rows, lexicon arrays, group word lists, and the
full local-search evaluation trace.

Use these result labels:

* `development_only`: the normal completed status;
* `resource_abstain`: a declared resource limit stopped construction;
* `input_mismatch`: a pinned hash or expected count failed;
* `implementation_failure`: a bound or score invariant failed.

Do not call `development_only` a success gate. A higher lower bound can show
that the local search found a better finite-map incumbent. It cannot repair the
known-cipher control gate or establish recovery of the planted key.

## Interpretation limits

The group bound is a relaxation. It ignores conflicts between groups and can
remain loose. The local search explores only single-unit reassignments and
two-unit swaps. A stop after eight accepted moves is a budget result, not a
global search result.

The cold and assisted maps use the same inspected validation input. Their
comparison is a development comparison, not an independent replicate. The
control's planted key and test metrics remain post-fit diagnostics from the
published reports and must not guide this run.

This plan tests finite optimization behavior on one known-cipher control. It
does not test VMS text, a historical language, a reading direction, or a
decipherment.

The project wiki will record implementation review, publication, and results.
