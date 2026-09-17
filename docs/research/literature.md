# Voynich manuscript literature

Research status: 2026-09-16. This review uses the Yale Beinecke MS 408 record,
primary measurements, peer-reviewed studies, and accessible research papers.
The source index is in [`sources.json`](sources.json).

This file uses **VMS** as a short form for the Voynich Manuscript.

**Voynichese** names the transcription string. **EVA** names one transcription
alphabet. Neither term means that the signs are letters. **Currier A/B** names
statistical page classes. These classes are not proven languages. A **hand** is
a proposed writing style. A hand is not proof of a separate author, language,
or cipher.

## What the object record supports

The Yale collection describes MS 408 as a codex in an unidentified script by an
unknown author. The drawings support broad section labels: plants, astronomical
or astrological diagrams, bathing or biological scenes, pharmaceutical items,
and paragraphs marked with stars. The labels describe the pictures. They do not
translate the text. Yale provides high-resolution page images and a physical
description ([S01](https://beinecke.library.yale.edu/beinecke/collections/beinecke-cipher-voynich-manuscript)).

Four solvent-treated parchment samples gave a combined radiocarbon age of
516 +/- 18 years BP (before 1950). Calibration gave 1404-1438 CE at 95.4% probability and
1411-1430 CE at 68.2% probability. One untreated sample from leaf 68 was
younger and showed contamination consistent with later carbon. The result dates
the sampled parchment. It does not date the writing, ink, pigments, or a source
text ([S02](https://voynich.nu/papers/Carbon_GH_2009.pdf)). A conservation report found materials compatible
with medieval production, but it did not identify an author or a reading
([S03](https://cool.culturalheritage.org/coolaic/sg/bpg/annual/v31/bpga31-ebook.pdf)).

The first confirmed owner was Rudolf II. Later evidence links the codex to
Jacobus de Tepenec, Georgius Barschius, Athanasius Kircher, Marci, Voynich,
Kraus, and Yale. The Roger Bacon and John Dee stories remain hypotheses. The
early provenance before Rudolf II is incomplete ([S01](https://beinecke.library.yale.edu/beinecke/collections/beinecke-cipher-voynich-manuscript)).

Digital paleography by Davis proposes five hands. Yale's 2025 summary repeats
the five-collaborator description ([S05](https://doi.org/10.1353/mns.2020.0011), [S04](https://news.yale.edu/2025/02/21/deciphering-mysterious-manuscript)).
This result is useful as a label for controlled tests. It is not settled fact.
The 2026 Timm preprint argues that the sample and diagnostic features can be
explained by continuous variation in one hand. That preprint is a challenge to
test, not a replacement consensus (see the non-core watch items below).

Currier A/B classes and the proposed hands overlap strongly. This creates a
confound: a model can learn page class, handwriting, label format, or section
layout instead of language. Every future comparison should report body text and
labels separately, and should condition on the proposed hand or remove it in a
control.

## What the statistics show

No result below decodes a word. Each result concerns a feature of a chosen
transcription and a chosen unit of analysis.

### Signals that resemble organized text

* Reddy and Knight analyzed a Currier transcription with about 37,900 tokens.
  Word frequencies follow a Zipf-like curve. Word lengths, word entropy, and
  some affix-like patterns fall in ranges seen in known texts. Page neighbors
  are more similar than scrambled pages, and pages preserve weak topic
  structure. Their hidden Markov model separates Currier A and B. These results
  support non-random organization. They do not identify a language or prove
  semantics ([S06](https://aclanthology.org/W11-1511/)).
* Montemurro and Zanette found long-range word co-occurrence structure. Their
  word networks differ between illustration sections, and their selected words
  cluster by section. Their controls did not include modern text generators or
  all plausible cipher families. Section clustering can arise from a topic,
  hand, repeated formula, or encoding rule. It is not a translation
  ([S07](https://doi.org/10.1371/journal.pone.0066344)).
* Amancio and colleagues compared word properties, network topology, and
  intermittency across texts in 15 languages. Most measures separate the
  manuscript from a shuffled control. They also report unusual repeated
  bigrams and high intermittency. Their classifier misranks some known texts,
  and the authors state that the dataset cannot predict the language. The result
  supports document structure, not a language identity ([S08](https://doi.org/10.1371/journal.pone.0067310)).
* Sterneck, Polish, and Bowern applied latent Dirichlet allocation (LDA), latent
  semantic analysis (LSA), and nonnegative matrix factorization (NMF) to pages
  and short chunks. Clusters track a conjunction of illustration section, Currier class,
  and Davis hand. This is a useful document-level replication target. Topic
  models are sensitive to tokenization, page length, model choice, and labels
  supplied from the same object. A cluster can track production conditions
  without tracking meaning ([S14](https://arxiv.org/abs/2107.02858)).

### Signals that remain unusual

* Voynichese has strong positional restrictions inside word-sized units. Many
  signs or sign groups prefer the beginning, middle, or end. Reddy and Knight
  find weak word-order information and unusually few repeated word bigrams.
  Word-level regularity therefore coexists with weak local syntax.
* Lindemann and Bowern compare three transcription forms with 311 Wikipedia
  language samples and 18 historical texts in eight languages. Conditional
  character entropy remains unusually low after tested changes to glyph
  composition, abbreviations, and transcription. The result is compatible with
  conflated distinctions, a positional writing convention, or a generator. It
  does not select a hidden language ([S13](https://arxiv.org/abs/2010.14697)).
* Gaskell and Bowern had 42 volunteers write short texts with no intended
  meaning. Human gibberish reproduced several natural-language metrics and was
  often closer to VMS transcriptions than meaningful comparison texts in their
  classifier. The samples were too short to test page-level organization. This
  is a stronger null than random characters, but it is not a proposed historical
  generator ([S12](https://ceur-ws.org/Vol-3313/paper4.pdf)).

The useful combined statement is narrow: the transcription has stable,
multi-level structure, and some of that structure resembles text. The same
statement is compatible with an encoded language, a formulaic or nonsemantic
system, a careful hoax, or a mixture of these. A Zipf curve, topic cluster, or
low entropy value cannot decide between them.

## Cipher and generation alternatives

Constructive alternatives show that selected VMS
statistics do not require a natural-language plaintext.

* Rugg's Cardan-grille construction uses a table of fragments and a movable
  grille. It can produce VMS-like words and could encode a plaintext. The
  reported production time is a feasibility estimate. The method does not show
  that MS 408 used it ([S09](https://doi.org/10.1080/0161-110491892755)).
* Rugg and Taylor show that the same table-and-grille family can reproduce a
  Zipf-like frequency curve, a narrow word-length distribution, and uneven
  word and syllable distributions. This is replication of target statistics.
  It is not a historical attribution ([S10](https://doi.org/10.1080/01611194.2016.1206753)).
* Timm and Schinner propose a self-citation process. A writer copies and
  modifies nearby forms while continuing the sequence. Their network generator
  reproduces selected word similarity and frequency behavior, including both
  Zipf laws. It does not explain every page feature, establish authorship, or
  decode the manuscript ([S11](https://doi.org/10.1080/01611194.2019.1596999)).
* Gaskell and Bowern provide a human-writing null. A person can create
  meaningless text with several language-like statistics without a table,
  cipher, or trained model. The experiment does not reproduce a full codex.
* Greshko's Naibbe cipher is a recent reversible feasibility test.
  It uses variable-length homophonic tables for plaintext unigrams and bigrams.
  The procedure can be done with period-appropriate materials and can encrypt
  Latin and Italian. The article and supplement reproduce many VMS-like
  statistics. In the supplement, Naibbe trials give the 70-most-common-word
  share (MCW70) about 0.44 +/- 0.01, within the reported VMS range. Their
  moving-average type-token ratio (MATTR) is about 0.56 +/- 0.01, above the
  reported VMS range. The author also shows topic-dependent clusters,
  repetition, rare glyphs, and word-similarity networks in mock ciphertext.
  The supplement states that this is not a VMS decryption and does not confirm
  that VMS is ciphertext. It does not match every word, line, or paragraph
  placement ([S15](https://doi.org/10.1080/01611194.2025.2566408)).

Naibbe therefore changes the question. It makes “a historical cipher could
  preserve these statistics” a demonstrated possibility. It does not provide a
  key for MS 408. A useful role is as a predeclared model family in a blind
  comparison against self-citation, human gibberish, and known-language cipher
  controls.

## Credible decipherment status

As of 2026-09-16, this review found no peer-reviewed, reproducible
whole-manuscript decipherment with an accepted key, a fixed plaintext language,
broad held-out coverage, and independent replication. Yale still describes the script as unidentified and
the text as undeciphered. The 2025 Yale summary says that linguistics can show
word patterns without showing word meanings ([S01](https://beinecke.library.yale.edu/beinecke/collections/beinecke-cipher-voynich-manuscript),
[S04](https://news.yale.edu/2025/02/21/deciphering-mysterious-manuscript)). The peer-reviewed linguistic review also states that the
Researchers have no consensus on the underlying language. It also states that the contents remain
undecipherable (Bowern and Lindemann, 2021; see context sources in
[`sources.json`](sources.json)).

Separate these four claims:

1. **Transcription claim:** a sign string or word boundary was recorded from an
   image.
2. **Structure claim:** a fixed corpus and metric show a pattern that survives
   declared null controls.
3. **Generation claim:** a fixed algorithm produces similar patterns from a
   known input, or from no semantic input.
4. **Decipherment claim:** a fixed key and language map unseen VMS groups to
   readable text with bounded exceptions, broad coverage, and independent
   replication.

Most published VMS results are in levels 1-3. A model that generates similar
   strings is not a model that reads MS 408. A fluent translation without a
   fixed map and blind test is not evidence of level 4.

The 2019 University of Bristol statement is also relevant to status. It says
that the university was not affiliated with the Cheshire paper and removed the
story while concerns about validity were assessed. Treat the 2018/2019 Cheshire
proposal as an unaccepted claim, not as a solved reading (see context sources).

## Most promising next experiment

Run a blind, held-out competition between **Naibbe-like reversible cipher**,
**self-citation generator**, **human-gibberish null**, and **known-language
cipher controls**. This is more informative than another language guess. It
can falsify a model even if no model wins.

1. Freeze the ZL and IT EVA corpora, physical leaf and foldout groups, section
   labels, and an uncertainty manifest before fitting. Keep body text, labels,
   diagrams, and non-Voynich annotations in separate strata.
2. Use training groups only to fit each generator. Use a validation set to
   choose parameters. Keep a test set hidden until all rules and metrics are
   frozen. Re-run the chosen model on the other transcription.
3. For Naibbe, fit only predeclared table families and a bounded card-selection
   rule. Do not construct tables from test word frequencies. For self-citation,
   freeze copy distance, edit operations, and section conditioning. For human
   gibberish, use the published volunteer data and a new matched sample only as
   a null, not as evidence about author intent.
4. Score held-out character, token, line, paragraph, page, section, and hand
   statistics. Include conditional character entropy, word length, exact and
   near-duplicate adjacency, line-edge positions, word-pair asymmetry,
   autocorrelation, page adjacency, topic clustering, and hand-conditioned
   performance. Use the same tokenization and sample size for every model.
5. Compare each model with within-group word-order shuffles,
   within-token character shuffles, group-label shuffles, and planted
   known-language ciphers. Report confidence intervals and every failed fit.
6. Ask an independent implementer to reproduce the frozen run. Do not attempt
   a semantic reading until one model wins on held-out data and passes the
   planted-control check. Even then, treat the result as a model selection
   result until a key maps unseen text to a stable language.

This experiment fits the repository's existing validation protocol. It tests
the ability to predict unseen physical groups. It does not assume that all
pages have one author or one encoding process.

## Strongest pitfalls

* **Parchment is not writing.** Radiocarbon constrains the sampled skin. It does
  not establish when the signs were written or when a source text was composed.
* **Transcription is a model.** EVA signs may combine strokes, split ligatures,
  or preserve uncertain spaces. Repeat all key tests under fixed alternative
  transcription modes.
* **Hand, class, section, and format are confounded.** A classifier can recover
  labels, page design, or production history. This can look like semantics.
* **The hand count is unsettled.** Use Davis's five labels as one annotation
  set. Test a continuous-hand or unknown-hand control. Do not treat either
  count as established provenance.
* **Metric leakage is easy.** Selecting a generator after inspecting VMS word
  frequencies or section clusters turns a fit into an illustration. Freeze the
  target metrics and hold out physical groups.
* **Multiple comparisons inflate confidence.** Predeclare the metric family,
  nulls, sample sizes, and correction rule. Report failed metrics.
* **A reversible mock cipher is not the VMS key.** Naibbe can decode its own
  simulated ciphertext. That says nothing about the correct table for MS 408.
* **Language-like output is not language identification.** Do not infer Latin,
  Hebrew, Nahuatl, or another language from a fluent local reading. Require a
  fixed historical reason, deterministic mapping, held-out text, and external
  replication.
* **Failure to decode is not proof of no meaning.** A procedural model can
  remain competitive without excluding a concealed, steganographic, or
  multi-layer message.

## Core source notes

The 15 core records in [`sources.json`](sources.json) are the primary evidence
set. Each note records one contribution and one limit.

* **S01 — Yale Beinecke collection and catalog.** Institutional record,
  object description, section labels, high-resolution images, and provenance
  chain. Current pages call the script unidentified. Historical catalog claims
  about Bacon, Dee, and New World plants are retained as provenance history,
  not as findings.
* **S02 — Hodgins, 2009.** Primary accelerator mass spectrometry (AMS)
  radiocarbon measurements and calibration
  for four leaves. Dates parchment and documents contamination control. It does
  not date writing or ink.
* **S03 — Zyats, Hodgins, Barabe, 2012.** Conservation, material, and dating
  collaboration report. It confirms major material progress while leaving
  authorship and meaning open.
* **S04 — Yale News, 2025.** Current institutional summary of undeciphered
  status and paleographic collaboration. A news item is not a new measurement.
* **S05 — Davis, 2020.** Digital paleography with Archetype/DigiPal and
  annotation tools. Proposes multiple hands, commonly summarized as five. The
  method and hand labels need independent replication. This review had access
  only to the abstract and paper metadata.
* **S06 — Reddy and Knight, 2011.** Hidden Markov model (HMM), frequency,
  word-length, word-order,
  topic, and page-order tests. Separates structure from a language claim.
* **S07 — Montemurro and Zanette, 2013.** Information-theoretic keywords and
  co-occurrence networks. Shows section-level organization. It does not test
  enough generative alternatives to establish semantics.
* **S08 — Amancio et al., 2013.** Cross-language network and intermittency
  comparison. Finds non-random structure with known-text classification limits.
* **S09 — Rugg, 2004.** Cardan-grille feasibility construction. Shows a
  plausible production mechanism, not historical use. This review had access
  only to the abstract and construction summary.
* **S10 — Rugg and Taylor, 2017.** Larger statistical replication with the
  table-and-grille family. Shows non-uniqueness of Zipf and word-length tests.
  This review had access only to the abstract and article metadata.
* **S11 — Timm and Schinner, 2020.** Self-citation network generator. Shows
  that local copying and modification can reproduce selected VMS properties.
  This review had access only to the abstract and article metadata.
* **S12 — Gaskell and Bowern, 2022.** Human meaningless-text experiment.
  Supplies a realistic low-level null. Samples are too short for full-codex
  claims.
* **S13 — Lindemann and Bowern, 2020/2021 arXiv version.** Corpus and
  conditional-entropy comparison. Reports strong positional constraints and
  keeps transcription effects visible.
* **S14 — Sterneck, Polish, and Bowern, 2021 arXiv version.** Topic models
  recover clusters tied to section and proposed hand. The clustering variables
  are not independent semantic labels.
* **S15 — Greshko, 2025, and supplementary material.** Naibbe is a reversible,
  period-plausible cipher model with mock VMS statistics. The author explicitly
  does not claim a VMS decryption. This review read the abstract and full open
  supplement; the publisher article was not accessible.

### Context sources and current watch items

These sources were read to check synthesis and current disputes. They are not
part of the 15-record primary index.

* Bowern and Lindemann, “The Linguistics of the Voynich Manuscript,” *Annual
  Review of Linguistics* 7 (2021), 285-308,
  [DOI](https://doi.org/10.1146/annurev-linguistics-011619-030613) and
  [author PDF](https://alumniacademy.yale.edu/sites/default/files/2021-07/The%20Linguistics%20of%20the%20Voynich%20Manuscript.pdf).
  This review states that there is no consensus on the underlying language and
  that the contents remain undecipherable. Its argument for natural language is
  an interpretation, not a consensus finding.
* University of Bristol, [2019 statement on the Cheshire paper](https://www.bristol.ac.uk/news/2019/may/voynich-manuscript.html).
  The statement records withdrawal of institutional affiliation while validity
  concerns were assessed. It does not itself settle the manuscript.
* Torsten Timm, [“One Hand, Five Labels”](https://zenodo.org/records/19119470),
  compiled 2026-03-19. This non-peer-reviewed preprint challenges the five-hand
  model and proposes continuous handwriting variation. Use it as a named
  alternative annotation and reproduce its tests before making hand claims.
