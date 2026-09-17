# Narrow monoalphabetic substitution experiment

Status: proposed future confirmatory experiment; a smaller pilot comes first,
version 1.1, 2026-09-16.

This experiment tests one narrow claim:

> One fixed input unit maps to one plaintext letter through an injective,
> monoalphabetic substitution. Word boundaries remain fixed.

The model has no homophones, nulls, transposition, anagramming, context rules,
folio-specific keys, spelling exceptions, or language-model corrections. A
failed test is evidence against the tested procedure and exact model settings
for the tested language and unitization. It does not establish that no key
exists, or reject another search procedure, corpus choice, language model,
unitization, encoding, or the possibility of meaning.

The experiment must recover keys on planted ciphertexts. A search that only
finds a high language score is not a substitution recovery method.

## 1. Two fixed input unitizations

Run the experiment separately for these tracks:

* `raw_eva`: each accepted lower-case EVA character is one input unit.
* `compound_eva_v1`: scan each token from left to right with longest match.
  The fixed compound list is `cth`, `ckh`, `cph`, `cfh`, `ch`, `sh`, `iin`,
  and `in`. An unmatched character remains one unit.

Do not tune the compound list on any split. Record the list and its hash in the
run manifest. A compound unit still maps to one plaintext letter in this
experiment. It does not expand into several plaintext letters.

### Alphabet cardinality gate

Let `C` be the input-unit inventory and `P` be the plaintext-letter inventory.
The strict map requires `|C| <= |P|`. Every input unit needs one distinct
plaintext letter. Unused plaintext letters are allowed.

The current corpus inventory has 25 raw EVA symbols and 33 units after the
declared compound scan. The default plaintext inventory has 26 lower-case ASCII
letters. Under this exact strict-injective model and these declared alphabets:

* The raw track is feasible as a 25-to-26 injective map.
* The compound track is infeasible as a 33-to-26 injective map.

Do not remove, merge, or ignore compound units to make the second track fit.
Report it as `infeasible_alphabet_cardinality` before key search. This is an
exact mathematical impossibility for the declared strict map and alphabets;
it says nothing about a non-injective, expanding, or otherwise different
model.

An optional broad-letter track is a different experiment. It can use at least
33 distinct plaintext units only when a historical reference corpus retains
those distinctions and the language manifest justifies them. Record the exact
orthography, alphabet, and source. Do not add a broad alphabet after viewing a
Voynich score.

An input unit absent from the training split has no test-time mapping. Count
unmapped units and affected tokens. Do not add a mapping from validation or test
text.

## 2. Corpus and split manifest

Use the accepted paragraph-body tokens from ZL as the primary Voynich corpus.
Run IT as a separate robustness corpus. Exclude labels, circular and radial
loci, non-Voynich annotations, uncertain or rare tokens, and loci interrupted by
`<->` or `<~>`. Keep one record for every exclusion.

Use the repository's versioned physical-group mapping for recto, verso, and
foldout protection. Store the exact mapping and source hashes with the run.
Never split the two sides of one leaf or panels of one folded sheet.

Create a new `substitution-v1` physical-group manifest. The current structural
test and validation groups have already been used for exploratory analyses.
They are not pristine evidence for this decoder. A new hash split of the same
inspected corpus can separate later tuning from scoring, but it does not by
itself create unseen evidence. Treat that split as an internal exploratory
holdout unless independent validation also supports the result.

For the future confirmatory target, use about 60 percent of groups for
training, 20 percent for validation, and 20 percent for test. Store exact
assignments, not only percentages. The assignment may be public during
deterministic program development. Freeze the candidate languages,
normalization, key rules, search budget, and scoring rules before reading any
test score. If a test score changes those rules, classify the run as
exploratory and create a new evaluation record.

### Upcoming pilot versus future confirmation

The upcoming pilot may use a standard sentence-level historical-corpus split
to debug the search, planted controls, and metrics. Sentences from one work
may occur in different partitions, so this pilot does not establish
whole-work independence and does not support a confirmatory language claim.

The future confirmation target must split reference corpora by complete works
or documents and use a fresh physical-group evaluation, with an independent
implementation or evaluator where possible. The pilot and confirmatory target
must remain separate in run records and claims.

