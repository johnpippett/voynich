# KST coverage and the English Abbreviation Hypothesis

Date: 2026-09-29.
This source check found no complete, independently checked reading method ready for a manuscript test.
It separates transcription coverage from support for assigned meanings.

## Coverage claim

[Kelly Standard Transcription, version 1.0](https://doi.org/10.5281/zenodo.18483132) concerns decisions between existing transcriptions.
Page 2 explicitly excludes semantic correctness from its scope.
Pages 3 and 11 call the reported result translation coverage.
Page 10 describes the same numerator as 5,387 processable lines out of 5,390.

This fraction rounds to 99.9 percent. It does not measure independently checked meanings.
The present check did not reproduce those corpus counts.

Page 12 names separate dictionary and grammar components for interpretation.
Page 16 says dictionary translations are available on request.

## Reading rules and example

The [English Abbreviation Hypothesis, version 1.0](https://doi.org/10.5281/zenodo.18483785) assigns English functions to transcription letters.
Page 7 lists six prefixes and five suffixes, with a prefix-root-suffix procedure.
Its example divides `daiin` as `da + iin`, but the five listed suffixes do not include `iin`.
The example needs additional rules. The separate Grammar V6.4 may supply them.

Pages 10–11 introduce an f1r sample as lines 1–6.
The output table shows lines 1 and 6. Line 1 contains ellipses.
That table does not supply a complete six-line output for reproduction.

These limits prevent a complete automatic reading test. They do not reject English or abbreviation systems.

## Probability claim

Pages 5 and 15 calculate `(1/26)^8 = 1/208,827,064,576`, approximately `4.78865 × 10^-12`.
This arithmetic is correct for eight independent, uniform matches.
Page 5's phrase “one in four trillion” disagrees with that value.

Page 5 acknowledges unresolved choices of word pool, letters, and correspondences, plus possible dependence.
The product does not include a probability model for those choices.
It therefore does not supply a calibrated p-value for a key. These pages cannot determine a corrected probability.

## Access and verification

The paper's GitHub link returned HTTP 404, as did its API and two README requests.
The author's website supplied a working link under a different account name.
The [repository](https://github.com/ignisterra-ai/voynich-kst-verification/tree/165b96d92d86718de1fd5268a84086b12ae68e1c) is fixed at commit `165b96d92d86718de1fd5268a84086b12ae68e1c` for this check.
Its README excludes the proprietary translation engine. The complete tree lists no Grammar V6.4 file.

The papers are version 1.0; the current repository describes KST version 1.3.
This check does not reconstruct the software version used for the papers.

The [coverage code](https://github.com/ignisterra-ai/voynich-kst-verification/blob/165b96d92d86718de1fd5268a84086b12ae68e1c/tools/coverage_calculator.py#L61-L110) measures accepted tokens divided by extracted tokens.
It does not calculate the reported fraction of lines.
Its required input table is absent from the fixed tree.

The supplied dictionary contains 384 serialized entries and 383 distinct keys because `v` occurs twice with the same value.
Its own note identifies the contents as a sample of the claimed 799 entries.
The sample has defined one-character keys for 25 lowercase letters, all except `w`.

The [recursive procedure](https://github.com/ignisterra-ai/voynich-kst-verification/blob/165b96d92d86718de1fd5268a84086b12ae68e1c/tools/coverage_calculator.py#L114-L139) accepts every string of 1–11 characters from those letters.
It can select one character at each step, reaching the last character before its depth limit.
This is a code property. No meaning is necessary for acceptance.

This bound does not calculate manuscript coverage or describe the unavailable translation engine.
It shows why the public coverage statistic cannot check the assigned meanings.

The [source record](english-abbreviation-source-check-2026-09-29.sources.json) gives exact PDF versions, hashes, selected pages, and access results.
Compare the source hashes and examine the cited pages to repeat this check.
The primary agent examined the method and example page images.
Separate AI tasks checked source access and the probability calculation.
The primary agent independently checked the arithmetic, dictionary counts, code paths, and recursion bound.

The required project suite passed all 85 tests. This result does not validate a key or translation.

No manuscript decoding, new sign assignment, or execution of supplied code followed.
A fixed reading test still needs the complete dictionary and grammar.
Any later candidate must also meet the project's [validation protocol](validation-protocol.md).
Raw source files and detailed receipts stay in the ignored result directory.
