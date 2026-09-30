# Kiltau Hebrew–Aramaic source check

Date: 2026-09-30. Source version: 9.11.0.

This source check found a rule conflict and limits in the evidence for the proposed meanings.
It gives no validated Voynich key or continuous translation.
The [source website](https://voynich.kiltau.com/) also states that the manuscript remains undeciphered.
This proposal differs from the [earlier Hebrew method](hebrew-key-audit-2026-09-29.md).

## A rule and its listed output disagree

The [rules data](https://voynich.kiltau.com/api/rules) gives rule R2 without exceptions: initial `o` becomes Hebrew Ayin, `ע`.
EVA, the Extensible Voynich Alphabet, records written shapes. An EVA character does not identify a linguistic letter.

The [lexicon data](https://voynich.kiltau.com/api/lexicon) gives `or` as `אוֹר`, which begins with Aleph, `א`.
Its entry lists R2 among the applied rules and gives five confidence stars.
Ayin and Aleph are different letters: U+05E2 and U+05D0.
The other listed rules, R19, R40, and R43, do not specify an Aleph exception.

This is a conflict between published records. No software failure was measured.
A stored lexicon entry can give repeatable output without agreement with the stated sign rule.
The examined material does not specify which record controls this example.

## What the backward-test results show

The [validation page](https://voynich.kiltau.com/validation) gives 10/10 Type I results and 34/37 Type II results.
A backward test converts proposed Hebrew or Aramaic forms to EVA, then searches the source corpus.
The Type I table supplies occurrences and interpretations of their context.
It says the ten anchors were fixed in version 7.4 before folio analysis.
The examined pages give no dated freeze record or scores from separate readers for the proposed meanings.

The validation page describes Type II items as discoveries from folio analysis, with no external predictive force.
The [API document](https://voynich.kiltau.com/api.md) instead describes forms predicted before their observation.
The captures do not explain this difference in timing.
The table contains 37 items, including words, sequences, rule patterns, and folio interpretations.
A separate note gives 29 confirmed items and three historical failures outside the dataset.
The page does not explain how these counts relate to 34/37.

The site's open-problem section lists blind validation by specialists outside the project with status `pending`.
These source claims do not show meanings recovered independently.
This source check did not reproduce the published counts or false-positive claim.

## External dictionary comparison

The homepage highlights `sar · al · daiindy` as its strongest anchor.
The primary agent knew the proposed meanings before this comparison. This was not a blind reading.

The comparison used three entries from Jastrow's dictionary, in Sefaria's electronic edition of the 1903 text.
The API returned several dictionaries despite the requested filter.
Selection therefore used both `parent_lexicon = Jastrow Dictionary` and each entry's `rid`.

| Proposed form | Selected entry | Finding |
| --- | --- | --- |
| `sar` → `שַׂר` | [U01906](https://www.sefaria.org/api/words/%D7%A9%D6%B7%D7%82%D7%A8?lexicon=Jastrow%20Dictionary) | Ruler, chief, and angelic senses; no physician sense in this entry. |
| `al` → `עַל` | [P00757](https://www.sefaria.org/api/words/%D7%A2%D6%B7%D7%9C?lexicon=Jastrow%20Dictionary) | Gives ordinary senses of upon, above, and about. |
| `din` component of `daiindy` | [D00635](https://www.sefaria.org/api/words/%D7%93%D6%B4%D6%BC%D7%99%D7%9F?lexicon=Jastrow%20Dictionary) | Gives judgment and law, among other senses. |

The proposed lexicon includes a physician sense for `sar`, with internal folio references but no external dictionary citation in that entry.
Its absence from one dictionary entry does not prove that specialized medical usage never existed.
The comparison does not validate the full `daiindy` form, its suffix, the phrase's grammar, or the EVA assignments.

The lexicon count agrees with the homepage: 419 entries have at least three stars and are not marked as candidates.
Four other entries with at least three stars are marked as candidates.
The complete response contains 549 entries. These counts apply to different groups and do not show a count error.

## Verification and decision

The [source record](kiltau-hebrew-aramaic-source-check-2026-09-30.sources.json) gives URLs, byte counts, SHA-256 hashes, and entry selectors.
Ten source bodies remain in the ignored `results/kiltau-source-audit-2026-09-30/` directory.
All ten source hashes and byte counts matched during the final comparison.

Separate AI tasks examined mapping rules and validation claims. The primary agent compared the dictionary entries and examined the combined evidence.
These checks are not external scholarly validation.
All 85 project tests passed. This software result does not validate the proposed meanings.

The work used static source captures and local record comparisons.
No translation service, backward-test endpoint, external source code, or manuscript decoder ran.
No new sign values or replacement meanings were supplied.

To repeat this source check:

1. Get the ten source files from the recorded URLs.
2. Compare their byte counts and SHA-256 hashes with the source record.
3. Treat changed bytes as a new source version.
4. Compare R2 with the `or` entry and its listed rules.
5. Examine the two test definitions and the Type II table.
6. Select the three named dictionary entries by lexicon and identifier.
7. Keep word senses separate from evidence for the manuscript assignments.

This audit stops without a reading experiment.
A later test needs explicit rule precedence, a fixed prediction record, and blind assessment of continuous text by specialists outside the project.
The [project validation protocol](validation-protocol.md) remains the acceptance standard.
