# Celsus projection v1

Status: proposed validation-only protocol. No pinned-source projection has run.

Version: 1.0.

Source review date: 2026-09-17.

This protocol checks one fixed Text Encoding Initiative (TEI) projection of
one Celsus source. TEI uses Extensible Markup Language (XML). The protocol
does not identify the Voynich Manuscript (VMS) language. It does not fit a
model. It does not produce a translation.

## Fixed evidence

Use the public Celsus source audit at repository revision `f26874c`.

| Item | Fixed value |
| --- | --- |
| Source repository | `https://github.com/PerseusDL/canonical-latinLit` |
| Source commit | `ae0fe427f56d7652efc3090af74a2663a4cbed60` |
| TEI source URL | `https://raw.githubusercontent.com/PerseusDL/canonical-latinLit/ae0fe427f56d7652efc3090af74a2663a4cbed60/data/phi0836/phi002/phi0836.phi002.perseus-lat5.xml` |
| Source bytes | `893899` |
| Source SHA-256 | `a4a5194ba38a7efd5192d20f2a7b696f4fa64105010eb629aa7c35255a935145` |
| Audit note | [`docs/research/celsus-source-audit.md`](../research/celsus-source-audit.md) |
| Audit receipt | [`reports/celsus-source-audit.json`](../../reports/celsus-source-audit.json) |
| Audit receipt SHA-256 | `aebba00a41c120e4101d94c67f4783e9de55106051d158f3ccd41246d960e6de` |

The audit receipt is part of the fixed input record. Verify its source URL,
source commit, source byte count, and source SHA-256 before the projection.
Keep the XML bytes unchanged. Do not fetch `master` again during the run.

The source is a classical Latin medical work. The Digital Latin Library dates
Celsus to the first century BCE to the first century CE. The source header
records the 1891 Daremberg and Teubner edition and the 2009 Perseus release.
This is an ancient medical control. It is not a medieval Latin corpus.

The repository states CC BY-SA 4.0 unless another status applies. The TEI
header has no file-level rights element. Check the repository README for an
exception before redistribution. This protocol acquires the source for local
validation. It does not authorize redistribution of the XML or its paragraphs.

## Gate before the run

Review and publish this protocol and its implementation before the first pinned-source projection.
Do not run the source projector while a rule, sample location, or output field
is open to change.

The external manifest `experiments/medical/freeze-v1.json` must record exact SHA-256 values for these five files:

- this protocol;
- `experiments/medical/tei_projection.py`;
- `experiments/medical/run_projection.py`;
- `experiments/medical/test_tei_projection.py`;
- `experiments/medical/test_run_projection.py`.

Create the manifest after review. Publish it with the code before the run.
The runner must verify the exact path set and each hash before projection.
Its receipt records the manifest hash. The public commit binds the manifest to the reviewed implementation.
A missing manifest or changed file stops the run.


First review `experiments/medical/tei_projection.py` and its synthetic tests.
Apply any independent review fixes before the source run. The synthetic tests
do not prove behavior on the pinned Celsus file. A fix after the source run
requires a new protocol version and a new validation record.

Do not change a rule after reading a projected paragraph. Do not select a rule
because it increases regularity, word counts, or any later model score.

## Input and private output

Fetch the pinned XML into an ignored directory such as
`results/celsus-projection-v1/`. Verify the byte count and SHA-256 before XML
parsing. Refuse a changed existing input. Do not silently refresh it.

Write full projected paragraphs only to ignored local output. Do not print full
paragraph text in a public report, log, or commit. The public result contains
aggregate counts, source URLs, configuration values, and hashes only.

Use this canonical paragraph record for the private output:

```json
{
  "book_id": "1",
  "chapter_id": "1",
  "chapter_key": "1:1",
  "local_paragraph_ordinal": 1,
  "text": "..."
}
```

Serialize one record per line as UTF-8 JSON. Use sorted keys and
`ensure_ascii=false` and compact separators `(",", ":")`. Keep source order. End the file with one newline. Hash
these exact bytes with SHA-256. Publish the hash, record count, and byte count.
Keep the file itself ignored.

Create separate private outputs for the module traversal and the independent
traversal. Publish both paragraph-file hashes and the comparison result.
Report failed checks as failures. Do not describe them as an accepted projection.

## Fixed source selection and locations

Read one direct `text/body` subtree. Validate the complete body before
traversal. Select every body paragraph inside one book and one chapter.

Use the following location fields:

- `book_id`: the nearest book `div/@n` value;
- `chapter_id`: the nearest chapter `div/@n` value;
- `chapter_key`: `book_id:chapter_id`;
- `local_paragraph_ordinal`: one-based XML order within that chapter.

The source has no paragraph `xml:id` or `n` value. Do not invent one. The
location tuple above is the stable source identifier for this protocol.

Use `empty_policy="include"`. Keep an output record when all selected text is
removed. Preserve its source location and ordinal. Report its empty count.
Do not drop an empty record in this first validation. A later drop policy is a
separate protocol setting.

