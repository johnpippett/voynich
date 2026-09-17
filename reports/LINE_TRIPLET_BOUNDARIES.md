# Fixed expansion lengths at line boundaries

Under the model below, every unit represented in training must have an expansion length divisible by three.
The model requires a common code phase at selected line boundaries. Spaces need not mark plaintext words.
All eight training matrices have full column rank. The result identifies no digit values, language, or plaintext.

## Model and competing outcomes

The earlier [word-boundary test](TRIPLET_BOUNDARIES.md) required each selected word to return to a common three-digit code phase.
Spaces need not mark plaintext words. Each internal space has one shared contribution.
Only each selected text line, with its fixed ending contribution, must return to the same phase.
Code phase is the position within a three-digit group.

Each unit emits a fixed digit string of unknown length `l[u]`.
Each internal space contributes the same unknown length `p`.
Each line ending contributes the same unknown length `b`.
There are no separate contributions that can change for each line.
Currier A and B have separate rules.

For line `i`, `C[i,u]` counts unit `u`, and `S[i]` counts internal spaces.
The model requires:

```text
sum(C[i,u] * l[u]) + S[i] * p + b = 0 modulo 3
```

A surviving nonzero unit remainder would keep a phase-changing fixed expansion compatible with this condition.
If every unit remainder is zero, each represented unit length must be divisible by three.
This allows lengths zero, three, six, and larger multiples. It excludes fixed lengths one, two, four, five, and other nonmultiples.
Neither outcome establishes a code or an absolute alignment of plaintext letters.

## Selection

The inputs are the pinned ZL and IT transcriptions in the [source manifest](../data/source_manifest.json).
The existing physical-group split remains fixed.
The primary representation joins `cth`, `ckh`, `cph`, `cfh`, `ch`, and `sh` with the existing longest-match rule.
Raw EVA supplies the sensitivity calculation.
The two classes, two sources, and two representations supply eight separate tracks.

The current record must be ordinary paragraph text of type `P0` or `P1` with class A or B.
The following record can have another type.
The current and next records must have `+` or `*` locators, consecutive locus numbers, and the same folio.
The [IVTFF specification](https://www.voynich.nu/software/ivtt/IVTFF_format.pdf), Table 8, defines these locators relative to the preceding locus.
These rules exclude first-on-page `@` records, records with an attached same-line item, missing next loci, and final records on each folio.

They select lines from format information. Image review has not certified their completeness or glyph readings.

The existing strict whole-line selector requires at least three lowercase words separated by literal periods.
After the specified control removal, these words must exactly match the parser tokens. Uncertainty, ambiguous spaces, and drawing interruptions exclude the line.
Compounds form within each word only. The number of internal spaces is the word count minus one.

The column alphabet comes from training only. The last two columns represent `p` and `b`.
Exact elimination gives the full nullspace, then its projection onto unit coordinates.
That projection permits both unknown contributions when it determines which unit lengths remain possible.
The plan stops a track when the projection is zero. Later constraints cannot restore unit freedom.

## Results

Every training row is distinct after reduction modulo three.
The column count includes the two unknown contributions.

| Source | Class | Units | Training lines | Columns | Rank | Unit freedom |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| ZL | A | Visual compounds | 221 | 26 | 26 | 0 |
| ZL | B | Visual compounds | 539 | 27 | 27 | 0 |
| IT | A | Visual compounds | 469 | 27 | 27 | 0 |
| IT | B | Visual compounds | 1,255 | 28 | 28 | 0 |
| ZL | A | Raw EVA | 221 | 23 | 23 | 0 |
| ZL | B | Raw EVA | 539 | 23 | 23 | 0 |
| IT | A | Raw EVA | 469 | 21 | 21 | 0 |
| IT | B | Raw EVA | 1,255 | 22 | 22 | 0 |

All eight systems force zero remainders for the represented unit lengths and both contribution coordinates.
All tracks stopped at training. No validation or test constraints were evaluated.
The inevitable survival of the zero vector supplies no prediction evidence.

The rule permits the next record to be a different text type.
In ZL training, three selected class-B lines precede `L0` label records. The IT count is nine.
Other next records have types `P0`, `P1`, `Pc`, or `Pr`.
The public certificates include all counts by next-record type.

## Limits and stopped branch

This result applies only to the fixed common-phase model, selected unit inventories, and format-selected lines.
It does not require spaces to be plaintext-word boundaries. It still requires fixed apparent spaces for the coefficient counts.
Units absent from training remain outside the conclusion.
Variable padding, discarded remainders, independent line phases, and context-dependent expansions remain outside the model.

The calculation gives a necessary condition. It does not measure how unusual the manuscript is.
The transcriptions describe the same physical manuscript, and the A/B classes are strata within it.
These are not eight independent physical replications. The corpus was previously examined, so this analysis is exploratory.
The result does not test the complete [Matlach proposal](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0260948) or establish a decipherment.

The branch is stopped. No new moduli, boundary locations, padding classes, or phase rules were fitted.

## Verification records

The [public coefficient certificates](line-triplet-boundary-certificates.json) contain 197 source rows across the eight systems.
Each square matrix has a determinant that is nonzero modulo three. This proves full column rank.
The primary agent verified the determinants with exact rational arithmetic.
The records contain source locations and coefficient rows, without line text or word lists.

A separate AI calculation reproduced the selected source references, exclusions, matrix hashes, ranks, nullspaces, and all 197 certificate rows.
It used a separate line selector and exact integer determinants. It reused the parser, physical-group split, and unit representation.
These checks verify the calculation. They are not independent transcriptions or external scholarly validation.

Local records remain in `results/line-triplet-residue-v1/`.
Source-free controls verify line selection, compound boundaries, shared contributions, and nullspaces with freedom only in contribution coordinates.

| Record | SHA-256 |
| --- | --- |
| Plan | `acb8ea0b6b579dee7458afabcfb4ba3752c7d24aa57661508cd2d9d92b06b0c4` |
| Executed script | `41a7d0076e9b1610208cde1f8618c381ef5615e2131c4a3bf92d123af7074c89` |
| Result | `3d5ceca1c7b96ed2de895903eb71c782475f88a8e2496ba94cbfa6d56cffcbe6` |
| Verification script | `7bc6210166be39d205e54b90296ad35af693e5192b3030f61352cde08538bdcd` |
| Verification result | `2553333ece5e3fff297a49b493eaac855c92533a33577e4db1661767f7be73c1` |
