# Bifolio v3 result review

Review date: 2026-09-16.

This review compares the previous reports with the bifolio-v3 reports. The previous reports use `conservative-foldout-groups-v2`. The v3 reports use provider `(Q,B)` metadata from `data/bifolio_manifest.json`.

The review reads the JSON reports. It does not change source code or report JSON files.

## Sources and grouping

The v3 reports use these source files.

| Source | SHA-256 | Locus records | Page headers | Q/B groups |
| --- | --- | ---: | ---: | ---: |
| `ZL3b-n.txt` | `bf5b6d4ac1e3a51b1847a9c388318d609020441ccd56984c901c32b09beccafc` | 5,385 | 227 | 52 |
| `IT2a-n.txt` | `7f27a8b0feed8f6de0a99900df6bf912dd1d295c38e5f830bac8b41c3f536fb5` | 5,215 | 225 | 52 |

The two source files agree on Q/B metadata for their 225 shared page headers. Every source locus record has Q and B metadata. The manifest hash used by the reports is `998cb3d6c8327ff0bdf786d52968fa3bec9f5fa9b05ba7ae56065fc9639fad72`.

The v3 context manifests contain all 52 Q/B groups. They assign 35 groups to train, 4 to validation, and 13 to test. Each group occurs in one split. The pairwise intersections between split group sets are zero. Therefore, no complete Q/B group crosses train and test.

The predictive manifests contain 50 groups. They assign 34 groups to train, 3 to validation, and 13 to test. Groups `71` and `73` are absent because the predictive run receives paragraph records. These groups contain only `Lz` and `Cc` records in both source files. They remain present in the context manifests.

Q/B metadata is complete for these provider source files. It is not an independent conservation examination. The physical grouping remains conditional on the provider metadata.

## Exact sample changes

The old reports contain 94 groups. The v3 reports contain 52 Q/B groups. The split hash prefix also changed from `voynich-408-v1:` to `voynich-bifolio-408-v3:`. The new group map and prefix therefore change the deterministic assignment.

`T/V/E` below means train, validation, and test. Each cell is `old -> v3`.

| Run | Context records, T/V/E | Context target positions, T/V/E | Predictive records, T/V/E | Predictive tokens, T/V/E |
| --- | --- | --- | --- | --- |
| ZL split | `3736 -> 3480 / 417 -> 374 / 1232 -> 1531` | `14056 -> 12743 / 1381 -> 2041 / 5597 -> 6250` | `2809 -> 2603 / 317 -> 308 / 1004 -> 1219` | `23265 -> 21620 / 2365 -> 2880 / 8559 -> 9689` |
| ZL join | `3736 -> 3480 / 417 -> 374 / 1232 -> 1531` | `12900 -> 11702 / 1257 -> 1877 / 5140 -> 5718` | `2809 -> 2603 / 317 -> 308 / 1004 -> 1219` | `21610 -> 20074 / 2191 -> 2669 / 7928 -> 8986` |
| IT split | `3731 -> 3473 / 413 -> 374 / 1071 -> 1368` | `16538 -> 15299 / 1617 -> 2481 / 6851 -> 7226` | `2808 -> 2603 / 317 -> 308 / 993 -> 1207` | `23493 -> 21820 / 2355 -> 2895 / 8563 -> 9696` |

The 78 changed page labels are the same for all three runs. The IT source has 225 page labels. ZL has 227. The ZL-only labels are `f116v` and `fRos`.

- Old test to v3 train, 22 labels: `f7r`, `f7v`, `f30r`, `f30v`, `f37r`, `f37v`, `f40r`, `f40v`, `f43r`, `f43v`, `f47r`, `f47v`, `f50r`, `f50v`, `f52r`, `f52v`, `f55r`, `f55v`, `f76r`, `f76v`, `f115r`, `f115v`.
- Old test to v3 validation, 2 labels: `f108r`, `f108v`.
- Old train to v3 test, 28 labels: `f6r`, `f6v`, `f15r`, `f15v`, `f17r`, `f17v`, `f25r`, `f25v`, `f28r`, `f28v`, `f29r`, `f29v`, `f32r`, `f32v`, `f57r`, `f57v`, `f75r`, `f75v`, `f77r`, `f77v`, `f82r`, `f82v`, `f93r`, `f93v`, `f96r`, `f96v`, `f106r`, `f106v`.
- Old train to v3 validation, 8 labels: `f21r`, `f21v`, `f22r`, `f22v`, `f73r`, `f73v`, `f111r`, `f111v`.
- Old validation to v3 test, 6 labels: `f3r`, `f3v`, `f65r`, `f65v`, `f113r`, `f113v`.
- Old validation to v3 train, 12 labels: `f2r`, `f2v`, `f16r`, `f16v`, `f33r`, `f33v`, `f38r`, `f38v`, `f67r1`, `f67r2`, `f67v1`, `f67v2`.

The ZL reports retain 149 of 227 page labels in the same split. The IT reports retain 147 of 225 page labels in the same split. The source record index sets change with these page moves. The report manifests contain the exact index arrays.

## Context scores

`B-U` is unigram bits minus original bigram bits. Positive values favor the bigram. `S-O` is shuffled-training bits minus original-training bits. Positive values favor original order. Units are bits per scored target.

Each cell gives `old -> v3 (change)`.

