# Stage 2 aggregate findings

**The project has not deciphered the Voynich manuscript.**

These results measure written structure and constrained model fits.
They do not identify a language, a translation, or a plaintext.
The experiments are exploratory.

## Reproduction and provenance

The [Stage 2 methods](../docs/research/stage2-methods.md) document defines the
reference partitions, models, controls, and runner limits.
Run these aggregate checks from the repository root:

```text
python scripts/build_stage2_summary.py
python scripts/check_substitution_inventory.py
python scripts/compare_reference_invariants.py
```

The report reads the aggregate JSON files and writes this file.
The result files record source hashes, code hashes, and configuration.
The [verification record](stage2-verification.json) records the execution and reproduction checks.
Use the [README](../README.md) to fetch inputs and repeat the structural runs.
Run the remaining searches in Bash with new output paths:

```bash
mkdir -p results/reproduction-stage2
for language in latin_llct italian_old; do
  python scripts/run_substitution_pilot.py --language "$language" --words 20000 --seeds {500..531} --output "results/reproduction-stage2/$language-controls.json"
  for source in ZL3b-n.txt IT2a-n.txt; do
    python scripts/run_voynich_substitution.py --language "$language" --source "$source" --output "results/reproduction-stage2/$language-$source.json"
  done
done
python scripts/check_naibbe_compatibility.py --output results/reproduction-stage2/naibbe-split.json
python scripts/check_naibbe_compatibility.py --uncertain-spaces join --output results/reproduction-stage2/naibbe-join.json
```

## Grouping and sampling

The global map has 52 source-backed groups with 35 train, 4 validation, and 13 test groups.
The prediction artifacts use 50 paragraph groups with 34 train, 3 validation, and 13 test groups.
Groups 71 and 73 have no eligible paragraph loci in these artifacts.
The prior version 2 grouping is superseded for prediction.
The `fRos` identifier maps to group 85.
The grouping version is `ivtff-bifolio-metadata-v3`. The split salt is `voynich-bifolio-408-v3:`.
The physical map manifest hash is `998cb3d6c8327ff0bdf786d52968fa3bec9f5fa9b05ba7ae56065fc9639fad72`.
The map uses provider Q/B metadata. It has no independent conservation examination.

The substitution runs select complete nonempty paragraph loci.
They exclude records with excluded tokens and `<->` or `<~>` diagram interruptions.
Each excluded locus appears in the first applicable category.
Whole-locus filters remove 10,224 otherwise accepted ZL words and 5,911 IT words from paragraph loci.
This selection can change the sample's word distribution.
The `split` and `join` spacing policies remain separate runs.

| Source | Not paragraph | No accepted tokens | Excluded tokens | Diagram interruptions | Eligible loci | Eligible words |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| ZL3b | 1,255 | 3 | 780 | 470 | 2,877 | 23,965 |
| IT2a | 1,097 | 1 | 66 | 613 | 3,438 | 28,500 |

## Character prediction

The table gives order-three loss in bits per predicted unit.
Loss denominators include the end-of-word symbol.
Each value is a point estimate. These artifacts have no character confidence interval.
Compare each observed value with the shuffled value in the same unitization.
Raw-EVA and grouped-unit bits use different units and are not directly comparable.

| Run | Raw observed | Raw shuffled | Grouped observed | Grouped shuffled |
| --- | ---: | ---: | ---: | ---: |
| zl-split | 1.8844 | 3.2542 | 2.1986 | 3.3475 |
| zl-join | 1.8905 | 3.2929 | 2.2119 | 3.4079 |
| it-split | 1.8855 | 3.2520 | 2.1970 | 3.3335 |

In each unitization, the observed order-three loss is lower than its shuffled baseline.
This result describes sequence structure. It does not identify meaning or language.

## Word-context prediction

The table gives test loss in bits per word.
Unknown targets share one symbol. These losses do not score complete word identity.
The intervals use 499 group-bootstrap draws and the 2.5 and 97.5 percentiles.
The first delta is unigram loss minus original-order bigram loss.
The second delta is shuffled-training loss minus original-order loss.

| Run | Unigram | Original bigram | Shuffled-training bigram | Unigram - original [95% CI] | Shuffled - original [95% CI] |
| --- | ---: | ---: | ---: | ---: | ---: |
| zl-split | 7.4539 | 8.1868 | 8.3251 | -0.733 [-0.793, -0.659] | +0.138 [+0.038, +0.226] |
| zl-join | 7.1930 | 7.8970 | 8.0138 | -0.704 [-0.737, -0.642] | +0.117 [+0.055, +0.173] |
| it-split | 7.5810 | 8.3483 | 8.5074 | -0.767 [-0.830, -0.687] | +0.159 [+0.054, +0.232] |

