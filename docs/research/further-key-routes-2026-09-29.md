# Further reading methods

Date: 2026-09-29.
This source study examines two published reading methods and one historical cipher.
It supplies no Voynich key or translation.
No manuscript search or decoder execution followed this study.

## Preedy: structure and meaning

The [main key](https://voynichmanuscriptdecoded.com/key/index.html) gives English concepts and roles for written signs.
Examples include fire and sunrise.
Some descriptions depend on a page's proposed subject, such as a plant, a body, or a vessel.
A semantic writing system can use signs without letter values.
The relevant question is whether fixed rules and external evidence identify its readings.

The [Bayesian report](https://voynichmanuscriptdecoded.com/research/Preedy_BSI_Report.pdf), dated 10 September 2026, tests prediction of an encoded sign sequence.
Its representation has 28 observed machine states from 29 key entries.
The report gives rules for a deterministic symbol encoder and states that its package contains the code.
Section 5.2 states that the experiment does not test the English descriptions against external referents.
It includes no plaintext recovery test.
We did not reproduce its numerical results.

The [codebook report](https://voynichmanuscriptdecoded.com/research/Preedy_Codebook_Transfer_Report.pdf), dated 12 September 2026, compares 5,040 permutations of seven roles.
Its model keeps the training labels and changes the test labels.
The original labels give the best reported score.
Section 4 also tests some renamings on both training and test data, with new model fits.
Those checks give equal scores.
Thus this comparison tests consistency between folios; it does not independently select the English meanings.

Both reports state these limits.
These structural results do not show that the English meanings are correct.
The examined sources do not give complete rules to select and combine all labels into one continuous English reading.
The BSI report gives hashes for a replication package available through an email request.
This study did not request the package or contact its authors.

## ATA: unfinished sound tables

The examined [ATA tables](https://www.turkicresearch.com/files/articles/3070.pdf) are not final.
The English notes on pages 2–3 state their limits.
Their notes distinguish tried sound values from alternatives that still need tests.
The table contains unresolved alternatives and does not include all manuscript signs.
Its stated aim is one fixed assignment, with exceptions for phonetic harmony.

The [November 2025 phonetic-range study](https://www.turkicresearch.com/files/articles/4071.pdf), pages 3–4, also states that its sound values are not final.
It gives alternative vowel readings and uses sentence context to select meanings.
Context and multiple sound values do not, by themselves, invalidate a writing system.
However, these sources do not fix all choices needed for a reproducible continuous reading.
We did not select missing values, merge table entries, or infer a completed decoder.

This finding concerns the examined versions.
It does not reject Turkish or every version of the proposed method.
A future test needs fixed sign recognition, sound-selection rules, and grammar before the test passage is read.

## A historical cipher with a changing alphabet

[Marco Vito's 2025 paper](https://dspace.ut.ee/bitstreams/40aeef0d-efa0-482f-8040-ead396b2dfc2/download) presents a cipher for Piero Capponi.
The paper considers 1484–1485 or 1486–1487 and suggests 1487 as the most likely date.
It gives no evidence of use beyond the intended recipient.
It is a later comparison, not a recovered Voynich key.

After each encoded letter, the next cipher sign becomes the starting point for the following letter.
The historical example maps `papa` to `t4li`.
Null signs carry no plaintext letter and do not change this state.
The source also has a nomenclator, a table of codes for whole words.
The alphabet's left side is damaged.

The method gives a concrete cipher family.
It supplies no assignment between Voynich shapes and that family's sign order from external evidence.
The Voynich sign units, null signs, and reset rules also remain unknown.
No new fit is justified by the historical example alone.

The following mathematical result is our inference from the state rule.
Let `r(c_i)` be a sign's position in a fixed cipher alphabet of size `m`.
Let `p_i` be the plaintext letter's position, with `a = 0`.
Let `s_i` be the current starting position.
For ordinary signs without a reset, the rule gives:

```text
r(c_i) = s_i + p_i                 (mod m)
s_(i+1) = r(c_i) + 1               (mod m)
p_i = r(c_i) - r(c_(i-1)) - 1      (mod m), after the first letter
```

This calculation excludes null signs and nomenclator codes.
The initial position cancels after the first ordinary letter.
Every sign sequence produces an index sequence under any fixed sign order.
This transform alone cannot select the correct order or demonstrate plaintext recovery.

## Verification and decision

The [source manifest](further-key-routes-2026-09-29.sources.json) records source URLs, SHA-256 hashes, and byte counts.
Downloaded sources remain outside the public repository.
The study used extracted text and rendered PDF pages for the relevant tables and limitations.
Separate AI tasks examined the reading proposals and the historical state rule.
These checks do not constitute external scholarly validation.
The project test suite passed all 85 tests.

The earlier stopped model branches remain stopped.
Further work needs evidence that connects fixed sign rules to external language or meaning constraints.
The [validation protocol](validation-protocol.md) keeps the acceptance conditions for a key or translation.
