# Voynich research

This project tests explanations for the Voynich manuscript, Beinecke MS 408.
It keeps source records and compares observations with explicit statistical controls.

**This project has not deciphered the manuscript.**
It has no validated key, plaintext language, or translation.

Read the [lexicon bounds](reports/LEXICON.md), [Stage 2 findings](reports/STAGE2.md), and [research status](STATUS.md).

The next [model prototype](experiments/homophonic/README.md) permits several
cipher units per plaintext letter. Its known-cipher controls must be checked
before manuscript use.
The [initial findings](reports/FINDINGS.md) remain available as historical results.
Stage 2 replaces their prediction partitions with source-backed bifolio groups.

The initial image is [folio 84r in Yale Digital Collections](https://collections.library.yale.edu/catalog/2002046?child_oid=1006226).
The [folio report](docs/research/folio.md) gives the identification evidence.

## Results

- The new lexicon pilot bounds the training score at 35.51% or less in four fixed substitution problems.
- That score averages token and type hit rates. The bounds apply only to the declared word lists, raw EVA units, and injective keys.
- Two lexicon controls recovered every test character. The Italian control still has at least 60 equally scoring keys.
- Stage 2 substitution controls recovered every test character for 32 Latin keys and 32 Old Italian keys.
- Each language used one fixed set of text partitions. These are repeated key tests, not independent text samples.
- The Stage 2 manuscript search found no validated reading. Its keys matched 8.6–11.3% of test words to the selected reference vocabularies.
- The source metadata identifies 52 bifolio groups. The two transcriptions agree on all 225 shared page assignments.
- Fixed published Naibbe tables accept 78.3–78.9% of tokens with split spacing. Many tokens have multiple candidate readings.

These results have narrow limits.
The lexicon bounds apply to one restricted key model.
These experiments do not cover every writing system or language.
The Naibbe tables used Voynich features during construction. Their compatibility is not independent evidence of a historical cipher.

## Reproduce the research

Use Python 3.11 or later. The analysis uses the Python standard library.

```sh
git clone https://github.com/johnpippett/voynich.git
cd voynich
python scripts/fetch_sources.py
python scripts/fetch_reference_sources.py
python scripts/fetch_naibbe_table.py
PYTHONPATH=src python -m voynich verify-sources
PYTHONPATH=src python -m unittest discover -s tests -v
PYTHONPATH=src:. python -m unittest discover -s experiments/lexicon -p 'test_*.py' -v
```

The download scripts retrieve pinned inputs and check their hashes.
They do not execute downloaded code.
Use new output paths for each run:

```sh
PYTHONPATH=src python -m voynich run --output results/reproduction/zl-split
PYTHONPATH=src python -m voynich run --uncertain-spaces join --output results/reproduction/zl-join
PYTHONPATH=src python -m voynich run --source data/raw/IT2a-n.txt --output results/reproduction/it-split
python scripts/export_results.py --reports-dir results/reproduction/aggregates results/reproduction/zl-split results/reproduction/zl-join results/reproduction/it-split
python scripts/run_voynich_substitution.py --language latin_llct --source ZL3b-n.txt --output results/reproduction/latin-zl.json
python scripts/check_naibbe_compatibility.py --output results/reproduction/naibbe.json
```

The [Stage 2 report](reports/STAGE2.md) gives the remaining experiment commands.
The [lexicon report](reports/LEXICON.md) gives the new bounded-search commands and results.
The [methods document](docs/research/stage2-methods.md) defines sampling, controls, normalization, and search settings.
The [verification record](reports/stage2-verification.json) records the checks for the published runs.
A new run does not update that record.
The [lexicon verification record](reports/lexicon-verification.json) covers the new solver and its public-source reproduction.

## Data and scope

The manuscript inputs are two EVA transcriptions published by René Zandbergen:

- Zandbergen–Landini, `ZL3b-n.txt`.
- Takahashi-derived interlinear transcription, `IT2a-n.txt`.

EVA is the Extensible Voynich Alphabet. It represents written shapes. It does not give them meaning.
The [transcription documentation](https://www.voynich.nu/transcr.html) describes the format and its limits.
The parser rejects uncertain or rare-symbol words from the statistical sample.
It records exclusions and supports separate split and join policies for uncertain spaces.

The reference texts contain Latin legal charters and Dante's Old Italian poetry.
Their dates, subjects, authors, and spelling conventions limit comparisons with the manuscript.
The [reference corpus report](docs/research/reference-corpora.md) records these limits and the source licences.

The repository distributes aggregate results, code, and metadata.
It does not distribute the manuscript transcriptions, complete parsed text, or reference text copies.
Source manifests do not grant permission to redistribute those inputs.

The [bifolio manifest](data/bifolio_manifest.json) uses provider metadata for quire `Q` and bifolio `B`.
The current grouping version is `ivtff-bifolio-metadata-v3`.
Independent conservation verification remains outstanding.
All manuscript analyses remain exploratory. A new partition does not make previously inspected data unseen.

## Research documents

- [Research design](docs/plans/design.md)
- [Validation protocol](docs/research/validation-protocol.md)
- [Hypothesis registry](docs/research/hypotheses.json)
- [Literature review](docs/research/literature.md)
- [Physical grouping audit](docs/research/physical-map-audit.md)
- [Naibbe inversion limits](docs/research/naibbe-inversion.md)

## Contributions

A proposed reading must have a fixed method, source locations, coverage measurements, and an exception record.
It must predict material excluded from development and permit independent reproduction.
Plausible words or illustrations alone do not satisfy these requirements.
Report unsuccessful experiments with their settings and limits.
Do not describe a statistical match as a translation.
