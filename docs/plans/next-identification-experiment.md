# Next identification experiment

Status: proposed bounded pilot, version 1.0, 2026-09-16.

The current raw-EVA substitution run is exploratory. It reports a fixed-key
search and language-model scores. It does not provide a lexical key, a source
language, or a translation. This plan tests one next identification step.

## Recommendation

Run approach A first: a globally constrained vocabulary and word-pattern
search over the existing raw-EVA units. Defer approach B until the project has
an image-backed segmentation table.

Approach A uses the current parser, raw-EVA alphabet, pinned reference corpus,
and fixed-key search. It adds one useful constraint: one key must make many
different VMS word types members of one frozen lexicon. The same key must work
on unseen physical groups. Known-key controls can measure recovery and nulls
can measure accidental lexical matches.

Approach B changes the transcription model and the cipher model at the same
time. EVA does not record every stroke or glyph component. It cannot prove
that a string is a ligature. The published ligature proposals are useful
candidate evidence, but they are not an accepted glyph inventory. Approach B
therefore has more degrees of freedom and weaker immediate controls.

This order does not rank historical explanations. It ranks the next test by
identifiability and control quality.

## Comparison of the two approaches

| Approach | Fixed claim | Useful positive control | Main false-positive risk | Decision |
| --- | --- | --- | --- | --- |
| A. Global lexicon key | One fixed injective raw-EVA key maps words to one predeclared language lexicon. | Seeded known-key Latin and Old Italian ciphertexts. | A broad lexicon and preserved word patterns can create accidental hits. | Run now. |
| B. Segmentation plus limited homophony | A fixed, source-backed tokenizer plus a bounded homophonic map expands or maps words to one language. | Seeded controls with the same tokenizer, abbreviation table, and homophonic key. | Candidate segmentation, abbreviation rules, and homophones can be selected to fit VMS output. | Defer. |

