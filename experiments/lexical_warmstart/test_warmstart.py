"""Independent tests for the exact lexical local-search warm start."""

from __future__ import annotations

from collections import Counter
from itertools import combinations
import pathlib
import random
import sys
import unittest


PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from experiments.lexical_warmstart.warmstart import (  # noqa: E402
    lexical_local_search,
)


Word = tuple[str, ...]


def _word(value: str | Word) -> Word:
    return tuple(value) if isinstance(value, str) else value


def _normalise_counts(counts: dict[str | Word, int]) -> dict[Word, int]:
    normalized: dict[Word, int] = {}
    for raw_word, weight in counts.items():
        word = _word(raw_word)
        normalized[word] = normalized.get(word, 0) + weight
    return dict(sorted(normalized.items()))


def _normalise_lexicon(lexicon: set[str | Word], alphabet: tuple[str, ...]) -> set[Word]:
    alphabet_set = set(alphabet)
    return {
        _word(word)
        for word in lexicon
        if set(_word(word)).issubset(alphabet_set)
    }


def _direct_score(
    key: dict[str, str],
    counts: dict[Word, int],
    lexicon: set[Word],
) -> int:
    return sum(
        weight
        for word, weight in counts.items()
        if tuple(key[symbol] for symbol in word) in lexicon
    )


