# Homophonic model prototype

This experiment tests maps where several cipher units can represent one
plaintext letter. No manuscript reading has been established.
This prototype provides no evidence of a decipherment.

The [protocol](../../docs/plans/visual-homophonic-pilot.md) defines the first
known-cipher controls. Manuscript experiments remain deferred.
No VMS run has been executed in this prototype.

## Components

* `units.py` preserves source spans for raw EVA or six selected compounds.
* `solver.py` bounds a weighted finite-lexicon objective over total maps.
* `bitset_bound.py` computes the same bound with bit operations.
* `controls.py` generates known keys and measures exact recovery.
* `ambiguity.py` counts key completions that preserve positive lexical hits.
* `anneal.py` searches for feasible starting maps with a character model.
* `run_controls.py` fits a control and writes its key before test scoring.

The scalar solver accepts any positive per-letter capacity, or `None` for no
capacity limit. The bitset engine accepts capacities `1`, `2`, and `None`.
Every cipher unit produces one letter. Word boundaries remain fixed.

A score certificate requires equal lower and upper bounds. It establishes the
optimum for the supplied finite problem. It does not establish key uniqueness
or a translation. A budget stop can retain valid bounds without an optimum
certificate.

The annealing score is a separate character-model objective. Its key supplies
a feasible starting map. The exact solver evaluates that map with its lexical
objective and keeps the full search domain.

## Checks

Run the synthetic tests from the project root:

```sh
python -m unittest discover -s experiments/homophonic -p 'test_*.py' -v
```

The tests use exhaustive small maps, direct score calculations, and known
synthetic plaintext. They do not establish performance on manuscript text.

## Reference controls

Fetch the pinned reference data with the project fetch script first.
The protocol defines four planned reference controls.
No new reference control has been executed.
Run the first cold Latin control with:

```sh
python experiments/homophonic/run_controls.py \
  --language latin_llct --family cap2 --seed 7000 \
  --nodes 1000 --bound-engine bitset \
  --output results/homophonic-feasibility-v1/latin-cold.json
```

Add these options for its separate assisted run:

```sh
--warm-start anneal --anneal-seed 408 --iterations 2000 \
--restarts 8 --temperature 0.02
```

Use `italian_old` for the second reference. Select a distinct output path for
every run. The runner refuses to overwrite a result or its key record.

Build the training lexicon from the training partition only.
Fit the map with encrypted validation words and that lexicon.
Freeze the map before test scoring.

Raw text and candidate word lists remain outside public reports. Reports
contain aggregate measurements, source hashes, settings, and synthetic keys.
