# Stage 2 substitution methods

Status: implemented method documentation for a bounded pilot. It reports no
pilot results and makes no Voynich solution claim.

This document describes the code in the repository. The future proposal in
[substitution-experiment.md](../plans/substitution-experiment.md) has a wider
scope. Keep that proposal separate from this pilot.

## Reference corpora

The [reference loader](../../src/voynich/reference.py) reads pinned Universal
Dependencies (UD) 2.18 CoNLL-U files from [reference_manifest.json](../../data/reference_manifest.json).
It checks each input file against its SHA-256 hash before parsing.

The Latin corpus is `latin_llct`. The upstream whole-charter split has 422
train charters, 48 validation charters, and 51 test charters. The loader reads
each charter identifier from the source headers and raises an error if one
charter crosses partitions. It removes 132 exact normalized duplicate
sentences from validation and 129 from test. Near duplicates remain.

The Old Italian corpus is `italian_old`. The loader assigns Dante's
`Inferno`, `Purgatorio`, and `Paradiso` to train, validation, and test. Each
canticle occurs across the upstream file labels, so this assignment combines
those labels by canticle. These partitions are canticles of one work by one
author. They are not independent texts.

For each complete surface form, the loader applies NFKD normalization,
casefolding, and removal of combining marks. It accepts the form only when
the complete result matches `[a-z]+`. It does not split a rejected form. It
keeps multiword-token surface forms, skips covered integer components, and
skips empty nodes.

## Substitution model

The implemented substitution runner uses raw EVA characters. It preserves
word boundaries and uses no cross-word transitions. A key is an injective map
from input symbols to lowercase ASCII letters `a` through `z`.

The reference language model uses character order 3 and additive smoothing
`alpha=0.1`. The model is fit on all words in the reference `train`
partition. It includes fixed word-boundary and end-of-word controls. The
model scores a next-character objective. It does not identify a language.

The search in [substitution.py](../../src/voynich/substitution.py) uses a
frequency-ranked first key and randomized restarts. The pilot configuration
uses search seed 408, 8 restarts, up to 2,000 proposals per restart, and
start temperature `0.02` bits per predicted symbol. The search records the
actual proposal count. It does not add homophones, nulls, transpositions,
spelling repairs, or per-token exceptions.

## Planted controls

The [planted-control runner](../../scripts/run_substitution_pilot.py) applies
a random injective key to reference words while preserving word boundaries.
The language model uses the complete reference `train` partition. The pilot
fits a key to a sampled validation text and scores held-out reference test
text.

The completed calibration batches used key seeds 500 through 531 and capped
each selected text sample at 20,000 words. For each language, every seed uses
the same text split and the same sampled words. The keys are multiple controls
on the same text, not independent texts. The search seed remains 408.

These controls test recovery power. They do not estimate a false-positive
rate. The pilot has no false-positive estimate.

## Voynich comparison runner

The [Voynich runner](../../scripts/run_voynich_substitution.py) compares an
observed sample with a `within_word_shuffle` sample. It fits each key on the
full eligible training partition and scores train, validation, and test. It
also records identity scores and a 32-key random-key test baseline. The
random-key baseline uses seed 409.

The current runner uses the [grouping module](../../src/voynich/groups.py).
It uses 52 source-backed `(Q,B)` groups from
[bifolio_manifest.json](../../data/bifolio_manifest.json), with grouping
version `ivtff-bifolio-metadata-v3` and split salt
`voynich-bifolio-408-v3:`. The split has 35 train, 4 validation, and 13 test
groups. The manifest SHA-256 is
`998cb3d6c8327ff0bdf786d52968fa3bec9f5fa9b05ba7ae56065fc9639fad72`.
The manifest uses provider IVTFF metadata. It is metadata-only. It does not
include or claim an original manual physical-sheet map.
No Voynich substitution result is reported here.

## Supporting checks

The [inventory check](../../scripts/check_substitution_inventory.py) reports
raw and grouped input-unit cardinality and injective alphabet feasibility. It
does not search a key or identify a language.

The [invariant comparison](../../scripts/compare_reference_invariants.py)
compares word lengths and repeated-unit patterns with reference training
words. Pattern support is a finite-vocabulary upper bound. It does not test a
joint key or identify a language.

## Pilot boundary

The future proposal includes the `compound_eva_v1` track, a fresh physical
group evaluation, larger confirmatory controls, and decision gates. Those
requirements do not describe a completed pilot. This document records method
scope only. It does not report result values, a plaintext, a language choice,
or a Voynich decipherment.
