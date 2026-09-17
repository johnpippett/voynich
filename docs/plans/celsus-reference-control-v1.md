# Celsus reference control v1

Status: fixed partition protocol; model run pending. Date: 2026-09-17.

This plan adds one ancient medical control to the existing synthetic
Latin and Italian controls. It does not test the Voynich Manuscript (VMS).
It does not identify a language or produce a translation.

## Aim and limits

Celsus is one additional author and work for an ancient medical-prose control.
It is not a replicated medical corpus or an independent Latin author replicate.
The result can show how one fixed cipher search behaves on medical vocabulary
and edited classical Latin. Genre, era, source edition, author, and language
effects remain confounded.

The smallest informative study has three descriptive cells:

| Cell | Input | Status |
| --- | --- | --- |
| Latin cold | Frozen Latin LLCT control | Existing result |
| Italian cold | Frozen Old Italian control | Existing result |
| Celsus cold | This plan | One new run |

Use one cold run for each cell. Do not add a warm start, a second seed, or a
new capacity after reading the Celsus result. The two existing reports are
comparators. They are not independent author replicates.

## Fixed source and projection

Use the source and projection from `celsus-projection-v1`.
The source is the pinned Perseus file at commit
`ae0fe427f56d7652efc3090af74a2663a4cbed60`.
Its URL is:

```text
https://raw.githubusercontent.com/PerseusDL/canonical-latinLit/ae0fe427f56d7652efc3090af74a2663a4cbed60/data/phi0836/phi002/phi0836.phi002.perseus-lat5.xml
```

The source SHA-256 is
`a4a5194ba38a7efd5192d20f2a7b696f4fa64105010eb629aa7c35255a935145`.
The source audit receipt SHA-256 is
`aebba00a41c120e4101d94c67f4783e9de55106051d158f3ccd41246d960e6de`.
The source has 550 paragraphs, 211 chapters, and eight books. The paragraph
counts by book are `28,45,45,35,204,80,74,39`. The selected subtrees contain
446 choices and 276 Greek foreign elements. These are source audit counts, not
word counts.

Use the accepted projection receipt before the control run. The receipt is
`reports/celsus-projection-v1/acceptance.json`, with SHA-256
`8067be5cb874a8e53472d11e3188be0eb92b7c30c3def9f31de2451e06fc6faf`.
It records status `COMPLETE`, result `PASS`, and manual status `ACCEPTED` at
public commit `cb75486e955e476e963e55fb23c73cee492ab000`. The module and
independent projected paragraph files have SHA-256
`f37d99f5ad0771c32c4d71934b58df00438ca7dadf870f89dc93b181c1d373f2`.
Verify these acceptance, source, and projection hashes before partitioning.
Do not use an unaccepted projection as a model input.

Use the corrected projection only. It keeps `corr` branches, excludes Greek
`foreign` content and editorial exclusions, preserves permitted tails, and
collapses only XML whitespace. It does not change `u/v`, `i/j`, case, ligatures,
spelling, or word boundaries. A raw-versus-corrected comparison is a separate
study.

The projection removes Greek spans from the model stream. It does not insert a
`[GREEK]` token or any other gap marker. The projection boundary check must
pass before tokenization. Keep the accepted projection receipt with its removed-node
counts as provenance. This stage does not measure the affected paragraph count.
If a paragraph has no usable token after removal,
keep its source record for the audit and omit it from the word stream.

## Source split

Use a complete chapter as the split unit. The group key is
`book_id:chapter_id`. Keep every paragraph in a chapter in one split. A
paragraph split could place repeated nearby medical formulas in both fit and
test data. A whole-book split would leave only eight groups and would be
dominated by Book 5, which has 204 of the 550 paragraphs. Chapter groups are
the smallest practical unit that removes paragraph-level leakage while
leaving 211 groups. This choice reduces one leakage path; it does not remove
shared author, topic, or adjacent-chapter dependence.

Assign chapters in source XML order, separately within each book:

1. Let `n` be the chapter count for the book.
2. Assign the first `floor(0.60*n)` chapters to `train`.
3. Assign the next `floor(0.20*n)` chapters to `validation`.
4. Assign the remaining chapters to `test`.

All books have enough chapters for all three splits. The resulting word and
paragraph counts are measured after tokenization. Do not rebalance by reading
model scores or by moving a chapter. This contiguous block split limits
paragraph leakage. It does not make adjacent chapters independent.

The split manifest must record every chapter key and its split. Publish the
manifest hash, not raw text. Stop if one chapter key appears in more than one
split or if the manifest differs from the frozen source order.

Use these split meanings:

- `train`: plaintext words build the lexicon.
- `validation`: plaintext words are encrypted and supplied to the solver as
  the fitting stream.
- `test`: plaintext words are encrypted after the fitted key record is saved.

