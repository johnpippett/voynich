"""Bounded threshold queries for finite homophonic lexicon problems.

The query asks whether one complete cipher-unit map reaches a fixed integer
hit score.  It does not estimate a posterior, prove a unique key, or return a
global optimum.  The problem object caches root candidates and one
``BitsetBound`` instance so repeated domain queries use the same objective.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
import hashlib
import heapq
import itertools
import json
from typing import Any
from types import MappingProxyType

from experiments.homophonic.bitset_bound import BitsetBound
from experiments.homophonic.solver import (
    _candidate_lists,
    _normalise_alphabet,
    _normalise_cipher_counts,
    _normalise_lexicon,
    _score_key,
    _validate_initial_key,
)


Word = str | tuple[str, ...]
Capacity = int | None


def _validate_capacity(capacity: Capacity) -> Capacity:
    """Validate the capacities implemented by the cached bound engine."""

    if capacity is None:
        return None
    if isinstance(capacity, bool) or not isinstance(capacity, int):
        raise ValueError("capacity must be 1, 2, or None")
    if capacity not in (1, 2):
        raise ValueError("capacity must be 1, 2, or None")
    return capacity


def _validate_target(target: int) -> int:
    if isinstance(target, bool) or not isinstance(target, int) or target < 0:
        raise ValueError("target must be a non-negative integer")
    return target


def _validate_node_budget(node_budget: int | None) -> int | None:
    if node_budget is None:
        return None
    if (
        isinstance(node_budget, bool)
        or not isinstance(node_budget, int)
        or node_budget < 0
    ):
        raise ValueError("node_budget must be a non-negative integer or None")
    return node_budget


def _normalise_symbol_order(
    symbol_order: Sequence[str] | None,
    cipher_symbols: tuple[str, ...],
    counts: Mapping[tuple[str, ...], int],
) -> tuple[str, ...]:
    if symbol_order is None:
        symbol_weights = {
            symbol: sum(
                weight for word, weight in counts.items() if symbol in word
            )
            for symbol in cipher_symbols
        }
        return tuple(
            sorted(
                cipher_symbols,
                key=lambda symbol: (-symbol_weights[symbol], symbol),
            )
        )
    try:
        values = tuple(symbol_order)
    except TypeError as exc:
        raise TypeError("symbol_order must be an iterable of ciphertext symbols") from exc
    if any(not isinstance(symbol, str) for symbol in values):
        raise ValueError("symbol_order must contain strings")
    if len(values) != len(set(values)) or set(values) != set(cipher_symbols):
        raise ValueError("symbol_order must contain every ciphertext symbol exactly once")
    return values


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _normalise_constraints(
    constraints: Mapping[str, str] | None,
    cipher_symbols: tuple[str, ...],
    alphabet: tuple[str, ...],
) -> dict[str, str]:
    if constraints is None:
        return {}
    if not isinstance(constraints, Mapping):
        raise TypeError("constraints must be a mapping")
    cipher_set = set(cipher_symbols)
    alphabet_set = set(alphabet)
    result: dict[str, str] = {}
    for cipher_symbol, plain_symbol in constraints.items():
        if not isinstance(cipher_symbol, str) or not isinstance(plain_symbol, str):
            raise ValueError("constraint symbols must be strings")
        if cipher_symbol not in cipher_set:
            raise ValueError("constraints contain a symbol absent from ciphertext")
        if plain_symbol not in alphabet_set:
            raise ValueError("constraint values must be in plaintext_alphabet")
        result[cipher_symbol] = plain_symbol
    return dict(sorted(result.items()))


def _normalise_forbidden_values(
    values: object,
    alphabet: tuple[str, ...],
) -> tuple[str, ...]:
    """Normalize one forbidden value collection without dropping symbols."""

    alphabet_set = set(alphabet)
    if isinstance(values, str):
        if values in alphabet_set:
            return (values,)
        # A string is also a convenient spelling for a set of one-character
        # alphabet symbols.  Reject mixed or unknown spellings explicitly.
        pieces = tuple(values)
    else:
        try:
            pieces = tuple(values)  # type: ignore[arg-type]
        except TypeError as exc:
            raise TypeError("forbidden values must be iterable") from exc
    if any(not isinstance(value, str) for value in pieces):
        raise ValueError("forbidden values must be strings")
    if any(value not in alphabet_set for value in pieces):
        raise ValueError("forbidden values must be in plaintext_alphabet")
    return tuple(sorted(set(pieces)))


def _normalise_forbidden(
    forbidden: Mapping[str, Iterable[str]] | None,
    cipher_symbols: tuple[str, ...],
    alphabet: tuple[str, ...],
) -> dict[str, tuple[str, ...]]:
    if forbidden is None:
        return {}
    if not isinstance(forbidden, Mapping):
        raise TypeError("forbidden must be a mapping")
    cipher_set = set(cipher_symbols)
    result: dict[str, tuple[str, ...]] = {}
    for cipher_symbol, values in forbidden.items():
        if not isinstance(cipher_symbol, str):
            raise ValueError("forbidden symbols must be strings")
        if cipher_symbol not in cipher_set:
            raise ValueError("forbidden contains a symbol absent from ciphertext")
        result[cipher_symbol] = _normalise_forbidden_values(values, alphabet)
    return dict(sorted(result.items()))


def _query_fingerprint(
    objective_domain_fingerprint: str,
    search_settings_fingerprint: str,
    target: int,
    constraints: Mapping[str, str],
    forbidden: Mapping[str, tuple[str, ...]],
    node_budget: int | None,
) -> str:
    return _digest(
        {
            "objective_domain_fingerprint": objective_domain_fingerprint,
            "search_settings_fingerprint": search_settings_fingerprint,
            "target": target,
            "constraints": [[key, value] for key, value in sorted(constraints.items())],
            "forbidden": [
                [key, list(values)] for key, values in sorted(forbidden.items())
            ],
            "node_budget": node_budget,
        }
    )


class ThresholdProblem:
    """Reusable finite-lexicon threshold problem.

    ``constraints`` are hard assignments for one query.  ``initial_key`` is a
    warm-start witness only.  It never restricts the root or the live frontier.
    The bound can ignore forbidden values for unassigned units, so it is loose
    but admissible.  Every generated key and every returned witness respects
    forbidden values.

    Normalized domain data is read-only after construction.  Build a new
    problem when the ciphertext, lexicon, alphabet, capacity, or branch order
    changes.
    """

    def __init__(
        self,
        ciphertext_counts: Mapping[Word, int],
        plaintext_lexicon: Iterable[Word],
        plaintext_alphabet: Iterable[str] | str,
        *,
        capacity: Capacity = 1,
        symbol_order: Sequence[str] | None = None,
    ) -> None:
        self._capacity = _validate_capacity(capacity)
        counts = _normalise_cipher_counts(ciphertext_counts)
        alphabet = _normalise_alphabet(plaintext_alphabet)
        lexicon, _raw_count, _unique_count, _rejected_count = _normalise_lexicon(
            plaintext_lexicon, alphabet
        )
        cipher_symbols = tuple(sorted({symbol for word in counts for symbol in word}))
        normalized_symbol_order = _normalise_symbol_order(
            symbol_order, cipher_symbols, counts
        )
        candidates = _candidate_lists(counts, lexicon, self._capacity)

        # Keep immutable or copied inputs.  Each query must be independent.
        self._ciphertext_counts = MappingProxyType(dict(counts))
        self._plaintext_lexicon = frozenset(lexicon)
        self._plaintext_alphabet = tuple(alphabet)
        self._cipher_symbols = cipher_symbols
        self._symbol_order = normalized_symbol_order
        root_candidates = {
            word: tuple(values) for word, values in sorted(candidates.items())
        }
        self._root_candidates = MappingProxyType(root_candidates)
        self._bound_engine = BitsetBound(
            self._ciphertext_counts,
            self._root_candidates,
            self._plaintext_alphabet,
            capacity=self._capacity,
        )

        fingerprint_payload = {
            "ciphertext_counts": [
                [list(word), weight]
                for word, weight in sorted(self._ciphertext_counts.items())
            ],
            "plaintext_lexicon": [
                list(word) for word in sorted(self._plaintext_lexicon)
            ],
            "plaintext_alphabet": list(self._plaintext_alphabet),
            "capacity": self._capacity,
        }
        self._problem_fingerprint = _digest(fingerprint_payload)
        self._search_settings_fingerprint = _digest(
            {
                "objective_domain_fingerprint": self._problem_fingerprint,
                "symbol_order": list(self._symbol_order),
            }
        )

    @property
    def capacity(self) -> Capacity:
        return self._capacity

    @property
    def ciphertext_counts(self) -> Mapping[tuple[str, ...], int]:
        return self._ciphertext_counts

    @property
    def plaintext_lexicon(self) -> frozenset[tuple[str, ...]]:
        return self._plaintext_lexicon

    @property
    def plaintext_alphabet(self) -> tuple[str, ...]:
        return self._plaintext_alphabet

    @property
    def cipher_symbols(self) -> tuple[str, ...]:
        return self._cipher_symbols

    @property
    def symbol_order(self) -> tuple[str, ...]:
        return self._symbol_order

    @property
    def root_candidates(self) -> Mapping[
        tuple[str, ...], tuple[tuple[str, ...], ...]
    ]:
        return self._root_candidates

    @property
    def problem_fingerprint(self) -> str:
        """Return the objective and normalized domain fingerprint."""

        return self._problem_fingerprint

    @property
    def search_settings_fingerprint(self) -> str:
        """Return the fingerprint for deterministic query branch settings."""

        return self._search_settings_fingerprint

    @property
    def bound_metadata(self) -> dict[str, int]:
        """Return construction metadata from the cached bound engine."""

        return self._bound_engine.metadata

    @property
    def root_bound(self) -> int:
        """Return the compatible-candidate upper bound for the empty map."""

        return self._bound_engine.root_bound

    def _validate_query_domains(
        self,
        constraints: Mapping[str, str] | None,
        forbidden: Mapping[str, Iterable[str]] | None,
    ) -> tuple[dict[str, str], dict[str, tuple[str, ...]]]:
        normalized_constraints = _normalise_constraints(
            constraints, self.cipher_symbols, self.plaintext_alphabet
        )
        normalized_forbidden = _normalise_forbidden(
            forbidden, self.cipher_symbols, self.plaintext_alphabet
        )
        return normalized_constraints, normalized_forbidden

    def _domain_impossible(
        self,
        constraints: Mapping[str, str],
        forbidden: Mapping[str, tuple[str, ...]],
    ) -> bool:
        usage = Counter(constraints.values())
        if self.capacity is not None and any(
            count > self.capacity for count in usage.values()
        ):
            return True
        if any(
            plain_symbol in forbidden.get(cipher_symbol, ())
            for cipher_symbol, plain_symbol in constraints.items()
        ):
            return True
        if self.capacity is not None and (
            self.capacity * len(self.plaintext_alphabet) < len(self.cipher_symbols)
        ):
            return True

        for cipher_symbol in self.symbol_order:
            if cipher_symbol in constraints:
                continue
            if not any(
                self.capacity is None or usage[plain_symbol] < self.capacity
                for plain_symbol in self.plaintext_alphabet
                if plain_symbol not in forbidden.get(cipher_symbol, ())
            ):
                return True
        return False

    def _complete_allowed(
        self,
        partial_key: Mapping[str, str],
        forbidden: Mapping[str, tuple[str, ...]],
    ) -> dict[str, str] | None:
        """Greedily complete a map, returning no witness on Hall failure."""

        key = dict(partial_key)
        usage = Counter(key.values())
        if self.capacity is not None and any(
            count > self.capacity for count in usage.values()
        ):
            return None
        for cipher_symbol in self.cipher_symbols:
            if cipher_symbol in key:
                continue
            for plain_symbol in self.plaintext_alphabet:
                if plain_symbol in forbidden.get(cipher_symbol, ()):
                    continue
                if self.capacity is not None and usage[plain_symbol] >= self.capacity:
                    continue
                key[cipher_symbol] = plain_symbol
                usage[plain_symbol] += 1
                break
            else:
                return None
        return dict(sorted(key.items()))

    def _result(
        self,
        *,
        status: str,
        target: int,
        constraints: Mapping[str, str],
        forbidden: Mapping[str, tuple[str, ...]],
        node_budget: int | None,
        nodes: int,
        frontier_upper: int,
        proof_kind: str,
        global_upper_bound: int | None = None,
        key: Mapping[str, str] | None,
        score: int | None,
        lower_bound: int | None,
        frontier_node_count: int,
        search_exhausted: bool,
        incumbent_key: Mapping[str, str] | None = None,
        incumbent_score: int | None = None,
        hit_type_count: int | None = None,
        pruned_nodes: int = 0,
    ) -> dict[str, Any]:
        normalized_key = None if key is None else dict(sorted(key.items()))
        normalized_incumbent = (
            None
            if incumbent_key is None
            else dict(sorted(incumbent_key.items()))
        )
        query_fingerprint = _query_fingerprint(
            self.problem_fingerprint,
            self.search_settings_fingerprint,
            target,
            constraints,
            forbidden,
            node_budget,
        )
        return {
            "status": status,
            "feasible": status == "feasible",
            "infeasible": status == "infeasible",
            "problem_fingerprint": self.problem_fingerprint,
            "objective_domain_fingerprint": self.problem_fingerprint,
            "search_settings_fingerprint": self.search_settings_fingerprint,
            "query_fingerprint": query_fingerprint,
            "query_target": target,
            "constraints": dict(sorted(constraints.items())),
            "forbidden": {
                symbol: list(values) for symbol, values in sorted(forbidden.items())
            },
            "node_budget": node_budget,
            "nodes": nodes,
            "pruned_nodes": pruned_nodes,
            "frontier_node_count": frontier_node_count,
            "frontier_upper": frontier_upper,
            "lower_bound": lower_bound,
            "upper_bound": max(
                frontier_upper,
                incumbent_score if incumbent_score is not None else 0,
                global_upper_bound if global_upper_bound is not None else 0,
            ),
            "proof_kind": proof_kind,
            "search_exhausted": search_exhausted,
            "capacity": self.capacity,
            "bound_engine": "BitsetBound",
            "symbol_order": list(self.symbol_order),
            "config": {
                "objective": "integer weighted exact finite-lexicon word hits",
                "query": "exists a complete feasible key with score >= target",
                "capacity": self.capacity,
                "bound_engine": "BitsetBound",
                "symbol_order": list(self.symbol_order),
                "forbidden_bound_policy": (
                    "forbidden values are ignored for unassigned units in the "
                    "admissible upper bound"
                ),
                "initial_key_role": "warm-start witness only",
            },
            "bound_metadata": self.bound_metadata,
            "key": normalized_key,
            "score": score,
            "hit_type_count": hit_type_count,
            "incumbent_key": normalized_incumbent,
            "incumbent_score": incumbent_score,
            "interpretation": (
                "This is a threshold witness query over the supplied finite "
                "lexicon. It does not claim a global optimum or key uniqueness."
            ),
        }

    def query(
        self,
        target: int,
        *,
        constraints: Mapping[str, str] | None = None,
        forbidden: Mapping[str, Iterable[str]] | None = None,
        node_budget: int | None = None,
        initial_key: Mapping[str, str] | None = None,
    ) -> dict[str, Any]:
        """Ask whether a constrained complete key reaches ``target``.

        A finite ``node_budget`` can leave a live frontier.  In that case the
        method returns ``unknown``.  It returns ``infeasible`` only for a
        domain impossibility, an exhausted search, or an upper bound below the
        target.  ``initial_key`` can improve a witness but never prunes search.
        """

        target = _validate_target(target)
        node_budget = _validate_node_budget(node_budget)
        normalized_constraints, normalized_forbidden = self._validate_query_domains(
            constraints, forbidden
        )
        initial = _validate_initial_key(
            initial_key,
            self.cipher_symbols,
            self.plaintext_alphabet,
            self.capacity,
        )
        for cipher_symbol, plain_symbol in normalized_constraints.items():
            if cipher_symbol in initial and initial[cipher_symbol] != plain_symbol:
                raise ValueError("initial_key conflicts with constraints")
        for cipher_symbol, plain_symbol in initial.items():
            if plain_symbol in normalized_forbidden.get(cipher_symbol, ()):
                raise ValueError("initial_key uses a forbidden value")

        if self._domain_impossible(normalized_constraints, normalized_forbidden):
            return self._result(
                status="infeasible",
                target=target,
                constraints=normalized_constraints,
                forbidden=normalized_forbidden,
                node_budget=node_budget,
                nodes=0,
                frontier_upper=0,
                proof_kind="domain_impossibility",
                key=None,
                score=None,
                lower_bound=None,
                frontier_node_count=0,
                search_exhausted=True,
            )

        if not self.cipher_symbols:
            if target == 0:
                return self._result(
                    status="feasible",
                    target=target,
                    constraints=normalized_constraints,
                    forbidden=normalized_forbidden,
                    node_budget=node_budget,
                    nodes=0,
                    frontier_upper=0,
                    proof_kind="witness",
                    key={},
                    score=0,
                    lower_bound=0,
                    frontier_node_count=0,
                    search_exhausted=True,
                    incumbent_key={},
                    incumbent_score=0,
                    hit_type_count=0,
                )
            return self._result(
                status="infeasible",
                target=target,
                constraints=normalized_constraints,
                forbidden=normalized_forbidden,
                node_budget=node_budget,
                nodes=0,
                frontier_upper=0,
                proof_kind="frontier_upper_below_target",
                key=None,
                score=None,
                lower_bound=0,
                frontier_node_count=0,
                search_exhausted=True,
                incumbent_key={},
                incumbent_score=0,
                hit_type_count=0,
            )

        # The warm-start map and the unconstrained greedy map are both
        # heuristics.  Neither one becomes a root restriction.
        best_key: dict[str, str] | None = None
        best_score: int | None = None
        best_hit_types: int | None = None
        root_upper = self._bound_engine.bound(normalized_constraints)

        def consider(candidate_key: Mapping[str, str] | None) -> bool:
            nonlocal best_key, best_score, best_hit_types
            if candidate_key is None:
                return False
            score, hit_types = _score_key(
                candidate_key,
                self.ciphertext_counts,
                set(self.plaintext_lexicon),
            )
            tie = tuple(candidate_key[symbol] for symbol in self.cipher_symbols)
            best_tie = (
                None
                if best_key is None
                else tuple(best_key[symbol] for symbol in self.cipher_symbols)
            )
            if (
                best_key is None
                or score > best_score  # type: ignore[operator]
                or (score == best_score and tie < best_tie)  # type: ignore[operator]
            ):
                best_key = dict(sorted(candidate_key.items()))
                best_score = score
                best_hit_types = hit_types
            return score >= target

        warm_start = dict(normalized_constraints)
        warm_start.update(initial)
        if consider(self._complete_allowed(warm_start, normalized_forbidden)):
            return self._result(
                status="feasible",
                target=target,
                constraints=normalized_constraints,
                forbidden=normalized_forbidden,
                node_budget=node_budget,
                nodes=0,
                frontier_upper=root_upper,
                global_upper_bound=root_upper,
                proof_kind="witness",
                key=best_key,
                score=best_score,
                lower_bound=best_score,
                frontier_node_count=1,
                search_exhausted=False,
                incumbent_key=best_key,
                incumbent_score=best_score,
                hit_type_count=best_hit_types,
            )
        if consider(self._complete_allowed(normalized_constraints, normalized_forbidden)):
            return self._result(
                status="feasible",
                target=target,
                constraints=normalized_constraints,
                forbidden=normalized_forbidden,
                node_budget=node_budget,
                nodes=0,
                frontier_upper=root_upper,
                global_upper_bound=root_upper,
                proof_kind="witness",
                key=best_key,
                score=best_score,
                lower_bound=best_score,
                frontier_node_count=1,
                search_exhausted=False,
                incumbent_key=best_key,
                incumbent_score=best_score,
                hit_type_count=best_hit_types,
            )

        if root_upper < target:
            return self._result(
                status="infeasible",
                target=target,
                constraints=normalized_constraints,
                forbidden=normalized_forbidden,
                node_budget=node_budget,
                nodes=0,
                frontier_upper=root_upper,
                global_upper_bound=root_upper,
                proof_kind="frontier_upper_below_target",
                key=None,
                score=None,
                lower_bound=best_score if best_score is not None else 0,
                frontier_node_count=0,
                search_exhausted=True,
                incumbent_key=best_key,
                incumbent_score=best_score,
                hit_type_count=best_hit_types,
            )

        remaining_order = tuple(
            symbol
            for symbol in self.symbol_order
            if symbol not in normalized_constraints
        )
        frontier: list[
            tuple[int, tuple[str, ...], int, int, tuple[tuple[str, str], ...]]
        ] = []
        sequence = itertools.count()

        def push_node(key: Mapping[str, str], depth: int, upper: int) -> None:
            prefix = tuple(key[symbol] for symbol in remaining_order[:depth])
            heapq.heappush(
                frontier,
                (
                    -upper,
                    prefix,
                    next(sequence),
                    depth,
                    tuple(sorted(key.items())),
                ),
            )

        push_node(normalized_constraints, 0, root_upper)
        nodes = 0
        pruned_nodes = 0
        pruned_upper_bound = 0

        while frontier and (node_budget is None or nodes < node_budget):
            neg_upper, _prefix, _sequence, depth, key_items = heapq.heappop(frontier)
            node_upper = -neg_upper
            key = dict(key_items)
            nodes += 1
            if node_upper < target:
                pruned_nodes += 1
                pruned_upper_bound = max(pruned_upper_bound, node_upper)
                continue

            if depth == len(remaining_order):
                if consider(key):
                    live_upper = max(
                        (entry[0] * -1 for entry in frontier),
                        default=0,
                    )
                    return self._result(
                        status="feasible",
                        target=target,
                        constraints=normalized_constraints,
                        forbidden=normalized_forbidden,
                        node_budget=node_budget,
                        nodes=nodes,
                        frontier_upper=live_upper,
                        global_upper_bound=max(
                            pruned_upper_bound,
                            live_upper,
                            node_upper,
                            best_score if best_score is not None else 0,
                        ),
                        proof_kind="witness",
                        key=best_key,
                        score=best_score,
                        lower_bound=best_score,
                        frontier_node_count=len(frontier),
                        search_exhausted=not frontier,
                        incumbent_key=best_key,
                        incumbent_score=best_score,
                        hit_type_count=best_hit_types,
                        pruned_nodes=pruned_nodes,
                    )
                continue

            branch_symbol = remaining_order[depth]
            usage = Counter(key.values())
            for plain_symbol in self.plaintext_alphabet:
                if plain_symbol in normalized_forbidden.get(branch_symbol, ()):
                    continue
                if self.capacity is not None and usage[plain_symbol] >= self.capacity:
                    continue
                child = dict(key)
                child[branch_symbol] = plain_symbol
                child_upper = self._bound_engine.bound(child)
                if child_upper < target:
                    pruned_nodes += 1
                    pruned_upper_bound = max(pruned_upper_bound, child_upper)
                    continue
                push_node(child, depth + 1, child_upper)

        if frontier:
            frontier_upper = -frontier[0][0]
            status = "unknown"
            proof_kind = "live_frontier"
            search_exhausted = False
        else:
            frontier_upper = 0
            status = "infeasible"
            proof_kind = "search_exhausted_no_witness"
            search_exhausted = True
        return self._result(
            status=status,
            target=target,
            constraints=normalized_constraints,
            forbidden=normalized_forbidden,
            node_budget=node_budget,
            nodes=nodes,
            frontier_upper=frontier_upper,
            global_upper_bound=max(
                pruned_upper_bound,
                frontier_upper,
                best_score if best_score is not None else 0,
            ),
            proof_kind=proof_kind,
            key=None,
            score=None,
            # Zero is the objective floor when no complete heuristic witness
            # was found.  It keeps an unknown result a non-negative interval.
            lower_bound=(best_score if best_score is not None else 0),
            frontier_node_count=len(frontier),
            search_exhausted=search_exhausted,
            incumbent_key=best_key,
            incumbent_score=best_score,
            hit_type_count=best_hit_types,
            pruned_nodes=pruned_nodes,
        )


def build_threshold_problem(
    ciphertext_counts: Mapping[Word, int],
    plaintext_lexicon: Iterable[Word],
    plaintext_alphabet: Iterable[str] | str,
    *,
    capacity: Capacity = 1,
    symbol_order: Sequence[str] | None = None,
) -> ThresholdProblem:
    """Build a reusable threshold problem and cache its compatible candidates."""

    return ThresholdProblem(
        ciphertext_counts,
        plaintext_lexicon,
        plaintext_alphabet,
        capacity=capacity,
        symbol_order=symbol_order,
    )


def query_threshold(
    problem: ThresholdProblem,
    target: int,
    *,
    constraints: Mapping[str, str] | None = None,
    forbidden: Mapping[str, Iterable[str]] | None = None,
    node_budget: int | None = None,
    initial_key: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Run one threshold query against a reusable problem."""

    if not isinstance(problem, ThresholdProblem):
        raise TypeError("problem must be a ThresholdProblem")
    return problem.query(
        target,
        constraints=constraints,
        forbidden=forbidden,
        node_budget=node_budget,
        initial_key=initial_key,
    )


__all__ = ["ThresholdProblem", "build_threshold_problem", "query_threshold"]
