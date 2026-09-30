# Decoder rules and source limits

Date: 2026-09-29.
The objective is a key or translation with independent verification.
These source checks do not show a correct key or translation.
They identify missing inputs and separate generated sentences from evidence for their meanings.
No external decoder ran, and no manuscript corpus was processed.

## Italian reader

The review uses [Vlegels commit `ba3ffea`](https://github.com/leonvlegels/Voynich/tree/ba3ffea6d517721b389e22af3a67f78db3674e73).
The [handoff](https://github.com/leonvlegels/Voynich/blob/ba3ffea6d517721b389e22af3a67f78db3674e73/HANDOFF.md#L43-L70) reports phoneme rules from 3,504 aligned Italian–EVA pairs.
This audit did not reproduce that count or those alignments.
EVA is a transcription of written shapes. Its units are not known linguistic letters.

The [included decoder](https://github.com/leonvlegels/Voynich/blob/ba3ffea6d517721b389e22af3a67f78db3674e73/voynich_folio_decode.py#L249-L313) first looks up complete tokens.
The no-`qo` branch needs a mapped `qo`-extended form and an unmapped alternative `o` form.
Its `k`, `p`, `op`, and `t` prefix rules need mapped stems. Unknown forms return `?`.
This function does not implement the reported general phoneme conversion method.

The [handoff](https://github.com/leonvlegels/Voynich/blob/ba3ffea6d517721b389e22af3a67f78db3674e73/HANDOFF.md#L171-L190) names `analysis/voynich_reverse_match.py` and `analysis/voynich_phoneme_map.py` as derivation tools.
Both paths are absent from the [complete Git tree](https://api.github.com/repos/leonvlegels/Voynich/git/trees/ba3ffea6d517721b389e22af3a67f78db3674e73?recursive=1) at this commit.
The API response contains 13 entries and marks the tree as not truncated.
The three examined files name no separate path for the aligned pairs or an independent validation set.
This result does not show that these materials never existed elsewhere.

The handoff's direct command also uses `analysis/voynich_folio_decode.py`, but the file is at the repository root.
Its `ROOT = Path(__file__).parent.parent` points above that root.
This static path difference does not show failure of the README's different corpus-generation command, which was not examined.

## Reproduction and generated prose

This review uses [Lackadaisical Security commit `c499311`](https://github.com/Lackadaisical-Security/Voynich-Script-Decoded/tree/c499311b8fb43351c91b03908948eaa9b1cdd18a).
The [final translator](https://github.com/Lackadaisical-Security/Voynich-Script-Decoded/blob/c499311b8fb43351c91b03908948eaa9b1cdd18a/voynich_translator_final.py#L37-L128) selects and simplifies stored lexicon meanings.
It also splits period-separated forms for component lookups.

The [reproduction guide](https://github.com/Lackadaisical-Security/Voynich-Script-Decoded/blob/c499311b8fb43351c91b03908948eaa9b1cdd18a/REPRODUCTION_METHODOLOGY.md#L383-L436) compares seven generated strings with seven expected strings stored in the guide.
It also names `voynich_translation_natural_english.md` as a comparison target, without a version or hash for that file.
This audit did not capture that target.

The [validation report](https://github.com/Lackadaisical-Security/Voynich-Script-Decoded/blob/c499311b8fb43351c91b03908948eaa9b1cdd18a/REPRODUCTION_VALIDATION_REPORT.md#L156-L164) gives a result of 27 exact matches.
The guide's seven-value comparison cannot reproduce that count by itself.
Matching the supplied phrases would check software output, without independently showing that their meanings are correct.

The [other translator](https://github.com/Lackadaisical-Security/Voynich-Script-Decoded/blob/c499311b8fb43351c91b03908948eaa9b1cdd18a/ultimate_voynich_translator.py#L48-L54) selects a subject domain from folio-number ranges.
That domain affects [contextual lookups](https://github.com/Lackadaisical-Security/Voynich-Script-Decoded/blob/c499311b8fb43351c91b03908948eaa9b1cdd18a/ultimate_voynich_translator.py#L446-L464) and [sentence construction](https://github.com/Lackadaisical-Security/Voynich-Script-Decoded/blob/c499311b8fb43351c91b03908948eaa9b1cdd18a/ultimate_voynich_translator.py#L675-L723).
The [sentence builder](https://github.com/Lackadaisical-Security/Voynich-Script-Decoded/blob/c499311b8fb43351c91b03908948eaa9b1cdd18a/ultimate_voynich_translator.py#L543-L673) groups decoded meanings, then uses a few group members in fixed sentence templates.
The botanical template uses only the first two substance meanings.

For this example, three decoded entries have `field == 'botanical_part'` and nonempty `english` values.
All three enter the substance group.
If the domain and other inputs stay unchanged, a change to only the third meaning cannot change the botanical sentence.
This consequence follows from the code. It does not show that any particular meaning is false.
Fluent output from this template cannot independently check every decoded term.

This audit did not examine the lexicon JSON, corpus JSON, or a separate complete f100r output.
It did not reproduce the reported accuracy or statistical results.

## Cheshire's reading choices

The review uses [Cheshire's 2019 article](https://doi.org/10.1080/02639904.2019.1599566), as captured from a mirror.
The publisher and university PDF requests returned HTTP 403.
The captured file has the article's DOI and journal header. The manifest identifies its source and hash.

On printed page 6, the article says that proposed `i` and short `e` forms can need visual judgment.
Printed page 16 explains the proposed f53r reading through examples from Galician, Portuguese, Latin, Greek, and Old French.
Figure 34 on printed page 17 labels its manuscript image as f53r.
These observations identify choices that a new passage test must specify.
They do not show that the proposed meanings are correct or show that ambiguity is impossible in historical writing.

The first review exceeded its eight-page limit: web extraction exposed 30 pages across the 2019 and 2017 papers.
That review examined no page images. It does not support a complete audit or a whole-source absence claim.
A recorded follow-up selected three images from the captured 2019 PDF before rendering: PDF pages 7, 17, and 18.
The primary agent checked only these images for the positive observations above.
This follow-up does not remove the first scope failure or give a complete conversion table.

## Next evidence requirements

A new Italian rule test needs the named derivation code, alignment inputs, and an independently checked target.
A reproduction check needs a versioned target and a complete comparison record.
A semantic check must test the assigned meanings against evidence outside those assignments.
Cheshire's method needs recorded procedures for sign choices and language choices before a new passage test.
The [validation protocol](validation-protocol.md) keeps the acceptance criteria.
None of these source findings justifies new sign values or another fit of a stopped model.

## Verification

The [source manifest](decoder-rule-eligibility-2026-09-29.sources.json) records source versions, SHA-256 hashes, examined locations, and access limits.
For a source check, download the stated version and compare its SHA-256 hash.
Examine the cited functions, guide sections, and PDF pages.
For the missing-script check, request the stated recursive tree and check its completeness and path list.
API metadata can change. The commit and source-file hashes identify the source version.

Separate AI tasks examined the Italian files and translator code.
The primary agent checked their findings against the saved sources and corrected one filename attribution.
The script names and direct command occur in `HANDOFF.md`, not `README.md`.
These checks are project reviews, not external scholarly validation.
The required project suite passed all 85 tests. This software result does not validate a translation.

Local source bodies and review records stay in ignored result directories.
No source-body copies form part of this public update.
