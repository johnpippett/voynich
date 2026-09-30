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

## Bounded reading attempt

A later attempt used two AI readers with separate source contexts.
One reader examined the original folio 1r sign row and only the first cipher line on folio 1v.
The other examined only the first two handwritten lines of Schulte's second paragraph on folio 1r.
The primary agent had already seen both pages and the candidate Latin words. Its comparison was not blind.
The method permitted one reading pass per reader and kept unclear forms unresolved.

The cipher reader returned no stable sign inventory or first-line sequence.
The viewer had reduced both full-page images for display. The reader left the sign and word boundaries unresolved.
This result limits the selected input method. It does not show that the source is unreadable.

The Latin reader also left uncertain and unreadable text.
The primary agent disagreed with two proposed word readings after image examination.
Both reader records remain unchanged. No request for a revised reading followed.
Without a stable cipher sequence, the comparison stopped before any sign-value assignment or separate-passage test.
No Voynich values followed.

The [attempt record](fontana-alignment-check-2026-09-30.json) gives the source URLs, file hashes, scope, and result.
All six recorded source-hash comparisons matched: three scope entries, two cipher-reader entries, and one Latin-reader entry.
These comparisons cover three unique images. The project suite passed all 85 tests; this software result does not validate a reading.
Local first-pass records and the comparison receipt remain in `results/fontana-alignment-2026-09-30/`.

To repeat the source examination, obtain the three images from the recorded URLs and compare their SHA-256 values.
Examine the stated regions and keep uncertain boundaries unresolved. Do not use the incomplete records as a cipher transcription.
A future attempt needs a stable sign record and explicit abbreviation rules before letter matching.
Do not repeat this input method with prompted word repairs.

## A limit of later transcriptions

[Marco Vito's 2025 study](https://www.nam-sism.org/Articoli/Articoli%202025/NAM%20N.%2021.%207.%20VITO%20La%20crittografia%20diplomatica%20e%20militare%20nell%27Italia%20del%20Quattrocento.pdf#page=16) describes occasional homophones on printed page 262.
Here, homophones are different cipher signs with the same letter value.
On page 263, note 28 says that the 1984 edition corrects writing errors without a note.
Vito distinguishes supplied and extra letters in his own readings.
This review examined the text on printed pages 262–264, without a figure analysis or an independent comparison of those editions.
These source claims do not establish Schulte's treatment of every sign.
They show why a readable Latin transcript must not automatically become an exact letter-by-letter target.

A [later source check](fontana-published-alphabet-2026-09-30.md) found Omont's printed 23-pair alphabet for the Paris manuscript.
That check also examined Vito's pages visually and recorded his changes to word spacing.
The earlier AI reading records remain unchanged. The later report keeps the published alphabet separate from an unsuccessful excerpt-reading check.
