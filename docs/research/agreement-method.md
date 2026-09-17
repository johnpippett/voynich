# Transcription agreement method

`voynich.agreement.compare_transcriptions(left_records, right_records)` compares
two parsed IVTFF record lists. It supports transcription review beside the
structural analysis. It does not select an accurate transcription.

## Alignment

The function uses this key for each record:

```text
(record["folio"], numeric index from record["locus"])
```

For example, `f84r.13,@P0` and `f84r.13,+P0` align. The locator and `kind`
remain in the result, but they do not change the key. A duplicate key in either
input raises `ValueError` before comparison. This prevents a multi-transcriber
input from silently overwriting a record.

The method assumes the two files use a normalized common IVTFF locus convention.
It does not repair shifted line numbering. Unmatched loci can result from
different coverage or numbering. The result reports `kind` mismatch counts.

## Clean agreement denominator

The function counts all aligned records. It marks an aligned pair as eligible
only when both records pass these checks:

* `excluded_tokens` is zero.
* The raw text has no uncertainty marker, rare annotation, or non-basic token.
* The raw text has no `<->`, `<~>`, or interruption annotation.
* The accepted token list is not empty.

The result reports exclusion counts by reason and by side. The clean agreement
coverage uses the eligible aligned-pair count as its denominator. This avoids
treating uncertain, rare, interrupted, or empty token streams as clean evidence.

## Agreement measures

The result reports exact raw-text agreement and exact accepted-token-sequence
agreement. It also reports token edit distance for eligible pairs.

Token edit distance is Levenshtein distance over token sequences. It counts
insertions, deletions, and substitutions. It is not character edit distance,
string similarity, or a count of changed tokens.

Mismatch examples include both raw strings and token lists. The result stores
at most 20 examples and reports the total mismatch count separately. Examples
also include eligibility reasons and the token-sequence edit distance.

## `f84r` evidence

The result always contains `focus.folio = "f84r"`. `focus.rows` contains every
union row for that folio, including unmatched rows. Each side contains its
locus, kind, raw text, and accepted tokens. This connects the comparison to
the supplied `f84r` image without assigning meaning to any line.

## Interpretation limits

Agreement does not establish which transcription is correct. The files can
share source material or conventions, so agreement does not prove independence.
Disagreement can reflect a damaged glyph, a different reading, a different
line boundary, or a parser exclusion. Use the output to locate review targets,
not to infer transcription quality from one score.

## Example

```python
from voynich.agreement import compare_transcriptions

result = compare_transcriptions(zl_records, it_records)
print(result["counts"])
print(result["agreement"]["tokens"])
for row in result["focus"]["rows"]:
    print(row["locus_index"], row["left"], row["right"])
```

The function uses only the Python standard library. Keep the input source
hashes, parser settings, and record files with any saved comparison result.
