# f1r margin columns and a proposed key

Date: 2026-09-29.
This source check recovered no complete, independently checked key from the f1r margin columns.
The 2024 multispectral account supplies a preliminary transcription and a handwriting attribution.
This report separates those findings from a validated decoding rule.

## The recent substitution claim

The first post in [the August 2026 discussion](https://www.voynich.ninja/thread-6027.html) reports applying a table through EVA to the manuscript text.
EVA is the Extensible Voynich Alphabet. It records written shapes.

The author reports the outputs `Rex` and `bleak`, with 17 occurrences of the latter.
The author says the locations of `Rex` do not fit its expected meaning.
The author also says the proposed key cannot give an actual translation.
These are source claims. This check did not reproduce their counts or outputs.

The author refers to an output attachment. The guest page does not show its file or link.
It also does not show the table, source article link, or code.
The page replaces the article link with a registration or login prompt.
It gives no rule for signs absent from the table.

The second discussion page supplies a different reader's speculative alternative, not the first author's key.
This access result does not show that the missing materials are unavailable to every reader.

## What the 2017 chart shows

J.K. Petersen's [2017 post](https://voynichportal.com/2017/03/18/vms-f1r-column-text-updated-chart/) links a chart that compares the f1r column with historical handwriting samples.
The [chart](https://i0.wp.com/voynichportal.com/wp-content/uploads/2017/03/Voy-f1rColumns2.png) gives the Voynich sample an unknown date.
One column of historical samples carries the label `Marci's Scribe 1640`.
That label identifies a sample used to compare forms. It does not identify the person who wrote the f1r columns.

The chart's note says none of the sampled hands matches the Voynich column text.
It places some individual letter features in sixteenth- and seventeenth-century handwriting.
This chart does not supply a complete Voynich-to-Latin substitution table.
It does not fix each sign reading or each alignment between the manuscript columns.

The chart was unavailable through the first direct requests.
A later request to the site's image service succeeded. The saved source record keeps both results.
The primary agent examined the chart image and its accompanying post.
The linked 2016 predecessor article was unavailable through the selected web and direct requests.
No conclusion about its contents follows from those access failures.

## The newer multispectral account

Lisa Fagin Davis's [2024 account](https://manuscriptroadtrip.wordpress.com/2024/09/08/multispectral-imaging-and-the-voynich-manuscript/) supplies a preliminary transcription from multispectral imaging.
It shows three columns, including two Roman alphabets offset by one position.
The transcription marks unknown entries beside the left column's `m`, `n`, and `q`, with uncertainty at other positions.
Davis also reports common signs missing from the sequence, including EVA `k`.

Davis compares the handwriting with Marci's autograph letter of 12 September 1640.
Her proposed 1662–1665 date depends on that attribution and his ownership period.
The similar letter forms support a later addition.
It does not give a measured ink date or a validated substitution rule.

The primary agent examined the transcription image and two images that compare letter forms and show-through.
No unknown entry was filled, and no glyph was converted to EVA.
The complete multispectral image archive was not examined.

Image credit: The Lazarus Project and The Chester F. Carlson Center for Imaging Science at Rochester Institute of Technology.
Manuscript: Beinecke Rare Book & Manuscript Library MS 408, f1r.

## Ordinary-light image check

The [Yale image](https://collections.library.yale.edu/iiif/2/1006076/full/full/0/default.jpg) contains weak vertical marks beside the body text.
The primary agent examined the full image and two margin regions.
The upper region contains letter-like forms. The lower region contains weaker marks among folds, stains, and damaged areas.
This inspection did not give a reading for every row or a complete parallel sign-to-letter table.

The region coordinates are `(2200, 250, 650, 1300)` and `(2200, 1550, 650, 1250)`.
Each tuple gives the source x-coordinate, y-coordinate, width, and height in pixels.
The source image measures 2972 by 3766 pixels.
These regions do not cover the complete margin.

The inspection does not identify the marks' date, hand, owner, or cause of weak visibility.
It does not show that all other images would give the same reading limit.
These are AI image observations, not an expert handwriting assessment.
The later multispectral source check above supplies additional information. The ordinary-light limit does not override it.

## Decision and verification

Do not use these columns as known plaintext or a validated key.
A candidate test needs fixed sign readings, row alignment, and rules for missing or uncertain signs.
It also needs a source record that separates visible marks from reconstructed entries.
After those inputs are fixed, a test must check continuous text under the project's [validation protocol](validation-protocol.md).

The [source record](f1r-margin-key-check-2026-09-29.sources.json) gives source URLs, SHA-256 hashes, and access limits.
Download the sources and compare their hashes. Examine the chart, cited source passages, and fixed image regions.
Dynamic web pages can change after capture. A changed hash requires examination of the changed content.

The required project suite passed all 85 tests. This software result does not validate a key or translation.
No manuscript corpus processing, new sign assignment, or external decoder execution followed.
Source bodies and detailed receipts stay in the ignored result directory.
