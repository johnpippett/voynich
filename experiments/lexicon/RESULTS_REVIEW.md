# Lexicon pilot results review

Review date: 2026-09-16.

This review covers the six required files in `results/lexicon-pilot-v1` and
their six key files. It checks the frozen protocol in
`docs/plans/lexicon-feasibility-v1.md`. It does not fit a new key or change a
pilot setting.

## Checks

A separate read-only checker loaded the six report files and the current
source files. It recomputed the integer objective, all fit hits, all
validation and test hits, mapping counts, known-key control accuracy, and
ambiguity counts. It also checked the following items:

- Each report key hash matches its key file.
- Each reference source hash matches the local pinned source bytes.
- Each manuscript source, source-manifest, reference-manifest, and
  bifolio-manifest hash matches the report.
- Every reported code hash matches the current code byte-for-byte.
- The fit key in each key file matches the score proof and the reported
  objective.
- No report contains a fitted key mapping. Reference reports contain an
  oracle SHA-256 value only. Key files contain returned fit mappings.
  Manuscript reports contain no oracle or encryption record.

The checker returned zero mismatches for all six runs. A separate scalar
bound replay for the Latin reference control returned the same fit key,
objective, score proof, ambiguity count, and test accuracy. The only expected
difference is the bound-engine label.

## Fit results

`T` is the number of word types. `N` is the number of word tokens. The score
uses `count*T+N` and divides by `2*T*N`.

| run | fit T / N | fit token hits / type hits | score | normalized score | solver result |
| --- | ---: | ---: | ---: | ---: | --- |
| `latin-reference` | 1,820 / 19,969 | 19,477 / 1,468 | 64,762,632 | 0.890978 | certified; 341 nodes |
| `italian-reference` | 6,196 / 31,681 | 27,405 / 2,829 | 259,426,929 | 0.660807 | certified; 1,402 nodes |
| `latin-zl` | 3,727 / 14,523 | 945 / 22 | 3,841,521 | 0.035486 | budget exhausted |
| `latin-it` | 4,422 / 17,450 | 912 / 31 | 4,573,814 | 0.029637 | budget exhausted |
| `italian-zl` | 3,727 / 14,523 | 1,149 / 38 | 4,834,197 | 0.044656 | budget exhausted |
| `italian-it` | 4,422 / 17,450 | 1,731 / 36 | 8,282,682 | 0.053669 | budget exhausted |

The two reference controls have equal integer lower and upper bounds. All four
manuscript runs expanded 10,000 nodes and have `score_certified=false` and
`search_exhausted=false`.

The manuscript bounds below use the same normalization, rounded to six decimal places.
The public summary rounds intervals outward. The JSON integer bounds define the exact limits.

| run | normalized lower bound | normalized upper bound |
| --- | ---: | ---: |
| `latin-zl` | 0.035486 | 0.349603 |
| `latin-it` | 0.029637 | 0.344602 |
| `italian-zl` | 0.044656 | 0.355031 |
| `italian-it` | 0.053669 | 0.351796 |

These are finite branch bounds for the declared key domain and lexicon. They
are not estimates of a false-positive rate.

## Held-out checks

The table gives lexical hits as `token hits / type hits`. Mapping gives mapped
tokens and types out of the complete held-out partition.

| run | validation hits | test hits | test mapping |
| --- | ---: | ---: | ---: |
| `latin-zl` | 140 / 17 | 466 / 17 | 7,161 / 2,277 of 7,162 / 2,278 |
| `latin-it` | 147 / 16 | 352 / 28 | 8,271 / 2,637 of 8,272 / 2,638 |
| `italian-zl` | 173 / 18 | 525 / 25 | 7,161 / 2,277 of 7,162 / 2,278 |
| `italian-it` | 267 / 24 | 690 / 27 | 8,271 / 2,637 of 8,272 / 2,638 |

Each manuscript test partition has one unmapped token, one unmapped type, and
one unmapped symbol occurrence. The checker found no key repair or hidden
mapping for these positions.

The Latin reference control recovered 23 of 23 fitted ciphertext symbols and
had 100% exact character and word accuracy on 19,931 test words. Its test
lexical hits were 19,136 of 19,931 tokens and 1,439 of 1,928 types.

