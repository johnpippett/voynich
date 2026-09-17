"""Fixture tests for the bounded development-run supervisor."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from experiments.search_development.supervise import (  # noqa: E402
    CHILD_MODULE,
    ResourceLimits,
    _child_command,
    _monitor_process,
    supervise_development,
)


def _start_fixture(body: str) -> subprocess.Popen[str]:
    return subprocess.Popen(
        [sys.executable, "-u", "-c", textwrap.dedent(body)],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )


def _limits(**overrides: object) -> ResourceLimits:
    values: dict[str, object] = {
        "stage_wall_seconds": 2.0,
        "total_wall_seconds": 3.0,
        "rss_limit_bytes": 7 * 1024 * 1024 * 1024,
        "poll_interval_seconds": 0.01,
        "terminate_grace_seconds": 0.1,
    }
    values.update(overrides)
    return ResourceLimits(**values)


class SupervisorTests(unittest.TestCase):
    def test_defaults_and_fixed_child_command(self) -> None:
        limits = ResourceLimits()
        self.assertEqual(limits.stage_wall_seconds, 1200.0)
        self.assertEqual(limits.total_wall_seconds, 1500.0)
        self.assertEqual(limits.rss_limit_bytes, 7 * 1024**3)
        self.assertEqual(limits.child_cpu_workers, 1)
        self.assertEqual(
            _child_command(),
            (sys.executable, "-m", CHILD_MODULE),
        )

    def test_normal_child_returns_safe_completion_aggregate(self) -> None:
        process = _start_fixture(
            """
            import json
            import sys
            print(json.dumps({"event": "progress", "phase": "root_bound", "state": "running"}), flush=True)
            print(json.dumps({"event": "progress", "phase": "root_bound", "state": "complete"}), flush=True)
            print(json.dumps({"event": "progress", "phase": "local_search", "state": "running"}), flush=True)
            print(json.dumps({"event": "progress", "phase": "local_search", "state": "complete"}), flush=True)
            print(json.dumps({"event": "complete", "status": "development_only"}), flush=True)
            """
        )
        result = _monitor_process(process, _limits())

        self.assertEqual(result["public"]["status"], "development_only")
        self.assertEqual(result["public"]["reason"], "completed")
        self.assertTrue(result["public"]["terminal_event_seen"])
        self.assertEqual(result["public"]["progress_event_count"], 4)
        self.assertEqual(result["public"]["last_phase"], "local_search")
        self.assertEqual(result["private"]["return_code"], 0)
        self.assertGreaterEqual(result["private"]["elapsed_seconds"], 0.0)
        self.assertIsNone(result["public"].get("bound"))
        self.assertIsNone(result["public"].get("score"))

    def test_child_error_is_aggregate_without_raw_stderr(self) -> None:
        process = _start_fixture(
            """
            import sys
            print('private /home/user/secret.json', file=sys.stderr, flush=True)
            raise SystemExit(3)
            """
        )
        result = _monitor_process(process, _limits())

        self.assertEqual(result["public"]["status"], "implementation_failure")
        self.assertEqual(result["public"]["reason"], "child_exit")
        self.assertEqual(result["public"]["stderr_line_count"], 1)
        self.assertNotIn("secret.json", repr(result["public"]))
        self.assertNotIn("/home/user", repr(result["public"]))
        self.assertEqual(result["private"]["return_code"], 3)

    def test_allowed_child_error_kinds_preserve_safe_statuses(self) -> None:
        expected = {
            "resource_abstain": ("resource_abstain", "child_resource_abstain"),
            "input_mismatch": ("input_mismatch", "child_input_mismatch"),
            "implementation_failure": (
                "implementation_failure",
                "child_implementation_failure",
            ),
            "output_exists": ("implementation_failure", "child_output_exists"),
        }
        for kind, (status, reason) in expected.items():
            with self.subTest(kind=kind):
                process = _start_fixture(
                    f"""
                    import json
                    print(json.dumps({{
                        "event": "error",
                        "kind": {kind!r},
                        "message": "secret=/home/user/score=123",
                    }}), flush=True)
                    raise SystemExit(2)
                    """
                )
                result = _monitor_process(process, _limits())

                self.assertEqual(result["public"]["status"], status)
                self.assertEqual(result["public"]["reason"], reason)
                self.assertEqual(result["public"]["child_error_event_count"], 1)
                self.assertNotIn("secret", repr(result["public"]))
                self.assertNotIn("123", repr(result["public"]))

    def test_unknown_child_error_kind_fails_closed(self) -> None:
        process = _start_fixture(
            """
            import json
            print(json.dumps({
                "event": "error",
                "kind": "untrusted_kind",
                "message": "secret=/home/user/score=123",
            }), flush=True)
            raise SystemExit(2)
            """
        )
        result = _monitor_process(process, _limits())

        self.assertEqual(result["public"]["status"], "implementation_failure")
        self.assertEqual(result["public"]["reason"], "malformed_progress")
        self.assertEqual(result["public"]["child_error_event_count"], 1)
        self.assertNotIn("untrusted_kind", repr(result["public"]))
        self.assertNotIn("secret", repr(result["public"]))

    def test_malformed_child_error_event_fails_closed(self) -> None:
        process = _start_fixture(
            """
            import json
            print(json.dumps({"event": "error"}), flush=True)
            raise SystemExit(2)
            """
        )
        result = _monitor_process(process, _limits())

        self.assertEqual(result["public"]["status"], "implementation_failure")
        self.assertEqual(result["public"]["reason"], "malformed_progress")
        self.assertEqual(result["public"]["child_error_event_count"], 1)

    def test_duplicate_child_error_events_fail_closed(self) -> None:
        process = _start_fixture(
            """
            import json
            for _ in range(2):
                print(json.dumps({
                    "event": "error",
                    "kind": "resource_abstain",
                }), flush=True)
            raise SystemExit(2)
            """
        )
        result = _monitor_process(process, _limits())

        self.assertEqual(result["public"]["status"], "implementation_failure")
        self.assertEqual(result["public"]["reason"], "malformed_progress")
        self.assertEqual(result["public"]["child_error_event_count"], 2)

    def test_output_after_terminal_event_fails_closed(self) -> None:
        process = _start_fixture(
            """
            import json
            events = [
                {"event": "progress", "phase": "root_bound", "state": "running"},
                {"event": "progress", "phase": "root_bound", "state": "complete"},
                {"event": "progress", "phase": "local_search", "state": "running"},
                {"event": "progress", "phase": "local_search", "state": "complete"},
                {"event": "complete", "status": "development_only"},
                {"event": "error", "kind": "resource_abstain"},
            ]
            for event in events:
                print(json.dumps(event), flush=True)
            """
        )
        result = _monitor_process(process, _limits())

        self.assertEqual(result["public"]["status"], "implementation_failure")
        self.assertEqual(result["public"]["reason"], "malformed_progress")
        self.assertEqual(result["public"]["child_error_event_count"], 0)

    def test_progress_after_terminal_event_fails_closed(self) -> None:
        process = _start_fixture(
            """
            import json
            events = [
                {"event": "progress", "phase": "root_bound", "state": "running"},
                {"event": "progress", "phase": "root_bound", "state": "complete"},
                {"event": "progress", "phase": "local_search", "state": "running"},
                {"event": "progress", "phase": "local_search", "state": "complete"},
                {"event": "complete", "status": "development_only"},
                {"event": "progress", "phase": "local_search", "state": "complete"},
            ]
            for event in events:
                print(json.dumps(event), flush=True)
            """
        )
        result = _monitor_process(process, _limits())

        self.assertEqual(result["public"]["status"], "implementation_failure")
        self.assertEqual(result["public"]["reason"], "malformed_progress")
        self.assertEqual(result["public"]["progress_event_count"], 4)
        self.assertGreaterEqual(result["public"]["malformed_output_count"], 1)

    def test_stage_wall_limit_kills_and_reaps_child_group(self) -> None:
        process = _start_fixture(
            """
            import json
            import time
            print(json.dumps({"event": "progress", "phase": "root_bound", "state": "running"}), flush=True)
            time.sleep(2)
            """
        )
        result = _monitor_process(
            process,
            _limits(stage_wall_seconds=0.05, total_wall_seconds=1.0),
        )

        self.assertEqual(result["public"]["status"], "resource_abstain")
        self.assertEqual(result["public"]["reason"], "stage_wall_time")
        self.assertIsNone(result["public"].get("score"))
        self.assertIsNotNone(process.poll())
        self.assertTrue(result["private"]["terminated_by_supervisor"])

    def test_stage_timer_stops_after_root_bound_completion(self) -> None:
        process = _start_fixture(
            """
            import json
            import time
            print(json.dumps({"event": "progress", "phase": "root_bound", "state": "running"}), flush=True)
            print(json.dumps({"event": "progress", "phase": "root_bound", "state": "complete"}), flush=True)
            time.sleep(0.12)
            print(json.dumps({"event": "progress", "phase": "local_search", "state": "running"}), flush=True)
            print(json.dumps({"event": "progress", "phase": "local_search", "state": "complete"}), flush=True)
            print(json.dumps({"event": "complete", "status": "development_only"}), flush=True)
            """
        )
        result = _monitor_process(
            process,
            _limits(stage_wall_seconds=0.05, total_wall_seconds=0.5),
        )

        self.assertEqual(result["public"]["status"], "development_only")
        self.assertEqual(result["public"]["reason"], "completed")

    def test_sampled_rss_limit_is_a_guard_not_a_hard_claim(self) -> None:
        process = _start_fixture(
            """
            import json
            import time
            data = bytearray(8 * 1024 * 1024)
            data[0] = 1
            print(json.dumps({"event": "progress", "phase": "root_bound", "state": "running"}), flush=True)
            time.sleep(2)
            """
        )
        result = _monitor_process(
            process,
            _limits(
                stage_wall_seconds=1.0,
                total_wall_seconds=2.0,
                rss_limit_bytes=1,
            ),
        )

        self.assertEqual(result["public"]["status"], "resource_abstain")
        self.assertEqual(result["public"]["reason"], "rss_observed")
        self.assertEqual(result["public"]["rss_guard"], "sampled_proc_rss")
        self.assertIsNone(result["public"].get("score"))
        self.assertGreaterEqual(result["private"]["rss_sample_count"], 1)
        self.assertIsNotNone(process.poll())

    def test_incomplete_progress_is_not_a_completed_run(self) -> None:
        process = _start_fixture(
            """
            import json
            print(json.dumps({"event": "progress", "phase": "root_bound", "state": "running"}), flush=True)
            print(json.dumps({"event": "progress", "phase": "root_bound", "state": "complete"}), flush=True)
            print(json.dumps({"event": "progress", "phase": "local_search", "state": "running"}), flush=True)
            print(json.dumps({"event": "progress", "phase": "local_search", "state": "complete"}), flush=True)
            """
        )
        result = _monitor_process(process, _limits())

        self.assertEqual(result["public"]["status"], "implementation_failure")
        self.assertEqual(result["public"]["reason"], "incomplete_progress")
        self.assertFalse(result["public"]["terminal_event_seen"])
        self.assertIsNone(result["public"].get("bound"))

    def test_missing_phase_sequence_is_not_completion(self) -> None:
        process = _start_fixture(
            """
            import json
            print(json.dumps({"event": "complete", "status": "development_only"}), flush=True)
            """
        )
        result = _monitor_process(process, _limits())

        self.assertEqual(result["public"]["status"], "implementation_failure")
        self.assertEqual(result["public"]["reason"], "malformed_progress")
        self.assertFalse(result["public"]["terminal_event_seen"])

    def test_duplicate_phase_sequence_is_not_completion(self) -> None:
        process = _start_fixture(
            """
            import json
            events = [
                {"event": "progress", "phase": "root_bound", "state": "running"},
                {"event": "progress", "phase": "root_bound", "state": "complete"},
                {"event": "progress", "phase": "local_search", "state": "running"},
                {"event": "progress", "phase": "local_search", "state": "complete"},
                {"event": "progress", "phase": "local_search", "state": "complete"},
                {"event": "complete", "status": "development_only"},
            ]
            for event in events:
                print(json.dumps(event), flush=True)
            """
        )
        result = _monitor_process(process, _limits())

        self.assertEqual(result["public"]["status"], "implementation_failure")
        self.assertEqual(result["public"]["reason"], "malformed_progress")
        self.assertGreaterEqual(result["public"]["malformed_output_count"], 1)

    def test_partial_numeric_progress_is_never_returned_after_resource_stop(self) -> None:
        process = _start_fixture(
            """
            import json
            import time
            print(json.dumps({"event": "progress", "phase": "root_bound", "state": "running", "bound": 123456}), flush=True)
            time.sleep(2)
            """
        )
        result = _monitor_process(
            process,
            _limits(stage_wall_seconds=0.05, total_wall_seconds=1.0),
        )

        self.assertEqual(result["public"]["status"], "resource_abstain")
        self.assertNotIn("123456", repr(result["public"]))
        self.assertNotIn("bound", result["public"])
        self.assertNotIn("score", result["public"])

    def test_interrupt_kills_and_reaps_owned_child(self) -> None:
        process = _start_fixture(
            """
            import time
            time.sleep(2)
            """
        )
        calls = 0
        real_sleep = time.sleep

        def interrupt_once(seconds: float) -> None:
            nonlocal calls
            calls += 1
            if calls == 1:
                raise KeyboardInterrupt
            real_sleep(seconds)

        with patch(
            "experiments.search_development.supervise.time.sleep",
            side_effect=interrupt_once,
        ):
            result = _monitor_process(process, _limits())

        self.assertEqual(result["public"]["status"], "resource_abstain")
        self.assertEqual(result["public"]["reason"], "interrupted")
        self.assertTrue(result["private"]["interrupted"])
        self.assertIsNotNone(process.poll())

    def test_resource_stop_kills_ignored_term_descendant(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory) / "descendant.pid"
            process = _start_fixture(
                f"""
                import pathlib
                import signal
                import subprocess
                import sys
                import time
                descendant = subprocess.Popen([
                    sys.executable,
                    "-c",
                    "import signal,time; signal.signal(signal.SIGTERM, signal.SIG_IGN); time.sleep(10)",
                ])
                pathlib.Path({str(marker)!r}).write_text(str(descendant.pid))
                time.sleep(10)
                """
            )
            result = _monitor_process(
                process,
                _limits(
                    stage_wall_seconds=0.05,
                    total_wall_seconds=1.0,
                    terminate_grace_seconds=0.05,
                ),
            )

            self.assertEqual(result["public"]["status"], "resource_abstain")
            self.assertTrue(result["private"]["terminated_by_supervisor"])
            descendant_pid = int(marker.read_text())
            deadline = time.monotonic() + 1.0
            while time.monotonic() < deadline:
                try:
                    os.kill(descendant_pid, 0)
                except ProcessLookupError:
                    break
                time.sleep(0.01)
            else:
                self.fail("ignored-term descendant survived process-group cleanup")

    def test_existing_output_is_refused_before_child_start(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "result.json"
            output.write_text("existing", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                supervise_development(
                    PROJECT_ROOT,
                    output_paths=[output],
                )


if __name__ == "__main__":
    unittest.main()
