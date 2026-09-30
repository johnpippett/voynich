# Sherwood: first example check

Date: 2026-09-30.

The first printed example is consistent with the author's reverse-reading claim if `cc` stays one unit during reversal.
This check establishes no validated manuscript key or translation.

## Source and result

The archived [botanical method page](https://web.archive.org/web/20190519191443/http://www.edithsherwood.com:80/voynich-botanical-plant-anagrams/) gives a folio 4r example before its alphabet table.
It prints `ccamus` and permits the `cc` unit to represent `c` or `ch`.
Reverse the five units, then apply each permitted value:

| Input units | Reversed units | Value of `cc` | Output |
| --- | --- | --- | --- |
| `cc a m u s` | `s u m a cc` | `c` | `sumac` |
| `cc a m u s` | `s u m a cc` | `ch` | `sumach` |

Both results agree with the printed claim. Ordinary character reversal gives `sumacc`.
This calculation interprets the example; it does not establish a general reversal procedure.
The proposed plant name helped determine the symbol value. Agreement therefore does not independently validate the plant identification or sign value.

The wider method selects plant names, rearranges letters, and permits alternative values and word divisions.
The examined page does not fix all choices for a new passage.
The separate [2014 method page](https://web.archive.org/web/20190521101312/http://www.edithsherwood.com:80/voynich-script-and-code/index.php) describes an unattempted disk proposal and warns that its modified alphabet is incomplete.
This review keeps those methods separate.

## Review limits

The selection rule chose the first worked example before source inspection. The expected answer was visible during inspection.
This was a check of a printed example, with no blind prediction or new manuscript reading.

The review examined Figure 1 and four sign images. The `u` image request failed with HTTP 502.
The complete HTML table structure remains available, but most sign images were not examined.
The source's printed input remains an assumption for the calculation. The image review did not independently verify that input.

Both live method URLs returned a hosting error page with HTTP 200. Archived copies supplied the method text.
Some image requests resolved to different archive dates. The source record preserves both requested and final URLs.
The review corrected an incomplete table extraction before publication and kept the faulty version as failure evidence.

## Reproduction

The [source record](sherwood-example-check-2026-09-30.sources.json) gives source hashes, access results, frozen inputs, and review records.
Compare the hashes before repeating the check. Use the printed input without manuscript transcription or spelling changes.
Run this Python calculation:

```python
units = ["cc", "a", "m", "u", "s"]
for value in ("c", "ch"):
    print("".join(value if unit == "cc" else unit
                  for unit in reversed(units)))
```

The expected lines are `sumac` and `sumach`, in that order.
A direct position check gives the same results. It reads input positions 5, 4, 3, 2, and 1.
No dictionary search, key change, corpus run, or stopped-study retry followed.
