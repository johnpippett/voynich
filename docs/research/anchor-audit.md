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

## Audit limits

This pass used catalogue descriptions, folio-layout records, and exact-locus
transcription lookup. It did not run manuscript statistics, fit a language
model, or reproduce manuscript images or full transcription text. The month
annotations, sign names, and figure descriptions remain metadata claims with
the source-specific uncertainty stated above.
