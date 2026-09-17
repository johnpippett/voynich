# Cyclic pairing control v1

Status: fixed development protocol, before the first run. Date: 2026-09-17.

This protocol measures ciphertext-only pair recovery in the fixed capacity-two
control emitter. It uses two validation streams from pinned reference inputs:
Latin LLCT and Old Italian. It does not use the Voynich manuscript.

This is an extension of inspected controls. It is a development result. It is
not a blind rerun and it does not repair or reclassify an earlier gate.

The runner and its synthetic tests implement this procedure. The external
freeze records their final reviewed bytes before any reference-stream run.

## Scope and aim

Run the same fixed control family for both corpora:

| Setting | Value |
| --- | --- |
| Corpora | `latin_llct`, `italian_old` |
| Control family | `cap2` |
| Seed | `7000` |
| Declared units | `c00` through `c51` |
| Capacity | Two units for each of 26 letters |
| Stream | Validation only |
| Matching budget | 100,000 branch nodes per search |
| Forced-edge limit | 26 witness-edge queries per corpus |

The aim is to measure whether cyclic alternation identifies observed unit
pairs when some declared units are unseen. The result must separate forced
observed-observed, observed-unseen, and unseen-unseen edges.

The run must not fit language letters, score a plaintext, translate text,
select a tied key, or make a claim about the manuscript. Reduction to pair
variables, substitution search, new seeds, and VMS streams require separate
protocols.

The prior inspected controls pin the validation stream hashes below. The
runner must use the same canonical stream hash and stop on a mismatch.
These values are input consistency pins, not pairing evidence.

| Corpus | Prior report | Report SHA-256 | `cipher_validation` SHA-256 |
| --- | --- | --- | --- |
| `latin_llct` | `reports/homophonic-feasibility-v1/latin-cold.json` | `923dba00df53ff05ca88e91362ea44c693d66b8f0824071d85cc5b0d984ba77e` | `eb03e98b086b9b8bc883f349afaee968bfeaeee8c95be5f66bec320e54b419b2` |
| `italian_old` | `reports/homophonic-feasibility-v1/italian-cold.json` | `4209022e13399bb7347b8f1d098f43c4d0922ae1b9c6df72382ed5553b44b0b3` | `d7e9c6e0b716cf7ea1c7deb4f135ca2692ea70b4f927548e99668ab0c1428492` |

## Fixed input

Use the frozen `load_reference_partitions` loader from
`src/voynich/reference.py`. It must read and hash every pinned CoNLL-U file
for both corpora, including train, validation, and test. It must enforce the
source manifest and the existing document and duplicate checks.

Use only `words["validation"]` from each returned corpus. Pass this list once
to `experiments.homophonic.controls.encrypt_words` with the frozen `cap2`
key from seed `7000`. The control emitter resets its offsets at this call
boundary. The resulting word boundaries and unit order form one complete
validation partition for the pair check.

The loader may read plaintext to create this fixed input. After encryption,
the pairing and forced-edge code may receive only the declared units and the
ciphertext validation partition. Do not pass plaintext, a lexicon, a fitted
map, a score, a planted pairing, or a planted orientation to those functions.
Do not encrypt or score train or test data.

## Freeze before the first run

Publish this plan and a separate pre-run freeze record before any control run.
The freeze record must contain the exact command, Python version, platform,
output paths, resource limits, and all SHA-256 values. A missing file or hash
mismatch stops the run before encryption or matching.

The current frozen code and manifest inputs are:

| Path | SHA-256 |
| --- | --- |
| `src/voynich/reference.py` | `97e173c761b137d3653a827315b62a68af3e96abd189afdecc46e9759d2b94d9` |
| `data/reference_manifest.json` | `f261b781f150991e3305aae5057a94dc91afd8e59c58bb22ff199347f5ce3e6d` |
| `experiments/homophonic/controls.py` | `4845d1de4e766c5d63b23919bab2715db24b431ba502112494e477a1740fd896` |
| `docs/plans/visual-homophonic-pilot.md` | `0e6a6edf5e0172f5e7a0f1fbf2f7ede8b9b181c7180aa616de58f44ae04d1249` |
| `experiments/cyclic_pairing/pairing.py` | `da9c89b4738d0dde959a3c730111dee864c05cd3e3b20932b2b8a3f30a57da95` |
| `experiments/cyclic_pairing/forced.py` | `3f3a4fc450b5921905b8931310379d8361a6ca0b8d2989b8b8e939ddbc8d76a4` |
| `experiments/cyclic_pairing/test_pairing.py` | `266d49547bf361a0f2ac290c88fb29f3e9ac86d08dbd73450654d50e87c1bf3d` |
| `experiments/cyclic_pairing/test_forced.py` | `1f33dbd220e709446634f78ac656a01c4ad180538c1427c14049073e98eb893c` |

