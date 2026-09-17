# Naibbe code review

Review date: 2026-09-16.

This review covers these files and the pinned local inputs:

* `src/voynich/naibbe.py`
* `tests/test_naibbe.py`
* `scripts/check_naibbe_compatibility.py`
* `data/naibbe_source_manifest.json`
* `docs/research/naibbe-inversion.md`
* `data/raw/naibbe/naibbe-cipher/references/naibbe_tables.csv`
* `data/raw/ZL3b-n.txt` and `data/raw/IT2a-n.txt`

The review did not change the implementation, tests, script, manifest, or
other reports. It did not publish data or contact a source provider. It did not
review a line-level inverse, a language model, or table fitting.

The protocol boundary is fixed. This is a fitted feasibility cipher check. It
is not a decipherment. It does not identify a key, a language, or a plaintext.

## Result

No correctness defect was found in the token-level inverse or in the pinned
token compatibility counts.

One scope limit remains. The forward API returns a tuple of emitted tokens. It
does not simulate the source program's output space-removal rate. The API
documents this behavior. The script's `--uncertain-spaces join` option changes
VMS input parsing. It does not simulate forward output joins. A line-level
forward reproduction must add and pin a seeded output-join stage.

## Inverse coverage

The CSV has 414 rows: three states, six tables, and 23 letters. The independent
check rebuilt the reverse index from the CSV and compared it with
`TableBook.candidates()` for every emitted token type.

* The table has 137 distinct unigram glyph strings and 18,935 bigram strings.
* Their union has 18,947 emitted token types.
* Every expected `DecodeCandidate` was present, and no extra candidate was
  present.
* Every candidate retained its plaintext, state, ordered table choices, and
  character split. `by_plaintext()` retained the same candidate cardinality.
* There are 99 non-unigram strings with more than one bigram decomposition.
  Those decompositions total 202. For example, the table-derived token
  `alyl` has two complete readings.

The ambiguity fields use separate meanings. `plaintexts` is the set of unique
plaintext strings. `candidate_count` counts full readings, including state,
table choices, and split. `latent_table_choice_ambiguity` groups table choices
within each plaintext. The aggregate counts token occurrences for fields named
`*_token_count`. It counts types for fields named `*_type_count`.

The aggregate does not expose plaintext-ambiguity and latent-choice ambiguity
counts by type. This limits reporting detail. It does not change the existing
token counts.

## Pinned compatibility counts

The table hash is
`4e7cfd54b7ec66515d39a51e11ec97e8e19b643b0b189124eebc3982e707dcec`.
The table hash in the manifest and the file hash are equal. The focused test
run passed all six tests, including the published table shape test.

The compatibility script checked all records, including records with excluded
tokens. It kept the ZL3b and IT2a sources separate.

| source | spacing | tokens | types | parseable tokens | parseable types | no-parse tokens | ambiguous tokens | latent-choice tokens |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| ZL3b | split | 37,889 | 7,678 | 29,683 (78.34%) | 2,871 (37.39%) | 8,206 | 14,619 | 321 |
| IT2a | split | 37,759 | 8,026 | 29,795 (78.91%) | 2,972 (37.03%) | 7,964 | 14,733 | 318 |
| ZL3b | join | 35,146 | 8,723 | 26,369 (75.03%) | 2,839 (32.55%) | 8,777 | 13,193 | 276 |
| IT2a | join | 37,759 | 8,026 | 29,795 (78.91%) | 2,972 (37.03%) | 7,964 | 14,733 | 318 |

The split run has maximum candidate count 4. Its mean candidate count is
1.2273 for ZL3b and 1.2387 for IT2a. The source hashes and excluded-token
counts match `data/naibbe_source_manifest.json`.

## Forward checks

The default deck has 52 cards. The alternate weights define a 78-card deck.
The implementation creates a weighted list, shuffles it with the seeded random
source, consumes cards in order, and shuffles a new deck when it is empty.
An independent synthetic check used a six-card deck. It consumed all six cards
before the next deck cycle and retained two choices for each bigram.

Respacing uses the same seeded random source before deck creation. The returned
units concatenate to the normalized input. The final character is always a
unigram. A custom collision table confirmed that a retry limit raises an error
when no acceptable reading exists. It does not emit an unchecked last attempt.

The forward model removes input spaces before respacing. It returns separate
tokens and does not remove spaces between those output tokens. This is the
space-join scope limit stated above.

## Fail-closed behavior

`load_table_csv()` checks the expected SHA-256 value before parsing. It rejects
wrong headers, missing values, duplicate codes, unknown states, unknown tables,
unknown letters, empty glyphs, spaced glyphs, missing rows, and extra rows.

`encrypt_fixed()` rejects letters outside the table alphabet. A Greek letter
and a raw symbol were rejected in independent checks. The documented J/I,
K/C, and W/UU normalization remains an explicit equivalence. An unknown VMS
token returns an explicit `no_parse` result. It is not treated as a plaintext
candidate.

## Source and licence record

The manifest pins the source repository at commit
`f2675ec5dd275268bc64dd48ea64fc0e0e9827a2` and records the table hash. The
local source repository, article text capture, supplement PDF, and Zenodo
workbook all match the hashes in the manifest.

The manifest records CC BY 4.0 for the open supplement and Zenodo record. It
records the source repository's modified MIT condition and the standard MIT
text in its top-level licence file. It requires the article citation and
copyright notice to remain with reused material. The VMS source page states no
open licence. The manifest does not assert an open licence for those files.

The compatibility script emits hashes and aggregate counts. It does not emit
the VMS token list. The implementation does not fit table entries or rank
plaintext candidates.

## Checks run

* `PYTHONPATH=src python -m unittest -v tests/test_naibbe.py` — 6 tests passed.
* Independent reverse enumeration over all 18,947 table-derived token types —
  exact match.
* Independent collision check — 99 multi-reading non-unigram strings and 202
  decompositions.
* Independent finite-deck, respacing, retry-limit, and unknown-symbol checks —
  passed.
* `scripts/check_naibbe_compatibility.py` with `split` and `join` spacing —
  completed for ZL3b and IT2a.
