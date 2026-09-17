# VMS local cyclic falsification v1

Status: fixed development protocol, before the first source run. Date: 2026-09-17.

This protocol tests one narrow emitter model on two fixed written-unit tracks.
It uses no language model, dictionary, key search, or translation.

The corpus and earlier unitization work are already inspected. This run is
therefore a development result. It is not blind confirmation.

## Model

Let `U` be the declared atomic unit set. Let `P` be the plaintext symbol set.
Each plaintext symbol has exactly `k` distinct units, with `k >= 2`.
Preimage sets for different plaintext symbols are disjoint. The emitter uses a
fixed cycle for each preimage set. It emits the next distinct unit whenever
the same plaintext symbol occurs. The stream order is preserved.

The protocol treats each eligible word as one independent uninterrupted
segment. Each segment has an arbitrary initial cycle phase. A word boundary
starts a new segment. The protocol makes no claim about continuity across a
line, gap, locus, folio, or physical leaf.

The model has no missing or hidden emissions. Every accepted visible unit is
an element of `U`. A different unitization or a model with hidden units is a
different model.

### Local certificate

If two adjacent units in one segment are equal, the model is impossible for
that segment.

If both positions encode the same plaintext symbol, the cycle must advance to
a different unit because `k >= 2`. If they encode different symbols, disjoint
preimage sets require different units. Both cases contradict equal adjacent
units.

The test is valid for every integer `k >= 2`. It does not identify `k`.
One certificate is sufficient to falsify the fixed model for the tested track,
source, and segment rule. Zero certificates only mean that this local test did
not falsify that model.

This check does not test a generic at-most-two map. Such a map can assign one
unit to a plaintext symbol and can permit adjacent repeats. It also does not
test a variable cycle, a reset inside a word, an inserted hidden unit, or a
different visual segmentation.

## Fixed source and word policy

Use the two existing IVTFF source files:

* `data/raw/ZL3b-n.txt`
* `data/raw/IT2a-n.txt`

Use `src/voynich/corpus.py` to validate IVTFF structure. Fix
`uncertain_spaces="split"`. The runner must preserve source location fields
from each locus record.

The local test accepts only a fully certain, complete word. The strict
word extractor must apply these rules before unitization:

1. Keep one contiguous basic EVA run with lowercase ASCII letters only.
2. Keep the source span and its token boundaries. Do not lower case source
   text during eligibility checks.
3. Reject a span that contains or touches an uncertain-space comma, uncertain
   reading, ligature construct, apostrophe, high-ASCII code, question mark,
   inline control, diagram marker, or other excluded source construct.
4. Reject an empty span and any span that the IVTFF parser cannot classify as
   one complete word.

The parser's accepted `tokens` list alone is not sufficient for this rule. It
can lower case some source marks and can represent a ligature as a token.
The strict extractor must retain source spans so that these cases remain
excluded.

Only top-level periods and commas separate candidate words. Delimiters inside
an inline construct do not create accepted subwords. Trim whitespace at a
candidate edge. Reject a candidate with interior whitespace; do not delete it.
The original parser treats whitespace as layout. This stricter rule avoids
creating adjacency by removing source characters.

Reject the complete candidate when it contains an inline construct, including
a paragraph or diagram marker. Reject both neighbors of a comma. A subsequent
period ends that uncertain boundary, including when an empty span intervenes.
Never extract an accepted substring from an excluded candidate. Keep the
original zero-based candidate index, including excluded non-empty candidates.
An empty span supplies no word and no repeat certificate.

Do not join words across whitespace, punctuation, loci, or records. Do not
drop an eligible word because another word in the same locus is excluded.
Record excluded-word counts by reason. A source with no eligible words is
`inconclusive_no_eligible_words`, not a negative result.

The two source files are separate transcription inputs. Report them
separately. A shared folio does not create independent evidence. A combined
count is descriptive only.

## Two predeclared unitizations

Run both tracks over the same eligible-word set. Do not select a track after
seeing a repeat result.

### `raw_eva`

Represent each lowercase EVA character as one atomic unit. Preserve its order.
Do not merge characters, remove rare characters, or add an unknown unit.

### `visual_six`

Use the six candidates defined in
`docs/plans/visual-homophonic-pilot.md`:

```text
ch, sh, cth, ckh, cph, cfh
```

Scan each word from left to right. Select the longest candidate at the current
position. Represent every remaining lowercase character as one singleton.
Reuse `experiments/homophonic/units.py`; map its `raw` and `visual` options to these two track names.
Use no other multi-character unit. In particular, do not add `in`, `iin`,
`ii`, `iii`, or `qo`.

The unitizer must return ordered, non-overlapping spans that cover the source
word exactly. It must reconstruct the accepted word from those spans. A span
failure stops the run.

The existing predictive worker has a separate grouped experiment with eight
declared units. Do not use that grouping for this six-candidate track. Pin the
six-candidate rule and its implementation in the run freeze.

## Measurement

For each source and unitization, process every eligible word independently.
For a word with units `u[0] ... u[n-1]`, inspect each index `i` from zero
through `n-2`. Count a certificate when `u[i] == u[i+1]`.

Count overlapping certificates separately. A word with two adjacent equal
pairs contributes two certificates and one affected word. Equal units at the
end of one word and the start of the next word do not form a pair.

The result record must contain these aggregate fields:

* eligible word count;
* eligible unit count;
* adjacent-pair count;
* certificate count;
* affected-word count;
* excluded-word counts by reason;
* counts per source file.