The six pinned CoNLL-U source files have these hashes:

| Corpus | File | SHA-256 |
| --- | --- | --- |
| `latin_llct` | `la_llct-ud-train.conllu` | `8aabc8735c7a623a9e4820e13861a87459dd0fb5b2d238f0583854143526a643` |
| `latin_llct` | `la_llct-ud-dev.conllu` | `040457f2e47265a5676c83ce236e1d625af41eda8f779812841e8ba84e28480c` |
| `latin_llct` | `la_llct-ud-test.conllu` | `81d9f57de66d83303ad4df54a60cd445ac089b50070d369831a632b4cf948e64` |
| `italian_old` | `it_old-ud-train.conllu` | `9e94e25d826632a005adc2a8a1daa88f46bdd1509d56090b4c82d27779e1a5e0` |
| `italian_old` | `it_old-ud-dev.conllu` | `6c900aecef3abebfe87c4e5d5c9880326cc69b8122e62ec95ef6c50fbe4e6e0b` |
| `italian_old` | `it_old-ud-test.conllu` | `19dc1ecf5bfffd552130be63c3dab02d1dd9b9e6a6d4bc31ace0fe6494ebdf89` |

The freeze record must also hash every manifest-listed README and license
file. The loader checks the six CoNLL-U hashes. These checks do not assert a
new license or change the source attribution in the manifest.

Before the first published run, the freeze record must hash the final
reviewed bytes of this plan and `docs/research/cyclic-emitter-pairing.md`.
It must record the six source hashes, the manifest hash, the prior report
pins, the frozen loader, the emitter, and the pairing modules.

Run all cyclic pairing tests before the control. The pairing and forced-edge
helpers have 20 tests. Study and wrapper tests cover additional gates.
Do not start a run if any test fails.

After code review and publication of the freeze, use this command:

```sh
python -m experiments.cyclic_pairing.run_controls
```

For each corpus, the runner writes these three files below
`results/cyclic-pairing-control-v1/<corpus>/`:

* `input.json`;
* `pairing.json`, including forced-edge evidence;
* `diagnostics.json`.

The freeze record must hash the runner before this command is used.
Run `python scripts/fetch_reference_sources.py` separately to populate the source cache.
The wrapper does not use the network. It writes aggregate supervision metadata
to `reports/cyclic-pairing-control-v1/supervision.json`.
It keeps measured resource data in `results/cyclic-pairing-control-v1/resources.json`.

## Ciphertext-only procedure

For each corpus, perform these steps in order:

1. Verify the freeze record, source manifest, and exact 52-unit inventory.
2. Load all source partitions and create the validation ciphertext partition.
3. Check the stream hash. Write an input record with source hashes, counts, and settings.
4. Build the compatibility graph from the ciphertext partition only.
5. Run a full-inventory matching search with a 100,000-node budget and at
   most two witnesses.
6. Run forced-edge queries for the selected witness, with the same node budget
   for every query and at most 26 edge queries.
7. Save `pairing.json`, including the outer matching result and all forced-edge
   evidence, before any planted-key diagnostic.
8. Only now compare graph edges and orientations with the known control key.

The pairing code must use `scope="full"`. A matching on observed units alone
is conditional and cannot support a full-inventory result. A budget stop must
remain `unknown_budget` unless at least two valid witnesses already prove
`multiple`. An exhaustive search may prove `unique` or `none`.

An exhausted full-inventory search can certify `unique`, including for the
52-unit inventory. The default two-witness limit is enough to certify
`multiple`; a future caller may request a larger witness limit.

