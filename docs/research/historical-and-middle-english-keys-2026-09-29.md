# Historical keys and Middle English reading choices

Date: 2026-09-29.
This source check found proposed sign tables, but no independently checked Voynich key or translation.
The check covers Vatne's reading method and access to Feely's and Strong's proposals.
No manuscript corpus, external decoder, or new sign assignments formed part of this work.

## Vatne's proposed key

Vatne's [Version 1 paper](https://sivbuggevatne.com/wp-content/uploads/2021/10/verson_1_75mb_2.pdf) gives tables of cipher labels and proposed readings on pages 22–23.
The page 23 table separates possible Latin letters from a selected transliteration.

For example, the label `d` has the possible readings `d/th`, but its selected transliteration is `d`.
A fixed transliteration is a useful method component. It does not select a meaning by itself.

EVA is the Extensible Voynich Alphabet. It records written shapes.
This check assumes no direct conversion from the author's labels to EVA.

Page 24 permits added vowels before or after consonants.
It gives position rules for two forms of proposed `r`, but does not specify every vowel choice.
Pages 25–27 keep alternate sound values. Pages 30–31 allow changes in spacing with reference to meaning.
The examined pages therefore leave choices between the selected transliteration and a continuous reading.
This finding does not show that historical spelling variation or ambiguous writing is impossible.

### The willow example

