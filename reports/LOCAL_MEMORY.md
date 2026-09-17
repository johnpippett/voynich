# Local-memory diagnostic

This is an exploratory diagnostic. It tests whether a recent word helps predict the next word under a finite edit kernel. It does not test translation, language, or historical copying.

The run uses `raw_eva` characters and `split` spacing. It uses the existing complete paragraph-line filter. The filter keeps lines with at least three tokens, no dropped tokens, and no `<->` or `<~>` diagram interruption. The split has 34 train groups, 3 validation groups, and 13 test groups. The data were inspected before this run. Therefore, the result is exploratory. The procedure ran after the lean plan. It had no public precommit freeze and no independent replay.

## Result

The exact-copy family selected `lambda=0` in both validation sets. Its test score is therefore the baseline score. The edit family selected `lambda=0.1`. It selected window 4 for ZL and window 16 for IT. Its validation gain was 0.019968 bits per target for ZL and 0.027821 for IT. This gain did not transfer reliably to the test sets.

| Source | Test baseline | Test edit | Absolute gain | Tail null excess (rank) | Same-length null excess (rank) |
| --- | ---: | ---: | ---: | ---: | ---: |
| ZL | 7.453892 | 7.458060 | -0.004167 | +0.002794 (0.21) | -0.000072 (0.53) |
| IT | 7.581044 | 7.579780 | +0.001264 | -0.003068 (0.91) | -0.001656 (0.79) |

The absolute gain is baseline loss minus edit loss. A positive value means lower edit loss. Order excess compares the observed edit loss with the mean loss from a null. A positive value means lower observed loss. Each null has 99 draws. The tail null uses seed 408. The same-length null uses seed 409. The first word stays fixed. The rank is `(1 + null losses <= observed loss) / 100`, where lower loss is better.

Neither source has a positive order excess against both nulls. Stop this finite edit-kernel branch. The test does not identify a language, a copying process, or a historical mechanism.

## Limits

Across both test sets, 2,887 of 13,476 target positions mapped to `UNK` (21.4%). `UNK` means a target word type that is absent from the repeated training vocabulary. The scores are mapped-target loss. They do not measure full word identity.

The same seven of thirteen test groups have positive edit gains in both transcriptions. These shared groups are not independent transcription replications. The split and the paragraph-line filter were already inspected. A new hash or split does not make this evidence unseen. The full proposed pipeline did not run. No bootstrap or control calibration was performed.

## Reproduction

Run these commands in a clean checkout. Use Python with assertions enabled.
Do not use `-O` or set `PYTHONOPTIMIZE`. The scripts use assertions for input and score checks.

```text
python scripts/fetch_sources.py
python scripts/run_local_memory_diagnostic.py ZL
python scripts/check_local_memory_order.py ZL
python scripts/run_local_memory_diagnostic.py IT
python scripts/check_local_memory_order.py IT
```

The run records are:

- [ZL selection](local-memory-diagnostic-v1/ZL/selection.json)
- [ZL test](local-memory-diagnostic-v1/ZL/test.json)
- [ZL order](local-memory-diagnostic-v1/ZL/order.json)
- [IT selection](local-memory-diagnostic-v1/IT/selection.json)
- [IT test](local-memory-diagnostic-v1/IT/test.json)
- [IT order](local-memory-diagnostic-v1/IT/order.json)

The procedure is [the diagnostic runner](../scripts/run_local_memory_diagnostic.py) and [the order checker](../scripts/check_local_memory_order.py). The design is [the lean plan](../docs/plans/local-memory-predictive-v1.md). Input attribution and source hashes are in [the source manifest](../data/source_manifest.json).
