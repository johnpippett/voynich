# Fixed expansion lengths at word boundaries

Under the model below, the selected transcription words require expansion lengths divisible by three for all units represented in training.
For these units, the model excludes fixed one-digit and two-digit expansions when each selected word boundary returns to the same code phase.
It does not identify a cipher, language, or plaintext.

## Model

Each transcription unit emits a fixed digit string of unknown length.
The proposed letter code uses groups of three digits.
Each word has one fixed boundary contribution, also of unknown length.
The word and boundary together return to the same position within a three-digit group.
This position is the code phase.

The test permits separate rules for Currier A and B.
For each word, let `c[u]` count unit `u`, let `l[u]` be its expansion length, and let `b` be the boundary contribution.
The model requires:

```text
sum(c[u] * l[u]) + b = 0 modulo 3
```

Only the remainder after division by three matters.
Zero remainder allows lengths zero, three, six, and larger multiples of three.
It does not establish empty emissions, absolute code alignment, or one plaintext letter per unit.

This is a new restricted model test, not a replication of a published decoder.
[Matlach, Janečková, and Dostál (2022)](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0260948), Discussion, describe a possible three-digit code.
They also allow spaces that do not mark plaintext words. Their proposal does not require the boundary condition tested here.
This result therefore does not reject that proposal.

## Selection and calculation

The inputs are the pinned ZL and IT transcriptions in the [source manifest](../data/source_manifest.json).
The existing physical-group split assigns separate training, validation, and test groups.
Each source and Currier class supplies a separate calculation.
The primary representation joins `cth`, `ckh`, `cph`, `cfh`, `ch`, and `sh` with the existing longest-match rule.
Raw EVA gives the sensitivity calculation.
Neither representation establishes linguistic letters.

Only P-kind records with class A or B supply words.
The existing strict word-span extractor rejects uncertain readings, ambiguous spaces, and special notation that touches a word.
Each retained span has a literal period on both sides after layout whitespace is removed.
An uncertain word elsewhere on the line does not exclude that span.

Each training word supplies a row of unit counts modulo three, followed by one for `b`.
Identical rows supply one constraint. The column alphabet comes from training only.
Exact elimination over the three possible remainders gives the matrix rank and nullspace.
The nullspace contains every length-remainder assignment that satisfies the constraints.
Its dimension gives the number of free coordinates, not a probability of correctness.

If training leaves no free coordinate, the track stops.
The zero vector satisfies every further row, so further scoring would add no evidence.
Otherwise, all surviving assignments receive the validation constraints, then the test constraints.
Words with units absent from training supply no additional constraint.
No favorable assignment, language model, or new boundary rule is selected.

## Results

The column count includes the boundary contribution.

| Source | Class | Units | Training tokens | Unique training rows | Columns | Training rank | Final rank |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| ZL | A | Visual compounds | 3,962 | 1,118 | 27 | 26 | 27 |
| ZL | B | Visual compounds | 9,099 | 1,844 | 28 | 28 | 28 |
| IT | A | Visual compounds | 4,724 | 1,298 | 26 | 26 | 26 |
| IT | B | Visual compounds | 10,625 | 2,103 | 27 | 27 | 27 |
| ZL | A | Raw EVA | 3,962 | 1,056 | 23 | 22 | 23 |
| ZL | B | Raw EVA | 9,099 | 1,776 | 23 | 23 | 23 |
| IT | A | Raw EVA | 4,724 | 1,223 | 20 | 20 | 20 |
| IT | B | Raw EVA | 10,625 | 2,031 | 21 | 21 | 21 |

Six tracks have full rank from training alone. Their validation and test stages did not run.

ZL class A initially permits one free direction in both representations: `l[g] = 2*l[z]` modulo three.
Every other training-unit remainder and the boundary remainder are already zero.
Validation leaves that direction unchanged.
Three distinct test rows remove the remaining freedom.
Four test tokens contain `j/v` units absent from training and supply no constraints.
All eight final systems therefore have only the zero remainder vector on their training alphabets.

## Interpretation and limits

Under the stated assumptions, none of the represented training units can have a fixed expansion length that changes the code phase.
The result permits lengths zero, three, six, and all other multiples of three.
It does not prove that those expansions exist or carry information.
Units absent from training remain outside the conclusion.

The result does not apply to arbitrary spaces, variable padding, discarded partial groups, context-dependent expansions, or a different unit inventory.
It also depends on the transcription readings and boundary choices.
No image review has certified the selected words for this experiment.
The two sources describe the same physical manuscript; they are not independent physical evidence.

The corpus was previously examined. These calculations are exploratory.
No broad claim of a first discovery is made.

The plan stopped this branch after the specified constraints.
No digit values, new sign decomposition, or translation were fitted.

A separate [line-boundary experiment](LINE_TRIPLET_BOUNDARIES.md) removes the word-closure assumption.
It finds the same divisibility constraint under a fixed common-phase condition at format-selected text lines.

## Records

The [public certificates](triplet-boundary-certificates.json) contain the coefficient matrices, column order, and source locations.
They contain no word transcriptions or complete parsed text.
Each final certificate is square. A determinant that is nonzero modulo three proves full column rank.

A separate AI calculation reproduced all eight selections, matrix hashes, ranks, nullspaces, and 195 certificate references.
It used a separate selection loop and exact integer determinants. It reused the parser, span extractor, unit representation, and physical-group split.
The primary agent also verified the published determinants with exact rational arithmetic.
These checks verify the calculation. They are not independent transcriptions or external scholarly validation.

Local records remain in `results/triplet-residue-v1/`.
They include the fixed plan, executed script, exact source-row references, and the calculation result.

| Record | SHA-256 |
| --- | --- |
| Plan | `f772de9a741894e6f82a7fd6ed1a78bcc92804de8450ffbbf05f53d7d04b04fd` |
| Executed script | `b27f9f6ef414e26458007929c4ed774425649d1aeee5d87da88457d9d63a3f56` |
| Result | `2f9b44bf0eea855ad3d385d5e5d1e90cb1b3605f0e06b778706921dcdce5f066` |
| Verification script | `7b89e30ead832cb2aa5b86c8eccfa554657106dcf1837f5528e2a5eb1930c971` |
| Verification result | `7f54b6573ef8e703206efb94e62ed497b78cc658a6e9b7c16f9280768ea16afd` |
