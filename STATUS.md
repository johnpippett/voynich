# Research status

The objective is to explain the Voynich manuscript's writing system and recover its content where possible.
That objective remains unresolved.
The project has no validated key, plaintext language, or translation.

## Completed research

The [complete-key report](reports/OPTIMAL_SET.md) contains the latest Latin development result.
The [assignment report](reports/IDENTIFIABILITY.md) contains the preceding conditional assignment results.
The [homophonic report](reports/HOMOPHONIC.md) contains the preceding controls and their limits.
The [lexicon report](reports/LEXICON.md) contains the earlier manuscript bounds.
The [Stage 2 report](reports/STAGE2.md) contains the earlier controlled searches.
The [initial report](reports/FINDINGS.md) preserves the earlier exploratory results.
The [Celsus projection report](reports/CELSUS_PROJECTION.md) validates one ancient medical source extraction.
The [Celsus partition report](reports/CELSUS_PARTITIONS.md) records 101,715 word tokens and independent checks of the fixed chapter split.
The [Italian search report](reports/HOMOPHONIC_SEARCH_DEVELOPMENT.md) records local-search improvements and remaining score bounds.

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
