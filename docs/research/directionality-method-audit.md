# Directionality method audit

Review date: 2026-09-17.

This is a theoretical and source-code audit. It does not run the downloaded
notebook, build a corpus, or measure the Voynich Manuscript.

## Sources

- [Parisel, *Directionality of the Voynich Script*, arXiv v4](https://arxiv.org/abs/2509.10573v4)
- [Full HTML of arXiv v4](https://arxiv.org/html/2509.10573v4)
- [DOI 10.48550/arXiv.2509.10573](https://doi.org/10.48550/arXiv.2509.10573)
- [Linked Kaggle notebook request, `scriptVersionId=313890554`](https://www.kaggle.com/code/labyrinthinesecurity/voynich-script-directionality?scriptVersionId=313890554)

The arXiv source package was version `2509.10573v4`. The linked Kaggle
notebook request included `scriptVersionId=313890554`. The returned metadata
reports kernel id `91090910`, current version 33, and last run time
`2026-09-14T08:51:28.3295526Z`. Its source JSON hash was
`26c488cef60800d89b9644d4923b5deb9bc3d84ae3b65a71718da2bcc3de0980`.
The returned metadata does not repeat `313890554`, so this audit does not claim
an independent binding between that URL parameter and the numbered revision.
The notebook may have changed after the arXiv v4 results.

## Result

An n-gram direction score measures asymmetry in the tested token sequence and
estimator. It does not by itself identify physical writing or reading
direction.

For a stationary process, or for a closed cyclic sequence with consistent
counting, exact empirical conditional entropy is reversal-invariant. Symmetric
Laplace self-cross-entropy has the same invariance under the same closed-domain
conditions. Finite endpoints, word resets, asymmetric boundary symbols,
train-test mismatch, or a frozen model can create a non-zero difference
without a physical reading direction.

The paper reports a positive
`Delta = X_LTR - X_RTL` for EVA. The reported signal can show that the tested
sequence has directional statistical structure. It does not distinguish a
physical RTL reading from boundary treatment, a constructed process, or a
cipher mechanism.

## Reversal theorem

Let `x` be a sequence over alphabet `A`, with length `N`. For a closed cycle,
indices are modulo `N`. Define the count of each cyclic `k`-block `u` by

```text
n_k^x(u) = count of t in {0,...,N-1} with
           (x_t, x_(t+1), ..., x_(t+k-1)) = u.
```

Let `R x` be the reversed cycle. For `u^R`, the block in reverse order,

```text
n_k^(R x)(u) = n_k^x(u^R).
```

Reversal only permutes the block labels. Therefore the block entropies satisfy

```text
H_k(x) = -sum_u (n_k^x(u)/N) log(n_k^x(u)/N)
H_k(R x) = H_k(x).
```

The empirical conditional entropy is

```text
C_k = H_(k+1) - H_k.
```

Thus `C_k(R x) = C_k(x)`. The same result holds for a stationary process:
the reversed process has block probability `P_R(u) = P(u^R)`, which preserves
each block entropy.

For a finite linear string, reversal also permutes fixed-length windows and
therefore preserves block entropies when each block order uses its own window
normalization. The cyclic condition is needed when `H_(k+1) - H_k` is called a
conditional entropy for one common stationary context distribution.

## Fitted n-gram likelihood

For a closed cycle, let `n_(k+1)(u,a)` count a context `u` followed by `a`.
Flow conservation gives

```text
sum_a n_(k+1)(u,a) = sum_a n_(k+1)(a,u) = n_k(u).
```

The unsmoothed MLE self-cross-entropy is

```text
L_0(x) = -sum_(u,a) n_(k+1)(u,a)
         log(n_(k+1)(u,a) / n_k(u)).
```

The reversal maps every joint count to the reversed joint count and maps the
context totals by the flow identity. Hence `L_0(R x) = L_0(x)`.

With a fixed alphabet of size `V`, one symmetric Laplace estimate is

```text
p_alpha(a|u) = (n_(k+1)(u,a) + alpha) / (n_k(u) + alpha*V).
```

Its self-cross-entropy is

```text
L_alpha(x) = -sum_(u,a) n_(k+1)(u,a) log p_alpha(a|u).
```

The same count permutation and flow identity give `L_alpha(R x) = L_alpha(x)`.
This requires one fixed outcome alphabet, one symmetric `alpha`, the same
context rule, and no boundary or unknown-symbol asymmetry. The proof does not
apply to a model that keeps one orientation's fitted parameters while scoring
the other orientation.

For independent train and test draws from one stationary source, the
population entropy of the source and its reversed process is equal. A fitted
comparison can use this fact only when both orientations reverse the train and
test draws and use the same boundaries and smoothing rules. Reusing the scored
sample for fitting violates this train-test condition. Finite fitted scores can
still differ because of sampling and estimator bias. A model fit on one
orientation and frozen while scoring the reverse sequence measures model
mismatch, not physical direction.

## Exact finite reset-corpus identity

The finite reset-corpus case has a more specific result. It explains the main
source of the score difference in the retrieved notebook.

Let the corpus contain reset sequences `s`. For order `k`, keep one event for
each length-`k+1` window inside each sequence. Write `N(u,a)` for the count of
context `u` followed by token `a`, and define

```text
out(u) = sum_a N(u,a)
```

Also define `in(u)` as the count of `u` as the suffix context of a valid
length-`k+1` window. Thus, for a window `(a_0,...,a_k)`, its prefix context is
`(a_0,...,a_(k-1))` and its suffix context is `(a_1,...,a_k)`.

Fit the same symmetric Laplace score in both orientations:

```text
L_alpha = -sum_(u,a) N(u,a) log(N(u,a) + alpha)
          + sum_u out(u) log(out(u) + alpha*V).
```

Here `V` is a fixed positive smoothing constant. Reversing every reset
sequence maps each window `(a_0,...,a_k)` to `(a_k,...,a_0)`. This is a
bijection of joint events, so the first sum is unchanged. The reverse context
counts are the `in(u)` counts, with a reversal of context labels. That label
permutation does not change the sum. Therefore

```text
L_forward - L_reverse
  = sum_u out(u) log(out(u) + alpha*V)
  - sum_u in(u)  log(in(u)  + alpha*V).
```

If the score is an average, divide the right side by the same event count or
token count used in both orientations. Sum over sequences of length at least `k+1`:

```text
out(u) - in(u)
  = sum_s (1[first k tokens of s are u] - 1[last k tokens of s are u]).
```

All interior occurrences cancel in `out(u) - in(u)`.
Sequences shorter than `k+1` add no event and must add zero to both sides.
The first and last contexts determine this count imbalance.
The score magnitude also depends on interior context counts because `t log(t + alpha*V)` is nonlinear.
Equal boundary imbalances can thus produce different score differences.
The score can be non-zero when the data have no physical direction.

The retrieved notebook uses `alpha=1` and sets `V = len(counts)`, where
`counts` is the number of observed complete n-gram types. Exact reversal keeps
the same number of types, so this `V` is common to both fits. It is not the
number `|A|` of possible next-token values. If the outcome alphabet has size
`|A|`, the smoothed probabilities sum to

```text
sum_a p(a|u) = (out(u) + alpha*|A|) / (out(u) + alpha*V).
```

They are normalized only when `V = |A|` (or when the implementation defines a
different outcome set with that cardinality). The identity still describes the
code's score because it uses the same pseudo-denominator. It does not turn that
score into a normalized language-model likelihood or identify physical
direction.

## Small boundary counterexample

Use alphabet `{0,1}` and the linear sequence `001`. Fit a first-order MLE with
no end marker.

The LTR bigrams are `00` and `01`. Both use context `0`, so the fitted
probabilities are `p(0|0) = p(1|0) = 1/2`. The total self-cross-entropy is
`2` bits.

The reversed sequence `100` has bigrams `10` and `00`. Each context occurs once
and has one observed successor, so both fitted probabilities are `1`. The
total self-cross-entropy is `0` bits.

Add-one smoothing with `V=2` gives `2` bits for `001` and
`2 log2(3/2)`, about `1.1699` bits, for `100`. The difference comes from the
two exposed endpoints. It is not evidence that one physical direction is
correct.

The block entropy difference does not show this effect. Both strings have the
same unigram counts and two distinct bigrams, so `H_2 - H_1` is equal. This
example separates reversal-invariant block entropy from a finite linear
conditional likelihood.

## Source observations

The v4 paper describes sentence splits and resampling, two smoothing methods, and no end marker.
Its EVA target label comes from its earlier direction statistic.
The paper does not identify a Kaggle revision.

The retrieved notebook has these properties:

| Component | Observation |
| --- | --- |
| Split and reset | Shuffled words, not sentences |
| Uncertain text | Removes individual uncertain tokens |
| Self-fit | Fits and scores the same words |
| Laplace denominator | Uses observed n-gram types for `V` |
| Length | Uses raw length or length plus one; no end event |
| Kneser-Ney output | Prints Laplace bootstrap differences and intervals |
| Kneser-Ney floor | Uses `1e-10`; only EVA calls are active |
| Bootstrap | No NumPy seed; shuffle argument `B=2000` is not passed onward |
| Shuffle | Permutes characters within words |
| EVA label | Uses RTL from the earlier statistic |

These observations concern the retrieved source. They do not establish that it produced the historical paper tables.
The [independent review](directionality-review.md) checks the observations and mathematics.

## What the statistic identifies

The statistic can identify a directional difference under a declared
tokenization, boundary rule, estimator, and split. It can support the narrower
statement that one tested stream is easier for one fitted model under that
protocol.

It cannot identify physical reading direction without an external direction
label or a validated causal link from sequence order to physical reading. A
positive `Delta` can arise from endpoint distributions, word resets, line
selection, finite training noise, smoothing rules, tokenization, or a process
that was generated with directional constraints.

The shuffle controls test whether some sequential order is present. They do not
separate physical direction from these other sources. Each estimator must use its own score and uncertainty calculation.

## Stronger validation design

Use these predeclared checks before interpreting a VMS direction result:

1. Compute cyclic block entropy and conditional entropy on fixed token streams.
   The reversed value must match exactly.
2. Use synthetic stationary cyclic controls with known generation direction.
   Include their reversals and report exact zero differences where the theorem
   applies.
3. Keep finite linear controls separate. Rotate sequence starts, preserve word
   lengths, and report endpoint and reset contributions.
4. Use symmetric boundary treatment, or report results with explicit BOS and
   EOS conventions. Do not mix word-reset and sentence-stream estimates.
5. Fit and evaluate orientation-matched models on independent folio or
   document groups. Do not split individual words.
6. Run the actual Laplace and Kneser-Ney estimators for their own intervals.
   Publish the estimator version, seed, alphabet, event count, and source hash.
7. Do not assign EVA a gold RTL label from the same statistic. Report held-out
   `Delta` and its group-level uncertainty. Reserve classification accuracy for
   controls with an external direction label.

These checks can establish a reproducible directional statistic. They still do
not establish a decipherment or a physical reading direction by themselves.
