# Fixed Hebrew decoder and prompt check

Date: 2026-09-29.
This check uses artificial strings. It does not read manuscript data or call a language model.
The question is whether the published fixed decoder has reproducible rules and whether its word prompt contains the current decoded target.

## Fixed sources

Use full_decode.py with SHA-256 c20f552a83ca8b6b619a182bedd43bafbc982cdc627bbbba9152c24552fbe3d6.
Use crib_attack.py with SHA-256 d3b3453689178064d91a49f06f102ac76c331c81f2293e8ff7e8884542de2d15.
Keep the source files unchanged in the local source archive.
Do not import either complete module.
Extract only the two decoder functions, their literal constants, the word-prompt function, and its literal section tables.
Use an empty Italian-output table. Compare only Hebrew ASCII output and unknown-unit counts.
Do not use the legacy decoder branch.

## Expected outputs, fixed before execution

| Artificial input | Hebrew ASCII output | Unknown units |
| --- | --- | ---: |
| qoa | y | 0 |
| qa | y | 0 |
| oa | yw | 0 |
| an | by | 0 |
| ar | sy | 0 |
| aii | sy | 0 |
| aiii | rhy | 0 |
| ach | ky | 0 |
| az | ?y | 1 |
| q | ? | 1 |
| qo | empty | 0 |

The prompt fixture has position 7, input an, decoded value by, length 2, and context context-alpha.
Use section herbal and request two candidates.
The prompt must contain its current decoded value, position, length, and context.
Changing only by to sy must change only that string in the prompt.
Changing only context-alpha to context-beta must change only that string in the prompt.
This tests information supplied to the generator. It does not reproduce generation or the claimed match count.

## Failure modes and checks

- A changed source or plan must stop the check before code extraction.
- Missing or duplicate selected definitions must stop the check.
- Nonliteral configuration must stop the check.
- An existing output file must remain unchanged.
- An unexpected decoder value must be recorded as a failure, without a new mapping or fixture.
- Two executions must give identical result files.
- An altered source must fail without an output file.
- A separate literal review must compare the specified values before the primary result is used.

A successful check establishes deterministic software behavior and target information in the prompt.
It does not establish Hebrew meaning, a correct key, or an independent plaintext prediction.