### Historical reference corpora

For each candidate language, create a language manifest before key search. It
must contain:

* language name and historical period;
* source work, edition or release, URL, version, and SHA-256 hash;
* region, genre, and date rationale;
* orthographic normalization and plaintext alphabet;
* document identifiers and the split assignment.

Use a small predeclared language list. Do not search every language and report
the highest score. The historical rationale must come from evidence outside
the proposed Voynich reading.

For the pilot, a standard sentence-level split is allowed as a practical
debugging choice, but it can place sentences from one work in different
partitions. This is a pilot limitation, not whole-work independence. For the
future confirmatory target, split each reference corpus by complete work or
document. Do not split adjacent sentences from one work across partitions.
Use about 70 percent of documents for language-model training, 15 percent for
validation, and 15 percent for test. If a corpus has too few documents, use
leave-one-work-out splits and record the lower power.

Normalize case and punctuation with one fixed rule. Keep word boundaries. Do
not remove rare letters after seeing key-search output. A document is eligible
for a planted control only when its normalized alphabet fits the declared
input-unit cardinality; report excluded documents before fitting.

## 3. Train-only key search

Use one deterministic search configuration per unitization and language. A
candidate key is an injective function `K: C -> P`. The search may use a
branch-and-bound, beam, hill-climbing, or another discrete method, but it must
return the key and the decoded text. It must not return only a similarity score.

Fit a fixed character language model on reference-corpus training documents.
The practical default is a character order-3 model with additive alpha 0.1.
Use validation documents to select a predeclared order or search setting. Do
not fit the language model on Voynich test text or reference test documents.

The search loop is:

1. Build the unit inventory from Voynich training groups only.
2. Build the plaintext inventory and language model from reference training
   documents only.
3. Search injective keys on Voynich training groups.
4. Decode validation groups with the frozen candidate keys.
5. Select the language, search setting, and one key on validation only.
6. Freeze the key, then decode the new Voynich test groups once.

Use a fixed seed and a fixed search budget. A practical starting budget is 32
restarts and 10,000 key proposals per restart for each feasible track and
language. Record every seed, restart, proposal limit, objective, and tie rule.
Changing the budget after seeing a result creates a new exploratory run.

The objective can rank candidate keys with the declared language model, but the
key must obey the substitution constraints. Do not add spelling fixes, unknown
letter guesses, or per-token choices after scoring.

## 4. Known-key planted controls

Use the same search code and budget on known plaintext controls. Generate each
control before the search with a seeded random injective key. Keep the plaintext
split and key hidden from the search.

Use at least 32 planted keys and 128 null controls per feasible language and
unitization in the confirmatory run. A smaller number must be fixed before the
run and reported as a pilot.

### Positive controls

For each eligible reference document, apply a random injective key to every
plaintext letter used by that document. Preserve word boundaries and all token
lengths. Make ciphertext units match the declared unitization. Evaluate the
key-search result on held-out ciphertext whose plaintext remains hidden.

Call a planted control recovered only when all of these conditions hold:

* the returned key matches the planted key on every unit used in held-out text;
* held-out plaintext unit accuracy is exact, apart from any predeclared unused
  plaintext letters;
* held-out token accuracy and word-pattern accuracy are reported;
* no exception or test-only key entry is used.

Compare keys only on used input and plaintext units. Permutations of unused
plaintext letters are equivalent and do not count as key errors.

### Negative and false-positive controls

Run the complete search on controls that preserve superficial structure while
removing the source language:

* shuffle input units within each word while preserving unit counts and lengths;
* shuffle word order within each paragraph or line;
* generate matched low-order unit surrogates from training data;
* apply a random key to a plaintext sequence from a mismatched language or
  document split.

Use the same candidate list, search budget, validation rule, and test scorer for
positive controls, nulls, and Voynich text. Report the null distribution of the
best validation and held-out scores. A false-positive rate is the fraction of
null controls that pass every declared score and lexical-pattern threshold.

The planted-control recovery rate measures method sensitivity. The null
pass-rate calibrates false positives. A method that cannot recover its planted
keys cannot support a negative conclusion about Voynich text.