The solver must not receive encrypted training words or plaintext validation
and test words. The loader may parse, tokenize, hash, split, and deduplicate
all partitions before the key record is written. The fixed control runner
encrypts and scores test words only after it saves the fitted key.
Test data must not affect fitting or model selection.

## Token policy

Keep the projected paragraph text as a provenance layer. Scan it from left
to right. A token candidate is a maximal run of characters for which
`char.isalpha()` is true, plus adjacent Unicode combining marks. Use this one
standard-library tokenizer for every Celsus split. Apply the existing
`voynich.reference.normalize_word` function to each candidate.

That function performs NFKD, case folding, removal of combining marks, and
acceptance of complete ASCII `a-z` forms. This is mechanical normalization.
It is not spelling repair. Do not repair `u/v`, `i/j`, abbreviations, source
editorial choices, or word boundaries. Do not use a dictionary to change a
word. Count rejected runs and retain their counts in the private manifest.

Keep Roman-numeral strings as literal letter tokens. Do not convert dosage
numbers to integers. Do not filter a token because it looks like a Roman
numeral. Record any Roman-like token count only as a fixed provenance
statistic. Digits and rejected non-ASCII runs follow the fixed normalization
rule and do not become model tokens.

Do not add tokens for removed Greek spans. Do not join tokens across a removed
span. The frozen projection already retains the source tail and reports a
retained-letter join failure. Do not repair a failed join in this experiment.

After tokenization, remove exact duplicate normalized paragraph sequences from
later splits in this order: `train`, then `validation`, then `test`. Keep the
first occurrence. Keep duplicates within one split. Do not remove repeated
word types; shared vocabulary is part of the lexical control. Record duplicate
counts by split. Near duplicates remain and are a stated limitation.

## Fixed cipher and search

Use the same synthetic control family as the published cold runs:

| Setting | Fixed value |
| --- | --- |
| Family | `cap2` homophonic control |
| Planted seed | `7000` |
| Cipher units | `c00` through `c51` |
| Plain alphabet | lowercase ASCII `a` through `z` |
| Planted key | exactly two cipher units per plaintext letter; solver allows at most two |
| Emitter | deterministic per-letter cycle, reset at each partition |
| Solver | frozen exact lexical solver and bitset bound |
| Warm start | none |
| Node budget | `1000` |

The synthetic units are deliberate. They make the reference control use the
same total cipher-unit-to-letter map family even when a source has fewer
observed symbols. They are not claims about VMS signs.

Use the integer lexical objective from the existing runner. For the validation
ciphertext, let `N` be the total token count and `T` the total type count. For
word type `w`, let `n(w)` be its token count:

```text
weight(w) = n(w) * T + N
```

The denominator is `2*T*N`. Report the exact score, token and type hit rates, solver
bounds, certification status, fitted-unit coverage, test-unit coverage, and
full and observed character and token recovery. Report ambiguity only with the
published distinction: preserved-hit completions are a lower bound, and they
are optimal-key bounds only when the objective is certified.

The planted key enters encryption and post-fit diagnostics only. It must not
enter the training lexicon, solver input, branch order, tie rule, stopping
rule, or model selection. Save the fitted key record before test diagnostics.

No model choice is made from Celsus test data. The family, seed, capacity,
solver, normalization, split rule, and budget are fixed before the run. The
validation stream is fitting input, not a model-selection set in this pilot.
If a later study compares families or token policies, select settings from a
predeclared training-only procedure. Freeze the selection before validation
fit and one test score. A new choice is a new plan and manifest.

## Freeze inputs

Before a run, publish a manifest with these inputs and hashes:

- this plan;
- the accepted Celsus projection receipt and source XML;
- the module and independent projected paragraph files;
- the split manifest and Celsus tokenizer adapter;
- `experiments/homophonic/run_controls.py`;
- `experiments/homophonic/controls.py`;
- `experiments/homophonic/solver.py`;
- `src/voynich/reference.py`;
- the frozen Latin and Italian cold reports;
- `docs/plans/visual-homophonic-pilot.md`.

The current comparator hashes are:

| Input | SHA-256 |
| --- | --- |
| `docs/plans/celsus-projection-v1.md` | `3f9dcb864c9302d220d0fe1cafbc869ef9422724221fe38860f9481e3ff28efa` |
| `src/voynich/reference.py` | `97e173c761b137d3653a827315b62a68af3e96abd189afdecc46e9759d2b94d9` |
| `docs/plans/visual-homophonic-pilot.md` | `0e6a6edf5e0172f5e7a0f1fbf2f7ede8b9b181c7180aa616de58f44ae04d1249` |
| `reports/homophonic-feasibility-v1/latin-cold.json` | `923dba00df53ff05ca88e91362ea44c693d66b8f0824071d85cc5b0d984ba77e` |
| `reports/homophonic-feasibility-v1/italian-cold.json` | `4209022e13399bb7347b8f1d098f43c4d0922ae1b9c6df72382ed5553b44b0b3` |