Page 30 proposes this reading for f55v: `oedain` → `oideun` → Middle English `withe`, meaning willow.
The [Middle English Dictionary entry MED53023](https://quod.lib.umich.edu/m/middle-english-dictionary/dictionary/MED53023) gives a willow sense for `with(e)`.
Its forms include the early plurals `wiðen` and `witthene`, which Vatne cites.
Vatne also prints `within`. The current entry header instead includes `withþene` and `withthin`; the quotation bodies were not checked.

This check supports the historical vocabulary reference. It does not check the manuscript reading, the drawing's plant identity, or their relation.

On page 32, Vatne says the sample translations do not validate the decoding.
Vatne proposes comparison of plant names with their illustrations. This check did not test that proposal.
The first check did not examine the later plant glossary. The follow-up below examines its selection method and the fixed f55v example.
A new test needs fixed reading choices and plant identifications made independently of the proposed decoded names.

### Scope

The first check covered pages 1–8. Two later tasks examined pages 15–24 and 25–32 after the contents page identified them.
These selections preceded the respective page extractions. The primary agent checked images of pages 23, 24, 25, 30, and 32.
Printed and PDF page numbers agree in these ranges. No claim about all 323 pages follows from this check.

The later check added pages 60–67 and 276–277. It did not reproduce all 104 reported plant-name readings.

The fixed dictionary target was `with(e)`. The earlier `wilwe` lookup was for navigation only.
A third web query corrected a domain-filter error after an initial two-query limit. The saved record keeps this scope change.

A later site search exposed 15 result cards. The check selected the exact `with(e)` entry.
Direct retrieval failed, but a hidden browser displayed the dictionary after automatic security verification.
The local record contains observations from that page, not original server bytes.

### Plant-comparison method

Page 61 explains how the plant glossary selects candidates.
A candidate plant name enters the table when the author sees a matching feature in the manuscript drawing.
The author omits other plants with the same vernacular name if they lack visual similarity.
Another column then rates the illustration match.
Thus, visual fit affects both selection and the stated support for a candidate.
This procedure does not keep the illustration evidence separate from candidate selection.

The first examples also use both directions of inference.
The f1v discussion starts from a proposed text reading, then selects a plant through described features (pages 62–63).
The f2v discussion starts from the illustration, then gives alternative proposed readings (pages 66–67).
Pages 60–67 give no complete candidate count or failed-match count.
These observations do not reproduce or disprove the reported total of 104 names.

### The selected f55v comparison

Pages 276–277 propose basket willow, *Salix viminalis*. The table selects paragraph 1, line 1, word 2.
Page 277 describes the resemblance as weak and records differences in color, flower/petals, and pedicel.
It records similarities in the stem and leaves.
The page also lists `withþene` and `withthin`, which agree with the dictionary header checked above.
The `within` spelling on page 30 therefore does not describe every form that the paper gives.

The primary agent examined the [Yale f55v image](https://collections.library.yale.edu/iiif/2/1006183/full/full/0/default.jpg) with the proposed name already known.
A separate AI task received the same image without the candidate name or decoded text.
The image has a central stem, a broad green region, small terminal structures, and branching forms below.
The individual leaf arrangement and diagnostic reproductive structures stay uncertain in this check.
These observations give no independently checked plant identification. They do not disprove the willow proposal.

The source check now shows how visual fit enters the glossary selection.
A test of the key still needs fixed reading rules and plant identifications made without the proposed decoded names.
It also needs the complete candidate set and failures, with a comparison rule fixed before evaluation.

## Feely source access

D’Imperio's [study](https://www.govinfo.gov/content/pkg/GOVPUB-D-PURL-gpo58694/pdf/GOVPUB-D-PURL-gpo58694.pdf#page=105) reproduces Feely's proposed alphabet in Figure 25.
The figure is on printed page 103, PDF page 105. Its caption cites Feely 1943, pages 11 and 34–35.
This is D’Imperio's adapted reproduction. The selected catalogue routes supplied no pages from Feely's original book.

Three later Internet Archive queries found no target record. One author query returned an unrelated Feely title.
These catalogue results do not show that no copy exists.

The figure gives proposed readings of f78r labels above a table of drawn signs and Latin-letter values.
The table includes single letters and groups, such as `ND`, `DER`, `PER`, and `UND`.
Some entries give alternatives, such as `ER,RE,E` and `EM,ME`.
The figure alone gives no general rule for these choices or abbreviation expansion.
The check made no new sign assignments and no conversion to EVA.
A future fixed reading test needs Feely's original explanation and a checked relation between the drawn signs and the test transcription.

The first eight-page examination reached the prose account, but not the figure.
A later page 56 check and four repeated prose-page checks also failed to locate it.
Machine caption recognition then found Figure 25 on page 105. A separate one-page selection preceded its image examination.
The saved records keep those unsuccessful selections. Printed-to-PDF page offsets differ across this scan.

## Strong source access

The [PubMed record](https://pubmed.ncbi.nlm.nih.gov/17740745/) identifies Strong's 1945 article in *Science*, volume 101, pages 608–609.
The [publisher PDF](https://doi.org/10.1126/science.101.2633.608) request returned HTTP 403.
The supplied letter-bundle link returned HTTP 404, and one archive-index request timed out.
No primary PDF page was read. These failures give no conclusion about the contents or completeness of Strong's key.

Two discovery queries exposed 28 result cards, above the initial five-record limit.
The worker recorded this failure and issued no further discovery queries.
The [NSA correspondence index](https://www.nsa.gov/Helpful-Links/NSA-FOIA/Declassification-Transparency-Initiatives/Historical-Releases/Friedman-Documents/Correspondence/) names a Friedman letter to Hagelin about the Voynich manuscript.
Its entry does not identify Strong as the author. The linked PDF was not opened.

## Verification and next requirements

The [source manifest](historical-and-middle-english-keys-2026-09-29.sources.json) records source hashes, page selections, and access limits.
Download the stated PDFs and compare their SHA-256 hashes. Examine the cited pages and the dictionary entry.
Page selections and discovery limits controlled source-check resources. They were not preregistered tests of manuscript meaning.

Separate AI tasks examined the method pages and historical source access. The primary agent checked the cited source images and dictionary entry.
These are project source checks, not external scholarly validation.
The required project suite passed all 85 tests. This software result does not validate a translation.

A proposed key must meet the [validation protocol](validation-protocol.md) before the project reports a translation.
The stopped model branches stay stopped. This source check gives no reason to add parameters to them.

Source bodies and detailed access records stay in ignored result directories.