## 5. Falsifiable lexical checks

An ordinary monoalphabetic substitution preserves these invariants:

* word boundaries and unit lengths;
* the repeated-unit pattern within each word, such as `abca -> 0120`;
* equality of repeated ciphertext word types;
* equality of corresponding prefixes, suffixes, and substrings after the same
  fixed map.

Use these checks on validation and test output. Use a fixed, versioned lexicon
or reference corpus. Do not create a lexicon from decoded Voynich output.

Report these metrics for each feasible unitization and language:

1. key recovery rate on planted controls;
2. held-out plaintext unit and token accuracy on planted controls;
3. Voynich mapped-unit and mapped-token coverage;
4. held-out character cross-entropy against the train-only language model;
5. word-pattern likelihood and fixed-lexicon hit rate;
6. false-positive rate across the null controls.

Compare every result with raw or compound identity output and with the matched
null controls. Compare raw and compound metrics only within their own unit
track. A lower bit rate after changing units is not a direct comparison.

## 6. Decision rules

Use Holm correction across all language, unitization, metric, and null tests in
the confirmatory family. Report all tested candidates, failed controls, scores,
coverage, unknown units, and confidence intervals.

### Planted controls

The search is validated only if the predeclared positive controls meet the
predeclared exact-key and held-out-text thresholds, and null controls remain
below the predeclared false-positive threshold. These thresholds are project
gates, not universal decipherment standards.

### Voynich candidate

A Voynich result is a candidate model only when one fixed key is selected on
training and validation data, covers the declared test text, and improves over
the identity and null controls. A candidate key that only raises language-model
score is not a reading.

Call it a decipherment only after all of these additional gates pass:

* the candidate language has an independent historical justification;
* the fixed key maps unseen text with bounded exceptions and broad coverage;
* a complete translation follows the fixed word boundaries and rules;
* an independent reader reads unseen groups without seeing the proposed output;
* a second implementation reproduces the key, test results, and reading.

If several keys or languages tie on held-out results, report the model as
underdetermined. If keys vary by section or physical group, the tested fixed-key
fit is unsupported; multi-key explanations remain outside this experiment. If
planted controls fail, the procedure lacks demonstrated sensitivity, so do not
infer a Voynich result from its failure. If planted controls pass but Voynich
text fails, the strongest conditional result is evidence against this procedure
and the exact fixed-key, language, unitization, and model settings tested. A
finite heuristic failure does not prove that no key exists or reject untested
search procedures and model variants.

## 7. Run record

Save one machine-readable record with:

* source URLs, retrieval dates, hashes, and parser settings;
* physical-group and substitution-test manifests;
* language corpus manifests and document splits;
* raw and compound unit inventories and cardinality decisions;
* plaintext alphabet and normalization rules;
* search algorithm name, objective, seed, restarts, and proposal budget;
* selected key, validation scores, test scores, and unknown-unit counts;
* planted-control recovery results and null false-positive results;
* every metric, correction, failed check, and interpretation limit.

The test assignment may be public during deterministic program development.
Record or publish it after the key, language list, normalization, search
budget, and scoring rules are frozen. If any test score was used to change
those rules, classify the run as exploratory and use a new confirmatory
evaluation.

## 8. Sources and limits

Use the repository's [corpus method](../research/corpus.md), source manifest,
and [validation protocol](../research/validation-protocol.md) for transcription
provenance and physical-group rules. The IVTFF format documentation is at
<https://www.voynich.nu/software/ivtt/IVTFF_format.pdf>.

The narrow search design can cite model-specific primary work such as Hauer and
Kondrak, “Decoding Anagrammed Texts Written in an Unknown Language and Script,”
TACL 4 (2016), <https://transacl.org/ojs/index.php/tacl/article/view/821>.
That study does not validate this experiment or establish a Voynich key.

The current structural test set has already informed exploratory reports. A
future substitution result that reuses it is exploratory, even if the key was
chosen by a new program. A newly hashed split of that same inspected corpus is
not pristine unseen evidence by itself. A fresh physical-group evaluation and
independent validation are future requirements for a confirmatory claim.
