"""Run one bounded Celsus known-cipher control."""

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
PROTOCOL = "celsus-reference-control-v1"
FREEZE_MANIFEST_PATH = Path("experiments/medical/control-freeze-v1.json")
RESULTS_ROOT = Path("results/celsus-reference-control-v1")
MODEL_ROOT = RESULTS_ROOT / "model"
COLD_PATH = MODEL_ROOT / "cold.json"
KEY_PATH = MODEL_ROOT / "cold.keys.json"
PUBLIC_RECEIPT_PATH = MODEL_ROOT / "supervision.json"
PRIVATE_RECEIPT_PATH = MODEL_ROOT / "resources.private.json"
PARTITION_MANIFEST_PATH = RESULTS_ROOT / "partition-manifest.json"
PARTITIONS_PATH = RESULTS_ROOT / "partitions.private.json"
PARAGRAPHS_PATH = RESULTS_ROOT / "paragraphs.private.jsonl"

EXPECTED_COMMAND = ("python", "-m", "experiments.medical.run_control")
EXPECTED_CHILD_COMMAND = ("python", "-m", "experiments.medical.control_study")
EXPECTED_PARAMETERS = {
    "family": "cap2", "seed": 7000, "capacity": 2,
    "declared_unit_count": 52, "node_budget": 1000,
    "bound_engine": "bitset", "warm_start": "none",
    "input_scope": "celsus_fixed_partitions",
    "test_score_order": "key_record_before_test_diagnostics",
}
EXPECTED_RESOURCES = {
    "wall_seconds": 1500.0, "rss_limit_bytes": 7 * 1024**3,
    "poll_interval_seconds": 0.25, "terminate_grace_seconds": 5.0,
    "as_limit_bytes": None, "child_cpu_workers": 1, "retry_count": 0,
}
OUTPUT_PATHS = (COLD_PATH, KEY_PATH, PUBLIC_RECEIPT_PATH, PRIVATE_RECEIPT_PATH)
# Keep the explicit name for callers that inspect all fixed outputs.
ALL_OUTPUT_PATHS = OUTPUT_PATHS

# The external manifest excludes itself. The list covers the child imports,
# partition freeze, partition outputs, comparator records, and fixed plans.
FREEZE_FILES = tuple(
    Path(value) for value in (
        "docs/plans/celsus-model-run-v1.md",
        "docs/plans/celsus-reference-control-v1.md",
        "docs/plans/visual-homophonic-pilot.md",
        "experiments/medical/control_study.py",
        "experiments/medical/test_control_study.py",
        "experiments/medical/run_control.py",
        "experiments/medical/test_run_control.py",
        "experiments/medical/partition-freeze-v1.json",
        "results/celsus-reference-control-v1/partition-manifest.json",
        "results/celsus-reference-control-v1/partitions.private.json",
        "results/celsus-reference-control-v1/paragraphs.private.jsonl",
        "experiments/medical/reference_adapter.py",
        "experiments/medical/test_reference_adapter.py",
        "experiments/medical/run_partition.py",
        "experiments/medical/test_run_partition.py",
        "src/voynich/__init__.py", "src/voynich/reference.py",
        "reports/celsus-projection-v1/acceptance.json",
        "reports/celsus-projection-v1/initial-receipt.json",
        "experiments/medical/freeze-v1.json",
        "docs/plans/celsus-projection-v1.md",
        "experiments/medical/tei_projection.py",
        "experiments/medical/run_projection.py",
        "experiments/medical/test_tei_projection.py",
        "experiments/medical/test_run_projection.py",
        "results/celsus-projection-v1/celsus-lat5.xml",
        "results/celsus-projection-v1/module-paragraphs.jsonl",
        "results/celsus-projection-v1/independent-paragraphs.jsonl",
        "experiments/homophonic/run_controls.py",
        "experiments/homophonic/controls.py",
        "experiments/homophonic/solver.py",
        "experiments/homophonic/bitset_bound.py",
        "experiments/homophonic/ambiguity.py",
        "experiments/homophonic/anneal.py",
        "experiments/lexicon/run_pilot.py",
        "experiments/lexicon/ambiguity.py",
        "experiments/lexicon/solver.py",
        "experiments/lexicon/bitset_bound.py",
        "src/voynich/corpus.py", "src/voynich/groups.py",
        "src/voynich/substitution.py",
        "reports/homophonic-feasibility-v1/latin-cold.json",
        "reports/homophonic-feasibility-v1/italian-cold.json",
    )
)
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
GATE_FIELDS = {"observed_positions_pass", "fully_observed_tokens_pass", "full_decoding_pass"}
EXPECTED_CODE_PATHS = frozenset({
    "experiments/homophonic/ambiguity.py",
    "experiments/homophonic/anneal.py",
    "experiments/homophonic/bitset_bound.py",
    "experiments/homophonic/controls.py",
    "experiments/homophonic/run_controls.py",
    "experiments/homophonic/solver.py",
    "experiments/lexicon/run_pilot.py",
    "src/voynich/corpus.py",
    "src/voynich/groups.py",
    "src/voynich/reference.py",
    "src/voynich/substitution.py",
})


