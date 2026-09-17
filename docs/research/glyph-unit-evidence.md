# Glyph units and linguistic units

Research status: 2026-09-16. This note reviews primary sources on the unit
choices used for the Voynich Manuscript (VMS). It separates written shapes,
transcription units, and linguistic units.

The **Extensible Voynich Alphabet (EVA)** is a reversible transcription system.
It records shapes from manuscript images. It does not assign pronunciation or
meaning. A **visual unit** is a stroke group that a source treats as one shape
for a stated analysis. A **linguistic unit** is a letter, sound, morpheme, or
word in a language. The sources below support some visual and statistical unit
choices. They do not support a VMS linguistic reading.

## Findings

The current project list is:

```text
cth, ckh, cph, cfh, ch, sh, iin, in
```

The evidence divides this list into two groups.

| Project form | Evidence in the sources | Safe status |
| --- | --- | --- |
| `ch`, `sh` | EVA marks these connected groups. Currier gives them separate symbols. Smith and Ponzi include them in a common visual inventory. | Strong visual compound candidates. Do not call them letters or sounds. |
| `cth`, `ckh`, `cph`, `cfh` | EVA marks these connected gallows groups. Currier says their positional behavior supports separate statistical symbols. Smith and Ponzi include the four forms in their visual inventory. | Strong visual compound candidates. The statistical result does not prove an indivisible glyph or a linguistic value. |
| `in`, `iin` | Earlier Currier and FSG alphabets used single analysis symbols for these forms. EVA writes them as `i` plus `n`, or `i` plus `i` plus `n`. Currier and Cuva also use related `i` series. | Historical analysis units. Treat as provisional compounds in this project. Do not call them single EVA glyphs. |

No reviewed source provides a complete, validated mapping from every EVA code
to a linguistic unit. EVA explicitly leaves such grouping to later analysis.
The safest use of a compound is therefore a named transcription or analysis
choice with a reversible raw span.

## What EVA records

