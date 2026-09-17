# Fixed endpoint relation across line breaks

The fixed within-line endpoint model has lower conditional likelihood than the comparison model in both transcriptions.
The result does not support use of that table without change across physical line breaks.
It does not establish a line reset, a language, a cipher, or a translation.

The earlier [boundary report](BOUNDARY_PREDICTION.md) concerns pairs inside one line.
[Smith and Ponzi (2019)](https://agnosticvoynich.files.wordpress.com/2019/06/glyph-combinations-across-word-breaks-in-the-voynich-manuscript-preprint.pdf) also excluded line-break pairs.
This check uses the last word of one line and the first word of the next line.
No claim of a first discovery is made.

Two models were fixed before extraction and scoring:

- H0 gives equal probability to all distinct arrangements of preceding final units within each matched cell.
- H1 gives each arrangement a weight from the unchanged within-line probability table.

Each cell keeps the following initial unit fixed at each target position.
The preceding final units can change positions within the cell; their multiset stays fixed.
Cells match folio, paragraph-first status of the preceding line, and both endpoint word lengths.
The comparison therefore removes differences in these cell-level marginal counts.
It does not control total line length, paragraph topic, or all effects of layout.
It does not preserve every line's internal composition under rearrangement.

H1 uses the existing training groups, `interior` table, alpha 0.1, and tau 10.
No cross-line parameter or strength factor was fitted.
The primary representation uses the existing six visual compounds. Raw EVA is a sensitivity check.
EVA describes written forms; these units are not established letters or sounds.

Selection starts from the complete source record order, before any line is removed.
Each pair has consecutive numeric loci on one folio, inside one closed marked paragraph.
Both loci must be P0 or P1. The following locator must be `+` or `*`.
Both lines must contain at least three complete words with unambiguous spacing and lowercase forms.
Drawing interruptions, rejected words, and special sign notation are excluded.
No pair crosses a removed record or paragraph boundary.
The [IVTFF specification](https://voynich.nu/software/ivtt/IVTFF_format.pdf) defines these layout codes and paragraph markers.
Paragraph boundaries remain transcriber decisions.

The score is the base-two logarithm of the conditional likelihood ratio, H1 divided by H0.
Negative values favor H0 under these two models.
The calculation includes every distinct endpoint arrangement in each cell.
It uses floating-point arithmetic, not a random sample of arrangements.

| Source | Units | Eligible pairs | Cells with both endpoints variable | Pairs in those cells | Log2 likelihood ratio |
| --- | --- | ---: | ---: | ---: | ---: |
| ZL | Six visual compounds | 185 | 12 | 24 | -7.262 |
| IT | Six visual compounds | 752 | 90 | 233 | -39.475 |
| ZL | Raw EVA | 185 | 10 | 20 | -4.671 |
| IT | Raw EVA | 752 | 77 | 206 | -22.064 |

The primary ZL cells cover eight physical groups. The primary IT cells cover eleven.
After removal of any one group, the visual ZL ratio remains between -7.692 and -4.665 bits.
The corresponding IT range is -39.525 to -30.889 bits.
Both ranges retain the result's direction. No single physical group determines that direction.
The raw results also retain their negative direction after each group removal.

The aggregate ratio assumes that the conditional models factor across cells.
Shared folios, paragraphs, and adjacent lines can create other dependencies.
This ratio is not a p-value or a probability that a writing mechanism is correct.
It tests the fixed pattern and its strength together.
A lower H1 likelihood does not establish absence of all cross-line dependence.
The two transcriptions describe the same manuscript. Their ratios must not be multiplied as independent evidence.
The strict rules leave substantially different source subsets, especially in ZL.
The corpus was previously inspected, so this remains exploratory evidence.

A separate selector matched all 937 source pairs and their paragraph assignments.
It reused the source parser but rebuilt paragraph spans, adjacency checks, spelling checks, and group selection.
A second calculation rebuilt the interior probability counts and enumerated each distinct arrangement directly.
It matched the count-vector calculation for all informative cells, group contributions, and totals.
The largest arithmetic difference was below 1.5e-14 bits.
Source-free fixtures checked repeated units, invariant cells, unequal weights, locus parsing, and the probability interface.
Three interface defects in the second script were corrected before its first manuscript run.
These checks establish calculation agreement. They are not independent transcription or external scholarly validation.

After scoring, a diagnostic image check selected the three ZL cells with the largest negative contributions.
Their six line connections occur on [f6v](https://collections.library.yale.edu/iiif/2/1006087/full/full/0/default.jpg),
[f82r](https://collections.library.yale.edu/iiif/2/1006222/full/full/0/default.jpg),
and [f86v5](https://collections.library.yale.edu/iiif/2/1006230/full/full/0/default.jpg).
AI inspection supports immediate line adjacency and placement within the recorded text blocks for all six connections.
One f82r view has a clipped glyph edge. A separate misaligned crop was excluded from the image evidence.
Endpoint glyph readings remain provisional. No complete transcription was independently certified.
This selected diagnostic is not blind validation and does not verify all scored pairs.
No image review changed a source reading, selected pair, or score.

The unchanged-transfer branch is stopped. No new filter, probability table, or fitted strength was introduced.
A later model that uses this table across line breaks must explain this result.
This result supplies a model constraint, not a decipherment.

Local records remain in `results/cross-line-transfer-v1/`.
They include the plan, two calculations, selected pairs, full cell scores, and verification receipt.
These local records are not published artifacts.

| Record | SHA-256 |
| --- | --- |
| Fixed plan | `6dc323f47206798771a30eb71b5c18f67c9712a19c96af686e7bbf83f1d95b59` |
| Count-vector result | `1ad1779d62f86529e7907ffe70e0ca5108fee906e50c8c7d81c2b2a5c4c00499` |
| Direct-enumeration result | `24c432d894adf2a3771600b564ae8e2ad669c1f70aa8b887a9d501c101599dee` |
