# Visual homophonic substitution pilot

Status: prototype protocol. Date: 2026-09-17. Manuscript experiments remain
deferred. Reference control settings must be frozen before their first run.

This plan does not change the frozen
[`lexicon-feasibility-v1.md`](lexicon-feasibility-v1.md) pilot. It reports no
new manuscript measurement.

## Frozen near-term objective

The near-term milestone is solver feasibility on pretokenized synthetic
controls. It has four tasks:

1. Check the fixed tokenizer and its source spans.
2. Generate atomic `c##` controls with fixed word boundaries.
3. Fit injective, capacity-two, and unrestricted synthetic keys.
4. Apply the validation and test gates in this plan.

Do not measure the VMS in this milestone. Do not draw VMS statistical
inferences. Existing VMS outputs remain exploratory. A new protocol cannot
make previously inspected data blind.

## Model definition

The proposed visual tokenizer uses longest match for these six compound
candidates:

```text
ch, sh, cth, ckh, cph, cfh
```

At each position, select the longest matching compound. Make every remaining
EVA atom one singleton cipher unit. Do not merge `in`, `iin`, `ii`, `iii`, or
`qo`. Do not drop rare or unmatched EVA forms.

The tokenizer accepts one canonical lowercase ASCII word. It rejects braces,
capitalization, separators, and other characters without conversion. It retains
unmatched lowercase characters as single units. Spans refer to this input word.
The tokenizer does not reconstruct handwritten forms or resolve uncertainty.

Let `U` be the ordered cipher-unit set. Let `P` be the 26 lowercase ASCII
letters. The decoder searches one total global map:

```text
f: U -> P
```

Each cipher unit maps to one letter. Several units can map to one letter. Here,
“homophonic” means multiple cipher symbols for one plaintext letter. It does
not assign sounds to VMS signs.

The model has these limits:

* Preserve every transcribed word boundary.
* Map every cipher unit to one letter. Use no nulls.
* Expand no unit to several letters. Use no abbreviations.
* Use no word, page, hand, section, neighbor, or position repair.
* Use one map for every word and every split.

For a known control, use a fixed emitter. For each plaintext letter `p`, collect
the units where `f(u) = p`. Emit them in a cyclic order. Advance the cycle at
each occurrence of `p` in a partition. Reset the cycle at each partition. The
decoder does not receive cycle state.

## Tokenizer checks

Run these checks before any solver control:

1. Apply longest match to fixtures that contain each compound and overlapping
   singleton prefixes.
2. Require ordered, non-overlapping spans.
3. Require spans to cover each input word exactly once.
4. Reconstruct each word from raw spans. Require exact source-string equality.
5. Preserve word boundaries and source word identifiers.
6. Report raw form, unit label, and half-open span for every unit.

The synthetic `c##` symbols are atomic control units. Store them as JSON arrays
within word arrays. Require exact serialization round trips and preserved word
boundaries. These controls do not pass through the EVA tokenizer. They cannot
validate units selected from manuscript images.

Any failed span or round-trip check blocks the control gate. Do not repair a
failed span during model fitting.

## Evidence and limits

The project note [`glyph-unit-evidence.md`](../research/glyph-unit-evidence.md)
links these sources:

