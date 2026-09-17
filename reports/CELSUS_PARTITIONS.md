# Celsus reference partitions

Research date: 2026-09-17. Status: partition stage complete; cipher control pending.

The fixed procedure retained all 550 projected paragraphs from eight books and
211 chapters. It produced 101,715 normalized word tokens.
These are reference-text preparation results. They establish no manuscript reading.

## Fixed split result

| Partition | Chapters | Paragraphs | Word tokens | Word types | Roman-like tokens |
| --- | ---: | ---: | ---: | ---: | ---: |
| Training | 124 | 252 | 62,423 | 10,805 | 702 |
| Validation | 38 | 123 | 12,145 | 3,794 | 316 |
| Test | 49 | 175 | 27,147 | 6,328 | 419 |

The procedure assigns complete chapters in source order within each book.
Training receives the first `floor(0.60*n)` chapters. Validation receives the
next `floor(0.20*n)` chapters. Test receives the remainder.
This rule does not balance word or paragraph counts.

No paragraph became empty after normalization. No alphabetic run was rejected.
No exact normalized paragraph sequence occurred in more than one partition.
The procedure retains repeated sequences within one partition. Near duplicates
and shared vocabulary remain possible.

Roman-like tokens contain only letters in `ivxlcdm`. This count does not
identify historical numbers, quantities, or dosages. These tokens remain words
in the reference stream.

## Source and method

The input is the [accepted Celsus projection](CELSUS_PROJECTION.md).
The [fixed protocol](../docs/plans/celsus-reference-control-v1.md) records the
chapter split, token rules, duplicate rule, and later cipher-control settings.
The [partition manifest](celsus-reference-control-v1/partition-manifest.json)
records source locations, counts, implementation hashes, and private-output hashes.

Celsus adds one ancient medical work. Author, period, genre, language, and
editorial differences remain confounded. This is not a replicated medical sample.
Chapter separation does not make adjacent chapters or books independent.

## Publication and verification

The initial code appeared in commit `ea0b847111219000cd697d5620c62317e9cc4826`.
GitHub checks found a test dependency on local source files.
Commit `afcb1f2a959f57f902c779f6bd16e882ab894d4e` replaced those inputs with synthetic fixtures.
The production partition code and text rules did not change.
The [initial manifest](../experiments/medical/partition-freeze-v1-initial.json)
preserves the earlier record. The revised manifest changes only the test-file hash.

[GitHub checks passed](https://github.com/johnpippett/voynich/actions/runs/35216105502)
before the first source run began at `2026-09-17T11:32:11.556640+00:00`.
The primary run used a clean checkout of the corrected public commit.
It used the accepted source bytes after checksum verification.

A separate clean public checkout fetched the pinned source and rebuilt the
projection. Its partition run reproduced all three output files byte for byte.
The [replay record](celsus-reference-control-v1/replay-verification.json)
records both command exits and the exact output hashes.

A [separate verifier](../scripts/verify_celsus_partitions_independently.py)
reconstructed normalization, chapter assignments, duplicate handling, and token streams.
It imported neither the adapter nor the partition runner.
Its [audit record](celsus-reference-control-v1/independent-audit.json) confirms
the private arrays, paragraph rows, and complete adapter manifest.
These are internal computational checks, not external historical validation.

## Reproduce the result

Use a fresh checkout with no existing projection or partition outputs.

```sh
python -m experiments.medical.run_projection --output-dir results/celsus-projection-v1
python -m experiments.medical.run_partition
python scripts/verify_celsus_partitions_independently.py
```

The first command fetches the pinned source. The second checks the published
acceptance receipt and all 18 frozen input hashes before paragraph parsing.
The third checks its own pinned inputs before independent calculation.
The commands retain source text and token arrays in ignored local directories.

The public partition-manifest SHA-256 is
`634ed31c54e1147ee930c6261ed9261938ec120f310db2e22ed54bca630dc9e1`.
Later cipher runs must use this fixed manifest. They must save the fitted key
before test encryption and accuracy scoring. No cipher fit occurred in this stage.