| Run | Test B-U | Test S-O | Validation B-U | Validation S-O |
| --- | ---: | ---: | ---: | ---: |
| ZL split | `-0.777117 -> -0.732901 (+0.044216)` | `0.117208 -> 0.138289 (+0.021081)` | `-0.621827 -> -0.635384 (-0.013556)` | `0.285799 -> 0.245275 (-0.040523)` |
| ZL join | `-0.724129 -> -0.703948 (+0.020182)` | `0.102365 -> 0.116814 (+0.014449)` | `-0.670548 -> -0.624358 (+0.046190)` | `0.101482 -> 0.167780 (+0.066298)` |
| IT split | `-0.793730 -> -0.767238 (+0.026492)` | `0.147108 -> 0.159087 (+0.011979)` | `-0.713562 -> -0.680856 (+0.032706)` | `0.176177 -> 0.274855 (+0.098679)` |

The v3 test group-bootstrap estimates use 499 draws and seed 408.

| Run | B-U estimate and 95% interval | S-O estimate and 95% interval |
| --- | ---: | ---: |
| ZL split | `-0.732901 [-0.792649, -0.658627]` | `0.138289 [0.037996, 0.225785]` |
| ZL join | `-0.703948 [-0.736950, -0.641562]` | `0.116814 [0.055330, 0.173114]` |
| IT split | `-0.767238 [-0.829710, -0.687346]` | `0.159087 [0.054273, 0.232204]` |

The fixed bigram remains worse than the unigram on every v3 test. Original-order training remains better than shuffled-order training on every v3 test.

## Character prediction scores

These values are observed test loss in bits per predicted symbol. Lower values are better. Each cell gives `old -> v3 (change)`.

### Raw EVA units

| Run | Order 0 | Order 1 | Order 2 | Order 3 |
| --- | ---: | ---: | ---: | ---: |
| ZL split | `3.877258 -> 3.887775 (+0.010517)` | `2.090043 -> 2.104476 (+0.014434)` | `1.869951 -> 1.883552 (+0.013601)` | `1.871815 -> 1.884411 (+0.012595)` |
| ZL join | `3.892190 -> 3.902353 (+0.010163)` | `2.106148 -> 2.117312 (+0.011164)` | `1.880076 -> 1.889263 (+0.009186)` | `1.883861 -> 1.890499 (+0.006639)` |
| IT split | `3.882072 -> 3.888756 (+0.006684)` | `2.110912 -> 2.116479 (+0.005567)` | `1.882395 -> 1.885436 (+0.003041)` | `1.884686 -> 1.885535 (+0.000849)` |

### Declared grouped units

| Run | Order 0 | Order 1 | Order 2 | Order 3 |
| --- | ---: | ---: | ---: | ---: |
| ZL split | `3.810750 -> 3.836643 (+0.025893)` | `2.293840 -> 2.323335 (+0.029495)` | `2.135607 -> 2.168251 (+0.032645)` | `2.161399 -> 2.198594 (+0.037195)` |
| ZL join | `3.829878 -> 3.855714 (+0.025836)` | `2.314917 -> 2.340971 (+0.026054)` | `2.150875 -> 2.178991 (+0.028115)` | `2.182388 -> 2.211863 (+0.029475)` |
| IT split | `3.824752 -> 3.843934 (+0.019182)` | `2.317202 -> 2.337552 (+0.020350)` | `2.149401 -> 2.170058 (+0.020657)` | `2.177190 -> 2.197039 (+0.019850)` |

For order 3, the v3 observed loss remains below the matching shuffled-training null.

| Run | Raw EVA null, old -> v3 | Grouped-unit null, old -> v3 |
| --- | ---: | ---: |
| ZL split | `3.232067 -> 3.254175 (+0.022109)` | `3.292708 -> 3.347452 (+0.054744)` |
| ZL join | `3.252251 -> 3.292900 (+0.040649)` | `3.349881 -> 3.407862 (+0.057981)` |
| IT split | `3.241368 -> 3.252023 (+0.010655)` | `3.318199 -> 3.333512 (+0.015312)` |

The v3 correction raises the reported character losses because the held-out page population changes. Orders 1, 2, and 3 remain below order 0 and beat the matching order-three shuffle control. These are structural scores. They do not identify a language or a translation.

## Changed and unchanged conclusions

The changed items are the physical split population, the group count, the split counts, and the numerical scores. The score changes are descriptive partition effects. They are not evidence that the model improved.

The following items did not change.

- The source hashes and total source records remain the same.
- The structure inventory and word-order sample remain identical in all three runs.
- The seed remains 408. The reports use 499 bootstrap draws and 499 word-order permutations.
- Context score target positions still match the declared split records.
- The fixed bigram remains worse than the unigram on each test split.
- Original-order context training remains better than shuffled training.
- Character order remains predictive under the declared raw and grouped-unit controls.
- The v3 manifests keep complete groups out of multiple splits.

A repeat check matched the full-ZL analysis after removal of only `created_utc`. The canonical JSON SHA-256 was `df6ad61d984d91991b4593a9ecc7919d306587f49c743ecf65c3d4c8aac3edad`.

These reports remain exploratory. The Q/B split is complete with respect to provider metadata. It still needs independent physical conservation verification before a confirmatory claim.

## Files reviewed

- [v3 ZL split report](../../reports/bifolio-v3/zl-split.json)
- [v3 ZL join report](../../reports/bifolio-v3/zl-join.json)
- [v3 IT split report](../../reports/bifolio-v3/it-split.json)
- [old ZL split report](../../reports/zl-split.json)
- [old ZL join report](../../reports/zl-join.json)
- [old IT split report](../../reports/it-split.json)
- [bifolio manifest](../../data/bifolio_manifest.json)
