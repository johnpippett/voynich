# Local cyclic obstructions

Status: synthetic theory note. Date: 2026-09-17.

This note gives small falsification checks for one fixed cyclic emitter. It
uses no Voynich data and gives no meaning to any glyph or word.

## Model contract

Declare the atomic cipher units, mapping family, and value `k` before reading
a stream. The exact unit-to-letter map can remain unknown.
Each plaintext letter has exactly `k` distinct cipher
units, where `k >= 2`. Unit sets for different letters are disjoint. The
emitter uses the next unit in a fixed cycle for each occurrence of that letter.
The stream order is preserved.

Divide input into predeclared uninterrupted atomic segments. A segment has no
reset, deleted symbol, uncertain symbol, or unknown unit boundary. A declared
reset starts a new cycle offset. Word or line breaks do not reset the cycle
unless the protocol says so. Do not change these segment or reset settings
after the stream is read.

## Adjacent-repeat certificate

The two-unit stream `[a, a]` inside one uninterrupted segment is impossible
under this model. If both positions come from the same plaintext letter, the
cycle advances to a different unit because `k >= 2`. If they come from
different letters, disjoint unit sets forbid the same unit in both letters.

This is a local certificate. It needs no lexicon, frequency model, or global
key search. A longer stream has the same certificate whenever two equal
atomic units are consecutive within one declared uninterrupted segment.

The certificate does not apply across a declared reset. The same first cycle
unit can occur at the start of two separate segments. It also does not apply
when an emitted unit may be missing, uncertain, or hidden by an unknown
unitization. A missing intervening emission can repair visible adjacency.

## Binary edge certificate

For `k = 2`, test a candidate pair `(u, v)` by projecting one uninterrupted
segment onto `u` and `v`. The projection must alternate. If two consecutive
occurrences of `u` have no `v` between them in the original segment, the
projection contains `u, u`; therefore `(u, v)` is impossible.

This gives a graph constraint for every candidate mate `v`. Other units between
the two `u` occurrences do not help, because projection removes them. A
candidate edge is absent when this check fails in any segment, or when the two
segments require incompatible fixed cycle starts.

If every declared candidate mate for `u` fails an exhaustive check, the fixed
binary emitter fails for that unitization and segment policy. If only some
edges fail, the result is a negative graph certificate. An edge that was not
found during a bounded search is unknown, not absent.

For `k > 2`, the same idea gives a class constraint: consecutive occurrences
of `u` in the projection onto a proposed `k`-unit class cannot be equal. A
complete test must also verify the fixed cycle order and the count of each
class member. The binary edge check alone is not a complete `k`-ary test.

## Limits of a rejection

A rejection applies only to the tested atomic unitization, uninterrupted
segments, reset locations, and emitter family. It can reject that control
model without rejecting all homophonic models. In particular, a solver with
an at-most-two capacity can allow one unit to represent a letter and does not
model cyclic alternation. It has a different hypothesis and is not falsified
by this certificate.

Future observations from raw EVA or visual groups must state the tested
unitization and segment policy. A failed repeated-unit check can reject that
bundle choice or fixed cyclic emitter. It cannot prove a translation, a
language, or a meaning, and it cannot reject every other homophonic model.
