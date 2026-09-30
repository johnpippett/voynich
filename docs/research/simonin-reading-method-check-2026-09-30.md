# Simonin interpretation status and source check

Date: 2026-09-30.

Simonin's current clarification does not present the proposed meanings as a validated decipherment.
The examined code gives repeatable interpretation rules, but its structural scores do not independently validate those meanings.
This check supplies no Voynich key or translation.

## Current claim and scope

The author's [addendum](https://zenodo.org/records/17508082), dated 2025-11-02, reports that later statistical controls did not support the proposed content interpretations.
It marks semantic readings, functional decipherment, and alchemical interpretations as unconfirmed.
It keeps the structural and computational claims.
This source check does not reproduce those later tests or independently validate all retained claims.

The code review fixes repository commit `cc9ea7663a5f87b50fe879c650079036c29cc6a3`.
It covers the README, six selected method files, and both addendum pages.
The [source record](simonin-reading-method-check-2026-09-30.sources.json) gives exact files, hashes, source ranges, and review limits.
No supplied program or manuscript corpus ran.

## Fixed interpretation procedure

The [full translator](https://github.com/GSimonin90/voynich-system-decipherment/blob/cc9ea7663a5f87b50fe879c650079036c29cc6a3/scripts/10b_translate_all_improved.py#L47-L173) assigns English terms from its dictionary after prefix and suffix processing.
It assigns subject and object roles from suffixes and assembles those terms into predefined sentence forms or lists.
It supplies a default relation when no connector is present. If several connectors occur, the last one selects the relation.
An unknown root remains as text without an untranslated-word marker.
The inspected source therefore defines an interpretation procedure. It does not independently establish its assigned meanings.

## Structural scores and meanings

The [thematic program](https://github.com/GSimonin90/voynich-system-decipherment/blob/cc9ea7663a5f87b50fe879c650079036c29cc6a3/scripts/02a_thematic_analysis_liftscore.py#L35-L113) selects one dictionary substring from each word.
The program calls this substring a root; that name does not establish a linguistic root.
It compares the root frequency within a section with its frequency across all included sections.

For a reported root, the score is:

`lift = (section_root_count / section_word_count) / (total_root_count / total_word_count)`

An empty section receives zero.
Dictionary values supply only the displayed meaning field.
Replacing those values while keeping the ordered keys, input, and section map unchanged cannot change the numerical scores.
This is a property of the source code, not a measured manuscript result.
It does not prove that every assigned meaning is false.

The [specific benchmark program](https://github.com/GSimonin90/voynich-system-decipherment/blob/cc9ea7663a5f87b50fe879c650079036c29cc6a3/scripts/09_find_specific_benchmarks.py#L89-L117) searches the generated interpretation for predefined English phrases.
It counts a result for each satisfied signature, not each distinct paragraph.
Its heat aliases make calcination types 1 and 3 identical tests. Types 2 and 4 are also identical tests.
The [process scan](https://github.com/GSimonin90/voynich-system-decipherment/blob/cc9ea7663a5f87b50fe879c650079036c29cc6a3/scripts/08a_find_process_signatures_v5.py#L121-L154) also searches assigned English terms within selected sections.
These searches do not independently establish the dictionary assignments.
No empirical benchmark count or process report was reproduced here.

## Decision and verification

The author has already separated the proposed meanings from the retained structural claims.
This candidate supplies no independently supported reading for a new manuscript test in this project.
A future reading needs external evidence for its meanings and a method fixed before evaluation on unseen text.
The project validation rules and earlier stopped studies remain unchanged.

To repeat this source check:

1. Download the exact files in the source record and compare their hashes and byte counts.
2. Read both addendum pages before interpreting the older claim titles.
3. Trace dictionary-value use in the thematic program and signature counting in the benchmark program.
4. Keep source-code conclusions separate from measured corpus results.

Detailed captures, page images, and reader records stay in `results/simonin-reading-method-check-2026-09-30/`.
Separate AI tasks examined the translation procedure and the two metric programs.
The primary agent reviewed their source claims and the addendum images.
All eleven captured source hashes and byte counts agreed with the source record. All 85 project tests passed.
