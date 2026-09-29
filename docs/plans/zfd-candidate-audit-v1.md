# Fixed ZFD source and output audit

Date: 2026-09-29. This is an exploratory candidate-key check.
Objective: determine whether one published decoder provides a reproducible reading candidate.
The broader project goal remains a verified manuscript key or translation.

## Fixed source

Use denoflore/ZFD commit 3f030a9293b8db15dc2c7b0d0e7c703e71711f62.
Check the saved hashes before loading the source.
Use only 06_Pipelines/zfd_decoder_v2.py and its unified_lexicon_v3.json.
The primary agent read the entire decoder before this plan.
Do not change its character table, lexical keys, boundary rules, or functions.
Do not run its main program. Import the reviewed module without bytecode writes.
The guide and character table are comparison sources, not interchangeable specifications.

## Fixed checks

1. Run the four numbered examples from GETTING_STARTED.md through eva_to_croatian.
   Inputs: qokeedy, chedy, shol, daiin.
   Guide outputs: kostedi, hedi, šol, dain.
   Report exact equality for each output. Do not repair vowels or final y.
2. Decode the same four tokens with the unchanged lexicon. Keep decomposition, residue, confidence, and classification.
   Report recognized character fractions as code scores, not correctness probabilities.
3. Make one synthetic copy of the lexicon. Replace only semantic string values with unique opaque labels.
   Semantic fields are meaning_en, meaning_hr, latin, latin_full, and grammatical_function.
   Preserve every dictionary key, form, order, and other value.
   Decode the same four tokens. Compare matched forms, residues, confidence, and resolution counters.
   Compare generated glosses separately. This counterfactual tests whether confidence validates meaning.
   Do not describe the synthetic labels as alternative translations.
4. Check the guide's claimed f88r sequence: qokeedy dal chol ar shedy.
   Search exact consecutive tokens within each unambiguous paragraph line on f88r in both pinned source files.
   Use the existing parser in split mode. Require zero excluded tokens and reject text with uncertain separators or unreadable markers.
   Also report an exact raw-source substring check for the dot-separated sequence within f88r records.
   Report eligible line and token counts and exclusions. Keep the search on f88r only.
   No alternate folio, reordered sequence, normalized spelling, or replacement example is permitted.

## Failure modes and limits

Wrong source bytes, missing lexicon, import errors, or malformed source inputs stop the audit.
A guide-code mismatch identifies inconsistent published instructions. It does not reject every version or Croatian.
An absent sequence can reflect guide provenance or transcription differences. It is not evidence about all manuscript content.
Equal confidence after semantic replacement demonstrates that the score cannot validate those meaning labels.
It does not prove that any particular label is false.
There is no key fitting, new manuscript translation, or language-model scoring.
The four guide examples were known before the test. This is not blind linguistic validation.

## Evidence

Before implementation, specify source-free E2E expectations for the audit command and its output schema.
Verify source hashes and input expectations before interpreting the output.
Use a new output path. Record setup, commands, plan and script hashes, source hashes, results, and all failure reasons.
Keep full manuscript text and downloaded source files in ignored local evidence.
Public output may contain the four short source examples, aggregate counts, hashes, and source references.
Stop this check after the fixed result. Any later candidate requires a separate question and plan.
