# Fixed expansion lengths for all code-block sizes

Research date: 2026-09-29.

Five training tracks have an exact integer certificate for every finite code-block size.
Under the fixed model, each represented unit must emit a multiple of the chosen block size.
The shared space and line-ending contributions must also be multiples of that size.
Three other tracks reached the fixed integer-size limit. They remain inconclusive.
The calculation supplies no symbol values, language, or plaintext.

## Question and fixed model

The [earlier experiment](LINE_TRIPLET_BOUNDARIES.md) established this restriction for blocks of three digits in all eight tracks.
The new question concerns every finite block size, without a search over individual moduli.
The owner asked to continue research before this separate study began.
The [plan](../docs/plans/line-phase-lattice-v1.md) and [file freeze](../experiments/line_phase/freeze-v1.json) preceded the calculation.

Each sign unit emits a fixed string of unknown length.
Each apparent internal space and each line ending have one shared contribution within a track.
Each selected line must return to a common code phase.
Code phase means the position within a code block.
Currier A and B have separate unknown length vectors.

For block size `q > 1`, the necessary condition is:

```text
A x = 0 modulo q
```

The matrix `A` contains integer unit counts, the internal-space count, and a final column of ones.
The vector `x` contains the unit lengths and the two shared contributions.
The published certificates give integer matrices `B` and selected rows `A_support` such that:

```text
B A_support = I
x = B A_support x = 0 modulo q
```

Here `I` is the identity matrix.
The same certificate applies to each candidate block size separately.
It does not require one length vector to satisfy all block sizes together.
It permits zero lengths and all nonnegative multiples of the selected block size.
It does not force numerical lengths to be zero.

## Inputs and method

The calculation keeps the earlier source pins, training split, line selection, alphabets, and eight source/class/representation tracks.
It reconstructs full integer counts from every selected training line.
The earlier public tables contain residues modulo three. They cannot replace these full counts.
All eight selection hashes and reduced training-matrix hashes match the earlier experiment.
No validation or test constraints entered the calculation.

Exact integer row operations construct a possible left inverse.
The method fixes the pivot order and keeps the coefficients of each row operation.
Direct multiplication checks every completed certificate.
The fixed limits are 600 seconds per track and 4,096 bits per intermediate integer.
No limit, unit inventory, or source selection changed after the calculation.

## Results

| Source | Class | Representation | Training lines | Columns | Certificate rows | Outcome |
| --- | --- | --- | ---: | ---: | ---: | --- |
| ZL | A | Visual compounds | 221 | 26 | 28 | Proved for every block size |
| ZL | B | Visual compounds | 539 | 27 | — | Integer-size limit |
| IT | A | Visual compounds | 469 | 27 | 29 | Proved for every block size |
| IT | B | Visual compounds | 1,255 | 28 | 31 | Proved for every block size |
| ZL | A | Raw EVA | 221 | 23 | 26 | Proved for every block size |
| ZL | B | Raw EVA | 539 | 23 | — | Integer-size limit |
| IT | A | Raw EVA | 469 | 21 | 22 | Proved for every block size |
| IT | B | Raw EVA | 1,255 | 22 | — | Integer-size limit |

Thus, both class-A sources support the restriction under both unit representations.
The IT class-B visual track also supports it.
The three resource stops do not establish a proper row lattice or a surviving nonzero residue.
They show only that this fixed calculation exceeded its integer-size limit.
The earlier modulo-three result remains valid for those tracks.

The [result record](line-phase-lattice-v1/result.json) gives every matrix hash and certificate hash.
The same directory contains five exact certificates and three resource-stop records.
The certificates contain count vectors and source references, without line text or word lists.

## Verification

The [command-check record](line-phase-lattice-e2e.json) contains 28 successful source-free end-to-end checks and the freeze-gate correction.
The checks include a proper lattice with full rank modulo three and a full integer lattice without a determinant-one square submatrix.
They also check malformed inputs, changed certificates, resource stops, and refusal to replace output files.
The tests do not exercise a 600-second timeout.

The primary agent checked all five integer products directly.
The [separate source check](line-phase-lattice-verification.json) reconstructs all eight training matrices and checks the five certificates against their source rows.
It also checks the three resource-stop records without treating them as mathematical results.
It reuses the existing parser, group split, and unit tokenizer. It does not use the new certificate-construction code.
These are checks within this project, not external scholarly validation.

The original frozen source verifier requires eight completed certificates, so it rejects the partial result.
That rejection remains in the local record.
The successful source check verified all eight matrices, five proofs, and three inconclusive resource stops.
An additional [partial-result verifier](../scripts/verify_line_phase_partial.py) supports the declared resource-stop outcome without changing the frozen calculation.

## Reproduction

The source pins are in [source_manifest.json](../data/source_manifest.json).
The repository download command retrieves those files and checks their hashes.
The following commands create a new run and a new verification receipt.
The verification command checks the published result against the local pinned sources.

```sh
python scripts/fetch_sources.py
python scripts/run_line_phase_lattice.py --freeze experiments/line_phase/freeze-v1.json --output results/line-phase-replay-v1
python scripts/verify_line_phase_partial.py --freeze experiments/line_phase/freeze-v1.json --results reports/line-phase-lattice-v1 --output results/line-phase-lattice-verification-v1/replay.json
```

The source-free proof command can check one published certificate without the transcription files:

```sh
python scripts/line_phase_lattice.py verify reports/line-phase-lattice-v1/ZL-A-visual.json
```

## Limits and stop decision

This result is a necessary condition for the fixed model. It does not measure how unusual the manuscript is.
The sources describe the same manuscript, and the analysis uses previously examined data.
The five proofs are not five independent physical replications.
Format-selected lines and EVA unit groups do not establish physical sign boundaries, complete lines, or linguistic units.

Variable padding, independent line phases, context-dependent expansions, and units absent from training remain outside the model.
The result does not reject all numerical codes or identify the writing mechanism.
The inevitable zero-residue vector gives no prediction evidence.
The study stops with five proofs and three inconclusive tracks. It does not increase resources or change the model after these outcomes.
