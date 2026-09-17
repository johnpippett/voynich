# Research status

The objective is to explain the Voynich manuscript's writing system and recover its content where possible.
That objective remains unresolved.
The project has no validated key, plaintext language, or translation.

## Current findings and stopped branches

A [text-column comparison](reports/COLUMN_ASSOCIATION.md) finds a small word-similarity excess in both transcriptions.
A control that preserves complete lines does not meet the declared criterion for an additional line-order effect.
The one-sided permutation p-values are 0.1586 for ZL and 0.0558 for IT.
We stopped this statistic. The column association alone does not establish copying between neighboring lines.

Two complete radial labels on f69v are identical in both pinned transcriptions.
They cannot map to different names through a fixed, context-independent function.
This [collision check](docs/research/anchor-audit.md#lunar-mansion-names-complete-label-collision) stops a one-to-one reading of the 28 labels as one fixed historical list.
It remains conditional on transcription equality and label role. It does not reject lunar content or position-dependent decoding.

The [fixed-expansion test](reports/LINE_TRIPLET_BOUNDARIES.md) gives an exact constraint on one three-digit code model.
It assumes fixed expansion lengths and shared space and line-ending contributions that restore the same code phase after each selected line.
Every represented training-unit length must then be divisible by three, separately in Currier A and B in both sources.
The result permits lengths zero, three, six, and larger multiples. It identifies no digit values or plaintext.

Spaces need not mark plaintext words. Variable padding, independent line phases, other unit inventories, and context-dependent expansions remain outside this model.
The [source audit](docs/research/anchor-audit.md) also records the stopped Hannig and gallows-continuation checks.
The examined Schechter decoder retrieves assigned whole-word meanings. Its coverage cannot distinguish those meanings from other nonempty assignments.
We stopped its sign-rule transfer branch without running the package. No plaintext resulted.
The Caspari–Faccini preprint supplies a partial visual key but leaves reading choices dependent on context.
We stopped full automatic decoder replication. The linked supplement was unavailable through the inspected source listings.

The [cross-boundary test](reports/BOUNDARY_PREDICTION.md) finds transferable prediction between recorded word parts.
A preceding final unit reduces the next initial-unit loss by about 0.18–0.20 bits in the visual-unit track.
An excess remains under matched folio, position, and word-length controls in both transcriptions.
The matched predecessor null can change labels for only 30.3% of ZL targets and 37.4% of IT targets.
The effect varies across page groups. It does not establish linguistic spaces, sounds, or meaning.
The main unitization has no gain on the small subset where both word types were absent from training.
A same-remainder control retains a positive excess in a small selected subset.
The `a/o` and `ch/sh` component results differ. They do not justify merging these signs.
All selected `a/o` targets have two units. Source readings and image judgments disagree at some locations.
We stopped further tuning of this short-form association. It does not identify a writing mechanism.
This is a constraint for future models, not a translation.

The fixed endpoint table has lower conditional likelihood than the matched comparison model [across physical line breaks](reports/CROSS_LINE_TRANSFER.md).
This result does not establish a line reset or absence of all cross-line dependence.

The [local word-memory test](reports/LOCAL_MEMORY.md) found no useful prediction gain from the observed word order.
Both transcriptions selected zero weight for exact repetition.
The edit model did not retain a useful advantage under the two word-order controls.
This result applies only to the specified vocabulary, raw EVA units, context windows, and group split.
It does not reject language or all copying processes.
We stopped this model branch without further parameter changes.

The synthetic cyclic quotient-recovery branch is also stopped.
Its unfinished development files produced no new manuscript result.
More solver work would not resolve the missing historical mapping.

Further experiments must state which competing explanations their results can distinguish.
Code, tests, and publications are supporting work. They are not decipherment results.

## Completed research

The [complete-key report](reports/OPTIMAL_SET.md) contains the Latin letter-recovery development result.
The [assignment report](reports/IDENTIFIABILITY.md) contains the preceding conditional assignment results.
The [homophonic report](reports/HOMOPHONIC.md) contains the preceding controls and their limits.
The [lexicon report](reports/LEXICON.md) contains the earlier manuscript bounds.
The [Stage 2 report](reports/STAGE2.md) contains the earlier controlled searches.
The [initial report](reports/FINDINGS.md) preserves the earlier exploratory results.
The [Celsus projection report](reports/CELSUS_PROJECTION.md) validates one ancient medical source extraction.
The [Celsus partition report](reports/CELSUS_PARTITIONS.md) records 101,715 word tokens and independent checks of the fixed chapter split.
The [Celsus model report](reports/CELSUS_MODEL.md) records an incomplete known-cipher search and failed exact-recovery gates.
The [Italian search report](reports/HOMOPHONIC_SEARCH_DEVELOPMENT.md) records local-search improvements and remaining score bounds.
The [cyclic pairing report](reports/CYCLIC_PAIRING.md) identifies 23 forced Latin pairs and 21 forced Italian pairs without plaintext-letter assignments.
The [local cyclic test](reports/LOCAL_CYCLIC.md) rejects the exact cyclic emitter on two fixed transcription unitizations. Both image checks remain uncertain.

The current work includes:

- Pinned transcriptions, source records, and tests for parsing and statistics.
- A complete map of the provider's 52 quire/bifolio groups.
- Repeated structural experiments with the corrected physical grouping.
- Pinned Latin and Old Italian reference texts with document-based partitions.
- Exact recovery of known substitution controls for 32 keys per language.
- Four unsuccessful manuscript substitution attempts with frozen keys and control scores.
- A complete candidate enumerator for the fixed published Naibbe tables.
- Global score bounds for four fixed lexicon and manuscript-training problems.
- Exact test-text recovery for two lexicon controls, with explicit key-ambiguity counts.
- Four homophonic controls with frozen settings, saved maps, recovery errors, and score bounds.
- Complete alternative-assignment queries for all 46 fitted units in the Latin homophonic control.
- Complete enumeration of four dictionary-optimal maps and exact character-model ranking of those maps.
- Two matching Celsus text projections, a byte-identical public replay, and AI inspection of 30 fixed source locations.

The Latin homophonic controls reached a certified dictionary optimum with four test character errors.
Exactly four keys attain that optimum. Certification alone does not establish the correct key.
The Italian controls stopped with unequal bounds and incomplete recovery.
All four controls failed their declared exact-recovery checks.

The assignment study proves that 45 selected assignments are necessary to attain the certified Latin dictionary score.
The remaining assignment is ambiguous. All four test errors occur at this unit.
The forced assignments cover 111,048 test characters without errors.
These results concern one finite objective and domain. They do not identify a manuscript key.
The study follows an inspected control failure and is not blind validation.

The later complete-key study retains all four optimal maps for the 46 observed units.
The training-only character model uniquely selects the correct observed map, with exact likelihood ratio `8036/1131` over each alternative.
That map recovers all 111,052 test characters and 19,931 test words.
A clean public replay matches all five result files. A separate calculation confirms all 18 audit checks.
This repairs the inspected Latin example. It does not change the original failed gates or validate a manuscript decoder.

Separate AI-agent tasks performed implementation and code review within this project.
These checks do not constitute external scholarly validation.
The original manuscript data remain essential for further research.

## Open questions

EVA code points are not established linguistic units.
A fixed substitution with preserved spaces is only one possible model.
The reference corpora do not cover all historical languages, genres, or spelling conventions.
The present search does not prove that every possible substitution key fails.
The new bounds concern specific finite lexicons and training samples.
They do not identify the optimum manuscript score or a historical key.
Naibbe compatibility does not identify a historical key or a unique plaintext.

Further work must test additional global encodings and independently justified sign units.
Each experiment must have known solutions, control failures, declared limits, and reproducible results.
A proposed solution must also meet the [validation protocol](docs/research/validation-protocol.md).

The public repository contains research methods and results.
Personal information and private attachment metadata remain excluded.
