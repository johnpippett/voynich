# Common visual-unit inventory

Date: 2026-09-30.
This inventory count supplies no sign values or manuscript reading.

## Question and method

Can every observed analysis unit have a different value in a 26-letter alphabet?
An injective map assigns different letters to different units.
More than 26 observed units make that complete assignment impossible.

The count uses the complete eligible cohort from the [raw-EVA pilot](../../reports/SPACEFREE_MANUSCRIPT_PILOT.md).
Its sources are the Zandbergen-Landini (ZL) and Takeshi Takahashi (IT) transcriptions.
The Extensible Voynich Alphabet (EVA) is a transcription system for written shapes. Its symbols need not represent linguistic letters.
The parser uses split uncertain spaces and the existing `ivtff-bifolio-metadata-v3` groups.
The first-match record categories remain non-paragraph, empty, excluded-token, interrupted, and eligible.
No eligible word or partition was removed for this count.

The unchanged [tokenizer](../../experiments/homophonic/units.py) selects the longest matching compound inside each accepted word.
Its compounds are `cth`, `ckh`, `cph`, `cfh`, `ch`, and `sh`.
Every other accepted code point remains a separate unit.
Compounds cannot cross a word boundary. Their spans reconstruct every normalized input word.
These are lowercase analysis labels. They do not keep every physical distinction in the source notation.

## Observed counts

| Source | Partition | Normalized EVA code points | Words | Units | Distinct labels |
| --- | --- | ---: | ---: | ---: | ---: |
| ZL | Train | 73,144 | 14,523 | 65,561 | 30 |
| ZL | Validation | 11,809 | 2,280 | 10,639 | 26 |
| ZL | Test | 36,122 | 7,162 | 32,458 | 28 |
| IT | Train | 89,225 | 17,450 | 79,919 | 26 |
| IT | Validation | 14,530 | 2,778 | 13,089 | 26 |
| IT | Test | 42,390 | 8,272 | 38,101 | 27 |

The ZL training count alone rules out a total injective 30-to-26 map under this representation.
The IT training count alone does not rule out that model. It does not prove that a key exists.
No key search followed this count.

## Source-defined common list

Smith and Ponzi give 23 common forms on page 2 of their [July 2018 preprint](https://agnosticvoynich.files.wordpress.com/2019/06/glyph-combinations-across-word-breaks-in-the-voynich-manuscript-preprint.pdf).
The final period is punctuation, not another unit.
Their list is an analysis convention, not a historical alphabet:

```text
o y a e ch sh k t f p ckh cth cfh cph d s r l i n m g q
```

The source PDF has SHA-256 `6bb5e9103da8da403d847fa7df979b64b23690dc71b13121788fe1b21aa3f6d2`.
The authors' Takahashi source omits the Rosettes. This does not show the same omission in this project's pinned sources.
A separate coverage question fixed this list before the coverage calculation.
The earlier manuscript and reference results were already known. This is not a blind study.

| Source | Partition | Units outside the list | All units | Common-unit coverage |
| --- | --- | ---: | ---: | ---: |
| ZL | Train | 129 | 65,561 | 99.8032% |
| ZL | Validation | 10 | 10,639 | 99.9060% |
| ZL | Test | 47 | 32,458 | 99.8552% |
| IT | Train | 158 | 79,919 | 99.8023% |
| IT | Validation | 14 | 13,089 | 99.8930% |
| IT | Test | 70 | 38,101 | 99.8163% |

All 23 common units occur in both training partitions.
The common unit `g` is absent from ZL validation. No common unit is absent from the other five partitions.
Every outside unit stays in the denominator. Coverage is not reading accuracy.

## Verification and limits

The six normalized stream hashes match the earlier published cohort.
The [aggregate record](visual-unit-inventory-2026-09-30.json) gives counts, label sets, ordered-unit hashes, and source hashes.
It excludes source text and frequency tables.
The original source files, private input records, and calculation receipts remain in ignored storage.

A separate scanner reproduced all six inventories and common-list coverage counts.
It did not import the first probe or the tokenizer.
It reused the earlier audited normalized streams, word lengths, and partition assignments.
Thus, this calculation does not independently verify the original parser or cohort selection.
The private coverage result sorts the common labels. Its membership agrees with the ordered source list above.

The counts concern an analysis representation, not a complete catalogue of physical signs.
They do not identify Latin, a cipher family, phonemes, or meanings.
A partial-map experiment needs separate fixed scoring, unknown-position rules, controls, and acceptance conditions.
