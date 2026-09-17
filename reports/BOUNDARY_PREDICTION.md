# Cross-boundary unit prediction

This report tests a conditional relation across existing segmented word boundaries. It does not detect boundaries. It does not show that spaces mark linguistic units.

The primary representation was the preselected `visual_six` unitization. It combines the six declared visual compounds. The raw-character result is a sensitivity result. The model predicts the current word's initial unit from the previous word's final unit. It uses separate baselines for the second, interior, and last word positions. The fixed smoothing values are `alpha=0.1` and `tau=10`. The split uses 34 train groups and 13 test groups. It uses no validation tuning.

## Held-out result

The table reports bits per target. The gain is baseline loss minus conditional loss. A positive value means lower conditional loss. Each order excess is observed gain minus the mean gain from that null. A positive value means higher observed gain.

| Source | Baseline | Conditional | Gain | Tail null excess (rank) | Same-length null excess (rank) | Matched null excess (rank) | Positive groups |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| ZL | 3.326461 | 3.123827 | +0.202634 | +0.392946 (0.01) | +0.252963 (0.01) | +0.081042 (0.01) | 10/13 |
| IT | 3.310252 | 3.127931 | +0.182321 | +0.353393 (0.01) | +0.235750 (0.01) | +0.096722 (0.01) | 8/13 |

Each null has 99 draws. The tail null uses seed 408. The same-length null uses seed 409. The matched null uses seed 410. All 99 null gains are below the observed gain for each source and null. The rank is `(1 + shuffled gains >= observed gain) / 100`. This is a descriptive rank. It is not a calibrated probability or a multiple-test result.

The tail and same-length nulls keep the first word fixed and preserve each line's target-word multiset. The same-length null also preserves target unit length at each position. The matched null keeps each target unit fixed. It swaps predecessor final units within strata matched by folio, target index, last-word flag, and both unit lengths. It does not preserve each line's word multiset. Variable-predecessor strata cover 1,892 of 6,250 ZL targets (30.3%) and 2,700 of 7,226 IT targets (37.4%). This is partial coverage. No null proves that all latent confounds are removed jointly.

`UNK` combines initial units absent from training. Its primary-track count is 3 for ZL and 2 for IT. The result concerns initial-unit prediction. A separate previous-word memory result scores full mapped words. Its bit values are not numerically comparable to this initial-unit result.

## Interpretation and limits

The result supports a held-out association between predecessor final units and current initial units under this fixed model. It does not establish a phonetic, semantic, or historical-cipher mechanism. The positive groups are not universal across the 13 test groups.

