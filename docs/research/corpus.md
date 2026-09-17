# Corpus method

This project uses two IVTFF files from the Voynich MS text analysis site. They use
shared IVTFF conventions, but they preserve separate readings:

- `data/raw/ZL3b-n.txt`: Zandbergen-Landini, version 3b.
- `data/raw/IT2a-n.txt`: Takeshi Takahashi data extracted from the Landini-Stolfi interlinear file, version 2a.

The source page is <https://www.voynich.nu/transcr.html>. The direct file URLs and
the retrieval records are in `data/source_manifest.json`. The manifest records the
UTC time, byte count, SHA256 digest, attribution, and use limits for each file.

The source page does not state an open licence for these files. Keep the attribution.
Check permission before redistribution. This project makes no translation claim.

The file format reference is <https://www.voynich.nu/software/ivtt/IVTFF_format.pdf>.
IVTFF means Intermediate Voynich Transliteration File Format. Each locus keeps its
source page, locus identifier, locator type, transcriber ID, and raw text.

## Parser

Use `voynich.corpus.parse_ivtff(path, uncertain_spaces="split")`.

The function returns one dictionary for each locus. Each dictionary has these keys:

- `folio`: the IVTFF page name, such as `f1r`.
- `locus`: the locus identifier without angle brackets.
- `kind`: the raw locus type, such as `P0`, `Lz`, or `Cc`.
- `transcriber`: the IVTFF locus ID, or the source ID for the downloaded ZL and IT files.
- `text_raw`: the logical locus text with IVTFF controls preserved.
- `tokens`: conservative basic EVA words in lower case.
- `metadata`: page variables such as `$I`, `$L`, and `$H`, plus active text tags.
- `excluded_tokens`: words excluded from `tokens`.
- `paragraph_start` and `paragraph_end`: paragraph marker flags.

IVTFF whitespace is layout. The parser ignores it. A period separates words.
The default `split` mode also splits at an uncertain comma. The `join` mode joins
the text on both sides of an uncertain comma for a sensitivity run.

The token stream accepts only `[a-z]+`. A brace ligature of basic EVA letters is
flattened. For example, `{cth}` becomes `cth`. The raw text keeps the braces.

The parser excludes a whole word when it contains an uncertain alternative, an
unreadable mark, a high-ASCII code, an apostrophe, or another rare construct. It
increments `excluded_tokens`. The raw text remains available for later review.

The parser validates inline comments, page variables, text tags, brackets,
ligatures, high-ASCII codes, and wrapped lines. It raises `ValueError` for
unexpected markup. It does not guess a damaged control sequence.

The controls `<->` and `<~>` mark text interrupted by a drawing. They become word
boundaries during token extraction. Downstream sequential analysis should filter
records whose `text_raw` contains either control when a line must be contiguous.

## Current counts

The current source files produce these counts with the default parser:

| source | loci | paragraph starts | paragraph ends | basic tokens | excluded words |
| --- | ---: | ---: | ---: | ---: | ---: |
| ZL | 5,385 | 740 | 740 | 37,889 | 1,137 |
| IT | 5,215 | 772 | 772 | 37,759 | 160 |

These counts describe the downloaded files. They do not prove that either
transliteration is correct. The two files use different readings and paragraph
boundaries. Keep them separate during comparison.
