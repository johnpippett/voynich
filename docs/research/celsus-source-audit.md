# Celsus source audit

Source review date: 2026-09-17.

This note audits a pinned machine-readable Text Encoding Initiative (TEI)
edition of Aulus Cornelius Celsus, *De Medicina*. TEI uses Extensible Markup
Language (XML). The note does not identify the language of the Voynich
Manuscript (VMS). It does not provide a translation.

## Decision

Use this source as a separate ancient medical-prose baseline after a fixed TEI
projection passes the checks below. The audit found book IDs `1` through `8` in
well-formed XML. It has clear book and chapter structure. It has a declared
editorial layer. This audit did not collate the file against the print edition.

This is a conditional go for a controlled baseline. It is not a replacement
for a medieval Latin corpus. The DLL author record places Celsus in the first
century BCE to the first century CE:
[DLL author record](https://catalog.digitallatin.org/dll-author/a5349).

## Pinned source and rights record

The source is in the PerseusDL `canonical-latinLit` repository. The `master`
branch resolved to commit
[`ae0fe427f56d7652efc3090af74a2663a4cbed60`](https://github.com/PerseusDL/canonical-latinLit/commit/ae0fe427f56d7652efc3090af74a2663a4cbed60)
on 2026-09-17. The commit was created on 2026-09-16.

The exact source file is
[`phi0836.phi002.perseus-lat5.xml`](https://raw.githubusercontent.com/PerseusDL/canonical-latinLit/ae0fe427f56d7652efc3090af74a2663a4cbed60/data/phi0836/phi002/phi0836.phi002.perseus-lat5.xml).
The CTS work metadata is
[`__cts__.xml`](https://raw.githubusercontent.com/PerseusDL/canonical-latinLit/ae0fe427f56d7652efc3090af74a2663a4cbed60/data/phi0836/phi002/__cts__.xml).

The repository [README](https://raw.githubusercontent.com/PerseusDL/canonical-latinLit/ae0fe427f56d7652efc3090af74a2663a4cbed60/README.md)
states that repository contents use CC BY-SA 4.0 unless another status is
given. It also asks users to offer Perseus any modifications. The repository
stores the [CC BY-SA 4.0 license text](https://raw.githubusercontent.com/PerseusDL/canonical-latinLit/ae0fe427f56d7652efc3090af74a2663a4cbed60/license.md).

The TEI header has no `<availability>`, `<licence>`, or `<rights>` element.
The repository statement is therefore the current digital license evidence.
The README also warns that components can have different rights. Check for a
file-specific exception before public redistribution. The 1891 print date is
not the rights basis.

The public audit script is
[`scripts/audit_celsus_source.py`](../../scripts/audit_celsus_source.py). It
downloads the pinned XML, CTS metadata, README, and license into the ignored
`results/celsus-source-audit/` directory. It refuses a changed existing file.
It verifies a download before it writes the file. It checks the expected byte
count, Git blob SHA-1, and SHA-256 before it parses the XML. A Git blob SHA-1
includes the `blob <byte-count>\0` prefix.

| File | Bytes | Git blob SHA-1 | SHA-256 |
| --- | ---: | --- | --- |
| `phi0836.phi002.perseus-lat5.xml` | 893,899 | `dead5082d1d181fd8e43dceeed4793f79213831c` | `a4a5194ba38a7efd5192d20f2a7b696f4fa64105010eb629aa7c35255a935145` |
| `__cts__.xml` | 1,694 | `8490f544b0edee9edef9f24e1d9785e9eba6727d` | `497674650e7a74c9f42257a144583b955c8a8989b958abf7e72b9d51efa5aa1a` |
| `README.md` | 2,334 | `dc327f44bde676e16bb63cd223afa922d00045b5` | `7ea684aea5b084c38fc919da2adf0df8339490243a43bf744fb8e27384d82623` |
| `license.md` | 18,625 | `033217724f8631eeb12987b30d76e8a62f275ceb` | `ccf0e8ce183761bf82700126cc45a4e907b2cede024e65e3fef5c2338b9b7063` |

Run the public audit from the repository root with:

```text
python scripts/audit_celsus_source.py
```

The default output directory is ignored. Use `--output-dir` to select another
ignored directory. The script also writes `public-receipt.json` to that
directory. The receipt records the fixed source review date `2026-09-17`.
It does not record the execution clock. The script exits with an error if any
aggregate check fails.
The public receipt is
[`reports/celsus-source-audit.json`](../../reports/celsus-source-audit.json).
It contains evidence URLs, hashes, aggregate checks, and no source text or
local user path. The audit uses only the Python standard library. It does not
create a corpus projection. It does not run a model.

## Bibliographic record and extent

The CTS work is `urn:cts:latinLit:phi0836.phi002`. The edition is
`urn:cts:latinLit:phi0836.phi002.perseus-lat5`.

The TEI header records:

- title: *De Medicina*;
- author: Celsus;
- editor: Charles Victor Daremberg;
- source edition: *A. Cornelii Celsi De medicina libri octo*;
- publisher: Teubner, Leipzig;
- print date: 1891;
- Perseus release date: 2009-10-07.

[Scaife](https://atlas.perseus.tufts.edu/library/urn%3Acts%3AlatinLit%3Aphi0836.phi002.perseus-lat5/)
confirms these bibliographic fields and the eight-book title. The [Digital
Latin Library record](https://catalog.digitallatin.org/dll-work/w2724) maps the
work to `W2724`, `phi0836.002`, and the same CTS URN.

The parser found book IDs `1` through `8`. It found 211 chapter divisions.
Chapter IDs repeat across books. The composite key `book_id:chapter_id` is
unique. The body has 550 paragraph elements. No body paragraph has an `xml:id`
or `n` identifier. These counts do not prove complete collation against the
print edition.

## XML audit

The XML is well formed. The audit found no parse error. It did not validate the
TEI schema.

The source-wide body audit contains:

- 8 books, with IDs `1` through `8`;
- 211 chapters, distributed as `11, 34, 27, 32, 29, 19, 34, 25`;
- 550 paragraphs;
- 446 `<choice>` elements;
- 276 `<foreign>` elements, all with `xml:lang="grc"`;
- 628 `<note>` elements;
- 10 `<del>` elements;
- no `<add>` elements;
- 217 `<head>` elements;
- 1,807 `<milestone>` elements;
- 361 `<pb>` elements;
- 5 `<figure>` elements;
- 525 `<hi>` elements.

All 446 choice elements use the same direct-child pattern:
`<sic>` followed by `<corr>`. No `orig`, `reg`, `abbr`, or `expan` choice
pattern occurs. The full TEI document has one `xml:id`, with no duplicate
`xml:id` value. The body has no duplicate composite chapter key. It has no
empty paragraph.

The audit found empty leaves for 1,807 milestones, 361 page breaks, and 14
foreign elements. These are structural or editorial cases. They are not
tokens.

The proposed projection selects only paragraphs inside a book and a chapter.
All 550 body paragraphs meet this rule. All 8 books and all 211 chapters have
at least one selected paragraph. The source-wide and selected counts differ
for some markup:

| Markup | Source-wide body count | Count inside selected paragraphs | Outside selected paragraphs |
| --- | ---: | ---: | ---: |
| `<choice>` | 446 | 446 | 0 |
| `<foreign>` | 276 | 276 | 0 |
| `<note>` | 628 | 626 | 2 |
| `<del>` | 10 | 7 | 3 |
| `<head>` | 217 | 4 | 213 |
| `<pb>` | 361 | 308 | 53 |
| `<milestone>` | 1,807 | 1,804 | 3 |
| `<figure>` | 5 | 4 | 1 |
| `<hi>` | 525 | 525 | 0 |

The public receipt records both views. Do not compare a projected count with a
source-wide count without stating the scope.

These counts are before projection. The selected column counts every node in a
selected paragraph subtree. It does not count retained text.

The receipt also records ancestor-exclusion diagnostics. The excluded ancestor
tags are `head`, `note`, `del`, `figure`, `foreign`, and `sic`. A child with
one of these ancestors is covered by the parent exclusion.

| Node | Selected subtree total | With excluded ancestor | Without excluded ancestor |
| --- | ---: | ---: | ---: |
| `<choice>` | 446 | 0 | 446 |
| `<foreign>` | 276 | 8 (`note`) | 268 |
| `<hi>` | 525 | 505 (`note`: 503; `note>note`: 2) | 20 |

The selected subtree has these direct drop candidates: `note` 625, `del` 7,
`foreign` 268, `pb` 307, `milestone` 1,800, and `sic` 446. `figure` and
`head` have zero direct candidates because their selected nodes have excluded
ancestors. The retained element candidates are `choice` 446, `corr` 446, and
`hi` 20. These are traversal diagnostics. They are not final token counts.
Do not treat all 276 foreign nodes as direct drops or all 525 highlight nodes
as retained nodes.

Representative syntax includes:

```xml
<choice><sic>...</sic><corr>...</corr></choice>
<foreign xml:lang="grc">...</foreign>
<del>...</del>
```

The private audit output stores the complete tag and attribute counts. The
public note reports only counts. It does not publish source-text arrays.

## Proposed deterministic TEI projection

This projection is proposed. It is not implemented in the current audit.

1. Read only `text/body`.
2. Keep the `book` and `chapter` divisions.
3. Store a composite source key as `book_id:chapter_id`.
4. Use each body `<p>` as one source paragraph.
5. Traverse mixed XML content in document order.
6. For each `<choice>`, keep `<corr>` and exclude `<sic>`.
7. Fail when a choice lacks exactly one `sic` and one `corr` child.
8. Exclude `<head>`, `<note>`, `<pb>`, `<milestone>`, `<figure>`, and `<del>`.
9. Exclude `<foreign xml:lang="grc">`.
10. Fail if a foreign element uses a language other than `grc`, or an unsupported editorial tag occurs.
11. Reject `<add>` elements.
12. Keep text inside `<hi>` and discard its formatting attribute.
13. Collapse XML whitespace only. Keep the source spelling in this layer.
14. Do not change `u/v`, `i/j`, ligatures, or word boundaries.
15. Record every exclusion count beside the derived text.

The mixed-content audit uses the parent text or the immediate previous sibling
tail before each element. It uses the element tail after it. It does not
simulate removal of adjacent excluded siblings. The scan found no selected
case where an excluded element had a Latin letter on both sides with no source
whitespace. This scan cannot prove that final retained text has no joins.
A future parser must check the final retained prefix and tail.

Use this fail-closed spacing rule:

- Keep the selected correction text in place. Then keep its tail text.
- Exclude foreign, note, and deleted content. Then keep each element tail.
- Do not add a space around a page break or milestone.
- If an exclusion creates adjacent Latin letters without source whitespace,
  stop and record the case. Do not insert a guessed space.
- Collapse whitespace only after mixed-content traversal completes.

The receipt records boundary classes for `choice`, `foreign`, `note`, `del`,
`pb`, and `milestone`. It records source-wide and selected counts for each
class. The boundary classes are a scan result, not a proof about projected
word joins.

The preprojection validation must reproduce book IDs `1` through `8`, 211
chapters, 550 selected paragraphs, 446 choice nodes, and 276 Greek foreign
nodes in selected paragraph subtrees. It must also show zero unknown choices,
zero empty paragraphs, zero duplicate composite chapter keys, and all 8 books
plus all 211 chapters with prose. Here, “all 8 books” means book IDs `1`
through `8`; it does not mean complete collation against print. Keep the raw
XML and the projected text as separate provenance layers. Check traversal
counters after the projection rules run. Do not require the raw foreign or
highlight totals as direct drop or retained totals.

## Limits

The source is an edited classical Latin medical work. It is not a medieval
Latin sample. Its apparatus, Greek quotations, headings, and medical terms can
change character and word statistics. A model score can show similarity to
this separate control. It cannot identify the VMS language.

The source is suitable for a separate ancient medical-prose control after the
projection is fixed and checked. Use one predeclared corrected-text policy.
Run a raw-versus-corrected sensitivity comparison only as a separate study.