Also record the hashes of the frozen solver modules. A changed input stops the
run. Do not refresh a source from a branch or overwrite an existing result.

## Staged partition freeze

Publish this plan, the adapter, its tests, the partition wrapper, and wrapper
tests before any source partition run. The wrapper requires a new external
`experiments/medical/partition-freeze-v1.json`. Its exact allowlist is:

- this plan;
- `experiments/medical/reference_adapter.py` and its test;
- `experiments/medical/run_partition.py` and its test;
- `src/voynich/__init__.py` and `src/voynich/reference.py`;
- the accepted receipt and initial receipt;
- `experiments/medical/freeze-v1.json` and its five pinned projection files;
- the pinned source XML;
- both module and independent projected JSONL files.

The wrapper checks every allowlisted byte before it imports the adapter or
parses the module JSONL. It requires the accepted receipt to report `PASS`,
`COMPLETE`, and `ACCEPTED`, and it requires the pinned source and projection
hashes. It reads the module JSONL once and calls the adapter once.

Run the fixed command only after the external freeze is published:

```sh
python -m experiments.medical.run_partition
```

The wrapper writes exactly these files to
`results/celsus-reference-control-v1/`:

- `partitions.private.json`;
- `paragraphs.private.jsonl`;
- `partition-manifest.json`.

The first two files are private. The public manifest contains adapter,
source, projection, acceptance, freeze, and private-output hashes. It has no
paragraph text, ciphertext, or token arrays. The wrapper refuses an existing
output directory or a symlink in its path.

Record the resulting public manifest hash before any solver process:

```sh
sha256sum results/celsus-reference-control-v1/partition-manifest.json
```

The partition loader may parse, hash, tokenize, and prepare all three
partitions before fitting. The solver may score the test partition only after
it saves the fitted key record. A later model run must record the adapter,
source, projection, and partition-manifest hashes before it starts.

## Known-cipher gates

Run the Celsus known-cipher control before any VMS scoring. Use the same key
generator and solver as the two comparator reports.

Pass the input gate only when the source, projection, split, tokenizer, and
all code hashes match the manifest. Pass the solver gate only when the returned
map is total over fitted units, capacity-valid, and scored by the fixed integer
objective. A certified score below the planted-key score is an implementation
failure. An uncertified search is incomplete; do not convert it into a pass.

Keep the inherited exact-recovery gate from
`docs/plans/visual-homophonic-pilot.md` unchanged. This plan does not lower
its threshold or replace it with a source or provenance check. A test recovery
error can show objective ambiguity, lexicon coverage limits, or finite search
limits. It is not an implementation failure unless a certified solver violates
the planted objective. It still fails the recovery gate and keeps all VMS use
deferred. A completed search and a recovery pass are separate statuses.

A Celsus input pass, solver pass, or finite score does not authorize VMS use.
If a control has an input or solver failure, publish the failure label and keep
VMS use deferred. Any later VMS protocol must independently pass its frozen
reference and exact-recovery gates.

## Outputs and interpretation

Write private token streams, encrypted streams, key records, and fit records to
an ignored result directory. The public aggregate report may contain hashes,
counts, scores, rates, bounds, statuses, resource use, and split metadata. It
must not contain paragraph text, raw reference arrays, ciphertext arrays, or
complete candidate rows.

Compare the Celsus cold report with the frozen Latin and Italian cold reports.
Use descriptive tables only. Do not pool the three cells as independent
samples. Do not report a p-value or a confidence interval that treats Celsus,
LLCT, and Dante as independent author replicates.

A higher Celsus recovery rate means that this finite control fits this source
under the fixed token and split policy. It does not show that the VMS is Latin,
medical, or solved. A lower rate can result from source vocabulary, chapter
split drift, corrected spelling, Greek removal, Roman-numeral frequency, lexicon
coverage, objective ambiguity, or a resource limit. It does not show that the
VMS has no meaning or that Latin is impossible.

This run is descriptive regardless of its score. Do not apply a VMS model
based on this plan. A later VMS protocol must pass its own frozen reference
and exact-recovery gates. The Celsus result remains a genre control and is not
independent historical validation.

## Resource and stop rules

Run one process with one CPU worker. Use the existing cold budget and no retry.
Sample process resident memory every 0.25 seconds. If it reaches 7 GiB, allow
5 seconds for cleanup, then stop the process and label the run
`resource_abstain`. This is a user-space monitor. It is not a kernel memory
cap. Use a 1,500-second wall limit. Label hash or split errors as
`input_mismatch`, certified objective violations as `implementation_failure`,
and a complete run with an uncertified frontier as `incomplete_search`.

Do not tune the split, tokenizer, budget, or family after inspecting any
Celsus score. A changed rule requires a new version, manifest, and result.
