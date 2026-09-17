# Global lexicon experiment

This experiment tests one fixed substitution key against a finite word list.
The word list is called a lexicon. A lexical hit is an exact word match.
A lexical hit does not establish a translation.

The experiment uses one injective key. Each ciphertext symbol has one plaintext
letter, and different ciphertext symbols have different plaintext letters.
Word boundaries and symbol units remain fixed.

## Score and bounds

For each input word type, the solver adds its weight when the complete decoded
word occurs in the lexicon. All weights are nonnegative integers.

The pilot gives equal weight to the token hit rate and the type hit rate.
Tokens include repetitions. Types are distinct words.
For a type with count `n`, its weight is `n*T + N`.
Here, `T` is the number of types and `N` is the number of tokens.
The score denominator is `2*T*N`.

Candidate words must have equal lengths and equal repeated-letter patterns.
Each partial key removes candidates that conflict with its assignments.
The remaining candidate weights give an upper bound for that branch.
A complete key supplies a feasible lower bound.
The search retains the maximum upper bound across all remaining branches.
All bound arithmetic uses integers.

Equal bounds prove the optimum score for this finite problem.
A node limit can leave unequal bounds. That result does not prove that every
key fails.
The lexicon does not include every word in a historical language.
Even a proven low upper bound cannot reject the whole language.

## Score and key ambiguity

An optimum score does not establish a unique key.
The ambiguity calculation fixes only assignments used by current positive-weight
hits. Every injective completion preserves those hits and cannot reduce the score.
If that score is a proven optimum, every counted completion is also optimal.

With `C` ciphertext symbols, `P` plaintext letters, and `U` fixed symbols, the
completion count is `(P-U)! / (P-C)!`.
This count is a lower bound. Other optimum keys can change the fixed assignments.
A count of one does not prove uniqueness.

## Validation scope

The tests compare small problems with direct key enumeration.
Known-text trials keep the planted key outside the search.
They measure score bounds and letter recovery separately.

The current pilot tests computational feasibility.
It does not implement the full [identification study](../../docs/plans/next-identification-experiment.md).
That proposed study requires additional controls and evaluation gates.
The manuscript partitions remain exploratory because the text has already been examined.

Run the experiment tests:

```sh
PYTHONPATH=src:. python -m unittest discover -s experiments/lexicon -p 'test_*.py' -v
```

Full corpus inputs and private run outputs remain outside the public repository.
