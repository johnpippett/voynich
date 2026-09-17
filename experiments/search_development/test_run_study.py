"""Synthetic tests for the bounded search-development runner."""

from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from unittest.mock import patch

from experiments.search_development.run_study import (
    CONTROL_FAMILY,
    DevelopmentConfig,
    ENCRYPTION_SEED,
    InputMismatch,
    ImplementationFailure,
    ResourceAbstain,
    StudyInputs,
    canonical_hash,
    main,
    run_local_search,
    run_root_bound,
    run_study,
    validate_inputs,
)


class SearchDevelopmentTests(unittest.TestCase):
    def _config(self) -> DevelopmentConfig:
        return DevelopmentConfig(
            alphabet="abc",
            capacity=2,
            move_budget=1,
            expected_validation_token_count=None,
            expected_validation_type_count=None,
            expected_training_lexicon_type_count=None,
            expected_cipher_unit_count=None,
            expected_candidate_row_count=None,
            expected_storage_estimate_bytes=None,
            expected_stream_sha256=None,
            expected_training_lexicon_sha256=None,
            expected_weighted_counts_sha256=None,
            expected_input_artifact_hashes={},
            expected_frozen_module_hashes={},
            expected_start_scores={},
            expected_key_record_hashes={},
            expected_report_hashes={},
            max_candidate_rows=100,
            max_estimated_storage_bytes=100_000,
            per_start_evaluation_limit=100,
            total_evaluation_limit=200,
            root_timeout_seconds=1,
            total_timeout_seconds=2,
            rss_limit_bytes=100_000_000,
        )

    def _inputs(self) -> StudyInputs:
        return StudyInputs.from_raw_counts(
            {("x", "y"): 1},
            {"ab"},
            starts={
                "cold_selected": {"x": "b", "y": "a"},
                "assisted_selected": {"x": "b", "y": "a"},
            },
            pinned_scores={"cold_selected": 0, "assisted_selected": 0},
            validation_stream_sha256="synthetic-stream",
            training_lexicon_sha256=canonical_hash(["ab"]),
            input_artifact_hashes={"synthetic": "fixture"},
        )

    def test_root_stage_reports_bounds_as_aggregates_without_word_arrays(self) -> None:
        result = run_root_bound(
            self._inputs(),
            config=self._config(),
        )

        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["candidate_row_count"], 1)
        self.assertEqual(result["group_bound"], 2)
        self.assertEqual(result["independent_bound"], 2)
        self.assertNotIn("groups", result)
        self.assertNotIn("words", json.dumps(result))

    def test_local_stage_checks_pinned_score_and_returns_total_map(self) -> None:
        inputs = self._inputs()
        result = run_local_search(
            inputs.weighted_counts,
            inputs.training_lexicon,
            inputs.starts["cold_selected"],
            pinned_score=0,
            start_name="cold_selected",
            config=self._config(),
        )

        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["initial_score"], 0)
        self.assertEqual(result["final_score"], 2)
        self.assertEqual(result["accepted_move_count"], 1)
        self.assertEqual(result["evaluation_count"], 5)
        self.assertEqual(result["key"], {"x": "a", "y": "b"})
        self.assertNotIn("words", json.dumps(result))

    def test_local_stage_rejects_pinned_score_mismatch(self) -> None:
        with self.assertRaises(InputMismatch):
            run_local_search(
                self._inputs().weighted_counts,
                self._inputs().training_lexicon,
                {"x": "b", "y": "a"},
                pinned_score=1,
                start_name="cold_selected",
                config=self._config(),
            )

    def test_local_stage_rejects_regressive_or_invalid_search_result(self) -> None:
        config = self._config()

        def result_for(**overrides):
            result = {
                "key": {"x": "a", "y": "b"},
                "score": 2,
                "initial_score": 2,
                "evaluation_count": 0,
                "accepted_move_count": 0,
                "status": "no_improving_move",
                "local_neighborhood_checked": True,
            }
            result.update(overrides)
            return result

        cases = (
            result_for(score=0),
            result_for(status="unknown_status"),
            result_for(local_neighborhood_checked=1),
            result_for(status="no_improving_move", local_neighborhood_checked=False),
            result_for(status="move_budget_exhausted", local_neighborhood_checked=True),
        )
        for fake_result in cases:
            with self.subTest(fake_result=fake_result):
                with self.assertRaises(ImplementationFailure):
                    run_local_search(
                        self._inputs().weighted_counts,
                        self._inputs().training_lexicon,
                        {"x": "a", "y": "b"},
                        pinned_score=2,
                        start_name="cold_selected",
                        config=config,
                        search_fn=lambda *args, **kwargs: fake_result,
                    )

    def test_json_word_arrays_are_normalized_and_duplicates_rejected(self) -> None:
        payload = {
            "validation_counts": [{"word": ["x", "y"], "count": 2}],
            "training_lexicon": [["a", "b"]],
            "starts": {
                "cold_selected": {"x": "a", "y": "b"},
                "assisted_selected": {"x": "a", "y": "b"},
            },
            "pinned_scores": {"cold_selected": 0, "assisted_selected": 0},
        }
        inputs = StudyInputs.from_mapping(payload)
        self.assertEqual(inputs.weighted_counts, {("x", "y"): 4})
        self.assertEqual(inputs.training_lexicon, (("a", "b"),))

        duplicate = {
            **payload,
            "validation_counts": [
                {"word": ["x", "y"], "count": 1},
                {"word": "xy", "count": 1},
            ],
        }
        with self.assertRaises(ValueError):
            StudyInputs.from_mapping(duplicate)

        invalid_unit = {
            **payload,
            "validation_counts": [{"word": ["x", 1], "count": 1}],
        }
        with self.assertRaises(TypeError):
            StudyInputs.from_mapping(invalid_unit)

    def test_validation_recomputes_canonical_hashes_and_expected_weight_hash(self) -> None:
        inputs = self._inputs()
        summary = validate_inputs(inputs, self._config())
        self.assertEqual(summary["training_lexicon_sha256"], canonical_hash(["ab"]))

        forged_lexicon_hash = StudyInputs.from_raw_counts(
            {("x", "y"): 1},
            {"ab"},
            starts={
                "cold_selected": {"x": "b", "y": "a"},
                "assisted_selected": {"x": "b", "y": "a"},
            },
            pinned_scores={"cold_selected": 0, "assisted_selected": 0},
            training_lexicon_sha256="forged",
        )
        with self.assertRaises(InputMismatch):
            validate_inputs(forged_lexicon_hash, self._config())

        wrong_weight_hash_config = replace(
            self._config(), expected_weighted_counts_sha256="0" * 64
        )
        with self.assertRaises(InputMismatch):
            validate_inputs(inputs, wrong_weight_hash_config)

    def test_local_stage_rejects_incomplete_or_capacity_invalid_map(self) -> None:
        for key in ({"x": "a"}, {"x": "a", "y": "a", "z": "a"}):
            with self.assertRaises((InputMismatch, ValueError)):
                run_local_search(
                    self._inputs().weighted_counts,
                    self._inputs().training_lexicon,
                    key,
                    pinned_score=0,
                    start_name="cold_selected",
                    config=self._config(),
                )

    def test_study_writes_key_records_before_public_aggregate(self) -> None:
        inputs = self._inputs()
        with tempfile.TemporaryDirectory() as directory:
            result = run_study(
                inputs,
                output_dir=Path(directory),
                config=self._config(),
                require_pinned_sources=False,
            )
            self.assertEqual(result["status"], "development_only")
            self.assertTrue((Path(directory) / "cold_selected.key.json").is_file())
            self.assertTrue((Path(directory) / "assisted_selected.key.json").is_file())
            self.assertTrue((Path(directory) / "aggregate.json").is_file())
            self.assertTrue((Path(directory) / "manifest.json").is_file())
            self.assertLess(
                (Path(directory) / "cold_selected.key.json").stat().st_mtime_ns,
                (Path(directory) / "aggregate.json").stat().st_mtime_ns,
            )
            public = json.loads((Path(directory) / "aggregate.json").read_text())
            forbidden = {"words", "ciphertext", "ciphertext_counts", "weighted_counts", "training_lexicon", "lexicon", "candidate_rows", "candidate_cache", "groups", "ungrouped_words", "evaluations", "accepted_moves"}
            def visit(value):
                if isinstance(value, dict):
                    self.assertTrue(forbidden.isdisjoint(value))
                    for child in value.values():
                        visit(child)
                elif isinstance(value, list):
                    for child in value:
                        visit(child)
            visit(public)
            self.assertEqual(public["best_lower_bound"], 2)
            self.assertEqual(public["root"]["group_bound"], 2)
            self.assertEqual(public["root"]["gap_to_best_lower_bound"], 0)
            self.assertEqual(public["starts"]["cold_selected"]["final_score"], 2)
            self.assertEqual(public["input"]["control_family"], CONTROL_FAMILY)
            self.assertEqual(public["input"]["encryption_seed"], ENCRYPTION_SEED)
            manifest = json.loads((Path(directory) / "manifest.json").read_text())
            self.assertEqual(manifest["config"]["control_family"], CONTROL_FAMILY)
            self.assertEqual(manifest["config"]["encryption_seed"], ENCRYPTION_SEED)
            self.assertIn("key_record_sha256", public["starts"]["cold_selected"])
            self.assertNotIn(directory, json.dumps(public))

    def test_study_refuses_existing_fixed_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "aggregate.json"
            path.write_text("keep")
            with self.assertRaises(FileExistsError):
                run_study(
                    self._inputs(),
                    output_dir=Path(directory),
                    config=self._config(),
                    require_pinned_sources=False,
                )
            self.assertEqual(path.read_text(), "keep")

    def test_study_fails_closed_when_lower_bound_exceeds_root_bound(self) -> None:
        inputs = StudyInputs.from_raw_counts(
            {("x", "y"): 1},
            {"ab", "ba"},
            starts={
                "cold_selected": {"x": "b", "y": "a"},
                "assisted_selected": {"x": "b", "y": "a"},
            },
            pinned_scores={"cold_selected": 2, "assisted_selected": 2},
        )
        fake_root = {
            "status": "complete",
            "group_bound": 0,
            "independent_bound": 0,
            "candidate_row_count": 1,
            "candidate_type_count": 1,
            "cipher_type_count": 1,
            "cipher_unit_count": 2,
            "group_count": 1,
            "residual_type_count": 0,
            "storage_estimate_bytes": 1,
            "metadata": {},
            "scope_limits": [],
        }
        with tempfile.TemporaryDirectory() as directory:
            with patch("experiments.search_development.run_study.run_root_bound", return_value=fake_root):
                with self.assertRaises(ImplementationFailure):
                    run_study(
                        inputs,
                        output_dir=Path(directory),
                        config=self._config(),
                        require_pinned_sources=False,
                    )
            self.assertFalse((Path(directory) / "aggregate.json").exists())

    def test_noarg_cli_emits_only_five_supervisor_events(self) -> None:
        events = (
            {"stage": "root_bound", "event": "start"},
            {"stage": "root_bound", "event": "complete"},
            {"stage": "local_search", "event": "start", "start": "cold_selected"},
            {"stage": "local_search", "event": "complete", "start": "cold_selected"},
            {"stage": "local_search", "event": "start", "start": "assisted_selected"},
            {"stage": "local_search", "event": "complete", "start": "assisted_selected"},
            {"stage": "study", "event": "aggregate_written"},
        )
        def fake_run(_inputs, **kwargs):
            for event in events:
                kwargs["progress"](event)
            return {"status": "development_only"}

        stream = StringIO()
        with patch(
            "experiments.search_development.run_study.load_pinned_italian_inputs",
            return_value=self._inputs(),
        ), patch(
            "experiments.search_development.run_study.run_study",
            side_effect=fake_run,
        ), redirect_stdout(stream):
            self.assertEqual(main([]), 0)
        lines = [json.loads(line) for line in stream.getvalue().splitlines()]
        self.assertEqual(
            lines,
            [
                {"event": "progress", "phase": "root_bound", "state": "running"},
                {"event": "progress", "phase": "root_bound", "state": "complete"},
                {"event": "progress", "phase": "local_search", "state": "running"},
                {"event": "progress", "phase": "local_search", "state": "complete"},
                {"event": "complete", "status": "development_only"},
            ],
        )

    def test_full_capacity_map_is_rejected_before_search(self) -> None:
        config = replace(self._config(), capacity=1)
        with self.assertRaises(InputMismatch):
            run_local_search(
                self._inputs().weighted_counts,
                self._inputs().training_lexicon,
                {"x": "a", "y": "a"},
                pinned_score=0,
                start_name="cold_selected",
                config=config,
            )

    def test_evaluation_limit_stops_without_an_aggregate(self) -> None:
        config = replace(self._config(), per_start_evaluation_limit=4)
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ResourceAbstain):
                run_study(
                    self._inputs(),
                    output_dir=Path(directory),
                    config=config,
                    require_pinned_sources=False,
                )
            self.assertFalse((Path(directory) / "aggregate.json").exists())

    def test_key_record_contains_mapping_but_no_word_arrays(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run_study(
                self._inputs(),
                output_dir=Path(directory),
                config=self._config(),
                require_pinned_sources=False,
            )
            record = json.loads(
                (Path(directory) / "cold_selected.key.json").read_text()
            )
            self.assertEqual(record["key"], {"x": "a", "y": "b"})
            self.assertNotIn("words", record)
            self.assertNotIn("ciphertext", record)
            self.assertNotIn("candidate_rows", record)

    def test_input_count_guard_runs_before_root_construction(self) -> None:
        config = replace(self._config(), expected_cipher_unit_count=3)
        with self.assertRaises(InputMismatch):
            run_root_bound(self._inputs(), config=config)


if __name__ == "__main__":
    unittest.main()
