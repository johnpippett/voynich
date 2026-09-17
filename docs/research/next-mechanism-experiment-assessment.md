# Next mechanism experiment assessment

**Status:** conceptual proposal only. It reports no new VMS fit or measurement.

**Review date:** 2026-09-17.

VMS means Voynich Manuscript. The next branch should test local word memory with a finite-window edit kernel. Use controls for frequency, word length, and line position.

This branch tests a mechanism beyond a character substitution or a homophonic key. It cannot identify the historical writing process from one feature set. Different generators can produce the same surface statistics.

## What the current results show

The current character test uses raw and grouped EVA units. Order-three prediction has lower loss than its within-word unit-shuffle baseline. The shuffle occurs after unit segmentation. This shows sequence structure, not language or meaning. See [STAGE2.md](../../reports/STAGE2.md).

The word-context test gives a narrower result. The original-order bigram has lower loss than its shuffled-training control and higher loss than the unigram in all three runs. Its fixed vocabulary and smoothing rule did not improve on word frequencies.

The word-order controls report positive effects for initial gallows, initial length difference, and adjacent near words. Exact repetition does not pass the corrected threshold. These effects are exploratory. They can result from frequency, word length, line position, morphology, or transcription choices. See [FINDINGS.md](../../reports/FINDINGS.md).

Current groups were already inspected during the project. They are not blind evidence. A new split cannot make inspected data unseen. Future results on these sources remain exploratory.

## Competing explanations

These hypotheses overlap. Report likelihood gains. Do not claim that one metric recovers one historical mechanism.

**H1: positional or morphological structure.** Word parts follow positions or classes. Shared slots, affixes, or bursty topics can create similar words. Such effects can also improve edit-kernel prediction.

**H2: local copy and edit memory.** A writer or generator copies an earlier word or word part, then edits it. A specified finite-window model predicts extra likelihood from recent similar words. Distance and shuffle effects depend on that model's rules.

**H3: stateful transduction.** A hidden source stream passes through a stateful unit or cipher process. It can preserve local dependencies while changing visible units. A known-text transducer control is needed. A gain alone cannot distinguish H2 from H3.

Natural languages can produce H2-like effects through morphology and repeated topics. A positive result supports local memory only after baseline and natural-text controls pass. It does not prove copying, cipher use, or a writing-system design.

## One bounded comparison

For each target word, compute a smoothed distribution from a fixed finite window of earlier words. Give a candidate more weight when its character sequence is close to a word in that window. Fit all weights on training groups.

Compare it with a baseline that uses training frequency, word length, and line position. Keep vocabulary, unknown-word rule, tokenization, and group split fixed. Set the exact window, edit measure, smoothing, and parameter count before the run.

Use held-out log-likelihood delta as the main result:

`delta = baseline loss - edit-kernel loss`

Report one delta for each held-out physical group. Report the median, interval, coverage, and positive-group count. Do not pool tokens as independent observations.

Specify a within-line word shuffle before the run. Preserve the scored target multiset and state which positional constraints remain fixed. Word shuffling preserves the length multiset, but not necessarily the length at each position. Use group-preserving resampling.

Calibrate with two synthetic sources. One has finite-window copy-and-edit memory. One matches frequency, word length, and line position but has no word memory. Separate these sources before testing the VMS.

Run the comparison on pinned Celsus, LLCT, and Italian-Old controls. Their dates, genres, and authors differ. They test metric behavior, not VMS language. A VMS delta that matches ordinary text is not special evidence.

This design is small enough to review. It does not require a slot grammar, self-citation simulator, or Naibbe inversion in the first run.

## Interpretation

Use these rules:

- A positive VMS delta that disappears under the shuffle supports local word context. It does not identify copy, morphology, or transduction.
- A persistent gain beyond calibrated sampling fluctuation in memory-free data requires a leakage or confound check.
- A delta that appears in natural controls with similar size weakens a VMS-specific claim.
- A delta that changes across groups requires section, length, and transcription review.
- A negative delta rejects only this finite-window edit model and its fixed baseline.

If H1, H2, and H3 remain observationally equivalent, the result is non-identifying. Do not add more surface metrics only to force a choice. Use a new intervention, such as a fixed known-text transducer or a predeclared source-order perturbation.

## Primary sources and reuse limits

- Reddy and Knight, [“What We Know about the Voynich Manuscript”](https://aclanthology.org/W11-1511/), 2011, reports morphology-like signatures, weak word-order effects, and a grille generator control. It does not select a generator.
- Hauer and Kondrak, [“Decoding Anagrammed Texts…”](https://aclanthology.org/Q16-1006/), 2016, tests substitution and within-word transposition on known ciphers. Candidate VMS words do not form a decipherment.
- Smith and Ponzi, [“Glyph combinations across word breaks…”](https://doi.org/10.1080/01611194.2019.1596998), 2019, tests boundary dependencies. Their public [preprint](https://agnosticvoynich.files.wordpress.com/2019/06/glyph-combinations-across-word-breaks-in-the-voynich-manuscript-preprint.pdf) supplies the full method text.
- Timm and Schinner, [“A possible generating algorithm of the Voynich Manuscript”](https://doi.org/10.1080/01611194.2019.1596999), 2020, gives a copy-and-vary generator. Its [repository](https://github.com/TorstenTimm/SelfCitationTextgenerator) states MIT terms. Pin a commit and settings before reuse.
- Zattera, [“A New Transliteration Alphabet…”](https://ceur-ws.org/Vol-3313/paper10.pdf), 2022, proposes a slot structure. The paper states CC BY 4.0. Its [v4j repository](https://github.com/mzattera/v4j) states GPLv3. Slot units have no proven linguistic values.
- Matlach, Janečková, and Dostál, [“The Voynich manuscript: Symbol roles revisited”](https://doi.org/10.1371/journal.pone.0260948), 2022, reports autocorrelation and a proposed steganographic code. The authors note false-positive risk.
- Greshko, [“The Naibbe cipher…”](https://doi.org/10.1080/01611194.2025.2566408), 2025, supplies a reversible known-text control. Its [repository](https://github.com/greshko/naibbe-cipher) states modified MIT terms. Its tables use VMS-derived features, so direct VMS compatibility is circular.
- Parisel, [“Evidence of Layered Positional and Directional Constraints…”](https://arxiv.org/abs/2604.19762v2), 2026, tests slot and grille generators. The paper lists CC BY 4.0. Its [repository](https://github.com/labyrinthinesecurity/currier-signatures) has no identified root licence file.

All links were accessed on 2026-09-17. These sources support method design. They do not provide a settled VMS writing-system explanation.
