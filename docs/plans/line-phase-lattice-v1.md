# Fixed expansion lengths for all block sizes

Date: 2026-09-29. This is a separate study after the owner asked to continue research.
The [three-digit study](../../reports/LINE_TRIPLET_BOUNDARIES.md) remains unchanged.

## Question

Does the same training evidence exclude phase-changing fixed expansions for every finite code-block size?
The earlier study answered this question only for blocks of three digits.
This study compares a restriction specific to that block size with a restriction that holds for every block size.
It does not search individual block sizes or select a favorable modulus.

For each track, let A contain integer counts for the same selected training lines.
The columns contain sign-unit counts, the internal-space count, and one shared line-ending contribution.
For block size q, the fixed model requires A x = 0 modulo q.
The vector x contains expansion lengths and the two shared contributions.
Code phase means the position within a code block.

An integer matrix B with B A = I gives x = 0 modulo q for every integer q greater than one.
Here I is the identity matrix.
Such a certificate excludes phase-changing fixed expansions under the stated model for all finite block sizes.
It permits zero lengths and all multiples of the block size.
This statement applies separately to each candidate block size. It does not require one length vector to satisfy all block sizes together.
It does not recover symbol values, a language, or plaintext.

## Fixed inputs

Use the same pinned ZL and IT sources, parser, physical-group split, and line selector as the three-digit study.
Keep Currier A and B separate. Keep the visual-compound and raw-EVA representations separate.
Use only the eight training tracks. Do not calculate validation or test constraints.
Keep the original alphabet, source-reference order, and selection hashes for each track.
Check these against the published three-digit record before certificate construction.

Calculate unreduced integer counts from the selected source lines.
The published three-digit coefficient rows contain residues, not full counts.
Do not use those residues as integer counts.
Confirm that reduction of the new counts reproduces each earlier training matrix hash.
Do not add units, lines, boundary locations, padding classes, or phase rules.

## Calculation and stop conditions

Use exact integer row operations with a record of their coefficients.
Process columns in their fixed order. Initially select the smallest nonzero absolute column entry, with current row-slot order as the tie rule.
Initial row slots follow source-reference order.
Use only row swaps, sign changes, and addition of integer multiples of rows.
Make each pivot positive. Use integer division and subtraction below the pivot.
Process rows below the pivot in increasing slot order.
Use the nonnegative remainder for a positive divisor.
Swap each nonzero remainder into the pivot slot and continue with that row until its entry is zero.
Then process the next row. Do not search the whole column again after each remainder swap.
If every diagonal pivot is one, remove the entries above the pivots to construct B.
Remove unused source rows from the public certificate.
Confirm B A = I by direct integer multiplication before reporting success.

Deficient rank contradicts the confirmed modulo-three rank. Treat it as an input or implementation error and stop.
After complete reduction, a nonunit pivot identifies a proper integer row lattice.
That outcome permits nonzero residues for at least one prime modulus. Do not select or test that modulus in this study.
It does not by itself locate freedom in the unit coordinates instead of the two shared contributions.
Do not interpret that outcome as a decoder or as evidence for a code.
Stop each track after ten minutes or if an intermediate integer exceeds 4,096 bits.
Apply these limits to row operations and the final product check, including individual products and running sums.
The standalone certificate verifier uses the same limits.
Keep incomplete output and the failure reason. Do not change selection or limits to obtain a successful result.
Resource stops give no conclusion about the integer row lattice.

## Failure checks and execution

The calculation can fail through residue reuse, changed selection, compound formation across spaces, or omitted contribution columns.
Other risks are sign errors, row-operation errors, incorrect matrix orientation, source drift, and unsupported claims after a resource stop.
Incomplete or malformed certificates must fail verification.

Before implementation, write source-free end-to-end checks for the certificate command.
Include a full integer lattice, a proper sublattice, deficient rank, negative entries, and a changed certificate.
Record commands, expected results, actual results, and output hashes in a repeatable artifact.
Freeze this plan, executable files, dependencies, and source hashes before the manuscript calculation.
Use exclusive output creation. Keep the freeze and each result.

A separate calculation must reproduce the source selection and integer rows.
It must check each certificate by direct multiplication without the row-reduction implementation.
Run the repository test command before publication.
Publish code, aggregate results, coefficient certificates, and verification records without complete line text or word lists.

## Limits

This is a necessary-condition proof for a fixed model, not a test of how unusual the manuscript is.
The source corpus was previously examined. The two transcriptions describe the same physical manuscript.
Format rules do not certify complete physical lines or correct glyph readings.
Independent line phases, variable padding, context-dependent lengths, and units absent from training remain outside the model.
The result cannot test all numerical codes or establish a translation.