Smith and Ponzi already reported glyph associations across word breaks in 2019. The contribution here is held-out prediction with fixed line-preserving and matched predecessor nulls, not a new discovery of boundary association. See the [Smith and Ponzi preprint](https://agnosticvoynich.files.wordpress.com/2019/06/glyph-combinations-across-word-breaks-in-the-voynich-manuscript-preprint.pdf) and the [method assessment](../docs/research/next-mechanism-experiment-assessment.md).

A nested check tested pairs with both word types absent from train. `visual_six` had 214 ZL and 234 IT targets, with one `UNK` initial each. Gains were -0.079614 and -0.045933 bits per target. Raw gains were -0.022296 for ZL and +0.012886 for IT. Unseen ordered pairs (words may be known) retained `visual_six` gains of +0.141210 over 5,162 ZL targets and +0.125963 over 5,989 IT targets. This does not show a uniform rule for new words. No bootstrap or significance test was run. It gives no causal inference and does not justify filter selection. Reproduce with `PYTHONPATH=src python scripts/check_boundary_novelty.py`. See [novelty record](boundary-prediction-v1/novelty.json).

The source groups and paragraph-line filter were inspected before this run. The result is exploratory. The transcriptions and unitizations are not independent replications. Input attribution and hashes are in the [source manifest](../data/source_manifest.json). The primary result records are [ZL](boundary-prediction-v1/ZL.json) and [IT](boundary-prediction-v1/IT.json). The fixed unitizer is [the `visual_six` implementation](../experiments/homophonic/units.py).

## Exact target-remainder control

A later exploratory control holds the complete target remainder fixed after its first unit.
It also matches folio, exact target index, last-word status, and preceding-word unit length.
Empty remainders are excluded. Only cells with variation in both endpoints can affect the score.
The existing fitted table is unchanged. This is a conditional association test after observing the target remainder.
It is not a new complete-word predictor.

| Source and units | Variable cells | Targets | Exact excess per variable target | 99-draw rank |
| --- | ---: | ---: | ---: | ---: |
| ZL visual | 45 | 99 | +0.191049 | 0.01 |
| IT visual | 70 | 153 | +0.143018 | 0.02 |
| ZL raw | 32 | 76 | +0.105203 | 0.08 |
| IT raw | 41 | 95 | +0.076107 | 0.04 |

The visual cells contain only 1.6% of eligible ZL targets and 2.1% of eligible IT targets.
The rank uses 99 predecessor-label permutations with seed 411.
The exact excess uses the complete permutation expectation, calculated from each cell's predecessor-label frequencies.
Thus, the expectation has no Monte Carlo error. The rank remains a descriptive finite-draw result.
Conditioning on part of the target and selecting variable cells can induce associations.
The test assumes exchangeability within each cell. It does not establish a cause, a morpheme, or a linguistic word boundary.

The descriptive component calculation found no uniform initial-unit effect.
For visual `a/o` cells, excess totals are +8.140 bits over 14 ZL targets and +1.767 bits over 13 IT targets.
For visual `ch/sh` cells, totals are -0.288 bits over 43 ZL targets and -0.527 bits over 51 IT targets.
These are selected component totals, not separate confirmatory tests.
Identical written remainders do not establish identical meanings. These results do not justify merging initial units.
They identify small candidate sets for source-image inspection.

The [same-tail record](boundary-prediction-v1/same-tail.json) preserves the original sampled expectation and ranks.
The [component record](boundary-prediction-v1/same-tail-components.json) contains all initial-unit sets and their exact expectation contributions.

## Image check and branch limit

The image check asked whether the selected `a/o` labels describe visible sign differences or uncertain transcription choices.
The selection contains all 14 ZL and 13 IT targets in the selected visual cells.
Seven targets have the same source locus in both sets. The resulting list contains 20 distinct folio/locus pairs.
Every target has exactly two visual units. Its second unit is `r` or `l`.
Thus, these cells supply no evidence of initial alternation across longer words.

The sources disagree at both selected IT locations on f85r1.
At locus 28, IT has initial `o` and ZL has `a`.
At locus 32, IT has `a` and ZL has `o`.
The corresponding ZL lines do not supply this selected cell under the fixed filter and matching rules.
These comparisons use the corresponding image locations, not equal token indices across different segmentations.

Image inspection does not resolve every label.
Two AI readers disagree on the initial at f86v5.35, even after checking the initial without the following sign.
Five locations have provisional shape labels. Fifteen remain uncertain because of location, boundary, or classification limits.
These readings are not external palaeographic validation.
The [image audit](boundary-prediction-v1/initial-ao-image-audit.json) records every selected case, image source, and approximate review box.
No source reading or model score was changed.

This branch stops here. Further tuning would not, by itself, distinguish morphology, copying, lexical context, or transcription choices.
The result supplies no sound, meaning, key, or translation.

## Reproduction

Use a fresh checkout with Python assertions enabled:

```text
python scripts/fetch_sources.py
python scripts/check_boundary_prediction.py ZL
python scripts/check_boundary_prediction.py IT
PYTHONPATH=src python scripts/check_boundary_novelty.py
python scripts/check_boundary_same_tail.py
python scripts/summarize_boundary_same_tail.py
```
