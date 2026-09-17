# Directionality review

Review date: 2026-09-17.

This review checks the mathematical claims and source observations in the
[directionality method audit](directionality-method-audit.md). It does not run
the notebook or fit a corpus.

## Sources

- [Parisel, *Directionality of the Voynich Script*, arXiv v4](https://arxiv.org/html/2509.10573v4)
- [Linked Kaggle notebook](https://www.kaggle.com/code/labyrinthinesecurity/voynich-script-directionality?scriptVersionId=313890554)

The retrieved notebook source has SHA-256
`26c488cef60800d89b9644d4923b5deb9bc3d84ae3b65a71718da2bcc3de0980`.
Its returned metadata reports current version `33`. The metadata does not
repeat `313890554`. Treat the source observations as a version-33 retrieval.
Do not claim an independent binding to that URL parameter.

The current method audit has SHA-256
`fd6d6e0f8cb4e2728fcd9bbf85b4508e9eddb9ea15592e0de2ffebf1db16f2a5`.
The retrieved metadata file has SHA-256
`2e21f4bc1de1fe6733033d0a8ef7850c51683da1051ce3b837ef285cabef5adb`.

## Mathematical checks

The cyclic reversal theorem is correct. Reversal permutes each cyclic block
label. It therefore preserves every block entropy and their difference.

The symmetric Laplace self-fit theorem is correct for a closed cycle. It needs
the same outcome set, smoothing value, context rule, and boundary treatment.
It does not apply when one fitted model scores the reversed stream.

The finite reset-corpus identity is also correct. Let `out(u)` count windows
with prefix context `u`. Let `in(u)` count windows with suffix context `u`.
For `F(z) = z log(z + alpha*V)`, the exact score difference is:

```text
L_forward - L_reverse = sum_u F(out(u)) - sum_u F(in(u)).
```

For each reset sequence, `out(u) - in(u)` equals one first-context indicator
minus one last-context indicator. Only this difference is fixed by the ends.
The score magnitude also depends on interior counts because `F` is nonlinear.
Avoid wording that says boundary marginals alone determine the score magnitude.

The train-test expectation needs explicit conditions. State independent train
and test samples from one stationary process, with equal reset and event rules.
Refit both orientation models after reversal. Stationarity alone does not
justify equality for an arbitrary finite corpus split.

The notebook does not establish this independent-sample condition. It shuffles
flattened word tokens from one input corpus and partitions them into two lists.
Related words and local line patterns can occur in both lists.

The `001` counterexample is correct. Its unsmoothed scores are 2 and 0 bits.
With add-one smoothing and `V=2`, the reversed score is
`2 log2(3/2)`, about 1.1699 bits. The entropy difference remains invariant.

## Source findings

The source observations in the method audit match the retrieved notebook; they
remain source observations and do not support exact reproduction without a
versioned run record.

## Inference boundary

The statistic measures order asymmetry under a declared tokenization, reset
rule, estimator, and split. It does not identify physical writing or reading
direction.

The EVA test label is assigned as RTL from the earlier direction statistic.
Its accuracy is therefore not an independent physical-direction test.

Shuffle controls can show loss of sequential structure. They cannot separate
physical direction from boundary treatment, tokenization, or a constructed
process. The result does not establish a language, decipherment, or translation.
