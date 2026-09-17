"""Run the fixed cyclic quotient control under an external byte freeze."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import signal
import subprocess
import sys
import time
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
PROTOCOL = "cyclic-quotient-recovery-v1"
FREEZE_MANIFEST_PATH = Path("experiments/cyclic_quotient/freeze-v1.json")
RESULTS_ROOT = Path("results/cyclic-quotient-recovery-v1")
PUBLIC_RECEIPT_PATH = Path("reports/cyclic-quotient-recovery-v1/supervision.json")
PRIVATE_RECEIPT_PATH = RESULTS_ROOT / "resources.json"
CORPORA = ("latin", "italian")
CORPUS_OUTPUT_NAMES = ("quotient.json", "fit.keys.json", "fit.json", "diagnostics.json")
CORPUS_OUTPUT_PATHS = tuple(
    RESULTS_ROOT / corpus / name
    for corpus in CORPORA
    for name in CORPUS_OUTPUT_NAMES
)
ALL_OUTPUT_PATHS = CORPUS_OUTPUT_PATHS + (PUBLIC_RECEIPT_PATH, PRIVATE_RECEIPT_PATH)

EXPECTED_COMMAND = ("python", "-m", "experiments.cyclic_quotient.run_frozen")
EXPECTED_CHILD_COMMAND = (
    "python", "-m", "experiments.cyclic_quotient.control_study",
    "--corpus", "{corpus}", "--output-dir",
    "results/cyclic-quotient-recovery-v1/{corpus}",
)
EXPECTED_PARAMETERS = {
    "corpora": list(CORPORA),
    "family": "cap2",
    "seed": 7000,
    "capacity": 1,
    "declared_unit_count": 52,
    "quotient_node_budget": 100_000,
    "solver_node_budget": 100_000,
    "bound_engine": "bitset",
    "input_scope": "validation_ciphertext_and_train_lexicon",
    "initial_key": "empty",
    "test_score_order": "no_test_scoring",
}
EXPECTED_RESOURCES = {
    "corpus_wall_seconds": 300.0,
    "rss_limit_bytes": 7 * 1024**3,
    "poll_interval_seconds": 0.25,
    "terminate_grace_seconds": 5.0,
    "as_limit_bytes": None,
    "child_cpu_workers": 1,
    "retry_count": 0,
}
UNITS = tuple(f"c{index:02d}" for index in range(52))
EXPECTED_DECLARED_UNITS_SHA256 = hashlib.sha256(
    (json.dumps(list(UNITS), sort_keys=True, separators=(",", ":")) + "\n").encode()
).hexdigest()
QUOTIENT_STATUSES = frozenset({"proved", "ambiguous", "unknown_budget", "infeasible"})
ABSTENTION_STATUSES = frozenset({"ambiguous", "unknown_budget", "infeasible"})
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
CONTROL_TEST_MODULES = (
    "experiments.cyclic_pairing.test_pairing",
    "experiments.cyclic_pairing.test_forced",
    "experiments.cyclic_quotient.test_quotient",
    "experiments.cyclic_quotient.test_study",
    "experiments.cyclic_quotient.test_control_study",
)

# The manifest excludes itself. The list covers the quotient, its pairing
# evidence, its reference loader, solver dependencies, and known result pins.
FREEZE_FILES = tuple(
    Path(value)
    for value in (
        "docs/plans/cyclic-quotient-run-v1.md",
        "docs/plans/cyclic-quotient-recovery-v1.md",
        "docs/plans/cyclic-pairing-control-v1.md",
        "docs/research/cyclic-emitter-pairing.md",
        "experiments/cyclic_quotient/__init__.py",
        "experiments/cyclic_quotient/quotient.py",
        "experiments/cyclic_quotient/test_quotient.py",
        "experiments/cyclic_quotient/study.py",
        "experiments/cyclic_quotient/test_study.py",
        "experiments/cyclic_quotient/control_study.py",
        "experiments/cyclic_quotient/test_control_study.py",
        "experiments/cyclic_quotient/run_frozen.py",
        "experiments/cyclic_quotient/test_run_frozen.py",
        "experiments/cyclic_pairing/__init__.py",
        "experiments/cyclic_pairing/pairing.py",
        "experiments/cyclic_pairing/forced.py",
        "experiments/cyclic_pairing/study.py",
        "experiments/cyclic_pairing/run_controls.py",
        "experiments/cyclic_pairing/test_pairing.py",
        "experiments/cyclic_pairing/test_forced.py",
        "experiments/cyclic_pairing/test_study.py",
        "experiments/cyclic_pairing/test_run_controls.py",
        "experiments/cyclic_pairing/freeze-v1.json",
        "experiments/homophonic/solver.py",
        "experiments/homophonic/bitset_bound.py",
        "experiments/homophonic/controls.py",
        "experiments/lexicon/run_pilot.py",
        "experiments/lexicon/ambiguity.py",
        "experiments/lexicon/solver.py",
        "experiments/lexicon/bitset_bound.py",
        "src/voynich/__init__.py",
        "src/voynich/reference.py",
        "src/voynich/corpus.py",
        "src/voynich/groups.py",
        "data/reference_manifest.json",
        "reports/homophonic-feasibility-v1/latin-cold.json",
        "reports/homophonic-feasibility-v1/italian-cold.json",
        "reports/cyclic-pairing-control-v1/latin_llct/input.json",
        "reports/cyclic-pairing-control-v1/latin_llct/pairing.json",
        "reports/cyclic-pairing-control-v1/latin_llct/diagnostics.json",
        "reports/cyclic-pairing-control-v1/italian_old/input.json",
        "reports/cyclic-pairing-control-v1/italian_old/pairing.json",
        "reports/cyclic-pairing-control-v1/italian_old/diagnostics.json",
        "data/raw/reference/latin_llct/la_llct-ud-train.conllu",
        "data/raw/reference/latin_llct/la_llct-ud-dev.conllu",
        "data/raw/reference/latin_llct/la_llct-ud-test.conllu",
        "data/raw/reference/latin_llct/README.md",
        "data/raw/reference/latin_llct/LICENSE.txt",
        "data/raw/reference/italian_old/it_old-ud-train.conllu",
        "data/raw/reference/italian_old/it_old-ud-dev.conllu",
        "data/raw/reference/italian_old/it_old-ud-test.conllu",
        "data/raw/reference/italian_old/README.md",
        "data/raw/reference/italian_old/LICENSE.txt",
    )
)


class FreezeFailure(RuntimeError):
    """The external freeze is absent or does not match."""


class ResourceFailure(RuntimeError):
    """The fixed Linux RSS monitor cannot run on this host."""


class SyntheticFailure(FreezeFailure):
    """The frozen synthetic controls did not pass."""


FIT_FEASIBLE_STATUSES = frozenset(
    {"exhaustive", "bound_certified", "budget_exhausted", "no_candidates", "empty_input"}
)
FIT_INFEASIBLE_STATUSES = frozenset({"infeasible_capacity"})
OUTPUT_ABSENT = "absent"
OUTPUT_VALID = "valid"
OUTPUT_INVALID = "invalid"


def canonical_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_path(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def _digest(value: Any) -> bool:
    return isinstance(value, str) and SHA256_PATTERN.fullmatch(value) is not None


def _mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise FreezeFailure(f"freeze field is not an object: {name}")
    return value


def _relative(value: Any) -> str:
    if not isinstance(value, str) or not value or "\\" in value:
        raise FreezeFailure("freeze path is invalid")
    path = Path(value)
    if path.is_absolute() or ".." in path.parts or path.as_posix() != value:
        raise FreezeFailure("freeze path is not repository relative")
    return value


def _regular_frozen_file(root: Path, relative: str) -> Path:
    path = root / relative
    cursor = path.parent
    while cursor != root:
        if cursor.is_symlink():
            raise FreezeFailure("a frozen file has a symlinked parent")
        if cursor == cursor.parent:
            raise FreezeFailure("a frozen file is outside the project root")
        cursor = cursor.parent
    if path.is_symlink() or not path.is_file():
        raise FreezeFailure("a frozen file is missing or not regular")
    return path


def verify_freeze_manifest(project_root: Path = REPOSITORY_ROOT) -> dict[str, Any]:
    """Verify every pinned byte before child imports or source parsing."""

    root = Path(project_root)
    path = root / FREEZE_MANIFEST_PATH
    if path.is_symlink():
        raise FreezeFailure("freeze manifest is a symlink")
    try:
        raw = path.read_bytes()
        manifest = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise FreezeFailure("freeze manifest is unavailable or invalid") from error
    if not isinstance(manifest, Mapping):
        raise FreezeFailure("freeze manifest is not an object")
    if manifest.get("schema_version") != 1 or manifest.get("protocol") != PROTOCOL:
        raise FreezeFailure("freeze identity does not match")
    if manifest.get("command") != list(EXPECTED_COMMAND):
        raise FreezeFailure("freeze command does not match")
    if manifest.get("child_command") != list(EXPECTED_CHILD_COMMAND):
        raise FreezeFailure("freeze child command does not match")
    if dict(_mapping(manifest.get("parameters"), "parameters")) != EXPECTED_PARAMETERS:
        raise FreezeFailure("freeze parameters do not match")
    if dict(_mapping(manifest.get("resources"), "resources")) != EXPECTED_RESOURCES:
        raise FreezeFailure("freeze resources do not match")
    runtime = _mapping(manifest.get("runtime"), "runtime")
    if any(not isinstance(runtime.get(name), str) or not runtime[name]
           for name in ("freeze_python", "implementation", "platform")):
        raise FreezeFailure("freeze runtime is incomplete")
    outputs = _mapping(manifest.get("outputs"), "outputs")
    expected_outputs = {
        "corpora": list(CORPORA),
        "corpus": [path.as_posix() for path in CORPUS_OUTPUT_PATHS],
        "public": PUBLIC_RECEIPT_PATH.as_posix(),
        "private": PRIVATE_RECEIPT_PATH.as_posix(),
    }
    if dict(outputs) != expected_outputs:
        raise FreezeFailure("freeze output paths do not match")
    entries = manifest.get("files")
    if not isinstance(entries, list):
        raise FreezeFailure("freeze files field is not a list")
    hashes: dict[str, str] = {}
    paths: list[str] = []
    for entry in entries:
        if not isinstance(entry, Mapping):
            raise FreezeFailure("freeze file entry is not an object")
        relative, digest = _relative(entry.get("path")), entry.get("sha256")
        if relative in hashes or not _digest(digest):
            raise FreezeFailure("freeze file entry is invalid or duplicated")
        hashes[relative] = digest
        paths.append(relative)
    expected = {item.as_posix() for item in FREEZE_FILES}
    if (
        set(hashes) != expected
        or len(hashes) != len(FREEZE_FILES)
        or paths != [item.as_posix() for item in FREEZE_FILES]
    ):
        raise FreezeFailure("freeze file allowlist does not match")
    if FREEZE_MANIFEST_PATH.as_posix() in hashes:
        raise FreezeFailure("freeze manifest cannot hash itself")
    for relative, expected_hash in hashes.items():
        file_path = _regular_frozen_file(root, relative)
        if sha256_path(file_path) != expected_hash:
            raise FreezeFailure("a frozen file is missing or changed")
    return {
        "manifest_path": FREEZE_MANIFEST_PATH.as_posix(),
        "manifest_sha256": sha256_bytes(raw),
        "protocol": PROTOCOL,
        "file_count": len(hashes),
        "files": [{"path": name, "sha256": hashes[name]} for name in sorted(hashes)],
        "hashes": hashes,
        "parameters": dict(EXPECTED_PARAMETERS),
        "resources": dict(EXPECTED_RESOURCES),
        "runtime": dict(runtime),
    }


def _existing_output(root: Path, relative: Path) -> Path | None:
    current = root
    if current.is_symlink():
        return current
    for part in relative.parts[:-1]:
        current /= part
        if current.is_symlink() or (current.exists() and not current.is_dir()):
            return current
    target = root / relative
    return target if os.path.lexists(target) else None


def preflight_outputs(project_root: Path = REPOSITORY_ROOT) -> tuple[Path, ...]:
    """Reject every fixed output and every symlinked output parent."""

    root = Path(project_root)
    if not root.is_dir():
        raise FileNotFoundError("project root is unavailable")
    if any(_existing_output(root, relative) is not None for relative in ALL_OUTPUT_PATHS):
        raise FileExistsError("a fixed output already exists")
    return tuple(root / relative for relative in ALL_OUTPUT_PATHS)


def ensure_linux_rss_support() -> None:
    if sys.platform != "linux" or platform.system() != "Linux" or not Path("/proc/self/status").is_file():
        raise ResourceFailure("Linux RSS sampling is unavailable")


def sample_rss_bytes(pid: int) -> int | None:
    try:
        text = Path(f"/proc/{pid}/status").read_text(encoding="ascii")
    except (FileNotFoundError, OSError, UnicodeDecodeError):
        return None
    for line in text.splitlines():
        fields = line.split()
        if fields and fields[0] == "VmRSS:" and len(fields) > 1 and fields[1].isdigit():
            return int(fields[1]) * 1024
    return None


def _signal_group_id(pgid: int, signum: int) -> None:
    try:
        os.killpg(pgid, signum)
    except (ProcessLookupError, OSError):
        pass


def _signal_group(process: subprocess.Popen[Any], signum: int) -> None:
    _signal_group_id(process.pid, signum)


def _owned_group_members(pgid: int) -> set[int]:
    """Return live process IDs in the process group created for one child."""

    members: set[int] = set()
    for status_path in Path("/proc").glob("[0-9]*/stat"):
        try:
            text = status_path.read_text(encoding="ascii")
            closing = text.rfind(")")
            fields = text[closing + 2 :].split()
            if closing < 0 or len(fields) < 3 or int(fields[2]) != pgid:
                continue
            members.add(int(status_path.parent.name))
        except (OSError, UnicodeDecodeError, ValueError):
            continue
    return members


def _cleanup_owned_group(pgid: int, grace: float) -> bool:
    """Stop remaining members of one owned group without targeting other groups."""

    deadline = time.monotonic() + max(0.0, grace)
    while True:
        members = _owned_group_members(pgid)
        if not members:
            return True
        _signal_group_id(pgid, signal.SIGTERM)
        if time.monotonic() >= deadline:
            break
        time.sleep(min(0.05, max(0.001, deadline - time.monotonic())))
    _signal_group_id(pgid, signal.SIGKILL)
    deadline = time.monotonic() + max(0.1, grace)
    while _owned_group_members(pgid) and time.monotonic() < deadline:
        time.sleep(0.05)
    return not _owned_group_members(pgid)


def monitor_process(
    process: subprocess.Popen[Any],
    *,
    resources: Mapping[str, Any] = EXPECTED_RESOURCES,
) -> dict[str, Any]:
    """Wait for one child and stop its process group at fixed limits."""

    started = time.monotonic()
    next_sample = started
    maximum = 0
    samples = 0
    reason: str | None = None
    wall = float(resources["corpus_wall_seconds"])
    limit = int(resources["rss_limit_bytes"])
    interval = float(resources["poll_interval_seconds"])
    grace = float(resources["terminate_grace_seconds"])
    while process.poll() is None:
        now = time.monotonic()
        if now >= next_sample:
            rss = sample_rss_bytes(process.pid)
            samples += 1
            if rss is None:
                if process.poll() is not None:
                    break
                reason = "rss_unsupported"
                _signal_group(process, signal.SIGTERM)
                break
            maximum = max(maximum, rss)
            if rss >= limit:
                reason = "rss_limit"
                _signal_group(process, signal.SIGTERM)
                break
            next_sample = now + interval
        if process.poll() is not None:
            break
        if now - started >= wall:
            reason = "wall_timeout"
            _signal_group(process, signal.SIGTERM)
            break
        time.sleep(min(0.05, interval, max(0.001, next_sample - now)))
    if reason is not None:
        try:
            process.wait(timeout=grace)
        except subprocess.TimeoutExpired:
            _signal_group(process, signal.SIGKILL)
            process.wait()
        finally:
            _signal_group(process, signal.SIGKILL)
        group_clean = _cleanup_owned_group(process.pid, grace)
    else:
        process.wait()
        group_clean = _cleanup_owned_group(process.pid, grace)
    return {
        "returncode": process.returncode,
        "termination_reason": reason,
        "elapsed_seconds": time.monotonic() - started,
        "max_rss_bytes": maximum,
        "rss_sample_count": samples,
        "group_clean": group_clean,
    }


def launch_child(
    project_root: Path,
    corpus: str,
    *,
    resources: Mapping[str, Any] = EXPECTED_RESOURCES,
) -> dict[str, Any]:
    """Start one fixed control child in a new process group."""

    ensure_linux_rss_support()
    if corpus not in CORPORA:
        raise ValueError("unknown corpus")
    output_dir = (RESULTS_ROOT / corpus).as_posix()
    command = [
        sys.executable, "-m", "experiments.cyclic_quotient.control_study",
        "--corpus", corpus, "--output-dir", output_dir,
    ]
    environment = dict(os.environ)
    source_path = str(project_root / "src")
    existing_path = environment.get("PYTHONPATH")
    environment["PYTHONPATH"] = os.pathsep.join(
        value for value in (str(project_root), source_path, existing_path) if value
    )
    process = subprocess.Popen(
        command,
        cwd=project_root,
        env=environment,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
        close_fds=True,
    )
    return monitor_process(process, resources=resources)


def run_synthetic_tests(project_root: Path = REPOSITORY_ROOT) -> dict[str, Any]:
    """Run all frozen source-free controls before a child launch."""

    command = [sys.executable, "-m", "unittest", *CONTROL_TEST_MODULES, "-v"]
    try:
        environment = dict(os.environ)
        source_path = str(project_root / "src")
        existing_path = environment.get("PYTHONPATH")
        environment["PYTHONPATH"] = os.pathsep.join(
            value for value in (str(project_root), source_path, existing_path) if value
        )
        completed = subprocess.run(
            command,
            cwd=project_root,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise SyntheticFailure("synthetic tests did not complete") from error
    output = completed.stdout + completed.stderr
    match = re.search(rb"Ran\s+(\d+)\s+tests?", output)
    if completed.returncode != 0 or match is None or int(match.group(1)) < 1:
        raise SyntheticFailure("synthetic tests failed")
    return {"status": "pass", "count": int(match.group(1)), "returncode": 0}


def _read_json(path: Path) -> dict[str, Any]:
    """Read one fixed output and preserve absent, valid, and invalid states."""

    if not os.path.lexists(path):
        return {"state": OUTPUT_ABSENT, "value": None, "sha256": None}
    if path.is_symlink() or not path.is_file():
        return {"state": OUTPUT_INVALID, "value": None, "sha256": None}
    try:
        raw = path.read_bytes()
        digest = sha256_bytes(raw)
        value = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        try:
            digest = sha256_path(path)
        except OSError:
            digest = None
        return {"state": OUTPUT_INVALID, "value": None, "sha256": digest}
    if not isinstance(value, dict):
        return {"state": OUTPUT_INVALID, "value": None, "sha256": digest}
    return {"state": OUTPUT_VALID, "value": value, "sha256": digest}


def _output_metadata(relative: Path, record: Mapping[str, Any]) -> dict[str, Any]:
    item: dict[str, Any] = {
        "path": relative.as_posix(),
        "present": record.get("state") != OUTPUT_ABSENT,
        "state": record.get("state"),
    }
    if record.get("sha256") is not None:
        item["sha256"] = record["sha256"]
    return item


def _corpus_directory_state(root: Path, corpus: str) -> tuple[bool, bool]:
    """Return directory-invalid and unexpected-file flags without exposing names."""

    directory = root / RESULTS_ROOT / corpus
    if not os.path.lexists(directory):
        return False, False
    if directory.is_symlink() or not directory.is_dir():
        return True, False
    try:
        names = {item.name for item in directory.iterdir()}
    except OSError:
        return True, False
    return False, bool(names - set(CORPUS_OUTPUT_NAMES))


def _common_record(value: Mapping[str, Any], corpus: str, freeze_hash: str) -> bool:
    if value.get("protocol") != PROTOCOL:
        return False
    if "corpus" in value and value.get("corpus") != corpus:
        return False
    hashes = [
        value[name]
        for name in ("freeze_manifest_sha256", "manifest_sha256")
        if name in value
    ]
    if any(not _digest(item) for item in hashes):
        return False
    outer_hash = value.get("outer_freeze_manifest_sha256")
    return outer_hash is None or outer_hash == freeze_hash


def _nonnegative_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _unit_list(value: Any) -> bool:
    return isinstance(value, list) and all(
        isinstance(item, str) and item in UNITS for item in value
    ) and len(set(value)) == len(value)


def _class_name(members: Sequence[str]) -> str:
    return "+".join(sorted(members))


def _validate_quotient(value: Mapping[str, Any], corpus: str, freeze_hash: str) -> bool:
    if not _common_record(value, corpus, freeze_hash):
        return False
    if value.get("record_kind") != "aggregate_cyclic_quotient_evidence":
        return False
    status = value.get("quotient_status")
    if status not in QUOTIENT_STATUSES:
        return False
    if (
        value.get("declared_unit_count") != 52
        or value.get("declared_units_sha256") != EXPECTED_DECLARED_UNITS_SHA256
    ):
        return False
    observed, unseen = value.get("observed_units"), value.get("unseen_units")
    if not _unit_list(observed) or not _unit_list(unseen) or set(observed) & set(unseen):
        return False
    if value.get("observed_unit_count", len(observed)) != len(observed):
        return False
    if value.get("unseen_unit_count", len(unseen)) != len(unseen):
        return False
    if len(observed) + len(unseen) != 52:
        return False
    classes = value.get("classes")
    if not isinstance(classes, list):
        return False
    members: list[str] = []
    for item in classes:
        if not isinstance(item, list) or len(item) not in (1, 2):
            return False
        if item != sorted(item) or any(unit not in observed for unit in item):
            return False
        if len(set(item)) != len(item):
            return False
        members.extend(item)
    if len(members) != len(set(members)):
        return False
    if status == "proved":
        if set(members) != set(observed) or len(classes) > 26:
            return False
        if value.get("class_count", len(classes)) != len(classes):
            return False
    elif classes:
        return False
    for field in ("forced_pairs", "singleton_units", "unknown_edges"):
        if field in value and not isinstance(value[field], list):
            return False
    return True


def _fit_details(
    value: Mapping[str, Any], quotient: Mapping[str, Any], corpus: str, freeze_hash: str,
    quotient_hash: str,
) -> dict[str, Any] | None:
    if not _common_record(value, corpus, freeze_hash):
        return None
    if value.get("record_kind") != "aggregate_quotient_lexicon_fit":
        return None
    if value.get("quotient_evidence_sha256") != quotient_hash:
        return None
    classes = quotient.get("classes", [])
    if value.get("class_count") != len(classes):
        return None
    expected_open_slots = sum(len(item) == 1 for item in classes)
    if value.get("open_slot_count") != expected_open_slots:
        return None
    if value.get("observed_unit_count") != len(quotient.get("observed_units", [])):
        return None
    solver_config = value.get("solver_config")
    if not isinstance(solver_config, Mapping):
        return None
    for key, expected in (("capacity", 1), ("bound_engine", "bitset"), ("node_budget", 100_000)):
        if solver_config.get(key) != expected:
            return None
    solver = value.get("solver")
    if not isinstance(solver, Mapping):
        return None
    status = value.get("status")
    if status != solver.get("status"):
        return None
    feasible = solver.get("feasible")
    certified = solver.get("score_certified")
    exhausted = solver.get("search_exhausted")
    if not all(isinstance(item, bool) for item in (feasible, certified, exhausted)):
        return None
    lower, upper, score = (
        solver.get("lower_bound"), solver.get("upper_bound"), solver.get("score")
    )
    if feasible:
        if status not in FIT_FEASIBLE_STATUSES:
            return None
        if not all(_nonnegative_int(item) for item in (lower, upper, score)):
            return None
        if not lower <= score <= upper:
            return None
        expected_certified = lower == upper == score
        if certified != expected_certified:
            return None
        if exhausted != (status == "exhaustive"):
            return None
    else:
        if status not in FIT_INFEASIBLE_STATUSES:
            return None
        if certified or not exhausted or any(item is not None for item in (lower, upper, score)):
            return None
    return {
        "status": status,
        "feasible": feasible,
        "score_certified": certified,
        "search_exhausted": exhausted,
        "lower_bound": lower,
        "upper_bound": upper,
        "score": score,
    }


def _validate_fit(
    value: Mapping[str, Any], quotient: Mapping[str, Any], corpus: str, freeze_hash: str,
    quotient_hash: str,
) -> bool:
    return _fit_details(value, quotient, corpus, freeze_hash, quotient_hash) is not None


def _validate_key(
    value: Mapping[str, Any], quotient: Mapping[str, Any], corpus: str,
    freeze_hash: str, quotient_hash: str, fit: Mapping[str, Any] | None = None,
) -> bool:
    if not _common_record(value, corpus, freeze_hash):
        return False
    if value.get("record_kind") != "complete_observed_quotient_key":
        return False
    if value.get("quotient_evidence_sha256") != quotient_hash:
        return False
    classes = quotient.get("classes", [])
    expected = {_class_name(item) for item in classes}
    key = value.get("class_key")
    if not isinstance(key, Mapping) or set(key) != expected:
        return False
    if value.get("quotient_status") != "proved":
        return False
    if value.get("class_names") != sorted(expected):
        return False
    members = value.get("class_members")
    expected_members = {
        _class_name(item): list(item) for item in quotient["classes"]
    }
    if not isinstance(members, Mapping) or set(members) != expected:
        return False
    if any(members[name] != expected_members[name] for name in expected):
        return False
    if value.get("open_slot_count") != sum(2 - len(item) for item in quotient["classes"]):
        return False
    observed_key = value.get("observed_unit_key")
    if not isinstance(observed_key, Mapping):
        return False
    letters = list(key.values())
    if not all(isinstance(item, str) and len(item) == 1 and "a" <= item <= "z" for item in letters):
        return False
    if len(set(letters)) != len(letters):
        return False
    induced = {
        unit: key[name]
        for name, class_members in expected_members.items()
        for unit in class_members
    }
    if dict(observed_key) != induced:
        return False
    coverage = value.get("coverage")
    expected_coverage = {
        "declared_unit_count": 52,
        "observed_unit_count": len(quotient.get("observed_units", [])),
        "unseen_unit_count": len(quotient.get("unseen_units", [])),
        "mapped_observed_units": len(induced),
    }
    if not isinstance(coverage, Mapping) or set(coverage) != set(expected_coverage):
        return False
    if any(coverage[field] != expected for field, expected in expected_coverage.items()):
        return False
    if fit is not None:
        if value.get("fit_status") != fit.get("status"):
            return False
        if value.get("score_certified") != fit.get("score_certified"):
            return False
    return True


def _valid_hash_mapping(value: Any) -> bool:
    if not isinstance(value, Mapping) or not value:
        return False
    for name, digest in value.items():
        path = Path(name) if isinstance(name, str) else None
        if (
            path is None
            or path.is_absolute()
            or ".." in path.parts
            or path.as_posix() != name
            or not _digest(digest)
        ):
            return False
    return True


def _count(value: Any) -> bool:
    return _nonnegative_int(value)


def _validate_score_partition(value: Any) -> bool:
    if not isinstance(value, Mapping):
        return False
    character, word, coverage, hits = (
        value.get("character"), value.get("word"),
        value.get("coverage"), value.get("dictionary_hits"),
    )
    if not all(isinstance(item, Mapping) for item in (character, word, coverage, hits)):
        return False
    if not all(_count(character.get(field)) for field in ("correct", "denominator")):
        return False
    if character["correct"] > character["denominator"]:
        return False
    if not all(_count(word.get(field)) for field in ("correct", "denominator")):
        return False
    if word["correct"] > word["denominator"]:
        return False
    coverage_fields = (
        "mapped_positions", "total_positions", "unexplained_positions",
        "complete_words", "word_denominator",
    )
    if not all(_count(coverage.get(field)) for field in coverage_fields):
        return False
    if coverage["mapped_positions"] + coverage["unexplained_positions"] != coverage["total_positions"]:
        return False
    if coverage["complete_words"] > coverage["word_denominator"]:
        return False
    if coverage["total_positions"] != character["denominator"]:
        return False
    if coverage["word_denominator"] != word["denominator"]:
        return False
    if not all(_count(hits.get(field)) for field in ("hits", "denominator", "complete_word_denominator")):
        return False
    if hits["hits"] > hits["complete_word_denominator"]:
        return False
    return (
        hits["denominator"] == word["denominator"]
        and hits["complete_word_denominator"] == coverage["complete_words"]
    )


def _validate_diagnostics(
    value: Mapping[str, Any], quotient: Mapping[str, Any], corpus: str,
    freeze_hash: str, quotient_hash: str, fit: Mapping[str, Any] | None = None,
) -> bool:
    if not _common_record(value, corpus, freeze_hash):
        return False
    if (
        value.get("record_type") != "diagnostics"
        or value.get("corpus") != corpus
        or value.get("status") != "complete"
        or value.get("quotient_evidence_sha256") != quotient_hash
    ):
        return False
    for field in ("source_manifest_sha256", "validation_stream_sha256"):
        if field in value and not _digest(value[field]):
            return False
    for field in ("source_file_hashes", "code_hashes"):
        if field in value and not _valid_hash_mapping(value[field]):
            return False
    if fit is None:
        return False
    if value.get("fit_status") != fit["status"]:
        return False
    if value.get("score_certified") != fit["score_certified"]:
        return False
    if value.get("lower_bound") != fit["lower_bound"] or value.get("upper_bound") != fit["upper_bound"]:
        return False
    if value.get("completion") != ("complete" if fit["score_certified"] else "incomplete_search"):
        return False
    settings = value.get("settings")
    if not isinstance(settings, Mapping):
        return False
    expected_settings = {
        "bound_engine": "bitset",
        "fit_capacity": 1,
        "quotient_node_budget": 100_000,
        "solver_node_budget": 100_000,
    }
    if any(settings.get(field) != expected for field, expected in expected_settings.items()):
        return False
    if not _validate_score_partition(value.get("validation")):
        return False
    if not _validate_score_partition(value.get("test")):
        return False
    planted = value.get("postfit_planted_map")
    if not isinstance(planted, Mapping):
        return False
    if not all(_count(planted.get(field)) for field in (
        "correct", "denominator", "observed_unit_count", "unseen_unit_count"
    )):
        return False
    if planted["correct"] > planted["denominator"] or planted["denominator"] > planted["observed_unit_count"]:
        return False
    return planted["observed_unit_count"] + planted["unseen_unit_count"] == 52


def validate_corpus_outputs(
    project_root: Path, corpus: str, freeze: Mapping[str, Any]
) -> dict[str, Any]:
    """Validate the fixed output matrix without exposing record contents."""

    root = Path(project_root)
    paths = {name: root / RESULTS_ROOT / corpus / name for name in CORPUS_OUTPUT_NAMES}
    records = {name: _read_json(path) for name, path in paths.items()}
    outputs = [
        _output_metadata(RESULTS_ROOT / corpus / name, records[name])
        for name in CORPUS_OUTPUT_NAMES
    ]
    invalid_directory, unexpected_outputs = _corpus_directory_state(root, corpus)
    base: dict[str, Any] = {
        "complete": False,
        "numeric_valid": False,
        "outputs": outputs,
        "unexpected_outputs": unexpected_outputs,
        "quotient_status": None,
        "fit_status": None,
        "score_certified": None,
        "bounds": None,
    }
    if invalid_directory or unexpected_outputs:
        base["reason"] = "unexpected_output"
        return base
    quotient_record = records["quotient.json"]
    if quotient_record["state"] != OUTPUT_VALID:
        base["reason"] = (
            "quotient_missing" if quotient_record["state"] == OUTPUT_ABSENT
            else "quotient_invalid"
        )
        return base
    quotient = quotient_record["value"]
    assert isinstance(quotient, dict)
    freeze_hash = str(freeze["manifest_sha256"])
    if not _validate_quotient(quotient, corpus, freeze_hash):
        base["reason"] = "quotient_invalid"
        return base
    quotient_hash = str(quotient_record["sha256"])
    quotient_status = quotient["quotient_status"]
    base["complete"] = True
    base["quotient_status"] = quotient_status
    fit_record, key_record, diagnostics_record = (
        records["fit.json"], records["fit.keys.json"], records["diagnostics.json"]
    )
    if quotient_status in ABSTENTION_STATUSES:
        if any(record["state"] != OUTPUT_ABSENT for record in (fit_record, key_record, diagnostics_record)):
            base["reason"] = "abstention_output_matrix"
            return base
        base["numeric_valid"] = True
        base["abstained"] = True
        return base
    if fit_record["state"] != OUTPUT_VALID:
        base["reason"] = "fit_missing_or_invalid"
        return base
    fit_value = fit_record["value"]
    assert isinstance(fit_value, dict)
    fit = _fit_details(fit_value, quotient, corpus, freeze_hash, quotient_hash)
    if fit is None:
        base["reason"] = "fit_invalid"
        return base
    base["fit_status"] = fit["status"]
    base["score_certified"] = fit["score_certified"]
    base["bounds"] = {
        field: fit[field] for field in ("lower_bound", "upper_bound", "score")
    }
    if not fit["feasible"]:
        if key_record["state"] != OUTPUT_ABSENT or diagnostics_record["state"] != OUTPUT_ABSENT:
            base["reason"] = "infeasible_output_matrix"
            return base
        base["numeric_valid"] = True
        base["abstained"] = False
        return base
    if key_record["state"] != OUTPUT_VALID or diagnostics_record["state"] != OUTPUT_VALID:
        base["reason"] = "feasible_output_matrix"
        return base
    key_value, diagnostics_value = key_record["value"], diagnostics_record["value"]
    assert isinstance(key_value, dict) and isinstance(diagnostics_value, dict)
    if not _validate_key(key_value, quotient, corpus, freeze_hash, quotient_hash, fit):
        base["reason"] = "key_invalid"
        return base
    if not _validate_diagnostics(
        diagnostics_value, quotient, corpus, freeze_hash, quotient_hash, fit
    ):
        base["reason"] = "diagnostics_invalid"
        return base
    base["numeric_valid"] = True
    base["abstained"] = False
    return base

def _corpus_status(run: Mapping[str, Any], validation: Mapping[str, Any]) -> str:
    if run.get("termination_reason") in {"wall_timeout", "rss_limit", "rss_unsupported"}:
        return "resource_abstain"
    if run.get("returncode") != 0 or not validation.get("numeric_valid"):
        return "implementation_failure"
    return "complete"


def _execution_status(run: Mapping[str, Any]) -> str:
    if run.get("termination_reason") in {"wall_timeout", "rss_limit", "rss_unsupported"}:
        return "resource_abstain"
    if run.get("returncode") is None:
        return "launch_failure"
    if run.get("returncode") == 0:
        return "exited_zero"
    return "exit_nonzero"


def _write_exclusive(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(canonical_json_bytes(value))


def run_controls(
    project_root: Path = REPOSITORY_ROOT,
    *,
    synthetic_runner: Any | None = None,
    child_runner: Any | None = None,
) -> dict[str, Any]:
    """Verify the freeze, run both children once, and save safe receipts."""

    root = Path(project_root)
    ensure_linux_rss_support()
    freeze = verify_freeze_manifest(root)
    preflight_outputs(root)
    if synthetic_runner is None:
        synthetic_runner = run_synthetic_tests
    if child_runner is None:
        child_runner = launch_child
    synthetic = synthetic_runner(root)
    corpus_results: list[dict[str, Any]] = []
    private_results: list[dict[str, Any]] = []
    for corpus in CORPORA:
        try:
            run = child_runner(root, corpus, resources=freeze["resources"])
        except Exception as error:
            run = {
                "returncode": None,
                "termination_reason": "launch_failure",
                "exception_type": type(error).__name__,
            }
        validation = validate_corpus_outputs(root, corpus, freeze)
        status = _corpus_status(run, validation)
        numeric_valid = bool(status == "complete" and validation["numeric_valid"])
        corpus_results.append({
            "corpus": corpus,
            "status": status,
            "execution_status": _execution_status(run),
            "numeric_outputs_valid": numeric_valid,
            "quotient_status": validation.get("quotient_status"),
            "fit_status": validation.get("fit_status"),
            "score_certified": validation.get("score_certified"),
            "bounds": validation.get("bounds"),
            "outputs": validation["outputs"],
        })
        private_results.append({"corpus": corpus, "status": status, "run": dict(run), "validation": dict(validation)})
    all_valid = all(item["numeric_outputs_valid"] for item in corpus_results)
    if all_valid:
        status = "complete"
    elif any(item["status"] == "resource_abstain" for item in corpus_results):
        status = "resource_abstain"
    else:
        status = "implementation_failure"
    public = {
        "schema_version": 1,
        "protocol": PROTOCOL,
        "command": list(EXPECTED_COMMAND),
        "child_command": list(EXPECTED_CHILD_COMMAND),
        "status": status,
        "execution_status": status,
        "numeric_outputs_valid": all_valid,
        "freeze": {
            "manifest_path": freeze["manifest_path"],
            "manifest_sha256": freeze["manifest_sha256"],
            "file_count": freeze["file_count"],
        },
        "parameters": dict(EXPECTED_PARAMETERS),
        "limits": dict(EXPECTED_RESOURCES),
        "synthetic_tests": synthetic,
        "corpora": corpus_results,
        "scope": "Finite known-corpus control only. No manuscript stream or language claim.",
    }
    private = {
        "schema_version": 1,
        "protocol": PROTOCOL,
        "status": status,
        "runtime": {
            "python": platform.python_version(),
            "implementation": platform.python_implementation(),
            "platform": platform.platform(),
        },
        "freeze": freeze,
        "synthetic_tests": synthetic,
        "corpora": private_results,
    }
    _write_exclusive(root / PUBLIC_RECEIPT_PATH, public)
    _write_exclusive(root / PRIVATE_RECEIPT_PATH, private)
    return public


def main(argv: Sequence[str] | None = None) -> int:
    """Run the fixed command without public options."""

    if argv is not None and len(argv):
        print(canonical_json_bytes({"status": "input_mismatch", "reason": "no_options"}).decode(), end="")
        return 2
    if argv is None and len(sys.argv) != 1:
        print(canonical_json_bytes({"status": "input_mismatch", "reason": "no_options"}).decode(), end="")
        return 2
    try:
        public = run_controls(REPOSITORY_ROOT)
    except SyntheticFailure:
        public = {
            "schema_version": 1,
            "protocol": PROTOCOL,
            "status": "implementation_failure",
            "execution_status": "implementation_failure",
            "numeric_outputs_valid": False,
            "reason": "synthetic_tests_failed",
        }
    except FreezeFailure:
        public = {
            "schema_version": 1,
            "protocol": PROTOCOL,
            "status": "input_mismatch",
            "execution_status": "input_mismatch",
            "numeric_outputs_valid": False,
            "reason": "freeze_verification_failed",
        }
    except ResourceFailure:
        public = {
            "schema_version": 1,
            "protocol": PROTOCOL,
            "status": "resource_abstain",
            "execution_status": "resource_abstain",
            "numeric_outputs_valid": False,
            "reason": "linux_rss_monitor_unavailable",
        }
    except FileExistsError:
        public = {
            "schema_version": 1,
            "protocol": PROTOCOL,
            "status": "output_exists",
            "execution_status": "input_mismatch",
            "numeric_outputs_valid": False,
            "reason": "fixed_output_exists",
        }
    except (FileNotFoundError, OSError):
        public = {
            "schema_version": 1,
            "protocol": PROTOCOL,
            "status": "implementation_failure",
            "execution_status": "implementation_failure",
            "numeric_outputs_valid": False,
            "reason": "output_preflight_failed",
        }
    print(canonical_json_bytes(public).decode(), end="")
    return 0 if public.get("numeric_outputs_valid") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "ALL_OUTPUT_PATHS", "CORPORA", "CORPUS_OUTPUT_NAMES", "CORPUS_OUTPUT_PATHS",
    "EXPECTED_CHILD_COMMAND", "EXPECTED_COMMAND", "EXPECTED_DECLARED_UNITS_SHA256",
    "EXPECTED_PARAMETERS", "EXPECTED_RESOURCES", "FREEZE_FILES", "FREEZE_MANIFEST_PATH",
    "FreezeFailure", "PRIVATE_RECEIPT_PATH", "PROTOCOL", "PUBLIC_RECEIPT_PATH",
    "RESULTS_ROOT", "ResourceFailure", "canonical_json_bytes", "ensure_linux_rss_support",
    "launch_child", "main", "monitor_process", "preflight_outputs", "run_controls",
    "run_synthetic_tests", "sample_rss_bytes", "sha256_bytes", "sha256_path",
    "validate_corpus_outputs", "verify_freeze_manifest",
]
