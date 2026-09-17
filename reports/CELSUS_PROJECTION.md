# Celsus projection result

The frozen Celsus projection completed with `PASS`.
The two independent traversals produced the same 550 paragraph records.
This result validates a fixed extraction procedure.
It does not identify the language of the Voynich manuscript.

The source is an ancient Latin medical edition of Celsus.
It is a control for extraction work.
Its date, genre, and editorial history differ from the Voynich manuscript.
The result does not provide a translation or a decipherment.

## Source and freeze

The source file has 893,899 bytes and SHA-256 `a4a5194ba38a7efd5192d20f2a7b696f4fa64105010eb629aa7c35255a935145`.
The source uses commit `ae0fe427f56d7652efc3090af74a2663a4cbed60` in the [canonical-latinLit repository](https://github.com/PerseusDL/canonical-latinLit).
The source is available as the [pinned TEI source](https://raw.githubusercontent.com/PerseusDL/canonical-latinLit/ae0fe427f56d7652efc3090af74a2663a4cbed60/data/phi0836/phi002/phi0836.phi002.perseus-lat5.xml).
The source audit revision is `f26874c`.
The audit receipt SHA-256 is `aebba00a41c120e4101d94c67f4783e9de55106051d158f3ccd41246d960e6de`.
See the [source audit](celsus-source-audit.json) for edition and rights evidence.

The frozen code commit is `c1753fc1f71836f50ff7c6946d722dead07441a9`.
It was published before the first projection. CI passed before 2026-09-17T09:59:43.718620Z.
See the [CI run](https://github.com/johnpippett/voynich/actions/runs/35207958885).
The freeze manifest SHA-256 is `5c48648f0098f1d303ddfc5309aa42d58899cd44b2b118a7cc55811f266f5631`.
The [frozen protocol](../docs/plans/celsus-projection-v1.md) defines the source rules and stop conditions.

The [initial receipt](celsus-projection-v1/initial-receipt.json) is a byte-exact copy of the pending run receipt.
The [acceptance receipt](celsus-projection-v1/acceptance.json) records the final review result.
The two receipts stay separate.

## Structure

The source has 8 books, 211 chapters, and 550 paragraphs.
The run includes one Latin edition wrapper.
It has no empty source paragraphs.

| Book | Chapters | Paragraphs |
| ---: | ---: | ---: |
| 1 | 11 | 28 |
| 2 | 34 | 45 |
| 3 | 27 | 45 |
| 4 | 32 | 35 |
| 5 | 29 | 204 |
| 6 | 19 | 80 |
| 7 | 34 | 74 |
| 8 | 25 | 39 |

The paragraph counts use direct chapter paragraph order.
The public receipts publish counts and hashes.
They do not publish paragraph text or individual review entries.

## Projection

The run uses `empty_policy=include`.
It emits 550 records across 211 chapters.
It emits 0 empty records and drops 0 empty records.
The module and independent files have the same bytes and SHA-256.

| Output | Records | Bytes | SHA-256 |
| --- | ---: | ---: | --- |
| Module traversal | 550 | 747,194 | `f37d99f5ad0771c32c4d71934b58df00438ca7dadf870f89dc93b181c1d373f2` |
| Independent traversal | 550 | 747,194 | `f37d99f5ad0771c32c4d71934b58df00438ca7dadf870f89dc93b181c1d373f2` |

The pending initial receipt has SHA-256 `f9333cdac5f45742f23ffb76b8600421635296fa1b855ab54412f3b94300be91`.
The fixed review checklist has SHA-256 `32bdec1422e4b80d25139b275b3810bff2f5ffb2818e2c628bebb5f886402aca`.
The private review context has SHA-256 `1e5186bcbac24ae86e52aae46dbc249732473752fdeb73908003b8e697ee44f5`.
The public receipts publish these hashes without the review context text.

The projector keeps `corr` content and excludes `sic`, `head`, `note`, `del`, `figure`, and `foreign` content.
It keeps the tail of each excluded root at the parent level.
It treats `pb` and `milestone` as transparent.
It collapses XML whitespace after traversal.
The independent traversal applies the same fixed rules.

The following counters have separate scopes.
Selected subtree counts include nodes that an ancestor can later exclude.
Actual retained counts record the final traversal.
Direct excluded counts record roots excluded at their parent.
Ancestor excluded counts record nodes below an excluded ancestor.
These scopes must not be subtracted as one table.

| Scope | Choice | Corr | Hi | Milestone | Paragraph | Page break | Sic | Del | Foreign | Note |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Selected subtree | 446 | 446 | 525 | 1804 | 550 | 308 | 446 | 7 | 276 | 626 |
| Actual retained | 446 | 446 | 20 | 1800 | 550 | 307 | — | — | — | — |
| Direct excluded roots | — | — | — | — | — | — | 446 | 7 | 268 | 625 |

Ancestor exclusion counts by tag are `figure=4`, `foreign=8`, `head=4`, `hi=505`, `milestone=4`, `note=1`, and `pb=1`.
The eight nested foreign nodes are below notes.
The direct foreign count is 268.

## Fixed review records

The review artifacts cover 30 fixed locations.
Each location checks 8 features.
All overall statuses are `PASS`.
No feature has `FAIL` (0 failures).

| Feature | PASS | FEATURE_NOT_PRESENT | FAIL |
| --- | ---: | ---: | ---: |
| `location_fields` | 30 | 0 | 0 |
| `source_spelling` | 30 | 0 | 0 |
| `xml_whitespace` | 30 | 0 | 0 |
| `choice_correction` | 20 | 10 | 0 |
| `excluded_content` | 24 | 6 | 0 |
| `tails` | 30 | 0 | 0 |
| `transparent_markers` | 30 | 0 | 0 |
| `empty_status` | 10 | 20 | 0 |

All three review files identify the method as AI-assisted manual source inspection.
These records are not human or external validation.
The report makes no human-review claim.

A batch 2 addendum corrected four tail presence labels after full subtree checks.
The addendum changed no projection rule.
The final `tails` row records 30 `PASS` values and zero `FEATURE_NOT_PRESENT` values.
The original batch 2 report remains unchanged.

The `empty_status` counts preserve the reviewer convention.
Batch 1 and batch 3 mark non-empty entries `FEATURE_NOT_PRESENT`.
Batch 2 marks the same non-empty include-policy check `PASS`.
The aggregate keeps both values.

The addendum found parent-order tails after transparent markers and choices in the four affected records.
The builder checks the addendum hash, locations, source subtree tail nodes, and unchanged projection files.

## Replay

The replay exited with status 0.
It reproduced the five frozen result files byte for byte.
The replay used detached commit `c1753fc1f71836f50ff7c6946d722dead07441a9`.
The original replay receipt has SHA-256 `13c1daf30d9cb95cf4ea8131d9eb88fe683002ab392a7d5a3c0309a190eb0e63`.
The public replay receipt omits process resource fields.
See [replay verification](celsus-projection-v1/replay-verification.json) (SHA-256 `4d5325bd7d650e84cc5cceb2b4640c40065d1e69d4f28d80dc41fdfbfbccb45d`).

## Limits

This run validates a source projection and an independent comparison.
It does not test a Voynich transcription, a cipher key, or a translation.
The Celsus text is an ancient medical control.
It cannot remove date, genre, edition, or orthography differences between corpora.

The 30 fixed review records do not inspect all 550 paragraphs.
AI-assisted inspection does not replace independent human review.
The public result publishes no raw source or paragraph context.

## Rebuild

Run the builder from the repository root:

```text
python scripts/build_celsus_projection_summary.py
```
The builder checks all pinned inputs before it writes an output.
An identical existing output is accepted.
A changed existing output stops the build.
The automated projection is publicly reproducible from the frozen source and code.
The manual review artifacts are private and cannot be derived by this command.
The builder requires the retained review files.
Their hashes identify the reviewed evidence.
The acceptance receipt hash is `8067be5cb874a8e53472d11e3188be0eb92b7c30c3def9f31de2451e06fc6faf`.