The forced-edge evidence in `pairing.json` must keep `forced`, `not_forced`,
and `unknown` separate. An edge is forced only when edge removal has an exhaustive `none`
result. If an edge-removed query returns a valid alternative witness, the
edge is `not_forced`, even when that query also stops at its node budget. An
edge is `unknown` only when the query finds no witness and stops before an
exhaustive result. If the original search has no witness, record `infeasible`
or `unknown_budget` and do not report forced edges.

`forced_edges` repeats the bounded full-matching search before its edge
queries. Record that original status, witness count, nodes, and budget in the
forced evidence as well as the outer matching result. The overall forced
status is `unknown_budget` when the repeated original search is incomplete,
an edge query is unknown, or queries are skipped. Record the original status,
query count, skipped count, witness count, node counts, and per-edge query
status.

The outer and repeated original searches must agree on status, witness count,
node count, budget, and first witness. A disagreement is an implementation failure.

The protocol limit is 26 queries because a complete 52-unit witness has 26
edges. Enforce `queries_run <= 26` in the run wrapper and record the limit.
Do not change the helper limit in this protocol.

## Records and diagnostics

Write private records below the ignored result directory
`results/cyclic-pairing-control-v1/`. Refuse to overwrite an existing record.
Do not place raw plaintext words, raw ciphertext word arrays, or model data in
the records.

Write `input.json`, `pairing.json`, and `diagnostics.json` for each corpus in
its corpus directory. Keep forced evidence inside `pairing.json`.

The input and pairing records must contain the protocol version, corpus,
family, seed, capacity, declared-unit count and hash, manifest hash, source
file hashes, frozen code and test hashes, validation stream hash, word and
unit-token counts, and `input_scope: "ciphertext_validation_only"`.

The pairing record must also contain the graph vertex count, observed and
unseen counts, edge count, edge counts by observed/unseen category, full
matching status, witness count, nodes visited, node budget, and any retained
unit-pair witnesses. A witness contains unit names only. It contains no
plaintext letter names.

The forced section in `pairing.json` must contain the full matching status,
the selected witness when one exists, per-edge statuses, query statuses,
witness counts, node counts, and aggregate forced, not-forced, and unknown
counts for:

* observed-observed edges;
* observed-unseen edges;
* unseen-unseen edges.

The diagnostics record is written last. It may compare the known control pair
set and cycle orientation with the earlier records. It must not choose a
matching, repair a graph, set a tie rule, or change a prior record. It must
state whether a full matching was unique, multiple, absent, or unknown. A
multiple result does not permit a selected pairing or a tie-picked key.

All 26 planted pairs must remain graph edges. Comparable orientations must agree.
Every reported forced edge must belong to the planted pair set.
A unique witness must equal that complete pair set. A positive control cannot
return an exhaustive `none` result. A contradiction records `implementation_failure`
and stops with a nonzero exit status. It does not alter the earlier pairing record.

## Runtime guard

The runner must use one process per corpus. Limit each corpus to 300
seconds of wall time. Sample resident set size every 0.25 seconds. Set a
7 GiB sampled RSS threshold. When the threshold is reached, send a
termination signal, allow a 5-second grace period, and then kill the process.
The sampled guard can overshoot. Do not set `RLIMIT_AS` or another
address-space limit. Keep the 100,000-node limit for the original and every
edge query. Enforce at most 26 edge queries.

The resource monitor requires Linux. Python and platform versions are recorded
for provenance; they are not exact version requirements.

## Gates and limits

Stop before result publication if any gate fails:

* the manifest or any frozen hash differs;
* a regenerated validation stream differs from its pinned hash;
* the loader does not verify all pinned source partitions;
* the inventory is not exactly 52 units with exactly two declared cipher units per letter;
* the synthetic tests do not pass;
* the pairer receives data outside the ciphertext-only interface;
* a record contains raw word arrays or plaintext fit data;
* pairing or forced evidence is written after planted diagnostics;
* a forced query exceeds 100,000 branch nodes or the 26-query limit;
* a budget stop is reported as an exhaustive result.

The protocol measures a property of this deterministic control emitter and
these two validation streams. It does not estimate a language property. The
reference corpora are control inputs with their stated source, genre, and
normalization limits. A complete or unique matching does not identify letter
names or a plaintext.

The shared research remains active. A later protocol must define any use of
pair groups in substitution search, any new control seed, any manuscript
stream, and any claim about decipherment.