class FreezeFailure(RuntimeError):
    """A reviewed file or fixed input is missing or changed."""


class ResourceFailure(RuntimeError):
    """The fixed resident-memory monitor cannot run on this host."""


def canonical_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True,
                       separators=(",", ":")) + "\n").encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_path(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def _digest(value: Any) -> bool:
    return isinstance(value, str) and SHA256_PATTERN.fullmatch(value) is not None


def _nonnegative_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _object(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise FreezeFailure(f"freeze field is not an object: {name}")
    return value


def _relative(value: Any) -> str:
    if not isinstance(value, str) or not value:
        raise FreezeFailure("freeze path is invalid")
    path = Path(value)
    if path.is_absolute() or ".." in path.parts or path.as_posix() != value:
        raise FreezeFailure("freeze path is not repository relative")
    return value


def verify_control_freeze(project_root: Path = REPOSITORY_ROOT) -> dict[str, Any]:
    """Verify the exact external freeze before any child import or launch."""

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
    if manifest.get("command") != list(EXPECTED_COMMAND) or manifest.get("child_command") != list(EXPECTED_CHILD_COMMAND):
        raise FreezeFailure("freeze command does not match")
    if dict(_object(manifest.get("parameters"), "parameters")) != EXPECTED_PARAMETERS:
        raise FreezeFailure("freeze parameters do not match")
    if dict(_object(manifest.get("resources"), "resources")) != EXPECTED_RESOURCES:
        raise FreezeFailure("freeze resources do not match")
    runtime = _object(manifest.get("runtime"), "runtime")
    if any(not isinstance(runtime.get(name), str) or not runtime[name]
           for name in ("freeze_python", "implementation", "platform")):
        raise FreezeFailure("freeze runtime is incomplete")
    outputs = {
        "cold": COLD_PATH.as_posix(), "keys": KEY_PATH.as_posix(),
        "public": PUBLIC_RECEIPT_PATH.as_posix(),
        "private": PRIVATE_RECEIPT_PATH.as_posix(),
    }
    if dict(_object(manifest.get("outputs"), "outputs")) != outputs:
        raise FreezeFailure("freeze output paths do not match")
    entries = manifest.get("files")
    if not isinstance(entries, list):
        raise FreezeFailure("freeze files field is not a list")
    hashes: dict[str, str] = {}
    for entry in entries:
        if not isinstance(entry, Mapping):
            raise FreezeFailure("freeze file entry is not an object")
        relative, digest = _relative(entry.get("path")), entry.get("sha256")
        if not _digest(digest) or relative in hashes:
            raise FreezeFailure("freeze file entry is invalid or duplicated")
        hashes[relative] = digest
    expected = {path.as_posix() for path in FREEZE_FILES}
    if set(hashes) != expected or len(hashes) != len(FREEZE_FILES):
        raise FreezeFailure("freeze file allowlist does not match")
    if FREEZE_MANIFEST_PATH.as_posix() in hashes:
        raise FreezeFailure("freeze manifest cannot hash itself")
    for relative, expected_hash in hashes.items():
        file_path = root / relative
        if file_path.is_symlink() or not file_path.is_file() or sha256_path(file_path) != expected_hash:
            raise FreezeFailure("a frozen file is missing or changed")
    return {
        "manifest_path": FREEZE_MANIFEST_PATH.as_posix(),
        "manifest_sha256": sha256_bytes(raw), "protocol": PROTOCOL,
        "file_count": len(hashes),
        "files": [{"path": p, "sha256": hashes[p]} for p in sorted(hashes)],
        "hashes": hashes, "parameters": dict(EXPECTED_PARAMETERS),
        "resources": dict(EXPECTED_RESOURCES), "runtime": dict(runtime),
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
    """Reject fixed output files and symlinked output parents."""

    root = Path(project_root)
    if not root.is_dir():
        raise FileNotFoundError("project root is unavailable")
    if any(_existing_output(root, relative) is not None for relative in ALL_OUTPUT_PATHS):
        raise FileExistsError("a fixed output already exists")
    return tuple(root / relative for relative in ALL_OUTPUT_PATHS)


def ensure_linux_rss_support() -> None:
    if platform.system() != "Linux" or not Path("/proc/self/status").is_file():
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


def _signal_group(process: subprocess.Popen[Any], signum: int) -> None:
    try:
        os.killpg(process.pid, signum)
    except (ProcessLookupError, OSError):
        pass


def monitor_process(process: subprocess.Popen[Any], *, resources: Mapping[str, Any] = EXPECTED_RESOURCES) -> dict[str, Any]:
    """Monitor one process and terminate its process group at a fixed limit."""

    started, next_sample = time.monotonic(), time.monotonic()
    maximum, samples, reason = 0, 0, None
    wall, limit = float(resources["wall_seconds"]), int(resources["rss_limit_bytes"])
    interval, grace = float(resources["poll_interval_seconds"]), float(resources["terminate_grace_seconds"])
    while process.poll() is None:
        now = time.monotonic()
        if now >= next_sample:
            rss, samples = sample_rss_bytes(process.pid), samples + 1
            if rss is None:
                if process.poll() is not None:
                    break
                reason = "rss_unsupported"
                _signal_group(process, signal.SIGTERM)
                break
            maximum = max(maximum, rss)
            if process.poll() is not None:
                break
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
    if reason:
        try:
            process.wait(timeout=grace)
        except subprocess.TimeoutExpired:
            _signal_group(process, signal.SIGKILL)
            process.wait()
        finally:
            _signal_group(process, signal.SIGKILL)
    else:
        process.wait()
    return {"returncode": process.returncode, "termination_reason": reason,
            "elapsed_seconds": time.monotonic() - started,
            "max_rss_bytes": maximum, "rss_sample_count": samples}


def launch_child(project_root: Path, *, resources: Mapping[str, Any] = EXPECTED_RESOURCES) -> dict[str, Any]:
    """Start the fixed child in a new process group."""

    process = subprocess.Popen(
        [sys.executable, "-m", "experiments.medical.control_study"], cwd=project_root,
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        start_new_session=True, close_fds=True,
    )
    return monitor_process(process, resources=resources)


def _read_json(path: Path) -> dict[str, Any] | None:
    if path.is_symlink() or not path.is_file():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _partition_pins(root: Path, freeze: Mapping[str, Any]) -> dict[str, str] | None:
    try:
        path, private = root / PARTITION_MANIFEST_PATH, root / PARTITIONS_PATH
        paragraphs = root / PARAGRAPHS_PATH
        if any(item.is_symlink() for item in (path, private, paragraphs)):
            return None
        raw, manifest = path.read_bytes(), json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(manifest, Mapping) or manifest.get("schema_version") != 1 or manifest.get("protocol") != PROTOCOL or manifest.get("raw_text_included") is not False:
            return None
        entries = manifest.get("private_outputs")
        if not isinstance(entries, Mapping):
            return None
        result, hashes = {"manifest": sha256_bytes(raw)}, freeze.get("hashes", {})
        if hashes.get(PARTITION_MANIFEST_PATH.as_posix()) != result["manifest"]:
            return None
        for name, item_path in (("partitions.private.json", private), ("paragraphs.private.jsonl", paragraphs)):
            item, digest = entries.get(name), sha256_path(item_path)
            if not isinstance(item, Mapping) or item.get("sha256") != digest or hashes.get(item_path.relative_to(root).as_posix()) != digest:
                return None
            result[name] = digest
        return result
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError):
        return None


def _gate(value: Any) -> bool:
    return isinstance(value, Mapping) and set(value) == GATE_FIELDS and all(item is None or isinstance(item, bool) for item in value.values())


def _valid_child(report: Mapping[str, Any], key_record: Mapping[str, Any]) -> bool:
    fixed = {"kind": "synthetic_reference_control", "family": "cap2", "seed": 7000, "node_budget": 1000, "bound_engine": "bitset", "warm_start": "none"}
    if any(report.get(name) != expected for name, expected in fixed.items()) or any(key_record.get(name) != report.get(name) for name in fixed):
        return False
    if key_record.get("fit_scope") != "encrypted validation words and plaintext training lexicon":
        return False
    solver, objective = report.get("solver"), report.get("objective")
    if not isinstance(solver, Mapping) or not isinstance(objective, Mapping) or solver.get("feasible") is not True:
        return False
    config = solver.get("config")
    if not isinstance(config, Mapping) or any(config.get(name) != expected for name, expected in {"capacity": 2, "bound_engine": "bitset", "node_budget": 1000, "initial_key_role": "completed warm-start incumbent only; root search has no fixed assignments"}.items()):
        return False
    score, lower, upper = (solver.get(name) for name in ("score", "lower_bound", "upper_bound"))
    certified, exhausted = solver.get("score_certified"), solver.get("search_exhausted")
    if not all(_nonnegative_int(value) for value in (score, lower, upper)) or not lower <= score <= upper or not isinstance(certified, bool) or not isinstance(exhausted, bool) or certified != (score == upper) or (exhausted and not certified):
        return False
    if objective.get("score_from_key") != score or objective.get("weights_match_denominator") is not True or not _nonnegative_int(objective.get("weights_total")):
        return False
    for name in ("nodes", "pruned_nodes", "frontier_node_count", "hit_type_count", "candidate_count_total", "candidate_type_count", "missing_candidate_count", "cipher_type_count", "total_weight"):
        if not _nonnegative_int(solver.get(name)):
            return False
    key = key_record.get("key")
    if not isinstance(key, Mapping) or not key or any(not isinstance(unit, str) or not re.fullmatch(r"c(?:0[0-9]|[1-4][0-9]|5[01])", unit) or not isinstance(letter, str) or len(letter) != 1 or not "a" <= letter <= "z" for unit, letter in key.items()):
        return False
    if any(sum(letter == candidate for candidate in key.values()) > 2 for letter in set(key.values())):
        return False
    fit_input, gates = report.get("fit_input"), report.get("gates")
    oracle = report.get("oracle")
    oracle_objective = oracle.get("objective") if isinstance(oracle, Mapping) else None
    oracle_score = oracle_objective.get("score_from_key") if isinstance(oracle_objective, Mapping) else None
    if not _nonnegative_int(oracle_score) or upper < oracle_score or (certified and score < oracle_score):
        return False
    return isinstance(fit_input, Mapping) and _nonnegative_int(fit_input.get("unit_count")) and len(key) == fit_input.get("unit_count") and isinstance(gates, Mapping) and set(gates) == {"validation", "test"} and all(_gate(gates[name]) for name in gates) and isinstance(report.get("test_fully_observed"), bool)


def validate_child_outputs(project_root: Path, freeze: Mapping[str, Any]) -> dict[str, Any]:
    """Check the two child records and return aggregate fields only."""

    root = Path(project_root)
    cold_path, key_path = root / COLD_PATH, root / KEY_PATH
    cold, key_record = _read_json(cold_path), _read_json(key_path)
    outputs = [{"path": path.as_posix(), "present": value is not None, **({"sha256": sha256_path(root / path)} if value is not None else {})} for path, value in ((COLD_PATH, cold), (KEY_PATH, key_record))]
    base = {"complete": cold is not None and key_record is not None, "outputs": outputs}
    if cold is None or key_record is None:
        return {**base, "numeric_valid": False, "reason": "outputs_missing"}
    actual_key_hash = sha256_path(key_path)
    if cold.get("key_record_sha256") != actual_key_hash:
        return {**base, "numeric_valid": False, "reason": "key_hash_mismatch"}
    pins, metadata = _partition_pins(root, freeze), cold.get("metadata")
    if pins is None or not isinstance(metadata, Mapping):
        return {**base, "numeric_valid": False, "reason": "partition_metadata_invalid"}
    expected = {"language": "celsus", "reference": "Celsus projected paragraphs", "partition_manifest_path": PARTITION_MANIFEST_PATH.as_posix(), "partition_manifest_sha256": pins["manifest"], "partitions_private_path": PARTITIONS_PATH.as_posix(), "partitions_private_sha256": pins["partitions.private.json"], "partition_protocol": PROTOCOL}
    metadata_ok = all(metadata.get(name) == value for name, value in expected.items())
    if not metadata_ok or not _valid_child(cold, key_record):
        return {**base, "numeric_valid": False, "reason": "solver_record_invalid" if metadata_ok else "partition_metadata_invalid"}
    hashes, code_hashes = freeze.get("hashes", {}), cold.get("code_sha256")
    if not isinstance(code_hashes, Mapping) or set(code_hashes) != EXPECTED_CODE_PATHS or any(not isinstance(name, str) or hashes.get(name) != digest or not _digest(digest) for name, digest in code_hashes.items()):
        return {**base, "numeric_valid": False, "reason": "code_hashes_invalid"}
    if cold.get("protocol_sha256") != hashes.get("docs/plans/visual-homophonic-pilot.md"):
        return {**base, "numeric_valid": False, "reason": "protocol_hash_invalid"}
    solver, gates = cold["solver"], cold["gates"]
    summary = {name: solver[name] for name in ("score", "lower_bound", "upper_bound", "score_certified", "search_exhausted", "status", "nodes", "pruned_nodes", "frontier_node_count")}
    summary.update({"fit_unit_count": cold["fit_input"]["unit_count"], "test_fully_observed": cold["test_fully_observed"], "gates": {split: dict(gates[split]) for split in ("validation", "test")}, "key_record_sha256": actual_key_hash, "partition_manifest_sha256": pins["manifest"]})
    return {**base, "numeric_valid": True, "score_certified": solver["score_certified"], "summary": summary}


def control_status(run: Mapping[str, Any], validation: Mapping[str, Any]) -> str:
    if run.get("termination_reason") in {"wall_timeout", "rss_limit", "rss_unsupported"}:
        return "resource_abstain"
    if run.get("returncode") == 2:
        return "input_mismatch"
    if run.get("returncode") != 0 or not validation.get("numeric_valid"):
        return "implementation_failure"
    return "completed" if validation.get("score_certified") else "incomplete_search"


def _write_exclusive(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(canonical_json_bytes(value))


def _runtime() -> dict[str, str]:
    return {"python": platform.python_version(), "implementation": platform.python_implementation(), "platform": platform.platform()}


def run_control(project_root: Path = REPOSITORY_ROOT, *, child_runner: Any | None = None) -> dict[str, Any]:
    """Verify, supervise, validate, and receipt one fixed child."""

    root, freeze = Path(project_root), verify_control_freeze(project_root)
    ensure_linux_rss_support()
    preflight_outputs(root)
    try:
        run = (child_runner or launch_child)(root, resources=freeze["resources"])
    except Exception as error:
        run = {"returncode": None, "termination_reason": "launch_failure", "exception_type": type(error).__name__, "elapsed_seconds": 0.0, "max_rss_bytes": 0, "rss_sample_count": 0}
    validation = validate_child_outputs(root, freeze)
    status = control_status(run, validation)
    summary = validation.get("summary", {}) if validation.get("numeric_valid") else {}
    public = {"schema_version": 1, "protocol": PROTOCOL, "command": list(EXPECTED_COMMAND), "child_command": list(EXPECTED_CHILD_COMMAND), "status": status, "numeric_outputs_valid": bool(validation.get("numeric_valid") and run.get("returncode") == 0), "freeze": {"manifest_path": freeze["manifest_path"], "manifest_sha256": freeze["manifest_sha256"], "file_count": freeze["file_count"]}, "parameters": dict(EXPECTED_PARAMETERS), "resources": dict(EXPECTED_RESOURCES), "runtime": _runtime(), "outputs": validation["outputs"], "solver": summary, "scope": "Known-cipher control only. It contains no manuscript measurement."}
    private = {"schema_version": 1, "protocol": PROTOCOL, "command": list(EXPECTED_COMMAND), "child_command": list(EXPECTED_CHILD_COMMAND), "status": status, "numeric_outputs_valid": public["numeric_outputs_valid"], "runtime": _runtime(), "freeze": freeze, "run": dict(run), "validation": {"complete": validation.get("complete"), "numeric_valid": validation.get("numeric_valid"), "reason": validation.get("reason"), "outputs": validation.get("outputs"), "summary": summary}}
    _write_exclusive(root / PUBLIC_RECEIPT_PATH, public)
    _write_exclusive(root / PRIVATE_RECEIPT_PATH, private)
    return public


def main(argv: Sequence[str] | None = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    if args:
        result = {"schema_version": 1, "protocol": PROTOCOL, "status": "implementation_failure", "numeric_outputs_valid": False, "reason": "fixed_command_takes_no_options"}
        print(canonical_json_bytes(result).decode(), end="")
        return 1
    try:
        result = run_control(REPOSITORY_ROOT)
    except FreezeFailure:
        result = {"schema_version": 1, "protocol": PROTOCOL, "status": "input_mismatch", "numeric_outputs_valid": False, "reason": "freeze_or_pinned_input_mismatch"}
    except ResourceFailure:
        result = {"schema_version": 1, "protocol": PROTOCOL, "status": "resource_abstain", "numeric_outputs_valid": False, "reason": "linux_rss_sampling_unavailable"}
    except FileExistsError:
        result = {"schema_version": 1, "protocol": PROTOCOL, "status": "implementation_failure", "numeric_outputs_valid": False, "reason": "fixed_output_exists"}
    except (FileNotFoundError, OSError):
        result = {"schema_version": 1, "protocol": PROTOCOL, "status": "implementation_failure", "numeric_outputs_valid": False, "reason": "output_preflight_failed"}
    except Exception:
        result = {"schema_version": 1, "protocol": PROTOCOL, "status": "implementation_failure", "numeric_outputs_valid": False, "reason": "wrapper_failure"}
    print(canonical_json_bytes(result).decode(), end="")
    return 0 if result.get("numeric_outputs_valid") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())


verify_freeze_manifest = verify_control_freeze
validate_model_outputs = validate_child_outputs
__all__ = ["ALL_OUTPUT_PATHS", "COLD_PATH", "EXPECTED_CHILD_COMMAND", "EXPECTED_CODE_PATHS", "EXPECTED_COMMAND", "EXPECTED_PARAMETERS", "EXPECTED_RESOURCES", "FREEZE_FILES", "FREEZE_MANIFEST_PATH", "FreezeFailure", "KEY_PATH", "MODEL_ROOT", "OUTPUT_PATHS", "PARTITION_MANIFEST_PATH", "PARTITIONS_PATH", "PARAGRAPHS_PATH", "PRIVATE_RECEIPT_PATH", "PROTOCOL", "PUBLIC_RECEIPT_PATH", "ResourceFailure", "RESULTS_ROOT", "canonical_json_bytes", "control_status", "ensure_linux_rss_support", "launch_child", "main", "monitor_process", "preflight_outputs", "run_control", "sample_rss_bytes", "sha256_bytes", "sha256_path", "validate_child_outputs", "validate_model_outputs", "verify_control_freeze", "verify_freeze_manifest"]
