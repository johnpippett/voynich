# Zodiac degree alignment: control within physical panels

Research status: 2026-09-17

The published figure-attribute sequence does not pass the specified test for additional alignment within physical panels.
The fixed alignment has 52 matches among 78 known positions.
The exact conditional p-value is **0.42044**.
We stopped this alignment branch as a source of fine positional constraints for label interpretation.
This result supplies no label meaning, language, or key.

## Competing explanations

A reported match with a zodiac degree table can depend on different attribute proportions in separate panels.
Alternatively, the table can supply additional information about positions within each panel.
The new control tests the second possibility while it keeps each panel's predicted class counts fixed.

This is an exploratory analysis of published observations.
The source, attributes, panel order, and shift already have a selection history.
The control is not a new blind image study.

## Source and input limits

The source is Averyanov's [*Thirty Names per Sign*, version 1](https://doi.org/10.5281/zenodo.21761983).
The [paper](https://zenodo.org/api/records/21761983/files/paper2_arxiv.pdf/content) reports a fixed shift of 23 and a sampled p-value of 0.0088.
Its data section limits the interpretation to a local division into halves.
It does not establish a degree reading across the manuscript.

The [release ZIP](https://zenodo.org/api/records/21761983/files/voynich_replication_v1.zip/content) omits three inputs required by `blind_recode_eval2.py`:

- The first-round answer CSV.
- The second-round position key.
- The second-round answer CSV.

The final sequence survives in `RESULT.md` and as literal arrays in `test_lunar_vs_degree.py`.
Separate extraction methods find agreement at all 90 positions, including 12 unknown values.
We used this published sequence. We could not verify the original answer-to-image joins from the release.
An input addendum records this change before calculation. The original unrun plan remains in the local record.

The sequence combines headdress observations for Pisces with clothing observations for Aries and Taurus.
It includes revised observations after an unsuccessful first round and retains most first-round observations for Aries and Taurus.
The calculation therefore depends on the released attribute definitions and position assignments.

The release identifies its binary table as al-Biruni §457, with 1 for female degrees and 0 for male degrees.
We did not obtain a readable primary page image that verifies the printed class markers.
The result below concerns the released table vectors. It does not certify their historical transcription.

## Fixed method

We kept the source's polarity, shift 23, and light-panel-first order.
For zero-based position `j`, the prediction is `table[(j - 23) % 30]`.
The score counts equal observed and predicted values at known positions.
Unknown positions remain fixed and contribute no score.

The control splits each shifted table at the physical-panel boundaries specified by the release:

| Sign | First panel | Second panel |
|---|---|---|
| Pisces | f70v2, 30 positions | None |
| Aries | f71r, 15 positions | f70v1, 15 positions |
| Taurus | f71v, 15 positions | f72r1, 15 positions |

Within each panel, we cyclically rotate the prediction through every offset.
We select each panel offset independently with equal probability.
Each rotation preserves that panel's predicted class counts and cyclic pattern.
It changes the alignment with the observed attributes and their fixed unknown positions.
This operation does not preserve table continuity between paired panels.

The conditional null hypothesis assigns equal probability to the relative starting positions within each panel.
Its exact space contains `30 * 15^4 = 1,518,750` offset combinations.
Repeated binary patterns retain their offset multiplicity.
The upper-tail p-value is the fraction with a score at least 52, including the identity combination.

The specified criterion requires `p <= 0.05` and an observed score above the null mean.
We did not search for another shift, polarity, attribute, panel subset, or null after this calculation.
For a reproduction check, we also enumerated the original null's `30^3` independent whole-sign rotations.
That check uses the same fixed observed alignment.

## Results

| Quantity | Whole-sign reproduction | New control within panels |
|---|---:|---:|
| Known positions | 78 | 78 |
| Observed matches | 52 | 52 |
| Mean matches under the null | 40.73333 | 50.86667 |
| Observed score minus null mean | 11.26667 | 1.13333 |
| Offset combinations | 27,000 | 1,518,750 |
| Combinations with at least 52 matches | 225 | 638,550 |
| Exact upper-tail fraction | 1/120 | 473/1125 |
| Exact p-value | 0.00833 | **0.42044** |

The whole-sign result is consistent with the source's sampled p-value of 0.0088.
The new control does not meet the specified criterion.

| Panel | Known positions | Observed matches | Mean matches under panel rotations |
|---|---:|---:|---:|
| f70v2 | 22 | 17 | 14.20000 |
| f71r | 14 | 8 | 8.40000 |
| f70v1 | 14 | 8 | 8.00000 |
| f71v | 14 | 6 | 7.26667 |
| f72r1 | 14 | 13 | 13.00000 |

The prediction is constant on f70v1 and f72r1 at the fixed shift.
Those two panels supply no information about their internal starting position under this control.
Their contributions remain in the total with their full offset multiplicity.

## Interpretation and stop decision

This result does not supply evidence for additional alignment within panels under the specified null.
It does not prove that differences between panels caused the original match.
The two nulls test different conditions. Their p-values are not probabilities that either historical explanation is true.

Conditioning on panel counts removes possible information carried by those counts.
Thus, the result does not reject every degree interpretation or establish that the drawings have no meaningful order.
It stops our use of this attribute/table match as a fixed, fine positional guide to label meanings.
No label text or candidate name was scored.

A separate image check examined the complete Cancer and Leo diagrams on f72r3 and f72v3.
The [Yale images](https://collections.library.yale.edu/catalog/2002046) show three figure bands and two figure bands, respectively.
We found no explicit start arrow or numeric sequence that fixes a unique traversal.
This check does not verify the Pisces, Aries, or Taurus slot assignments used by the calculation.

## Verification and records

The input check independently reconstructed the archived sequence and compared all 90 positions with the source's literal arrays.
The calculation reproduced the published count of 52 matches among 78 known positions.
A separate implementation matched every panel score profile and both complete score distributions.
A direct enumeration of all combinations also confirmed the joint distribution of the saved panel profiles.
These are internal calculation checks, not external scholarly validation.
The local freeze records the plan, input addendum, calculation, source files, and pre-score check.
The [aggregate record](ZODIAC_PANEL_CONTROL.json) records exact results and SHA-256 hashes.
It contains no answer sequence, manuscript transcription, personal contact details, or local absolute paths.

The source files and detailed calculation records remain in the ignored local research directory.
They are supporting records, not evidence of a decipherment.
