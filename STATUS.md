# Research status

The objective is to explain the Voynich manuscript's writing system and recover its content where possible.
That objective remains unresolved.
The project has no validated key, plaintext language, or translation.
The owner asked to continue research on 2026-09-29.
The [continuation record](docs/research/continuation-record-2026-09-29.md) defines the selected work and outstanding limits.
The [pause record](docs/research/pause-record-2026-09-17.md) preserves the earlier findings and unfinished development.

## Current findings and stopped branches

The [Romance matrix check](docs/research/romance-matrix-source-check-2026-09-29.md) finds automatic dictionary acceptance for every phonetic token with one to three characters.
The program's edit-distance rule also gives different meanings when equal-distance entries change order.
Eight artificial inputs and six order checks reproduced this behavior. They supply no manuscript reading or independent evidence for the meanings.

The [Naibbe relabeling control](reports/NAIBBE_RELABEL_CONTROL.md) tests four known keys on artificial Latin text without original spaces.
All four searches failed, with at most two correct assignments among the observed test labels.
In every case, the known key has a lower fit loss than the saved search key.
Thus, these saved maps are not optima for the fixed objective. This result does not reject Latin, Naibbe, or all possible keys.

The attempt stops without a manuscript experiment. A clean replay reproduced all result fields except elapsed time.

The [historical source check](docs/research/historical-key-comparisons-2026-09-29.md) now includes a complete printed key from Meister's 1902 book.
Its printed 1448 date remains uncertain because named titles have later dates under specific identifications.
The neighboring 1483 key has separate rules. Fontana's complete sign assignments remain outside the reviewed sources.
It supplies no fixed correspondence with Voynich signs.
The reviewed Pahlavi proposal leaves reading choices unresolved in its continuous-text example.

The [Hebrew source check](docs/research/hebrew-key-audit-2026-09-29.md) confirms a fixed consonant transliteration on eleven artificial inputs.
Its word-generation prompt receives the decoded target before it requests alternatives.
Those matches cannot independently establish meanings. The paper reports that its fixed output does not read as Hebrew.
The check establishes no manuscript key or translation.

The [Sun and Moon name check](reports/SOLAR_LUNAR_NAMES.md) finds no common complete word for either fixed pair of figures.
Both transcriptions give empty intersections under both uncertain-space rules.
The result concerns accepted tokens on one foldout. Uncertain readings and circular boundaries limit the conclusion.
The exact-name branch stops without a candidate name or sign value.

The [astronomical source review](docs/research/astronomical-anchor-review-2026-09-29.md) establishes no fixed planet or sector name correspondence.
It also confirms a 2009 ink sample from f116v, without resolving the external locus's hand or writing layer.

The [candidate-key audit](docs/research/candidate-key-audit-2026-09-29.md) checks the current ZFD corpus decoder and its evidence.
Three of four guide examples disagree with the current corpus decoder.
A control changes all four glosses without a change to the confidence scores.
The fixed sample line is absent from both pinned f88r transcriptions under the specified checks.
The corpus check tests repeatable output. A separate statistical test uses another decoder and lexicon configuration.
The historical ingredient-set comparison cannot select pairs between written forms and meanings by itself.
A recent sign-unit study measures class-letter agreement, which differs from complete plaintext recovery.
These source checks supply no verified manuscript key or translation.

The [further source study](docs/research/further-key-routes-2026-09-29.md) separates Preedy's structural scores from verification of meanings.
The examined ATA sound tables are not final and leave reading choices unresolved.
A documented Florentine cipher gives a historical state rule, but no assignment to Voynich signs.
No new manuscript fit followed these source findings.

The [integer line-phase study](reports/LINE_PHASE_LATTICE.md) extends the earlier modulo-three condition to every finite block size in five training tracks.
Both class-A sources pass under both unit representations. The IT class-B visual track also passes.
Three other tracks reached the fixed 4,096-bit limit and remain inconclusive.
Under the fixed common-phase model, each represented length and shared contribution must be a multiple of the chosen block size.
This necessary condition supplies no symbol values or plaintext. The study stops without changed limits or additional data.

The [source refresh](docs/research/source-availability-2026-09-29.md) found a newer zodiac replication archive.
It does not restore the original answer CSV files. The Caspari–Faccini supplement remains absent from the checked listings.

A [zodiac degree-alignment control](reports/ZODIAC_PANEL_CONTROL.md) tests a published figure-attribute sequence while preserving each physical panel's class counts.
The fixed alignment has 52 matches among 78 known positions. Its exact conditional p-value is 0.42044.
We stopped this alignment as a source of fine positional constraints for label interpretation.
The result depends on the released sequence and table vectors. Missing raw inputs prevent independent verification of the answer-to-image joins.

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
