# Physical map audit

This audit checks physical bifolia and foldout leaves in the ambiguous folio ranges.
It uses Yale records and René Zandbergen's codicological pages.
It does not infer physical identity from drawing similarity.

A **folio** is a numbered leaf. A **bifolio** is one sheet folded once.
A **foldout** is a leaf or bifolio with extra folds. A **panel** is one folded surface.
A Yale canvas is an image capture. It is not a physical-leaf identifier.

## IVTFF bifolio metadata

The IVTFF specification defines page variable `$Q` as the quire number.
It encodes quires 1 through 20 as `A` through `T`, with `P` and `R` unused.
It defines `$B` as the bifolio number within a quire, counted outside to inside.
Therefore, `(Q,B)` is a direct bifolio key in these source page headers.

The two original input files agree for all ten audited components:

| Q/B | Quire | Folios | IT2a page headers | ZL3b page headers | Result |
| --- | ---: | --- | ---: | ---: | --- |
| `I/1` | 9 | `67,68` | 10 | 10 | Match |
| `J/1` | 10 | `69,70` | 6 | 6 | Match |
| `K/1` | 11 | `71,72` | 8 | 8 | Match |
| `N/1` | 14 | `85,86` | 6 | 7 | Match; ZL3b includes `fRos` |
| `O/1` | 15 | `87,90` | 6 | 6 | Match |
| `O/2` | 15 | `88,89` | 6 | 6 | Match |
| `Q/1` | 17 | `93,96` | 4 | 4 | Match |
| `Q/2` | 17 | `94,95` | 6 | 6 | Match |
| `S/1` | 19 | `99,102` | 6 | 6 | Match |
| `S/2` | 19 | `100,101` | 4 | 4 | Match |

The files cover all 20 numeric folios in this scope.
They contain 62 IT2a page headers and 63 ZL3b page headers.
They contain 1,505 and 1,669 selected locus records, respectively.
Missing scoped folios, missing Q/B metadata, and Q/B mismatches are all zero.
The ZL3b `fRos` header has `Q=N` and `B=1`, so it belongs with `85/86`.

This metadata removes the need for a Q-only fallback for the ten audited components.
A Q-only split is still conservative when the full normal-bifolio map is unavailable.
The source files contain 18 Q groups but 52 Q/B groups.
Q-only grouping merges two physical bifolios in each of Quires 15, 17, and 19.
Use Q+B when the source page metadata is available.
Use whole-Q holding only as an explicit conservative fallback.

The full metadata-only map is in [bifolio_manifest.json](../../data/bifolio_manifest.json).
It contains all 52 Q/B groups and 227 ZL3b page headers.

Source references:

