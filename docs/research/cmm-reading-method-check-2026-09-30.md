# CMM reading-method source check

Date: 2026-09-30.

The Comprehensive Method and Mapping (CMM) proposal supplies explicit mappings and an English rendering procedure.
Its examined validation code does not establish the assigned meanings.
This check found no validated Voynich key or translation.

## Scope

The check fixes repository commit `c7c3b66fe6c4e5ea8c172df4c607befeae823740`.
It covers the README, translation guide, core pipeline, and input builder.
EVA means Extensible Voynich Alphabet, a transcription system.
It does not execute the supplied program, examine its full input corpus, or reproduce its reported manuscript results.
The [source record](cmm-reading-method-check-2026-09-30.sources.json) gives URLs, hashes, and the calculation limits.

## The lexicon measure

The [mapping functions](https://github.com/keninayoung/Voynich_Pipeline/blob/c7c3b66fe6c4e5ea8c172df4c607befeae823740/voynich_pipeline.py#L98-L146) can give 20 different Latin terms.
Those terms are exactly the 20 entries in the [built-in `MED_LEX` set](https://github.com/keninayoung/Voynich_Pipeline/blob/c7c3b66fe6c4e5ea8c172df4c607befeae823740/voynich_pipeline.py#L322-L324).
The decoder also adds one `fac` or `usa` to each kept clause. Neither term belongs to that set.
Unknown characters give no term.

Let `N` be the number of terms in the final Latin output, and `C` the number of kept clauses.
For nonempty output, the [metric](https://github.com/keninayoung/Voynich_Pipeline/blob/c7c3b66fe6c4e5ea8c172df4c607befeae823740/voynich_pipeline.py#L350-L369) is therefore:

`lexicon_alignment = round((N - C) / N, 4)`

For empty output, the score is zero.
This equation also covers the decoder's fallback clause.
The primary agent and another AI task independently found this result in the source.

The [README](https://github.com/keninayoung/Voynich_Pipeline/blob/c7c3b66fe6c4e5ea8c172df4c607befeae823740/README.md#L14) describes alignment with Trotula and Hildegard corpora.
The examined metric loads neither corpus. It measures membership in the pipeline's own output vocabulary.
Thus, a high score cannot independently show that the pairs between Voynich forms and Latin meanings are correct.
This finding does not show that every assigned meaning is false.

## An English input that passes the filter

The [translation guide](https://github.com/keninayoung/Voynich_Pipeline/blob/c7c3b66fe6c4e5ea8c172df4c607befeae823740/translation_guide.md#L8) includes this English description in a field called Original EVA:

> a straight short thick descending stroke with a

Seven of its eight words contain only characters from the filter's EVA set.
The substring `shor` in `short` meets the seed condition. No word in this fragment meets the exclusion condition.
Both the [pipeline filter](https://github.com/keninayoung/Voynich_Pipeline/blob/c7c3b66fe6c4e5ea8c172df4c607befeae823740/voynich_pipeline.py#L24-L81) and [input-builder filter](https://github.com/keninayoung/Voynich_Pipeline/blob/c7c3b66fe6c4e5ea8c172df4c607befeae823740/build_full_voynich_csv_strict.py#L19-L73) therefore accept this fragment.
The character fraction is `7/8`, above their `0.80` threshold.

An independently written calculation used constants from the retained source files, without importing or executing those files.
All four cases matched expectations fixed before the calculation.
Adding the excluded word `folio` caused rejection. The positive and negative artificial controls gave the expected results.
A replay in an empty directory gave identical result bytes.
Another AI reader found the same result directly from the source.

The first calculation stopped at a source-encoding error in an unrelated comment.
The revised calculation parsed only the required ASCII constant declarations. It kept the source files and expected results unchanged.
Both calculation versions and the failure record remain available.

This result concerns the exact fragment. It does not measure contamination in the current full input corpus.
The guide examples can come from another pipeline version; this check does not assume version agreement.

## Other validation limits

The [sensitivity function](https://github.com/keninayoung/Voynich_Pipeline/blob/c7c3b66fe6c4e5ea8c172df4c607befeae823740/voynich_pipeline.py#L373-L410) compares different processing paths.
Its reference path uses clause segmentation, term removal, verb insertion, and clause selection.
Its perturbed path tokenizes the input directly and omits those steps.
It permutes selected unit-map values but keeps character mappings unchanged.

The function reports one decrease in unigram entropy. It does not fix its random seed.
It changes negative decreases to zero.
It does not measure the Z-score decrease named in the README.
The source difference does not by itself measure the size of any reported error.

The [English renderer](https://github.com/keninayoung/Voynich_Pipeline/blob/c7c3b66fe6c4e5ea8c172df4c607befeae823740/voynich_pipeline.py#L243-L291) uses predefined conditions and action phrases.
Readable English from that renderer is not evidence independent of those choices.

## Decision and verification

The check stops before a manuscript decoding run.
A later reading test needs source-audited input and independent evidence for the assigned meanings.
A sensitivity test must apply the same processing to its reference and perturbed inputs.
No new sign value, word repair, or corpus fit followed this check.

All nine captured source-file hashes and byte counts matched. All 85 project tests passed.
The public source record gives the fixed inputs, source ranges, expected filter results, and calculation hashes.
Detailed sources and records stay in `results/new-key-contracts-2026-09-30/`.
These software and source checks do not validate a translation.
