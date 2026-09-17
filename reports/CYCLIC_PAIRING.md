# Cyclic pairing control results

The ciphertext-only method identifies all 23 observed Latin pairs.
It identifies 21 forced Italian pairs, but other observed Italian pairs remain ambiguous.
Neither result assigns plaintext letters or supplies a manuscript reading.

## Fixed experiment

The [protocol](../docs/plans/cyclic-pairing-control-v1.md) uses the inspected `cap2` controls with seed `7000`.
Each of 26 letters cycles through two distinct cipher units across word boundaries.
The run uses one complete validation stream per corpus and a declared inventory of 52 units.
The pair search receives ciphertext units only. It receives no lexicon, plaintext words, or planted pairing.
The known-key checks occur after the pairing record is saved.

The corrected run used commit `6c007385d758a91bb230c92d69ff8bc50f59f709`.
Its [freeze manifest](../experiments/cyclic_pairing/freeze-v1.json) has SHA-256
`66c2cdeb461278804ff3be16d592940711a450a33ac8db7f46e12d38c8eca12b`.
The run completed both corpora with exit code zero.
The [supervision record](cyclic-pairing-control-v1/supervision.json) records the fixed limits and output hashes.

## Pairing results

| Measurement | Latin LLCT | Old Italian |
| --- | ---: | ---: |
| Validation words | 19,969 | 31,681 |
| Cipher unit tokens | 110,777 | 130,576 |
| Observed units | 46 | 47 |
| Unseen units | 6 | 5 |
| Compatible graph edges | 44 | 66 |
| Full-matching status | Multiple | Multiple |
| Witnesses saved by the bounded search | 2 | 2 |
| Forced observed-observed pairs | 23 | 21 |
| Selected observed-observed pairs proved non-forced | 0 | 2 |
| Unknown edge queries | 0 | 0 |

Each original search used 27 branch nodes and retained two full witnesses.
Each corpus then completed 26 edge-removal queries with no skipped query.
The query classifications apply to the selected witness edges. They do not classify every graph edge individually.
All 26 planted control pairs remained graph edges. All comparable cycle orientations agreed with the control emitter.
These last two measurements are post-pairing diagnostics. They did not select a witness.

The aggregate records contain graph counts, witnesses, edge-query evidence, and source hashes:

- Latin: [input](cyclic-pairing-control-v1/latin_llct/input.json), [pairing](cyclic-pairing-control-v1/latin_llct/pairing.json), [diagnostics](cyclic-pairing-control-v1/latin_llct/diagnostics.json).
- Italian: [input](cyclic-pairing-control-v1/italian_old/input.json), [pairing](cyclic-pairing-control-v1/italian_old/pairing.json), [diagnostics](cyclic-pairing-control-v1/italian_old/diagnostics.json).

## Independent enumeration

A [separate calculation](../scripts/verify_cyclic_pairing_independently.py) rebuilt the graphs from cipher-unit occurrence positions.
It used its own exhaustive matching enumerator. It did not import the pairing or forced-edge implementation.
The source loader and control emitter remain shared dependencies.
The calculation verified source hashes, graph counts, reported witnesses, forced pairs, and alternative witnesses.
Its diagnostic-record check verifies consistency; it does not independently repeat the planted-key orientation calculation.

| Independent result | Latin LLCT | Old Italian |
| --- | ---: | ---: |
| Complete full matchings | 15 | 945 |
| Distinct observed pair relations | 1 | 26 |
| Forced pairs | 23 | 21 |
| Units left after forced pairs are removed | 6 | 10 |
| Edges among those remaining units | 15 | 45 |
| Exhaustive search nodes | 44 | 1,354 |

Both searches exhausted their graph within the separate 1,000,000-node limit.
The [audit receipt](cyclic-pairing-control-v1/independent-audit.json) contains the complete measurements and checks.

In Latin, the remaining six units are unseen. Every pair among them is compatible.
Their 15 complete pairings leave the observed relation unchanged.
Thus the 46 observed units have one fixed division into 23 pairs, while unseen pair identities remain unresolved.

In Italian, five observed units and five unseen units remain after the 21 forced pairs are removed.
Every pair among these ten units is compatible. Their 945 full completions give 26 observed relations.
This ambiguity includes observed units; it is not confined to unseen pairs.
The fixed [quotient recovery plan](../docs/plans/cyclic-quotient-recovery-v1.md) must therefore abstain on Italian.
A later Latin run can test the class-to-letter search after its implementation freeze.

## Replay and failed attempt

A fresh anonymous public checkout reproduced all seven corrected output files byte for byte.
The [replay receipt](cyclic-pairing-control-v1/replay-verification.json) records the commit, commands, hashes, and return codes.
The checkout had no tracked changes after the run. The new public supervision file was untracked, as expected.

The first attempt used commit `2995a6ad80e8d769a4145ba13a15e521d4733831`.
A copied Latin stream hash contained one incorrect character. The Latin child stopped before writing input or pairing evidence.
The Italian child completed. The [first receipt](cyclic-pairing-control-v1/attempt-1/supervision.json) and its Italian records remain preserved.
The [initial freeze](../experiments/cyclic_pairing/freeze-v1-initial.json) also remains preserved.

The correction changed only the copied pin, its regression test, and related protocol records.
The prior Latin report, source text, emitter, pairing method, seed, and budgets did not change.
All 54 cyclic tests passed before the corrected run.
The [correction audit](../experiments/cyclic_pairing/STUDY_REVIEW.md#final-pin-correction-audit) records this test count and the corrected file hashes.

## Reproduction

Use a fresh checkout of the corrected pre-result commit:

```sh
git checkout --detach 6c007385d758a91bb230c92d69ff8bc50f59f709
python scripts/fetch_reference_sources.py
python -m experiments.cyclic_pairing.run_controls
```

Use a fresh checkout because the wrapper refuses existing outputs, including the published supervision path.
The source-fetch command verifies the pinned downloads. The control wrapper does not use the network.

## Limits

The results concern the exact deterministic control emitter and two previously inspected validation streams.
They are development results, not blind replication on new keys or new works.
A fixed pair relation is not a plaintext-letter map. A compatible graph does not establish a historical encoding method.
No manuscript stream was used in this experiment. No original recovery gate has been changed.
