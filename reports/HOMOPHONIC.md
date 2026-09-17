# Homophonic feasibility pilot

The Latin cold control has a certified finite dictionary score of `370396722` over denominator `384842568`.
Its selected map has `4` test character errors in `111052` positions.
Its map matches the planted assignment for `45/46` units observed in the validation fitting input.
At least `4` optimal key completions preserve its current hits.
Other optimal maps can exist.
These runs use reference controls. They contain no manuscript measurement.

## Frozen scope

The four runs use Latin LLCT and Old Italian reference partitions.
Latin LLCT contains early medieval Tuscan legal charters.
The Old Italian source is Dante Alighieri's Comedy, an edited text by one author.
The [reference corpora](../docs/research/reference-corpora.md) document these source limits.
Their dates, genres, and editorial histories differ.
Their scores are descriptive controls and are not direct language comparisons.

Each reference uses one encryption seed, `7000`.
The cold and annealing runs within each reference use the same ciphertext.
The map family is `cap2` with 52 atomic `c##` units and two units for each letter.
Each run uses the bitset bound and a 1,000-node budget.
Annealing uses order `3`, additive smoothing `0.1`, capacity `2`, seed `408`, eight restarts, 2,000 iterations, and temperature `0.02`.
The solver fits only units that occur in the encrypted validation input.
The selected map is written before the test partition is scored.

The [frozen protocol](../docs/plans/visual-homophonic-pilot.md) is at commit `ce8b626ab3cf8147829716f7828dff7fceba6cde`.
The [solver review](../experiments/homophonic/REVIEW.md) records the search limits.
The [reference manifest](../data/reference_manifest.json) identifies the source corpora.

## Results

The objective uses exact integer token and type hits.
For a cipher word type with count `n`, the weight is `n*T + N`.
`T` is the cipher word-type count and `N` is the cipher token count.
The denominator is `2*T*N`.
These type counts are cipher word types.
Homophonic cycles can increase the number of cipher types.
Therefore, these scores are not comparable with the old injective Latin score `0.891` in the [injective report](LEXICON.md).

The primary results table shows fitted key recovery and test character errors.
A score is certified when its valid lower and upper bounds are equal.
A certified score does not prove a unique key or the correct planted key.

| Run | Reference | Fitted key correct / observed | Test character errors / total | Score certified | Optimal-key lower bound |
| --- | --- | ---: | ---: | --- | ---: |
| `latin-cold` | Latin | `45/46` | `4/111052` | yes | `4` |
| `latin-assisted` | Latin | `45/46` | `4/111052` | yes | `4` |
| `italian-cold` | Old Italian | `8/47` | `73687/130084` | no | not certified |
| `italian-assisted` | Old Italian | `23/47` | `43604/130084` | no | not certified |

The bounds table shows raw integer values.

| Run | Lower bound | Upper bound | Denominator |
| --- | ---: | ---: | ---: |
| `latin-cold` | `370396722` | `370396722` | `384842568` |
| `latin-assisted` | `370396722` | `370396722` | `384842568` |
| `italian-cold` | `90866594` | `815036950` | `897839540` |
| `italian-assisted` | `222253278` | `815036950` | `897839540` |

The fit and gate table keeps validation and test diagnostics separate.
Validation is a fit diagnostic. Test scoring uses the frozen selected map.
The declared gate requires complete recovery for observed positions and fully observed tokens.

| Run | Fit token hits | Fit type hits | Validation gate | Test gate |
| --- | ---: | ---: | --- | --- |
| `latin-cold` | `19477/19969` | `9150/9636` | fail | fail |
| `latin-assisted` | `19477/19969` | `9150/9636` | fail | fail |
| `italian-cold` | `5800/31681` | `274/14170` | fail | fail |
| `italian-assisted` | `12112/31681` | `1598/14170` | fail | fail |

A failed declared gate keeps the VMS study deferred.

## Warm-start diagnostics

The annealing runs fit a character model with fixed word boundaries.
The character-model score is separate from the exact lexicon objective.
The annealing map supplies an incumbent only.
The exact solver selects the final map by the integer lexicon objective.

| Run | Warm character score | Warm lexical score | Selected lexical score | Warm test characters correct | Selected test characters correct |
| --- | ---: | ---: | ---: | ---: | ---: |
| `latin-assisted` | 608357.381 negative log2 | `79255614` | `370396722` | 78358/111052 (70.56%) | 111048/111052 (99.9964%) |
| `italian-assisted` | 662118.217 negative log2 | `222253278` | `222253278` | 86480/130084 (66.48%) | 86480/130084 (66.48%) |

The warm character score is a negative log2 probability.
A lower character score and a higher lexical score have different meanings.
The warm and selected test columns show separate map diagnostics.

## Artifacts

The public JSON records contain full integer counts, hashes, and partition diagnostics.
The key records contain the selected maps without corpus word arrays.

| Run | Result | Key record |
| --- | --- | --- |
| `latin-cold` | [JSON](homophonic-feasibility-v1/latin-cold.json) | [key](homophonic-feasibility-v1/latin-cold.keys.json) |
| `latin-assisted` | [JSON](homophonic-feasibility-v1/latin-assisted.json) | [key](homophonic-feasibility-v1/latin-assisted.keys.json) |
| `italian-cold` | [JSON](homophonic-feasibility-v1/italian-cold.json) | [key](homophonic-feasibility-v1/italian-cold.keys.json) |
| `italian-assisted` | [JSON](homophonic-feasibility-v1/italian-assisted.json) | [key](homophonic-feasibility-v1/italian-assisted.keys.json) |

## Reproduction

Run these commands from the repository root with new output paths.
The runner refuses an existing result or key file.

```sh
mkdir -p results/reproduction-homophonic-v1
python experiments/homophonic/run_controls.py --language latin_llct --family cap2 --seed 7000 --nodes 1000 --bound-engine bitset --warm-start none --output results/reproduction-homophonic-v1/latin-cold.json
python experiments/homophonic/run_controls.py --language latin_llct --family cap2 --seed 7000 --nodes 1000 --bound-engine bitset --warm-start anneal --anneal-seed 408 --iterations 2000 --restarts 8 --temperature 0.02 --output results/reproduction-homophonic-v1/latin-assisted.json
python experiments/homophonic/run_controls.py --language italian_old --family cap2 --seed 7000 --nodes 1000 --bound-engine bitset --warm-start none --output results/reproduction-homophonic-v1/italian-cold.json
python experiments/homophonic/run_controls.py --language italian_old --family cap2 --seed 7000 --nodes 1000 --bound-engine bitset --warm-start anneal --anneal-seed 408 --iterations 2000 --restarts 8 --temperature 0.02 --output results/reproduction-homophonic-v1/italian-assisted.json
```

The four result records and four key records are linked in the tables above.
The [verification receipt](homophonic-verification.json) records checks for the published artifacts.

## Limits

The controls use finite reference lexicons and known synthetic ciphertext.
They do not estimate a false-positive rate.
They do not reject all keys, all languages, or all cipher models.
A certified finite score does not establish a historical reading.
The controls provide no decipherment or translation.
