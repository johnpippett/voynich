# Falsifiable validation protocol

Status: predeclared research protocol, version 1.0, 2026-09-16.

Stage 2 note: the protocol below preserves the original proposal and first-stage implementation status.
Its provisional grouping is historical. The current implementation uses 52 source Q/B groups.
See the [Stage 2 methods](stage2-methods.md) and [results](../../reports/STAGE2.md).
The proposed confirmation gates below remain unmet. The pilot does not claim to implement all of them.

This protocol tests proposed readings of the Voynich manuscript. It separates
exploration from confirmation. It treats a reading as a model that must predict
text that the researcher did not use during development.

The protocol does not try to prove that the manuscript has meaning or that it
has no meaning. Statistical regularity alone cannot decide that question.

The repository's first implementation is an exploratory structural stage.
It does not decode the text into a language or produce a translation.
It does not select a historical language or claim a solution.
The proposed solution gates below apply to a later decoder with a separately
frozen configuration and held-out evaluation.

### Current exploratory stage

The current run has these fixed settings:

* Word-order tests use complete paragraph lines with at least three accepted
  tokens, no dropped tokens, and no `<->` or `<~>` diagram interruption. Each of 499
  null samples changes the word order within each line. The seed is 408.
* The four word-order statistics are:

  - Initial `k`, `t`, `p`, or `f` rate.
  - Initial-word length minus the mean length of the other words.
  - Adjacent words with edit distance at most one.
  - Adjacent exact repetitions.

  Holm correction covers these four tests within one run.
* Character prediction uses orders zero through three with additive smoothing
  alpha 0.1. It compares raw EVA characters with one declared compound-form
  grouping. The raw-EVA null shuffles code points within each token. The
  grouped null shuffles declared grouped units within each token and keeps
  each unit's internal order.
* Word prediction uses the declared word-bigram interpolation with tau 10. It
  compares the observed training sequence with a within-line word-order-shuffle
  training sequence. `folio_group`-level bootstrap resampling estimates
  uncertainty.

The exploratory predictive split uses
`int.from_bytes(SHA256(("voynich-408-v1:" + folio_group).encode()).digest()[:8], "big") % 10`.
Hash buckets 0 and 1 are test, bucket 2 is validation, and the other buckets
are training. The current canonical `folio_group` mapping keeps these numeric
groups together: `69/70`, `71/72`, `85/86`, `88/89/90`, `94/95`, and
`100/101/102`. The `85/86` union has direct Yale support. The other
cross-number unions are candidate relations. The mapping does not identify
every physical sheet. The mapping version is `conservative-foldout-groups-v2`.
The source alias `fRos` maps to `85`. A foldout
manifest must merge all panels of a physical folded leaf before a result is
called confirmatory. All current outputs remain exploratory until that check,
the frozen decoder protocol, and independent review are complete.

## 1. Corpus lock

Use the ZL and IT EVA transcriptions in IVTFF format as the primary inputs.
Record the exact URL, file name, IVTFF version, retrieval time, and SHA-256
hash for every input. Keep the raw bytes unchanged. A changed source is a new
corpus version. It must have a new split manifest.

Use the IVTFF page and locus metadata. Keep paragraph text, labels, circular
text, and radial text as separate strata. Exclude Latin or other non-Voynich
annotations from the primary corpus. Report every exclusion with its locus.

The parser must map each normalized symbol and token to its source file, folio,
side, locus, and character span. A result without this map is not reproducible.

This is a future confirmatory requirement. The current parser handles basic EVA
input. It keeps the source locus and raw text. It rejects uncertain or
unreadable tokens. It supports the declared `uncertain_spaces='split'` and
`uncertain_spaces='join'` policies. It does not yet keep character spans or
implement the other uncertainty modes below. First-stage reports must state
this limit.

### Physical grouping

The observation unit is a locus. The future confirmatory split unit is a
physical group. The current exploratory split unit is a canonical
`folio_group`.

* Put the recto and verso of one leaf in one `leaf_id`. Never split `f12r` and
  `f12v` between partitions.
* Put every panel of one folded leaf in one `foldout_id`. Never split a folded
  panel from its other panels.
* Put all loci from a group, including labels, in the same partition. Train body
  and label models separately. A label must not become a training feature for
  body text on the same group.
* If the IVTFF metadata does not identify a foldout, add a versioned manifest
  from the manuscript images before the confirmatory run.

The first-stage split uses the canonical `folio_group` mapping listed above.
It joins recto and verso surfaces with the same number and applies the
conservative cross-number unions. The `85/86` union has direct Yale support.
The other unions remain candidate relations. This map does not identify every
physical sheet. Audit known foldouts before a split is used for confirmation.

Keep a second, optional analysis that uses body text only. This prevents short
labels from driving results for paragraph text. Never silently mix the two
analyses.

