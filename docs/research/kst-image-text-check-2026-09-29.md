# KST image and text source check

Date: 2026-09-29.
This source check examines whether the proposed image tests independently support a reading of the manuscript.
It supplies no validated key or translation.

## Source and scope

[Paper 3](https://doi.org/10.5281/zenodo.18627510) describes predictions of image features from Kelly Standard Transcription (KST) data.
The English PDF identifies itself as version 2.1, dated 2026-02-23.
The Zenodo record's version field says V1.0. The source record identifies the exact file and its SHA-256 hash.

The check follows the method, public prompts, reported results, limitations, and the f25v example.
It also checks the linked application paper and the fixed public repository.
The earlier [coverage review](english-abbreviation-source-check-2026-09-29.md) remains separate from this image test.

## What the public test measures

Paper 3, pages 6–7 and 13–15, supplies links between prefix classes, functions, colors, and image parts.
For example, class B has the supplied function “Processing,” the color green, and leaves as its Herbal image part.
The prompt counts prefixes and asks an AI system for visual predictions.
The user then examines the image and assigns a coherence category.

This procedure could test an association between written forms and image features.
Such an association would not, by itself, identify the supplied functional meanings.
The numerical prefix ratios do not use those meanings.
Renaming a function leaves those ratios and the fixed class-to-image table unchanged.
This observation concerns the public count and table, not every response that an AI system could generate.

The prompts explicitly include the section and folio number.
An AI system could use those inputs or earlier knowledge of the manuscript when it generates an answer.
This is an uncontrolled route for information, not proof that any reported response used it.
Section-specific predictions therefore need controls with the same section information.

## Reported image results

Pages 9–10 list six example folios, each with High coherence.
Page 9 gives qualitative coherence categories and significance thresholds.
Those thresholds are not a measured image-test p-value.
The table does not give the complete test denominator, random-baseline calculation, or independent image scores.

Page 9 states that predictions preceded image viewing.
Page 11 also states that the work did not use a completely independent blind-test team.
A stated order of work does not replace the missing prediction and observation records.
These limits prevent verification of the claimed independent test; they do not show that the listed observations are false.

## Linked application paper

[Paper 4](https://doi.org/10.5281/zenodo.18627514), also supplied as an English version 2.1 PDF, adds a preliminary ten-page image test.
Its page 9 lists six folios. Page 10 reports `p < 0.001` for the preliminary test.
Those pages do not supply all ten records, the measured image score, or the random-baseline calculation.
Page 10 explicitly says formal statistical data will follow further testing.
Page 8 specifies a ten-point scale, while page 15 supplies qualitative coherence categories without a numerical conversion rule.

Paper 4 also gives a separate calculation for class A never being primary on 227 pages.
Page 9 assumes equal class probabilities and uses `(0.75)^227`.
It prints an approximation of `10^-28`.
Our exact-fraction calculation gives approximately `4.35 × 10^-29`.

The product requires independent page events with an A-primary probability of one quarter.
The source does not establish those assumptions from the data.
The calculation uses no image observations and cannot serve as the missing image-test score.

The class labels alone do not make each class equally likely to have the largest prefix count.
Page 8 also includes Gold when it selects the largest class score, while the probability calculation assigns one quarter to each class.
The relationship between that five-class rule and the four-class chance model needs an explicit definition.
Neither result establishes the proposed functional meanings.

## The f25v example

Page 10 separates public color predictions from shape predictions that require the complete V15 dictionary.
The latter example assigns functions to `shol`, `kor`, and `dar`, then predicts a dragon, snake, or pipe network near the root.
It gives no numerical word counts or source loci for that derivation.
The complete dictionary is available only through a separate collaboration process.

The [Yale f25v image](https://collections.library.yale.edu/iiif/2/1006123/full/full/0/default.jpg) shows a small outlined creature beside the lower plant part.
Large green pointed forms occupy much of the drawing. Brown branching forms extend below them.
The primary agent examined this image after reading the proposed interpretation.
This check confirms the depicted feature. It cannot verify that a fixed reading predicted it independently.

The paper's general Herbal table maps class C to stems and class D to roots.
Its f25v public example nevertheless connects a high C value to prominent roots.
The example does not state a public rule for this change of image part.
The separate private interpretation may use additional rules, but this check cannot reproduce them.

## Public reproduction files

The [repository tree](https://github.com/ignisterra-ai/voynich-kst-verification/tree/165b96d92d86718de1fd5268a84086b12ae68e1c) is fixed at commit `165b96d92d86718de1fd5268a84086b12ae68e1c`.
Its complete listing has no separately named image predictions, observation data, image scorer, or test log.
The examined verification script checks transcription statistics and a probability formula. It has no image inputs or image scores.
The section table contains text counts and coverage claims, without image observations.
The checked files cannot reproduce the reported image test.

## Decision and verification

No new sign value, manuscript decoding, or execution of supplied code followed this check.
The image example supplies no independently checked relation between a written form and a meaning.
The project's [validation protocol](validation-protocol.md) still requires a fixed reading method and independent validation.

A new test needs fixed text inputs, stored predictions, and image scores made without access to the predictions.
It also needs a complete sample denominator and a defined control with the same section information.
An AI test must remove folio identifiers or measure their contribution through a fixed control.
These are requirements for later work, not completed tests.

The [source record](kst-image-text-check-2026-09-29.sources.json) gives source versions, hashes, examined pages, and access limits.
The primary agent checked the source tables, prompt, repository files, and Yale image.
Separate AI tasks examined the protocol and public reproduction files. These tasks are not external scholarly validation.

The required project suite passed all 85 tests. This result does not validate the proposed reading.
Raw sources and detailed receipts remain in the ignored result directory.
