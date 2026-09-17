# Celsus TEI projection

This directory contains a fixed XML extraction procedure for a proposed ancient Latin medical control.
The [protocol](../../docs/plans/celsus-projection-v1.md) defines the source, rules, and acceptance checks.
The [validation report](../../reports/CELSUS_PROJECTION.md) records the first source run and its separate manual acceptance.
Both traversals produced the same 550 paragraph records. A clean public checkout reproduced all five output files.

The paragraph projector accepts source bytes. The separate runner verifies the pinned source and compares two traversals.
It keeps full text private and writes public aggregate records. It does not fit a model.

## Use

```python
from experiments.medical.tei_projection import project_tei

result = project_tei(xml_bytes, empty_policy="include")
records = [item.to_dict() for item in result.paragraphs]
report = result.report
```

`empty_policy` must be `include` or `drop`. `include` keeps an empty record.
`drop` removes the record after it receives its stable source ordinal. Both
policies report the source count and the empty count.

## Fixed rules

- The root and every XML element must use the exact TEI namespace.
- The projector reads one direct `text/body` subtree.
- Body tags are limited to the tags recorded by the source audit.
- An optional single direct `body` edition wrapper is allowed when it has
  `type="edition"`, `xml:lang="lat"`, and no `n` or `subtype`.
- The edition wrapper cannot be nested, duplicated, or otherwise malformed.
- A `book` div must be a direct child of `body` or the edition wrapper.
- A `chapter` div must be a direct child of a `book` div.
- A paragraph must be a direct child of a `chapter` div.
- Each book or chapter division must have a non-empty `n` value.
- Paragraphs, books, and chapters inside excluded or editorial branches fail.
  This prevents note text or hidden structure from becoming records.
- Duplicate book IDs and duplicate `book_id:chapter_id` keys fail.
- Paragraph ordinals start at one within each chapter and follow XML order.
- A `choice` must contain exactly `sic` followed by `corr`. Only `corr` is kept.
- Every `foreign` must have `xml:lang="grc"`. This rule also applies inside
  excluded notes, figures, and other excluded subtrees.
- `head`, `note`, `del`, `figure`, `foreign`, and `sic` content is excluded.
  Their valid outer tails remain in document order.
- `hi` and `corr` content is retained. Nested `hi` elements remain inline.
- `pb` and `milestone` are transparent. They do not add spaces.
- The projector preserves mixed-content order and element tails.
- It collapses XML whitespace (`space`, tab, carriage return, and line feed)
  only. It does not change case, `u/v`, `i/j`, ligatures, or Unicode spelling.
- An exclusion never creates a guessed space. The projector compares the
  actual retained prefix with the next retained segment. If both boundary
  characters are letters and no retained XML whitespace separates them, the
  projection fails. The check covers adjacent and nested exclusions.
- An empty correction is a deletion. If its `sic` branch has source content,
  the boundary check remains active through the `sic` and `corr` tails.
- Nested choices apply the same rule. Their choice text and selected branch
  tails remain in XML order. An empty nested correction remains a deletion.
- The boundary check uses the same selected stream: choice text, `sic` tail,
  selected correction content, and correction tail.

The validator runs over the complete body before paragraph traversal. It
therefore checks unsupported tags, `add`, malformed choices, and non-Greek
foreign elements inside excluded subtrees.

## Report fields

`source_counts` counts tags in the complete body subtree, including `body`.
`selected_subtree_counts` counts tags in all selected paragraph subtrees.
`actual_retained` counts elements visited as retained or transparent.
`direct_excluded` counts excluded roots at the point of exclusion.
`ancestor_excluded` counts descendants below an excluded root. It contains
tag totals and paths such as `foreign|note` and `note|note`.

The report also records book IDs, chapter keys, paragraph counts, the empty
paragraph policy, and dropped empty records. These counts do not claim that
the source has complete print-edition collation.

## Verification

Run the synthetic tests from the repository root:

```text
PYTHONPATH=src:. python -m unittest experiments.medical.test_tei_projection -v
```

The fixtures cover mixed content, choice tails, notes, Greek inside notes,
nested highlights, transparent page markers, stable IDs and ordinals,
duplicate IDs, empty records, unsupported tags, namespace failures, Unicode
spelling, direct-parent structural failures, and the retained-boundary
exclusion check.

The fixtures do not prove behavior on the pinned Celsus file.

## Fixed source runner

After publication of the reviewed implementation and freeze manifest, run:

```sh
python -m experiments.medical.run_projection --output-dir results/celsus-projection-v1
```

The runner requires the exact eight-book source structure and checks the external five-file freeze manifest.
It compares source locations, projected records, counts, and hashes from two separate XML traversals.
Private JSONL files contain full paragraphs. Public receipts contain aggregate data and source links.
The fixed manual review remains pending after automated checks pass. Preserve that initial receipt when recording the manual result.

Run both synthetic suites with:

```sh
PYTHONPATH=src:. python -m unittest discover -s experiments/medical -p 'test_*.py' -v
```

See the [projector review](PROJECTION_REVIEW.md) and [runner review](RUNNER_REVIEW.md) for review scope and remaining limits.
