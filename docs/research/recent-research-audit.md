# Recent Voynich research audit: 2025–2026

Research status: 2026-09-17

This bounded audit covers five recent records absent from
[`docs/research/literature.md`](literature.md). The search used author records,
full accessible arXiv preprints, Zenodo records, and linked code or data. It
used the terms “Voynich manuscript”, “decipherment”, “directionality”,
“encoding”, “generator”, and “Currier”. These records do not establish journal peer review. The existing note covers Greshko's
2025 Naibbe paper and the Timm 2026 hand critique.

EVA is a transliteration system. It is not a decoded alphabet. “Plaintext
coverage” means a fixed mapping to readable source text. A generator that
matches statistics has no plaintext coverage.

## Works reviewed

### 1. Parisel, “Directionality of the Voynich Script”

**Record.** [arXiv:2509.10573v4](https://arxiv.org/abs/2509.10573v4), version
dated 2025-09-24; first record dated 2025-09-11. DOI:
[10.48550/arXiv.2509.10573](https://doi.org/10.48550/arXiv.2509.10573).

**Method and result.** The paper compares left-to-right and right-to-left
n-gram cross-entropy and perplexity on RF1b-e, with English, French, Hebrew,
and Arabic controls. Laplace and Kneser–Ney smoothing, paired bootstrap
intervals, and within-reset-sequence shuffles are reported. The reversed
stream receives lower perplexity in the reported 2-, 3-, and 4-gram setup.

**Limits and plaintext.** The paper maps no token to plaintext, recovers no
key, and makes no decipherment claim. The RTL class was selected from the
observed result, and no physical-leaf holdout tests that choice. The controls
have mixed higher-order results, and the retrieved notebook uses word resets
that differ from the paper's description. [Versioned full
HTML](https://arxiv.org/html/2509.10573v4) and the linked [Kaggle
notebook](https://www.kaggle.com/code/labyrinthinesecurity/voynich-script-directionality/)
are the primary method records.

### 2. Parisel, “Evidence of Layered Positional and Directional Constraints”

**Record.** [arXiv:2604.19762v2](https://arxiv.org/abs/2604.19762v2), arXiv
version dated 2026-06-16. The HTML body displays 2026-08-24 as a manuscript
date. DOI: [10.48550/arXiv.2604.19762](https://doi.org/10.48550/arXiv.2604.19762).

**Method and result.** The paper measures four boundary and direction
signatures on 37,016 RF1b-e words and four comparison corpora. A word-level
Markov generator reproduces the opposite character and boundary directions.
The author then tests slot and Cardan-grille generators. No tested
configuration reaches all four signatures for either Currier dialect.

**Limits and plaintext.** The work maps no token to plaintext, recovers no
key, and makes no decipherment claim. The Markov result warns that directional
dissociation can follow from surface word statistics. The profile comparison
uses one EVA transcription, uncertain word boundaries, and calibration rather
than held-out plaintext prediction. See the [versioned full
HTML](https://arxiv.org/html/2604.19762v2) and [currier-signatures
repository](https://github.com/labyrinthinesecurity/currier-signatures).

### 3. Parisel, “A Quantitative Confirmation of the Currier Language Distinction”

**Record.** [arXiv:2604.25979v2](https://arxiv.org/abs/2604.25979v2), version
dated 2026-05-05. DOI:
[10.48550/arXiv.2604.25979](https://doi.org/10.48550/arXiv.2604.25979).

**Method and result.** After removing markup and uncertain readings, the paper
uses 36,500 EVA word tokens across 200 folios. The initial mixture uses 185 folios.
A Beta–Binomial mixture predicts
held-out folio labels at 89.2% accuracy without Currier labels. The later
switch analysis assigns 195 of 197 folios, and the paper reports a 31-template
inventory and a `d/l` gradient.

**Limits and plaintext.** The work classifies folio structure. It does not
decode a word, identify a language, recover a key, or claim decipherment. The
89.2% result predicts corpus labels, not unseen plaintext. The analysis depends
on EVA, Currier section labels for comparison, and approximate independence.
It requests replication with other transcriptions. See the
[versioned full HTML](https://arxiv.org/html/2604.25979v2) and
[currier-models repository](https://github.com/labyrinthinesecurity/currier-models).

### 4. Averyanov, “A Workshop Cipher”

**Record.** Zenodo [version `v1` API record](https://zenodo.org/api/records/21761192),
published 2026-08-02, DOI
[10.5281/zenodo.21761192](https://doi.org/10.5281/zenodo.21761192), licence
`CC-BY-NC-ND-4.0`.

**Method and result.** The paper builds a six-table Naibbe-class generator with
serial reuse, graphotactic choice, spelling noise, and section table dialects.
It fits static and dynamic statistics, checks IT2a, and compares competing
generators on six pre-registered held-out windows. The author presents a
mechanism-identification claim; this audit uses the narrower term forward-model
feasibility.

**Limits and plaintext.** The paper explicitly presents a mechanism, not a
decipherment. It recovers no table key and reads no Voynich word. The result is
model compatibility, not plaintext prediction. The model uses stand-in tables,
one research group, and no independent implementation identified in the
reviewed sources. Primary records are the [paper PDF](https://zenodo.org/api/records/21761192/files/paper1_arxiv.pdf/content),
[replication ZIP](https://zenodo.org/api/records/21761192/files/voynich_replication_v1.zip/content),
and [data and code page](https://voynich.site/data-and-code?lang=en).

### 5. Averyanov, “Thirty Names per Sign”

**Record.** Zenodo [version `v1` API record](https://zenodo.org/api/records/21761983),
published 2026-08-02, DOI
[10.5281/zenodo.21761983](https://doi.org/10.5281/zenodo.21761983), licence
`CC-BY-4.0`.

**Method and result.** The paper tests zodiac labels as a bounded register with
profile, positional, multiplicity, and period controls against degree-name
lists. It reports rejection of seven source classes. A 1524 Lleida sanctoral
passes raw positional tests but fails the period control because its signal
comes from later additions. The period control is the strongest safeguard.

**Limits and plaintext.** It reads no label, identifies no source list,
recovers no key, and makes no decipherment claim. “Decipherable in principle”
is a capacity claim, not plaintext coverage. The transcriptions derive from
the same images, and the degree order is inherited. A later local half-ring
signal is not extended to a manuscript-wide reading. Primary records are the
[paper PDF](https://zenodo.org/api/records/21761983/files/paper2_arxiv.pdf/content),
[replication ZIP](https://zenodo.org/api/records/21761983/files/voynich_replication_v1.zip/content),
[full paper page](https://voynich.site/paper-2-labels?lang=en), and [data and
code page](https://voynich.site/data-and-code?lang=en).

The separate [directionality audit](directionality-method-audit.md) checks the estimator.
The [medical source audit](antidotarium-source-audit.md) checks one released reference corpus.

## Cross-work assessment and next test

These works add directional, boundary, folio-state, forward-generation, and
label-falsification constraints. None supplies a fixed plaintext mapping. The
common weakness is transcription dependence: the works use EVA-derived text or
label sets. ZL3b and IT2a derive from the same physical manuscript.

Run one fixed held-out comparison. Keep body text, labels, circular writing,
radial writing, and external annotations in separate strata. Use ZL3b and IT2a
with physical-leaf or folded-leaf groups held out. Freeze each model's table
family, parameter ranges, corpus, and seeds before fitting. Compare Parisel's
signatures and folio diagnostics with Averyanov's generator, self-citation,
compression, Cardan-grille, matched nulls, and planted known-language ciphers.
Choose parameters on training groups, use a separate validation set, and test
once on held-out groups. Report failures. A structural result is not a
decipherment until a fixed key maps unseen groups to stable plaintext and an
independent implementer reproduces it.

## Search limits

This audit covers five records in the stated 2025–2026 scope. It is not an
exhaustive search of every repository or language. Paid journal pages were not
used as evidence. No code or model was run during this audit.
