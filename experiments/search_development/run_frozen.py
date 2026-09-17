"""Run the reviewed homophonic development study through its supervisor.

The entry point verifies the external freeze manifest before it starts a child.
It writes one safe supervisor receipt and one private resource receipt.
It does not import the study runner before source verification.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
from collections.abc import Callable, Mapping, Sequence
from typing import Any


PROTOCOL = "homophonic-search-development-v1"
FREEZE_MANIFEST_PATH = Path("experiments/search_development/freeze-v1.json")
REPOSITORY_ROOT = Path(__file__).resolve().parents[2]

# Keep this list explicit. The freeze manifest must not add or remove a
# reviewed file without a new entry-point review.
FREEZE_FILES = (
    Path("docs/plans/homophonic-search-development-v1.md"),
    Path("experiments/search_development/run_study.py"),
    Path("experiments/search_development/test_run_study.py"),
    Path("experiments/search_development/supervise.py"),
    Path("experiments/search_development/test_supervise.py"),
    Path("experiments/search_development/run_frozen.py"),
    Path("experiments/search_development/test_run_frozen.py"),
    Path("experiments/group_bound/pivot.py"),
    Path("experiments/group_bound/test_pivot.py"),
    Path("experiments/group_bound/bitset.py"),
    Path("experiments/group_bound/test_bitset.py"),
    Path("experiments/lexical_warmstart/warmstart.py"),
    Path("experiments/lexical_warmstart/test_warmstart.py"),
    Path("experiments/homophonic/solver.py"),
    Path("experiments/homophonic/bitset_bound.py"),
    Path("experiments/homophonic/controls.py"),
    Path("experiments/homophonic/run_controls.py"),
    Path("experiments/lexicon/run_pilot.py"),
    Path("src/voynich/__init__.py"),
    Path("src/voynich/corpus.py"),
    Path("src/voynich/groups.py"),
    Path("src/voynich/reference.py"),
    Path("src/voynich/substitution.py"),
    Path("data/reference_manifest.json"),
    Path("docs/plans/visual-homophonic-pilot.md"),
    Path("reports/homophonic-feasibility-v1/italian-cold.json"),
    Path("reports/homophonic-feasibility-v1/italian-cold.keys.json"),
    Path("reports/homophonic-feasibility-v1/italian-assisted.json"),
    Path("reports/homophonic-feasibility-v1/italian-assisted.keys.json"),
)

CHILD_OUTPUT_PATHS = (
    Path("reports/homophonic-search-development-v1/manifest.json"),
    Path("reports/homophonic-search-development-v1/cold_selected.key.json"),
    Path("reports/homophonic-search-development-v1/assisted_selected.key.json"),
    Path("reports/homophonic-search-development-v1/aggregate.json"),
)
PUBLIC_RECEIPT_PATH = Path(
    "reports/homophonic-search-development-v1/supervision.json"
)
PRIVATE_RECEIPT_PATH = Path(
    "results/search-development-v1/resources.json"
)
PUBLIC_SUPERVISOR_RECEIPT_PATH = PUBLIC_RECEIPT_PATH
PRIVATE_SUPERVISOR_RECEIPT_PATH = PRIVATE_RECEIPT_PATH
FIXED_CHILD_OUTPUT_PATHS = CHILD_OUTPUT_PATHS
ALL_OUTPUT_PATHS = CHILD_OUTPUT_PATHS + (
    PUBLIC_RECEIPT_PATH,
    PRIVATE_RECEIPT_PATH,
)
EXPECTED_COMMAND = (
    "python",
    "-m",
    "experiments.search_development.run_frozen",
)
EXPECTED_PARAMETERS = {
    "control": "italian_old_cap2",
    "seed": 7000,
    "alphabet": "abcdefghijklmnopqrstuvwxyz",
    "capacity": 2,
    "grouping": "static_min_symbol",
    "move_budget": 8,
    "trace_mode": "summary",
    "test_scored": False,
}
EXPECTED_RESOURCES = {
    "root_timeout_seconds": 1200.0,
    "total_timeout_seconds": 1500.0,
    "rss_limit_bytes": 7 * 1024**3,
    "poll_interval_seconds": 0.25,
    "terminate_grace_seconds": 5.0,
    "as_limit_bytes": None,
    "child_cpu_workers": 1,
    "max_candidate_rows": 12_600_000,
    "max_estimated_storage_bytes": 2_000_000_000,
    "per_start_evaluation_limit": 11_000,
    "total_evaluation_limit": 22_000,
}
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}\Z")


class FreezeFailure(RuntimeError):
    """The reviewed source freeze is unavailable or does not match."""


def canonical_json_bytes(value: Any) -> bytes:
    """Return stable UTF-8 JSON bytes with one final newline."""

    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    """Return the SHA-256 digest of bytes."""

    return hashlib.sha256(value).hexdigest()


def sha256_path(path: Path) -> str:
    """Return the SHA-256 digest of one file."""

    return sha256_bytes(path.read_bytes())


def _safe_relative_path(value: Any) -> str:
    if not isinstance(value, str) or not value:
        raise FreezeFailure("freeze file path is invalid")
    path = Path(value)
    if path.is_absolute() or ".." in path.parts or path.as_posix() != value:
        raise FreezeFailure("freeze file path is not repository relative")
    return value


def _require_mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise FreezeFailure(f"freeze field is not an object: {name}")
    return value


def _same_fixed_value(actual: Any, expected: Any) -> bool:
    if isinstance(expected, (int, float)) and not isinstance(expected, bool):
        return (
            isinstance(actual, (int, float))
            and not isinstance(actual, bool)
            and actual == expected
        )
    return type(actual) is type(expected) and actual == expected


def _output_value(outputs: Mapping[str, Any], names: Sequence[str]) -> Any:
    for name in names:
        if name in outputs:
            return outputs[name]
    raise FreezeFailure("freeze output declaration is incomplete")


def _validate_output_declaration(outputs: Mapping[str, Any]) -> None:
    declared_child = _output_value(
        outputs,
        ("child", "child_outputs", "child_output_paths"),
    )
    if not isinstance(declared_child, list):
        raise FreezeFailure("freeze child output declaration is not a list")
    child_paths = tuple(_safe_relative_path(value) for value in declared_child)
    expected_child = tuple(path.as_posix() for path in CHILD_OUTPUT_PATHS)
    if child_paths != expected_child:
        raise FreezeFailure("freeze child output paths do not match the fixed set")
    declared_public = _safe_relative_path(
        _output_value(
            outputs,
            ("public", "public_receipt", "public_supervisor_receipt"),
        )
    )
    declared_private = _safe_relative_path(
        _output_value(
            outputs,
            ("private", "private_receipt", "private_supervisor_receipt"),
        )
    )
    if declared_public != PUBLIC_RECEIPT_PATH.as_posix():
        raise FreezeFailure("freeze public receipt path does not match")
    if declared_private != PRIVATE_RECEIPT_PATH.as_posix():
        raise FreezeFailure("freeze private receipt path does not match")


def _validate_manifest_shape(manifest: Mapping[str, Any]) -> None:
    version = manifest.get("schema_version")
    if isinstance(version, bool) or version != 1:
        raise FreezeFailure("freeze schema version is not 1")
    if manifest.get("protocol") != PROTOCOL:
        raise FreezeFailure("freeze protocol does not match")
    command = manifest.get("command")
    if command != list(EXPECTED_COMMAND):
        raise FreezeFailure("freeze command does not match the fixed entrypoint")
    parameters = _require_mapping(manifest.get("parameters"), "parameters")
    resources = _require_mapping(manifest.get("resources"), "resources")
    _require_mapping(manifest.get("runtime"), "runtime")
    for name, expected, actual in (
        ("parameters", EXPECTED_PARAMETERS, parameters),
        ("resources", EXPECTED_RESOURCES, resources),
    ):
        for key, expected_value in expected.items():
            actual_value = actual.get(key)
            if not _same_fixed_value(actual_value, expected_value):
                raise FreezeFailure(f"freeze {name} value does not match: {key}")
    outputs = _require_mapping(manifest.get("outputs"), "outputs")
    _validate_output_declaration(outputs)


def verify_freeze_manifest(project_root: Path = REPOSITORY_ROOT) -> dict[str, Any]:
    """Verify the exact reviewed file set and return safe hash metadata.

    The freeze manifest is intentionally excluded from ``FREEZE_FILES``. This
    prevents a manifest self-hash cycle while keeping all source hashes fixed.
    """

    root = Path(project_root)
    manifest_path = root / FREEZE_MANIFEST_PATH
    if manifest_path.is_symlink():
        raise FreezeFailure("freeze manifest is a symlink")
    try:
        manifest_bytes = manifest_path.read_bytes()
    except (FileNotFoundError, OSError) as exc:
        raise FreezeFailure("freeze manifest is unavailable") from exc
    try:
        manifest_value = json.loads(manifest_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise FreezeFailure("freeze manifest is not valid JSON") from exc
    if not isinstance(manifest_value, Mapping):
        raise FreezeFailure("freeze manifest is not an object")
    _validate_manifest_shape(manifest_value)

    entries = manifest_value.get("files")
    if not isinstance(entries, list):
        raise FreezeFailure("freeze files field is not a list")
    paths: list[str] = []
    hashes: dict[str, str] = {}
    for entry in entries:
        if not isinstance(entry, Mapping):
            raise FreezeFailure("freeze file entry is not an object")
        relative = _safe_relative_path(entry.get("path"))
        digest = entry.get("sha256")
        if not isinstance(digest, str) or SHA256_PATTERN.fullmatch(digest) is None:
            raise FreezeFailure("freeze file hash is invalid")
        if relative in hashes:
            raise FreezeFailure("freeze files contain a duplicate path")
        paths.append(relative)
        hashes[relative] = digest

    manifest_name = FREEZE_MANIFEST_PATH.as_posix()
    if manifest_name in hashes:
        raise FreezeFailure("freeze manifest cannot hash itself")
    expected_paths = {path.as_posix() for path in FREEZE_FILES}
    if set(paths) != expected_paths or len(paths) != len(expected_paths):
        raise FreezeFailure("freeze file paths do not match the reviewed set")

    verified_files: list[dict[str, str]] = []
    for relative in paths:
        path = root / relative
        if path.is_symlink() or not path.is_file():
            raise FreezeFailure("a frozen file is missing")
        actual = sha256_path(path)
        if actual != hashes[relative]:
            raise FreezeFailure("a frozen file hash does not match")
        verified_files.append({"path": relative, "sha256": actual})
    return {
        "manifest_path": manifest_name,
        "manifest_sha256": sha256_bytes(manifest_bytes),
        "protocol": PROTOCOL,
        "files": verified_files,
        "command": list(EXPECTED_COMMAND),
    }


_verify_freeze_manifest = verify_freeze_manifest


def _existing_output_path(root: Path, relative: Path) -> Path | None:
    current = root
    if current.is_symlink():
        return current
    parts = relative.parts
    for part in parts[:-1]:
        current = current / part
        if current.is_symlink():
            return current
    target = root / relative
    if os.path.lexists(target):
        return target
    return None


def _preflight_outputs(project_root: Path) -> tuple[Path, ...]:
    """Reject every existing output, including a symlink at any component."""

    root = Path(project_root)
    if not root.is_dir():
        raise FileNotFoundError("project root is unavailable")
    paths = tuple(root / relative for relative in ALL_OUTPUT_PATHS)
    seen: set[Path] = set()
    for relative, path in zip(ALL_OUTPUT_PATHS, paths):
        if relative in seen:
            raise RuntimeError("fixed output paths are not unique")
        seen.add(relative)
        existing = _existing_output_path(root, relative)
        if existing is not None:
            raise FileExistsError("a fixed output already exists")
        if path.is_symlink():
            raise FileExistsError("a fixed output is a symlink")
    return paths


def _default_supervise_development(
    project_root: Path,
    *,
    output_paths: Sequence[Path],
    limits: Any,
) -> Mapping[str, Any]:
    """Import the supervisor only after the freeze and output preflight."""

    from experiments.search_development.supervise import supervise_development

    return supervise_development(
        project_root,
        output_paths=output_paths,
        limits=limits,
    )


# This name is injectable in tests and keeps the production import boundary
# explicit. It does not import ``run_study``.
supervise_development = _default_supervise_development


def _default_limits() -> Any:
    from experiments.search_development.supervise import ResourceLimits

    return ResourceLimits()


def _safe_public_supervisor(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {
            "status": "implementation_failure",
            "reason": "malformed_supervisor_result",
        }
    allowed = (
        "status",
        "reason",
        "progress_event_count",
        "last_phase",
        "last_state",
        "terminal_event_seen",
        "stderr_line_count",
        "child_error_event_count",
        "malformed_output_count",
        "rss_guard",
    )
    result: dict[str, Any] = {}
    for key in allowed:
        item = value.get(key)
        if isinstance(item, (str, int, bool)) or item is None:
            result[key] = item
    if result.get("status") not in {
        "development_only",
        "resource_abstain",
        "implementation_failure",
        "input_mismatch",
        "output_exists",
    }:
        result["status"] = "implementation_failure"
        result["reason"] = "invalid_supervisor_status"
    return result


def _child_output_metadata(root: Path) -> tuple[list[dict[str, Any]], bool]:
    metadata: list[dict[str, Any]] = []
    complete = True
    for relative in CHILD_OUTPUT_PATHS:
        path = root / relative
        present = path.is_file() and not path.is_symlink()
        entry: dict[str, Any] = {
            "path": relative.as_posix(),
            "present": present,
        }
        if present:
            entry["sha256"] = sha256_path(path)
        else:
            complete = False
        metadata.append(entry)
    return metadata, complete


def _write_exclusive(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(canonical_json_bytes(value))


def _safe_limits(manifest: Mapping[str, Any]) -> Mapping[str, Any]:
    resources = manifest.get("resources")
    if not isinstance(resources, Mapping):
        return {}
    safe: dict[str, Any] = {}
    for key, value in resources.items():
        if isinstance(key, str) and isinstance(value, (str, int, float, bool)):
            safe[key] = value
        elif isinstance(key, str) and value is None:
            safe[key] = None
    return dict(sorted(safe.items()))


def _validate_effective_limits(limits: Any) -> None:
    """Reject a production limit override that differs from the freeze."""

    for key, expected in EXPECTED_RESOURCES.items():
        if key not in {
            "root_timeout_seconds",
            "total_timeout_seconds",
            "rss_limit_bytes",
            "poll_interval_seconds",
            "terminate_grace_seconds",
            "as_limit_bytes",
            "child_cpu_workers",
        }:
            continue
        attribute = {
            "root_timeout_seconds": "stage_wall_seconds",
            "total_timeout_seconds": "total_wall_seconds",
            "rss_limit_bytes": "rss_limit_bytes",
            "poll_interval_seconds": "poll_interval_seconds",
            "terminate_grace_seconds": "terminate_grace_seconds",
            "as_limit_bytes": "as_limit_bytes",
            "child_cpu_workers": "child_cpu_workers",
        }[key]
        actual = getattr(limits, attribute, object())
        if not _same_fixed_value(actual, expected):
            raise FreezeFailure("effective resource limits do not match the freeze")


def run_frozen(
    project_root: Path = REPOSITORY_ROOT,
    *,
    supervisor_fn: Callable[..., Mapping[str, Any]] | None = None,
    limits: Any | None = None,
) -> dict[str, Any]:
    """Verify the freeze, run the fixed child, and write safe receipts."""

    root = Path(project_root)
    freeze = verify_freeze_manifest(root)
    _preflight_outputs(root)
    manifest_value = json.loads(
        (root / FREEZE_MANIFEST_PATH).read_text(encoding="utf-8")
    )
    child_paths = tuple(root / relative for relative in CHILD_OUTPUT_PATHS)
    effective_limits = _default_limits() if limits is None else limits
    _validate_effective_limits(effective_limits)
    if supervisor_fn is None:
        supervisor_fn = supervise_development
    try:
        supervisor_result = supervisor_fn(
            root,
            output_paths=child_paths,
            limits=effective_limits,
        )
    except Exception as exc:
        supervisor_result = {
            "public": {
                "status": "implementation_failure",
                "reason": "supervisor_exception",
            },
            "private": {
                "exception_type": type(exc).__name__,
            },
        }

    supervisor_public = _safe_public_supervisor(
        supervisor_result.get("public")
        if isinstance(supervisor_result, Mapping)
        else None
    )
    supervisor_private = (
        supervisor_result.get("private", {})
        if isinstance(supervisor_result, Mapping)
        else {}
    )
    if not isinstance(supervisor_private, Mapping):
        supervisor_private = {"malformed_private_result": True}
    child_metadata, child_complete = _child_output_metadata(root)
    status = supervisor_public.get("status", "implementation_failure")
    numeric_outputs_valid = status == "development_only" and child_complete
    if status == "development_only" and not child_complete:
        status = "implementation_failure"
        supervisor_public = {
            **supervisor_public,
            "status": status,
            "reason": "child_outputs_incomplete",
        }
    if status not in {
        "development_only",
        "resource_abstain",
        "implementation_failure",
        "input_mismatch",
        "output_exists",
    }:
        status = "implementation_failure"
        supervisor_public = {
            **supervisor_public,
            "status": status,
            "reason": "invalid_supervisor_status",
        }
        numeric_outputs_valid = False

    public = {
        "schema_version": 1,
        "protocol": PROTOCOL,
        "command": list(EXPECTED_COMMAND),
        "runtime": {
            "python": platform.python_version(),
            "implementation": platform.python_implementation(),
            "platform": platform.platform(),
        },
        "status": status,
        "numeric_outputs_valid": numeric_outputs_valid,
        "freeze": {
            "manifest_path": freeze["manifest_path"],
            "manifest_sha256": freeze["manifest_sha256"],
            "file_count": len(freeze["files"]),
            "files": freeze["files"],
        },
        "supervisor": supervisor_public,
        "resources": _safe_limits(manifest_value),
        "child_outputs": child_metadata,
        "scope": [
            "Numeric child reports are valid only when status is development_only.",
            "A resource or implementation failure does not publish a partial bound.",
            "The child study is a finite Italian control and does not test the manuscript.",
        ],
    }
    private = {
        "schema_version": 1,
        "protocol": PROTOCOL,
        "command": list(EXPECTED_COMMAND),
        "runtime": {
            "python": platform.python_version(),
            "implementation": platform.python_implementation(),
            "platform": platform.platform(),
        },
        "status": status,
        "numeric_outputs_valid": numeric_outputs_valid,
        "freeze": freeze,
        "supervisor": {
            "public": supervisor_public,
            "private": dict(supervisor_private),
        },
        "resources": _safe_limits(manifest_value),
        "child_outputs": child_metadata,
    }
    private_path = root / PRIVATE_RECEIPT_PATH
    public_path = root / PUBLIC_RECEIPT_PATH
    _write_exclusive(private_path, private)
    _write_exclusive(public_path, public)
    return json.loads(canonical_json_bytes(public))


def _argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=REPOSITORY_ROOT)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the fixed supervised development entrypoint."""

    args = _argument_parser().parse_args(argv)
    try:
        public = run_frozen(args.project_root)
    except FreezeFailure:
        public = {
            "schema_version": 1,
            "protocol": PROTOCOL,
            "status": "input_mismatch",
            "reason": "freeze_verification_failed",
        }
    except (FileExistsError, FileNotFoundError, OSError):
        public = {
            "schema_version": 1,
            "protocol": PROTOCOL,
            "status": "implementation_failure",
            "reason": "output_preflight_failed",
        }
    print(canonical_json_bytes(public).decode("utf-8"), end="")
    return 0 if public.get("status") == "development_only" else 1


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "ALL_OUTPUT_PATHS",
    "CHILD_OUTPUT_PATHS",
    "EXPECTED_COMMAND",
    "EXPECTED_PARAMETERS",
    "EXPECTED_RESOURCES",
    "FIXED_CHILD_OUTPUT_PATHS",
    "FREEZE_FILES",
    "FREEZE_MANIFEST_PATH",
    "FreezeFailure",
    "PRIVATE_RECEIPT_PATH",
    "PRIVATE_SUPERVISOR_RECEIPT_PATH",
    "PROTOCOL",
    "PUBLIC_RECEIPT_PATH",
    "PUBLIC_SUPERVISOR_RECEIPT_PATH",
    "canonical_json_bytes",
    "main",
    "run_frozen",
    "sha256_bytes",
    "sha256_path",
    "supervise_development",
    "verify_freeze_manifest",
    "_verify_freeze_manifest",
]
