# Local cyclic certificate review

Review date: 2026-09-17.

This is a read-only review of the pure local certificate core and its
synthetic tests. It uses no VMS source files, source counts, images, or
manuscript arrays. It does not run a source parser or a future runner.

## Material findings

No logical certificate defect was found under the fixed per-word contract.
One integration guard remains: `WordSpan.word_index` is local to one text
extraction. A future aggregator must key affected words by source record and
locus. It must not sum words from several loci by local index alone.

## Artifact identity

The earlier handoff named this core hash:

```text
38d22d1e1f01d6d6d912616eddd49ae4e6a8dcd963639c81ecf557cdb7da9409
```

The current final workspace bytes for `experiments/local_cyclic/certificate.py`
hash to:

```text
b6ce40d04fd2325e7500be3c9445970ba63853c8b0a00a8bc0c9c73f254821c2
```

The tests match the handoff hash:

```text
experiments/local_cyclic/test_certificate.py
449ac8d378512bc2deeb4432a33ad23276ec4489872718c10162d778b3028a25
```

The reused unitizer and its six tests hash to:

```text
experiments/homophonic/units.py
fc321f7cc59bf91aed1061d9fb72b531125ab9255ae171167de0bbe289c59760
experiments/homophonic/test_units.py
a6f7ca23a6377d95836c53b543c1e339cc47358cdf2e76fa5ec79fbea6a53209
```

Root confirmed that the current `b6ce...` bytes are the final core. The change
from `38d...` adds the default `representation="raw"` argument. This review
covers the current final bytes. Use `b6ce...` for the freeze record and retain
`38d...` only as the prior byte-version identifier.

## Result

The current core implements the stated local certificate. For each eligible
word, it compares adjacent units only within that word. If two adjacent units
are equal, the exact emitter with `k >= 2` distinct units per plaintext symbol
cannot produce the word. Different plaintext symbols cannot repair the repeat
because their preimage sets are disjoint. The certificate is therefore valid
for the fixed source, unitization, word segmentation, and emitter contract.

The core does not compare the last unit of one word with the first unit of the
next word. It also does not compare words from different loci. Deleted words,
excluded controls, and locus boundaries therefore cannot create a false
adjacency certificate. A certificate-free result remains
`not_falsified_by_local_check`; it does not support a reading.

## Boundary and eligibility review

`extract_word_spans` follows the clarified strict policy:

* It trims layout whitespace at the candidate edges.
* It rejects interior whitespace.
* It splits on top-level periods and keeps periods inside consumed constructs.
* It splits on top-level commas and marks both adjacent candidates with
  `uncertain_space`.
* It consumes bracket, brace, high-ASCII, and angle-control constructs before
  processing their internal punctuation.
* It rejects the complete candidate that touches a control, uppercase code,
  question mark, apostrophe, non-ASCII code, or other construct.
* It never lowercases a source candidate or keeps a valid substring from an
  excluded candidate.

The period reset after an empty comma neighbor is covered by
`test_clean_period_clears_an_empty_comma_neighbor`. The comma behavior is
covered by `test_uncertain_comma_invalidates_both_adjacent_words`.
`test_excluded_candidate_cannot_supply_partial_repeat` checks that a diagram
marker does not leak a partial repeat. The control tests also cover paragraph
controls, inline controls, uncertain readings, ligatures, apostrophes,
high-ASCII codes, uppercase input, non-ASCII input, and incomplete spans.

These rules prevent an excluded marker or an unknown space from joining two
known unit runs. A caller must still pass one locus text at a time or preserve
unique source-record identity when it aggregates results. `WordSpan.word_index`
is local to one extraction. Reusing that index across loci can undercount
`affected_word_count`, even though it cannot create a cross-locus certificate.

## Unitization and certificate review

`unitize_word` delegates to the frozen raw and `visual` six-candidate
unitizer. The unitizer uses longest match, returns ordered half-open spans, and
keeps unmatched lowercase characters as singleton units. The local visual
tests cover all six compounds, exact reconstruction, and a repeated visual
unit span. The six frozen unitizer tests also pass.

The certificate loop uses adjacent pairs from the unit sequence. It counts
overlapping repeats separately, records the first unit index of each repeat,
and records a half-open span for the visual track. The synthetic `aaa` test
confirms two certificates at indices zero and one. The visual span tests
confirm that spans are contiguous and do not overlap.

The pure result object contains unit labels, indices, counts, and optional
unit spans. It does not contain the source surface or a complete raw word.
`WordExtraction` and `WordSpan` do contain source surfaces for in-memory
processing. A future runner must serialize only the result fields allowed by
the plan. It must not serialize those extraction objects or raw words.

## Test evidence

The focused local suite passed:

```text
python -m unittest experiments.local_cyclic.test_certificate -v
Ran 15 tests in 0.001s
OK
```

The frozen unitizer suite passed:

```text
python -m unittest experiments.homophonic.test_units -v
Ran 6 tests in 0.010s
OK
```

The tests use symbolic strings only. They do not read source files or images.

## Conditions before any source run

Freeze the current final core hash with the test, unitizer, and plan bytes
together. The future runner must preserve source file, locus, and
transcriber identity in each certificate location. It must keep word indices
unique within that source context when it sums affected words. It must write
locations and aggregate fields without raw words or full token arrays.

The result can falsify the exact fixed emitter for one fixed track when a
certificate exists. It cannot reject a model with hidden units, a different
word segmentation, a reset inside a word, a variable cycle, a generic
at-most-two map, or a different unitization. No source result follows from
this review.
