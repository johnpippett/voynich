# Folio identification

## Result

The supplied image is **Beinecke MS 408, folio 84r**. Identification confidence is **high**.

The image shows the Arabic foliation `84` in the upper-right margin. The Yale IIIF manifest labels the matching page `84r`. The page image has the same distinct layout as the supplied image:

- a scalloped upper border;
- a long green-filled scene with small human figures;
- a large block of unidentified script below that scene;
- a second horizontal scene in the middle of the page;
- a rounded group of figures at lower left; and
- a winding blue and green line at the left margin.

The Yale image for `84v` has a different layout. It has blue circular scenes on the right side and does not match the supplied image. This recto/verso check uses the Yale images. It does not infer the side from the visible foliation alone.

## Yale identifiers

The Yale record is object `2002046`, **Cipher manuscript (Voynich manuscript)**, Beinecke MS 408.

| Item | Exact value |
| --- | --- |
| Yale IIIF manifest | `https://collections.library.yale.edu/manifests/2002046` |
| Manifest-listed canvas | `https://collections.library.yale.edu/manifests/oid/2002046/canvas/1006226` |
| Image label | `84r` |
| Yale image ID | `1006226` |
| Yale catalog page | `https://collections.library.yale.edu/catalog/2002046?child_oid=1006226` |
| IIIF Image API service | `https://collections.library.yale.edu/iiif/2/1006226` |
| Full Yale JPEG | `https://collections.library.yale.edu/iiif/2/1006226/full/full/0/default.jpg` |
| Image dimensions | `2753 × 3745` pixels |

The canvas URI and the image URI above come from the `84r` item in the manifest. The catalog child URL is the human-facing Yale link for the same image. The adjacent manifest item is `84v`, image ID `1006227`:

`https://collections.library.yale.edu/catalog/2002046?child_oid=1006227`

The item before `84r` is `83v`, image ID `1006225`. The next item is a foldout entry labelled `85r (part) (part of 85-86 foldout)`. This sequence supports the page order without treating the foldout as a normal single page.

## Source description and limits

Yale's detailed catalog places folios `75r–84v` in Part III. It calls this a “Biological” section and describes small-scale nude figures in fluids, tubes, and capsules. That is a catalog description of the drawings. It does not establish what the figures or the text mean.

The Yale record describes the writing as unidentified and undeciphered. The image can support observations about page layout, line placement, colours, figures, and marks. It cannot support a translation, a language assignment, an author, or a semantic reading. Visual resemblance to a familiar object is a hypothesis until a controlled transcription and comparison support it.

Do not call the text “read,” “translated,” or “decoded” from this page. Use neutral labels such as `upper scene`, `central text block`, `middle scene`, `lower-left scene`, and `winding line` until a separate method supports a stronger label.

## Physical grouping update

The predictive split now uses the implemented conservative union groups in [physical-groups.md](physical-groups.md). Each component uses its smallest numeric folio as its representative. The code maps the composite `fRos` alias to representative `85`.

This grouping prevents the known `85/86` foldout from crossing partitions. It also applies conservative unions for other Yale cross-number foldout candidates. The candidate unions do not prove physical identity. A complete physical-sheet diagram remains required for confirmatory work.

## Verification record

On 2026-09-16, the Yale manifest was fetched and its `items` array was checked. The item at index 152 has label `84r`, canvas ID `1006226`, and the full-image dimensions recorded above. The item at index 153 has label `84v` and canvas ID `1006227`.

The full Yale images were downloaded locally for inspection. They are not distributed in this public repository. Use the [canonical Yale 84r image](https://collections.library.yale.edu/iiif/2/1006226/full/full/0/default.jpg) or the [canonical Yale 84v image](https://collections.library.yale.edu/iiif/2/1006227/full/full/0/default.jpg) for public access. Their SHA-256 values and local provenance paths are recorded in `data/folio_sources.json`. A fixed-size image comparison gave the `84r` candidate a lower pixel error than the `84v` candidate. The decision rests on the matching page features and the Yale labels, not on that simple comparison alone.

## Next manual annotation step

Use the full-resolution Yale `84r` image. Trace the page boundary, then mark each figure and each adjacent text line in the upper scene with image-pixel coordinates. Give each mark a neutral ID such as `84r-upper-01`. Record uncertain marks with `?`. Do not assign a translation or a biological meaning during this first pass.

## Primary sources

1. Yale Digital Collections, [Beinecke MS 408 IIIF manifest](https://collections.library.yale.edu/manifests/2002046).
2. Yale Digital Collections, [84r catalog image](https://collections.library.yale.edu/catalog/2002046?child_oid=1006226).
3. Yale Beinecke Library, [Beinecke MS 408 detailed catalog description](https://pre1600ms.beinecke.library.yale.edu/docs/pre1600.ms408.htm).
4. Yale Library, [The Beinecke Cipher (Voynich) Manuscript](https://beinecke.library.yale.edu/beinecke/collections/beinecke-cipher-voynich-manuscript).