### Future confirmatory transcription uncertainty

The first-stage parser uses strict rejection and declared spacing policies. It
does not yet run the alternative-reading modes in this section.

For a future confirmatory decoder, do not replace uncertainty markers by
researcher judgment after seeing a result. Run these fixed modes:

1. `strict`: remove a token that contains an unresolved alternative or an
   illegible symbol.
2. `first`: select the first alternative in each marked alternative.
3. `second`: select the second alternative where one exists. Retain the first
   option when no second option exists.
4. `mask`: replace each uncertain character by one fixed unknown symbol.

The parser must report token and character coverage for every mode. A
confirmatory result must have the same direction of effect in `strict`,
`first`, and `second`, or the result is transcription-sensitive. The `mask`
mode is a robustness report. It cannot rescue a failed confirmatory result.

Do not merge EVA signs, split EVA signs, or change word separators during a
confirmatory run unless that operation is part of the predeclared hypothesis.
Record each such operation in the transformation manifest.

## 2. Frozen partitions

The first-stage predictive split is fixed by the hash rule in the current
exploratory section above. It has about 70 percent training, 10 percent
validation, and 20 percent test groups. It is not stratified.

For a future confirmatory decoder, create a manifest from unique physical
groups before training a decoder. Use a stable hash or an explicitly listed
assignment, and record the exact proportions. The manifest must join recto,
verso, and every panel of one folded sheet. A decoder can reuse the first-stage
manifest only after the foldout audit. Otherwise, use a new frozen manifest.
Do not describe either split as stratified unless the manifest has that
property.

If a future split leaves a section with fewer than three groups, mark that
section as sparse. Do not claim section-level generalization for a sparse
section. Keep the test list private to the final evaluator until all model
choices and exception rules are frozen.

The partition manifest must include the input hashes, seed, grouping rules,
strata, group IDs, and a manifest hash. A later run must use the same manifest
for the same corpus version. A new seed gives a variance analysis. The analyst
must select the split before viewing results.

Use `train` to fit mappings, tokenizers, language models, and hyperparameters.
Use `dev` for model selection. Use `test` once for the primary report. Do not
inspect test translations while changing a method. If test output was viewed,
mark that run exploratory and create a new frozen test set for confirmation.

Run a secondary leave-one-section-out analysis. Treat it as a generalization
check, not a replacement for the physical-group test.

## 3. Future candidate-system contract

Every proposed reading must provide the following deterministic functions:

* `fit(train, manifest, hypothesis_config)` returns a mapping, tokenizer,
  language choice, and exception ledger.
* `decode(locus, mapping)` returns output, coverage, and every fallback event.
* `score(output, split)` returns each predeclared metric and its denominator.

The same input bytes, manifest, configuration, and seed must produce the same
output. Do not use folio-specific maps unless the hypothesis explicitly states
that the manuscript uses independent local codes. Such a model must pay for
each local code in the exception ledger and must pass the same held-out test.

### Exception ledger

An exception is a token, sign, spelling, word boundary, or grammar rule that
does not follow the fixed mapping. The ledger must contain the source locus,
reason, rule, author, and whether the rule was frozen before the test.

Count exceptions by token and by character. Do not hide exceptions in a
dictionary, normalization step, language-model vocabulary, or human spelling
correction. A reading with an open-ended exception list is not a fixed
decipherment.

## 4. Future confirmatory metrics

Report all metrics for `train`, `dev`, and `test`, with group bootstrap intervals
where possible. Report body and label strata separately. Report results for
each uncertainty mode and for ZL and IT where loci can be aligned.

### M1. Held-out coverage

`coverage = decoded token positions without fallback or exception /
eligible token positions`.

Report character coverage, token coverage, and unseen-token coverage. A model
can look accurate when it refuses difficult tokens. Coverage can prevent this
error.

### M2. Mapping determinism

For input types that occur more than once, report the fraction that receive one
output under the fixed map. Report conflicting assignments, collision rate, and
exception rate.
Compute these values on unseen groups. Do not count a language model's chosen
word as evidence for a deterministic map.

### M3. Held-out predictive score

For a candidate historical language, compute character or word cross-entropy
in bits on decoded test output. Fit the scoring model only on the declared
training reference corpus and training groups. Compare the candidate with the
same model class applied to the undecoded EVA stream and to every null control.

If no fixed, versioned historical-language reference corpus exists, omit this
metric. Do not call an intrinsic EVA n-gram score a language identification.

### M4. Section generalization

When section labels are fixed before analysis, train a simple classifier on the
decoded training output and predict test sections. Report macro-F1 and a group
bootstrap interval. Compare with the raw EVA stream and order-destroying nulls.

Section prediction can show topical structure. It cannot prove a translation.
An encoding can keep section information without exposing its language.

### M5. Transcript agreement