- [IVTFF specification, page variables](https://voynich.nu/software/ivtt/IVTFF_format.pdf)
- `data/raw/IT2a-n.txt`, original IVTFF source, version 2a
- `data/raw/ZL3b-n.txt`, original IVTFF source, version 3b

## Supported physical components

The source diagrams support these components:

| Folios | Physical structure | Foldout detail | Support |
| --- | --- | --- | --- |
| `67, 68` | One bifolio | Both folios fold out. Folio 67 has two panels. Folio 68 has three panels. | High |
| `69, 70` | One bifolio | Folio 70 folds out. | High |
| `71, 72` | One bifolio | Folio 72 folds out to three panels. | High |
| `85, 86` | One six-panel bifolio (folding leaf) | The six panels include the Rosettes drawing across f85v and f86r. | High |
| `87, 90` | One bifolio | Folio 90 folds out. | High |
| `88, 89` | One bifolio | Folio 89 folds out. | High |
| `93, 96` | One bifolio | No foldout is reported for these two folios. | High |
| `94, 95` | One bifolio | Folio 95 folds out. | High |
| `99, 102` | One bifolio | Folio 102 folds out. | High |
| `100, 101` | One bifolio | Folio 101 has a fold. Its recto and verso designs cross the fold. | High |

The folio pairs for Quires 15, 17, and 19 come from the source schemata.
They are not guesses based on adjacent page images.

## Audit of the current candidate sets

The earlier conservative candidates need this physical interpretation:

| Existing candidate | Exact physical map | Result |
| --- | --- | --- |
| `{69,70}` | `{69,70}` | Keep. |
| `{71,72}` | `{71,72}` | Keep. |
| `{85,86}` | `{85,86}` | Keep. This is the Yale sextuple-folio folding leaf. |
| `{88,89,90}` | `{88,89}` and `{87,90}` | Split for an exact physical map. The old set is a conservative leakage holdout, not one sheet. |
| `{94,95}` | `{94,95}` | Keep. |
| `{100,101,102}` | `{100,101}` and `{99,102}` | Split for an exact physical map. The old set is a conservative leakage holdout, not one sheet. |

Two more physical unions are required in this scope: `{67,68}` and `{93,96}`.
The audit also records `{87,90}` and `{99,102}` because they are the conjugate leaves that the wide images can hide.

Do not change model code from this audit alone. The existing broad unions can remain as conservative controls.
Label them as conservative controls if they remain.

## Evidence for each quire

### Quire 9: folios 67 and 68

Zandbergen's quire page states that Quire 9 has one bifolio composed of folios 67 and 68.
It states that both folios fold out. The page gives two panels for f67 and three panels for f68.
Its [quire schema](https://voynich.nu/q09/schema09.gif) shows the folded surfaces.

Yale's IIIF manifest has separate captures for f67 and f68:

- [f67r, canvas 1006194](https://collections.library.yale.edu/catalog/2002046?child_oid=1006194)
- [f67v, canvas 1006195](https://collections.library.yale.edu/catalog/2002046?child_oid=1006195)
- [f68r, canvas 1006196](https://collections.library.yale.edu/catalog/2002046?child_oid=1006196)
- [f68v, canvas 1006197](https://collections.library.yale.edu/catalog/2002046?child_oid=1006197)

These separate Yale captures do not remove the source's bifolio relation.

### Quire 10: folios 69 and 70

Zandbergen's quire page states that Quire 10 has one bifolio composed of folios 69 and 70.
It identifies f70 as the foldout folio. The [quire schema](https://voynich.nu/q10/schema10.gif) places f69 at the binding. It places f70 to the right.

Yale canvas `1006199` is labelled `69v and 70r`.
Yale canvases `1006200` and `1006201` are parts of `70v`.

- [Yale composite canvas 1006199](https://collections.library.yale.edu/catalog/2002046?child_oid=1006199)
- [Yale canvas 1006200](https://collections.library.yale.edu/catalog/2002046?child_oid=1006200)
- [Yale canvas 1006201](https://collections.library.yale.edu/catalog/2002046?child_oid=1006201)

### Quire 11: folios 71 and 72

Zandbergen's quire page states that Quire 11 has one bifolio composed of folios 71 and 72.
It identifies f72 as a triple-foldout folio. The [quire schema](https://voynich.nu/q11/schema11.gif) places f71 at the binding. It places f72 to the right.

Yale canvas `1006203` is labelled `71v and 72r`.
Yale canvases `1006204` and `1006205` are parts of `72v`.

- [Yale composite canvas 1006203](https://collections.library.yale.edu/catalog/2002046?child_oid=1006203)
- [Yale canvas 1006204](https://collections.library.yale.edu/catalog/2002046?child_oid=1006204)
- [Yale canvas 1006205](https://collections.library.yale.edu/catalog/2002046?child_oid=1006205)

### Quire 14: folios 85 and 86

Yale's detailed catalog calls f85r–f86v one sextuple-folio folding leaf.
It lists Quire XIV as a sextuple fold-out.

The IVTFF specification gives the physical interpretation.
It calls f85 and f86 one bifolio with a horizontal fold and two vertical folds.
It describes six panels. The Rosettes drawing covers f85 verso and f86 recto.

- [Yale catalog, physical description and collation](https://pre1600ms.beinecke.library.yale.edu/docs/pre1600.ms408.htm)
- [IVTFF specification, section 4.2](https://voynich.nu/software/ivtt/IVTFF_format.pdf)
- [Quire 14 schema](https://voynich.nu/q14/schema14.gif)
- [Yale canvas 1006228](https://collections.library.yale.edu/catalog/2002046?child_oid=1006228)
- [Yale canvas 1006229](https://collections.library.yale.edu/catalog/2002046?child_oid=1006229)
- [Yale canvas 1006230](https://collections.library.yale.edu/catalog/2002046?child_oid=1006230)
- [Yale Rosettes canvas 1006231](https://collections.library.yale.edu/catalog/2002046?child_oid=1006231)

The Yale manifest labels the first three captures as parts of the `85-86 foldout`.
It labels canvas `1006231` as `85v and 86r (foldout)`.
The `fRos` name is a page alias for this drawing. It is not a new physical leaf.

### Quire 15: folios 87 through 90

Zandbergen's quire page states that the quire contains folios 87 through 90.
It identifies folios 89 and 90 as foldout folios.
The [quire schema](https://voynich.nu/q15/schema15.gif) shows two bifolios:
`87/90` is the lower sheet, and `88/89` is the upper sheet.

This distinction matters for Yale canvas `1006235`.
That canvas is labelled `89v (part) and 90r`.
It is an opened spread across the two bifolios.
It does not make f89 and f90 one sheet.

- [Yale canvas 1006233, `88v and 89r`](https://collections.library.yale.edu/catalog/2002046?child_oid=1006233)
- [Yale canvas 1006235, `89v (part) and 90r`](https://collections.library.yale.edu/catalog/2002046?child_oid=1006235)
- [Quire 15 page](https://voynich.nu/q15/index.html)
- [Quire 15 schema](https://voynich.nu/q15/schema15.gif)

The exact physical components are therefore `{88,89}` and `{87,90}`.
The current `{88,89,90}` component is too broad for a physical-sheet claim.

### Quire 17: folios 93 through 96

Zandbergen's quire page states that Quire 17 contains folios 93 through 96.
It identifies f95 as the foldout folio.
The [quire schema](https://voynich.nu/q17/schema17.gif) shows two bifolios:
`94/95` is the upper sheet, and `93/96` is the lower sheet.

Yale canvas `1006241` is labelled `94v and 95r`.
It shows a cross-number side of the `{94,95}` bifolio.

- [Yale canvas 1006241](https://collections.library.yale.edu/catalog/2002046?child_oid=1006241)
- [Yale canvas 1006242](https://collections.library.yale.edu/catalog/2002046?child_oid=1006242)
- [Yale canvas 1006243](https://collections.library.yale.edu/catalog/2002046?child_oid=1006243)
- [Quire 17 page](https://voynich.nu/q17/index.html)
- [Quire 17 schema](https://voynich.nu/q17/schema17.gif)

The exact physical components are `{94,95}` and `{93,96}`.

### Quire 19: folios 99 through 102

Zandbergen's quire page states that Quire 19 contains folios 99 through 102.
It identifies f101 and f102 as foldout folios.
It treats f101 as one design on each side, because text crosses its fold.
The [quire schema](https://voynich.nu/q19/schema19.gif) shows two bifolios:
`100/101` is the upper sheet, and `99/102` is the lower sheet.

This distinction matters for Yale canvas `1006251`.
That canvas is labelled `101v (part) and 102r`.
It is an opened spread across the two bifolios.
It does not make f101 and f102 one sheet.

- [Yale canvas 1006249, `100v and 101r`](https://collections.library.yale.edu/catalog/2002046?child_oid=1006249)
- [Yale canvas 1006251, `101v (part) and 102r`](https://collections.library.yale.edu/catalog/2002046?child_oid=1006251)
- [Yale canvas 1006250](https://collections.library.yale.edu/catalog/2002046?child_oid=1006250)
- [Yale canvas 1006252](https://collections.library.yale.edu/catalog/2002046?child_oid=1006252)
- [Yale canvas 1006253](https://collections.library.yale.edu/catalog/2002046?child_oid=1006253)
- [Quire 19 page](https://voynich.nu/q19/index.html)
- [Quire 19 schema](https://voynich.nu/q19/schema19.gif)

The exact physical components are `{100,101}` and `{99,102}`.
The current `{100,101,102}` component is too broad for a physical-sheet claim.

## Image relation rules

Use these rules when mapping Yale canvases to physical components:

1. Treat a source schema or explicit bifolio statement as physical evidence.
2. Treat a Yale label such as `69v and 70r` as a captured opened side.
3. Do not treat every wide canvas as one sheet.
4. Do not join folios only because they are adjacent in an opened image.
5. Keep every panel of one folded folio with its numeric folio.
6. Keep `fRos` with the `{85,86}` component.

The Yale catalog warns that foldout foliation is not always consistent.
The IVTFF specification also says that a fold crease can cross continuous writing.
Panel names therefore describe the image layout. They do not provide a text reading.

## Exact correction proposal

For a physical-sheet map in this scope, use these numeric components:

```text
67 ~ 68
69 ~ 70
71 ~ 72
85 ~ 86
87 ~ 90
88 ~ 89
93 ~ 96
94 ~ 95
99 ~ 102
100 ~ 101
```

Keep `fRos` as an alias to the `85/86` component.
Do not merge `{88,89}` with `{87,90}`.
Do not merge `{100,101}` with `{99,102}`.

This proposal does not change source code.
It gives the integration step a checked physical map.

## Bounded unknowns and next check

This audit does not map every normal bifolio in the manuscript.
It only resolves the foldout ranges that affect the current split review.
The Yale catalog gives quire-level counts and warns about inconsistent foliation.
It does not replace a complete conservation diagram.

The next manual annotation should mark the binding edge, every fold crease, and each folio number on full-resolution Yale images.
Then compare the marks with the seven source schemata.
Run one split check that asserts no exact component appears in more than one partition.

A picture or drawing similarity is not a reading of the manuscript text.
Use the source text records for transliteration and use this map only for physical grouping.

## Primary sources

- [Yale Beinecke MS 408 detailed catalog](https://pre1600ms.beinecke.library.yale.edu/docs/pre1600.ms408.htm)
- [Yale IIIF manifest for MS 408](https://collections.library.yale.edu/manifests/2002046)
- [Zandbergen, Description of the MS](https://voynich.nu/descr.html)
- [Zandbergen, Origin and folio/quire numbers](https://voynich.nu/extra/sp_origin.html)
- [Zandbergen, visual layout](https://voynich.nu/layout.html)
- [IVTFF format specification](https://voynich.nu/software/ivtt/IVTFF_format.pdf)
- [Zandbergen Quire 9](https://voynich.nu/q09/index.html), [Quire 10](https://voynich.nu/q10/index.html), [Quire 11](https://voynich.nu/q11/index.html)
- [Zandbergen Quire 14](https://voynich.nu/q14/index.html), [Quire 15](https://voynich.nu/q15/index.html), [Quire 17](https://voynich.nu/q17/index.html), [Quire 19](https://voynich.nu/q19/index.html)
