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

## Reproduction

Use a fresh checkout with Python assertions enabled:

```text
python scripts/fetch_sources.py
python scripts/check_boundary_prediction.py ZL
python scripts/check_boundary_prediction.py IT
PYTHONPATH=src python scripts/check_boundary_novelty.py
```
