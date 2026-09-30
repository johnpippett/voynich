# Strong worksheet example check

Date: 2026-09-29.
The visible lower digits agree with a previously reported 12-step cycle.
A proposed forward letter shift includes five letters from the worksheet, but gives 30 possible outputs.
This check does not give a unique reading, Strong's complete method, or a validated key.

## Source and scope

The source is the [99-page scanned collection](https://web.archive.org/web/20061215213410id_/http://internet.cybermesa.com:80/~galethog/Voynich/Strong.pdf).
The [archive report](strong-archived-source-check-2026-09-29.md) records its identity and limits.
This check uses the first row of PDF page 75 and the first main line of page 82.
The [calculation record](strong-worksheet-example-check-2026-09-29.json) gives the source hash, inputs, assumptions, failure modes, and results.

The proposed text was visible before the model was selected.
The arithmetic rules were recorded before the calculations, but they are not an independent prediction.
No new manuscript passage or EVA transcription was processed.

## Visible numbers

Two AI readers agreed on 32 clear lower digits across 38 positions.
Six triangular marks remain unresolved. Their positions are kept as `?`:

```text
13579 / 7531 / ?7?1357 / 97531? / 7? / 13579 / 753 / 1?7?13
```

An unclear initial mark is excluded. It has not been assigned zero or another value.
The final group may continue beyond the visible boundary.
The first proposed word has six letters, but only five clear lower digits.

All 32 known digits agree with the repeating sequence `135797531474`, starting at its first digit.
No value was supplied for the six unresolved marks.
The comparison advances one step per recorded position, across group boundaries.
It adds no steps for spaces and does not test spacing rules.

Among periods from 1 through 38, the known positions agree with lengths 12, 24, 36, and 38.
Length 12 is the shortest compatible period in this fragment.
Length 38 has no comparison between positions in different cycles. These results do not show a cycle for the manuscript.

The clear digit 9 excludes a direct lower-digit index into the eight rows on page 75.
This result does not exclude an additional operation or a different table.

## Direct table lookup

The primary reader read the first group's upper marks as six instances of 1.
A separate reader could not confirm their grouping. Thus, the row assignment remains an assumption.

With that assumption, the second sign does not give the second proposed letter through direct lookup.
Page 82 shows a bench form with a caret above it. Page 75 places those components under G in row 1.
The proposed second letter is H. Row 1 under H shows an open curve.
This difference rejects only that direct lookup using those page and row choices.

## Proposed letter shift

The following model is an inference from the example. It is not an instruction found in Strong's notes.
The model uses the 23 visible column headings in this order:

```text
ABCDEFGHIKLMNOPQRSTUVWX
```

The model first selects candidate columns from broad visual classes in row 1.
It then adds or subtracts the lower digit from each column position, with wraparound after 23 positions.
Similar loop forms have different edges and proportions. Their grouping does not show that they represent the same sign.

The check includes only positions 2–6 of the first word.
Readers differed between U and V at position 5, so both readings remain in the comparison.
The first position is excluded because its lower mark is unclear.

| Position | Candidate columns | Lower digit | Proposed letter | Forward outputs | Backward outputs |
| --- | --- | --- | --- | --- | --- |
| 2 | G | 1 | H | H | F |
| 3 | H, S | 3 | V | L, V | E, P |
| 4 | A, F, M | 5 | R | F, L, R | T, A, G |
| 5 | D, K, L, O, V | 7 | U or V | L, R, S, V, E | U, C, D, G, O |
| 6 | W | 9 | H | H | N |

The forward operation includes a proposed letter at each position. At position 5, it includes V but not U.
Its candidate sets give 30 possible five-letter outputs. No output was selected for its meaning.
The backward operation also gives 30 possible outputs, but fails the proposed-letter comparison at four positions.
Thus, forward arithmetic explains part of the example under the stated assumptions, without determining a unique result.

The table choice, visual classes, row assignment, alphabet order, and number alignment remain assumptions.
The known proposed letters could have influenced those choices.
This result has no independent validation or statistical significance claim.

## Earlier discussions

The number cycle was already known from published discussion before this check.
[Nick Pelling's 2004 message](https://voynich.net/Arch/2004/08/msg00279.html) interprets it as a schedule of six alphabet labels.
That message leaves the advance at spaces or half-spaces unresolved.
It does not specify this column-shift model or explain the upper row marks.

The [2010 Strong's Cipher post](https://voynichattacks.wordpress.com/2010/02/26/strongs-cipher/) instead tests assumed settings with ten alphabets and a 17-position schedule.
Those settings do not reproduce the eight-row worksheet table.
Neither examined discussion supplies the complete rules needed to connect this table to a continuous reading.
The search was limited to two queries and three candidate pages.

## Verification

1. Download the PDF from the source URL in the calculation record.
2. Compare its byte count and SHA-256 hash with that record.
3. Render PDF pages 75 and 82, then examine the selected row and line.
4. Keep unresolved marks and alternative readings in their recorded positions.
5. Run the command below from the repository root.
6. Compare the output with the `expected` object in the calculation record.

```sh
python scripts/check_strong_worksheet.py docs/research/strong-worksheet-example-check-2026-09-29.json
```

The script checks the recorded arithmetic. It does not check visual sign identity or decode manuscript text.
Separate AI tasks read the table, transcribed the example, and calculated the fixed inputs.
The primary agent examined the images and checked the arithmetic with a separate calculation.
Detailed source images, earlier crop selections, and review records remain in the ignored result directory.

The public command passed in an empty temporary directory with only the script and calculation record.
Its counts, candidate sets, and letter comparisons agreed with the separate calculation.
The required project suite passed all 85 tests. These software checks do not validate a translation.

The table review initially described G as a caret alone. A larger crop showed the bench below it, and the record was corrected.
The worksheet result does not change the project's validation requirements.
Any next check must fix the visual classes and arithmetic before examining another proposed output.
