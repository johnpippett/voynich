# Romance matrix source check

Date: 2026-09-29.
This study checks a published conversion program at one fixed source version.
It supplies no validated Voynich key or translation.

## Finding

The program gives dictionary meanings to every nonempty phonetic token with at most three characters.
Thus, translation coverage on those tokens cannot support the proposed sound values or meanings.
An artificial input with three identical glyphs receives a botanical meaning without an exact dictionary match.
Changing dictionary order changes that meaning while every dictionary pair stays unchanged.

The fixed program is deterministic. Its output depends on dictionary order when several entries have the same minimum distance.
This finding does not show that every dictionary entry is wrong.
It does not test whether the manuscript contains Latin or a Romance language.
No manuscript decoding followed this check.

## Source and active method

The source is [mateothour-idk/translate-voynich](https://github.com/mateothour-idk/translate-voynich/tree/93a3d9a52bf8419680bcf2b3eec42ea9ab24476f), commit `93a3d9a52bf8419680bcf2b3eec42ea9ab24476f`.
The [author's announcement](https://www.reddit.com/r/voynich/comments/1wqyjpz/i_built_an_interactive_web_app_to_test_a/) led to this repository.
The announcement describes a beta program with approximate handling of unknown words.
We fixed the source version before function execution.
The hosted service was not tested. This report concerns the pinned repository.

The active [application](https://github.com/mateothour-idk/translate-voynich/blob/93a3d9a52bf8419680bcf2b3eec42ea9ab24476f/voynichapp.py#L145-L192) has its own conversion function.
It changes the input to lowercase, removes characters outside `[a-z\s]`, and applies an ordered list of replacements to each token.
It then compares each resulting phonetic token with every key in the selected dictionary.
The program accepts a minimum Levenshtein distance of at most three.
This distance counts single-character insertions, deletions, and substitutions.

The program imports two dictionaries from [voynichdatos.py](https://github.com/mateothour-idk/translate-voynich/blob/93a3d9a52bf8419680bcf2b3eec42ea9ab24476f/voynichdatos.py#L4-L48).
Each dictionary has 77 entries.
An import failure selects different dictionaries inside the application. This check uses the imported dictionaries.
The function joins selected meanings with spaces. It uses no sentence-level grammar or page context in this path.
Unmatched tokens keep their phonetic spelling in square brackets.

The dictionary loop replaces its current choice only when a new distance is strictly smaller.
The first entry at the minimum distance therefore wins a tie.
The output does not show that distance or the other tied entries.
The examined mapping files give no independent historical citations for their individual sound and meaning assignments.
This limited source check does not establish that such evidence is unavailable elsewhere.

## Short-token bound

Both dictionaries contain the two-character keys `su` and `si`.
Let a phonetic token have length `n`, where `1 <= n <= 3`.
At most `min(n, 2)` substitutions and `abs(n - 2)` insertions or deletions change it to `su`.
The total is `max(n, 2) <= 3`.
Therefore, at least one dictionary entry passes the distance limit for every such token.

This is a bound on the program's phonetic output tokens.
Some replacement rules increase input length, so the statement does not cover every raw input token with three characters.
The bound shows why short-token acceptance alone is not evidence for the assigned meanings.

## Fixed artificial probes

The probe inputs and expected outputs were fixed after source inspection and before the first execution.
They check program behavior; they are not blind linguistic tests.
The checker extracts the two literal dictionaries and only two reviewed functions through Python's abstract syntax tree.
It executes no application startup, corpus loader, network operation, or manuscript input.

| Artificial input | Phonetic output | Original dictionary output | Minimum distance | Tied entries |
| --- | --- | --- | ---: | ---: |
| `f` | `f` | `its` | 2 | 2 |
| `ff` | `ff` | `its` | 2 | 2 |
| `fff` | `fff` | `plant` | 3 | 12 |
| `ffff` | `ffff` | `[ffff]` | 4 | 39 |

Reversing dictionary order changes the first two meanings to `if` and the third to `air`.
The fourth input stays unmatched.
The three exact dictionary matches in the other two inputs keep their outputs under this order change.
The phonetic strings stay unchanged in all six order checks.

The complete probe has eight input cases and six dictionary-order cases.
All fixed expectations match.
The [result record](../../reports/romance-matrix-source-probes-v1.json) includes distances, tied keys, and every output.
These outputs reproduce supplied rules. They do not validate a manuscript reading.

## Version and documentation limits

The [README](https://github.com/mateothour-idk/translate-voynich/blob/93a3d9a52bf8419680bcf2b3eec42ea9ab24476f/README.md) describes conversion in `voynichdata.py`.
The complete repository tree has `voynichdatos.py`, with a different name.
The application imports dictionaries from that file but defines its conversion rules locally.
The small audit script imports the absent filename.
That audit script does not test translation accuracy.

The README gives `eee` as `ie`, whereas the executed function gives `ei`.
The README also describes removal of an isolated `h`; the executed function keeps it.
The separate `reglas.txt` file is not read by this conversion function.
These differences prevent treatment of all listed rule descriptions as one fixed method.

The data module defines a simulated-corpus fallback for a missing local text file.
The examined application does not call that loader.
Its displayed corpus comes from its own network loader.
The artificial checks execute neither loader, and they make no claim about displayed corpus counts.

## Reproduction and verification

The [source record](romance-matrix-source-check-2026-09-29.sources.json) fixes the five inspected files and their SHA-256 values.
The complete tree listed nine files. We did not read either manuscript text file.
Local source bodies, the initial scope, probe expectations, and execution records stay in `results/romance-matrix-check-2026-09-29/`.
The public checker verifies both Python source hashes before it compiles the selected functions.

1. Create a new local source directory.
2. Download `voynichapp.py` and `voynichdatos.py` from the exact raw URLs in the source record.
3. Run the checker with that directory and a new output path:

```sh
python experiments/romance_matrix/check_source.py --source-directory SOURCE_DIRECTORY --output RESULT.json
```

4. Compare the result bytes with `reports/romance-matrix-source-probes-v1.json`.
5. Keep the result and source hashes with the replay record.

A new empty directory with fresh source downloads produced an identical result file.
Its SHA-256 is `9d53a288f0ec35ba4c00f8f05fe82d258c318649ac35181661ed77db32302ab4`.
An altered source failed before output creation. An existing result stayed unchanged after a rejected overwrite.
The required project suite passed all 85 tests.

A separate AI source review confirmed the active dictionary path, replacement order, distance threshold, and tie rule before seeing the probe results.
It also confirmed the differences between the application, README, and rules file.
The primary agent checked the cited lines and the complete result record.
These project checks are not external scholarly validation.

## Decision

This version does not supply independent support for a continuous reading.
Short-token coverage and fluent dictionary words cannot provide that support by themselves.
A future test needs fixed sound rules and external evidence for their meanings before a new passage is decoded.
No replacement meaning, repaired rule, or manuscript search forms part of this study.
