# Substitution result review

Review date: 2026-09-16.

This is a read-only audit of the planted controls and the corrected manuscript
runs. It covers:

* `results/substitution-pilot/latin-32keys.json`
* `results/substitution-pilot/italian-32keys.json`
* `results/substitution-v3-reviewed/{latin-zl,latin-it,italian-zl,italian-it}.json`
* the four matching `.keys.json` files

The reviewed reports are byte-for-byte copies of the public files in
`reports/substitution/`. The audit did not change source code, result files, or
key files. It did not publish data.

## Result

No hash, key-freeze, coverage, arithmetic, or oracle-leak defect was found in
the reviewed outputs.

The planted controls recovered every tested key. This result calibrates search
power on known synthetic substitutions. It does not show that the manuscript
has that substitution form, language, or plaintext.

The manuscript runs have lower test loss for the observed input than for the
within-word shuffle and identity controls in all four conditions. The scores
are calibration values. They are not statistical rejection thresholds.

## Hash and freeze checks

The four reports have these source hashes:

| source | SHA-256 |
| --- | --- |
| `ZL3b-n.txt` | `bf5b6d4ac1e3a51b1847a9c388318d609020441ccd56984c901c32b09beccafc` |
| `IT2a-n.txt` | `7f27a8b0feed8f6de0a99900df6bf912dd1d295c38e5f830bac8b41c3f536fb5` |

Each report source hash equals the local source file and the entry in
`data/source_manifest.json`. The report hash for that manifest is
`77c9f755ed47c19ccfe3ef92b7699953d5d5e9ada729492662c94154d3d2f4f1`.
The reference manifest hash is also equal to the current
`data/reference_manifest.json` hash in every report.

The reports use these current code hashes. All report values match the local
files:

| file | SHA-256 |
| --- | --- |
| `scripts/run_voynich_substitution.py` | `7e5e779677e149b35e68bf64f2df34608b751544fd126049ea7c1f9ce94e03cd` |
| `src/voynich/corpus.py` | `064c45794d523b5c07ea10621752e325d35709f619e0763ac6ba1561f0fa1dc2` |
| `src/voynich/reference.py` | `97e173c761b137d3653a827315b62a68af3e96abd189afdecc46e9759d2b94d9` |
| `src/voynich/substitution.py` | `3c246844b9adcd003d593eff97b53c6a3d1f54bc1fd76bc8e5145345aadf3332` |
| `src/voynich/groups.py` | `c4cf7918e9a32cf511b7315eb54de0cde151424b008038222da9a7a2577b9bc3` |

For each manuscript run, the exact bytes of the matching `.keys.json` file
hash to the report `key_record_sha256`. Both key dictionaries in the report
equal the matching key file. Each report sets
`key_frozen_before_test_scoring` to `true`.

The key file records this rule:

`Lowest training objective only; no validation or test key selection.`

The key records select eight restarts by their training objective. The report
does not use validation or test scores to select a key.

## Coverage and score accounting

The parser keeps complete non-empty paragraph loci only. It rejects records
with excluded tokens or diagram interruption markers. The corrected reports
record the parser policy, source hash, filter counts, and shuffle seeds.

Independent parsing reproduced every filter count, group assignment, split
word count, score field, and lexical field.

| language | source | key symbols | words train/validation/test | test key coverage | observed bits | shuffled bits | identity bits | observed lexical hits |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Latin | ZL3b | 24 | 14,523 / 2,280 / 7,162 | 21/22 (95.45%) | 5.0375 | 6.1966 | 6.4792 | 776/7,162 (10.83%) |
| Latin | IT2a | 20 | 17,450 / 2,778 / 8,272 | 20/21 (95.24%) | 5.1601 | 6.1620 | 6.4611 | 710/8,272 (8.58%) |
| Italian | ZL3b | 24 | 14,523 / 2,280 / 7,162 | 21/22 (95.45%) | 4.4098 | 5.5407 | 5.8644 | 809/7,162 (11.30%) |
| Italian | IT2a | 20 | 17,450 / 2,778 / 8,272 | 20/21 (95.24%) | 4.4286 | 5.5445 | 5.8470 | 779/8,272 (9.42%) |

