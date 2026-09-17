# Anchor audit: labels, marginalia, and diagram constraints

Research status: 2026-09-17

This audit records evidence that can constrain a future decoder of the Voynich
manuscript. It does not assign a language, translate a token, or claim a
solution. It treats an EVA token as a shape transcription. It treats an
external anchor as a repeatable relation between a locus and a visible page
layout or catalogue description.

The audit uses the Yale catalogue and IIIF record, current folio descriptions
at Voynich.nu, and the ZL3b and IT2a IVTFF transcription files. These sources
provide different evidence types, but the two transcription files still derive
from the same manuscript. Agreement between them supports transcription
stability. It does not provide two physical observations. No full text or
image is reproduced here.

## Candidate summary

| # | Candidate and exact folio/locus | Use or hold |
|---|---|---|
| 1 | Later-hand central annotations on `f70v2`, `f70v1`, `f71r`, `f71v`, `f72r1`, `f72r2`, `f72r3`, `f72v3`, `f72v2`, `f72v1`, `f73r`, and `f73v`. | Use for panel order and annotation-layer checks. Hold as plaintext. |
| 2 | Repeated `Lz` labels: `otaly` at `f70v2.15,&Lz`, `f72v3.31,&Lz`, `f73r.6,@Lz`; `okeody` at `f72v2.15,&Lz`, `f73r.7,&Lz`, `f73v.6,@Lz`; `okam` at `f72r2.25,&Lz`, `f72v3.4,&Lz`. | Use as an equality baseline only for a declared context-independent or same-state mapping. Permit fixed context- or state-dependent mappings. Hold meaning. |
| 3 | Zodiac `Lz` inventories on `f70v2`, `f70v1`, `f71r`, `f71v`, `f72r1`, `f72r2`, `f72r3`, `f72v3`, `f72v2`, `f72v1`, and `f73r`. | Use for corpus partition and label segmentation. Hold sign names as semantics. |
| 4 | Mixed-script external locus `<f116v.1,@Lx>`. | Hold outside the primary decoder until hand and layer are resolved. |
| 5 | Later ownership and alphabet-like material on `f1r`. | Reject as a plaintext anchor. Keep for provenance controls. |
| 6 | Possible colour or Latin-script marks on `f1v` and `f4r`. | Hold for ink and pigment analysis only. |
| 7 | Overwritten or disputed marginal writing near the figure on `f66r`. | Reject as a plaintext anchor. Keep as a negative control. |

## Numbered evidence and predictions

### 1. Later-hand central annotations

Voynich.nu records a central label in a later hand on the listed zodiac panels.
The Yale catalogue places f67r–73v in the astronomical and astrological
diagram section. The panel position is a strong annotation anchor. It does not
show that the form is part of the main script, or that a sign name describes
nearby writing. The source language and readings remain debated.

