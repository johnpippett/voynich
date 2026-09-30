# Fixed blue-word transfer check

Date: 2026-09-29.
Goal: Check exact `key` counts outside the plant-feature discovery groups.
Architecture: Read fixed source files, remove discovery groups, and count one token by the released color tags.
Tools: Python standard library and the existing project group map.
Review focus: Source hashes, group exclusions, exact token counts, missing text, and limits on interpretation.

## Evidence available before this plan

The source report proposes EVA `key` for blue. Its two analyses use overlapping folios and the same transcription.
The saved plant-feature output reports three occurrences on blue-flower folios, none in its comparison set, and fifteen overall.
The saved color output omits this candidate from its limited export.
No counts outside the discovery groups were calculated before this plan.
This check is exploratory. The source author could have examined all these pages.

## Fixed inputs

Use `geoffitect/voynich` commit `860d278a6fa72a39605a11513716e56298411d47`.
The companion source manifest fixes three files and their SHA-256 hashes:

- `scripts/04_content/plant_features.py`: the literal `PLANT_FEATURES` map.
- `scripts/04_content/color_crossref.py`: the literal `COLOR_TAGS` map.
- `data/transcription/voynich_nlp.json`: the released words and folio metadata.

Read the two maps with `ast.literal_eval`. Do not execute source code.
Reject an absent, repeated, or nonliteral map assignment.
Check each source hash before parsing.
Use `src/voynich/groups.py`, SHA-256 `15b77e967ce296634a36a3deacba660c14a4d4615c99597949b5586d682bdef0`.
Use `data/bifolio_manifest.json`, SHA-256 `998cb3d6c8327ff0bdf786d52968fa3bec9f5fa9b05ba7ae56065fc9639fad72`.
Check both project hashes before loading the group code.
This map uses provider quire and bifolio metadata. It is not a separate conservation assessment.

## Fixed operation

1. Take every folio in `PLANT_FEATURES` as discovery material, for all features.
2. Form the union of their project group identifiers with `group_id`.
3. Visit every folio in `COLOR_TAGS` in sorted order.
4. Exclude any folio whose group occurs in that discovery union.
5. Exclude missing metadata, then nonherbal metadata, then missing or empty text, in that order.
6. Keep a folio only when its metadata has `illustration == "H"` and its text contains words.
7. Join its sentence word lists without other token changes.
8. Count only exact string equality with `key`.
9. Place each kept folio in `blue_tag` if its color map has a `B` key.
10. Place other kept folios in `no_blue_tag`.

Record every discovery folio and group, kept folio, and exclusion reason.
For each kept folio, record its group, token count, `key` count, and tag category.
For each category, record folio count, distinct group count, token count, `key` count, and folios with `key`.
Count distinct groups within each category. A group can contain pages in both categories.
Record the plan, script, manifest, source, and group hashes in the result.
Do not record machine paths, raw page text, or personal metadata in public results.

The interface is `MANIFEST SOURCE_ROOT NEW_OUTPUT`.
The manifest has a `sources` map with roles `plant_features`, `color_tags`, and `corpus`.
Each role has `path`, `sha256`, and `url` fields. Paths are relative to `SOURCE_ROOT`.
Reject an existing output. Produce deterministic JSON without a timestamp or local path.

## Failure modes and checks before implementation

The first E2E test must fail before implementation. Use artificial inputs and the real command interface.
Keep a test artifact that another operator can run with setup, commands, results, and the earlier failure.

- Wrong groups: exclude both `f1v` and `f8r` when discovery contains `f1r`.
- Substring counting: do not count `monkey` or `keyed` as `key`.
- Missing text: exclude it; do not treat it as a zero-count folio.
- Nonherbal text: exclude `f51r` with illustration `A`, even if it contains `key`.
- Foreign execution: place an unconditional exception after a literal map; the count must still succeed.
- Altered source: reject a hash mismatch without output.
- Dynamic map: reject a function call in place of a literal map without output.
- Existing output: reject the run and keep its bytes unchanged.
- Nondeterminism: two executions must give equal result bytes.

The fixture uses discovery `f1r` and six color-tag folios.
The excluded discovery group contains `f1v` with four `key` tokens and `f8r` with three.
The blue-tag folio `f49r` has `["key", "monkey", "key"]`.
The other kept folio `f50r` has `["monkey", "keyed"]`.
Nonherbal `f51r` has `["key"]`. Herbal `f52r` has no text.
Expected blue totals: one folio, one group, three tokens, two `key` tokens, and one positive folio.
Expected other totals: one folio, one group, two tokens, zero `key` tokens, and zero positive folios.
After implementation, use a second calculation to check the source count and exclusions. Run the required project suite.

## Decision and limits

Report all results without a fitted cutoff, candidate ranking, p-value, or change to the candidate word.
The tags are the author's annotations. Absence of `B` is not verified absence of blue paint.
No new image identification, source-language assignment, sign value, or translation follows from this count.
A repeated association would justify a later image audit. It would not establish the word's meaning.
No occurrence supplies no support from this subset. It does not disprove the proposed meaning.
Do not replace pages, change token boundaries, or expand this check after its result.