The test key coverage denominator is the number of distinct cipher symbols in
the test split. One test symbol is unseen by the training key in each run.
The scores still include every test word. An unknown symbol is handled by the
scoring API and is recorded in the report; it is not silently removed.

The test random-key baseline has 32 keys per run. Its bit ranges are:

| language | source | random test range, bits per symbol |
| --- | --- | ---: |
| Latin | ZL3b | 6.2089–6.9765 |
| Latin | IT2a | 6.2433–6.9867 |
| Italian | ZL3b | 5.9189–6.6984 |
| Italian | IT2a | 5.6844–6.4770 |

The random keys use seed 409. An independent recomputation reproduced all 32
values and both range endpoints in every report.

Filter accounting also reproduced the corrected report fields:

| source | total records | eligible records | eligible accepted words | records with excluded tokens | excluded tokens | diagram records |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| ZL3b | 5,385 | 2,877 | 23,965 | 780 | 1,137 | 470 |
| IT2a | 5,215 | 3,438 | 28,500 | 66 | 160 | 613 |

The remaining records are non-paragraph or have no accepted tokens. These
categories are present in the report and are disjoint by the documented
filter order.

## Planted controls

The 32-key reports use seeds 500 through 531. The search receives synthetic
ciphertext made from sampled reference validation words. The model was trained
on reference training words. The search does not receive the planted key or
held-out plaintext. In all 32 runs for each language:

| language | fitting words | held-out words | exact key recovery | exact character recovery | exact word recovery | held-out bits per symbol |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Latin | 19,969 | 19,931 | 32/32 | 32/32 | 32/32 | 1.8943496695 |
| Italian | 20,000 | 31,152 | 32/32 | 32/32 | 32/32 | 2.4652542406 |

The learned-key and planted-key held-out scores are equal in every control
because every fitted key is exact. The search records
`reference_key_provided: false`.

These native scores are not direct controls for the manuscript scores. The
native controls use reference-language words and a complete synthetic
substitution. The manuscript runs use raw EVA words, a 20- or 24-symbol source
alphabet, and a model trained on the native reference corpus. Word domains,
symbol coverage, and input normalization differ. A value such as 4.4 or 5.0
bits per symbol must therefore not be read as a rejection threshold against
the 1.89 or 2.47 native control value.

## Oracle and interpretation limits

The manuscript fit uses reference training words only. The observed and
within-word-shuffle keys are selected from training objectives. Test scoring
starts after key-file creation, and the key hash matches the frozen file. No
reference key is supplied to either manuscript search.

The within-word shuffle preserves word count, order, length, and each word's
character multiset. It is one calibration condition. The 32 random keys per
run provide a small reference range. Neither defines a null distribution or a
formal false-positive rate.

The language model scores within-word character sequences. It does not score
word order. The split policy uses provider Q/B metadata and reports complete
provider coverage, but it does not include an independent conservation
examination (`independent_conservation_verification: false`). The grouping and
source conventions remain stated limits of the result.

The reports describe an exploratory search. They do not provide a translation,
identify a language, or establish a decipherment.

## Checks run

* Recomputed source, source-manifest, reference-manifest, grouping-manifest,
  code, and key-record hashes.
* Compared the reviewed reports with the earlier v3 reports. Fit dictionaries
  and numerical score values are equal; the corrected reports also label each
  score with its actual partition.
* Reparsed ZL3b and IT2a with the reported filter policy and reproduced all
  filter counts, group manifests, split word counts, and lexical counts.
* Recomputed all observed, shuffled, identity, and random-key score fields.
* Checked that each key file equals the report key dictionary and that its
  selection rule excludes validation and test key selection.
* Checked both planted-control reports: 32 seeds, 32/32 exact recovery for
  each language, no search-time reference key, and matching oracle scores.
