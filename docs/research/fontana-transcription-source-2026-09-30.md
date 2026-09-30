# A digitized Fontana transcription

Date: 2026-09-30.
This source check found a new route to historical cipher evidence. It supplied no Voynich sign values.

The [Bayerische Staatsbibliothek record](https://www.digitale-sammlungen.de/de/details/bsb00015141) identifies Heinrich Schulte's 1910 transcription of Fontana's secret writing.
The item is *Transkription der Geheimschrift in des Johannes de Fontana Bellicorum instrumentorum liber*, BSB Cod.icon. 242 a.
The catalogue record lists 45 paper leaves.

The [image manifest](https://api.digitale-sammlungen.de/iiif/presentation/v2/bsb00015141/manifest) has two index entries:

| Index entry | Canvas | Folio label |
| --- | ---: | --- |
| `Titelkommentar` | 5 | Ir |
| `Lateinische Transkription` | 7 | 1r |

The index has no separate key or alphabet entry. This does not show that all leaves lack a key.
The color chart on the title-commentary page is a scan target, not cipher evidence.
The linked search service returned HTTP 404. The review saved the catalogue record, manifest, page images, and individual page text.

## What the opening page supports

Schulte canvas 7, folio 1r, has a margin note `1v.` and Latin text.
The opening words also appear in the visible Latin paragraph on [Fontana's folio 1v](https://api.digitale-sammlungen.de/iiif/image/v2/bsb00013084_00007/full/full/0/default.jpg).
This visual comparison supports the page relation. We did not compare every word.
The original first paragraph is already in Latin. This comparison does not show a cipher reading.

A later paragraph starts `Oportet in anteriori parte`.
Treat it as possible plaintext for later review. The inspected page places no cipher signs beside it and gives no sign-value table.
This review did not connect the paragraph to cipher signs. No proposed letter values were tested on another passage.
Do not treat its position on the page as a complete key.

## Scope, verification, and next requirement

The bounded review covers canvases 3 through 10: opening matter and the first two numbered folios.
It also covers the catalogue and image index. It does not cover all 45 leaves.
The [source record](fontana-transcription-source-2026-09-30.sources.json) gives URLs, byte counts, and SHA-256 values for 23 kept files.
All 23 file sizes and hashes matched during the final source check.
The original Fontana folio 1v image also matched its earlier published source hash.

Internal reviews inspected the new source and compared the opening page with the original image.
These checks are not external scholarly validation.
This source check did not produce a cipher reading or give values to Voynich signs.

Before you test a key, record each historical sign and its proposed letter value.
Then test those values on a separate source passage.
Use separate evidence to connect Fontana signs to Voynich signs.
Keep the first access failures in the [earlier historical source record](historical-key-comparisons-2026-09-29.md).