[Reddy and Knight](https://aclanthology.org/W11-1511/) report that some VMS
glyphs can be read as distinct characters or as ligatures. They also use a
transcription whose glyph choices differ from other transcriptions. This makes
segmentation a real uncertainty, not evidence for one segmentation.

[Lindemann and Bowern](https://arxiv.org/abs/2010.14697) test glyph
composition, transcription, scribal conventions, and abbreviations. Their
reported entropy differences do not select a language or a decoding key.

[Matlach, Janečková, and Dostál](https://doi.org/10.1371/journal.pone.0260948)
propose possible ligatures, including candidates involving `f`, `m`, `q`, `n`,
and `g`. Their method uses corpus heuristics and visual judgments. The paper
also describes the component choices as ambiguous. Treat its candidate list as
a versioned proposal, not as a transcription fact.

Medieval abbreviation references can constrain a later candidate table. The
[Cappelli digital lexicon](https://www.adfontes.uzh.ch/en/ressourcen/abkuerzungen/cappelli-online)
and [Abbreviationes Online](https://abbreviationes.net/) do not establish that
any VMS glyph has one of their meanings. They can supply source-backed forms
only after an image-based glyph comparison.

## A. Fixed hypothesis

Test this narrow hypothesis, `H-A`:

> For one predeclared language, one fixed injective map from raw EVA units to
> lowercase ASCII letters maps most eligible VMS word tokens to exact members
> of one frozen surface lexicon. Word boundaries remain fixed.

The map is a function `K: C -> P`, where `C` is the raw-EVA unit inventory and
`P` is `a` through `z`. It is injective. The map is shared by all physical
groups and both sides of a leaf. The model has no homophones, compound
segmentation, nulls, transposition, word repairs, per-token choices, or
folio-specific keys. It has no exception ledger for this pilot.

Use two language candidates only:

* `latin_llct`, the pinned UD 2.18 LLCT2 corpus in
  [`data/reference_manifest.json`](../../data/reference_manifest.json);
* `italian_old`, the pinned UD 2.18 Italian-Old corpus in the same manifest.

The primary lexicon for each candidate is the set of unique normalized surface
forms in its reference training partition. Use the current project rule:
NFKD, casefold, remove combining marks, and retain complete ASCII `a-z` forms.
Record rejected forms. Do not use lemmas, translations, or a morphological
generator in the primary pilot.

This is a finite corpus lexicon. It is not a complete historical dictionary.
An optional DMLBS or TLIO export is a separate exploratory track. Store its
edition, retrieval date, export method, license, and SHA-256 hash. Do not
combine lexica or select a dictionary after seeing a VMS score. The DMLBS is
focused on British Medieval Latin, and `italian_old` is one work by one author.

### Word-pattern constraints

Represent a word by its first-occurrence pattern. For example, `abca` becomes
`0120`. A lexicon candidate can match a ciphertext word only when its length
and pattern are equal. This is an upper-bound filter. It is not evidence for a
language because the filter does not identify a key.

For every candidate key, decode every eligible token with that one key. Count
an exact lexicon hit only when the complete decoded token is in the frozen
lexicon. Do not assign a different lexicon word to each token after scoring.
Repeated ciphertext types must decode to one repeated plaintext type.

Use one deterministic global solver. It may use branch-and-bound, constraint
propagation, or a bounded discrete search. It must return the key, decoded
tokens, search bound, and tie rule. It must not return only a vocabulary score.
If the solver uses a candidate cap or a node limit, freeze that value before
the VMS test. A finite search failure is evidence against the tested procedure
and settings. It is not proof that no key exists.

Use this fixed training objective:

```text
S(K) = 0.5 * exact_lexicon_token_rate(K)
     + 0.5 * exact_lexicon_type_rate(K)
```

The type rate prevents frequent repeated tokens from being the only evidence.
Report the two components separately. Use the existing train-only character
model only as a predeclared tie breaker. Do not use a semantic translator or a
human reader to select a key.

### Optional finite-domain certificate

For a frozen finite lexicon and the finite injective-key domain, an exact
branch-and-bound run may compute a certified bound for
`S* = max_K S(K)`. The run must enumerate every feasible key or attach an
admissible upper bound to every pruned branch. Record the best score, the upper
bound, the node count, the stopping status, and the complete configuration hash.
If the upper bound equals the best score, report the exact optimum. If a
predeclared project gate is above that certified upper bound, the result is a
narrow conditional result against this finite lexicon and objective. It does
not address other languages, lexica, segmentations, homophony, or keys outside
the model. A heuristic search that finds no good key has no such certificate;
it reports only the tested procedure and settings.

## Data and partitions

Use accepted paragraph-body ZL tokens as the primary VMS input. Run IT as a
separate transcription robustness check. Use strict parser output and the
declared spacing policy. Keep exclusions, source hashes, loci, and group IDs.
Do not add character-level reinterpretations during this pilot.

The current exploratory physical-group split may be used to debug the solver.
The manuscript text has already supported exploratory analyses. A new hash or
new physical-group manifest over that same viewed text does not make the text
pristine or unseen. Use such partitions only for exploratory results. A future
confirmatory claim needs genuinely uninspected evaluation material or an
independent evaluator or data source. A new physical manifest can improve
grouping, but it cannot erase prior exposure.

For each language, use the pinned reference training partition to build the
lexicon and language model. Use reference validation data for selection. Keep
reference test data for one held-out control evaluation. The Italian partitions
are canticles from one work by one author. This is a pilot limitation, not
whole-work independent validation.

## Freeze, selection, and evaluation

Freeze one manifest before reading any VMS test score. Include:

* ZL and IT input hashes, parser version, accepted-token rule, and exclusions;
* physical-group assignments and foldout status;
* the two language IDs and their lexicon source hashes;
* ASCII normalization, word-pattern definition, and token eligibility;
* the solver name, objective, candidate cap, node or proposal limit, seed, and
  tie rule;
* the primary metrics, project gates, null controls, and correction rule.

The assignment may be public during deterministic program development. Freeze
the key rules and scoring rules before reading any test output. Do not change a
lexicon, language list, normalization, solver budget, or threshold after test
scoring. If test output changes a rule, label the run exploratory and create a
new evaluation record.

Use this sequence:

1. Fit each language candidate and each search setting on VMS training groups.
2. Select one language, setting, and key on validation groups only.
3. Freeze the selected key and decode the VMS test groups once.
4. Report both language candidates. Use the maximum null score across them when
   testing a language-selected result.
5. Repeat the direction check on IT. Treat it as robustness evidence, not an
   independent confirmation.

If the current VMS test output has been viewed while developing the solver,
do not call a later score confirmatory. A new physical-group evaluation over
the same viewed text remains exploratory. Use genuinely uninspected evaluation
material or an independent evaluator or data source for a confirmatory claim.

## Controls

### Known-key controls

Run at least 32 seeded positive controls per language. Use seeds `500` through
`531`, unless a new seed range is frozen before the run. For each control,
build the lexicon and language model from plaintext reference training data
only. Do not encrypt or place training words in the solver input. Encrypt a
frozen sample of reference validation words with an injective key from the same
raw-EVA alphabet, preserve word boundaries, and fit the solver on those
ciphertext validation words. Encrypt reference test words with the same key
and evaluate the learned key once on that ciphertext test. Keep the planted key
and test plaintext evaluation-only. Use the current pilot sampling rule and
record its seed and cap.

Report exact used-symbol key recovery, reference-test symbol accuracy, token
accuracy, type accuracy, and lexicon-hit rates. A zero denominator is
`undefined`, not zero.

Run a second positive control with an input symbol that appears only in held-out
text. It tests unmapped-symbol accounting. Do not add a test-only key entry.

The [Copiale study](https://aclanthology.org/W11-1202/) is a useful historical
homophonic-cipher control reference. Its cipher has no word spacing and uses a
different cipher family. Do not treat it as a positive control for `H-A`. If a
licensed transcription is later used, it is an out-of-model stress test only.

### False-positive controls

Use the same solver, lexicon, search budget, validation rule, and test scorer.
Use 1,000 replicates per null family with seed 408 and the plus-one tail
estimate `(1 + exceedances) / 1001`.

* `N1 group-key null`: apply an independent random injective key to each VMS
  physical group. Each group keeps token lengths, within-token equality and
  repetition patterns, and ranked frequency counts up to that group's
  relabeling. Literal symbol identities and pooled corpus symbol frequencies
  change. The independent group keys break one global key.
* `N2 within-word null`: permute raw-EVA units within each token. Preserve each
  token length and unit multiset. This tests whether a score uses only unit
  counts.
* `N3 pattern-decoy lexicon`: create a lexicon with the same exact type count,
  length distribution, frequency weights, and word-pattern histogram as the
  real lexicon. Apply an independent seeded letter permutation to each decoy
  type. If a generated form collides with an earlier form, redraw with the next
  deterministic counter until the exact type count is restored. Preserve the
  source frequency weight and record the seed and collision count. A failed
  redraw is an invalid replicate, not a smaller lexicon. This preserves
  pattern geometry but removes a shared language lexicon.
* `N4 matched-unit surrogate`: for each physical group, pool its observed raw
  units, apply one seeded random permutation, and place that exact multiset into
  the original token boundaries and lengths. Preserve exact group symbol
  counts, token counts, and lengths. Remove source word types and cross-position
  order. Do not sample units from an approximate IID distribution.

The primary null statistic is the maximum held-out token hit rate across both
language candidates. Apply Holm correction to secondary metrics and to any
additional predeclared lexicon track. Do not add a null family after seeing a
score.

## Metrics and project gates

Report these measures for training, validation, and held-out test groups:

1. exact used-symbol key recovery and held-out symbol accuracy on planted
   controls;
2. mapped character, token, and type coverage on VMS;
3. exact lexicon token and type hit rates;
4. pattern-compatible upper-bound rates;
5. the train-only character-model score and the null exceedance rate.

For the pilot, use these project gates before reading the VMS test score:

* at least 90 percent of positive controls recover every used key entry;
* at least 95 percent held-out symbol accuracy on positive controls;
* a VMS candidate maps at least 95 percent of eligible test token positions;
* its held-out token hit rate is above the 99th percentile of the maximum null
  distribution and within the predeclared positive-control calibration range;
* the selected key has at least 90 percent symbol agreement across five
  training-group bootstrap fits, with no per-group key patches.

These are project gates for this pilot. They are not universal decipherment
standards. If positive controls fail, the procedure has not shown sensitivity.
If controls pass and VMS fails, report evidence against this tested fixed-key,
lexicon, search, and corpus setting only. Do not reject all keys or all
encodings.

## Approach B: deferred experiment contract

Do not run B in the A pilot. Prepare it only after an image review produces a
versioned segmentation table. The table must contain, for each candidate:

* EVA sequence or glyph identity and proposed component sequence;
* image locus, source image URL, and reviewer record;
* the external abbreviation or ligature source;
* whether the rule is visual, positional, or statistical;
* a fixed confidence label and an explicit alternative.

The smallest useful B model is:

1. a longest-match tokenizer with one frozen candidate table;
2. at most two ciphertext units per plaintext letter;
3. one global homophonic map shared by all groups;
4. at most eight source-backed abbreviation expansions, each fixed before
   language scoring;
5. no context-dependent substitutions, free nulls, or folio-specific rules.

Generate positive controls with the exact tokenizer, abbreviation table, and
homophonic map. Generate group-key, within-token, and pattern-decoy nulls with
the same unitization. Require the solver to recover the planted map and the
held-out plaintext before interpreting any VMS score.

This design tests a limited encoding model. It does not test whether medieval
scribes generally used abbreviations, and it does not assign a meaning to any
glyph from a dictionary entry. A failure can reflect wrong segmentation,
transcription, language, or search. A pass still requires a fixed historical
justification, broad reading on uninspected evaluation material or by an
independent evaluator, and independent reproduction.

## Interpretation limits

An exact lexicon hit is a string match. It is not a translation or a semantic
match. A high hit rate can result from a broad lexicon, shared word patterns,
historical spelling overlap, or a search artifact.

The primary result can support only this conditional statement: the tested
procedure found a fixed map that predicts the held-out lexical metric better
than the declared controls for the declared corpus and language. It cannot
identify authorship, topic, source location, meaning, or truth of a proposed
translation.

The experiment does not prove that VMS has no meaning. It does not prove that
the text is natural language. It does not prove that a failed finite search
has examined all keys. It tests one narrow, frozen procedure.

## Primary sources

* Reddy and Knight, “What We Know About The Voynich Manuscript” (2011),
  [ACL Anthology](https://aclanthology.org/W11-1511/).
* Lindemann and Bowern, “Character Entropy in Modern and Historical Texts”
  (2020), [arXiv](https://arxiv.org/abs/2010.14697).
* Matlach, Janečková, and Dostál, “The Voynich manuscript: Symbol roles
  revisited” (2022), [PLOS ONE](https://doi.org/10.1371/journal.pone.0260948).
* Knight, Megyesi, and Schaefer, “The Copiale Cipher” (2011),
  [ACL Anthology](https://aclanthology.org/W11-1202/).
* [Dictionary of Medieval Latin from British Sources](https://www.dmlbs.ox.ac.uk/web/dmlbs.html).
* [Tesoro della Lingua Italiana delle Origini](https://tlio.ovi.cnr.it/TLIO/).
