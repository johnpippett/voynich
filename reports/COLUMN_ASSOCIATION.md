# Text-column similarity and line order

Both pinned transcriptions show a small text-column association in the selected Currier B lines.
Words at selected columns are more similar than other source words of the same length.
The line-order control does not meet the declared criterion for an additional neighbor effect.
These results do not identify copying, a language, or plaintext.
The column calculation uses transcription character counts, not physical image coordinates.
We make no claim of a first discovery.

## Competing explanations

The first comparison asks whether source-word positions are exchangeable within each source line, after matching word length.
The alternative has additional word similarity at the selected column.
Vocabulary that depends on line position can cause this association.
For example, initial words can share forms across lines without a direct relation between those lines.
The comparison does not keep initial, final, and interior source positions in separate control sets.

The follow-up comparison keeps each selected line intact and changes line order within its folio.
It asks whether the recorded order supplies additional similarity beyond these complete-line patterns.
Paragraph structure, changing topics, vertical layout, and copying can all affect this comparison.
Neither comparison can identify copying as the cause.

## Sources and selection

The inputs are [ZL3b-n](https://www.voynich.nu/data/ZL3b-n.txt) and [IT2a-n](https://www.voynich.nu/data/IT2a-n.txt).
The [aggregate record](COLUMN_ASSOCIATION.json) gives their SHA-256 hashes.
EVA is a transcription of written forms. Its characters are not established letters or sounds.

Selection uses the existing parser, strict word-span check, and version 3 group split.
It includes only Currier B paragraph lines in the existing test groups, with at least three complete words.
It excludes uncertain signs, uncertain word boundaries, incomplete words, and drawing interruptions.
Each selected line uses the nearest earlier selected line on the same folio as its source.
Removed records can separate these lines. The experiment does not require immediate physical adjacency.

| Source | Selected lines | Folios | Line pairs | Eligible targets | Candidate targets | Coverage |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| ZL | 169 | 20 | 149 | 1,042 | 1,353 | 77.01% |
| IT | 417 | 21 | 396 | 2,948 | 3,758 | 78.45% |

Both sources cover five groups: `57`, `75`, `77`, `85`, and `106`.
The groups follow the provider's quire/bifolio metadata. This experiment does not independently verify their physical membership.
The largest group supplies 33.21% of eligible ZL targets and 27.58% of eligible IT targets.
Before scoring, both sources passed fixed limits for target count, coverage, group count, and group concentration.
These limits were 200 targets, 25% coverage, three groups, and at most 50% from one group.

Only 65 ZL pairs and 308 IT pairs have consecutive source-record indices.
These index gaps do not independently establish physical line distances.
The source subsets differ substantially. The two transcriptions describe one manuscript and are not independent historical replications.
The project has examined other statistics on these test groups. This study is exploratory.

## Fixed statistic

The target column equals the sum of earlier target-word lengths, plus one character for each following space.
Starting at the source-line beginning, add each word length plus one.
Select the first source word whose cumulative value is at least the target column.
If none qualifies, use index `min(last_source_index, target_word_index)`.
This inclusive rule follows the pinned generator helper. At an exact boundary, it can select the preceding word.
Raw character lengths count `ch` and `sh` as two characters each.

For target word `x` and selected source word `y`, similarity is:

`q(x, y) = 1 - Levenshtein(x, y) / max(len(x), len(y))`.

Insertion, deletion, and substitution each have cost one.
Controls are all other word positions on that source line with the same character length as `y`.
Repeated spellings remain separate control positions. A target without a control is omitted.
The target value is its selected similarity minus its mean control similarity.
The final statistic gives each eligible target equal weight.

| Source | Mean similarity excess | 95% group bootstrap interval | Range after removing one group |
| --- | ---: | --- | --- |
| ZL | 0.017448 | [0.001142, 0.027227] | [0.010965, 0.023065] |
| IT | 0.015926 | [0.007872, 0.026343] | [0.011158, 0.018585] |

The bootstrap samples the five groups with replacement 9,999 times, using seed 170918.
Each draw divides the summed group excess by the summed eligible-target count.
The interval uses sorted draw indices 249 and 9749. Five groups provide limited information about variation between groups.
Both sources have positive bootstrap lower endpoints and positive leave-one-group-out estimates. Two individual ZL groups have negative excesses.

Interior source positions contribute 0.012490 to the ZL total mean and 0.011308 to the IT total mean.
This accounting does not establish an interior-only effect: those targets still have controls from other position roles.

## Line-order control and stop decision

We made 9,999 uniform permutations of complete selected lines within each folio, using seed 170919 separately for each source.
Folios use lexical order. Each draw starts from the recorded line order and shuffles each folio independently.
Words keep their original positions within each line. Lines stay on their original folio.
The statistic uses successive lines in each new order, without a connection from the last line to the first.
The first line supplies a source but has no preceding target pair. The eligible-target denominator can change.

| Source | Recorded-order score | Permutation mean | Difference | One-sided p-value |
| --- | ---: | ---: | ---: | ---: |
| ZL | 0.017448 | 0.009623 | 0.007825 | 0.1586 |
| IT | 0.015926 | 0.008423 | 0.007502 | 0.0558 |

The p-value is `(1 + draws at least as large as the recorded score) / 10000`.
It applies only to exchangeability of the selected complete lines within their folios.
The central permutation quantiles are [-0.005940, 0.025315] for ZL and [-0.000822, 0.017807] for IT.
They describe the permutation distribution. They are not confidence limits for an effect.
Eligible-target counts range from 998 to 1,083 for ZL and 2,821 to 2,961 for IT.

Sixteen ZL folios and twenty IT folios contain a line pair.
Four isolated ZL lines and one isolated IT line cannot contribute a pair under any permutation.
All group-removal differences remain positive: 0.001010–0.011548 for ZL and 0.002704–0.011576 for IT.
But neither p-value meets the fixed limit of 0.05. The declared rule requires both sources to pass.
We stopped this statistic without new filters, unit representations, or control rules.

This result does not prove line exchangeability or absence of a neighbor effect.
This comparison makes no generator-specific prediction. It cannot reject all copying models.
It shows that the initial column association alone does not establish a special relation with the preceding qualifying line.
The follow-up is exploratory because the initial association informed its design.

## Generator calibration

Before manuscript scoring, we checked whether the statistic detects a configured source-position preference in an author's generator.
The alternative was that variation or other generator rules prevent detection with this statistic.
We used [Timm's repository at revision a6ede22](https://github.com/TorstenTimm/SelfCitationTextgenerator/tree/a6ede2202dd7ad6285ce2c007bf22c2a0e7709b7).
The [paper record](https://doi.org/10.1080/01611194.2019.1596999) supplied the abstract and metadata. The full publisher article was unavailable.
We do not assume that repository settings reproduce the paper's experiment.

We compiled unchanged Java source and generated 20 paired seed runs, with source-position thresholds 28 and zero.
Other settings stayed fixed, including 1,200 output lines, 29 lines per page, and the author's initial line.
The initial line comes from the manuscript. The metric excludes it as both a target and a source.

Threshold zero does not disable the source-position branch.
Before mode selection and filters, the ordinary branch probabilities are 29% at threshold 28 and 1% at threshold zero.
The corresponding line-initial probabilities are 15% at threshold 28 and 11% at threshold zero.
Other source choices and word changes remain active.
The calculation uses every earlier output line within fixed blocks of 29 lines.
These blocks do not reconstruct internal generator pages or selected word ancestry.

All 20 paired differences are positive. Their mean is 0.006303, with 95% bootstrap interval [0.005644, 0.006926].
The bootstrap samples 20 seed pairs with replacement 9,999 times, using seed 170917 and sorted indices 249 and 9749.
This establishes sensitivity to that parameter change in the pinned generator.
It does not calibrate a manuscript rejection threshold or identify the manuscript's production method.
The manuscript uses a different line-selection rule and different text geometry.

## Verification and records

We fixed each plan, adapter, source pin, and calibration configuration before its scoring run.
A separate AI calculation reproduced all 40 synthetic output measurements and the paired comparison.
It used separate position and edit-distance calculations. Differences were below 2e-16.
A second saved calibration verifier reproduced all 40 measurements with separate edit-distance and column calculations.
A separate AI calculation reproduced the manuscript selection, counts, group sums, uncertainty intervals, and position-role summaries.
It reused the parser, strict span extractor, and group selector, but rebuilt the column and similarity calculations.
The separate calculation also reproduced all 9,999 line-order statistics and eligible-target counts for each source.
It matched the permutation means, quantiles, p-values, and group-removal differences.
These calculation checks are not external scholarly validation or independent transcription.

Local records remain in `results/timm-column-calibration-v1/`.
The public aggregate record contains counts, scores, and hashes, without manuscript words or complete lines.
