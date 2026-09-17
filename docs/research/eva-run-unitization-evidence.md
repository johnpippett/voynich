# EVA run unitization evidence

**Research date:** 2026-09-17
**Status:** exploratory methods note

This note adds evidence about repeated EVA `e` and `i` to [Glyph units and linguistic units](glyph-unit-evidence.md). It does not fit rules to project counts.

## Finding

EVA codes written shapes. It does not establish linguistic letters. The reviewed evidence does not support a universal `ee` or `ii` glyph unit.

Repeated `i` forms have stronger historical transcription support than repeated `e` forms. Currier and FSG used compact analysis symbols for `in`, `iin`, `iiin`, and related final series. This supports one named historical mapping, not every `ii` merge.

The six groups `ch`, `sh`, `cth`, `ckh`, `cph`, and `cfh` remain the strongest visual compound candidates. The EVA font specification marks them as connected. It does not give the same universal rule for lower-case `ee` or `ii`.

## Focused source evidence

* René Zandbergen, [“Analysis of the text”](https://www.voynich.nu/extra/sp_analysis.html), copyright 2021, latest update 13 June 2021, sections **Strings of i's** and **Definition of the Cuva analysis alphabet**, Tables 4–6. The page compares Currier, EVA, and v101 treatments of repeated runs. Currier and EVA keep `ee`, `eee`, and similar `e` strings as sequences, while Currier gives compact labels to several `i`-final series. Cuva maps `ee`, `eee`, and `eeee`, but the page states that Cuva is for text analysis. It also leaves open whether repeated minims are characters or parts of characters.

* René Zandbergen, [“Transliteration of the Text”](https://www.voynich.nu/transcr.html), latest update 31 May 2025, sections **Landini–Zandbergen: Eva** and **v101**. EVA is a reversible shape transliteration. The page says that older alphabets treated `in` and `iin` as units, while EVA writes the visible sequences. It says analysts must decide how to group such forms. EVA capitals and braces can record connectivity, but they do not assign sound or meaning.

* Gabriel Landini, [*EVA Alphabet Font Version 2 Reference*](https://www.voynich.nu/hist/gabriel/eva2_reference.pdf), document updated July 2004, PDF p. 4. The connectivity table marks the six visual groups as connected. It gives `Ee` as an example of a connected `ee` occurrence. That example records a marked connection; it does not justify merging every lower-case `ee`.

* Prescott H. Currier, [*Papers on the Voynich Manuscript*](https://www.voynich.nu/extra/curr_main.html), seminar manuscript dated 30 November 1976, sections **The Nature of the Symbols** and **The Nature of the Symbols cth, ckh, cph, cfh**. Currier describes `a` as potentially formed from `e` and `i`, and treats the gallows groups as separate statistical symbols. He also says that the apparent construction from `e` and `i` does not by itself mean anything. This is a visual and statistical hypothesis, not an agreed unit rule.

* Lisa Fagin Davis, [“Voynich Paleography”](https://ceur-ws.org/Vol-3313/keynote2.pdf), CEUR Vol-3313, Malta conference 30 November–1 December 2022, PDF pp. 2–3, §2 **Background and Methodology**. Her image-annotation study found no easily identifiable hand differences in the common `[e]` and `[i]` forms. She calls the method subjective. Common-form stability is therefore not evidence of atomicity.

* Luke Lindemann and Claire Bowern, [*Character Entropy in Modern and Historical Texts*](https://arxiv.org/abs/2010.14697v2), version 2 dated 18 May 2021, §3.1.1 and Figure 4, PDF pp. 8–11. Their paper-specific **Minimal** and **Maximal** transcriptions set analytical bounds. They state that handwriting and script analysis must assess particular decompositions. Do not combine their Figure 4 mapping with another conversion table under one undefined track.

## Current protocol limit

The [fixed protocol](../plans/vms-local-cyclic-falsification-v1.md) declares lower-case `raw_eva` and the six-group `visual_six` track. The [extractor](../../experiments/local_cyclic/certificate.py) does not lower-case or strip connectivity. It accepts canonical lower-case `a-z` candidates, preserves accepted spelling, and rejects candidates containing capitals or braces. If an upstream source has already omitted connectivity metadata, the extractor cannot reconstruct it. The historical conversion of Takahashi's capitalized EVA to lower case is a distinct source stage.

The existing [f84r audit](f84r-local-repeat-image-audit.md) found its two fixed spans image-uncertain. Neither verifies two atomic repeated glyphs.

## Bounded future comparison

Treat the following as a proposal after the inspected results, not as a blind preregistration:

1. Keep `raw_eva` and `visual_six` as baselines.
2. Add one named **Lindemann–Bowern Minimal v2 Figure 4** track. Audit its exact two additions and mapping before implementation. Do not append Zandbergen or Cuva rules.
3. If source files retain case or braces, add `eva_connectivity_preserved`. A different source can change eligible words. Compare only an explicit paired intersection, and report excluded coverage for every track.
4. Keep universal `ee` and `ii` merges as separate unsupported sensitivity controls. Do not present them as discovered signs.

Use a fixed folio and line list for image review. Mark each candidate span `separate`, `connected`, or `uncertain`, and retain the raw span and image coordinates. Do not select regions from repeat counts. Use Yale's [MS 408 collection](https://collections.library.yale.edu/catalog/2002046). Run synthetic segmentation controls before manuscript analysis.

A result supports a visual boundary only when source metadata or held-out image review supports that boundary rule. A score under an unsupported repeat merge remains a sensitivity result. It is not evidence of a sign inventory, language, or decipherment.

## Open questions

Which source records preserve case or braces for the exact spans? Do independent reviewers agree on repeated `e` and `i` boundaries? Does the paper-specific Minimal mapping change results without new rule selection? These are transcription questions, not decipherment evidence.
