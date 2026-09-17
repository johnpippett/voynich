"""Behavioral tests for the exploratory word-context experiment."""

from __future__ import annotations

import pathlib
import sys
import unittest


PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from voynich.context import run_context
from voynich.groups import group_id, grouping_config, split_bucket


def _record(folio: str, tokens: list[str], locus: str = "1", **extra: object) -> dict:
    record = {
        "folio": folio,
        "locus": locus,
        "kind": "P0",
        "tokens": tokens,
        "metadata": {"source": "test"},
        "excluded_tokens": 0,
    }
    record.update(extra)
    return record


def _folio_for_bucket(bucket: int) -> str:
    for number in grouping_config()["folio_map"]:
        folio = f"f{number}r"
        if split_bucket(group_id(folio)) == bucket:
            return folio
    raise AssertionError(f"no folio for bucket {bucket}")


class ContextBehaviorTests(unittest.TestCase):
    def test_probability_summaries_are_normalized(self) -> None:
        result = run_context(
            [
                _record(_folio_for_bucket(3), ["a", "b", "a", "b"] * 3),
                _record(_folio_for_bucket(0), ["a", "b", "a", "b"]),
            ],
            bootstraps=9,
        )

        for name in ("original", "shuffled_train"):
            model = result["models"][name]
            self.assertAlmostEqual(model["unigram_probability_sum"], 1.0, places=12)
            for total in model["conditional_probability_sums"].values():
                self.assertAlmostEqual(total, 1.0, places=12)

    def test_test_words_do_not_enter_training_vocabulary(self) -> None:
        train = _folio_for_bucket(3)
        test = _folio_for_bucket(0)
        result = run_context(
            [
                _record(train, ["known", "known", "known", "known"]),
                _record(test, ["known", "secret", "known"]),
            ],
            bootstraps=9,
        )

        model = result["models"]["original"]
        self.assertNotIn("secret", model["vocabulary"])
        self.assertEqual(result["scores"]["test"]["unigram"]["unknown_target_count"], 1)
        self.assertEqual(result["scores"]["test"]["unigram"]["unseen_target_count"], 1)
        self.assertEqual(result["scores"]["test"]["unigram"]["scored_words"], 2)

    def test_pruned_training_singleton_is_unknown_but_not_unseen(self) -> None:
        train = _folio_for_bucket(3)
        test = _folio_for_bucket(0)
        result = run_context(
            [
                _record(train, ["known", "singleton", "known"]),
                _record(test, ["known", "singleton", "secret"]),
            ],
            bootstraps=9,
        )

        score = result["scores"]["test"]["unigram"]
        self.assertEqual(score["unknown_target_count"], 2)
        self.assertEqual(score["unseen_target_count"], 1)
        self.assertIn("singleton", result["models"]["original"]["training_types"])
        self.assertNotIn("singleton", result["models"]["original"]["vocabulary"])

    def test_confirmed_foldout_group_keeps_85_and_86_together(self) -> None:
        result = run_context(
            [
                _record("f85r", ["a", "b", "c"]),
                _record("f86v", ["a", "b", "c"]),
                _record("fRos", ["a", "b", "c"]),
                _record("f1r", ["a", "b", "c"]),
            ],
            bootstraps=9,
        )

        manifest = result["split_manifest"]
        self.assertEqual(manifest["test"]["groups"], ["85"])
        self.assertEqual(manifest["test"]["folios"], ["f85r", "f86v", "fRos"])
        self.assertEqual(manifest["test"]["group_manifest"][0]["folios"], ["f85r", "f86v", "fRos"])
        self.assertEqual(manifest["grouping_config"]["confirmed_cross_number_foldout"], [85, 86])

    def test_unsupported_folio_identifier_is_rejected_by_shared_grouping(self) -> None:
        with self.assertRaises(ValueError):
            run_context([_record("not-a-folio", ["a", "b", "c"])], bootstraps=9)

    def test_bigram_counts_do_not_cross_line_boundaries(self) -> None:
        train = _folio_for_bucket(3)
        test = _folio_for_bucket(0)
        result = run_context(
            [
                _record(train, ["a", "x", "x"], locus="1"),
                _record(train, ["b", "y", "y"], locus="2"),
                _record(test, ["x", "b", "y"], locus="1"),
            ],
            bootstraps=9,
        )

        pair_counts = result["models"]["original"]["bigram_counts"]
        self.assertNotIn("b", pair_counts.get("x", {}))
        self.assertEqual(result["counts"]["training_transitions"], 4)

    def test_repeated_grammar_beats_unigram_and_original_order_beats_shuffle(self) -> None:
        train = _folio_for_bucket(3)
        test = _folio_for_bucket(0)
        records = [
            _record(train, ["a", "b", "c"] * 20, locus=str(i))
            for i in range(4)
        ]
        records.append(_record(test, ["a", "b", "c"] * 5))
        result = run_context(records, bootstraps=49)
        differences = result["scores"]["test"]["differences"]

        self.assertGreater(differences["bigram_improvement_over_unigram"]["bits_per_word"], 0.0)
        self.assertGreater(differences["original_order_improvement_over_shuffled"]["bits_per_word"], 0.0)

    def test_ineligible_lines_and_interruption_markers_are_not_scored(self) -> None:
        train = _folio_for_bucket(3)
        test = _folio_for_bucket(0)
        result = run_context(
            [
                _record(train, ["a", "b"]),
                _record(train, ["a", "b", "c"], excluded_tokens=1),
                _record(train, ["a", "b", "c"], text_raw="a<->b"),
                _record(train, ["a", "b", "c"], text_raw="a<~>b"),
                _record(test, ["a", "b", "c"]),
            ],
            bootstraps=9,
        )

        self.assertEqual(result["counts"]["eligible_lines"]["train"], 0)
        self.assertEqual(result["counts"]["eligible_lines"]["test"], 1)
        self.assertEqual(result["scores"]["test"]["unigram"]["scored_words"], 2)

    def test_group_bootstrap_and_run_are_reproducible(self) -> None:
        records = [
            _record(_folio_for_bucket(3), ["a", "b", "c"] * 4),
            _record(_folio_for_bucket(0), ["a", "b", "c"] * 3),
            _record(_folio_for_bucket(1), ["a", "c", "b"] * 3),
        ]
        first = run_context(records, bootstraps=49)
        second = run_context(records, bootstraps=49)

        self.assertEqual(first, second)
        self.assertEqual(first["bootstrap"]["draws"], 49)
        self.assertEqual(first["bootstrap"]["unit"], "folio_group")
        self.assertEqual(first["bootstrap"]["group_count"], 2)
        self.assertEqual(
            set(first["bootstrap"]["per_group_score_sums"]),
            {_folio_for_bucket(0)[1:-1], _folio_for_bucket(1)[1:-1]},
        )


if __name__ == "__main__":
    unittest.main()
