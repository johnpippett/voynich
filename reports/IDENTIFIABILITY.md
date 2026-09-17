# Optimal-key identifiability

The fixed Latin `cap2` control uses target `370396722` for a finite lexicon and a capacity of 2.
The 46 fitted units classify as 45 forced, 1 ambiguous, and 0 unresolved.
These classifications apply to the supplied finite objective and domain. They do not establish historical truth or key uniqueness.
The earlier homophonic pilot had 4 errors in 111052 test character positions.
It recovered 45 of 46 fitted unit assignments. This assessment does not change that result.
The forced units cover 111048 test positions with 0 errors.
The ambiguous units cover 4 test positions with 4 errors.
All 4 earlier errors are in the ambiguous category.
This follow-up uses an inspected control failure. It is exploratory and is not blind validation.

## Finding

A `forced` result means that the threshold proof excluded every map with score at or above the target after it forbade the selected letter.
This result is conditional on the published certificate, finite lexicon, alphabet, capacity, and query settings.
The query code checks certificate metadata. It does not prove the global certificate.
An `ambiguous` result has a target-scoring witness with the selected letter forbidden. Each witness is a separate map.
An `unresolved` result means that the bounded query did not classify the unit.

## Test diagnostics

The table compares each category with the planted control map. This post-query diagnostic did not set or repair a classification.

| Category | Units | Map matches | Test positions | Correct | Errors |
| --- | ---: | ---: | ---: | ---: | ---: |
| `forced_at_certified_optimum` | 45 | 45 | 111048 | 111048 | 0 |
| `ambiguous` | 1 | 0 | 4 | 0 | 4 |
| `unresolved` | 0 | 0 | 0 | 0 | 0 |
| `unobserved` | 0 | 0 | 0 | 0 | 0 |

The diagnostic rows cover 111052 test character positions.
The `unobserved` row covers test units outside the fitted map.

## Scope and replay

The source certificate comes from the published Latin homophonic control at report SHA-256 `923dba00df53ff05ca88e91362ea44c693d66b8f0824071d85cc5b0d984ba77e`.
The [baseline protocol](../docs/plans/visual-homophonic-pilot.md) has SHA-256 `0e6a6edf5e0172f5e7a0f1fbf2f7ede8b9b181c7180aa616de58f44ae04d1249` and uses commit `ce8b626ab3cf8147829716f7828dff7fceba6cde`.
The [identifiability protocol](../docs/plans/optimal-key-identifiability-v1.md) has SHA-256 `ba61e56ff7730531f946450ac86b910842fc313bb52b7b34b415391125d6046d`.
The [run record](identifiability-v1-latin/run.json) stores the complete source hash map and the certificate metadata.
The identifiability protocol is frozen at commit `f7dbb21d4281f440b05542be0fbd8eec638136fe`.
The [runner](../experiments/identifiability/run_assessment.py), [assessor](../experiments/identifiability/assess.py), and [threshold API](../experiments/identifiability/threshold.py) define the replay.

```sh
python experiments/identifiability/run_assessment.py \
  --output-dir results/identifiability-v1-latin
```

Replay inputs include the [baseline report](homophonic-feasibility-v1/latin-cold.json) and its [key record](homophonic-feasibility-v1/latin-cold.keys.json).
The runner regenerates the 46 query records and writes them to the output directory.
A separate public checkout reproduced all 49 JSON files byte for byte.
The [verification record](identifiability-verification.json) gives the checks and their limits.
The [reference-corpus note](../docs/research/reference-corpora.md) defines the Latin control source.
No VMS data or plaintext is used in this assessment. The result does not support a decipherment claim.

## Public records

The generator wrote this report only after it verified all 46 query files, the decisions hash, the query hashes, and the diagnostic totals.

| Record | Link |
| --- | --- |
| Run | [run.json](identifiability-v1-latin/run.json) |
| Decisions | [decisions.json](identifiability-v1-latin/decisions.json) |
| Assessment | [assessment.json](identifiability-v1-latin/assessment.json) |

## Unit results

The 46 queries used 1616 nodes in total.

