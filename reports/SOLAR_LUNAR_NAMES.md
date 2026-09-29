# Solar and lunar name check

Date: 2026-09-29.
No common complete word occurs in the accepted texts for either fixed pair of Sun or Moon figures.
Both pinned transcriptions give this result under both rules for uncertain spaces.
The two transcriptions are readings of the same manuscript, not separate manuscript witnesses.
This result supplies no name, sign value, or translation.

## Question and selection

The proposed name model puts one unchanged whole written name in each selected text for the same object.
This check asks whether those texts have such a common word.
It does not assume that every word is a name or that a name appears only beside one object.
The [fixed plan](../docs/plans/solar-lunar-name-check-v1.md) records the selections, failure modes, and limits before the calculation.

The [quire description](https://www.voynich.nu/q09/index.html) identifies two Sun figures and three Moon figures on f68r.
The central face on f68r3 has a less certain identification.
The [Yale image](https://collections.library.yale.edu/iiif/2/1006196/full/full/0/default.jpg) shows all five regions on one foldout.
This is an exploratory check. These regions are not separate validation groups.

| Region | Fixed loci | Text placement |
| --- | --- | --- |
| Sun 1 | `f68r1.5,@Pb`; `f68r1.6,+Pb`; `f68r1.7,+Pb` | Inside the upper medallion |
| Sun 2 | `f68r2.31,@Cc` | Around the lower medallion |
| Moon 1 | `f68r1.37,@Cc` | Around the lower medallion |
| Moon 2 | `f68r2.6,@Cc` | Around the upper medallion |
| Moon 3 | `f68r3.22,@Cc` | Around the central face |

The [f68r1](https://www.voynich.nu/q09/f068r1_tr.txt), [f68r2](https://www.voynich.nu/q09/f068r2_tr.txt), and [f68r3](https://www.voynich.nu/q09/f068r3_tr.txt) interlinear descriptions give the text placements.
Image inspection supports these placements but does not certify complete glyph readings or word boundaries.
The Sun and Moon names are source interpretations, not translated text.

## Result

The existing parser keeps accepted basic EVA tokens and counts excluded tokens.
EVA records written shapes. It does not establish linguistic letters.
The check takes the intersection of region token sets, separately for each transcription and uncertain-space rule.
It makes no spelling changes, partial matches, affix removals, or searches in other regions.

| Source | Region | Accepted words, split / join | Distinct accepted words | Excluded tokens |
| --- | --- | ---: | ---: | ---: |
| ZL | Sun 1 | 3 / 3 | 3 | 0 |
| ZL | Sun 2 | 11 / 10 | 9 | 1 |
| ZL | Moon 1 | 4 / 4 | 4 | 1 |
| ZL | Moon 2 | 6 / 6 | 6 | 2 |
| ZL | Moon 3 | 10 / 10 | 10 | 0 |
| IT | Sun 1 | 3 / 3 | 3 | 0 |
| IT | Sun 2 | 11 / 11 | 11 | 0 |
| IT | Moon 1 | 4 / 4 | 4 | 1 |
| IT | Moon 2 | 7 / 7 | 7 | 1 |
| IT | Moon 3 | 10 / 10 | 10 | 0 |

The two-Sun intersection is empty in all four tracks.
The adjacent two-Moon intersection is also empty, before the less certain central face is included.
The three-Moon intersection is therefore empty in all four tracks.
The [count receipt](solar-lunar-name-check-v1/result.json) records all loci, source hashes, and exclusion counts.

## Limits and decision

IT accepts every token in the two selected Sun texts.
The other comparisons have excluded readings, so their absence result is incomplete.
All results depend on source spellings, word boundaries, circular-text start points, and figure identities.
The calculation uses recorded tokens. It does not join a possible word across a circle's transcription start.
Inflected names, aliases, names absent from descriptions, and other encoding rules remain possible.

This exact-name model gives no candidate for a name-based key constraint.
The study stops without replacement regions or a looser comparison.
It does not reject astronomical content or language.

## Verification

The plan and executed script are unchanged from their saved versions.
Two runs produced identical result files.
Another run used new source downloads in a separate directory and produced the same file.
The script refused an existing output path and rejected an altered source without writing output.
The [replay receipt](solar-lunar-name-check-v1/verification.json) records these results.

The [replay instructions](solar-lunar-name-check-v1/README.md) give the setup, command, and expected result hash.
The [image source record](solar-lunar-name-check-v1/sources.json) gives source URLs, image rectangles, and SHA-256 hashes.
The full local result preserves raw selected records; the public receipt contains counts and source references.

A separate AI calculation read the seven source fields without the corpus parser or prior result files.
It reproduced all twenty region token collections and all twelve intersections.
All twenty-eight locus exclusion counts and uncertain-space flags also agreed.
The primary agent compared its receipt with the first result.
The [comparison receipt](solar-lunar-name-check-v1/separate-calculation.json) records the script and result hashes.
These project checks do not constitute external scholarly validation.
