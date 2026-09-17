# Exact lexical local search

`lexical_local_search` improves a complete cipher-unit map under a finite dictionary objective.
It checks each legal single-unit reassignment and each two-unit swap.
It accepts the largest positive score change. Equal scores use the smallest complete map in sorted unit order.

Each move changes only word types that contain an affected unit.
The implementation verifies each accepted move with a complete score calculation.
Capacity limits restrict how many cipher units can map to each plaintext letter.

`move_budget` limits accepted improving moves. A zero budget does not inspect a neighborhood.
The final map gives a feasible lower bound. It does not prove a global optimum or a unique key.

Use `trace_mode="summary"` for larger inputs. This mode omits the complete map for each rejected neighbor.
It retains aggregate counts and accepted move records. Keep these records private when they contain source text.

Read the [independent review](REVIEW.md) and [development protocol](../../docs/plans/homophonic-search-development-v1.md).
