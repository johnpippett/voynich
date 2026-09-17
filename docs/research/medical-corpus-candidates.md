# Medieval Latin medical corpus candidates

Access date for this note: 2026-09-17.

These records identify possible future comparison inputs. They do not identify
the language of the Voynich Manuscript (VMS). They also do not provide a
translation.

The records use three separate dates when the sources provide them:

- work date: the estimated date of composition;
- witness date: the date of the surviving manuscript or print;
- digital date: the date of the scan or catalogue record.

The Internet Archive (IA) files contain optical character recognition (OCR) output.
They are not manually verified digital transcripts. Audit their quality before corpus use.

## Ranked candidates

| Rank | Candidate | Proposed use | Decision |
| --- | --- | --- | --- |
| 1 | Hildegard, *Causae et curae* | Medical prose reference | No clean corpus; noisy-only after [OCR audit](causae-ocr-audit.md) |
| 2 | Arnaldus, *Regimen sanitatis ad regem Aragonum* | Manuscript-OCR stress case | Use only as a noisy sensitivity source until audited |
| 3 | *Regimen sanitatis Salernitanum* | Printed medical-poetry sensitivity source | Optional; weak work-date and attribution control |

## 1. Hildegard, *Causae et curae*

### Work record

The IRHT-CNRS FAMA record names Hildegard of Bingen (1098–1179). It gives a
work date of 1150–1160, prose form, and a natural-science encyclopedia genre:
[FAMA record](https://fama.irht.cnrs.fr/oeuvre/635540).

The BnF authority record calls the work a medical treatise in five books. It
also records the title *Liber compositae medicinae* and two manuscript
witnesses:
[BnF authority record](https://catalogue.bnf.fr/ark:/12148/cb12204627f).

The machine text comes from Paul Kaiser's 1903 Teubner edition. The National
Library of Medicine records 254 pages and Latin text:
[NLM catalogue record](https://www.ncbi.nlm.nih.gov/nlmcatalog/351993).

### Digital witness and access

The IA item is [bub_gb_hExUwWa8tNoC](https://archive.org/details/bub_gb_hExUwWa8tNoC).
The item metadata gives the 1903 edition, Latin language, and publisher. It
also gives a Public Domain Mark URL:
[IA metadata](https://archive.org/metadata/bub_gb_hExUwWa8tNoC) and
[Public Domain Mark](https://creativecommons.org/publicdomain/mark/1.0/).

The machine-readable files are:

- [OCR TXT](https://archive.org/download/bub_gb_hExUwWa8tNoC/bub_gb_hExUwWa8tNoC_djvu.txt), 625,942 bytes, MD5 `d3313abf256997675a97d542ce68b1b5`, SHA1 `71f59a5523a5f72140a452ee2060848d97241c69`.
- [OCR XML](https://archive.org/download/bub_gb_hExUwWa8tNoC/bub_gb_hExUwWa8tNoC_djvu.xml), 6,896,663 bytes, MD5 `eadde967fc69a7032ef20d8dd171bcfb`, SHA1 `5a66dc0e0083f807513231a09bc4b577178884a0`.

The provider metadata gives no word count. The project must compute a word
count after a fixed extraction procedure.

The Public Domain Mark is a provider statement for this IA item. The record
does not separately describe copyright in the OCR as a new derivative. Record
the item statement and the OCR file hash. Confirm the redistribution scope
before public bundling.

### Split and limits

The five books can provide blocked partitions for sensitivity checks.
They belong to one work and one author. They are not independent language samples.

The OCR is from a 1903 edited print. It can contain page headers, apparatus,
broken words, and recognition errors. The edition can also reflect editorial
spelling choices. Remove front matter and apparatus with a documented rule.
Keep the source pages for audit.

Retain this candidate for a future medical-prose sensitivity source.
The [OCR audit](causae-ocr-audit.md) rejects clean-corpus use. It supports
noisy-only use after page-aware extraction.

## 2. Arnaldus de Villanova, *Regimen sanitatis ad regem Aragonum*

### Work and witness record

The Universitat Autònoma de Barcelona Arnau DB dates the work to 1305–1308. It describes
a health regimen for Jaume II and includes advice on bathing, diet, exercise,
sleep, and other daily conditions:
[Arnau DB](https://webs.uab.cat/arnau/en/practica-2/).

Sciència.cat records Latin, prose form, health-regimen genre, complete work,
and estimated date c. 1305–1308. It also lists the Philadelphia witness:
[Sciència.cat record](https://www.sciencia.cat/db/presentacio.htm?obra=1946).

The Philadelphia catalogue describes the witness as a 14th-century or circa
1400 copy from Spain or southern France. It has 28 folios and rounded Gothic
script. The catalogue identifies two sections:

- *Regimen generale* or *Liber de conservatione sanitatis*, fols. 1r–26r;
- *Regimen speciale*, fols. 26r–28v.

See the [OPenn record](https://openn.library.upenn.edu/Data/0027/html/cpp_10a_210.html).

The witness date is not the work date. The IA metadata field `date=1300` is a
catalogue approximation. Use the institutional work and witness records above.

### Digital witness and access

The IA item is [cpp_10a_210](https://archive.org/details/cpp_10a_210). Its
[metadata](https://archive.org/metadata/cpp_10a_210) gives Public Domain rights
and the Public Domain Mark URL. OPenn states that the images and the content
are free of known copyright restrictions and in the public domain. It states
that the metadata is released under CC0:
[CC0](https://creativecommons.org/publicdomain/zero/1.0/).

The machine-readable files are:

- [OCR TXT](https://archive.org/download/cpp_10a_210/cpp_10a_210_djvu.txt), 73,596 bytes, MD5 `d35dc1ab44e6faa46e696c880cbdbecb`, SHA1 `b992bed88d2bd6ad7eb93e6faaa31d2af5f78381`.
- [OCR XML](https://archive.org/download/cpp_10a_210/cpp_10a_210_djvu.xml), 1,786,168 bytes, MD5 `b19e81a205c5d3c48bfe9e7771da498a`, SHA1 `a5764ecc1600e698d36ac8cdcf47a7c850cd579d`.

The provider records give no word count. The project must compute one after
extraction.

OPenn's rights statement covers the manuscript images and content. IA marks
its item as Public Domain. Neither record gives a separate copyright statement
for the IA OCR derivative. Keep the scan, OCR, and project-derived text as
separate provenance layers.

### Split and limits

The two catalogue sections support a blocked section split. Both sections are
parts of one work and one manuscript witness. They are not independent samples.

The OCR is a poor transcription of rounded Gothic script. It contains blank
lines, broken characters, and non-text catalogue material.
Use it only as an OCR stress case after a page-aware extraction audit.
It is not a clean Latin baseline. Record rejected forms and any
normalization of abbreviations or long-s characters.

## 3. *Regimen sanitatis Salernitanum*

### Work and witness record

The BnF authority record describes a Latin poem of hygiene and care. It gives
the Salernitan medical school as compiler, associates the text with Jean de
Milan, and marks attribution to Arnaldus de Villanova as contested:
[BnF authority record](https://catalogue.bnf.fr/ark:/12148/cb122933900).

The record places the main compilation in the second half of the 13th century.
It says that some precepts are older and that the text has many revisions. It
does not provide one secure composition date. Do not use the date of the later
print as the work date.

The Jagiellonian Digital Library holds the selected 1491 Strasbourg
incunabulum. Its record gives Latin language, Georg Husner as publisher, source
BJ St. Dr. Inc. 96, and digital identifier `NDIGSTDR049026`:
[Jagiellonian record](https://jbc.bj.uj.edu.pl/en/dlibra/publication/688538/edition/763108/regimen-sanitatis-salernitanum).

### Digital witness and access

The Jagiellonian record marks the digital object “Domena publiczna (public
domain).” The IA mirror also records that status, but it gives no license URL:
[IA item](https://archive.org/details/jbc.bj.uj.edu.pl.NDIGSTDR049026) and
[IA metadata](https://archive.org/metadata/jbc.bj.uj.edu.pl.NDIGSTDR049026).

The machine-readable files are:

- [OCR TXT](https://archive.org/download/jbc.bj.uj.edu.pl.NDIGSTDR049026/NDIGSTDR049026_djvu.txt), 325,998 bytes, MD5 `c5aa22114b48622b423ca6f90ce9b7c9`, SHA1 `94cc89a3298fc7004b6b589cfc75dbd5d3b67916`.
- [OCR XML](https://archive.org/download/jbc.bj.uj.edu.pl.NDIGSTDR049026/NDIGSTDR049026_djvu.xml), 3,802,812 bytes, MD5 `57653e74e35ebe9299849e4f1760b14d`, SHA1 `aa75cc417fda511cf6122e1101e9cd2211a89d67`.

The records give verse extent but no official word count. The OCR rights are
not stated separately from the digital object's public-domain status.

### Split and limits

The poem has one witness and a contested work history. Use explicit printed
sections after inspection. Do not treat arbitrary verse blocks as independent
works.

The 1491 print includes editorial and commentary layers. OCR can misread
long-s characters, abbreviations, and page layout. This source is a printed
poetry sensitivity control. It is not a clean prose reference and should not
be pooled with the first two candidates.

## Negative findings

- CELT's [*Regimen Sanitatis* record](https://celt.ucc.ie/published/L600009A/header.html)
  states restricted access and cites a copyright estate. It is not a public
  corpus input without permission.
- The reviewed [ALMA text-edition API](https://alma.hadw-bw.de/api/text-editions/fre-medicine)
  exposed a French Trotula edition, not a reusable Latin machine text. The
  [IA English translation record](https://archive.org/details/trotulaenglishtr0000unse)
  does not provide a Latin source or clear reuse terms.
- The reviewed [Hildegard *Physica* extract](https://medievalbestiary.bestiary.ca/etexts/etext113765.htm)
  provides page images, not a verified machine-readable text.
- [CREMMA-Medieval-LAT](https://github.com/HTR-United/CREMMA-Medieval-LAT)
  provides small medical manuscript samples, not a complete work corpus. Its
  [repository metadata](https://raw.githubusercontent.com/HTR-United/CREMMA-Medieval-LAT/main/htr-united.yml)
  and [Zenodo record](https://doi.org/10.5281/zenodo.7013436) require a license
  check before reuse.

## Integrity and use conditions

None of the IA items has a Git commit for the OCR. Pin the IA identifier, exact
filename, provider MD5 and SHA1, and a project-computed SHA-256 after fetch.

No full candidate was downloaded or added to the repository for this audit.
The existing CoNLL-U parser does not apply to these OCR files without a new,
documented extraction step. Keep that step separate from the current controls.