* [EVA transcription guide](https://www.voynich.nu/transcr.html)
* [Currier paper](https://www.voynich.nu/extra/curr_main.html)
* [Smith–Ponzi preprint](https://agnosticvoynich.files.wordpress.com/2019/06/glyph-combinations-across-word-breaks-in-the-voynich-manuscript-preprint.pdf)
* [Ligature study](https://doi.org/10.1371/journal.pone.0260948)

These sources support the six forms as written-shape or statistical-unit
candidates. They support segmentation only. EVA does not assign pronunciation
or meaning. The sources do not show that the forms are letters, sounds, or
cipher units. Smith and Ponzi keep `i` and `n` separate in their common visual
inventory. This supports excluding `in` and `iin` from the six compounds.

The cipher map is a new model assumption. The reviewed sources do not establish
its use in the VMS. Preserved word boundaries, no nulls, no abbreviations, and
no context repairs make the model testable. They do not make it historical.

## Future factorial design

The following four cells are a future VMS design. The near-term controls use
synthetic atomic units. They do not estimate VMS effects.

| Cell | Unitization | Map constraint |
| --- | --- | --- |
| `raw-injective` | Existing raw EVA units | At most one unit per letter |
| `raw-cap2` | Existing raw EVA units | At most two units per letter |
| `visual-injective` | Six longest-match compounds plus singles | At most one unit per letter |
| `visual-cap2` | Six longest-match compounds plus singles | At most two units per letter |

For score `S`, report these contrasts:

* Unitization: `visual-injective - raw-injective`.
* Map freedom: `raw-cap2 - raw-injective`.
* Combined change: `visual-cap2 - raw-injective`.
* Interaction: `(visual-cap2 - visual-injective) - (raw-cap2 - raw-injective)`.

An injective cell needs `|U| <= 26`. A capacity-two cell needs `|U| <= 52`.
Report infeasible cells. Do not truncate units. Do not call the combined cell a
unitization effect when its paired map cell is absent.

Unrestricted many-to-one mapping is a separate upper-capacity sensitivity
control. It is not a third factorial level.

## Map families and synthetic keys

For a VMS cell, the solver searches maps. It does not use a seeded map.

An injective map has at most one cipher unit per plaintext letter. A capacity-two
map has at most two. An unrestricted map lets every unit select any of 26
letters. Its map class has `26^m` assignments for `m = |U|`.

For every fitted map, report `m` and the full preimage distribution. Include the
number of plaintext letters with zero, one, two, and more than two units. The
synthetic families use different inventory sizes. Their score differences are
not a causal estimate of capacity.

Known controls use a separate synthetic inventory. They do not use the observed
VMS unit count:

* Injective controls use `c00` through `c25`.
* Capacity-two and unrestricted controls use `c00` through `c51`.

The capacity-two inventory has exactly two units for each plaintext letter. The
injective inventory has exactly one. For each control seed:

1. Shuffle the synthetic units and the 26 letters.
2. Assign injective units to distinct letters.
3. Assign two capacity-two units to each letter.
4. Assign the first 26 unrestricted units to distinct letters. Assign the rest
   to any letters.
5. Shuffle each letter's unit order for the fixed emission cycle.

Use 32 fixed seeds per family and corpus. Reserve `6000`–`6031` for injective,
`7000`–`7031` for capacity two, and `8000`–`8031` for unrestricted controls.
These generators define surjective positive strata. They are control fixtures,
not representative samples of every map.

Record each seed, synthetic unit order, map, emission order, and partition reset.
Do not inspect VMS data or held-out reference words when generating a key.

## Known-cipher control protocol

### First reference feasibility runs

Freeze this initial subset before reading a new reference result:

| Setting | Value |
| --- | --- |
| Reference sources | Latin LLCT and Old Italian, with the existing pinned partitions |
| Control family | `cap2` |
| Encryption seed | `7000` |
| Fitting input | All encrypted validation words |
| Lexicon | Unique normalized training words |
| Objective weight for a type with count `n` | `n*T+N`, where `T` counts types and `N` counts tokens |
| Score denominator | `2*T*N` |
| Cipher-unit order | Descending total objective weight of types that contain the unit; lexical ties |
| Bound engine | Bitset, checked against the scalar engine |
| Exact search budget | 1,000 expanded or pruned frontier nodes per run |
| Starting maps | One cold run and one annealing-assisted run per reference |
| Annealing model | Three preceding letters, additive smoothing `0.1`, fixed word boundaries |
| Annealing training | Plaintext reference training words only |
| Annealing budget | Eight restarts, 2,000 proposals per restart, seed `408` |
| Temperature | `0.02` bits per predicted position, linearly reduced to zero |
| Held-out scoring | Write the selected key first; score the test partition afterward |

There are four initial runs. Run them sequentially to limit memory use.
Record any resource stop. Do not report an unfinished process as a scored run.
The warm start supplies an incumbent only. It does not restrict the search root.
Record both the heuristic map and the map selected by the lexical objective.

These four reference controls are planned and have not been executed.

These runs test computational feasibility. One encryption key per reference
does not complete the planned 32-key calibration. They do not permit a manuscript
experiment or a language claim. Use a new output path for each later revision.

Use the frozen Latin LLCT and Old Italian partitions and token policy from the
lexical pilot. Build the plaintext lexicon from each training partition only.

For every synthetic key:

1. Build the training lexicon from plaintext training words.
2. Encrypt training, validation, and test words for audit.
3. Fit the unknown map on encrypted validation words and the training lexicon.
4. Do not supply encrypted training words to the solver. The same plaintext
   types built the lexicon. That input would make the control artificially easy.
5. Freeze the returned map before test scoring.
6. Use the planted map only for control scoring, never for selection.

Copy each plaintext word boundary. Emit one cipher unit per plaintext letter.
These controls contain no nulls, abbreviations, word joins, or context repairs.

## Coverage and diagnostic gates

Define the fully observed stratum by test coverage:

* **Fully observed:** every test unit occurs in encrypted validation fitting
  data. Validation accuracy is a fitting diagnostic, not held-out evidence.
* **Partly observed:** at least one test unit is absent from encrypted
  validation fitting data. This is a coverage limit, not a search defect.

Report weighted test-unit coverage and test-word coverage. Weighted coverage is
the fraction of test unit positions whose unit occurs in fitting data. Test-word
coverage is the fraction of test words whose units all occur in fitting data.

The near-term gate reports pooled character and token counts for observed test
positions. It also reports the per-replicate pass rate. A 100% pooled score can
hide a failed replicate. Keep every replicate and every failure.

Apply the same calculations to validation as a fitting diagnostic. A zero
denominator is `null`. It is not 100% and it is not a failed search.

For fully observed keys, test character and exact-token recovery can reach 100%
only as a diagnostic. A finite lexicon does not guarantee this result. Score the
planted map as an oracle. Its character and token ceiling is 100% by construction.

Report observed and absent test positions separately. An error on an observed
unit is a decoding error. It can result from objective ambiguity or a
generalization failure. It is an algorithm defect only when the certified search
fails its planted-objective check below. An absent unit has no fitting
observation. The earlier Italian baseline contains validation units outside
every positive lexical hit. Their presence in fitting data does not establish
their assignments.

## Key ambiguity

Let `B_planted` be the validation objective from the planted map. Let `B_best`
be the certified solver objective. Do not assume that `B_planted` is optimal.
The training lexicon can omit validation word types.

Count optimal keys only after exhaustive enumeration or a proof. A heuristic
list is not a count. Otherwise report a lower bound or `not certified`.

For each incumbent positive lexical hit set, report the units used in those hits
and the units outside them. A completion lemma for outside units supplies a
lower bound only. Positive-hit coverage does not prove identifiability.

Apply these labels independently. A control can have more than one label:

1. **Decoding error:** the returned map has an observed validation or test
   error. This is not automatically an algorithm defect.
2. **Key-identifiable:** `B_best = B_planted`, the planted map is optimal, and
   all optimal maps agree on observed validation and test units.
3. **Objective-insensitive:** `B_best = B_planted`, but optimal maps differ on
   an observed unit.
4. **Lexical overfit:** `B_best > B_planted`. The objective prefers another map.
5. **Generalization failure:** a validation-selected map has a test error.
6. **Algorithm defect:** a certified search returns `B_best < B_planted`.
7. **Unidentifiable:** a test unit is absent from fitting data.

An uncertified search is incomplete. Exact score does not imply key recovery.
The earlier Italian reference control reports 24 fitting symbols and at least 60
optimal keys ([`reports/LEXICON.md`](../../reports/LEXICON.md), [Italian reference
control](../../reports/lexicon-pilot-v1/italian-reference.json)). It is a reference
control, not a manuscript result. This plan does not remeasure that pilot. Record
its objective ambiguity separately.

## Deferred nulls

The following nulls belong to the future VMS study. The near-term milestone runs
synthetic controls only.

Word order within a partition is invariant under the lexical objective. A
word-order shuffle has the same bag-of-word score. Do not use it as a null.

Use these predeclared nulls later:

1. **Within-word unit shuffle:** permute units inside each word. Preserve word
   boundaries, word lengths, unit counts, and partition sizes.
2. **Group relabel:** after tokenization, apply an independently seeded
   bijection from cipher unit to cipher unit inside each physical group. Keep
   spans, words, and group sizes. Composition by a bijection preserves local
   patterns and preimage capacity for every decoder family. Draw no plaintext
   map for this null.
3. **Decoy lexicon:** apply one deterministic alphabet permutation per training
   type. Preserve exact length, within-word equality pattern, type count, and
   each type's token count. Redraw after collisions with the next declared
   seed. Decide before generation whether to exclude original training forms.
   Never inspect validation or test words. Collision exhaustion invalidates the
   replicate.

## Deferred VMS sequence and inference

When the VMS study resumes, use this sequence:

1. Fit candidate maps with the training partition only.
2. Select settings and a key with the validation partition.
3. Freeze the selected key before any test read.
4. Score the test partition once.

No VMS inferential claim is allowed until the four cells, two reference
languages, null families, and replicate count are fixed. Predeclare a
max-statistic or Holm family correction. Bootstrap by physical Q/B blocks.
Keep all current VMS outputs exploratory. Do not call a lexical score a
translation or a decipherment.

## Near-term completion gate

The near-term work is complete when:

* EVA units pass source-span checks. Atomic `c##` words pass serialization
  round trips and preserve word boundaries.
* Injective controls use 26 units. Capacity-two controls use 52 units with two
  units per plaintext letter.
* The solver fits encrypted validation against the training lexicon and scores
  a frozen map on test.
* Aggregate observed-position and observed-token gates reach 100%, or each
  failure is recorded by category.
* Coverage limits, objective ambiguity, and non-certified key counts are
  reported separately.

This gate tests the solver and the control generator. It does not test the VMS.

## Lexicon limits and boundary

The current lexicons are finite surface lexicons. LLCT is early medieval legal
charter prose. Old Italian is Dante's edited *Comedy*. They do not cover all
historical Latin, all Italian, or the unknown VMS genre.

They use normalized surface forms. They do not add lemmas, variants, names,
abbreviations, or repaired words. A finite lexicon can produce chance hits.
Homophony adds map freedom. These limits require known-cipher controls.

This document proposes a future VMS study. It does not authorize changes to the
current lexical pilot. Do not implement the VMS cells or inferential tests until
methodological review approves the frozen near-term controls.
