"""Bounded supervisor for the synthetic Italian development runner.

The production child command is fixed to ``python -m
experiments.search_development.run_study``. The child writes newline-delimited
JSON progress events to stdout:

* ``{"event": "progress", "phase": "root_bound", "state": "running"}``
* ``{"event": "progress", "phase": "root_bound", "state": "complete"}``
* ``{"event": "progress", "phase": "local_search", "state": "running"}``
* ``{"event": "progress", "phase": "local_search", "state": "complete"}``
* ``{"event": "complete", "status": "development_only"}``

The four progress events must occur once and in this order. The final event
must occur after them. The supervisor reads this protocol from child stdout.
An error event can use one of ``resource_abstain``, ``input_mismatch``,
``implementation_failure``, or ``output_exists`` as its ``kind``. Unknown,
malformed, duplicate, and post-terminal events fail closed.

The supervisor returns safe aggregate status data. It does not return child
payloads, scores, bounds, raw errors, or local paths. Resource values in the
private result use a monotonic wall clock, a child-usage delta, and sampled
``/proc`` resident set size (RSS). The RSS value is a sampled guard, not a
kernel memory hard limit. An optional address-space ceiling uses ``RLIMIT_AS``
and is not an RSS measurement.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import math
import os
from pathlib import Path
import queue
import resource
import signal
import subprocess
import sys
import threading
import time
from collections.abc import Iterable, Sequence
from typing import Any, TextIO


CHILD_MODULE = "experiments.search_development.run_study"
_ALLOWED_PHASES = frozenset(("root_bound", "local_search"))
_ALLOWED_STATES = frozenset(("running", "complete"))
_ALLOWED_CHILD_ERROR_KINDS = frozenset(
    (
        "resource_abstain",
        "input_mismatch",
        "implementation_failure",
        "output_exists",
    )
)
_CHILD_ERROR_REASONS = {
    "resource_abstain": "child_resource_abstain",
    "input_mismatch": "child_input_mismatch",
    "implementation_failure": "child_implementation_failure",
    "output_exists": "child_output_exists",
}


@dataclass(frozen=True)
class ResourceLimits:
    """Limits for one fixed child process.

    ``rss_limit_bytes`` is checked at polling samples. It can be exceeded
    between samples. ``as_limit_bytes`` is an optional virtual address-space
    ceiling applied inside the child with ``RLIMIT_AS``.
    """

    stage_wall_seconds: float = 1200.0
    total_wall_seconds: float = 1500.0
    rss_limit_bytes: int = 7 * 1024**3
    poll_interval_seconds: float = 0.25
    terminate_grace_seconds: float = 5.0
    as_limit_bytes: int | None = None
    child_cpu_workers: int = field(default=1, init=False)

    def __post_init__(self) -> None:
        for name, value in (
            ("stage_wall_seconds", self.stage_wall_seconds),
            ("total_wall_seconds", self.total_wall_seconds),
            ("poll_interval_seconds", self.poll_interval_seconds),
            ("terminate_grace_seconds", self.terminate_grace_seconds),
        ):
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f"{name} must be numeric")
            if isinstance(value, float) and not math.isfinite(value):
                raise ValueError(f"{name} must be finite")
            if value <= 0:
                raise ValueError(f"{name} must be positive")
        if self.total_wall_seconds < self.stage_wall_seconds:
            raise ValueError("total_wall_seconds must be at least stage_wall_seconds")
        if (
            isinstance(self.rss_limit_bytes, bool)
            or not isinstance(self.rss_limit_bytes, int)
            or self.rss_limit_bytes <= 0
        ):
            raise ValueError("rss_limit_bytes must be a positive integer")
        if self.as_limit_bytes is not None and (
            isinstance(self.as_limit_bytes, bool)
            or not isinstance(self.as_limit_bytes, int)
            or self.as_limit_bytes <= 0
        ):
            raise ValueError("as_limit_bytes must be a positive integer or None")


def _child_command() -> tuple[str, str, str]:
    """Return the only command that the production supervisor can launch."""

    return (sys.executable, "-m", CHILD_MODULE)


def _ensure_output_paths_absent(output_paths: Iterable[str | Path]) -> None:
    for raw_path in output_paths:
        path = Path(raw_path)
        if os.path.lexists(path):
            raise FileExistsError("a declared output already exists")


def _read_proc_rss_bytes(pid: int) -> int | None:
    """Read one Linux ``VmRSS`` sample for ``pid``."""

    try:
        with open(f"/proc/{pid}/status", encoding="ascii") as stream:
            for line in stream:
                if line.startswith("VmRSS:"):
                    fields = line.split()
                    if len(fields) >= 2:
                        return int(fields[1]) * 1024
    except (FileNotFoundError, PermissionError, OSError, ValueError):
        return None
    return None


def _set_child_address_space_limit(limit: int) -> None:
    resource.setrlimit(resource.RLIMIT_AS, (limit, limit))


def _stream_reader(
    stream: TextIO,
    name: str,
    events: queue.Queue[tuple[str, str | None]],
) -> None:
    try:
        for line in stream:
            events.put((name, line))
    finally:
        events.put((name, None))


def _terminate_owned_process_group(
    process: subprocess.Popen[str],
    grace_seconds: float,
) -> None:
    """Terminate and reap the process group created by this supervisor."""

    # The leader can exit between the monitor poll and this call. Send the
    # signal to the owned group in that race, so descendants cannot survive.
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    deadline = time.monotonic() + grace_seconds
    while True:
        try:
            os.killpg(process.pid, 0)
        except ProcessLookupError:
            break
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        time.sleep(min(0.05, remaining))
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    process.wait()


def _consume_event(
    name: str,
    line: str,
    state: dict[str, Any],
) -> None:
    if name == "stderr":
        state["stderr_line_count"] += 1
        return

    state["stdout_line_count"] += 1
    try:
        payload = json.loads(line)
    except (TypeError, ValueError):
        state["malformed_output_count"] += 1
        return
    if not isinstance(payload, dict):
        state["malformed_output_count"] += 1
        return

    event = payload.get("event")
    if state["terminal_event_seen"]:
        state["malformed_output_count"] += 1
        return
    if state["child_error_event_count"]:
        if event == "error":
            state["child_error_event_count"] += 1
        state["malformed_output_count"] += 1
        return
    if event == "progress":
        phase = payload.get("phase")
        progress_state = payload.get("state")
        if phase not in _ALLOWED_PHASES or progress_state not in _ALLOWED_STATES:
            state["malformed_output_count"] += 1
            return

        sequence_error = False
        if phase == "root_bound":
            if progress_state == "running":
                if state["root_bound_running_seen"]:
                    sequence_error = True
                else:
                    state["root_bound_running_seen"] = True
            elif (
                not state["root_bound_running_seen"]
                or state["root_bound_complete_seen"]
            ):
                sequence_error = True
            else:
                state["root_bound_complete_seen"] = True
                if not state["stage_complete"]:
                    state["stage_complete"] = True
                    state["stage_complete_observed_at"] = time.monotonic()
        elif not state["root_bound_complete_seen"]:
            sequence_error = True
        elif progress_state == "running":
            if state["local_search_running_seen"]:
                sequence_error = True
            else:
                state["local_search_running_seen"] = True
        elif not state["local_search_running_seen"] or state["local_search_complete_seen"]:
            sequence_error = True
        else:
            state["local_search_complete_seen"] = True

        if sequence_error:
            state["malformed_output_count"] += 1
            return
        state["progress_event_count"] += 1
        state["last_phase"] = phase
        state["last_state"] = progress_state
        return
    if event == "complete":
        if (
            state["terminal_event_seen"]
            or not state["root_bound_complete_seen"]
            or not state["local_search_complete_seen"]
        ):
            state["malformed_output_count"] += 1
            return
        state["terminal_event_seen"] = True
        state["terminal_status"] = payload.get("status")
        return
    if event == "error":
        state["child_error_event_count"] += 1
        kind = payload.get("kind")
        if not isinstance(kind, str) or kind not in _ALLOWED_CHILD_ERROR_KINDS:
            state["child_error_kind"] = "unknown"
            state["malformed_output_count"] += 1
            return
        state["child_error_kind"] = kind
        return
    state["malformed_output_count"] += 1


def _drain_events(
    events: queue.Queue[tuple[str, str | None]],
    state: dict[str, Any],
) -> None:
    while True:
        try:
            name, line = events.get_nowait()
        except queue.Empty:
            return
        if line is not None:
            _consume_event(name, line, state)


def _child_cpu_delta(
    before: resource.struct_rusage,
    after: resource.struct_rusage,
) -> float:
    return max(
        0.0,
        (after.ru_utime + after.ru_stime)
        - (before.ru_utime + before.ru_stime),
    )


def _monitor_process(
    process: subprocess.Popen[str],
    limits: ResourceLimits,
    *,
    started_at: float | None = None,
    usage_before: resource.struct_rusage | None = None,
) -> dict[str, Any]:
    """Monitor one already-created, process-group-leading child."""

    if started_at is None:
        started_at = time.monotonic()
    if usage_before is None:
        usage_before = resource.getrusage(resource.RUSAGE_CHILDREN)

    events: queue.Queue[tuple[str, str | None]] = queue.Queue()
    readers = [
        threading.Thread(
            target=_stream_reader,
            args=(process.stdout, "stdout", events),
            daemon=True,
        ),
        threading.Thread(
            target=_stream_reader,
            args=(process.stderr, "stderr", events),
            daemon=True,
        ),
    ]
    for reader in readers:
        reader.start()

    state: dict[str, Any] = {
        "progress_event_count": 0,
        "last_phase": None,
        "last_state": None,
        "stage_complete": False,
        "stage_complete_observed_at": None,
        "root_bound_running_seen": False,
        "root_bound_complete_seen": False,
        "local_search_running_seen": False,
        "local_search_complete_seen": False,
        "terminal_event_seen": False,
        "terminal_status": None,
        "child_error_event_count": 0,
        "child_error_kind": None,
        "malformed_output_count": 0,
        "stdout_line_count": 0,
        "stderr_line_count": 0,
    }
    max_rss_bytes: int | None = None
    rss_sample_count = 0
    resource_reason: str | None = None
    terminated_by_supervisor = False
    interrupted = False

    try:
        while process.poll() is None:
            _drain_events(events, state)
            rss_bytes = _read_proc_rss_bytes(process.pid)
            if rss_bytes is not None:
                rss_sample_count += 1
                max_rss_bytes = max(max_rss_bytes or 0, rss_bytes)

            elapsed = time.monotonic() - started_at
            if elapsed >= limits.total_wall_seconds:
                resource_reason = "total_wall_time"
            elif (
                (
                    not state["stage_complete"]
                    or state["stage_complete_observed_at"]
                    > started_at + limits.stage_wall_seconds
                )
                and elapsed >= limits.stage_wall_seconds
            ):
                resource_reason = "stage_wall_time"
            elif rss_bytes is not None and rss_bytes >= limits.rss_limit_bytes:
                resource_reason = "rss_observed"

            if resource_reason is not None:
                terminated_by_supervisor = True
                _terminate_owned_process_group(
                    process,
                    limits.terminate_grace_seconds,
                )
                break

            time.sleep(limits.poll_interval_seconds)
    except KeyboardInterrupt:
        interrupted = True
        terminated_by_supervisor = True
        resource_reason = "interrupted"
        _terminate_owned_process_group(process, limits.terminate_grace_seconds)

    _drain_events(events, state)
    for reader in readers:
        reader.join(timeout=max(1.0, limits.terminate_grace_seconds + 1.0))
    _drain_events(events, state)
    for stream in (process.stdout, process.stderr):
        if stream is not None:
            stream.close()
    return_code = process.wait()
    usage_after = resource.getrusage(resource.RUSAGE_CHILDREN)
    elapsed_seconds = max(0.0, time.monotonic() - started_at)

    if resource_reason is not None:
        public_status = "resource_abstain"
        reason = resource_reason
    elif state["malformed_output_count"]:
        public_status = "implementation_failure"
        reason = "malformed_progress"
    elif state["child_error_kind"] in _CHILD_ERROR_REASONS:
        child_kind = state["child_error_kind"]
        public_status = (
            "resource_abstain"
            if child_kind == "resource_abstain"
            else (
                "input_mismatch"
                if child_kind == "input_mismatch"
                else "implementation_failure"
            )
        )
        reason = _CHILD_ERROR_REASONS[child_kind]
    elif return_code != 0:
        public_status = "implementation_failure"
        reason = "child_exit"
    elif state["child_error_event_count"]:
        public_status = "implementation_failure"
        reason = "child_error_event"
    elif not state["terminal_event_seen"]:
        public_status = "implementation_failure"
        reason = "incomplete_progress"
    elif state["terminal_status"] != "development_only":
        public_status = "implementation_failure"
        reason = "invalid_terminal_status"
    else:
        public_status = "development_only"
        reason = "completed"

    public = {
        "status": public_status,
        "reason": reason,
        "progress_event_count": state["progress_event_count"],
        "last_phase": state["last_phase"],
        "last_state": state["last_state"],
        "terminal_event_seen": state["terminal_event_seen"],
        "stderr_line_count": state["stderr_line_count"],
        "child_error_event_count": state["child_error_event_count"],
        "malformed_output_count": state["malformed_output_count"],
        "rss_guard": "sampled_proc_rss",
    }
    private = {
        "elapsed_seconds": elapsed_seconds,
        "cpu_seconds": _child_cpu_delta(usage_before, usage_after),
        "max_rss_bytes": max_rss_bytes,
        "rss_sample_count": rss_sample_count,
        "rss_limit_bytes": limits.rss_limit_bytes,
        "poll_interval_seconds": limits.poll_interval_seconds,
        "stage_wall_seconds": limits.stage_wall_seconds,
        "total_wall_seconds": limits.total_wall_seconds,
        "as_limit_bytes": limits.as_limit_bytes,
        "return_code": return_code,
        "terminated_by_supervisor": terminated_by_supervisor,
        "interrupted": interrupted,
        "wall_measurement": "monotonic supervisor elapsed; polling can overshoot",
        "cpu_measurement": "RUSAGE_CHILDREN delta",
        "rss_measurement": "maximum sampled /proc VmRSS; not a hard cap",
    }
    return {"public": public, "private": private}


def supervise_development(
    project_root: str | Path,
    *,
    output_paths: Sequence[str | Path] = (),
    limits: ResourceLimits | None = None,
) -> dict[str, Any]:
    """Launch and supervise the fixed development child.

    ``output_paths`` are preflight-only declarations. The supervisor refuses
    to start when one exists. It never accepts an arbitrary command or child
    argument payload.
    """

    limits = ResourceLimits() if limits is None else limits
    _ensure_output_paths_absent(output_paths)
    root = Path(project_root)
    if not root.is_dir():
        raise FileNotFoundError("the project root is unavailable")

    usage_before = resource.getrusage(resource.RUSAGE_CHILDREN)
    started_at = time.monotonic()
    environment = os.environ.copy()
    environment["PYTHONUNBUFFERED"] = "1"
    environment["VOYNICH_SEARCH_CPU_WORKERS"] = "1"
    environment["PYTHONPATH"] = os.pathsep.join(
        (str(root / "src"), str(root))
    )
    preexec_fn = None
    if limits.as_limit_bytes is not None:
        preexec_fn = lambda: _set_child_address_space_limit(  # noqa: E731
            limits.as_limit_bytes
        )

    try:
        process = subprocess.Popen(
            _child_command(),
            cwd=root,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            start_new_session=True,
            preexec_fn=preexec_fn,
        )
    except (OSError, subprocess.SubprocessError):
        return {
            "public": {
                "status": "implementation_failure",
                "reason": "spawn_error",
                "progress_event_count": 0,
                "last_phase": None,
                "last_state": None,
                "terminal_event_seen": False,
                "stderr_line_count": 0,
                "child_error_event_count": 0,
                "malformed_output_count": 0,
                "rss_guard": "sampled_proc_rss",
            },
            "private": {
                "elapsed_seconds": max(0.0, time.monotonic() - started_at),
                "cpu_seconds": 0.0,
                "max_rss_bytes": None,
                "rss_sample_count": 0,
                "rss_limit_bytes": limits.rss_limit_bytes,
                "poll_interval_seconds": limits.poll_interval_seconds,
                "stage_wall_seconds": limits.stage_wall_seconds,
                "total_wall_seconds": limits.total_wall_seconds,
                "as_limit_bytes": limits.as_limit_bytes,
                "return_code": None,
                "terminated_by_supervisor": False,
                "interrupted": False,
                "wall_measurement": "monotonic supervisor elapsed; polling can overshoot",
                "cpu_measurement": "RUSAGE_CHILDREN delta",
                "rss_measurement": "maximum sampled /proc VmRSS; not a hard cap",
            },
        }
    return _monitor_process(
        process,
        limits,
        started_at=started_at,
        usage_before=usage_before,
    )


__all__ = [
    "CHILD_MODULE",
    "ResourceLimits",
    "supervise_development",
]
