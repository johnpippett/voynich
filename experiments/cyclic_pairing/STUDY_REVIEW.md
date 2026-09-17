# Cyclic pairing study review

Review date: 2026-09-17.

This review covers synthetic unit streams only. It does not load a reference
corpus or the Voynich manuscript. It does not run a model or a control stream.

## Reviewed snapshot

- [`study.py`](study.py), SHA-256 `73f18f96627d47d5a8d02e7499af726d69f0bc5f65c825bfc4b61b756b7db0b3`;
- [`test_study.py`](test_study.py), SHA-256 `b53f50e74c454d36fdf8ce85774ff31dc9ca4d02bffc103cd65f080b752af1fd`;
- [`run_controls.py`](run_controls.py), SHA-256 `37016a443dda3e042be58fbddcf858f896d42246f60cbd3c17a3e9985b98abab`;
- [`test_run_controls.py`](test_run_controls.py), SHA-256 `9e98b99fbba44429a0f023e6d6fefa3b70634102a84f9b4e8cad83f379fdf63c`;
- [`__init__.py`](__init__.py), SHA-256 `34b9b19317fdaea3e3b99f51d5c45db120c5eae6ac91068aaf7369d8df6ce00b`;
- [`pairing.py`](pairing.py), SHA-256 `da9c89b4738d0dde959a3c730111dee864c05cd3e3b20932b2b8a3f30a57da95`;
- [`forced.py`](forced.py), SHA-256 `3f3a4fc450b5921905b8931310379d8361a6ca0b8d2989b8b8e939ddbc8d76a4`;
- [`WRAPPER_REVIEW.md`](WRAPPER_REVIEW.md), SHA-256 `0f0087bcd6e57f1a0c4231d3fdb1ef32badb923d1d4bf385d4fa6363273c8742`;
- [`cyclic-pairing-control-v1.md`](../../docs/plans/cyclic-pairing-control-v1.md), SHA-256 `4df185f2f56b7e9dd8721cdd7b996c16aeb6f1ba49d0b6abce13f60db99823c6`.

## Review result

The current implementation has no remaining blocking defect in the study or
wrapper gates reviewed here. The final reported synthetic gate has 54 passing
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

## Final pin correction audit

The first control attempt stopped the Latin child before it wrote `input.json`.
The cause was a one-character Latin stream pin error. The Italian child
completed under the initial freeze, but the two-corpus attempt was incomplete.

The prior Latin report remains unchanged. Its report hash is
`923dba00df53ff05ca88e91362ea44c693d66b8f0824071d85cc5b0d984ba77e`, and its
`cipher_validation` value is
`eb03e98b086b9f8bc883f349afaee968bfeaeee8c95be5f66bec320e54b419b2`.
The failed code used `...b9b8...` at one position. The corrected study,
wrapper, and protocol now use the report value. The Italian pin matched its
prior report. A static audit found no other pin mismatch.

The corrected study SHA-256 is
`73f18f96627d47d5a8d02e7499af726d69f0bc5f65c825bfc4b61b756b7db0b3`.
The corrected wrapper SHA-256 is
`37016a443dda3e042be58fbddcf858f896d42246f60cbd3c17a3e9985b98abab`.
The corrected wrapper-test SHA-256 is
`9e98b99fbba44429a0f023e6d6fefa3b70634102a84f9b4e8cad83f379fdf63c`.
The corrected protocol SHA-256 is
`4df185f2f56b7e9dd8721cdd7b996c16aeb6f1ba49d0b6abce13f60db99823c6`.
The corrected freeze SHA-256 is
`66c2cdeb461278804ff3be16d592940711a450a33ac8db7f46e12d38c8eca12b`.
The initial freeze remains preserved at
[`freeze-v1-initial.json`](freeze-v1-initial.json), SHA-256
`271df785f0df13415dfdaec44ce91b7b3ba9e317d052ec904914ad89ca9b3981`.
The initial receipt directory remains at
[`attempt-1`](../../reports/cyclic-pairing-control-v1/attempt-1).

The final synthetic gate reports 54 passing tests after the pin correction.
This audit did not rerun a reference stream or change source code.
