# Fixed solar and lunar name check

Date: 2026-09-29.
This is an exploratory manuscript check. The corpus and page images were previously examined.
No word intersection was computed before this record.

## Question

Could one complete, unchanged recorded word occur in each selected text associated with the same celestial object?
This is a necessary condition only for a restricted name model.
That model places the same whole written name in each selected object's text.
The result will not identify a name, language, reading direction, sign value, or translation.
The texts can describe more than one object. Appearance in the other object's text is not a rejection condition.
All five regions share one physical foldout. They are not independent validation groups.

## Fixed regions and loci

These selections use the catalogue, interlinear section descriptions, locus metadata, and full Yale image 1006196.
They do not use candidate word matches.

- Sun 1: f68r1.5,@Pb; f68r1.6,+Pb; f68r1.7,+Pb. The three words inside the upper medallion.
- Sun 2: f68r2.31,@Cc. The ring around the lower medallion.
- Moon 1: f68r1.37,@Cc. The ring around the lower medallion.
- Moon 2: f68r2.6,@Cc. The ring around the upper medallion.
- Moon 3: f68r3.22,@Cc. The inner ring around the central face.

The Sun and Moon names are catalogue interpretations. They are not recovered text.
The section-to-locus match must agree with the source ordering and visible placement.
If a mapping fails, retain the failed mapping and stop. Do not replace a target.

## Sources and operations

Use data/raw/ZL3b-n.txt, SHA-256 bf5b6d4ac1e3a51b1847a9c388318d609020441ccd56984c901c32b09beccafc.
Use data/raw/IT2a-n.txt, SHA-256 7f27a8b0feed8f6de0a99900df6bf912dd1d295c38e5f830bac8b41c3f536fb5.
Use the existing src/voynich/corpus.py parser.
Run its split and join settings separately. Keep both results without selecting the better one.
For each source and setting, form the union of accepted tokens in each fixed region.
Compute the two-Sun intersection and the three-Moon intersection.
Also retain the two-Moon intersection for the adjacent panels, before the less certain central-face interpretation is included.
Record each candidate's occurrence in all five regions. Retain raw selected records and all exclusion counts locally.
Do not join physical loci, change letters, remove affixes, reverse words, or search elsewhere.

## Failure modes and checks before implementation

- A source changed: reject before parsing when its hash differs.
- A locus is absent or duplicated: reject; no replacement selection.
- A wrong locus-to-image match: stop and preserve the failed assumption.
- The parser removes an uncertain token: retain the raw record and exclusion count; absence remains conditional.
- Uncertain spaces change tokens: retain both split and join settings.
- A circular transcription starts inside a word: record the start uncertainty; do not invent a join.
- A zero intersection is overstated: limit it to exact words in the accepted selected source text.
- A nonzero intersection is overstated: retain candidate status; do not give it a meaning.
- A shared physical page is treated as blind evidence: label every result exploratory.

Before the manuscript calculation, the artifact must specify these expected checks:
- Each input hash matches and each of the seven selected loci occurs once per source.
- Each source supplies five region token sets in each of two settings.
- Every intersection equals direct membership in all relevant region sets.
- Every exclusion count and uncertain-space flag is retained per locus.
- A second run gives equal scientific fields.
- A separate direct source-field calculation checks the candidate sets, with limits stated.

## Decision

A stable common word can become a candidate for a later external-name test, without an assigned meaning.
No common word stops this exact-name model for accepted text only.
Uncertain readings, inflected names, aliases, names absent from descriptions, and other word boundaries remain outside that conclusion.
No replacement regions or looser comparison will follow this result in this study.
