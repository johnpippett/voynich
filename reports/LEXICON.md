# Lexicon pilot v1

The pilot measures exact word hits for one fixed injective key.
An injective key maps each input symbol to one different lowercase letter.
The reference lexicons and manuscript partitions are finite.
The pilot does not decipher the Voynich manuscript.
It does not identify a language, a translation, or a plaintext.
The manuscript runs are exploratory.

## Scope and score

The runner fits a key on reference validation counts or manuscript train counts.
Each reference lexicon uses its train partition.
The score is the mean of the token hit rate and the type hit rate.
For a type with count `n`, the integer weight is `n*T + N`.
`T` is the type count and `N` is the token count.
The score denominator is `2*T*N`.
The JSON records contain the integer scores and denominators.

The solver keeps every pattern candidate.
The bitset bound is valid for every key in the tested finite domain.
Equal bounds certify the optimum score for that finite problem.
Unequal bounds leave the finite optimum unknown.
The bound does not reject all keys, all Latin, all Italian, or all cipher models.
The report keeps score proof and key recovery as separate measures.

## Reproduction and documents

The [finite lexicon protocol](../docs/plans/lexicon-feasibility-v1.md) fixes the inputs and search settings.
The [lexicon experiment notes](../experiments/lexicon/README.md) define the score and ambiguity calculation.
The [stage methods](../docs/research/stage2-methods.md) describe the reference and manuscript data limits.
Use new output paths because the runner refuses existing result and key files.
Run these commands from the repository root:

```sh
mkdir -p results/reproduction-lexicon-v1
python experiments/lexicon/run_pilot.py --kind reference --language latin_llct --node-budget 10000 --seed 500 --bound-engine bitset --output results/reproduction-lexicon-v1/latin-reference.json
python experiments/lexicon/run_pilot.py --kind reference --language italian_old --node-budget 10000 --seed 500 --bound-engine bitset --output results/reproduction-lexicon-v1/italian-reference.json
python experiments/lexicon/run_pilot.py --kind manuscript --language latin_llct --source ZL3b-n.txt --node-budget 10000 --bound-engine bitset --output results/reproduction-lexicon-v1/latin-zl.json
python experiments/lexicon/run_pilot.py --kind manuscript --language latin_llct --source IT2a-n.txt --node-budget 10000 --bound-engine bitset --output results/reproduction-lexicon-v1/latin-it.json
python experiments/lexicon/run_pilot.py --kind manuscript --language italian_old --source ZL3b-n.txt --node-budget 10000 --bound-engine bitset --output results/reproduction-lexicon-v1/italian-zl.json
python experiments/lexicon/run_pilot.py --kind manuscript --language italian_old --source IT2a-n.txt --node-budget 10000 --bound-engine bitset --output results/reproduction-lexicon-v1/italian-it.json
```

## Reference controls

Each control uses one seeded key and the complete reference test partition.
The solver does not receive the planted key.
The test character and token values measure recovery for the observed test symbols.
They do not measure recovery of unused alphabet symbols.

| Corpus | Fit mean score (reference validation) (token / type) | Test characters | Test tokens | Key assignments | Certified score | Optimal-key lower bound | Artifacts |
| --- | ---: | ---: | ---: | ---: | --- | ---: | --- |
| Latin | 89.1% (97.5% / 80.7%) | 100.0% | 100.0% | 23/23 | yes | 1 | [JSON](lexicon-pilot-v1/latin-reference.json); [key](lexicon-pilot-v1/latin-reference.keys.json) |
| Old Italian | 66.1% (86.5% / 45.7%) | 100.0% | 100.0% | 21/24 | yes | 60 | [JSON](lexicon-pilot-v1/italian-reference.json); [key](lexicon-pilot-v1/italian-reference.keys.json) |

Both controls recovered every test character and every test token.
The Italian control recovered 21 of 24 fitted key assignments.
At least 60 optimal key completions exist for the Italian control.
A count of one does not prove key uniqueness.
The Italian count of at least 60 demonstrates objective ambiguity.

These controls are positive controls for the new lexicon runner.
The earlier 32-key n-gram study is a separate experiment.
These controls do not estimate a false-positive rate.

## Manuscript runs

The four manuscript runs used the two reference lexicons and two pinned transcriptions.
Each run used all eligible v3 training words and a 10,000-node budget.
Each run reached its node budget before score certification.
The bound percentages use the integer score denominator.
The test columns report exact finite-lexicon hits for the returned key.

| Lexicon | Source | Train lower score bound | Train upper score bound | Nodes | Optimum status | Test token hits | Test type hits | Test mapped / unmapped (tokens; types) | Artifacts |
| --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: | --- |
| Latin | `ZL3b-n.txt` | 3.54% | 34.97% | 10,000 | not certified; budget exhausted | 466/7,162 | 17/2,278 | 7,161/1; 2,277/1 | [JSON](lexicon-pilot-v1/latin-zl.json); [key](lexicon-pilot-v1/latin-zl.keys.json) |
| Latin | `IT2a-n.txt` | 2.96% | 34.47% | 10,000 | not certified; budget exhausted | 352/8,272 | 28/2,638 | 8,271/1; 2,637/1 | [JSON](lexicon-pilot-v1/latin-it.json); [key](lexicon-pilot-v1/latin-it.keys.json) |
| Old Italian | `ZL3b-n.txt` | 4.46% | 35.51% | 10,000 | not certified; budget exhausted | 525/7,162 | 25/2,278 | 7,161/1; 2,277/1 | [JSON](lexicon-pilot-v1/italian-zl.json); [key](lexicon-pilot-v1/italian-zl.keys.json) |
| Old Italian | `IT2a-n.txt` | 5.36% | 35.18% | 10,000 | not certified; budget exhausted | 690/8,272 | 27/2,638 | 8,271/1; 2,637/1 | [JSON](lexicon-pilot-v1/italian-it.json); [key](lexicon-pilot-v1/italian-it.keys.json) |

The displayed manuscript lower bounds range from 2.96% to 5.36%.
The four upper bounds remain unequal to their lower bounds.
Therefore, the runs do not certify an optimum score.
The largest outward-rounded training upper bound is 35.51%.
Across these four finite training problems, every key has a score at or below 35.51% under its corresponding lexicon and partition.
This conditional bound applies to the tested training partitions and finite lexicons.
It does not apply to test scores, the full manuscript, other lexicons, or other models.
Each test partition has one unmapped token and one unmapped type.
The test hit rates are descriptive results for fixed inputs and returned keys.
Reference corpus comparisons are descriptive because genre and vocabulary differ.

Each public JSON record contains source, code, and key-record SHA-256 values.
The key records contain the returned keys without corpus word arrays.
The [verification receipt](lexicon-verification.json) records byte checks for the published artifacts.

## Limits

The manuscript runs provide no false-positive calibration.
They do not reject all keys or all candidate languages.
They do not provide a translation or a decipherment.
A finite lexicon hit does not establish historical meaning.
The results do not support a universal threshold.