Align the ZL and IT loci by physical group and locus. Report exact output-token
agreement and normalized edit similarity for unambiguous aligned material.
Report disagreement coverage separately. A result that appears in one
transcription only is transcription-dependent until resolved from manuscript
images.

The first implementation uses these five metrics. Do not add a metric to the
confirmatory family after viewing test output.

## 5. Future baselines and null controls

Run every candidate method against these controls with the same partition,
selection budget, and scoring code.

* `B0 identity`: score the original EVA tokens without a proposed decoding.
* `N1 word-order shuffle`: permute word order within each physical group while
  preserving group word counts, token lengths, and token frequencies.
* `N2 character-order shuffle`: permute characters within each token while
  preserving each token's character multiset and length.
* `N3 group-label shuffle`: permute section labels between physical groups while
  preserving the label counts. Use this only for section prediction.
* `N4 cross-transcript pairing shuffle`: break ZL-IT locus pairing while
  preserving each transcript's group and locus counts.
* `N5 synthetic cipher controls`: create known-language text with the declared
  cipher family, then pass it through the complete search and frozen split.
  This measures whether the method can recover a real planted solution.
* `N6 matched generative surrogates`: generate strings from the fitted length,
  character-frequency, and low-order transition distributions. Keep group
  sizes, but remove source-language words.

For confirmatory permutation tests use 10,000 permutations and the plus-one
estimate `(exceedances + 1) / (10,000 + 1)`. Use the same random seed and list
of permutations for all compared candidates. A significant result against one
null does not reject the other nulls.

N1 and N2 test whether word order or character order carries the result. N5
tests recovery on data with a known answer. N6 tests whether a local generator
can explain the result without a language. None of these controls proves that
the manuscript is nonsemantic.

## 6. Current exploratory outputs

The first implementation reports three exploratory analyses. They do not test
the proposed solution gates and must not be called decipherment evidence.

### X1. Within-line word-order tests

Use only complete paragraph loci with at least three accepted tokens, no dropped
tokens, and no `<->` or `<~>` diagram interruption. For each of 499 permutations, shuffle
words within each line with seed 408. Test these four statistics:

* Initial `k`, `t`, `p`, or `f` rate.
* Initial-word length minus the mean length of the other words.
* Adjacent words with edit distance at most one.
* Adjacent exact repetitions.

Use a greater tail for the three enrichment statistics and a two-sided tail for
the length difference. Apply Holm correction to these four tests within the run.

These tests reject only the stated within-line exchangeability model. They do
not test a language, a cipher, or semantic content.

### X2. Character prediction

Fit character orders zero through three with additive smoothing alpha 0.1.
Compare raw EVA characters with one declared compound-form grouping. For the
raw-EVA null, shuffle code points within each training token. For the grouped
null, shuffle declared grouped units and keep each unit's internal order. Use
the fixed `folio_group` split. Report unknown symbols, end symbols, and bits per
symbol.

### X3. Word-context prediction

Fit the declared interpolated word-bigram model with tau 10. Compare observed
training context with a training set made by shuffling words within each
paragraph line. Use `folio_group`-level bootstrap resampling for uncertainty.
Keep the same test groups and scoring code for the two conditions.

All X1-X3 settings, scores, and null results are exploratory structural
observations. They can motivate a future decoder, but they cannot show a
language, a translation, or the absence of meaning.

## 7. Future confirmatory decoder experiments

### E0. Corpus and uncertainty audit

After the parser adds the future source map and uncertainty modes, parse the two
files. Report coverage, marker counts, locus counts, group counts, and ZL-IT
disagreement. Stop the confirmatory run if the parser cannot reproduce these
counts from the stored hashes.

### E1. Held-out decoding benchmark

Use `train` for each registered hypothesis. Select only on `dev`. Freeze the
configuration. Evaluate once on `test`. Report M1, M2, and M3, plus all
baselines and N1, N2, N5, and N6. Each proposed candidate must show a better
score than B0 and survive the relevant order and synthetic controls after
multiple-comparison correction.

### E2. Physical generalization benchmark

Run E1 again by holding out each major section in turn. Keep recto-verso and
foldout groups intact. Report the range of held-out coverage and predictive
score. A method that works only on one section is a local model, not a broad
reading.

### E3. Transcript and uncertainty robustness

Run the frozen E1 configuration across ZL, IT, and the four uncertainty
modes. Report M5 and the change in every primary effect. Do not retune a map
for a transcript or uncertainty mode after seeing its test output.

### E4. Content and nonsemantic comparison

Run M4 when section metadata is available. Compare the decoded candidate with
B0, N1, N3, and N6. Fit the registered procedural or generative hypothesis on
the same training groups. If it predicts the held-out statistics as well as a
language candidate, retain the two explanations and do not claim a translation.

## 8. Multiple comparisons and reporting

