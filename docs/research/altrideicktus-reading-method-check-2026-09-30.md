# Altrideicktus reading-method source check

Date: 2026-09-30.

The examined Altrideicktus tutorial does not supply a complete, repeatable reading procedure.
This check found no validated Voynich key or translation.
It stops before a manuscript decoding run.

## Scope

The check covers three author pages, all five written-tutorial pages, and material slides 4–8.
The [source record](altrideicktus-reading-method-check-2026-09-30.sources.json) gives exact URLs, hashes, page selections, and access limits.
The primary agent examined all ten selected page images.
Another AI task separately examined the five tutorial pages.
Both readers saw the proposed answers; this was not a blind reading test.

## Rule limits

The [tutorial](https://www.voynichcode.org/wp-content/uploads/2024/08/Voynich_codebreaking_tutorial.pdf) gives several values for some signs on pages 1–2.
Word position limits the nine-like sign to prefix or suffix values, but it does not select one value within each group.
Page 3 marks supplied and extra letters in its proposed solution without a general rule or limit for those changes.

The partial key on page 2 assigns `cis` to its last abbreviation sign.
The printed sign with the same shape on page 3 receives `cur` or `cinoris` in the worked example.
Both readers found this difference in the page images.
The tutorial gives no rule for that change.
This finding concerns that printed pair; it does not establish an error in every abbreviation assignment.

The [material slides](https://www.voynichcode.org/wp-content/uploads/2024/08/voynichcode_video_tutorial.pdf) give nine alternative readings for one printed group on page 7.
Page 6 names context propagation, but the selected pages do not define a procedure that selects the alternatives.
The author's [writing-system page](https://www.voynichcode.org/the-writing-system-of-the-voynich-text/) also describes this context-dependent method without a complete selection procedure.

The extracted PDF characters represent custom-font encodings.
They are not verified EVA symbols. EVA means Extensible Voynich Alphabet, a transcription system.
This check uses the page images for sign comparisons and assigns no new sign values.

## Evidence limits

The tutorial relates proposed meanings to nearby illustrations.
Its examined examples do not report a blind continuous-text test or verification by readers outside the project.
An illustration used to select a meaning cannot independently validate that selection.
These findings concern the examined sources, not the author's book or unread material.

The tutorial cites Cappelli's 1982 abbreviation handbook.
The university's old PDF address returned an HTML page. Other download routes returned HTTP 403.
This check therefore makes no finding about the handbook's detailed rules.
A historical Latin abbreviation convention would still need evidence for its proposed correspondence with a Voynich sign.

## Decision and verification

A later reading test needs fixed rules for alternative values, abbreviation expansions, and supplied or removed letters.
It also needs meanings checked independently of the illustrations that helped select them.
No new manuscript transcription, word repair, corpus fit, or decoder execution followed this source check.
This decision does not reject Latin or every possible abbreviation method.

To repeat the source check:

1. Download the five sources from the source record.
2. Compare their SHA-256 hashes and byte counts with that record.
3. Render the listed PDF pages at 145 dots per inch with `pdftoppm`.
4. Compare tutorial pages 2–3 and examine the stated rule limits on all selected pages.
5. Keep font encodings separate from verified manuscript transcriptions.

Detailed source captures, images, reader records, and access failures stay in `results/altrideicktus-key-check-2026-09-30/`.
All five source-file hashes and byte counts agreed with the source record. All 85 project tests passed.
The project validation rules and earlier stopped studies remain unchanged.