Gabriel Landini and René Zandbergen describe EVA as a shape alphabet. Its aim
is to represent the manuscript and to allow conversion from earlier
transcriptions. It is not a semantic alphabet. Their transliteration guide
also states that transliteration is symbol by symbol and makes no claim about
pronunciation ([“Transliteration of the Text,” sections “What is a transliteration?” and “EVA”](https://www.voynich.nu/transcr.html), accessed 2026-09-16).

The EVA reference font gives these construction examples:

| EVA form | Font or connectivity description | Interpretation limit |
| --- | --- | --- |
| `ch` | A connected `c`-curve and `h` form. | It records a written group. It does not say that `c` and `h` are letters. |
| `sh` | A connected `s`-like and `h` form in Basic EVA. | Some transcriptions use `Sh` to record a connectivity variant. |
| `cth`, `ckh`, `cph`, `cfh` | Connected or joined forms built around the gallows forms `t`, `k`, `p`, and `f`. | The joined shape is not proof of a ligature in the linguistic sense. |
| `q` and `qo` | `q` has a right connection in the EVA convention. | A connected `qo` may be one visual group, but the reviewed studies do not require that merge. |
| Capitals and braces | Capital letters and braces can record joins or special connectivity. | Formatting records a transcription decision. It is not a phonetic marker. |

The [EVA Alphabet Font Version 2 Reference](https://www.voynich.nu/hist/gabriel/eva2_reference.pdf),
pp. 1, 4, and 6 (copyright notice and update history: 1997–2004), gives the
font forms and the mappings used by older alphabets. The [EVA alphabet
reference](https://www.ic.unicamp.br/~stolfi/EXPORT/projects/voynich/work/programs/c/projects/voynich/alphabet-gabriel/eva.htm),
sections “Basic EVA” and “Extended EVA,” gives the same connectivity rules in
machine-readable HTML. These are transcription conventions, not a claim that
the manuscript writer used a Latin-like letter inventory.

EVA has a Basic and an Extended alphabet. The Basic set contains common forms.
The Extended set records rare forms, variants, embellishments, and ligature
forms. A rare code can therefore represent a rare shape, a variant, or a
source-format decision. It is not automatically a rare letter. A model must
retain the raw code and its source span when it cannot apply a named grouping.

## Direct mappings from the primary sources

The table below compares the main published alphabets. The older alphabet
columns show analysis labels. They do not give readings.

| EVA spelling or form | Currier or FSG label | Cuva analysis label | Published visual treatment | Project use |
| --- | --- | --- | --- | --- |
| `ch` | `S` | `S` | Connected Basic EVA group. | Keep as a visual compound candidate. |
| `sh` / `Sh` | `Z` | `Z` | Connected group, with capitalization used for a connectivity distinction in some files. | Keep as a visual compound candidate; preserve the raw case and span. |
| `cth` / `cTh` | `Q` | `TS` | Connected gallows group. Currier reports behavior unlike a simple `t` plus `ch`. | Keep as a visual compound candidate. Do not infer `/t/` or `/ch/`. |
| `ckh` / `cKh` | `X` | `KS` | Connected gallows group. | Keep as a visual compound candidate. Do not infer `/k/` or `/ch/`. |
| `cph` / `cPh` | `W` | `PS` | Connected gallows group. | Keep as a visual compound candidate. |
| `cfh` / `cFh` | `Y` | `FS` | Connected gallows group. | Keep as a visual compound candidate. |
| `in` | `N` in older Currier/FSG conventions | `N` | EVA writes the sequence as two Basic forms. | Keep only as a named historical analysis compound. |
| `iin` | `M` in older Currier/FSG conventions | `M` | EVA writes the sequence as three Basic forms. | Keep only as a named historical analysis compound. |
| `ii`, `iii`, `iiin` | Related `i`-series forms | `N`, `M`, `NN` in the cited Cuva rules | EVA does not define one general `i`-series glyph. | Do not merge in the baseline. |
| `ir`, `iir`, `iiir`; `il`, `iil`, `iiil`; `im`, `iim`, `iiim` | Related final series in Currier | Separate Cuva rules | Currier lists these as related word-final series. | Treat as sequences unless a separate experiment pre-registers another rule. |
| `ee`, `eee`, `eeee` | No EVA single-glyph claim | `U`, `UE`, `UU` in Cuva | Cuva maps these for analysis. | Do not treat these mappings as visual or phonetic facts. |
| `qo` | No required single label | No required merge in the cited rules | EVA records a right connection after `q`; a visual `qo` group is possible. | Keep `q` and `o` separate in the proposed test. |

The source for the Cuva column is the downloadable [EVA-to-Cuva bitranslation
file](https://voynich.nu/software/bitrans/Eva-Cuva.bit). Zandbergen describes
Cuva as an analysis alphabet. He does not present it as a better transliteration
or a semantic alphabet ([“Analysis of the text,” section “The Cuva alphabet”](https://www.voynich.nu/extra/sp_analysis.html),
accessed 2026-09-16). This makes the file useful as an exact, reproducible
comparison table. It does not make `TS`, `KS`, `PS`, `FS`, `N`, or `M` sounds.

The [same analysis page](https://www.voynich.nu/extra/sp_analysis.html)
explains why EVA can be unsuitable when an analysis needs one unit per visible
shape. It gives `ch` and several `i` series as examples of multi-character EVA
strings. It also warns that an analysis alphabet is not a true transliteration.
This is evidence for testing multiple encodings. It is not evidence for a
hidden alphabet.

## Evidence from glyph and position studies

Currier's 1976 paper is the earliest source in this review that makes a strong
statistical unit claim. He describes `cth`, `ckh`, `cph`, and `cfh` as part of
the same visual family as `ch`. He reports that the four groups behave almost,
but not exactly, like `ch` and `sh`. He concludes that the groups function as
symbols in their own right for his analysis. He does not assign them sounds or
meanings. The paper also lists the final series `n`, `in`, `iin`, `iiin`, and
parallel `l`, `r`, and `m` series ([Currier, “Papers on the Voynich Manuscript,”
1976 paper, sections on gallows and final series](https://www.voynich.nu/extra/curr_main.html),
HTML transcription accessed 2026-09-16).

This supports two limited conclusions. First, the six connected forms in the
current list have a documented visual and positional basis. Second, the
historical `in` and `iin` choices sit inside a larger family. They are not a
complete rule for all repeated `i` forms.

Smith and Ponzi define a glyph by its visible stroke group. Their definition
does not require a theory of script or language. In their Takahashi EVA corpus,
they select common analysable units with at least 50 occurrences:

```text
o y a e ch Sh k t f p cKh cTh cFh cPh d s r l i n m g q .
```

They report that `x` is the next common form at about 35 occurrences. They do
not merge `in` or `iin` in this inventory. They also note that `Sh` can have a
connected or separate top stroke. They leave `qo` unmerged for their word-break
test. These choices show that even a visual
analysis must state its corpus, frequency threshold, and connectivity policy.
They do not establish a universal glyph inventory ([Smith and Ponzi, “Glyph
Combinations across Word Breaks in the Voynich Manuscript,” 2018 preprint,
PDF pp. 1–3 and 13–16](https://agnosticvoynich.files.wordpress.com/2019/06/glyph-combinations-across-word-breaks-in-the-voynich-manuscript-preprint.pdf),
accessed 2026-09-16).

Smith and Ponzi measure combinations across apparent word gaps. Their results
show positional structure, but the authors keep the unit definition separate
from claims about words and sounds. This separation is useful for the project:
a unit can predict a boundary without being a phoneme, morpheme, or word.

Matlach, Janečková, and Dostal define a ligature as a graphic composition of
at least two immediately successive graphemes. They then test candidate
compositions with heuristic losses and incidence matrices. They state that
candidate decompositions such as `ckh` and other gallows forms are ambiguous.
The paper therefore supports a controlled model comparison. It does not
validate one decomposition ([“The Voynich manuscript: Symbol roles revisited,”
PLOS ONE 17(1), 2022, Background and Methods](https://doi.org/10.1371/journal.pone.0260948);
[open PDF](https://journals.plos.org/plosone/article/file?id=10.1371/journal.pone.0260948&type=printable),
accessed 2026-09-16).

Zandbergen's transliteration review gives the reason for this caution. Image
to text conversion loses layout, spacing, handwriting distinctions, and some
grouping information. Different researchers therefore use different character
sets and obtain different counts. A stable token in a file can be a useful
analysis object while still being uncertain as a physical glyph ([“Special
Topics: Transliteration of the text,” sections on the character set and
grouping](https://voynich.nu/extra/sp_transcr.html), accessed 2026-09-16).

## Abbreviation and phonetic evidence

Some sources compare VMS shapes with medieval Latin abbreviation signs. These
comparisons are visual analogies only.

Currier compares a VMS sign with the Latin abbreviation shape used for parts of
`con`, `cum`, or `-us`. Zandbergen's writing-system page shows related Latin
abbreviation examples and the visual families of the gallows forms. The same
page says the VMS forms are not typical abbreviations. Neither source gives a
validated VMS expansion or sound value ([“The Writing System,” sections on
Latin characters and abbreviations](https://www.voynich.nu/writing.html),
accessed 2026-09-16).

The positional evidence also does not establish phonetics. Currier's final
series and cross-word dependencies may reflect a writing convention, an
encoding process, or a language. His paper keeps alternatives such as words,
syllables, letters, and digits open. Smith and Ponzi test glyph sequences at
word gaps without assigning sounds. The EVA documentation explicitly avoids a
pronunciation claim. The reviewed primary sources therefore provide no safe
mapping such as `c` = /k/, `h` = /h/, or `in` = a syllable.

Do not use a proposed glyph split as a translation step. A phonetic or
linguistic claim needs a fixed reading method, a historical reason for the
target language, broad coverage, held-out tests, and independent replication.

## Comparison with the current project list

The current six visual compounds are a reasonable baseline. They match the
connected forms documented by EVA and the common visual inventory used by
Smith and Ponzi. Currier's positional result gives a separate statistical
reason to keep them available as units.

The current `in` and `iin` compounds need a different label. They match older
Currier and FSG analysis symbols, and they appear in the Cuva mapping. EVA
itself writes them as sequences. Smith and Ponzi keep `i` and `n` separate in
their visual inventory. The project should therefore report results for
`in` and `iin` as historical analysis compounds, not as established glyphs or
linguistic units.

The list is not complete under any reviewed source:

* Currier lists related `iiin`, `ir`, `iir`, `iiir`, `il`, `iil`, `iiil`, `im`,
  `iim`, and `iiim` series.
* Cuva includes additional `i` and `e` sequence rules for its own analysis.
* Smith and Ponzi include common single forms: `o`, `y`, `a`, `e`, `k`, `t`,
  `f`, `p`, and `d`. They also include `s`, `r`, `l`, `i`, `n`, `m`, `g`, and
  `q`.
* EVA Extended contains rare shapes and ligature forms. The rare forms cannot
  be safely discarded when a unitization claims full coverage.

These differences do not show that one source is wrong. They answer different
questions. EVA preserves a reversible transcription. Currier studies positional
symbols. Cuva supplies an analysis recoding. Smith and Ponzi study common
visible stroke groups. A result must name the question and the source format.

## One controlled next unitization

Run one reversible visual-unit experiment based on the Smith–Ponzi common
inventory. Keep the current raw EVA and current compound list as baselines.
Do not replace either baseline.

Use these fixed rules:

1. Read the existing Basic EVA stream and retain each raw source span.
2. Match the six connected visual forms first: `ch`, `sh` or `Sh`, `cth` or
   `cTh`, `ckh` or `cKh`, `cph` or `cPh`, and `cfh` or `cFh`.
3. Match the common single forms reported by Smith and Ponzi. Include `o`,
   `y`, `a`, `e`, `k`, `t`, `f`, `p`, and `d`. Also include `s`, `r`, `l`, `i`,
   `n`, `m`, `g`, and `q`.
4. Keep `in`, `iin`, `ii`, `iii`, `iiin`, `qo`, and all other sequences as
   successive units. Do not add a phonetic split or merge.
5. Keep `.`, word gaps, and metadata outside the glyph-unit stream. Keep every
   unmatched or rare EVA form as an opaque raw unit with its source span.
6. Store the raw spelling, canonical visual label, and character offsets. This
   makes the recoding reversible and makes rare-form coverage measurable.

This experiment has one clear question. Test prediction and generalization with
the documented common visual inventory. Use the same physical splits, word-gap
policy, and controls. Compare it with the raw EVA and current compound
baselines. Predeclare the metrics. Include held-out leaves or page groups.
Report coverage and all unmatched codes.

An improvement would show a useful representation for a stated task. It would
not show that the units are letters, sounds, or words. A failure would not show
that the VMS has no linguistic content.

## Source record

The following primary sources were read for the sections cited above. Access
dates are 2026-09-16.

| Source | Contribution used here | Main caveat |
| --- | --- | --- |
| [Landini and Zandbergen, “Transliteration of the Text”](https://www.voynich.nu/transcr.html) | Defines EVA as a reversible shape transcription and describes Basic and Extended EVA. | A web reference page, not a peer-reviewed glyph theory. |
| [Landini, “EVA Alphabet Font Version 2 Reference”](https://www.voynich.nu/hist/gabriel/eva2_reference.pdf) | Gives font examples, connectivity forms, and mappings to earlier alphabets. | A font and transcription reference. It does not define linguistic values. |
| [Landini and Zandbergen, EVA alphabet reference](https://www.ic.unicamp.br/~stolfi/EXPORT/projects/voynich/work/programs/c/projects/voynich/alphabet-gabriel/eva.htm) | Gives Basic/Extended EVA and bracket, capital, and connectivity rules. | The page documents an encoding convention. It is not a manuscript grammar. |
| [Zandbergen, “Analysis of the text”](https://www.voynich.nu/extra/sp_analysis.html) | Explains the Cuva analysis alphabet and the `i`-series problem. | Cuva is explicitly an analysis recoding, not a true transliteration. |
| [Zandbergen, “Transliteration of the text”](https://voynich.nu/extra/sp_transcr.html) | Separates image evidence from grouping and character-set decisions. | It describes limits; it does not resolve them. |
| [Currier, “Papers on the Voynich Manuscript”](https://www.voynich.nu/extra/curr_main.html) | Supplies the gallows and final-series statistical observations. | The paper reports no decipherment and uses a historical transcription. |
| [Smith and Ponzi, “Glyph Combinations across Word Breaks”](https://agnosticvoynich.files.wordpress.com/2019/06/glyph-combinations-across-word-breaks-in-the-voynich-manuscript-preprint.pdf) | Defines a visual glyph for a stated corpus and lists common analysable units. | The threshold and unit list are study choices; rare forms are excluded. |
| [Matlach, Janečková, and Dostal, “Symbol roles revisited”](https://doi.org/10.1371/journal.pone.0260948) | Formalizes candidate graphical compositions and tests heuristic losses. | Candidate decomposition remains ambiguous and model dependent. |
| [Zandbergen, “The Writing System”](https://www.voynich.nu/writing.html) | Records visual comparisons with Latin letters and abbreviations. | Visual analogy does not provide a VMS expansion or sound. |
| [Zandbergen, `Eva-Cuva.bit`](https://voynich.nu/software/bitrans/Eva-Cuva.bit) | Provides a downloadable, exact EVA-to-Cuva analysis mapping. | A recoding for analysis, not a verified glyph or phonetic inventory. |

The source record supports a representation experiment. It does not support a
translation, a language identification, or a claim that any EVA compound is a
linguistic letter.
