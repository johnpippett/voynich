# Physical foldout groups

## Decision

Yale directly supports one physical folded group that crosses numeric folios `85` and `86`.

The detailed Yale catalog describes folios `85r–86v` as one “sextuple-folio folding leaf”. The IIIF manifest also labels four image captures as parts of the same `85-86 foldout`. Keep every surface from folios `85` and `86` in one held-out group.

The implementation now applies the conservative union groups in this note. It uses the smallest numeric folio in each component as the representative. It maps the composite `fRos` alias to representative `85`.

This is a folded leaf. It is not a claim that folios `85` and `86` form a normal bifolium or a pair of conjugate leaves. The Yale catalog uses “bifolium” for a different structure at missing folios `109–110`. It uses “conjugate leaves” for the stubs after missing folio `74`.

## Terms for the split

- A **folio** is the catalogued leaf number. `r` and `v` identify its recto and verso.
- A **leaf** is one physical parchment sheet. A leaf can have several folded panels.
- A **panel** is a surface in a folded leaf. One Yale canvas can show one panel, several panels, or a partial panel.
- A **bifolium** is a sheet folded once to form two leaves. It is not a synonym for every foldout.
- A **quire** is a gathering of leaves. Quire labels such as `XIV` and `XV` do not identify a single physical leaf.

The model should group at the physical-leaf or folded-leaf level. It should not group by Yale canvas ID. Several canvases can show parts of one physical foldout.

## Primary codicological evidence

Yale's detailed catalog states that the manuscript has five double-folio, three triple-folio, one quadruple-folio, and one sextuple-folio folding leaves. It warns that collation is difficult because foldout leaves are not always foliated consistently.

The same catalog lists `XIV` as a sextuple fold-out. It lists `XV` as one triple and one double fold-out. It lists `XVI` as one double fold-out and `XVII` as two double fold-outs. It does not provide a complete number-to-leaf lookup table. Treat the quire sequence as context, not as a new group identifier.

For Part IV, the catalog states `ff. 85r-86v`. It then calls this item “This sextuple-folio folding leaf”. This directly supports the `85/86` group. The manifest provides the image-level evidence below.

## ZL composite alias evidence

The Zandbergen-Landini IVTFF source defines `<fRos>` at header lines `5253–5258`. Its header calls the record part of a “6-page 9-circle composite”. The page and circle map lists pages `85v` and `86r`.

This source supports the `fRos` alias to representative `85` after the `85/86` union. It does not make `fRos` a new physical leaf. The raw source remains an input artifact and is not distributed by this repository.

## Manifest evidence

