# Complete optimal-set Latin control

**The project has not deciphered the Voynich manuscript.**

This report describes one inspected development control. It does not give a manuscript reading, translation, or historical key.
The result covers one declared finite domain and keeps the earlier failed recovery gate unchanged.

## Scope and result

The earlier score certificate gives lower and upper bounds of `370,396,722` for the target `370,396,722`.
The certificate uses the `bitset` bound and has a live frontier of 25 nodes. `search_exhausted` is `false`.
The published query records force 45 assignments. Unit `c40` remains ambiguous. No unit remains unresolved.
The enumeration gives unit `c40` the full 26-letter lower-case ASCII alphabet before capacity checks.
It visits 5 nodes, reaches 4 feasible leaves, and prunes 22 capacity branches.
It retains 4 maps at the exact target score. The raw product bound is 26.
This is complete only for the supplied weighted ciphertext, lexicon, alphabet, capacity, and forced assignment domain.
Together, the score certificate, forced exclusions, and complete enumeration establish exactly four optimum maps in this finite control.
The secondary model uses training plaintext only, a three-character context, and exact additive smoothing 1/10.
It scores validation tokens with a 28-symbol vocabulary, including unknown and end symbols. Ratios use the `j` map as the baseline.

| Candidate | Free unit `c40` | Exact secondary ratio | Secondary maximizer | Fitted assignments | Test characters | Test words |
| ---: | :---: | :---: | :---: | ---: | ---: | ---: |
| 0 | `j` | `1/1` | no | 45/46 | 111048/111052 | 19927/19931 |
| 1 | `w` | `1/1` | no | 45/46 | 111048/111052 | 19927/19931 |
| 2 | `y` | `1/1` | no | 45/46 | 111048/111052 | 19927/19931 |
| 3 | `z` | `8036/1131` | yes | 46/46 | 111052/111052 | 19931/19931 |

The four exact maps use `c40 = j`, `w`, `y`, and `z`.
The maps cover 46 observed cipher units. Assignments for unused cipher units remain unidentified.
The `z` map is the only exact secondary maximizer and the display map.
It matches all 46 fitted assignments, all 111,052 test characters, and all 19,931 test words in this known control.
The baseline map remains a 45-of-46 assignment match with four test-character errors. This follow-up does not change the earlier failed exact-recovery gate.
The test comparison runs after selection. It does not change the candidate set or the tie rule.

## Provenance and reproduction

The publication freeze commit is `883da35809cb1a3828876f272f108ae103fdf98a`. The freeze precedes the primary run at `09:14:24.58 UTC`.
The secondary protocol hash is `17abf949562b5152c104b8fb8c6987079b22514d87bb93aa155236b2d8c6867c`.
The input records 17 implementation hashes. The three new module hashes are checked below.

| Public record | SHA-256 |
| --- | --- |
| `input.json` | `3a9b5f0fe4dc69abcb13e10dcbf63d8086c2bf329af84d62b47b0477c6470eec` |
| `enumeration.json` | `4a5e43e6331c7e1a4ce32fae3ff84d5af6defcc6d77e641a4260bc6a53b2776c` |
| `ranking.json` | `8641d91ab568326e70539711cb0e48ccc69ec0514b2043496ccef3b65f2d39e0` |
| `selection.json` | `1eb5be203055324320b8d517e83bc42ee8579090bd1718e3194ef09be04f9b82` |
| `result.json` | `112fd2823d569462a6cccd6422d023eafcca987eb4dcb3ed550262d1dc3cb54a` |

| New implementation file | SHA-256 |
| --- | --- |
| `experiments/optimal_set/enumerate.py` | `443b53105412e28b1b00172c38776e6a9d43ef94c45a774533e2a2e0e443e5d8` |
| `experiments/optimal_set/secondary.py` | `367d4ed3bd88a7601183a5870d978c19a50b0a2c7ccdd28127185aae559cdc85` |
| `experiments/optimal_set/run_study.py` | `225ed29bf5ad72733fd7282bcb1f5794a137a1c1ecd9d455cd67b9e020233448` |

Run the fixed study from the clean freeze checkout:

```sh
git checkout 883da35809cb1a3828876f272f108ae103fdf98a
python scripts/fetch_reference_sources.py
python experiments/optimal_set/run_study.py --output-dir results/optimal-set-secondary-v1-latin
```

The summary generator is in the later publication checkout. Run it there against the published records:

```sh
python scripts/build_optimal_set_summary.py
```

The five public JSON records are byte-for-byte copies of the run records.
This script checks their canonical bytes, SHA-256 links, map set, exact ratios, diagnostic totals, and source hashes.
The [verification receipt](optimal-set-verification.json) records 262 passing tests and a clean public replay.
All five replay files match the primary files byte for byte.
The [independent record audit](optimal-set-record-audit.json) rebuilt model counts and exact ratios without importing the secondary scorer.
All 18 audit checks pass. These are internal computational checks, not external scholarly validation.

## Limits

The score certificate and 45 exclusions apply to the fixed Latin control only.
The selected `z` map is a finite-control result. It does not identify manuscript language, meaning, authorship, or plaintext.
The study is inspected exploratory development, not blind validation.