## Fixed XML validation

Require one `TEI` root in the exact TEI namespace. Require one direct `text`
child and one direct `body` child. Require the exact TEI namespace on every
element.

Validate all body markup before paragraph traversal. Fail on any unsupported
tag or structure. Do not skip invalid content because it is inside an
excluded subtree.

The pinned source has one direct body wrapper. It is a structural edition
wrapper, not a book or a chapter:

- Require one direct body `div` with `type="edition"` and `xml:lang="lat"`.
- Require no `n` or `subtype` on this wrapper.
- Require eight direct book divisions and seven direct `pb` markers inside it.
- Permit only those book divisions and `pb` markers as wrapper children.
- Treat the wrapper and its direct `pb` markers as transparent.
- Do not emit a paragraph record for the wrapper or its markers.
- Require no second edition wrapper and no nested edition wrapper.
- Reject a wrong wrapper type, wrong language, duplicate wrapper, or extra
  direct body element.

The reviewed module may support this wrapper as an optional form for synthetic
fixtures. The pinned-source run must require the exact wrapper above. A direct
body layout without the wrapper is a separate synthetic fixture. Do not use
that layout to accept the pinned source.

Require these division rules:

- Except for the edition wrapper, a `div` must have subtype `book` or `chapter`.
- A book or chapter `div` must have `type="textpart"`.
- A book and chapter must have a non-empty `n` value.
- A book must be a direct child of the edition wrapper.
- A chapter must be a direct child of one book.
- A chapter cannot contain another chapter.
- A book cannot occur inside another book or chapter division.
- Book IDs must be unique.
- `book_id:chapter_id` keys must be unique.
- A paragraph must be a direct child of its matching chapter.
- Nested paragraphs fail.

Require these correction and language rules:

- A `choice` must contain exactly `sic` followed by `corr`.
- A `choice` cannot contain direct non-whitespace text.
- `sic` and `corr` must be direct children of `choice`.
- Every `foreign` must have `xml:lang="grc"`.
- A foreign language other than `grc` fails, even inside an excluded subtree.
- An `add` element fails.

Treat unknown editorial tags, missing identifiers, duplicate identifiers, and
namespace errors as validation failures. Do not make a fallback record.

## Fixed text projection

Traverse mixed content in document order. Preserve source character spelling.
Do not change case, `u/v`, `i/j`, ligatures, punctuation, or Unicode form.

Apply these fixed rules:

- Keep the `corr` branch of each `choice`.
- Exclude `sic` text and descendants.
- Exclude `head`, `note`, `del`, `figure`, and `foreign` text and descendants.
- Preserve the tail of each excluded root at its parent traversal.
- Do not preserve tails from descendants inside an excluded subtree.
- Keep `hi` text. Ignore its formatting attributes.
- Keep nested `hi` content inline.
- Treat `pb` and `milestone` as transparent.
- Do not add a space for `pb` or `milestone`.
- Preserve selected text and tails before whitespace collapse.

Preserve XML whitespace rules exactly. Collapse only U+0020 space, tab,
carriage return, and line feed runs to one U+0020 space after traversal. Strip
only those XML whitespace characters at the paragraph ends. Preserve
non-XML whitespace such as non-breaking space. Do not apply NFKD, casefolding,
ASCII conversion, spelling repair, or word-boundary repair.

For a `choice`, keep the `corr` content and its tail. Preserve any `sic` tail
in its document position. The independent traversal must use the same fixed
choice rule and must expose any disagreement.

## Retained-boundary check

Check the retained stream after each content exclusion.
A non-empty `corr` replaces its `sic` branch and can remain inside a word.
An empty correction that removes non-empty `sic` content requires an exclusion-boundary check.
Apply that check before the first retained branch tail or later segment.
Do not use only the immediate sibling text. Continue over adjacent excluded
nodes, nested excluded nodes, and transparent markers until the next retained
segment or paragraph end.

For each exclusion boundary, compare:

1. the last non-XML-whitespace character in the retained prefix; and
2. the first non-XML-whitespace character in the next retained segment.

If both characters are Unicode letters and no source XML whitespace separates
them, fail. Do not insert a space. Do not remove a letter. Do not continue
with a repaired paragraph.

The source audit boundary scan used immediate sibling text. It is a diagnostic
only. It does not prove the final retained stream has no joins. This protocol
requires the final retained-prefix and next-segment check above.

Record the source location and error when a boundary check fails.
Keep detailed text context in ignored output. Publish the location and pass or fail result only.

## Structural validation targets

The preprojection source counts must match the public audit:

| Count | Required value |
| --- | ---: |
| Direct edition wrappers | `1` |
| Direct wrapper book divisions | `8` |
| Direct wrapper page breaks | `7` |
| Book IDs | `1` through `8` |
| Chapters | `211` |
| Paragraphs | `550` |
| Paragraphs outside book and chapter | `0` |
| Empty source paragraphs | `0` |
| Choice elements | `446` |
| Foreign elements | `276`, all `grc` |
| Notes | `628` |
| Deleted elements | `10` |
| Add elements | `0` |

