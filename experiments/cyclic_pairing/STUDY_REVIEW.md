# Cyclic pairing study review

Review date: 2026-09-17.

This review covers synthetic unit streams only. It does not load a reference
corpus or the Voynich manuscript. It does not run a model or a control stream.

## Reviewed snapshot

- [`study.py`](study.py), SHA-256 `bdf9da11293e32e0483f55b100153ca49f4822efa0021541c116143f47022be3`;
- [`test_study.py`](test_study.py), SHA-256 `b53f50e74c454d36fdf8ce85774ff31dc9ca4d02bffc103cd65f080b752af1fd`;
- [`run_controls.py`](run_controls.py), SHA-256 `b45b8b5ce82a73236a691350dc7e633c2de6cd6e801d3791a5e65b6f5409772a`;
- [`test_run_controls.py`](test_run_controls.py), SHA-256 `9b5a32fc6439cf4c223d328a49c193601d724ffcc1fe7de0517138b3bc88f2c8`;
- [`__init__.py`](__init__.py), SHA-256 `34b9b19317fdaea3e3b99f51d5c45db120c5eae6ac91068aaf7369d8df6ce00b`;
- [`pairing.py`](pairing.py), SHA-256 `da9c89b4738d0dde959a3c730111dee864c05cd3e3b20932b2b8a3f30a57da95`;
- [`forced.py`](forced.py), SHA-256 `3f3a4fc450b5921905b8931310379d8361a6ca0b8d2989b8b8e939ddbc8d76a4`;
- [`WRAPPER_REVIEW.md`](WRAPPER_REVIEW.md), SHA-256 `0f0087bcd6e57f1a0c4231d3fdb1ef32badb923d1d4bf385d4fa6363273c8742`;
- [`cyclic-pairing-control-v1.md`](../../docs/plans/cyclic-pairing-control-v1.md), SHA-256 `6da0d8b862dacfb90b3255bb5df4212d180052729f2d9170bc8ea2e6e30c3310`.

## Review result

The current implementation has no remaining blocking defect in the study or
wrapper gates reviewed here. The final reported synthetic gate has 53 passing
tests. The updated plan hash is recorded above. The external pre-run freeze
remains a required gate before any control stream runs.

This review does not create a numeric result. A real run must still pass the
freeze, source, stream, resource, and output checks in the protocol.

## Resolved findings

The earlier review found four study-side gaps and wrapper validation gaps.
The current snapshot addresses them as follows:

1. The child checks the expected encrypted validation-stream hash before it
   writes `input.json` or builds the graph. The wrapper checks the same hash.
2. The child hashes the raw freeze record and rejects missing or invalid
   source, code, and test hash maps. The wrapper requires the freeze runtime
   fields and the reviewed parameter and output shape.
3. The child compares the outer and repeated full matching searches. It checks
   status, witness count, node count, node budget, and selected witness.
4. The child rejects a missing planted pair, an orientation mismatch, an
   invalid matching status, or a forced edge outside the planted pair set.
   The wrapper requires the complete planted pair set, zero orientation
   mismatches, a unique witness equal to that set, and consistent forced-edge
   evidence.

The wrapper now rejects malformed witnesses, duplicate or incomplete unit
pairs, invalid edge-query status, inconsistent category counts, and a forced
status that disagrees with the original matching status. It also rejects a
unique diagnostic witness with incomplete control-pair overlap and a record
with a wrong validation hash. A failed child diagnostic becomes an
implementation-failure record and cannot pass the numeric-validity check.

## Confirmed safeguards

The study uses the fixed `c00` through `c51` inventory and full matching
scope. It gives the matcher a ciphertext validation partition only. It does
not pass plaintext, a lexicon, a fitted key, or the planted pairing to the
pairing or forced-edge functions.

The study writes `input.json`, then `pairing.json`, then the known-control
diagnostic. It refuses to overwrite an existing output record. Public records
contain hashes, counts, unit pairs, and status data. They do not contain raw
words, plaintext letters, or a key.

The forced-edge record keeps `forced`, `not_forced`, and `unknown` separate.
It records the common node budget, query status, witness data, skipped queries,
and category totals. The wrapper enforces the 26-query limit and validates the
evidence before it accepts numeric output.

## Scope and limits

These checks establish the control procedure and its record safeguards. They
do not establish a language property, a plaintext, a translation, or a
Voynich interpretation. A complete or unique unit matching does not identify
letter names.

The review used synthetic tests only. It did not verify a real reference
stream, resource limit event, or published numeric result. The external
freeze must bind the final files, runtime, source inputs, output paths, and
resource limits before the runner starts.
