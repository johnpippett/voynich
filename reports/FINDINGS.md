# Initial findings

**The project does not show a decipherment.**

These experiments measure features of two existing transcriptions.
They do not produce plaintext or identify a language.
All results are exploratory.

The [run protocol snapshot](../docs/plans/run-design-v2.md) preserves the exact design used for these experiments.
The [verification record](verification.json) records source checks, code checks, and the exact comparison of two runs.

## Inputs and coverage

| Run | Locations | Accepted tokens | Excluded tokens | Word-order lines |
| --- | ---: | ---: | ---: | ---: |
| zl-split | 5,385 | 37,889 | 1,137 | 2,800 |
| zl-join | 5,385 | 35,146 | 1,132 | 2,783 |
| it-split | 5,215 | 37,759 | 160 | 3,355 |

`split` treats an uncertain space as a word boundary. `join` removes that uncertain boundary.
The IT input has no uncertain-space commas. Its two spacing policies give the same tokens.
Accepted tokens contain basic EVA characters after the declared normalization.
EVA represents written shapes. It does not identify linguistic letters.

## Word-order controls

The control permutes words within each eligible line, using 499 samples and seed 408.
The tests exclude incomplete lines, `<->` and `<~>` diagram interruptions, labels, and lines with fewer than three words.

| Run | Statistic | Observed | Null expectation | Holm-adjusted p |
| --- | --- | ---: | ---: | ---: |
| zl-split | adjacent_equal | 0.00951 | 0.00908 | 0.230 |
| zl-split | adjacent_near | 0.04626 | 0.04059 | 0.008 |
| zl-split | initial_gallows | 0.22036 | 0.07756 | 0.008 |
| zl-split | initial_length_difference | 0.42662 | 0.00000 | 0.008 |
| zl-join | adjacent_equal | 0.00917 | 0.00801 | 0.018 |
| zl-join | adjacent_near | 0.04151 | 0.03573 | 0.008 |
| zl-join | initial_gallows | 0.22063 | 0.07006 | 0.008 |
| zl-join | initial_length_difference | 0.47699 | 0.00000 | 0.008 |
| it-split | adjacent_equal | 0.00952 | 0.00894 | 0.132 |
| it-split | adjacent_near | 0.04339 | 0.03914 | 0.008 |
| it-split | initial_gallows | 0.22444 | 0.07628 | 0.008 |
| it-split | initial_length_difference | 0.42823 | 0.00000 | 0.008 |

`initial_gallows` measures initial EVA `k`, `t`, `p`, or `f`.
`initial_length_difference` compares the first word with the mean length of the other words.
`adjacent_near` measures word pairs with edit distance at most one, including equal words.
`adjacent_equal` measures exact repetitions.
`initial_gallows`, `initial_length_difference`, and `adjacent_near` have positive effects in all three runs.
Exact repetition does not pass the 0.01 corrected threshold in these runs.
The smallest possible unadjusted p-value is 0.002. Values at this limit do not measure the full evidence strength.
The correction covers four tests within each run. The sensitivity runs are not independent confirmations.

## Character prediction

Prediction loss measures surprise in bits per predicted unit. Lower values indicate better prediction.
The table uses raw EVA characters and includes the end-of-word symbol in the denominator.
Order zero uses no preceding character. Order three uses up to three preceding characters.

| Run | Order 0 | Order 1 | Order 2 | Order 3 | Shuffled training, order 3 |
| --- | ---: | ---: | ---: | ---: | ---: |
| zl-split | 3.8773 | 2.0900 | 1.8700 | 1.8718 | 3.2321 |
| zl-join | 3.8922 | 2.1061 | 1.8801 | 1.8839 | 3.2523 |
| it-split | 3.8821 | 2.1109 | 1.8824 | 1.8847 | 3.2414 |

Character order supplies predictive information on the selected test groups.
The aggregate JSON files also contain all compound-unit results.
Those controls shuffle compound units after segmentation. They do not shuffle characters before segmentation.
Bit rates from different symbol units are not directly comparable.
No historical-language comparison corpus was used. These scores cannot identify a language.

## Word prediction

The fixed bigram model uses the preceding word. The unigram model uses training word frequencies.
Both models score the same target positions. The bigram uses interpolation strength 10.

Loss values are bits per scored target.

| Run | Test targets | Unigram loss | Bigram loss | Shuffled-training loss | Unknown targets | Truly unseen targets |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| zl-split | 5,597 | 7.5481 | 8.3252 | 8.4425 | 20.5% | 14.9% |
| zl-join | 5,140 | 7.2264 | 7.9505 | 8.0529 | 26.1% | 19.4% |
| it-split | 6,851 | 7.5558 | 8.3495 | 8.4966 | 21.9% | 15.9% |

Unknown targets include rare training words omitted from the model vocabulary.
Truly unseen targets did not occur in the training lines.
Loss values refer to this reduced vocabulary, which combines unknown words into one symbol.
The fixed bigram performs worse than the unigram in these runs.
Original-order training performs better than shuffled training.
This result does not show that word order lacks information or that the manuscript lacks language.
Sparse counts, tokenization, and the fixed smoothing rule can affect this comparison.
The aggregate files include paired group-bootstrap intervals and every group score.

## Transcription agreement

The comparison aligns 5,214 locations.
It retains 3,760 pairs after the stated exclusion rules.
Accepted token sequences agree exactly in 2,080 eligible pairs (55.3%).
The comparison contains 47 locations on folio 84r.
Agreement does not show accuracy or independence. The transcriptions can share sources and conventions.
The public report contains aggregate counts. Complete text comparisons remain local.

## Review corrections and limits

The initial exploratory split used numeric folio numbers alone.
That split separated folios 85 and 86, which Yale identifies as one foldout.
The reported runs use `conservative-foldout-groups-v2` and join the declared candidate groups.
The `fRos` identifier also joins group 85.
Candidate unions prevent possible overlap. They do not prove physical identity.
The [physical-group report](../docs/research/physical-groups.md) separates direct evidence from these assumptions.
A complete physical-sheet map is not available.
Character models retain certain words from incomplete lines. Word-context models exclude those lines to preserve adjacency.
This difference in samples prevents a direct comparison of their loss values.

## Further work

1. Complete the image-based map of physical sheets and uncertain transcription locations.
2. Add historical-language reference texts and known ciphers with recoverable solutions.
3. Compare fixed cipher and text-generation models on new evaluation groups.
4. Require a deterministic reading method before testing a proposed translation.

No candidate key, plaintext language, or translation has passed those tests.
The [literature review](../docs/research/literature.md) records relevant sources and competing explanations.
