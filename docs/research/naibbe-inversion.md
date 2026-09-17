# Naibbe inversion review

Review date: 2026-09-16.

Scope: the primary Naibbe article, its open supplement, the published source
repository, and a small fixed-table inversion check. This note assesses
inversion feasibility. It does not claim a decipherment of MS 408.

## Result

Naibbe is reversible when the table file, plaintext normalization, token
boundaries, respacing rule, and table-selection state are known. The published
artifacts do not provide those values for MS 408. A VMS inversion must therefore
enumerate latent token states and table choices. It will return candidate
strings, not a unique plaintext.
Ambiguous plaintext is candidate enumeration, not recovery. Unique recovery
needs the full table, normalization, token boundaries, respacing rule, deck
state, and a mapping that resolves one candidate.

The current table file gives this compatibility result under an exhaustive
token parser:

| input | accepted tokens | parseable tokens | parseable types | ambiguous tokens |
| --- | ---: | ---: | ---: | ---: |
| ZL3b | 37,889 | 29,683 (78.34%) | 2,871/7,678 (37.39%) | 14,619 (38.58%) |
| IT2a | 37,759 | 29,795 (78.91%) | 2,972/8,026 (37.03%) | 14,733 (39.02%) |

These counts use the repository's basic EVA token parser and the published CSV.
The CSV was populated from common Voynich B affixes. The result is therefore a
VMS-fitted compatibility check. It is not independent evidence that MS 408 used
Naibbe.

## Exact forward rule

