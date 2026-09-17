# Local cyclic runner review

Review date: 2026-09-17.

This is a read-only review of the fixed local-cyclic runner and its synthetic
tests. It uses no real IVTFF source bytes, source counts, manuscript images,
or VMS arrays. The only parser calls occur in disposable synthetic fixtures.

## Material findings

No runner correctness defect was found under the fixed protocol contract. The
runner verifies all 13 allowlisted files before it imports the parser or the
certificate core. It then checks output paths, runs the frozen synthetic tests,
imports the runtime, parses each source once, extracts each record once, and
uses the same extractions for both tracks.

The runner does not enforce a timeout for the complete source command. Its
internal 60-second timeout covers only the synthetic child test process. Use
the external 60-second timeout for the full fixed command when root adds it to
the freeze and run plan. Do not treat a successful unit test run as a complete
source-run resource check.

## Artifact pins

The current runner and test hashes are:

```text
experiments/local_cyclic/run_frozen.py
da5c6460944d21cf3fa44ed097199eb2473e161f06658de055382952500980c9

experiments/local_cyclic/test_run_frozen.py
3090a0a14944b6a9e78c08d61a81a6b05ab2d7bbc6c28d094c845faa1cec39a5
```

The runner freezes these 13 files in this order:

1. `docs/plans/vms-local-cyclic-falsification-v1.md`
2. `experiments/local_cyclic/__init__.py`
3. `experiments/local_cyclic/certificate.py`
4. `experiments/local_cyclic/test_certificate.py`
5. `experiments/local_cyclic/run_frozen.py`
6. `experiments/local_cyclic/test_run_frozen.py`
7. `experiments/homophonic/units.py`
8. `experiments/homophonic/test_units.py`
9. `src/voynich/__init__.py`
10. `src/voynich/corpus.py`
11. `data/source_manifest.json`
12. `data/raw/ZL3b-n.txt`
13. `data/raw/IT2a-n.txt`

The freeze record is outside this allowlist. The runner checks the schema,
protocol, command, source IDs, unitizations, outputs, runtime field, path
format, file order, regular-file status, and every SHA-256 value. It rejects
duplicates, unknown paths, path traversal, symlinked files, and symlinked
parent directories.

## Freeze and execution order

`main` accepts no command-line options. The only fixed command is:

```text
python -m experiments.local_cyclic.run_frozen
```

`run_frozen` performs these operations in this order:

1. Verify the external freeze record and all 13 file bytes.
2. Refuse an existing output or output path component.
3. Run the 21 synthetic certificate and unitizer tests in a child process.
4. Import the corpus parser, certificate core, and frozen unitizer.
5. Parse each source with `uncertain_spaces="split"`.
6. Extract strict words once for every source record.
7. Run `raw_eva` and `visual_six` over the same extraction objects.
8. Write exactly four exclusive-create JSON outputs.

The hash gate runs before `_load_runtime` and before `parse_ivtff`. The mutated
byte test patches `_load_runtime` and confirms that a freeze failure prevents
that call. The output tests confirm that an existing file or symlinked results
directory fails before source work and leaves an existing sentinel unchanged.
The module command loads the package initializer before the module body, but
the frozen initializer is a minimal docstring and imports no parser or core.

## Synthetic subprocess verification

The disposable fixture creates two synthetic records for each of two source
IDs. The CLI test runs the actual child command with no options in a separate
process. It returns zero and writes these four JSON outputs:

```text
results/vms-local-cyclic-falsification-v1/ZL3b-n-raw_eva.json
results/vms-local-cyclic-falsification-v1/ZL3b-n-visual_six.json
results/vms-local-cyclic-falsification-v1/IT2a-n-raw_eva.json
results/vms-local-cyclic-falsification-v1/IT2a-n-visual_six.json
```

The synthetic count test confirms two records, three eligible words, seven
raw units, four adjacent pairs, two certificates, and two affected words. The
two certificates use the same local candidate word index in different records.
The runner sums affected words per record and keeps locations with record
indices zero and one. This verifies the required source-index alignment.

The visual test records the half-open span `[0, 1]`. The JSON checks find no
`tokens` or `surface` field. Locations contain source file, record index,
folio, locus, transcriber, candidate word index, unit index, unit label, and
the visual span when present. They do not contain source words or complete
token arrays.

## Source and count handling

The runner reads `record["text_raw"]` and passes it to the strict extractor.
It does not use the parser's filtered `tokens` list. It keeps source IDs
separate and reports the relative source file in each output. It preserves
record order and the parser's `folio`, `locus`, and `transcriber` fields in
certificate locations.

The extraction list is built once per source record before either track runs.
The raw and visual reports therefore use the same eligible-word population.
Excluded-word counts are summed once per source and copied into both track
reports. Per-record affected-word counts are summed because candidate word
indices restart for each locus.

The runner checks that the certificate count equals the number of saved
locations. It sets the three declared status values from aggregate eligible
word and certificate counts. It records `image_review` as
`not_performed`.

## Test evidence

The complete synthetic suite passed:

```text
python -m unittest experiments.local_cyclic.test_run_frozen \
  experiments.local_cyclic.test_certificate \
  experiments.homophonic.test_units
Ran 29 tests
OK
```

This includes eight runner tests, 15 strict-certificate tests, and six
unitizer tests. The runner tests use temporary project directories and
synthetic IVTFF text only. No real source file was parsed for this review.

## Conditions before source use

Root must publish the freeze record with the exact 13-file allowlist and
hashes. Root must add the fixed command, four output paths, and the external
60-second whole-command timeout to the run plan. The source command must run in
an environment that preserves the fixed project root and Python module path.

After those conditions, the runner can produce a bounded transcription result
for the declared source bytes and two fixed unitizations. The result can test
the exact local cyclic contract. It cannot establish a language, plaintext,
translation, or manuscript solution.
