# Stage 2 publication audit

Audit date: 2026-09-16.

This review covers the Stage 2 README and status page, the Stage 2 report and
methods, bifolio-v3 reports, substitution reports, new data manifests, and
staged research documents.

## Result

The reviewed files contain no personal information, personal filesystem path,
email address, or private attachment identifier. They do not contain the full
manuscript corpus or a reference-text copy. Bibliographic author names and
source names are research metadata. The public repository URL is an allowed
release identifier.

The scientific boundary is clear in the main publication files. They state that
the experiments do not identify a language, meaning, plaintext, translation, or
decipherment. The Q/B map is complete for the provider metadata. It is not an
independent conservation examination.

The release has five documentation checks. Resolve them before a public update.

## Findings

| ID | Level | Evidence | Finding and required action |
| --- | --- | --- | --- |
| P-1 | Medium | `docs/research/context-method.md:3,24-40`; `docs/research/physical-groups.md:71`; `data/folio_sources.json:77-115`; `docs/research/substitution-design-review.md:52-56`; `docs/research/hypotheses-v1.json:9-33` | These files describe the v1 or v2 grouping as current, or do not mark the text as a pre-v3 record. Mark each file as historical or pre-v3, or update its current-method references to `ivtff-bifolio-metadata-v3`. The v2 protocol and its reports already state that they are historical. |
| P-2 | Medium | `data/bifolio_manifest.json:17,23,33`; `data/physical_map_evidence.json:122-127` | The manifest cites the Q/B definition at PDF page 19 in one field and PDF page 20 (one-based) in another. The physical-evidence record also stores page 19. Confirm the source page convention and use one explicit citation before release. |
| P-3 | Low | `reports/stage2-verification.json:3` | The verification record has `created_utc` on 2026-09-17, while this audit is dated 2026-09-16. This can be a UTC date rollover. Confirm the timestamp or state the time-zone basis. |
| P-4 | Low | `README.md:20`; `reports/STAGE2.md:103-110` | The README says that test-word hit rates are about 9–11%. The four reported values are 8.6%, 9.4%, 10.8%, and 11.3%. Use the exact range, or state that 9–11% is a rounded summary. |
| P-5 | Low | `README.md:22`; `reports/STAGE2.md:116-127` | The README gives one approximate Naibbe rate. The split runs are 78.3% and 78.9%, while the ZL join run is 75.0%. State that the 78% value is for split mode, or include the mode-specific values. |

## Group totals and model eligibility

The counts agree when the source map and the model input filter are kept
separate.

| Artifact | Groups | Train / validation / test | Scope |
| --- | ---: | ---: | --- |
| Provider Q/B manifest | 52 | 35 / 4 / 13 | All source page and locus metadata |
| Context v3 reports | 52 | 35 / 4 / 13 | Complete eligible context population, including groups without paragraph loci |
| Predictive and substitution paragraph runs | 50 | 34 / 3 / 13 | Groups 71 and 73 have only `Lz` and `Cc` records and have no eligible paragraph loci |

The 50-group model count does not mean that the source map is incomplete.
Groups 71 and 73 remain in the context manifests. The source check reports
5,385 ZL locus records across 227 page headers and 5,215 IT locus records
across 225 page headers. Both sources cover 52 Q/B groups, and they agree on
the 225 shared page headers. See `docs/research/bifolio-v3-results-review.md:13-24`
and `reports/STAGE2.md:24-38`.

## Reference limits

The methods retain the limits needed for a public result. The Latin reference
has 422 train, 48 validation, and 51 test charters. The loader removes 132
exact normalized validation duplicates and 129 test duplicates. Near duplicates
remain. The Old Italian reference assigns Dante's three canticles to the three
partitions. They are one work by one author, not independent texts. See
`docs/research/stage2-methods.md:16-32` and
`docs/research/reference-corpora.md:159-173`.

The planted controls use repeated keys on one text partition. They measure
recovery for the tested controls. They do not estimate a false-positive rate.
The fixed Naibbe table was built with Voynich features. Its compatibility rate
is therefore circular evidence, not evidence for a historical cipher. See
`docs/research/stage2-methods.md:60-66` and `reports/STAGE2.md:78-92,116-145`.

## Content and privacy checks

The bifolio, reference, physical-map, and Naibbe manifests contain hashes,
URLs, source labels, licenses, and analysis limits. They do not contain source
text. The aggregate reports contain counts, scores, group assignments, hashes,
and record indices. The two Naibbe reports contain only the declared short
`arma` control tokens. They do not contain manuscript word lists, decoded
corpus text, or a reference-text copy.

The scan found no absolute home path, temporary path, email address, credential,
private-key block, or attachment identifier in the reviewed publication files.
Relative names such as `assets/yale-folio-84r.jpg` identify a local inspection
copy of a public Yale image. They do not identify a user file. The local article
capture in `data/naibbe_source_manifest.json` is represented by a hash and is
marked as non-redistributable.

## Files reviewed

The review included:

* `README.md`, `STATUS.md`, and `reports/STAGE2.md`;
* `docs/research/stage2-methods.md` and the bifolio-v3 result review;
* all JSON files in `reports/substitution/` and `reports/bifolio-v3/`;
* `data/bifolio_manifest.json`, `data/naibbe_source_manifest.json`,
  `data/physical_map_evidence.json`, and `data/reference_manifest.json`;
* the new Stage 2 plans and research reviews, plus the historical grouping
  and verification records that they reference.

This audit records publication checks. It does not provide external scholarly
validation and does not make a claim about the manuscript's language or
meaning.

## Publication corrections

The primary agent checked the source specification again before publication.
Table 6 spans printed PDF pages 19–20. The Q row starts on page 19; the B row is on page 20.
The manifest and evidence record now cite pages 19–20 with explicit one-based numbering.
The physical description uses pages 11–12.
Only citation fields changed in the bifolio manifest. Page assignments and physical groups did not change.
The affected analysis runs were repeated after the metadata and code hashes changed.

Historical method documents now point to Stage 2.
The current hypothesis registry identifies `hypotheses-v1.json` as the unchanged historical registry.
The folio-source record marks its earlier grouping discussion as historical.

The README now gives the exact 8.6–11.3% lexical range.
Its Naibbe summary specifies split spacing and the 78.3–78.9% range.
Review documents use a research-session date. Execution records use UTC timestamps.
The date difference does not change the recorded order of work.