The article describes the following procedure ([Greshko, 2025](https://doi.org/10.1080/01611194.2025.2566408), sections 2.1–2.5).

1. Remove case, Arabic numerals, diacritics, punctuation, and original spaces.
2. Split the remaining letters into one-letter and two-letter plaintext units.
   The simplified die rule gives probabilities (1/2) and (1/2). The standard
   two-dice rule gives (17/36) unigrams and (19/36) bigrams. The last letter
   is always a unigram when it is left over.
3. For each table `t` in `{alpha, beta1, beta2, beta3, gamma1, gamma2}`, store
   three strings for each letter: `U_t(x)`, `P_t(x)`, and `S_t(x)`.
4. Draw a table for each letter from a shuffled deck. A unigram `x` emits
   `U_t(x)`. A bigram `xy` draws two tables and emits
   `P_t1(x) + S_t2(y)`.
5. Discard cards after each draw. Shuffle a new deck when the current deck is
   empty.

The paper gives approximate table probabilities (5:2:2:2:1:1). The source
code makes the variants concrete. The 52-card variant uses weights

```text
alpha 20, beta1 8, beta2 8, beta3 8, gamma1 4, gamma2 4
```

The 78-card variant uses

```text
alpha 28, beta1 14, beta2 11, beta3 11, gamma1 7, gamma2 7
```

The latter is an approximation to the paper's ratio, not the same exact
probabilities. `naibbe.py` defaults to 52 cards. `naibbe_v2.py` defaults to 78
cards. The Zenodo workbook also defaults to 78 cards. These are separate
reproducibility choices.

The source implementation adds details that the article leaves as choices:

* `clean_line` maps J to I, K to C, and W to UU after removing diacritics. It
  also expands several ligatures. The CSV has 414 rows, or three states for six
  tables and 23 letters. It has no J, K, or W rows.
* The Python implementation uses a Bernoulli draw with `RESPACING=17` for the
  standard rule and `RESPACING=18` for the simplified rule.
* The main script calls the encoder once per input line. Each call creates a new
  shuffled deck. It does not record a random seed.
* `SPACE_REMOVAL_RATE=0.03` can join adjacent emitted tokens in the output.
  This is an output operation, not part of the reversible table mapping.

The original `naibbe.py` option `UNAMBIGUOUS=True` rejects a bigram only when
its concatenation equals a known unigram string. It does not reject collisions
between two different bigram decompositions. An exhaustive CSV check finds 99
non-unigram strings with multiple distinct bigram readings, covering 202
decompositions. `naibbe_v2.py` adds a full bigram catalog and a 10,000-attempt
limit. If that limit is reached, it emits the last attempt. A strict encoder
must fail or record the ambiguity at that point.

## Exact reverse rule and its limits

For a token `w`, a complete fixed-table candidate set is

```text
R(w) = { x : U_t(x) = w for some t }
       union { xy : P_t(x) + S_r(y) = w for some t,r }
```

The split point must range over every character boundary. The paper's slot
grammar can help find the boundary, but exhaustive table matching is the safer
operation when the table file is known.

The published `decrypt_naibbe.py` is a display decoder. In its default
`BASIC=True` mode, it returns a unigram as soon as one matches. It hides all
valid bigram readings for that token. Its reverse maps also overwrite duplicate
glyph keys. The current duplicate unigram entry is the same plaintext letter,
but this behavior is unsafe for a new table file. Its compound mode tests only
two-token splits after a space was omitted. It does not perform full line-level
segmentation.

An inverse for VMS must retain every member of `R(w)`, plus a no-parse state.
It must also retain merged-token segmentations when spaces are uncertain. A
language model can rank these candidates. Its first-ranked candidate is not a
cryptographic recovery.

The following issues affect any inverse implementation:

| priority | issue | required control |
| --- | --- | --- |
| P1 | The original encoder allows 99 multi-reading bigram strings. | Use the full catalog and fail when the retry limit is reached. |
| P1 | The default decoder hides valid readings when a unigram matches. | Store all token candidates before ranking. |
| P1 | The paper, `naibbe.py`, `naibbe_v2.py`, and the workbook use different defaults. | Pin the commit, CSV hash, deck, respacing, seed, space rule, and reset rule. |
| P2 | Normalization merges J/I, K/C, W/UU, and other forms. | Score only the normalized alphabet and report each equivalence. |
| P2 | The table file uses VMS B data. | Separate table fitting from held-out VMS scoring. |

## Identifiability

The forward process hides several independent variables:

* The unigram or bigram state is hidden when a string belongs to both classes.
* The table or ordered table pair is hidden after encryption.
* The shuffled deck order and the deck reset point are hidden. VMS line
  boundaries do not prove the encoder's reset points.
* The table strings were selected and rank-matched using Voynich B data. Fitting
  those strings to the same VMS tokens being scored creates circular evidence.
* Normalization loses case, punctuation, spaces, diacritics, and distinctions
  such as J/I, K/C, and W/UU.
* A 3% space-removal rule creates unknown token joins. The article also allows
  intuitive or deterministic respacing, so the segmentation is not fixed by
  the paper alone.
* Latin and Italian are demonstrated source languages. The VMS plaintext
  language, if any, is unknown.

These variables permit many plaintext candidate sequences. A fitted language
score can select a candidate from this set even when the table model is false.
The score must therefore be evaluated on held-out folios and against synthetic
and non-Naibbe controls.

## Smallest implementable inverse test

Use two bounded tests.

First, freeze one known forward instance. Pin the GitHub commit and the CSV
hash `4e7cfd54b7ec66515d39a51e11ec97e8e19b643b0b189124eebc3982e707dcec`,
52-card weights, `RESPACING=17`, zero space removal, `UNAMBIGUOUS=True`, and
seed 0. Encrypt normalized `armavirumquecano` with a standard-library harness.
The independent check produced these plaintext units and tokens:

```text
units: ar ma v i ru m qu e ca no
tokens: aleeor aiiinaiin shor qokedy qopcheo sain ofeeol lchedy lchaiin opchor
candidate counts: 1 1 2 2 1 2 1 2 1 1
```

The known unit is in the complete candidate set for all ten tokens. Four tokens
remain ambiguous. This test checks implementation and candidate preservation.

Second, run a VMS compatibility test without fitting table strings:

1. Freeze the CSV and a predeclared finite family: 52 or 78 cards, standard or
   simplified respacing, line-local or continuous deck state, and zero or 3%
   space removal.
2. For each accepted VMS token, enumerate `R(w)`. Preserve every reading,
   every merged-space split, and every no-parse token.
3. Report token and type coverage, candidate count, no-parse rate, and coverage
   by folio, hand, and transcription. Keep ZL3b and IT2a as separate inputs.
4. Train any Latin or Italian ranking model on external text only. Score held-out
   VMS folios. Compare with known plaintext encrypted by the same frozen
   procedure and with non-Naibbe generators.

A pass means that a fixed Naibbe family is compatible with the held-out token
and language statistics. It does not identify the VMS key, plaintext language,
or meaning. A useful failure is also possible: low held-out coverage, high
ambiguity, or no advantage over controls would reject this fixed family.

The repository now contains a fixed-table oracle at
`src/voynich/naibbe.py`. It validates the pinned CSV, keeps every candidate's
state and table choices, and exposes separate plaintext and latent-choice
ambiguity. `scripts/check_naibbe_compatibility.py` prints source hashes and
aggregate counts only. It performs no table fitting or language ranking. The
source pins and licences are recorded in
`data/naibbe_source_manifest.json`. The focused test file
`tests/test_naibbe.py` reports six passing tests in this review.

## Source and access record

Primary sources:

* [Greshko, *The Naibbe cipher*](https://doi.org/10.1080/01611194.2025.2566408).
* [Open supplementary record](https://doi.org/10.6084/m9.figshare.30730162),
  CC BY 4.0. The downloaded PDF SHA-256 is
  `210bb31729b64b29d0e1112c5b414d29625ca540581baee2d67456a5dd5c071f`.
* [Published source repository](https://github.com/greshko/naibbe-cipher),
  checked at commit
  [`f2675ec5dd275268bc64dd48ea64fc0e0e9827a2`](https://github.com/greshko/naibbe-cipher/tree/f2675ec5dd275268bc64dd48ea64fc0e0e9827a2).
  The repository contains `naibbe.py`, `naibbe_v2.py`,
  `decrypt_naibbe.py`, and `references/naibbe_tables.csv`.
* [Zenodo supplementary record](https://doi.org/10.5281/zenodo.16415087),
  which provides the original Excel implementation and datasets. Its metadata
  declares CC BY 4.0. The GitHub README describes a modified MIT condition,
  while the top-level `LICENSE` file contains standard MIT text. Preserve the
  copyright notice and article citation, and check each file before reuse. The
  downloaded `Naibbe Cipher.xlsx` SHA-256 is
  `890835df665d33b96228d4a587030fee2bc1637783dc627b4e6aa584186cadcd`.

Direct publisher HTML and PDF requests returned HTTP 403 during this review.
The article citation above remains the primary reference. The exact rules were
checked against the accessible article text, the open supplement, the source
code, and the workbook metadata. The local article text capture is not a
redistributable article copy.

The VMS counts above use `data/raw/ZL3b-n.txt` and `data/raw/IT2a-n.txt` from
the repository source manifest. Those source files have no stated open licence
on their source page. Keep their attribution and obtain permission before
redistribution.