The source is the [Yale IIIF manifest](https://collections.library.yale.edu/manifests/2002046). The labels below are the labels in its `items` array. A catalog link uses Yale object `2002046` and the child image ID.

| Conservative folio set | Yale manifest evidence | Evidence level |
| --- | --- | --- |
| `{69, 70}` | Canvas `1006199` is labelled `69v and 70r`. Canvases `1006200` and `1006201` are both labelled `70v (part)`. [Catalog image](https://collections.library.yale.edu/catalog/2002046?child_oid=1006199) | Candidate cross-number foldout relation. The combined image has several fold lines. |
| `{71, 72}` | Canvas `1006203` is labelled `71v and 72r`. Canvases `1006204` and `1006205` are both labelled `72v (part)`. [Catalog image](https://collections.library.yale.edu/catalog/2002046?child_oid=1006203) | Candidate cross-number foldout relation. The combined image has several fold lines. |
| `{85, 86}` | Canvases `1006228`, `1006229`, and `1006230` say `part of 85-86 foldout`. Canvas `1006231` is labelled `85v and 86r (foldout)`. [Catalog image](https://collections.library.yale.edu/catalog/2002046?child_oid=1006231) | Direct. The manifest and the detailed catalog identify the same folded leaf. |
| `{88, 89, 90}` | Canvas `1006233` is labelled `88v and 89r`. Canvas `1006235` is labelled `89v (part) and 90r`. Canvas `1006234` is `89v (part)`, and canvas `1006237` is `90v (part)`. [First combined image](https://collections.library.yale.edu/catalog/2002046?child_oid=1006233) | Conservative transitive group. Two cross-number relations share folio `89`. The manifest shows multi-panel captures, but it does not state one physical-leaf ID. |
| `{94, 95}` | Canvas `1006241` is labelled `94v and 95r`. Canvas `1006242` is labelled `95v (part)`. [Catalog image](https://collections.library.yale.edu/catalog/2002046?child_oid=1006241) | Candidate cross-number foldout relation. It also fits Yale's `XVI` entry for one double fold-out. |
| `{100, 101, 102}` | Canvas `1006249` is labelled `100v and 101r`. Canvas `1006251` is labelled `101v (part) and 102r`. Canvases `1006250`, `1006252`, and `1006253` are partial views of `101v` or `102v`. [First combined image](https://collections.library.yale.edu/catalog/2002046?child_oid=1006249) | Conservative transitive group. Two cross-number relations share folio `101`. It fits Yale's `XVII` entry for two double fold-outs, but the catalog does not map each quire entry to folio numbers. |

The wide canvases are photographs of opened material. A wide canvas alone does not prove that two numbered surfaces form one physical leaf. It can show facing leaves or a partial capture. The `85/86` labels remove this uncertainty for that group. Use the other sets as conservative overrides until a panel and leaf map is frozen.

## Implemented grouping

The implementation uses the following relations as a versioned, source-backed override to the numeric folio split:

```text
69 ~ 70
71 ~ 72
85 ~ 86
88 ~ 89
89 ~ 90
94 ~ 95
100 ~ 101
101 ~ 102
```

Build connected components from these relations. This yields the sets in the table. Let the integration step assign versioned group IDs. This note does not invent IDs.

Keep recto and verso surfaces with the same numeric folio in the same component. Keep all partial and full canvases for a listed folio in that component. Do not treat repeated canvases, such as a full `90r` view after a partial foldout capture, as new physical leaves.

The current configuration is `conservative-foldout-groups-v2`. Its representatives are `69`, `71`, `85`, `88`, `94`, and `100`. The `fRos` alias maps to `85`. The configuration records `85/86` as confirmed and records the other components as conservative candidates.

## What remains uncertain

The Yale catalog gives foldout counts and quire order. It does not provide a complete physical-sheet diagram for every number. Therefore:

- `{85, 86}` is directly established as one sextuple-folio folded leaf.
- `{69, 70}`, `{71, 72}`, `{94, 95}` are supported as cross-number foldout candidates by combined manifest labels and image geometry.
- `{88, 89, 90}` and `{100, 101, 102}` are conservative transitive sets. The manifest links the pairs, but the source does not expose a single physical-leaf identifier.
- Wide single-number canvases, such as `67r`, `67v`, `68r`, and `68v`, do not create a cross-number override. Do not infer one from image width alone.

The implemented candidate unions are leakage controls. They do not prove physical identity for every candidate component. A complete physical-sheet diagram remains required before confirmatory claims.

Before a confirmatory run, inspect the full-resolution Yale images. Record fold lines, panel boundaries, foliation marks, and visible sewing or binding evidence. Preserve the Yale labels. Do not replace them with semantic or historical interpretations.

## Primary sources

1. Yale Digital Collections, [Beinecke MS 408 IIIF manifest](https://collections.library.yale.edu/manifests/2002046).
2. Yale Digital Collections, [Beinecke MS 408 detailed catalog](https://pre1600ms.beinecke.library.yale.edu/docs/pre1600.ms408.htm), especially its physical description, collation, and Part IV entry.
3. Local Zandbergen-Landini IVTFF source, `ZL3b-n.txt`, `<fRos>` header lines `5253–5258`. The raw source is an input artifact and is not distributed here.
4. Yale Library, [The Beinecke Cipher (Voynich) Manuscript](https://beinecke.library.yale.edu/beinecke/collections/beinecke-cipher-voynich-manuscript), which directs researchers to the complete digital images and detailed foliation.
