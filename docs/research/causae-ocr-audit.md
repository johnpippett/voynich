# *Causae et curae* OCR audit

Access date: 2026-09-17.

This audit covers the 1903 Paul Kaiser edition of Hildegard's *Causae et
curae*. It does not identify the language of the Voynich Manuscript (VMS).

## Decision

The OCR is machine-readable, but it is not a clean corpus input.
Use it only as a noisy sensitivity source until a manual audit or second transcription comparison confirms its text quality.

The sampled printed pages were legible. The OCR has frequent character errors.
The edition also contains editorial corrections and additions.
Do not treat this OCR as a clean reference corpus.

## Source and rights record

The IRHT-CNRS FAMA record gives Hildegard of Bingen (1098–1179), a work date
of 1150–1160, prose form, and a natural-science encyclopedia genre:
[FAMA](https://fama.irht.cnrs.fr/oeuvre/635540).

The BnF record calls the work a medical treatise in five books. It lists two
manuscript witnesses and the alternate title *Liber compositae medicinae*:
[BnF](https://catalogue.bnf.fr/ark:/12148/cb12204627f).

The National Library of Medicine records the 1903 Leipzig Teubner edition as
Latin text with 254 pages:
[NLM](https://www.ncbi.nlm.nih.gov/nlmcatalog/351993).

The IA item is [bub_gb_hExUwWa8tNoC](https://archive.org/details/bub_gb_hExUwWa8tNoC).
The direct JSON record is
[IA metadata](https://archive.org/metadata/bub_gb_hExUwWa8tNoC).

The JSON record verifies these fields:

- identifier: `bub_gb_hExUwWa8tNoC`;
- title: `Hildegardis Causae et curae`;
- date: `1903`;
- language: `lat`;
- publisher: `Lipsiae, In aedibus B.G. Teubneri`;
- `licenseurl`: `http://creativecommons.org/publicdomain/mark/1.0/`.

The JSON `rights` field is empty. The Public Domain Mark is the provider's
rights statement for the IA item. The record does not state separate rights
for IA's OCR as a new derivative. Keep this scope limitation in any reuse
record.

The audit fetched only OCR files and six small page JPEGs. It did not fetch the
full PDF, the full image set, or a ZIP archive.

## Pinned OCR files

The private audit script is `results/medical-source-audit/audit_causae.py`.
It writes only inside the ignored `results/medical-source-audit/` directory.
The script checks the existing file before reuse. It fails on a hash mismatch.

| File | Direct URL | Bytes | MD5 | SHA1 | SHA-256 |
| --- | --- | ---: | --- | --- | --- |
| OCR TXT | [download](https://archive.org/download/bub_gb_hExUwWa8tNoC/bub_gb_hExUwWa8tNoC_djvu.txt) | 625,942 | `d3313abf256997675a97d542ce68b1b5` | `71f59a5523a5f72140a452ee2060848d97241c69` | `f3ee9bd8bed8196e05379a6f6065a2bf912e3d9c6fc911546b647867f66588da` |
| OCR XML | [download](https://archive.org/download/bub_gb_hExUwWa8tNoC/bub_gb_hExUwWa8tNoC_djvu.xml) | 6,896,663 | `eadde967fc69a7032ef20d8dd171bcfb` | `5a66dc0e0083f807513231a09bc4b577178884a0` | `b5228adb2f4acde80bc938917f0f0fd454baef86c28a30a54ac3fc073d86eead` |

The checksums match the IA metadata API. The SHA-256 values come from this
audit fetch.

## XML structure

The XML has 267 `OBJECT` page nodes. All 267 objects have a `PARAM` node with
a stable DjVu page name. OCR text appears below this path:

```text
OBJECT/HIDDENTEXT/PAGECOLUMN/REGION/PARAGRAPH/LINE/WORD
```

Each `WORD` node has `coords` and an `x-confidence` value. The confidence value
is a provider metric. It is not a calibrated word-accuracy estimate.

The raw XML has these counts:

| Part | XML objects | Raw `WORD` nodes | Mean confidence | Median confidence | Below 50 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Front matter | 0–7 (8) | 965 | 26.52 | 21 | 85.91% |
| Body | 8–252 (245) | 81,000 | 29.95 | 24 | 81.20% |
| Indexes | 253–263 (11) | 3,445 | 30.02 | 26 | 81.31% |
| End matter | 264–266 (3) | 91 | 21.11 | 14 | 91.21% |

These are OCR node counts. They are not validated word counts.

## Page and book boundaries

The following ranges are provisional. They use OCR headings and sampled page images.
Validate each boundary before corpus extraction.

| Part | Proposed XML object range | Raw `WORD` nodes |
| --- | ---: | ---: |
| Book I | 8–43 | 11,981 |
| Book II | 44–173 | 43,004 |
| Book III | 174–193 | 6,587 |
| Book IV | 194–229 | 11,734 |
| Book V | 230–252 | 7,694 |

Use object 8 as the body start. It contains the printed title and the start of
Book I. Objects 0–7 contain the title pages, library material, preface, and
editorial apparatus. Objects 253–263 contain indexes. Objects 264–266 contain
scan and borrower material.

The private `inspect_causae.py` script records this structure in
`structure_report.json`. It also records page-image hashes.

## Fixed image spotcheck

The audit used five fixed pages: objects 5, 8, 44, 174, and 230. It read the
first 20 non-empty XML `WORD` nodes from each page. Some nodes are headers,
page numbers, or preface text. They are not a random representative sample.

The audit compared those nodes with the visible print in the matching IA
BookReader JPEGs. It ignored case and terminal punctuation. It did not join
line-break hyphens.

Manual notes recorded 74 apparent matches among 100 checked positions. This is
not a reproducible corpus-accuracy estimate. The private script stores no
per-token annotations or ground-truth transcription for these 100 positions.
A separate AI-agent visual check covered 40 positions.
Object 8 matched 18 of 20, and object 44 matched 16 of 20.

| Object | Page role | Apparent matches noted in 20 |
| ---: | --- | ---: |
| 5 | Editor preface | 8 |
| 8 | Book I start | 18 |
| 44 | Book II body | 16 |
| 174 | Book III start | 16 |
| 230 | Book V body | 16 |

The visual notes show letter substitutions, false character shapes, and a
line-break word split. The preface page has the worst noted result. The body
pages also show repeated errors. Treat the 74/100 value as a bounded spotcheck,
not as a measured OCR error rate.

The six page images are private audit inputs. Their URLs and SHA-256 values are
in `results/medical-source-audit/structure_report.json`:

- [object 5](https://archive.org/download/bub_gb_hExUwWa8tNoC/page/n5_w1600.jpg): `bef6fc3c16d48f249ccc0d9ba69e46970b50ecef6311ae96de1a898d1bce66ce`;
- [object 8](https://archive.org/download/bub_gb_hExUwWa8tNoC/page/n8_w1600.jpg): `5febe23f0ca84420ffd6f7deb7dabf81ca8f911139ee960b53a4c7c41f45276c`;
- [object 44](https://archive.org/download/bub_gb_hExUwWa8tNoC/page/n44_w1600.jpg): `637193dbd8415ba40b6e66b4d6d0a49c8552a95b1458457b062b9a992f7a85db`;
- [object 174](https://archive.org/download/bub_gb_hExUwWa8tNoC/page/n174_w1600.jpg): `20c58f16bd3714760f01c31d35cc3012e1ee730a180671510d7ff6a3453be10f`;
- [object 230](https://archive.org/download/bub_gb_hExUwWa8tNoC/page/n230_w1600.jpg): `cb1f8e55dde6d476dc8ff6a5396cdac6ba9db5c0fc6252f6f3d96f3ecec2ea9a`;
- [object 253](https://archive.org/download/bub_gb_hExUwWa8tNoC/page/n253_w1600.jpg): `4605a0aee34c0cedf1106f856cea08f6e7538fe963b928448319944ee44d5b86`.

Object 253 was fetched separately to inspect the two-column index layout.
It was not one of the five spotcheck pages. It is excluded from the proposed body range.

## Proposed page-aware extraction

Keep the raw OCR and each derived text with its object index. Apply these steps
only in a future extraction review:

1. Select objects 8–252.
2. Keep words in XML column, region, paragraph, line, and word order.
3. Add an object boundary before each selected page.
4. Split the body into the five book ranges above.
5. Remove recurring running headers and printed page numbers from the top coordinate band.
6. Remove the repeated `ed. Kaiser.` footer and the `Digitized by Google` watermark.
7. Remove footnote lines and index material by page-aware rules.
8. Preserve editorial brackets, crosses, asterisks, and angle brackets as flags.
9. Do not silently apply the editor's corrections or additions.
10. Do not join line-break hyphens without image review.
11. Record every removed line, rejected form, and page identifier.

The sample pages use 2500 × 3513 pixel coordinates. Running headers and page
numbers occur near the low y-coordinate band. The digitization watermark occurs
near the high y-coordinate band. These coordinates can support an initial filter.
Full extraction still needs page review.

## Corpus go/no-go

The source is **no-go for a clean reference corpus**. The source is **usable
only as a noisy OCR sensitivity source** after page-aware extraction.

The source has one edited edition and one authorial work. Its five books can
provide blocked parts. They cannot provide independent language samples.

Do not use a score from this OCR as evidence for a VMS language or translation.
