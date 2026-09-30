# Decipherist reading-method source check

Date: 2026-09-30.

The examined Decipherist method does not define all changes needed for its printed word examples.
Its cited historical manuscripts supply useful comparisons, but no Voynich sign assignments.
This check supplies no validated key or translation.

## Printed rules and examples

The [article](https://thedecipherist.com/articles/voynich_manuscript/) proposes reading from right to left and gives a partial sign table.
The selected method sections also state that vowels can be implied or abbreviated.
They do not specify vowel omission, placement, or selection rules for these rows. Other letter changes also remain undefined.

A bounded calculation used two vocabulary rows and only the listed character values.
It reversed each printed Unicode sequence and enumerated every permitted value combination.
The plan fixed expected results and failure conditions before the calculation.

| Printed source token | Claimed word | All outputs from the explicit table and reversal |
| --- | --- | --- |
| `oꝺꝺa` | `OLLA` | `ALLA`, `ALLO`, `LLA`, `LLO` |
| `oꝺꝺo` | `OLIO` | `ALLA`, `ALLO`, `OLLA`, `OLLO` |

Neither output set contains its claimed word. Both sets agree with the plan's expected results.
This calculation uses only the explicit values and reversal.

These printed labels are not verified EVA symbols or independently checked manuscript transcriptions.
EVA means Extensible Voynich Alphabet, a transcription system.
This narrow result identifies missing reading rules. It does not reject every abbreviation method or the proposed language.

## Historical comparisons

The [Cambridge catalogue](https://cudl.lib.cam.ac.uk/iiif/MS-DD-00010-00068) describes MS Dd.10.68 as a medical compilation with astrological and philosophical material.
It dates the Italian handwriting to the fourteenth or early fifteenth century.
It also identifies a medical sonnet in Judaeo-Italian, written in Hebrew script.
This source supports the historical existence of the broad language practice and genre.
It does not establish a correspondence with Voynich signs.

The [Bodleian catalogue](https://iiif.bodleian.ox.ac.uk/iiif/manifest/beb0de5a-04fd-4ee7-b622-c3ebdca105ef.json) identifies MS. Reggio 43 as a Hebrew collection with medical and astronomical texts.
Its date statement spans 1275–1860; this range does not date each component.
No original manuscript text or image from either collection formed part of this check.

## Additional source selection

Another AI task used three searches to examine possible methods by [Ulyanenkov](https://arxiv.org/abs/1604.04149) and [Jama](https://arxiv.org/abs/2505.02261).
It found no method ready for a reading test within the material examined.
This limited result does not establish that either complete paper lacks a key or validation.

The PDF reader exposed nine Ulyanenkov pages in one response. With two abstract records, this exceeded the six-page limit by five pages.
The worker stopped further source review. It read no Jama paper pages.
The remaining paper contents are unverified. This report makes no detailed claim about their methods.

## Decision and verification

A reading test needs complete rules for the sign values, supplied vowels, and other changes before evaluation on unseen text.
The examined source sections do not meet that requirement.
No new sign value, manuscript decoding run, or translation repair followed.

The [source record](decipherist-reading-method-check-2026-09-30.sources.json) gives source hashes, selected sections, exact calculation inputs, and access limits.
To repeat the calculation, reverse each listed token and concatenate every combination of its recorded character values.
Compare the resulting set with the claimed word. Do not add an unstated reading operation.

The Cambridge viewer returned HTTP 403, but its descriptive image-service manifest was available.
All four source hashes and byte counts agreed. A repeat calculation reproduced both output sets.
Another AI task examined the same source sections and agreed about the incomplete reading rules.
All 85 project tests passed. These software checks do not validate any proposed manuscript meaning.

Detailed source captures and calculation records stay in `results/remaining-reading-routes-2026-09-30/`.
The existing validation rules and stopped studies remain unchanged.
