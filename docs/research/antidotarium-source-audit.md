# Antidotarium Nicolai source audit

Audit date: 2026-09-17

Scope: provenance, date, genre, access, license, and corpus partition for the
*Antidotarium Nicolai* text in Averyanov's Paper I replication package. I read
the relevant archive files as text. I did not run package code, run a model, or
publish source text or images.

## Decision

This source is a **conditional go** for historical provenance and genre
registration. It is a **no-go** as a clean Latin control corpus in its released
text form. Use it only after a new extraction identifies the Latin passages,
records page and edition boundaries, and resolves the rights for that edition.

The source is a useful additional medical comparator because it belongs to the
medieval pharmacy and recipe tradition. This is a provenance decision. It does
not select a corpus by fit and does not change the Celsus plan.

| Check | Status | Reason |
| --- | --- | --- |
| Record and receipt | GO | Zenodo gives a version, size, and checksum. |
| Historical identity and genre | GO | DBNL identifies the edition, Latin print source, and medical genre. |
| Released text as Latin-only data | NO-GO | The file is flattened PDF text with mixed editorial and language material. |
| Rights for reuse or redistribution | CONDITIONAL | Package and source terms do not give one clear reuse grant. |

## Record and receipt

Zenodo record 21761192 identifies Paper I as version `v1`, published on
2026-08-02, under `CC BY-NC-ND-4.0`. Its API lists
`voynich_replication_v1.zip` at 2,270,408 bytes with MD5
`da9f4521ffdbb049ac2c1a1e6ae858aa`.
[Zenodo record API](https://zenodo.org/api/records/21761192) ·
[Zenodo DOI](https://doi.org/10.5281/zenodo.21761192)

The private download matched that size and MD5. Its SHA-256 is
`c01f3a8e064e709464711b6d1b3254d2c41f9fdf9205c2681b8573b655e6eada`.
[Archive endpoint](https://zenodo.org/api/records/21761192/files/voynich_replication_v1.zip/content)

Relevant archive paths are `replication/README.md`,
`replication/analysis/test_antidotarium.py`,
`replication/analysis/test_antidotarium.md`, and
`replication/data/research/corpora/antidotarium_nicolai_latin_vandenberg1917.txt`.

The corpus file is 166,477 bytes, with archive CRC `99784493` and SHA-256
`004d23b8057cbcca4af3e22c92fa1a07841bb6b6accdc2123ef17a46b3fb1ef6`.
The ZIP entry gives `2026-07-09 04:20`; its date fields do not state a
timezone. The file has four comment lines and one flattened text line. Its
body has 152,495 ASCII letters, matching the paper's rounded 152,000-letter
description. These are integrity checks, not manuscript or language tests.

## Edition and genre

**DBNL colophon evidence.** DBNL identifies *Antidotarium Nicolaï (Ms.
15624-15641, Kon. Bibl. te Brussel)* as a W.S. van den Berg edition printed in
Leiden in 1917. DBNL describes its digital text as a diplomatic representation
of that edition and names a Leiden University Library copy, shelf mark 1065 D
39. Its title record classifies the work as prose and non-fiction, with artes
literature and medicine as subgenres. DBNL also notes that the book places
Middle Dutch and Latin on facing pages, while the digital order alternates
them. [DBNL colophon](https://www.dbnl.org/tekst/_ant004wsva01_01/colofon.php) ·
[DBNL title record](https://www.dbnl.org/tekst/_ant004wsva01_01/)

**Van den Berg introduction evidence.** The introduction places the Latin
*Antidotarium* of Nicolaus Salernitanus at about 1100 and in the first decades
of the twelfth century. The 1917 volume prints the Middle Dutch translation
from Brussels MS 15626, whose copy ends with `anno domini 1351`, beside the
oldest Latin printed edition, from Venice in 1471. The replication file is a
2026 derived text based on the 1917 edition. It is not a direct Latin
manuscript transcription. [DBNL introduction](https://www.dbnl.org/tekst/_ant004wsva01_01/_ant004wsva01_01_0002.php)

## Corpus partition

The corpus header cites DBNL PDF identifier `_ant004wsva01_01`, says that the
PDF text layer has no spaces inside words, and describes page selection with
Latin markers such as `recipe`, `valet`, and `contra` against Dutch markers.
The stored file still contains front matter, page and folio markers, editorial
notes, Dutch material, and OCR joins. It has no page, column, or language-span
boundaries. The archive contains no source PDF, page-selection manifest, or
item-level license statement.

The package test script reads the whole file with `[a-z]+`, changes `w` to
`uu`, `j` to `i`, and `k` to `c`, keeps a fixed alphabet, and creates random
one- or two-letter units. This produces derived normalized data. It does not
prove that the input is a Latin-only historical source. The shipped result is
an analysis output, which this audit did not reproduce.

The layers are therefore:

* **Historical source:** the Latin 1471 printed text represented in the 1917
  edition.
* **Translated layer:** the Middle Dutch translation from Brussels MS 15626.
* **Released derived data:** flattened PDF text plus the script's normalized
  and randomly segmented stream.

## Access and rights

The Zenodo license covers the deposited package. Its README calls the
plaintext corpora public domain, but it gives no separate rights record for
this file. See `replication/README.md` in the [replication
archive](https://zenodo.org/api/records/21761192/files/voynich_replication_v1.zip/content).

DBNL marks the 1917 work **possibly protected**. Its terms allow private
download and printing, short quotation with attribution, and linking. Other
reuse or republication requires a rights investigation and, when rights
remain, permission. DBNL also states that its collection has database-right
limits for large-scale downloads. [DBNL work-specific
terms](https://www.dbnl.org/titels/gebruiksvoorwaarden.php?id=_ant004wsva01) ·
[DBNL general terms](https://www.dbnl.org/overdbnl/copyright.php)

The age of the medieval work and 1471 print does not by itself settle rights
in the 1917 scholarly edition, its transcription, or the DBNL text layer.
Treat the current corpus as private research material. Do not redistribute it,
add it to a public corpus, or publish derived text until the edition and
extraction rights are documented.

## Next action

Keep this record as a conditional candidate for a medieval medical reference.
For a usable control corpus, make a rights-cleared extraction of only the
Latin 1471 text in the 1917 edition. Record page ranges, edition layer,
abbreviation and spelling treatment, and a reproducible source receipt. Keep
the Middle Dutch translation, editorial apparatus, and OCR material separate.
Do not choose this corpus because it improves a model fit.
