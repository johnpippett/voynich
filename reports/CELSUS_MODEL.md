# Celsus known-cipher control

The fixed solver failed to recover the Celsus control text exactly.
It stopped at 1,000 search nodes with unequal score bounds.
The saved map recovered 92,936 of 150,708 test characters and 3,675 of 27,147 test words.
The result is `incomplete_search`; it is not a certified optimum or a manuscript reading.

## Fixed input and method

The [source projection](CELSUS_PROJECTION.md) and [chapter partitions](CELSUS_PARTITIONS.md) supply the accepted Celsus input.
This is one ancient medical work in a modern scholarly edition. It is not a medieval medical corpus.
The source normalization and exclusions remain unchanged.

The [reference protocol](../docs/plans/celsus-reference-control-v1.md) fixes the model and data partitions.
The [operational plan](../docs/plans/celsus-model-run-v1.md) fixes the command, output checks, and resource limits.
The run uses capacity two, seed `7000`, a bitset bound, 1,000 nodes, and no warm start.
The solver receives the encrypted validation words and the plaintext training lexicon.
The runner saves its fitted map before test encryption and accuracy diagnostics.
The known control map enters encryption and post-search diagnostics only.

The corrected run used commit `ab859004f25d1fea69939b70eb5f992d0e58688d`.
The [43-file freeze](../experiments/medical/control-freeze-v1.json) has SHA-256
`63c862d19c6891d43257b36f2e0f15c88529d0929b1087022fc46260c1bc371f`.
The command exited successfully and wrote valid numeric records.
Successful execution did not satisfy the recovery gates.

## Solver result

| Measurement | Result |
| --- | ---: |
| Training word tokens | 62,423 |
| Training lexicon types | 10,805 |
| Validation word tokens, N | 12,145 |
| Validation cipher word types, T | 8,015 |
| Fitted cipher units | 48 |
| Objective denominator, 2NT | 194,684,350 |
| Fitted score and reported solver lower bound | 16,202,725 |
| Reported solver upper bound | 170,919,175 |
| Post-search planted-map score | 166,472,985 |
| Search nodes | 1,000 |
| Remaining frontier nodes | 24,703 |
| Score certified | No |
| Search exhausted | No |

The objective adds `count(word) * T + N` for each cipher word type decoded to a training-lexicon entry.
The saved map gives 1,620 validation token hits and 265 type hits.
Its normalized objective is approximately 8.32%. This percentage is a dictionary score, not character accuracy.

The known control map gives 10,739 token hits and 6,620 type hits, with a normalized score of approximately 85.51%.
That post-search diagnostic shows a much better feasible map exists. It did not initialize or change the fitted map.
The planted score remains below the reported upper bound. Neither fact certifies the optimum.

## Recovery measurements

| Measurement | Validation | Test |
| --- | ---: | ---: |
| Correct characters | 41,682 / 67,319 | 92,936 / 150,708 |
| Character accuracy | 61.92% | 61.67% |
| Correct words | 1,535 / 12,145 | 3,675 / 27,147 |
| Word accuracy | 12.64% | 13.54% |
| Unobserved cipher positions | 0 | 0 |
| Exact recovery gates | All fail | All fail |

The fitted map agrees with 14 of the 48 observed control assignments.
Every test position uses an observed unit. The test errors therefore arise from wrong assignments, not missing test-unit coverage.
The four declared units absent from fitting remain outside the fitted map.

The [model record](celsus-model-control-v1/cold.json), [saved map](celsus-model-control-v1/cold.keys.json), and [supervision record](celsus-model-control-v1/supervision.json) retain the full aggregate result.
No source words or plaintext paragraphs are included in these public files.

## Verification

A fresh anonymous public checkout repeated source retrieval, text projection, chapter partitioning, and the fixed model command.
All three model output files matched the primary run byte for byte.
The [replay receipt](celsus-model-control-v1/replay-verification.json) records the pinned commit, commands, and matching hashes.

A [separate calculation](../scripts/verify_celsus_model_independently.py) verified all pinned inputs before parsing.
It independently implemented cyclic emission, objective scoring, and character and word comparisons.
It shares the fixed seeded-key generator and accepted partition inputs.
The calculation confirmed the stream hashes, fitted-map coverage, capacity, scores, key agreement, and recovery gates.
The [audit receipt](celsus-model-control-v1/independent-audit.json) records those checks.
It did not repeat the search or independently reconstruct the upper bound.

The [wrapper review](../experiments/medical/CONTROL_WRAPPER_REVIEW.md) records 24 passing core and wrapper tests.
The command tests include a real subprocess with a synthetic child.

## Preserved initial attempt

The first command used commit `dc71f118122becccc009f6c8859915e310bc47e2`.
It stopped before child launch because an output-path constant was assigned after the command-line entry point.
Import-based tests had not exposed that execution order.
The fix moved the assignment and added a subprocess regression.

The [initial freeze](../experiments/medical/control-freeze-v1-initial.json) and [failed launch record](celsus-model-control-v1/attempt-1/launch.json) remain available.
No model result came from that attempt. The correction changed no source partition, objective, seed, or solver setting.

## Reproduction and limits

Use a fresh checkout of `ab859004f25d1fea69939b70eb5f992d0e58688d`.
Reproduce the pinned projection and partition stages from their linked reports before running:

```sh
python -m experiments.medical.run_control
```

The wrapper refuses existing model outputs and changed input bytes.
The model command does not use the network. Keep source text outside the public repository.

This is a known artificial cipher on one author and work. It does not provide an independent sample of historical languages.
The failed bounded search does not reject medical Latin, homophonic encodings, or other manuscript models.
It shows that this fixed solver configuration did not recover this control.
No manuscript measurement or translation follows from the result.