The result must contain every certificate location, in deterministic source
order. Do not keep only selected examples. Each location contains:

* relative source file;
* zero-based source record index;
* folio, locus, and transcriber;
* zero-based candidate-word index within the locus;
* zero-based unit index of the first equal unit;
* equal unit label;
* optional half-open unit span for the visual track.

Do not write raw words or complete token arrays to the result. The location
fields must permit later image review without exposing a selected word list.
The certificate count must equal the number of saved locations.

Use these status values:

* `falsified_for_fixed_track` when the certificate count is greater than zero;
* `not_falsified_by_local_check` when eligible words exist and the count is
  zero;
* `inconclusive_no_eligible_words` when the denominator is zero.

These statuses are per source and per unitization. A failure in `raw_eva`
does not reject `visual_six`. Failures in both fixed tracks reject both fixed
track models under this local certificate only.

Do not compute a p-value or combine the two tracks into one significance value.
The certificate is a logical contradiction under a fixed model contract.

## Fixed command and outputs

Run this command from a fresh repository checkout after publication of the freeze:

```sh
python -m experiments.local_cyclic.run_frozen
```

The command accepts no options. It runs the 21 frozen certificate and unitizer tests before parsing source text.
The eight runner tests must also pass before publication.
The package initializer imports no source-processing module before the hash gate.

Write these four records below `results/vms-local-cyclic-falsification-v1/`:

- `ZL3b-n-raw_eva.json`
- `ZL3b-n-visual_six.json`
- `IT2a-n-raw_eva.json`
- `IT2a-n-visual_six.json`

Check all output paths before parsing. Refuse existing outputs and symlinked path components.
Write each record with exclusive creation. Keep any partial output from an interrupted command.

Allow 60 seconds for the whole command in the external run supervisor.
On timeout, terminate its process group, wait five seconds, and kill remaining processes.
Do not retry the same output directory or change the word policy after a result.
The wrapper itself performs no network request. Source downloads must finish before freeze verification.

## Provenance and freeze

Before any source parsing for the actual run, publish a freeze record with:

* this plan's SHA-256;
* `data/source_manifest.json` SHA-256;
* both source-file SHA-256 values;
* `src/voynich/corpus.py` SHA-256;
* the strict word extractor SHA-256;
* the frozen `experiments/homophonic/units.py` and its test SHA-256 values;
* the synthetic test SHA-256;
* Python version, command, and output paths.

Record the actual hash values in the freeze record. Do not use placeholders in
the run record. Refuse to run when a pinned byte differs or an output already
exists. Do not parse source text until all byte checks pass.

The runner must write one aggregate record for each source and track
under `results/vms-local-cyclic-falsification-v1/`. The record must include
the protocol name, unitization name, model contract, input hashes, aggregate
counts, statuses, and complete certificate locations. It must state that image
review was not performed.

## Synthetic controls

Freeze and test these controls before the source run. Use symbolic atomic unit
names, separate from EVA symbols.

### Model-positive controls

Generate segments from disjoint preimage sets of size two and size three.
Use a fixed cycle and several arbitrary initial phases. Place segments in
separate words. The expected certificate count is zero for each size and
phase. This checks that resets and cycle phases do not create false repeats.

### Model-negative controls

Start with a model-positive segment. Replace one interior unit so that one
adjacent pair is equal. The expected result is one certificate at the known
unit index. Add a separate three-unit-repeat fixture and expect two
overlapping certificates.

Place equal units at the ends of two different words. Expect zero
certificates. Place the same unit non-consecutively in one word. Expect zero
certificates. These controls check the segment and adjacency boundaries.

### Eligibility and unitizer controls

Give the strict extractor fixtures with uncertainty, ligature syntax, a
non-ASCII code, an excluded marker, and an incomplete span. Each must be
excluded and must not create a certificate.

Exercise every six-candidate visual unit and its longest-match behavior with
synthetic span fixtures. Require exact coverage, ordered spans, and exact
round-trip reconstruction. Run the same fixture through the raw track and
verify that the two unit sequences remain separate measurements.

No synthetic control may supply a key, language, or expected manuscript
result. A control failure blocks the source run.

## Image review and limits

The local result is a transcription result. It is not an image result. If a
certificate is found, a later reviewer may inspect the pinned folio image at
the recorded location. The review must classify each location as
`image_verified`, `image_uncertain`, or `image_not_checked`.

Image review cannot delete or edit a certificate. A transcription correction
requires a new source hash and a new protocol run. Do not present an image
review as independent transcription evidence.

The protocol can reject only the exact combination of source bytes, strict
word policy, atomic unitization, segment resets, and cyclic emitter stated
here. A writing system that uses ligatures, hidden emissions, another
segmentation, or another reset rule is outside this result. A repeat-free
stream does not support a translation, language identification, or manuscript
solution.

## Bounded implementation steps

1. Add a pure strict-word extractor and the two unitizers. Keep source reading
   outside the certificate function.
2. Add a pure certificate function with synthetic positive, negative, boundary,
   eligibility, and span tests.
3. Add a hash-checking runner. Make it refuse stale inputs and existing output.
4. Publish the freeze record after code and tests pass. Only then parse the two
   source files and write aggregate records with all locations.
5. Review images, if needed, in a separate record after the transcription
   result is immutable.

No source counts, certificate counts, image examples, or manuscript result are
reported before the protocol and implementation freeze.
