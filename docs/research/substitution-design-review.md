# Fixed monoalphabetic substitution search: design review

Historical document: this file records work before the Stage 2 grouping correction.
See [Stage 2 methods](stage2-methods.md) for the current implementation and [results](../../reports/STAGE2.md) for measurements.

Review date: 2026-09-16.

The current predictive code measures EVA sequence structure. It does not decode a
language. It defines two different source unitizations:

* `raw_eva`: one Unicode code point per unit;
* `grouped`: the declared longest-match units `cth`, `ckh`, `cph`, `cfh`,
  `ch`, `sh`, `iin`, and `in`, with other characters kept as single units.

A substitution search can produce useful evidence only when it tests a frozen
model class on held-out groups and recovers planted controls with the same
search budget. A readable training output alone is weak evidence. A character
language model can make arbitrary symbol strings look like partial language.

## Recommended first model

Register one ordinary substitution family before the search:

* map each declared source unit to one target alphabet symbol;
* use one global map for all groups and all token positions;
* keep source token boundaries unchanged;
* use one fixed target-language normalization and one fixed target-language
  language model;
* allow no word-specific rules, folio-specific maps, spelling repairs, or
  unlisted symbols.

Run `raw_eva` and `grouped` as separate hypotheses. A grouped unit is one
source symbol for that hypothesis. It is not evidence that the compound form is
a glyph or a linguistic letter.

Use the current source token boundaries for the first run. The parser's
`uncertain_spaces='split'` and `uncertain_spaces='join'` settings are separate
input hypotheses. Do not choose one from test output. A model that removes
spaces or creates new spaces is a different model class and needs its own
predeclared search, complexity limit, planted controls, and correction.

The map domain must come from the declared unitization and the training groups.
Map a test-only source unit to one fixed unknown symbol and report its coverage.
Do not add a test-only unit to the key after seeing its output. Do not map an
unknown symbol to a convenient target letter.

Require equal source and target alphabet cardinality for an ordinary bijection,
or use a partial injective map with an explicit unused-symbol rule. A source
alphabet larger than the target alphabet is not an ordinary substitution. Test
many-to-one or limited-homophone maps as a separate registered family. Give
each such family a fixed homophone limit and an exception ledger.

## Frozen data and transcription choices

Use one frozen manifest for a run. The current `folio_group` hash and the
`conservative-foldout-groups-v2` mapping are suitable for an exploratory run.
A confirmatory run needs a physical folded-leaf manifest that includes every
panel. Keep the 85/86 union and all other candidate unions in the manifest with
their evidence status.

Keep ZL and IT as separate input runs. Do not pool their tokens to fit one map.
Run the same registered procedure for both transcriptions and compare map
support, coverage, held-out scores, and aligned output. Use the same rule for
the future `strict`, `first`, `second`, and `mask` uncertainty modes. Fit a map
on each declared input mode by the frozen procedure, or apply one frozen map to
the other mode if that transfer test was registered. Do not retune exceptions
after reading a result.

Keep paragraph body text and labels as separate strata. A primary body-text map
must not use labels from the same group as training features. Report a label
run only when its input filter, map, and score denominator are predeclared.

## Search contract

Use a target language model fit only on an independent historical reference
corpus. Do not fit or adapt that model on decoded Voynich text. Fit its
parameters on reference-train data, select fixed hyperparameters on reference
development data, and keep reference-test data hidden until the final scoring
step.

Split the reference corpus by document, edition, or author. Do not split one
document into random lines. Remove duplicate editions and near-duplicate
passages before the split. Record the source, date, region, script, edition,
normalization rules, license, and SHA-256 hash. A modern corpus is not a
historic-language control unless the project records why it is suitable.

If no versioned reference corpus has independent historical support for a
candidate language, omit the target-language predictive metric. An intrinsic
EVA n-gram score cannot identify a language.

Use a fixed deterministic search procedure. A practical starting budget is a
predeclared number of random permutations and a fixed number of pair-swap
proposals per permutation. For example, use 32 restarts and 25,000 proposals
per restart for a 26-symbol key. Increase this budget only after the planted
controls are defined, and freeze the new budget before running manuscript test
groups.

For each restart:

1. Create a deterministic random bijection from the registered seed.
2. Propose only map-preserving swaps, with a fixed proposal schedule.
3. Score the decoded training groups with the frozen target model.
4. Keep the best key at the end of the fixed schedule.

Select one key among restarts by development score. Use a fixed tie break,
such as development score, then training score, then canonical key bytes. Do
not select by test score, a screenshot, a few readable words, or manual edits.
Use the same restart count, proposal count, seed list, stopping rule, and score
weights for the manuscript and every control.

Serialize the frozen key with sorted source units, target alphabet, source
unitization, space policy, transcription mode, target-corpus hash, model
parameters, seeds, restart count, proposal count, and objective weights. Hash
the serialized key. The test decoder must load this file and must not change
the map, unknown handling, or exception ledger.

## Scoring rule

Use one fixed objective for search. A suitable form is:

