# Voynich research

This project tests explanations for the Voynich manuscript, Beinecke MS 408.
It keeps source information and compares observations with explicit statistical controls.

**This project does not show a decipherment.**
Statistical structure does not show a language, a translation, or the absence of meaning.

Read the [initial findings](reports/FINDINGS.md) and [research status](STATUS.md).
The findings include three complete analysis runs, transcription comparisons, and the limits of each experiment.

The initial image is folio [84r in Yale Digital Collections](https://collections.library.yale.edu/catalog/2002046?child_oid=1006226).
The [folio report](docs/research/folio.md) gives the identification evidence.

## Reproduce the research

Use Python 3.11 or later. The analysis uses the Python standard library.

```sh
git clone https://github.com/johnpippett/voynich.git
cd voynich
python scripts/fetch_sources.py
PYTHONPATH=src python -m voynich verify-sources
PYTHONPATH=src python -m unittest discover -s tests -v
PYTHONPATH=src python -m voynich run --output results/zl-split
PYTHONPATH=src python -m voynich run --source data/raw/ZL3b-n.txt --uncertain-spaces join --output results/zl-join
PYTHONPATH=src python -m voynich run --source data/raw/IT2a-n.txt --output results/it-split
```

Each run writes the configuration, input hash, code hashes, statistics, and parsed source records.
Existing result directories remain unchanged. Use a new output directory for another run.

Export aggregate results after the three runs finish:

```sh
python scripts/export_results.py --replace results/zl-split results/zl-join results/it-split
python scripts/build_summary.py
```

The export command replaces the committed aggregate reports in your local checkout.
The summary script uses those reports and the downloaded source files.
The committed verification record describes the original research runs. A new run does not update that record.
Review all conclusions after a method or input change.

## Data

The source manifest records two EVA transcriptions published by René Zandbergen:

- Zandbergen–Landini, `ZL3b-n.txt`.
- Takahashi-derived interlinear transcription, `IT2a-n.txt`.

EVA is the Extensible Voynich Alphabet. It represents written shapes. It does not give them meaning.
The source [transcription documentation](https://www.voynich.nu/transcr.html) describes the format and its limitations.

The download script retrieves files from their original provider and checks their hashes.
The repository does not distribute the transcription files or complete parsed copies.
The manifest does not give permission to redistribute those files.

The current parser handles basic EVA input with strict rejection.
It keeps each location and its original text.
It rejects uncertain or rare-symbol words from the initial statistical sample.
It reports exclusions and supports `uncertain_spaces='split'` and
`uncertain_spaces='join'`.

## Experiments

- Corpus counts and character entropy.
- Word permutations within complete paragraph lines.
- Character prediction on separate `folio_group` values.
- Word prediction with a previous-word model and shuffled-training control.
- Comparison of aligned transcription locations.

The tests use fixed parameters and explicit controls.
All initial results are exploratory.
The current split uses conservative `folio_group` unions. It keeps `69/70`, `71/72`, `85/86`, `88/89/90`, `94/95`, and `100/101/102` together.
The `85/86` union has direct Yale support. The other cross-number unions are candidate relations.
The mapping does not identify every physical sheet.
The mapping version is `conservative-foldout-groups-v2`. The source alias `fRos` maps to `85`.
The validation protocol records this limitation and the requirements for future decoding tests.

## Research documents

- [Research design](docs/plans/design.md)
- [Corpus methods](docs/research/corpus.md)
- [Literature review](docs/research/literature.md)
- [Validation protocol](docs/research/validation-protocol.md)
- [Hypothesis registry](docs/research/hypotheses.json)

## Contributions

A proposed reading must have a fixed method, source locations, coverage measurements, and an exception record.
It must predict material excluded from development.
It must make independent reproduction possible.
Plausible words or illustrations alone do not satisfy these requirements.

Report unsuccessful experiments with their settings and limitations.
Do not describe a statistical match as a translation.