The original-order bigram has higher loss than the unigram in all three runs.
The original-order bigram has lower loss than the shuffled-training bigram in all three runs.
These comparisons do not show that the manuscript lacks language or word-order information.

## Planted substitution controls

The search recovered every held-out key assignment in 32 controls for each reference corpus.
Each control uses the same sampled text and partition as the other keys in its corpus.
The 32 keys are repeated controls on one partition, not 32 independent texts.
The key measure covers symbol types that occur in held-out text.
It does not claim recovery of unused alphabet entries.
The pilot does not estimate a false-positive rate.

| Reference corpus | Keys | Fit words | Held-out types | Held-out key assignment | Character recovery | Word recovery |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Latin | 32 | 19,969 | 23 | 32/32 (100%) | 32/32 (100%) | 32/32 (100%) |
| Old Italian | 32 | 20,000 | 21 | 32/32 (100%) | 32/32 (100%) | 32/32 (100%) |

The controls calibrate recovery power for observed key assignments. They do not show that the Voynich text uses a substitution or a reference language.
The recovered Latin control has test loss 1.8943 bits per symbol.
The recovered Old Italian control has test loss 2.4653 bits per symbol.
These values describe different texts and symbol distributions. They are calibration values, not language-rejection thresholds.
The reference texts contain Latin legal charters and Dante's poetry. Genre, date, spelling, and authorship differ from the unknown manuscript source.

## Voynich substitution runs

These runs use raw EVA units, fixed word boundaries, and an injective lowercase ASCII key.
The key is fixed before test scoring.
The runner fits the full eligible train partition and scores train, validation, and test.
This report shows the test aggregates.
The table reports test loss, lexicon hits, and the 32-key random-key range.
All loss comparisons in this table use the same raw-EVA unit track for each source and language.

| Language | Source | Test words | Observed bits/symbol | Within-word shuffle | Identity | Random-key range | Lexicon hits | Fully mapped |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Latin | `ZL3b-n.txt` | 7,162 | 5.038 | 6.197 | 6.479 | 6.209-6.977 | 10.8% | 7,161/7,162 |
| Latin | `IT2a-n.txt` | 8,272 | 5.160 | 6.162 | 6.461 | 6.243-6.987 | 8.6% | 8,271/8,272 |
| Old Italian | `ZL3b-n.txt` | 7,162 | 4.410 | 5.541 | 5.864 | 5.919-6.698 | 11.3% | 7,161/7,162 |
| Old Italian | `IT2a-n.txt` | 8,272 | 4.429 | 5.545 | 5.847 | 5.684-6.477 | 9.4% | 8,271/8,272 |

Observed test lexicon hits range from 8.6% to 11.3% in these four runs.
The within-word shuffle hit rates are lower, from 5.3% to 7.2%.
Each transcription has one unassigned test symbol type. One test occurrence remains partial.
These runs do not reject all keys or all candidate languages.
They do not produce a translation or a decipherment.

## Naibbe table compatibility

The 414 table rows encode 23 plaintext letters and produce 18,935 distinct bigram strings.
The split runs accept about 78% of tokens. Join results differ by source.
Compatibility measures whether a token has at least one reading under the fixed tables.
Ambiguity counts full candidates, including table choices. Different candidates can share plaintext.
Mean candidate counts include tokens with no reading, which contribute zero.

| Mode | Source | Compatible tokens | Ambiguous tokens | Ambiguous types | Mean candidates | Maximum |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| split | ZL3b | 29,683/37,889 (78.3%) | 14,619 | 182 | 1.227 | 4 |
| split | IT2a | 29,795/37,759 (78.9%) | 14,733 | 185 | 1.239 | 4 |
| join | ZL3b | 26,369/35,146 (75.0%) | 13,193 | 182 | 1.181 | 4 |
| join | IT2a | 29,795/37,759 (78.9%) | 14,733 | 185 | 1.239 | 4 |

The table is fixed during this run. Its construction used Voynich features, so this compatibility test is circular.
The run keeps candidate choices. It does not rank candidates or choose a language.
The small `arma` control returned one candidate for each of `ar` and `ma`.
That control does not recover plaintext from corpus tokens.
The forward control does not simulate output space-removal joins.
No corpus-wide unique plaintext result appears in this report.

## Limits

The inventory check finds 25 raw-EVA units for ZL3b and 21 for IT2a.
The grouped unitizations have 33 and 29 units. An injective map to 26 lowercase ASCII letters is not feasible for those grouped counts.
This is a conditional inventory result. It does not test another segmentation or encoding family.

The reference invariant comparison uses finite vocabularies.
It does not test one joint key, control every corpus difference, or reject a language.
A failed heuristic search does not exhaust possible keys.
No result in this report establishes a universal threshold.
