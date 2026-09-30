# A published Fontana cipher alphabet

Date: 2026-09-30.

This source check found a published alphabet with 23 sign-to-letter pairs.
The alphabet is for the Paris *Secretum de thesauro* manuscript, BnF NAL 635.
It does not give a Voynich key or translation.

## The primary source

Henri Omont's article appears in *Bibliothèque de l'École des chartes*, volume 58, 1897, pages 253–258.
The [Persée record](https://www.persee.fr/doc/bec_0373-6237_1897_num_58_1_447898) identifies the article but masks illustrations.
The [Internet Archive volume](https://archive.org/download/bibliothquedel58sociuoft/bibliothquedel58sociuoft.pdf#page=260) contains the printed alphabet on page 254, PDF page 260.
The attached manuscript plate is PDF page 262. Printed page 255 follows on PDF page 263.

The table places each cipher sign above its Latin label.
Labels: `a b c d e f g h i k l m n o p q r s t u x y z`.
There are no separate `j`, `v`, or `w` labels.
The primary agent and another AI task found the same 23 pairs, without an unclear column alignment.
The two records agree about the printed table. It does not validate every manuscript reading.

Omont gives five explicit vowel rules:

| Written shape | Printed value |
| --- | --- |
| Circle alone | `i` |
| Circle with a stroke to the left | `a` |
| Circle with a stroke to the right | `u` |
| Circle with a stroke upward | `e` |
| Circle with a stroke downward | `o` |

He places the abbreviation bar below the word.
The bar can replace final `m` or `n`, or mark an abbreviated word.
Thus, the alphabet does not by itself specify every abbreviation expansion.

## One bounded input check

A fresh AI reader received only the alphabet crop and one short cipher entry from the attached plate.
It did not receive the published Latin reading.
The primary agent selected the entry after seeing that reading. Selection was not blind.
The method permitted one pass and required unresolved signs and abbreviation marks to remain explicit.

The reader supplied no usable sign sequence from the two visible lines.
It could not identify the individual written signs reliably and left their positions and readings unresolved.
No letter-match score or abbreviation expansion followed.
The first record remains unchanged, and no reader retry followed.

This result limits the selected AI input method. It does not reject Omont's alphabet or show that the source is unreadable.
The published table is a new source for future work; its successful use on continuous text remains unverified here.
The [earlier failed reading attempt](fontana-transcription-source-2026-09-30.md#bounded-reading-attempt) remains a different record.

## A source-transcription constraint

A visual examination also covered [Vito's 2025 Fontana section](https://www.nam-sism.org/Articoli/Articoli%202025/NAM%20N.%2021.%207.%20VITO%20La%20crittografia%20diplomatica%20e%20militare%20nell%27Italia%20del%20Quattrocento.pdf#page=16), printed pages 262–264.
Its Figure 5 shows a manuscript spread, without an alphabet table.
Note 28 states that the printed readings change spacing for readability.
It uses square brackets for supplied letters and parentheses for written letters treated as errors.
Upright type identifies plain text; italic type identifies cipher readings.

These conventions prevent direct use of the printed words as an exact sign-position record.
This source statement does not establish how Schulte's earlier transcription treats every sign.

## Original manuscript image follow-up

A further check used the original BnF image of folio 8r.
The [BnF manifest](https://gallica.bnf.fr/iiif/ark:/12148/btv1b10023795x/manifest.json) identifies it as canvas 29.
The [source image](https://gallica.bnf.fr/iiif/ark:/12148/btv1b10023795x/f29/full/full/0/native.jpg) measures 2,986 by 4,172 pixels.
This source differs from the printed facsimile used in the earlier failed check.

The primary agent fixed the folio and reading rules before it obtained the image.
The selected input was the first two cipher lines, above the red Latin heading.
The primary agent fixed crop coordinates after examining the page layout and before reading signs.
The method used the same printed alphabet and permitted one pass per reader.
It required uncertain signs and abbreviation marks to remain explicit, without Latin word repairs.

The primary agent recorded 17 and 19 tentative sign positions, with eight unresolved letter values.
The other AI reader did not confirm these positions.
That reader could not supply a stable sequence or word boundaries.
It recorded only two low-confidence shape candidates on line 1 and a possible abbreviation bar on line 2.
Thus, the records do not establish a common sign sequence or a continuous reading.

The primary agent had seen published readings from other folios and chapter titles, including the neighboring folio 8v.
Neither reader consulted a proposed folio 8r reading during this check.
The folio selection was not random. The method had no numeric agreement threshold.
This was an exploratory input check, not a confirmatory reading test.

Some tall or descending marks approach the crop edges.
This crop limit and the uncertain shape matches remain in the first-pass records.
No changed crop, alphabet change, abbreviation expansion, or reader retry followed.
The result limits this AI reading procedure. It does not show that the manuscript is unreadable.

The replay produced crops with identical decoded pixel values from the saved JPEG.
The source and three reader-input hashes matched. All 85 project tests passed.
Source files, reading records, and the replay receipt stay in `results/fontana-original-reading-2026-09-30/`.
The source record gives the crop rectangles and hashes. No Voynich sign assignment followed.

## Verification and next requirement

The [source record](fontana-published-alphabet-2026-09-30.sources.json) gives the source URLs, hashes, page numbers, and crop coordinates.
It records the initial broken link, access failures, and later successful journal download as different events.
All eight source-file hashes and byte counts matched, including two saved HTTP error responses and the earlier Vito PDF.
The table labels agree between the two visual records. Both input image hashes match the first-pass reading record.
These checks are not external scholarly validation.

All 85 project tests passed. This software result does not validate a manuscript reading.

To repeat the source check:

1. Get the journal PDF from the recorded URL and compare its SHA-256 hash.
2. Examine the alphabet and abbreviation paragraph on PDF page 260.
3. Use the recorded page numbers, resolution, and rectangle coordinates to render each crop.
4. Record abbreviation marks and uncertain signs in different fields from letter values.
5. Do not replace the first-pass result with a reading informed by the published answer.

A later reading needs a stable sign record from continuous source text.
Use on Munich or Voynich needs further evidence for sign correspondence and reading rules.
No Voynich sign assignment, corpus fit, or decoder execution followed this source check.