| Unit | Selected | Result | Nodes | Record |
| --- | --- | --- | ---: | --- |
| `c00` | `n` | `forced` | 31 | [JSON](identifiability-v1-latin/c00.json) |
| `c01` | `a` | `forced` | 18 | [JSON](identifiability-v1-latin/c01.json) |
| `c02` | `h` | `forced` | 53 | [JSON](identifiability-v1-latin/c02.json) |
| `c03` | `x` | `forced` | 54 | [JSON](identifiability-v1-latin/c03.json) |
| `c04` | `d` | `forced` | 38 | [JSON](identifiability-v1-latin/c04.json) |
| `c05` | `s` | `forced` | 20 | [JSON](identifiability-v1-latin/c05.json) |
| `c06` | `l` | `forced` | 41 | [JSON](identifiability-v1-latin/c06.json) |
| `c07` | `f` | `forced` | 49 | [JSON](identifiability-v1-latin/c07.json) |
| `c08` | `q` | `forced` | 50 | [JSON](identifiability-v1-latin/c08.json) |
| `c09` | `x` | `forced` | 55 | [JSON](identifiability-v1-latin/c09.json) |
| `c10` | `b` | `forced` | 42 | [JSON](identifiability-v1-latin/c10.json) |
| `c11` | `i` | `forced` | 12 | [JSON](identifiability-v1-latin/c11.json) |
| `c12` | `k` | `forced` | 56 | [JSON](identifiability-v1-latin/c12.json) |
| `c14` | `t` | `forced` | 23 | [JSON](identifiability-v1-latin/c14.json) |
| `c15` | `m` | `forced` | 32 | [JSON](identifiability-v1-latin/c15.json) |
| `c16` | `k` | `forced` | 57 | [JSON](identifiability-v1-latin/c16.json) |
| `c17` | `g` | `forced` | 45 | [JSON](identifiability-v1-latin/c17.json) |
| `c18` | `a` | `forced` | 19 | [JSON](identifiability-v1-latin/c18.json) |
| `c21` | `v` | `forced` | 46 | [JSON](identifiability-v1-latin/c21.json) |
| `c22` | `q` | `forced` | 52 | [JSON](identifiability-v1-latin/c22.json) |
| `c23` | `m` | `forced` | 33 | [JSON](identifiability-v1-latin/c23.json) |
| `c24` | `z` | `forced` | 58 | [JSON](identifiability-v1-latin/c24.json) |
| `c26` | `v` | `forced` | 47 | [JSON](identifiability-v1-latin/c26.json) |
| `c27` | `e` | `forced` | 16 | [JSON](identifiability-v1-latin/c27.json) |
| `c28` | `o` | `forced` | 30 | [JSON](identifiability-v1-latin/c28.json) |
| `c29` | `u` | `forced` | 27 | [JSON](identifiability-v1-latin/c29.json) |
| `c30` | `t` | `forced` | 22 | [JSON](identifiability-v1-latin/c30.json) |
| `c31` | `b` | `forced` | 43 | [JSON](identifiability-v1-latin/c31.json) |
| `c32` | `u` | `forced` | 26 | [JSON](identifiability-v1-latin/c32.json) |
| `c33` | `n` | `forced` | 29 | [JSON](identifiability-v1-latin/c33.json) |
| `c34` | `c` | `forced` | 34 | [JSON](identifiability-v1-latin/c34.json) |
| `c35` | `o` | `forced` | 28 | [JSON](identifiability-v1-latin/c35.json) |
| `c36` | `p` | `forced` | 36 | [JSON](identifiability-v1-latin/c36.json) |
| `c37` | `r` | `forced` | 25 | [JSON](identifiability-v1-latin/c37.json) |
| `c38` | `c` | `forced` | 35 | [JSON](identifiability-v1-latin/c38.json) |
| `c39` | `g` | `forced` | 44 | [JSON](identifiability-v1-latin/c39.json) |
| `c40` | `j` | `ambiguous` | 0 | [JSON](identifiability-v1-latin/c40.json) |
| `c41` | `r` | `forced` | 24 | [JSON](identifiability-v1-latin/c41.json) |
| `c43` | `e` | `forced` | 17 | [JSON](identifiability-v1-latin/c43.json) |
| `c44` | `p` | `forced` | 37 | [JSON](identifiability-v1-latin/c44.json) |
| `c45` | `h` | `forced` | 51 | [JSON](identifiability-v1-latin/c45.json) |
| `c46` | `l` | `forced` | 40 | [JSON](identifiability-v1-latin/c46.json) |
| `c47` | `i` | `forced` | 13 | [JSON](identifiability-v1-latin/c47.json) |
| `c49` | `f` | `forced` | 48 | [JSON](identifiability-v1-latin/c49.json) |
| `c50` | `d` | `forced` | 39 | [JSON](identifiability-v1-latin/c50.json) |
| `c51` | `s` | `forced` | 21 | [JSON](identifiability-v1-latin/c51.json) |

## Independent review limits

This report validates public record integrity and scope. It does not rebuild the corpus or the heavy bound.
The planted-map comparison is an audit diagnostic. It does not turn a conditional result into a truth claim.
The inspected-control failure limits the evidence. A later manuscript study would need its own protocol and certificate.

<!-- Source hashes are retained in run.json. -->
