# Hebrew key and generated readings

Date: 2026-09-29.
The examined method has a fixed consonant transliteration, but no verified continuous translation.
Its word-generation prompt contains the current decoded target before it asks for alternatives.
Matches from that process do not independently establish the key or its meanings.

## Fixed method

This review fixes `antenore/voynich-toolkit` at commit `cb137630762908517636b7f9ffb98bc5fe0dc05e`.
The [March 2026 paper](https://github.com/antenore/voynich-toolkit/blob/cb137630762908517636b7f9ffb98bc5fe0dc05e/paper/paper.pdf), Table 1, gives a map to Hebrew consonants.
The table covers 19 of 22 consonants.
The [fixed decoder](https://github.com/antenore/voynich-toolkit/blob/cb137630762908517636b7f9ffb98bc5fe0dc05e/src/voynich_toolkit/full_decode.py#L128-L244) gives the complete preprocessing order.

It groups `ch`, removes an initial `qo` or an initial `q` from longer strings, and groups pairs of `i`.
It reverses the processed word and applies the letter map.
At the first output position, it changes dalet to bet and he to samekh.
Unknown units give `?`.
Table 1 calls this removal a q-prefix rule; the code also removes the `o` in an initial `qo`.

The [fixed software check](../../reports/hebrew-key-check-v1/README.md) uses eleven artificial inputs, without manuscript data.
Every Hebrew ASCII output and unknown-unit count agrees with the expectation recorded before execution.
For example, `qoa` and `qa` give `y`, while `oa` gives `yw`.
These examples test preprocessing. They do not identify words or meanings.

## What the generator receives

The [word prompt](https://github.com/antenore/voynich-toolkit/blob/cb137630762908517636b7f9ffb98bc5fe0dc05e/src/voynich_toolkit/crib_attack.py#L1007-L1065) includes the target's current decoded form, position, consonant count, and nearby decoded context.
The [calling code](https://github.com/antenore/voynich-toolkit/blob/cb137630762908517636b7f9ffb98bc5fe0dc05e/src/voynich_toolkit/crib_attack.py#L1104-L1136) gets this form from the target's EVA word.
The prompt requests alternatives that fit the stated subject and permitted letters.
It does not include the target's raw EVA spelling.

Our artificial prompt test confirms this information flow.
Changing only the decoded target changes that value in the prompt.
Changing only the nearby context changes that context in the prompt.
All five fixed prompt checks passed.
We did not call the generator or reproduce the paper's match counts.

The code subsequently compares generated alternatives with the target EVA word.
The [page script](https://github.com/antenore/voynich-toolkit/blob/cb137630762908517636b7f9ffb98bc5fe0dc05e/scripts/decode_all_pages.py#L94-L169) can replace a fixed output with a candidate that has zero recorded distance.
It then requests a translation with a vocabulary list and a section hint.
This process selects text with knowledge of the target. It is not an independent prediction of known plaintext.

A separate whole-page generator receives target word lengths, positions, anchors, and section information.
That route also uses target information, but differs from the word prompt tested here.
We did not examine the encoder's complete variant rules or reproduce either generation route.

## Language evidence and decision

The paper's section 4.2 reports that the fixed output does not read as Hebrew.
Its section 4.6 reports a failed word-order comparison on its selected phrases.
These are author-reported results; we did not reproduce their numerical values.
The abstract also claims exact generated matches and coherent recipe content.
The inspected generation code cannot make those matches an independent test of meaning.

The source review covers paper pages 1–15 of 21 and the specified code paths.
It does not reject Hebrew or every possible variant of the method.
Keep the fixed transliteration separate from the generated readings.
A future reading test must use unchanged rules and continuous text, with external language assessment.
No manuscript key, letter value, or translation is established by this check.

## Verification

The [plan](../plans/hebrew-key-check-v1.md) fixes the inputs, expected outputs, failure checks, and scope before execution.
Two executions produced identical result files.
The checker rejected altered source and plan bytes without an output file.
It refused an existing output path without changing that file.
A separate AI source review confirmed all eleven literal outputs and the prompt expectations without executing the code.
The [clean replay](../../reports/hebrew-key-check-v1/clean-replay.json) used new source downloads in a separate directory and produced an identical result file.

The [source record](../../reports/hebrew-key-check-v1/sources.json) contains URLs, byte counts, and SHA-256 hashes.
Downloaded source bodies and local working records remain outside the public repository.
These software checks and AI reviews are not external scholarly validation.
