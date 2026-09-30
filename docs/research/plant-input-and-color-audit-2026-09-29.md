# Plant inputs and a proposed color word

Date: 2026-09-29.
These checks supply no validated key or translation.
They examine two public code proposals and add an Appendix image check.
The [source record](plant-input-and-color-audit-2026-09-29.sources.json) gives exact versions and SHA-256 hashes.

## Latin decoder: plant information enters the reading

This source review uses [`mruckman1/voynich`](https://github.com/mruckman1/voynich/tree/59472f00905ad923258bf529ea1420b35694ffa3) revision `59472f00905ad923258bf529ea1420b35694ffa3`.
The default combined Phase 13 operation decodes text, then compares that text with proposed plant identifications.
Its decoder already receives per-folio humoral categories from `PLANT_IDS`.
These categories are labels for proposed medical qualities, such as hot-dry or cold-wet.
The per-folio values in `botanical_identifications.py` were outside this source review.

The [Phase 13 code](https://github.com/mruckman1/voynich/blob/59472f00905ad923258bf529ea1420b35694ffa3/src/voynich/phases/phase13.py#L53-L125) passes the plant metadata and each folio identifier to the decoders.
The [first decoder](https://github.com/mruckman1/voynich/blob/59472f00905ad923258bf529ea1420b35694ffa3/src/voynich/modules/phase12/budgeted_csp.py#L125-L165) adds 50 points to candidate words in the folio's humoral category.
The [next decoder](https://github.com/mruckman1/voynich/blob/59472f00905ad923258bf529ea1420b35694ffa3/src/voynich/modules/phase12/ngram_mask_solver.py#L401-L409) reads the same category.
It [multiplies matching candidate scores by three](https://github.com/mruckman1/voynich/blob/59472f00905ad923258bf529ea1420b35694ffa3/src/voynich/modules/phase12/ngram_mask_solver.py#L506-L518).

The separate option for an explicit plant-name prior is off in this constructor call.
Thus, this finding concerns humoral input. It does not show direct insertion of either reported plant name.
The code review also does not show whether these score changes caused either reported match.
No code from this repository was executed.

The [permutation test](https://github.com/mruckman1/voynich/blob/59472f00905ad923258bf529ea1420b35694ffa3/src/voynich/modules/phase13/illustration_correlation.py#L301-L356) assigns completed decoded texts to different folios.
It does not decode again after those assignments change.
Its result therefore is not a test of the full procedure with the original relation to humoral inputs removed.
This limits the illustration comparison as evidence from a separate source.

The author's [method report](https://github.com/mruckman1/voynich/blob/59472f00905ad923258bf529ea1420b35694ffa3/METHODOLOGY.md#L717-L734) records two genus matches among 22 folios and permutation p-value 0.094.
Its [null-control section](https://github.com/mruckman1/voynich/blob/59472f00905ad923258bf529ea1420b35694ffa3/METHODOLOGY.md#L959-L970) reports that none of sixteen metrics fully separates manuscript output from all three null types.
These are reported results, not calculations repeated by this project.
They do not establish a Latin reading. This source inspection does not reject Latin or every output from the proposal.

Before a future text-only check, remove all folio-derived plant information from the decoder.
A test of the full procedure must decode again within the applicable randomization.
This review did neither. It stops at the documented input dependence.

## Proposed `key` reading: blue

This check uses [`geoffitect/voynich`](https://github.com/geoffitect/voynich/tree/860d278a6fa72a39605a11513716e56298411d47) revision `860d278a6fa72a39605a11513716e56298411d47`.
Its [progress report](https://github.com/geoffitect/voynich/blob/860d278a6fa72a39605a11513716e56298411d47/reports/PROGRESS.md) proposes EVA `key` for blue.
The plant-feature and paint-color analyses use overlapping folios and the same transcription.
Both count all words on a folio. Neither assigns a token to a particular flower or painted region.

The [plant-feature analysis](https://github.com/geoffitect/voynich/blob/860d278a6fa72a39605a11513716e56298411d47/scripts/04_content/plant_features.py) searches 25 features and ranks words on that same data.
It has no holdout set or correction for multiple comparisons.
Its saved output gives three `key` occurrences on blue-flower folios, none in the comparison set, and fifteen overall.
The [color analysis](https://github.com/geoffitect/voynich/blob/860d278a6fa72a39605a11513716e56298411d47/scripts/04_content/color_crossref.py) also uses hand-coded folio tags.
Its limited export has no `key` row. This omission cannot show whether the reported paint enrichment is correct.
These analyses give a discovery lead, without a separate semantic test.

The [fixed transfer plan](../plans/blue-word-transfer-v1.md) removes every physical group represented in the plant-feature discovery map.
It keeps the candidate word, transcription, color tags, and exact-token rule.
It records the remaining counts without fitting a cutoff or changing the selected pages.
The count is conditional on the released tags and transcription.
The earlier paint-color analysis used the same color-tag pool. These pages do not form a holdout set for that analysis.
Here, transfer means only recurrence outside the plant-feature groups.

The [result](../../reports/BLUE_WORD_TRANSFER.md) keeps 34 folios after 91 group exclusions and one missing-text exclusion.
The three blue-tagged pages contain 289 words and no exact `key` token.
The other 31 pages contain 2,711 words and two `key` tokens, on f50v and f96v.
This subset supplies no positive support for the proposed meaning.
The small sample and unverified tags prevent a general rejection. No different candidate or weaker comparison followed.

## Bax Appendix 1: source-image check

The earlier [partial-key check](anchor-audit.md#partial-sound-key-opening-word-coverage) used fourteen EVA units from the PDF text layer.
The source-image check now includes Appendix 1 on pages 56–57 of [Bax's January 2014 paper](https://stephenbax.net/wp-content/uploads/2014/01/Voynich-a-provisional-partial-decoding-BAX.pdf).
The author PDF request gave HTTP 403. A Google Viewer cache supplied a 62-page copy with the same title, version, and date.
Its SHA-256 is `bdac04fb06fb94e7af33fda9d9539e603725da7b91f116aed1e79b83b78fef67`.

The images show these labels: `k y d r m n sh s o a in iin e ee`.
The table has no separate EVA entry for `ch` or `f`.
The table gives `/tʃ/` as one possible sound for `sh` and uses `CH` in proposed name readings.
Neither use adds a separate EVA `ch` entry.

Each opening word still has characters outside the fixed list.
This check added no new target, sign assignment, or name comparison.
The images show the table inventory. They do not validate the sign readings against other manuscript pages or establish the proposed sounds.

## Review limits

The primary agent examined the cited code paths and both Appendix images.
Separate AI tasks examined the source logic, candidate selection, and Appendix labels.
These checks are not an external scholarly assessment.
Keep the stopped candidate branches closed unless new evidence changes their stated conditions.