def _key_tuple(key: dict[str, str], symbols: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(key[symbol] for symbol in symbols)


def _expected_moves(
    key: dict[str, str],
    symbols: tuple[str, ...],
    alphabet: tuple[str, ...],
    capacity: int | None,
) -> list[tuple[str, tuple[str, ...], tuple[str, ...], tuple[str, ...]]]:
    usage = Counter(key.values())
    moves: list[tuple[str, tuple[str, ...], tuple[str, ...], tuple[str, ...]]] = []
    for symbol in symbols:
        old_value = key[symbol]
        for new_value in alphabet:
            if new_value == old_value:
                continue
            if capacity is not None and usage[new_value] >= capacity:
                continue
            moves.append(("reassign", (symbol,), (old_value,), (new_value,)))
    for left, right in combinations(symbols, 2):
        left_value = key[left]
        right_value = key[right]
        if left_value == right_value:
            continue
        moves.append(
            (
                "swap",
                (left, right),
                (left_value, right_value),
                (right_value, left_value),
            )
        )
    return moves


def _record_signature(record: dict[str, object]):
    return (
        record["kind"],
        tuple(record["units"]),
        tuple(record["from_values"]),
        tuple(record["to_values"]),
    )


class LexicalWarmStartTests(unittest.TestCase):
    def test_incident_deltas_and_final_score_match_direct_recomputation(self) -> None:
        counts = {
            ("x", "x"): 3,
            ("x", "y"): 2,
            ("y", "z"): 5,
            ("z",): 1,
        }
        lexicon = {"aa", "ab", "bc", "a", "b", "c"}
        alphabet = ("a", "b", "c")
        result = lexical_local_search(
            counts,
            lexicon,
            alphabet,
            capacity=2,
            initial_key={"x": "a", "y": "b", "z": "c"},
            move_budget=2,
        )
        normalized_counts = _normalise_counts(counts)
        usable_lexicon = _normalise_lexicon(lexicon, alphabet)
        symbols = tuple(sorted({symbol for word in normalized_counts for symbol in word}))

        self.assertLessEqual(result["accepted_move_count"], 2)
        self.assertFalse(result["score_certified"])
        self.assertEqual(
            result["score"],
            _direct_score(result["key"], normalized_counts, usable_lexicon),
        )
        for record in result["evaluations"]:
            before = record["key_before"]
            candidate = record["candidate_key"]
            before_score = _direct_score(before, normalized_counts, usable_lexicon)
            after_score = _direct_score(candidate, normalized_counts, usable_lexicon)
            self.assertEqual(record["score_before"], before_score)
            self.assertEqual(record["score_after"], after_score)
            self.assertEqual(record["delta"], after_score - before_score)
            self.assertEqual(
                record["score_after"], record["score_before"] + record["delta"]
            )
            self.assertEqual(
                _record_signature(record),
                next(
                    signature
                    for signature in _expected_moves(
                        before, symbols, alphabet, 2
                    )
                    if signature == _record_signature(record)
                ),
            )
            usage = Counter(candidate.values())
            self.assertEqual(set(candidate), set(symbols))
            self.assertTrue(all(value in alphabet for value in candidate.values()))
            self.assertTrue(all(count <= 2 for count in usage.values()))

    def test_best_positive_move_uses_lexical_tiebreak(self) -> None:
        result = lexical_local_search(
            {("x", "y"): 1},
            {"ab", "ba"},
            "ab",
            capacity=2,
            initial_key={"x": "b", "y": "b"},
            move_budget=1,
        )

        self.assertEqual(result["key"], {"x": "a", "y": "b"})
        self.assertEqual(result["score"], 1)
        self.assertEqual(result["accepted_move_count"], 1)
        selected = [record for record in result["evaluations"] if record["selected"]]
        self.assertEqual(len(selected), 1)
        self.assertEqual(selected[0]["kind"], "reassign")
        self.assertEqual(selected[0]["units"], ["x"])

    def test_capacity_one_swap_can_improve_when_reassignment_is_full(self) -> None:
        result = lexical_local_search(
            {("x", "y"): 1},
            {"ab"},
            "ab",
            capacity=1,
            initial_key={"x": "b", "y": "a"},
            move_budget=1,
        )

        self.assertEqual(result["key"], {"x": "a", "y": "b"})
        self.assertEqual(result["score"], 1)
        accepted = result["accepted_moves"]
        self.assertEqual(len(accepted), 1)
        self.assertEqual(accepted[0]["kind"], "swap")

    def test_budget_and_no_worsening_stop_without_false_optimality(self) -> None:
        counts = {("x", "y"): 1}
        lexicon = {"ab"}
        zero_budget = lexical_local_search(
            counts,
            lexicon,
            "ab",
            capacity=2,
            initial_key={"x": "b", "y": "b"},
            move_budget=0,
        )
        self.assertEqual(zero_budget["status"], "move_budget_exhausted")
        self.assertEqual(zero_budget["evaluation_count"], 0)
        self.assertEqual(zero_budget["accepted_move_count"], 0)
        self.assertFalse(zero_budget["score_certified"])

        local = lexical_local_search(
            counts,
            lexicon,
            "ab",
            capacity=2,
            initial_key={"x": "a", "y": "b"},
            move_budget=3,
        )
        self.assertEqual(local["status"], "no_improving_move")
        self.assertEqual(local["score"], 1)
        self.assertFalse(local["score_certified"])
        self.assertTrue(
            all(
                record["delta"] > 0
                for record in local["evaluations"]
                if record["selected"]
            )
        )

    def test_empty_input_and_strict_validation(self) -> None:
        empty = lexical_local_search(
            {},
            {"a"},
            "ab",
            capacity=1,
            initial_key={},
            move_budget=2,
        )
        self.assertEqual(empty["status"], "empty_input")
        self.assertEqual(empty["key"], {})
        self.assertEqual(empty["score"], 0)
        self.assertFalse(empty["score_certified"])

        common = {
            "ciphertext_counts": {"x": 1},
            "plaintext_lexicon": {"a"},
            "plaintext_alphabet": "ab",
            "capacity": 1,
            "initial_key": {"x": "a"},
            "move_budget": 1,
        }
        for kwargs in (
            {**common, "initial_key": {}},
            {**common, "initial_key": {"x": "a", "y": "b"}},
            {**common, "initial_key": {"x": "q"}},
            {**common, "capacity": 3},
            {**common, "capacity": True},
            {**common, "move_budget": -1},
            {**common, "move_budget": True},
            {**common, "move_budget": 1.0},
        ):
            with self.assertRaises((TypeError, ValueError)):
                lexical_local_search(**kwargs)

    def test_repeated_units_and_random_tiny_cases(self) -> None:
        repeated = lexical_local_search(
            {("x", "x"): 4, ("x", "y"): 2},
            {"aa", "ab"},
            "ab",
            capacity=1,
            initial_key={"x": "a", "y": "b"},
            move_budget=2,
        )
        self.assertEqual(repeated["score"], 6)
        self.assertEqual(repeated["key"], {"x": "a", "y": "b"})

        rng = random.Random(20260917)
        for case in range(40):
            alphabet = tuple("abc")
            symbol_count = rng.randint(1, 3)
            symbols = tuple(f"u{index}" for index in range(symbol_count))
            counts: dict[Word, int] = {}
            for _ in range(rng.randint(1, 6)):
                word = tuple(rng.choice(symbols) for _ in range(rng.randint(0, 3)))
                counts[word] = rng.randint(0, 5)
            if not any(counts):
                counts[(symbols[0],)] = rng.randint(0, 5)
            active_symbols = tuple(
                sorted({symbol for word in counts for symbol in word})
            )
            lexicon = {
                tuple(rng.choice(alphabet) for _ in range(rng.randint(0, 3)))
                for _ in range(rng.randint(0, 8))
            }
            for capacity in (1, 2, None):
                if capacity is not None and capacity * len(alphabet) < len(active_symbols):
                    continue
                initial: dict[str, str] = {}
                usage: Counter[str] = Counter()
                for symbol in active_symbols:
                    choices = [
                        value
                        for value in alphabet
                        if capacity is None or usage[value] < capacity
                    ]
                    value = choices[0]
                    initial[symbol] = value
                    usage[value] += 1
                for budget in (0, 1, 3):
                    result = lexical_local_search(
                        counts,
                        lexicon,
                        alphabet,
                        capacity=capacity,
                        initial_key=initial,
                        move_budget=budget,
                    )
                    normalized_counts = _normalise_counts(counts)
                    usable_lexicon = _normalise_lexicon(lexicon, alphabet)
                    self.assertEqual(
                        result["score"],
                        _direct_score(result["key"], normalized_counts, usable_lexicon),
                        (case, capacity, budget),
                    )
                    evaluations_by_iteration: dict[int, list[dict[str, object]]] = {}
                    for record in result["evaluations"]:
                        before = record["key_before"]
                        candidate = record["candidate_key"]
                        self.assertEqual(
                            record["delta"],
                            _direct_score(candidate, normalized_counts, usable_lexicon)
                            - _direct_score(before, normalized_counts, usable_lexicon),
                            (case, capacity, budget, record),
                        )
                        evaluations_by_iteration.setdefault(record["iteration"], []).append(record)
                    for iteration, records in evaluations_by_iteration.items():
                        before = records[0]["key_before"]
                        expected = _expected_moves(
                            before,
                            active_symbols,
                            alphabet,
                            capacity,
                        )
                        self.assertEqual(
                            [_record_signature(record) for record in records],
                            expected,
                            (case, capacity, budget, iteration),
                        )
                        selected = [record for record in records if record["selected"]]
                        if selected:
                            self.assertEqual(len(selected), 1)
                            best_score = max(record["score_after"] for record in records)
                            best_records = [
                                record
                                for record in records
                                if record["score_after"] == best_score
                            ]
                            expected_record = min(
                                best_records,
                                key=lambda record: _key_tuple(
                                    record["candidate_key"], active_symbols
                                ),
                            )
                            self.assertEqual(
                                selected[0]["candidate_key"],
                                expected_record["candidate_key"],
                            )
                            self.assertGreater(selected[0]["delta"], 0)

    def test_summary_trace_matches_full_result_without_neighbor_records(self) -> None:
        kwargs = {
            "ciphertext_counts": {
                ("x", "x"): 3,
                ("x", "y"): 2,
                ("y", "z"): 5,
                ("z",): 1,
            },
            "plaintext_lexicon": {"aa", "ab", "bc", "a", "b", "c"},
            "plaintext_alphabet": "abc",
            "capacity": 2,
            "initial_key": {"x": "a", "y": "b", "z": "c"},
            "move_budget": 2,
        }
        full = lexical_local_search(**kwargs, trace_mode="full")
        summary = lexical_local_search(**kwargs, trace_mode="summary")

        for field in (
            "key",
            "score",
            "status",
            "score_certified",
            "accepted_move_count",
            "evaluation_count",
        ):
            self.assertEqual(summary[field], full[field], field)
        self.assertEqual(summary["trace_mode"], "summary")
        self.assertEqual(full["trace_mode"], "full")
        self.assertTrue(full["evaluations"])
        self.assertEqual(summary["evaluations"], [])
        self.assertEqual(summary["accepted_moves"], full["accepted_moves"])
        self.assertLessEqual(len(summary["accepted_moves"]), kwargs["move_budget"])

        full_iterations: dict[int, list[dict[str, object]]] = {}
        for record in full["evaluations"]:
            full_iterations.setdefault(record["iteration"], []).append(record)
        expected_iterations = []
        for iteration, records in full_iterations.items():
            expected_iterations.append(
                {
                    "iteration": iteration,
                    "candidate_count": len(records),
                    "positive_candidate_count": sum(
                        record["delta"] > 0 for record in records
                    ),
                    "best_delta": max(record["delta"] for record in records),
                    "best_score_after": max(
                        record["score_after"] for record in records
                    ),
                    "selected": any(record["selected"] for record in records),
                }
            )
        self.assertEqual(summary["trace_summary"]["iterations"], expected_iterations)
        self.assertEqual(
            summary["trace_summary"]["candidate_count_total"],
            len(full["evaluations"]),
        )
        self.assertNotIn("evaluations", summary["trace_summary"])
        self.assertNotIn("candidate_key", repr(summary["trace_summary"]))
        self.assertNotIn("key_before", repr(summary["trace_summary"]))

    def test_summary_mode_preserves_ties_capacity_and_budget(self) -> None:
        kwargs = {
            "ciphertext_counts": {("x", "y"): 1},
            "plaintext_lexicon": {"ab"},
            "plaintext_alphabet": "ab",
            "capacity": 1,
            "initial_key": {"x": "b", "y": "a"},
            "move_budget": 1,
        }
        full = lexical_local_search(**kwargs)
        summary = lexical_local_search(**kwargs, trace_mode="summary")
        self.assertEqual(summary["key"], full["key"])
        self.assertEqual(summary["score"], full["score"])
        self.assertEqual(summary["accepted_moves"], full["accepted_moves"])
        self.assertEqual(summary["accepted_moves"][0]["kind"], "swap")
        self.assertEqual(summary["trace_summary"]["candidate_count_total"], 1)
        self.assertEqual(summary["trace_summary"]["selected_move_count"], 1)
        self.assertLessEqual(
            summary["trace_summary"]["accepted_map_count"], kwargs["move_budget"]
        )

        zero = lexical_local_search(
            **{**kwargs, "move_budget": 0}, trace_mode="summary"
        )
        self.assertEqual(zero["evaluations"], [])
        self.assertEqual(zero["accepted_moves"], [])
        self.assertEqual(zero["trace_summary"]["candidate_count_total"], 0)
        self.assertEqual(zero["trace_summary"]["iterations"], [])

    def test_trace_mode_is_explicitly_validated(self) -> None:
        kwargs = {
            "ciphertext_counts": {"x": 1},
            "plaintext_lexicon": {"a"},
            "plaintext_alphabet": "ab",
            "capacity": 1,
            "initial_key": {"x": "a"},
            "move_budget": 1,
        }
        for mode in ("compact", "", None, True, 1):
            with self.assertRaises((TypeError, ValueError)):
                lexical_local_search(**kwargs, trace_mode=mode)


if __name__ == "__main__":
    unittest.main()