Sources: [Voynich.nu writing-layer record](https://voynich.nu/writing.html),
[quire 10](https://www.voynich.nu/q10/index.html),
[quire 11](https://www.voynich.nu/q11/index.html),
[quire 12](https://www.voynich.nu/q12/index.html), and the
[Yale catalogue](https://pre1600ms.beinecke.library.yale.edu/docs/pre1600.ms408.HTM).

Prediction: image review should find a central later-hand annotation on each
listed panel. No f74 panel survives. If the marks share ink and hand with the
main text, revise the layer decision.

### 2. Repeated labels at zodiac loci

ZL3b and IT2a record the same EVA strings at the same listed `Lz` loci. The
folio descriptions place these labels next to diagram figures or stars. This
supports observed glyph-string equality and label segmentation. It does not
support a translation.

The equality constraint has a defined scope. A decoder must preserve the
equality only when it declares a context-independent mapping, or the same
declared context and state, before testing. A fixed contextual, positional, or
key-state mapping may assign different outputs to the same glyph string. Such
a rule must be explicit, finite, and tested on held-out loci. The `@` and `&`
markers are locus metadata, not token content.

Alternatives include a shared transcription error, a glyph distinction lost in
the encoding, a repeated label formula, or a context-bound token. Image review
can reject any equality class whose glyphs differ.

Sources: [ZL3b IVTFF](https://www.voynich.nu/data/ZL3b-n.txt),
[IT2a IVTFF](https://www.voynich.nu/data/IT2a-n.txt),
[quire 10](https://www.voynich.nu/q10/index.html),
[quire 11](https://www.voynich.nu/q11/index.html), and
[quire 12](https://www.voynich.nu/q12/index.html).

Prediction: each declared decoder family should state whether these repeated
inputs share state. The family must then predict the listed loci without adding
folio-specific exceptions.

### 3. Label class and count

The folio descriptions distinguish figure or star labels from central
annotations and from circle writing. Examples include 29 figure labels plus a
central star label on `f70v2`, 15 labels on `f71r`, 29 on `f72r2`, and 30 on
`f72r3`. Counts depend on segmentation of touching or damaged writing. Sign
names can also be tentative.

Sources: [Voynich.nu transliteration method](https://www.voynich.nu/transcr.html),
[quire 10](https://www.voynich.nu/q10/index.html),
[quire 11](https://www.voynich.nu/q11/index.html),
[quire 12](https://www.voynich.nu/q12/index.html), and the
[Yale catalogue](https://pre1600ms.beinecke.library.yale.edu/docs/pre1600.ms408.HTM).

Prediction: image-based re-transcription should reproduce each label-set
boundary and documented count, with exceptions recorded. Keep `Lz`, `Cc`, `R`,
and body-text loci separate.

### 4. Mixed-script writing on `f116v`

The `Lx` locus `<f116v.1,@Lx>` records one external-writing item among four
lines. The folio description reports apparent Latin, German, and Voynich
writing in a non-standard layout. The item may be original, later, overwritten,
or a pen trial. Apparent language forms are not translations.

Sources: [quire 20](https://www.voynich.nu/q20/index.html),
[ZL3b IVTFF](https://www.voynich.nu/data/ZL3b-n.txt),
[Voynich.nu transliteration method](https://www.voynich.nu/transcr.html), and the
[Yale catalogue](https://pre1600ms.beinecke.library.yale.edu/docs/pre1600.ms408.HTM).

Prediction: palaeographic and ink-layer review should classify the item as a
separate hand or explain why it belongs to the main script. Matching hand and
ink would remove the exclusion.

### 5. Later ownership material on `f1r`

The right-margin alphabet-like columns and bottom ownership inscription are
later-owner material. They provide provenance evidence, not a main-script
reading. The columns could be an owner alphabet, a decryption attempt, or a
later copy.

Sources: [quire 1](https://www.voynich.nu/q01/index.html),
[Yale IIIF manifest](https://collections.library.yale.edu/manifests/2002046), and
[Voynich.nu ownership record](https://voynich.nu/extra/sinapius_books.html).

Prediction: image review should place the marks in a later layer or hand and
exclude them from body and label corpora. Original-ink continuity would require
a new layer decision.

### 6. Possible colour-related marks

The marks on `f1v` and `f4r` occupy paint or drawing areas rather than stable
text lines. Voynich.nu treats them as possible colour annotations and records
uncertain readings. They may be production notes, later additions, accidental
strokes, or incorrect readings.

Sources: [Voynich.nu writing-layer record](https://voynich.nu/writing.html),
[origin discussion](https://voynich.nu/origin.html), and [quire 1](https://www.voynich.nu/q01/index.html).

Prediction: multispectral or high-resolution review should establish whether
each mark lies under, over, or beside the paint and whether it shares the main
writing hand.

### 7. Marginal writing on `f66r`

The page has a marginal figure and a separate label inventory. The source
records overwritten and disputed readings near the figure. The writing may be
a later note, a pen trial, pseudo-German, or damaged Voynich text.

Sources: [quire 8](https://www.voynich.nu/q08/index.html) and the
[origin discussion](https://voynich.nu/origin.html).

Prediction: require a stable reading and layer assignment from direct image and
palaeographic review before any decoder uses this material.

## Boundary notes

The Yale catalogue describes f67r–73v as diagram pages with zodiac signs and
circles. The folio pages at Voynich.nu give more detailed label and figure
descriptions. These descriptions identify page regions. They do not prove that
a figure name or zodiac sign is the meaning of nearby writing.

The `Lz`, `Cc`, `R`, and `Lx` markers come from the IVTFF transcription method.
They describe locus types. They do not identify letters, words, or a language.
Keep body text, labels, circular writing, radial writing, and external writing
as separate strata in any decoder evaluation.

The description of `f73v` contains an internal catalogue mismatch: its image
description mentions a figure with a crossbow and a central December annotation,
while a later tentative-identification line repeats the Scorpius label. Use
“zodiac panel” for this audit. Recheck the image before using any sign name as
metadata.

## Recommended constraints for a future decoder

1. Preserve the observed glyph-string equality at repeated `Lz` loci.
   Require equal plaintext only for a declared context-independent or same-state decoder.
   Test transcription equality and segmentation before testing language models or translations.
2. Keep later-hand month annotations outside the primary script. Use their
   positions only to test panel order and annotation layers.
3. Keep `Lz`, `Cc`, `R`, `Lx`, and body-text loci separate. Do not merge them
   because they occur on the same page.
4. Require a fixed reading method, an image-reproducible locus, and a held-out
   check before treating any marginal mark as a plaintext anchor.

These constraints support structure tests. They do not identify a language or
provide a plaintext translation.

## Later check: plant labels and repeated drawings

This check tested exact label reuse. It did not assign a plant name or a language.
The question was whether a recorded label also occurs beside its reported large-drawing counterpart.
An exact repeat would support recurrence. It would not establish a name or meaning.

The [quire 19 record](https://voynich.nu/q19/index.html) links fragment 212 on f102r2 with f18v, and fragment 213 with f23r.
The [quire 3 record](https://voynich.nu/q03/index.html) gives the corresponding large-drawing descriptions.
These descriptions come from one provider. They are not independent expert confirmations.
The two large drawings share a bifolio; the two labels share a page.

The [interlinear record](https://www.voynich.nu/q19/f102r2_tr.txt) places labels above both bottom-row root fragments.
Current ZL and IT records agree: `f102r2.21,@Lf` is `koldarod`, and `f102r2.22,@Lf` is `odalydary`.
The `Lf` code marks a plant-fragment label. It does not establish its meaning.

AI review of [Yale region 212](https://collections.library.yale.edu/iiif/2/1006251/5700,2450,900,700/full/0/default.jpg) supports the first attachment.
Review of [region 213](https://collections.library.yale.edu/iiif/2/1006251/6600,2450,1000,800/full/0/default.jpg) supports the second attachment.
The independent image reader could not verify either complete glyph string.
Both labels therefore failed the original image-verification condition.

Before any recurrence query, the plan added a separate check conditional on the two published readings.
It kept both target pages and exact strings fixed. It did not convert image uncertainty into a verified reading.
The corpus was previously inspected. This was an exploratory check, not blind validation.

Use the pinned ZL3b and IT2a files with the existing IVTFF parser in split mode.
Accept P-kind lines with no rejected tokens, uncertain spaces, drawing interruptions, or empty token lists.
Remove IVTFF free comments before checking commas for uncertain spacing.
Keep one-word lines. Compare complete tokens exactly.
Do not remove affixes, substitute signs, join tokens, or search for partial matches.

| Source | Recorded label | Target | Accepted lines / all P-lines | Accepted tokens | Exact matches |
| --- | --- | --- | --- | --- | --- |
| IT | `koldarod` | f18v | 10 / 10 | 71 | 0 |
| IT | `odalydary` | f23r | 8 / 11 | 74 | 0 |
| ZL | `koldarod` | f18v | 6 / 10 | 40 | 0 |
| ZL | `odalydary` | f23r | 1 / 11 | 11 | 0 |

Each specificity check covered 128 other provider-classified herbal pages, using the same line filter.
IT had accepted text on 123 of those pages; ZL had accepted text on 111.
Neither string occurred in that accepted text.
Complete page coverage was limited: IT had 30 pages for the f18v comparison and 31 for f23r; ZL had none.
These counts do not prove absence from excluded text.

The IT result excludes verbatim reuse of `koldarod` within the complete accepted paragraph-line set on f18v.
The other three target checks have incomplete coverage.
None verifies the uncertain label images or rejects related content, inflection, aliases, or contextual encoding.
This exact-reuse branch supplies no lexical anchor and is stopped.
No whole-page similarity test or spelling adjustment followed the result.

A separate AI task confirmed the counts with another implementation of the filter and exact search.
It reused the existing parser. This was not an independent transcription or external scholarly review.
The local result record has SHA-256 `e3e55d5c1ffd8a6042ea13b36e38d696208144e480a3260cf9432a39f157422b`.
The plan, including its pre-query amendment, has SHA-256 `8118917be677ded133c90281bf6ba5de504f6cce33fd4812663e3748a757f79b`.

## Ring and margin-column comparison

This check asked whether the f66r margin column repeats the f57v ring sequence twice.
The fixed comparison permitted only a starting offset and one reading-direction reversal.
It required sign boundaries before comparison. It permitted no new sign groups or partial matches.

The [quire 8 description](https://voynich.nu/q08/index.html) reports four repetitions of 17 characters on f57v and 34 margin entries on f66r.
The [f57v interlinear record](https://voynich.nu/q08/f057v_tr.txt) identifies the second ring, read clockwise from the northwest start.
The [f66r interlinear record](https://voynich.nu/q08/f066r_tr.txt) permits single characters or ligatures in its middle column.
The pages belong to the same bifolio. They are not independent validation samples.

The current ring locus is `f57v.3,+Cc`.
ZL records 68 fields; IT records 69 because its final segment is split into `r` and `n`.
Neither count establishes how many individual signs the manuscript contains.
The column has 34 loci, from `f66r.16,@L0` through `f66r.49,+L0`.
Both sources record its eleventh entry, `f66r.26,+L0`, as `air`.

AI inspection of the [f57v image](https://collections.library.yale.edu/iiif/2/1006187/full/full/0/default.jpg) supports the ring layout.
The [f66r column image](https://collections.library.yale.edu/iiif/2/1006192/240,290,200,2400/full/0/default.jpg) supports the vertical entry order.
It also shows that the eleventh entry is a compound or word-like group.
These inspections do not establish 68 and 34 individual sign units.

The required unit boundaries remain unresolved. The comparison stopped before template matching.
No entries were merged, removed, or assigned new meanings.
This result supplies no order anchor and does not reject related content or a shared writing system.
The local plan, source extraction, image hashes, and gate record remain in `results/ring-column-order-v1/`.

## Drawing-gap pairing feasibility

This check asked whether physical left/right pairings across drawings carry an endpoint association.
The null permits preceding final units to move between comparable gaps while each following initial unit stays fixed.
It does not assume linguistic adjacency. A positive association would not identify a cipher, language, or continuous writing state.

The [2024 drawing study](https://arxiv.org/abs/2404.13069v1) compares token populations before and after drawings.
It does not test the joint relation between the two sides of each gap.
The [IVTFF specification](https://voynich.nu/software/ivtt/IVTFF_format.pdf) distinguishes aligned drawing interruptions, `<->`, from vertically misaligned interruptions, `<~>`.

The plan used the existing test groups and the two pinned transcriptions.
It selected complete paragraph lines with exactly one internal `<->`, at least three words, and no ambiguous spacing or normalized sign forms.
Each line supplies the two words immediately beside the gap.
Matched cells hold folio, target position, last-word status, paragraph-start status, and both word lengths fixed.
A cell can contribute information only if both endpoint labels vary.

| Source | Unit representation | Eligible pairs | Matched cells | Variable cells | Variable targets | Groups with variable cells |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| ZL | Six visual compounds | 64 | 64 | 0 | 0 | 0 |
| IT | Six visual compounds | 132 | 127 | 0 | 0 | 0 |
| ZL | Raw EVA | 64 | 63 | 1 | 2 | 1 |
| IT | Raw EVA | 132 | 128 | 2 | 4 | 2 |

The primary representation has no variable matched cells in either source.
The permitted permutations therefore cannot change the fixed endpoint score.
The plan required at least 20 variable targets across three physical groups, without majority concentration in one group.
Both sources fail this coverage requirement. The raw-character sensitivity check cannot replace the primary result.
No model was fitted, no score was computed, and no image-based pairing test followed.
The branch is stopped without weaker matching, new groups, or changed filters.
This is a feasibility failure. It is not evidence for or against text continuity across drawings.
A separate AI task rebuilt the grouping and matching calculations and confirmed all counts.
It reused the source parser. This is not external scholarly validation.

The local record is `results/drawing-gap-pairing-v1/feasibility.json`.
Its SHA-256 is `bc29bcc65e725697434c7a690682de8a44208370d9aef14f8b17c3c65544909e`.
The plan and executed counting script remain beside that record.

## Published anagram decoder feasibility

This review asked whether a published substitution key could predict text outside its example.
A successful fixed-key prediction could support that key over a reading fitted separately to each passage.

The [Hauer and Kondrak paper](https://aclanthology.org/Q16-1006.pdf), sections 4 and 5, supplies a search method but no complete Voynich key.
The paper gives decoding results for ten pages. It does not give results from a test with the same fixed key on other pages.
The authors state that the outputs do not have correct syntax or consistent meaning.
They used spelling corrections and machine translation for their English example. It is not the raw decoder output.

The [code README](https://github.com/bmhauer/hk-langid/blob/e86ef47f79fef9a68438260436050a37e29d4c45/README) states that the experimental data is not included.
External language models, interpolation coefficients, and candidate-word tables are necessary program inputs.
The examined revision contains no Voynich key or experimental data files.

The original PDF image also has a wrapped Hebrew example and a font-mapping error in extracted text.
Neither word order nor spelling was changed to force a cipher alignment.
No key fit, consistency search, or manuscript experiment followed.
This branch is stopped. A new reconstruction would test a new model specification, not a recovered published key.
This source limit does not reject Hebrew or anagram ciphers.

## Partial sound key: opening-word coverage

[Bax (2014)](https://stephenbax.net/wp-content/uploads/2014/01/Voynich-a-provisional-partial-decoding-BAX.pdf) gives approximate sound values for fourteen signs or clusters.
His hellebore example checks a proposed spelling against a plant identity selected before the reading.
It does not independently identify the plant.

A separate AI task selected three other plant candidates from published image descriptions.
It did not use their Voynich words or Bax's key for selection.
The candidates were Ipomoea on f1v, Urtica on f25r, and Viola on f9v.
These identifications remain conditional on their sources; species and some broader identifications are disputed.
The sources are [Tucker and Talbert (2013)](https://umb.herbalgram.org/media/3jojkmox/issue100.pdf), sections Convolvulaceae, Urticaceae, and Violaceae,
and [Han (2011)](https://www.as.up.krakow.pl/jvs/library/2-7-2011-05-25/pansyvm.pdf) for f9v.

Before extraction, the plan fixed all three pages and the first token of the first P-kind record on each page.
The permitted EVA units were `k y d r m n sh s o a in iin e ee`.
This list comes from the text layer of Bax's Appendix 1; its glyph images were not independently checked.
The gate tested complete unit coverage before any comparison with plant names.

| Folio | Opening word in both sources | Complete coverage |
| --- | --- | --- |
| f1v | `kchsy` | No |
| f25r | `fcholdy` | No |
| f9v | `fochor` | No |

Each word contains EVA `c`; no permitted unit contains that character.
No exact segmentation with only the listed units can cover any of these words.
This character argument does not assume that EVA characters are linguistic letters.
A separate source-line check, without the corpus parser, confirmed all six entries.
This check is not an independent transcription or external expert review.

The first run retained the leading `<%>` marker in the first-field value and failed the acceptance check.
The corrected check removed only that structural marker and retained every target and sign value.
Both attempts remain in the local record.

The branch stopped before plant-name comparison, new sign assignments, or image-based transcription checks.
This is a coverage limit for the specified partial map, not a rejection of the broader proposal.
No plant name or plaintext was recovered.
The local records remain in `results/bax-partial-key-v1/`.
The corrected result has SHA-256 `00b128b7b294e7189aeb9b3c18192cff471cfebad897ee3173730aac85aeecd3`.

## Initial audit limits

The initial pass used catalogue descriptions, folio-layout records, and exact-locus
transcription lookup. It did not run manuscript statistics, fit a language
model, or reproduce manuscript images or full transcription text. The month
annotations, sign names, and figure descriptions remain metadata claims with
the source-specific uncertainty stated above.
