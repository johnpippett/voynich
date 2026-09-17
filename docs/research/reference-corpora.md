# Reference corpora

This project uses two pinned Universal Dependencies (UD) treebanks as
historical language references. They support tests of ordinary substitution
models against the Voynich Manuscript (VMS). They do not identify the VMS
language.

The source release is UD 2.18. The access date is 2026-09-16. The full source
metadata and SHA-256 values are in
[`data/reference_manifest.json`](../../data/reference_manifest.json).

## Selected sources

### Latin LLCT

[UD Latin LLCT](https://universaldependencies.org/treebanks/la_llct/index.html)
contains the LLCT2 treebank. It has 521 early medieval Latin charters from
Tuscany. The charters date from AD 774 to 897. The provider classifies the
genre as legal and documentary. The provider also describes the language as a
non-standard Latin variety.

The pinned repository is
[UD_Latin-LLCT at commit `df63d06c`](https://github.com/UniversalDependencies/UD_Latin-LLCT/tree/df63d06c5a7788b457f50bf37526146e9225c27d).
The `r2.18` tag points to this commit. The provider page and the pinned
`LICENSE.txt` state CC BY-SA 4.0. The manifest stores both files and their
hashes.

The source README states that the UD release omits 223 sentences from the
original LLCT2 corpus. The missing sentences require further conversion work.
The manifest records this limit.

### Italian-Old

[UD Italian-Old](https://universaldependencies.org/treebanks/it_old/index.html)
contains Dante Alighieri's *Comedy*. The work was composed approximately from
1306 to 1321. The treebank uses the 1994 Petrocchi edition. The provider
classifies the text as Florentine Old Italian poetry.

The pinned repository is
[UD_Italian-Old at commit `2c1361d6`](https://github.com/UniversalDependencies/UD_Italian-Old/tree/2c1361d621dafa7c465da0947f73765caaf743af).
The `r2.18` tag points to this commit. The provider page and the pinned
`LICENSE.txt` state CC BY-SA 4.0. The provider page says that the annotation
remains under revision. The commit fixes the input for this project.

This treebank is one work by one author. It is not a broad sample of Old
Italian. Its poetry, Florentine variety, and edited spelling can affect model
scores.

## Why these sources are limited

The VMS date, genre, language, and token rules remain uncertain. The selected
corpora have known dates and genres. They are comparison baselines only.

LLCT is legal charter prose. Italian-Old is one literary poem. Their dates and
genres do not match an unknown VMS source by default. A score against either
corpus cannot establish a source language.

The two sources also have different editorial histories. LLCT uses a modern
conversion of annotated charter text. Italian-Old uses an edited Dante text.
The VMS glyph stream has no agreed word or sentence segmentation. Do not treat
the extracted spaces as evidence for a VMS word boundary.

[UD Latin UDante](https://universaldependencies.org/treebanks/la_udante/index.html)
was reviewed as a third candidate. Its current provider page and README state
CC BY-NC-SA 3.0. Its pinned `LICENSE.txt` states CC BY-SA 4.0. The mismatch is
unresolved in the source release. It is not included here.

The UD licensing guidance says that users must read the `LICENSE.txt` file of
each treebank. It also warns that an underlying text can have separate rights.
See the [UD licensing guidance](https://universaldependencies.org/contributing/licensing.html).
Check the source terms before redistributing fetched text or derived data.

## Fetch and extraction

Run the fetcher from the repository root:

```text
python scripts/fetch_reference_sources.py
```

The fetcher downloads only into `data/raw/reference/`. That directory is
ignored by Git. It downloads the three CoNLL-U splits, `README.md`, and
`LICENSE.txt` for each corpus.

The fetcher checks every source SHA-256 value before it accepts a file. It
fails when an existing file has a different value. It does not replace a
changed file silently. It writes downloaded and extracted files by an atomic
temporary-file step.

The fetcher combines splits in this order:

1. `train`
2. `dev`
3. `test`

It writes these derived files:

```text
data/raw/reference/latin_llct/latin_llct.txt
data/raw/reference/italian_old/italian_old.txt
```

The derived text uses this fixed rule:

1. Ignore CoNLL-U comment lines.
2. Keep a multiword-token surface `FORM` when it contains a Unicode letter or
   number.
3. Skip all integer component rows covered by a retained multiword-token
   range.
4. Skip empty-node IDs with a decimal point.
5. Skip integer rows with `UPOS=PUNCT`.
6. Keep the `FORM` value of other integer rows.
7. Write one non-empty sentence per line.
8. Join forms with one ASCII space.
9. Write UTF-8 text with LF line endings.

The output keeps source Unicode. The fetcher does not apply case folding,
transliteration, or ASCII filtering.

The current analysis parser applies this separate normalization:

1. Apply Unicode NFKD.
2. Apply casefolding.
3. Remove combining marks.
4. Keep the complete form only when it matches `[a-z]+`.
5. Reject the complete form when it contains an apostrophe, hyphen, digit, or
   unsupported ligature.

The parser does not split a rejected form. It reports rejected forms in its
statistics. Keep this policy fixed when you compare a reference with the VMS.

The manifest records counts for each exclusion. For LLCT, the output has
9,023 sentences and 207,126 tokens. For Italian-Old, it has 3,419 sentences
and 101,670 tokens. These counts refer to the extraction rule above.

The current parser reads raw CoNLL-U input. It returns a sentence list with
`id`, `document`, `reference`, and `words` fields. It also returns extraction statistics and
the normalization name. The `words` field contains normalized ASCII forms.
The runner uses raw CoNLL-U input. The derived text files support archival
inspection only.

LLCT stores its charter key in a `# reference` comment. For example,
`document_id='36:1047'-span='1'` identifies one sentence in one charter.
Italian-Old stores the work and sentence key in `# sent_id`. For example,
`OldItalian_Dante_Inferno-1` identifies one sentence in *Inferno*.
The raw files remain the source for these IDs and all rejected surface forms.

The manifest identifies these split files:

```text
data/raw/reference/latin_llct/la_llct-ud-train.conllu
data/raw/reference/latin_llct/la_llct-ud-dev.conllu
data/raw/reference/latin_llct/la_llct-ud-test.conllu
data/raw/reference/italian_old/it_old-ud-train.conllu
data/raw/reference/italian_old/it_old-ud-dev.conllu
data/raw/reference/italian_old/it_old-ud-test.conllu
```

## Current model partitions

Keep the upstream split labels for source traceability. Do not treat those
labels as independent documents.

The LLCT source partitions contain disjoint charter sets: 422 training, 48 validation, and 51 test charters.
The analysis preserves those assignments and rejects a charter that crosses partitions.
Italian source partitions share all three canticles.
The analysis recombines them: *Inferno* trains the model, *Purgatorio* supplies calibration text, and *Paradiso* supplies test text.
All three canticles belong to one work by one author. This limits the Italian control.

The analysis removes a sentence from a later partition if its normalized words duplicate an earlier partition.
It preserves repetitions within a partition. Near duplicates can remain.
This removes 132 Latin validation sentences and 129 Latin test sentences.
No Italian sentences are removed by this rule.

Use the raw CoNLL-U files when a model needs lemmas, part-of-speech tags, or
source sentence identifiers. Use the derived text files when a model needs
only ordered surface forms and sentence boundaries.

Compare the same token policy across the VMS stream and every reference. Test
permuted controls and unrelated historical controls when possible. Report
tokenization, normalization, held-out split, and exclusion counts with every
score. A model that matches a statistical property has reproduced that
property. It has not decoded the VMS.
