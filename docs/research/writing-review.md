# ASD-STE100 writing review

Review date: 2026-09-16.

This review applies selected ASD-STE100 Issue 9 rules to the listed research
documents and generated public prose. It does not certify full ASD-STE100
compliance.

## Reference and rules

The review used [ASD-STE100 Issue 9](https://www.asd-ste100.org/assets/files/ASD-STE100_ISSUE9.pdf), dated 2025-01-15.

The review used these rules:

* Section 1, Rules 1.1-1.3, 1.6, 1.11, and 1.14: approved words, technical terms, consistent terms, and American English spelling.
* Section 3, Rules 3.2-3.6: permitted verb forms, active voice, and limits on complex verb forms and `-ing` forms.
* Section 4, Rules 4.1-4.5: short sentences, complete sentences, vertical lists, connecting words, and articles.
* Section 5, Rules 5.1-5.5: instructions, one action per sentence, sequence, conditions, and notes.
* Section 6, Rules 6.1-6.6: gradual information and one topic per sentence and paragraph.
  It also sets a maximum of 25 words per descriptive sentence and six sentences per paragraph.
* Section 8, Rules 8.1 and 8.4-8.7: punctuation, vertical-list word counts, identifiers, and hyphenated words.
* Section 9, Rules 9.1-9.4: alternate sentence construction, correct approved-word use, and consistent terminology.

The review also used the dictionary introduction and the list of recurring
errors. It checked entries for `any`, `both`, `establish`, `fit`, `may`, `need`,
`over`, and `repeat`.
The statistical term `fit` remains where it identifies a subject-field model
operation. Code, identifiers, URLs, and JSON keys remain literal.

## Material corrections

* [README.md](../../README.md) now uses active wording. It states that the
  project does not show a decipherment. It states that statistical structure
  does not show a language or translation. It documents basic-EVA strict
  parsing, the `split` and `join` spacing policies, the canonical `folio_group`
  split, and the physical-sheet limit.
* [AGENTS.md](../../AGENTS.md) uses direct instructions and generic project
  wording.
* [Research design](../plans/design.md) adds the `<->` and `<~>` diagram
  interruption filter. It records the conservative folio groups, the `fRos`
  alias, the mapping version, and the different raw-EVA and grouped null units.
* [Implementation plan](../plans/implementation.md) records the canonical
  group mapping and uses direct verification steps.
* [Validation protocol](validation-protocol.md) states the current parser
  limit. It separates exploratory results from future confirmation. It
  describes the two null-unit rules and labels future solution gates as
  proposed. It scopes the numerical starting points as project proposals.
* [Hypothesis registry](hypotheses.json) records the current parser limit,
  canonical group unions, null-unit rules, and `proposed_solution_gates`.
* [Findings report](../../reports/FINDINGS.md) and
  [`build_summary.py`](../../scripts/build_summary.py) use direct wording,
  identify both diagram interruption markers, and state conclusions that match
  the result tables.
* [Status report](../../STATUS.md) uses direct wording for the unresolved
  objective and the requirements for the next stage.

No result values or result links were added during this review.