Declare the hypothesis IDs, language candidates, model classes, metrics,
uncertainty modes, and nulls before the confirmatory run. Treat each
hypothesis-by-metric-by-mode comparison as a reported comparison.

Use Holm correction within each confirmatory family at alpha = 0.01. Report
uncorrected values, adjusted values, effect sizes, intervals, denominators,
and all failed tests. Use exploratory labels for analyses that were added after
test output was viewed. Do not convert an exploratory pattern into a confirmed
claim by running the same test again.

Do not use a single p-value to show a decipherment. A result must also meet the
proposed solution gates below and survive independent reproduction.

## 9. Proposed solution gates

Call a reading a solution only when every proposed gate passes.

The numerical values below are proposed project gates. They are not universal
standards for decipherment. Freeze the values and their denominators before
the final test, or label the run exploratory.

1. **Fixed method.** The mapping, tokenization, language model, and exception
   rules are deterministic, versioned, and frozen before the final test.
2. **Bounded exceptions.** The ledger is complete, independently justified,
   and small enough that it cannot encode the answer. The report must state a
   proposed numeric exception and coverage thresholds before testing. One
   proposed starting point is at most 1 percent of eligible body tokens and at
   least 95 percent body-token coverage on unseen groups. The report must give
   a written pretest reason for a different threshold.
3. **Historical language fit.** The proposed language has independent historical
   evidence for the manuscript's time and setting. Its grammar, morphology,
   and lexicon are documented outside the proposed decoding. A language chosen
   only because it gives plausible words fails this gate.
4. **Blind unseen reading.** A reader who did not prepare the map receives only the
   frozen method and an unseen folio set. The reader must produce a continuous
   reading with word boundaries and grammar, and must report uncertainty before
   seeing a proposed translation. Independent evaluators must meet a
   predeclared agreement threshold on a predeclared sample.
5. **Broad coverage.** The method must meet the frozen coverage threshold across
   major sections, Currier-language classes, body text, and labels where labels
   are claimed. It must pass physical-group and leave-one-section-out tests.
6. **Independent reproduction.** A second person or implementation must obtain
   the same map, exceptions, held-out scores, and blind-reading result from the
   raw hashes and manifest.

Round-trip reconstruction is necessary for some cipher models, but it is not
evidence of meaning by itself. A language model that produces plausible words
or translations is not evidence of a solution without the fixed-map,
held-out, historical, blind, coverage, and reproduction gates.

Failure of a proposed gate rejects that candidate reading. It does not prove that the
manuscript is meaningless, random, or impossible to decipher.

## 10. Known pitfalls

* **Physical leakage:** Recto-verso pairs and folded panels share layout,
  scribal, and topical information. A line-level split gives false confidence.
* **Parser leakage:** Keeping a token, alphabet, or character in the vocabulary
  because it appears in test data inflates prediction. Build vocabularies on
  training groups only, and map unseen symbols to a fixed unknown symbol.
* **Exception leakage:** A spelling correction or special sign rule can encode
  the answer. Freeze the ledger before the final test and count every entry.
* **Section leakage:** Section names, folio metadata, and labels can reveal a
  target class. Keep body and label models separate and compare with raw-EVA
  and label-shuffle controls.
* **Transcript drift:** ZL and IT do not provide identical readings. Record
  disagreement coverage and never treat one file as ground truth for the other.
* **Small strata:** Rare sections and labels have low power. Report their
  denominators and do not generalize from them.
* **Search inflation:** Testing many languages, maps, and normalizations makes
  one plausible output likely by chance. Lock the candidate list and correct
  for all comparisons.
* **Plausible text:** A language model can turn partial or arbitrary symbols
  into readable words. It cannot replace a fixed map and blind held-out reading.
* **Entropy overreach:** Low or high entropy describes the selected encoding.
  It does not prove language, randomness, authorship, or no meaning.
* **Round-trip overreach:** A flexible encoder can reconstruct its input by
  construction. Independent language and reading tests are necessary.

## 11. References and data rules

Use the IVTFF specification and transcription documentation maintained at
<https://www.voynich.nu/transcr.html> and
<https://www.voynich.nu/software/ivtt/IVTFF_format.pdf>. Cite the exact input
files used, not a mutable web page alone.

Previous statistical work can support a test, but it cannot replace held-out
validation. For example, Montemurro and Zanette report information-theoretic
structure in the manuscript (PLOS ONE 8(6), e66344,
<https://doi.org/10.1371/journal.pone.0066344>). Treat such structure as a
descriptive observation, not as a translation.

Claims about cipher recovery must state their model class and test data. For an
example of a model-specific Voynich claim, see Hauer and Kondrak's
monoalphabetic and anagrammed-substitution study
(TACL 4, 2016, <https://transacl.org/ojs/index.php/tacl/article/view/821>).