The chapter counts by book must be
`1:11, 2:34, 3:27, 4:32, 5:29, 6:19, 7:34, 8:25`.
The paragraph counts by book must be
`1:28, 2:45, 3:45, 4:35, 5:204, 6:80, 7:74, 8:39`.

Report a count for every `book_id:chapter_id` key. Compare the per-chapter
source counts between both traversals. Require the same 211 keys and the same
paragraph count for every key. Report the source and projected counts by
book and chapter. Keep full paragraph location records in the private JSONL outputs.

With `empty_policy="include"`, the projected record count must equal the 550
source paragraph count. The empty projected count may be non-zero. Report it.
Do not replace an empty record with a selected non-empty record.

The selected paragraph subtree counts are preprojection counts. They are not
retained-text counts. The public audit reports, among other values, 446 choice
nodes, 276 foreign nodes, 626 notes, 7 deletions, and 525 highlights inside
selected paragraph subtrees. Do not require 276 direct foreign drops or 525
retained highlights.

Report actual traversal counters separately:

- retained element counts;
- direct excluded-root counts;
- ancestor-excluded descendant counts and paths;
- boundary-validation status;
- empty projected paragraph count;
- per-book and per-chapter record counts, with private per-paragraph locations.

These counters describe this fixed projection run. They do not prove that the
source edition is complete or that the source language is the VMS language.

## Independent comparison

Run `project_tei` from the reviewed `experiments/medical/tei_projection.py`.
Run a separate standard-library XML traversal for comparison. The comparison
traversal must not import projector visitor functions or reuse its internal
state. It may share the frozen rule table and source bytes.

Compare these values exactly:

- source SHA-256 and source byte count;
- source book IDs, chapter keys, and paragraph locations;
- per-book, per-chapter, and total paragraph counts;
- empty paragraph policy and empty counts;
- canonical paragraph records and their SHA-256 hashes;
- retained, direct-excluded, and ancestor-excluded counters;
- boundary-validation status;
- validation errors for intentionally invalid fixtures.

Stop on any mismatch. Record the first source location and both values. Do not
change a tag rule, whitespace rule, or boundary rule to make the values match.

## Fixed manual checks

Perform manual checks only at locations fixed before the source output is read.
Use the first and last selected paragraph in each book. This gives 16 source
locations. Also check the global source paragraph ordinals
`1 + 36k` for `k=0..15`, and ordinal `550`. This gives at most 33 unique
locations after duplicate removal.

The global ordinal is one-based XML order over body paragraphs. Convert each
location to the fixed book, chapter, and local ordinal tuple. Do not replace a
location because it has no choice, exclusion, marker, or boundary. Record
“feature not present” for that location.

For each location, compare the raw XML subtree with both local outputs. Check
the location fields, source spelling, XML whitespace, choice correction,
excluded content, tails, transparent markers, and empty status. Record each
check as pass, fail, or feature not present. Keep the checklist in ignored
output. Publish only its count and aggregate result.

## Acceptance gates and stop rules

Accept the validation only when all gates pass:

1. The source URL, commit, byte count, and SHA-256 match the audit receipt.
2. The reviewed projector and its tests are frozen before the source run.
3. All source structure counts match the fixed targets.
4. Both traversals produce identical records and hashes.
5. Every boundary check passes without an inserted or removed character.
6. Every fixed manual check passes or records “feature not present”.
7. The public report contains no paragraph text, private path, or user data.
8. The public report contains aggregate counts and hashes for both traversals.

Stop projection and publish an aggregate failure record when any gate fails. Stop on an
unsupported tag, non-Greek foreign element, malformed choice, missing or
duplicate location identifier, structural mismatch, or retained-letter join.
Do not silently repair, skip, normalize, or retokenize the source.

Do not fit a language model, search a VMS key, score a translation, or make a
language claim in this validation. A passing result only shows agreement on a
fixed extraction procedure and its independent comparison.

## Command

From the clean published freeze checkout, run:

```sh
python -m experiments.medical.run_projection --output-dir results/celsus-projection-v1
```

The runner fetches the fixed XML when its local input is absent.
It leaves acceptance pending until the fixed manual review is complete.
Retain that initial receipt. Record manual review and final acceptance in a separate result record.
Do not overwrite the initial pending receipt.

## Future run sequence

1. Complete the projector and runner reviews and any required fixes.
2. Publish this protocol and the reviewed implementation before the source run.
3. Verify the pinned source and audit receipt.
4. Run the module and independent traversal into separate ignored outputs.
5. Run the fixed manual checks.
6. Compare records, hashes, structure, counters, and boundaries.
7. Write the aggregate public report with all acceptance checks and failures.

No source projection has run under this proposed protocol.
A changed rule requires a new plan version and a new audit.