```text
objective = - target-LM bits on decoded text
            - fixed penalty for unmapped source units
            - fixed penalty for registered exceptions
```

Report every component and its denominator. Keep the target LM, penalties, and
word-boundary treatment fixed across languages, unitizations, and controls.

The primary held-out result should include:

* bits per decoded character and bits per decoded word;
* target-LM vocabulary unknown rate;
* source-character and source-token coverage;
* decoded token count and character count;
* exception count by source locus and exception type;
* the train, development, and test scores using the one frozen key;
* score change from the raw-EVA identity baseline and each registered null;
* the full restart score distribution and the selected key hash.

The current predictive model's EVA bits per symbol measure written sequence
structure. They are not a target-language score and must not be presented as
evidence for a decoded language.

Preserved spaces give a strong diagnostic. A fixed substitution preserves token
lengths and repeated-token patterns. Report these values before and after
decoding. If a boundary-changing model is added, score it with a separate
fixed segmentation model and report the number of boundary operations. An
open-ended segmentation table can manufacture words from arbitrary strings.

Use a character LM and a word or subword LM with fixed vocabularies. A character
LM alone can reward fragments such as common letter pairs. A word LM alone can
reward a small number of common words while the remaining output is unknown.
Report both scores and the unknown rate. Do not add a dictionary after viewing
the output.

## Planted known-cipher controls

Run the complete search before using it on manuscript test groups. Keep the
true planted keys out of the search inputs and initialization.

### Clean planted controls

For each registered target language and unitization:

1. Select independent reference documents after the reference-corpus split.
2. Apply the fixed target normalization and space policy.
3. Apply a random known bijection from target symbols to the declared source
   units.
4. Store the resulting ciphertext as records with the same group and token
   boundary fields used by the decoder.
5. Fit and select the key from control-train groups only.
6. Freeze it using control-development groups, then evaluate once on
   control-test groups.

Use several fixed random planted keys. Evaluate exact key recovery on symbols
observed in training, per-symbol assignment accuracy, decoded test-character
accuracy, exact token accuracy, target-LM score, and exception count. A source
symbol absent from training has no identifiable key assignment; report that
support separately.

The search must recover a clean planted control with the declared budget. If it
fails a control but returns a plausible Voynich output, the output is a search
artifact until the method is changed and retested on fresh controls.

An optional shape-matched control may preserve the observed token-length and
group-size distributions. Define its sampling procedure before use. Record
which target words were rejected because no fixed-length match existed. Do not
call a shape-matched control a natural historical text if the sampling removes
its document order or grammar.

## Negative controls

Apply the same unitization, split, target model, search budget, and selection
rule to each control.

| Control | Transformation | Expected use |
| --- | --- | --- |
| Random-key baseline | Score a fixed set of random bijections with the same key support. | Calibrate the maximum score expected from key choice. |
| N1 word-order shuffle | Shuffle words within each eligible line for every split, preserving line word counts and token lengths. | Test whether a result depends on word order. |
| N2 unit-order shuffle | Shuffle raw code points for `raw_eva`, or declared grouped units for `grouped`, within every token. | Test whether the relevant unit order carries the score. |
| N6 generative surrogate | Generate records from frozen lengths, frequencies, and low-order transitions without a target lexicon. | Test whether local structure can produce the same score. |
| Wrong-language control | Use a predeclared historical reference language with no expected source match. | Measure false-positive rates across language candidates. |
| Cipher mismatch control | Encode reference text with a predeclared non-monoalphabetic rule, such as a position-dependent map. | Test whether the search incorrectly claims recovery outside its model class. |

The manuscript result must be compared with the maximum null score and its
restart distribution. A higher score than one null does not reject the other
nulls. Use the validation protocol's plus-one permutation estimate and Holm
correction for the declared comparison family when a permutation test is used.

Do not use a control only after a favorable manuscript output. Add all controls
to the frozen configuration before viewing manuscript test output.

## Evidence thresholds

A substitution search gives useful evidence for this model family only when all
of these conditions hold:

* the same procedure recovers clean planted controls;
* one frozen map gives held-out improvement on unseen physical groups;
* the improvement exceeds the matched negative-control maxima under the same
  search budget;
* coverage is high and the exception ledger is bounded;
* the result remains present across the registered unitization, transcription,
  and uncertainty analyses;
* the target language was selected from predeclared historical evidence;
* a blind reader can produce a continuous held-out reading under the project
  solution gates.

These conditions support a fixed model family. They do not alone establish a
translation. Failure of a planted control rejects the current search design;
failure on the manuscript does not show that the text has no meaning.

## Stop conditions before test use

Stop and redesign the run when any of these events occurs:

* a language, unitization, space rule, or exception is added after test output;
* the key uses source units or target words obtained from test groups;
* the target reference corpus contains a duplicate or near-duplicate of the
  scored text;
* the search uses a growing dictionary, word list, or spelling table;
* an optimized output is judged by visual readability without held-out scores;
* the search fails a clean planted control;
* the physical group manifest is incomplete for the intended claim.

Label any run that violates a stop condition exploratory. Create a new frozen
test set before making a confirmatory claim.
