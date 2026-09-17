# Voynich substitution runner review

Review date: 2026-09-16.

This review covers `scripts/run_voynich_substitution.py` and its current
inputs. It checks split use, key selection, shuffle controls, missing symbols,
score labels, source verification, reference partitions, and code hashes.

I ran a smoke execution for `latin_llct` with the ZL source, one restart, and
zero search iterations. It completed and wrote a report. The pre-parse source
hash matched `data/source_manifest.json`. The report contained reference file
hashes, the reference manifest hash, the group configuration, and module code
hashes.

## Checks that passed

The runner fits both keys on `sample['train']`. It writes the key record before
it scores any split. It does not use validation or test scores for key
selection. The search call receives no reference or planted key.

The unit null shuffles each raw string character within each accepted token.
It preserves token length and the raw character multiset. It does not shuffle
grouped units. The report correctly calls this `within_word_shuffle` and
states that the run uses raw EVA units.

The key domain comes from the manuscript training partition. A source unit
that appears only in validation or test remains unmapped. `score_heldout`
reports its unknown occurrence count, missing type count, and key coverage.
The lexical check marks an unmapped output with `?`.

The reference loader fits the language model from the selected language's
reference `train` words. It verifies the pinned reference files and reports
the document split and duplicate exclusions. The two reference partitions
remain separate. The Old Italian metadata records that its partitions are
canticles from one work.

The 32-key random test baseline is a comparison set. It is not a false
positive estimate. The report states this limit.

## Finding: train scores are labelled as held-out

Severity: minor reporting defect.

The runner calls `score_heldout` for `train`, `validation`, and `test`
(`scripts/run_voynich_substitution.py:104-110`). That helper sets
`evaluation_split` to `"heldout"`. The smoke report therefore labels the
training score as held out:

```text
scores.train.observed.evaluation_split == "heldout"
```

The numerical scores and key selection are still correct. The label can cause
a reader to treat the training score as an independent result. Use the direct
scorer for the training split, or set the field to the actual split name after
scoring. Keep `heldout` only for validation and test scores when the same
helper is used.

## Finding: the sample filter drops complete tokens without reporting them

Severity: material sample-definition issue for a public report.

The loop skips a complete paragraph record when any token in that record is
excluded (`scripts/run_voynich_substitution.py:54-58`). It also skips every
paragraph record that contains `<->` or `<~>`. This removes accepted tokens
from the affected record. It does not only remove the uncertain token.

An independent count for the ZL source found 37,889 accepted parser tokens.
The runner retained 23,965 words. It dropped 6,279 accepted words from loci
with excluded words and 3,945 accepted words from diagram-interrupted loci.
It also excludes non-paragraph records. These rules may be intentional, but
the report does not record them or their counts. A reader cannot reconstruct
the eligible sample from `sample_words` alone.

Record the exact parser mode and filter, including record counts, accepted
tokens, excluded tokens, and diagram interruptions by split. Then either keep
the complete-record rule as a declared conservative rule or retain accepted
tokens from an incomplete record under a separate declared analysis. Do not
interpret the resulting split as a full accepted-token sample without this
ledger.

## Finding: run provenance omits manifest and shuffle settings

Severity: minor reproducibility gap.

The source hash gate is correct, but the report records only the resulting
source digest. It does not record the hash or selected entry from
`data/source_manifest.json`. The `code_sha256` map also omits that input
manifest. A changed manifest could therefore bless a different source without
appearing in the run record.

The report also records the search seed but not the shuffle operation and its
three seeds. The current code uses seeds 408, 409, and 410 for train,
validation, and test, in dictionary insertion order. Record these values,
`uncertain_spaces="split"`, the raw-character unitization, and the preserved
multiset and length rules. Include the source-manifest digest or selected
manifest entry in the run record.

These gaps do not invalidate the smoke execution. They make an output less
self-describing than the source and grouping hashes suggest.

The run remains exploratory. It uses a train-only key and fixed reference
model, but it has one unit-shuffle control and a 32-key comparison set. Those
controls do not estimate a false-positive rate or establish a Voynich reading.

## Correction verification

Review date: 2026-09-16.

The reviewed runner patch resolves the three reporting findings above.

* Each score now names its actual split. The four reviewed reports label the
  score groups `train`, `validation`, and `test` correctly.
* The report now records sequential filter categories and counts for records,
  accepted words, and excluded tokens. It declares the complete-locus rule.
* The report now records the source-manifest SHA-256 digest, parser mode,
  filter policy, raw-character shuffle, preserved properties, and partition
  seeds 408, 409, and 410.

The old and reviewed reports were compared for `latin-zl` and `italian-zl`.
The reviewed outputs also include `latin-it` and `italian-it`. Every available
old and reviewed pair has the same observed and shuffled keys, key-record hash,
search records, random-key baseline, sample counts, and numerical score fields.
Only the split labels and the new metadata changed. The four reviewed reports
therefore preserve the calibrated search results while correcting their
provenance and labels.

No remaining runner reporting finding is known from this scoped review. The
results remain exploratory and do not support a decipherment claim.