The Italian reference control recovered 21 of 24 fitted ciphertext symbols
and had 100% exact character and word accuracy on 31,152 test words. Its test
lexical hits were 26,261 of 31,152 tokens and 2,458 of 6,024 types. The three
unmatched fitted symbols do not occur in a positive hit. This gives 60 key
completions that preserve the current positive hits.

## Ambiguity

The count below is the number of injective key completions that preserve the
current positive fit hits. It is not an optimum-key count for an uncertified
manuscript run.

| run | symbols in positive hits | preserving completions | certified optimum lower bound |
| --- | ---: | ---: | ---: |
| `latin-reference` | 23 | 1 | 1 |
| `italian-reference` | 21 | 60 | 60 |
| `latin-zl` | 14 | 239,500,800 | not available |
| `latin-it` | 13 | 8,648,640 | not available |
| `italian-zl` | 12 | 43,589,145,600 | not available |
| `italian-it` | 12 | 121,080,960 | not available |

## Hash receipt

The six reports use one common code-hash map. The current files match these
values:

| file | SHA-256 |
| --- | --- |
| `experiments/lexicon/run_pilot.py` | `2eb25cdeb4fdf8ef167a3f10c2463b1ef61c23b1dd7e34a3aea9368c6edf69e5` |
| `experiments/lexicon/solver.py` | `d560df778f43615a36ffe43989e9c85cfab4c09263fab1f377f9fccc73592fd8` |
| `experiments/lexicon/ambiguity.py` | `297c8b318fcac6053bd26856b4393ec440b24d5eca1c9bf52f8e6d5f2d7825f2` |
| `experiments/lexicon/bitset_bound.py` | `4bd025e026dccfbaff7a7bc0dad61c6292ab7046b21620b14442df538fc31ef9` |
| `src/voynich/corpus.py` | `064c45794d523b5c07ea10621752e325d35709f619e0763ac6ba1561f0fa1dc2` |
| `src/voynich/reference.py` | `97e173c761b137d3653a827315b62a68af3e96abd189afdecc46e9759d2b94d9` |
| `src/voynich/groups.py` | `15b77e967ce296634a36a3deacba660c14a4d4615c99597949b5586d682bdef0` |

The pinned input hashes are:

- `data/reference_manifest.json`: `f261b781f150991e3305aae5057a94dc91afd8e59c58bb22ff199347f5ce3e6d`
- `data/source_manifest.json`: `77c9f755ed47c19ccfe3ef92b7699953d5d5e9ada729492662c94154d3d2f4f1`
- `data/bifolio_manifest.json`: `998cb3d6c8327ff0bdf786d52968fa3bec9f5fa9b05ba7ae56065fc9639fad72`
- `data/raw/ZL3b-n.txt`: `bf5b6d4ac1e3a51b1847a9c388318d609020441ccd56984c901c32b09beccafc`
- `data/raw/IT2a-n.txt`: `7f27a8b0feed8f6de0a99900df6bf912dd1d295c38e5f830bac8b41c3f536fb5`

The six reference corpus files also match the hashes recorded in
`data/reference_manifest.json`. Each key file hash matches its report:

| key file | SHA-256 |
| --- | --- |
| `latin-reference.keys.json` | `cc6dee2fdd900b16b3eace660763b86fbe03339bb71f66a6bb9d74ce2cadf846` |
| `italian-reference.keys.json` | `7c2b2452bb909066bc78c77028945c34c900312cab4db66be4694fe36e3f71a1` |
| `latin-zl.keys.json` | `cb7cd14bdfb6861e7fe1c55ee3d59fe9009e1550df2d25c2c029793621a31775` |
| `latin-it.keys.json` | `fc2a3d016cbf8e03b831b61207694773360f36af07a9a967b2c2c9280dd79ad4` |
| `italian-zl.keys.json` | `28056785b51419d32fc29277b3632ee34ffec7f63e9af885eb036dd7022996c7` |
| `italian-it.keys.json` | `ba3931e40a3001aeefabd1954b58200c5cca144d54f463495a98fefdbc969478` |

## Limits

The pilot uses one fixed injective substitution model and one fixed lexicon
for each reference corpus. It does not test other encodings, word repairs,
lemmas, semantics, history, or language identification. It does not estimate
false-positive rates. A lexical match is not a decipherment.

The two reference controls use synthetic seeded ciphertext. Their results
show that the final runner can recover test plaintext under the declared
finite controls. They do not show recovery of every fitted key assignment.
They do not validate a manuscript language hypothesis.
