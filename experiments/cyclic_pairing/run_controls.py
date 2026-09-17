"""Run the frozen ciphertext-only cyclic pairing controls.

The entry point verifies the external freeze before it imports or starts the
study. It runs one fixed child for each reference corpus and writes safe
supervision metadata after both children stop.
"""

from __future__ import annotations

import argparse
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
PROTOCOL = "cyclic-pairing-control-v1"
FREEZE_MANIFEST_PATH = Path("experiments/cyclic_pairing/freeze-v1.json")
RESULTS_ROOT = Path("results/cyclic-pairing-control-v1")
PUBLIC_RECEIPT_PATH = Path("reports/cyclic-pairing-control-v1/supervision.json")
PRIVATE_RECEIPT_PATH = Path("results/cyclic-pairing-control-v1/resources.json")
CORPORA = ("latin_llct", "italian_old")
CORPUS_OUTPUT_NAMES = ("input.json", "pairing.json", "diagnostics.json")
CORPUS_OUTPUT_PATHS = tuple(
    RESULTS_ROOT / corpus / name
    for corpus in CORPORA
    for name in CORPUS_OUTPUT_NAMES
)
ALL_OUTPUT_PATHS = CORPUS_OUTPUT_PATHS + (PUBLIC_RECEIPT_PATH, PRIVATE_RECEIPT_PATH)

EXPECTED_COMMAND = ("python", "-m", "experiments.cyclic_pairing.run_controls")
EXPECTED_CHILD_COMMAND = (
    "python",
    "-m",
    "experiments.cyclic_pairing.study",
    "--corpus",
)
EXPECTED_PARAMETERS = {
    "corpora": list(CORPORA),
    "family": "cap2",
    "seed": 7000,
    "capacity": 2,
    "declared_unit_count": 52,
    "node_budget": 100_000,
    "max_edge_queries": 26,
    "input_scope": "ciphertext_validation_only",
    "synthetic_test_count": 20,
}
EXPECTED_RESOURCES = {
    "corpus_wall_seconds": 300.0,
    "poll_interval_seconds": 0.25,
    "rss_limit_bytes": 7 * 1024**3,
    "terminate_grace_seconds": 5.0,
    "as_limit_bytes": None,
    "child_cpu_workers": 1,
}
EXPECTED_DECLARED_UNITS_SHA256 = "16018ee0527c55f40d0d3707a0b162570b3bdd5c64c52aa1617e04baf6349619"
EXPECTED_VALIDATION_STREAM_HASHES = {
    "latin_llct": "eb03e98b086b9f8bc883f349afaee968bfeaeee8c95be5f66bec320e54b419b2",
    "italian_old": "d7e9c6e0b716cf7ea1c7deb4f135ca2692ea70b4f927548e99668ab0c1428492",
}
# SHA-256 of the sorted 26 unit pairs produced by the fixed cap2 seed 7000.
# The wrapper checks this diagnostic receipt without passing the planted key to
# the ciphertext-only pairing functions.
EXPECTED_CONTROL_PAIR_SET_SHA256 = "e25c3707102e82a0be3eef8588d8bf4362dc54c223b822b3697528f39c36206f"
EXPECTED_CONTROL_PAIRS = (
    ("c00", "c33"),
    ("c01", "c18"),
    ("c02", "c45"),
    ("c03", "c09"),
    ("c04", "c50"),
    ("c05", "c51"),
    ("c06", "c46"),
    ("c07", "c49"),
    ("c08", "c22"),
    ("c10", "c31"),
    ("c11", "c47"),
    ("c12", "c16"),
    ("c13", "c19"),
    ("c14", "c30"),
    ("c15", "c23"),
    ("c17", "c39"),
    ("c20", "c25"),
    ("c21", "c26"),
    ("c24", "c40"),
    ("c27", "c43"),
    ("c28", "c35"),
    ("c29", "c32"),
    ("c34", "c38"),
    ("c36", "c44"),
    ("c37", "c41"),
    ("c42", "c48"),
)

# The freeze manifest is external and excludes itself. Keep this tuple fixed
# so a changed manifest cannot add an unreviewed input or implementation file.
FREEZE_FILES = (
    Path("docs/plans/cyclic-pairing-control-v1.md"),
    Path("docs/research/cyclic-emitter-pairing.md"),
    Path("experiments/cyclic_pairing/study.py"),
    Path("experiments/cyclic_pairing/test_study.py"),
    Path("experiments/cyclic_pairing/run_controls.py"),
    Path("experiments/cyclic_pairing/test_run_controls.py"),
    Path("experiments/cyclic_pairing/pairing.py"),
    Path("experiments/cyclic_pairing/forced.py"),
    Path("experiments/cyclic_pairing/test_pairing.py"),
    Path("experiments/cyclic_pairing/test_forced.py"),
    Path("experiments/cyclic_pairing/__init__.py"),
    Path("experiments/homophonic/controls.py"),
    Path("src/voynich/__init__.py"),
    Path("src/voynich/reference.py"),
    Path("data/reference_manifest.json"),
    Path("docs/plans/visual-homophonic-pilot.md"),
    Path("reports/homophonic-feasibility-v1/latin-cold.json"),
    Path("reports/homophonic-feasibility-v1/italian-cold.json"),
    Path("data/raw/reference/latin_llct/la_llct-ud-train.conllu"),
    Path("data/raw/reference/latin_llct/la_llct-ud-dev.conllu"),
    Path("data/raw/reference/latin_llct/la_llct-ud-test.conllu"),
    Path("data/raw/reference/latin_llct/README.md"),
    Path("data/raw/reference/latin_llct/LICENSE.txt"),
    Path("data/raw/reference/italian_old/it_old-ud-train.conllu"),
    Path("data/raw/reference/italian_old/it_old-ud-dev.conllu"),
    Path("data/raw/reference/italian_old/it_old-ud-test.conllu"),
    Path("data/raw/reference/italian_old/README.md"),
    Path("data/raw/reference/italian_old/LICENSE.txt"),
)

SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
PRIVATE_PATH_PATTERN = re.compile(r"(?:^|\s)/(?:home|tmp|Users|root|private)(?:/|$)")
FORBIDDEN_KEYS = frozenset(
    {
        "words",
        "plaintext",
        "plaintext_words",
        "ciphertext",
        "ciphertext_words",
        "partitions",
        "partition",
        "key",
        "cipher_to_plain",
        "emission_order",
        "lexicon",
        "model",
        "source_path",
    }
)
MATCHING_STATUSES = frozenset(
    {"unique", "multiple", "none", "unknown_budget", "not_closed", "empty_scope"}
)


class FreezeFailure(RuntimeError):
    """The reviewed source freeze is unavailable or does not match."""


def canonical_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_path(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def _safe_relative_path(value: Any) -> str:
    if not isinstance(value, str) or not value:
        raise FreezeFailure("freeze path is invalid")
    path = Path(value)
    if path.is_absolute() or ".." in path.parts or path.as_posix() != value:
        raise FreezeFailure("freeze path is not repository relative")
    return value


def _require_mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise FreezeFailure(f"freeze field is not an object: {name}")
    return value


def _validate_freeze_shape(manifest: Mapping[str, Any]) -> None:
    if manifest.get("schema_version") != 1:
        raise FreezeFailure("freeze schema version is not 1")
    if manifest.get("protocol") != PROTOCOL:
        raise FreezeFailure("freeze protocol does not match")
    if manifest.get("command") != list(EXPECTED_COMMAND):
        raise FreezeFailure("freeze command does not match")
    if manifest.get("child_command") != list(EXPECTED_CHILD_COMMAND):
        raise FreezeFailure("freeze child command does not match")
    parameters = _require_mapping(manifest.get("parameters"), "parameters")
    resources = _require_mapping(manifest.get("resources"), "resources")
    runtime = _require_mapping(manifest.get("runtime"), "runtime")
    for field in ("freeze_python", "implementation", "platform"):
        if not isinstance(runtime.get(field), str) or not runtime[field]:
            raise FreezeFailure(f"freeze runtime field is invalid: {field}")
    if dict(parameters) != EXPECTED_PARAMETERS:
        raise FreezeFailure("freeze parameters do not match")
    if dict(resources) != EXPECTED_RESOURCES:
        raise FreezeFailure("freeze resources do not match")
    outputs = _require_mapping(manifest.get("outputs"), "outputs")
    if outputs.get("corpora") != list(CORPORA):
        raise FreezeFailure("freeze corpus outputs do not match")
    if outputs.get("public") != PUBLIC_RECEIPT_PATH.as_posix():
        raise FreezeFailure("freeze public receipt path does not match")
    if outputs.get("private") != PRIVATE_RECEIPT_PATH.as_posix():
        raise FreezeFailure("freeze private receipt path does not match")
    expected_corpus_paths = [path.as_posix() for path in CORPUS_OUTPUT_PATHS]
    if outputs.get("corpus") != expected_corpus_paths:
        raise FreezeFailure("freeze corpus output paths do not match")


def verify_freeze_manifest(project_root: Path = REPOSITORY_ROOT) -> dict[str, Any]:
    """Verify the exact reviewed file set and return safe hash metadata."""

    root = Path(project_root)
    manifest_path = root / FREEZE_MANIFEST_PATH
    if manifest_path.is_symlink():
        raise FreezeFailure("freeze manifest is a symlink")
    try:
        manifest_raw = manifest_path.read_bytes()
        manifest = json.loads(manifest_raw.decode("utf-8"))
    except (FileNotFoundError, OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise FreezeFailure("freeze manifest is unavailable or invalid") from exc
    if not isinstance(manifest, Mapping):
        raise FreezeFailure("freeze manifest is not an object")
    _validate_freeze_shape(manifest)
    entries = manifest.get("files")
    if not isinstance(entries, list):
        raise FreezeFailure("freeze files field is not a list")
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
        hashes[relative] = digest
    expected_paths = {path.as_posix() for path in FREEZE_FILES}
    if set(hashes) != expected_paths or len(hashes) != len(expected_paths):
        raise FreezeFailure("freeze file allowlist does not match")
    if FREEZE_MANIFEST_PATH.as_posix() in hashes:
        raise FreezeFailure("freeze manifest cannot hash itself")
    verified: list[dict[str, str]] = []
    for relative in sorted(hashes):
        path = root / relative
        if path.is_symlink() or not path.is_file():
            raise FreezeFailure("a frozen file is missing or is a symlink")
        if sha256_path(path) != hashes[relative]:
            raise FreezeFailure("a frozen file hash does not match")
        verified.append({"path": relative, "sha256": hashes[relative]})
    return {
        "manifest_path": FREEZE_MANIFEST_PATH.as_posix(),
        "manifest_sha256": sha256_bytes(manifest_raw),
        "protocol": PROTOCOL,
        "file_count": len(verified),
        "files": verified,
        "parameters": dict(EXPECTED_PARAMETERS),
        "resources": dict(EXPECTED_RESOURCES),
    }


def _freeze_file_map(freeze: Mapping[str, Any]) -> dict[str, str]:
    files = freeze.get("files")
    if not isinstance(files, list):
        return {}
    result: dict[str, str] = {}
    for entry in files:
        if not isinstance(entry, Mapping):
            return {}
        path = entry.get("path")
        digest = entry.get("sha256")
        if not isinstance(path, str) or not _valid_digest(digest):
            return {}
        result[path] = digest
    return result


def _expected_provenance(freeze: Mapping[str, Any], corpus: str) -> dict[str, dict[str, str]]:
    file_map = _freeze_file_map(freeze)
    source = {
        path.name: file_map.get(path.as_posix(), "")
        for path in FREEZE_FILES
        if path.parts[:3] == ("data", "raw", "reference")
        and len(path.parts) > 3
        and path.parts[3] == corpus
        and path.suffix == ".conllu"
    }
    code = {
        name: digest
        for name, digest in file_map.items()
        if Path(name).suffix == ".py" and "test" not in Path(name).name
    }
    tests = {
        name: digest
        for name, digest in file_map.items()
        if Path(name).suffix == ".py" and "test" in Path(name).name
    }
    return {
        "source_file_hashes": source,
        "code_hashes": code,
        "test_hashes": tests,
        "frozen_file_hashes": file_map,
    }


def _provenance_matches(
    input_record: Mapping[str, Any], freeze: Mapping[str, Any], corpus: str
) -> bool:
    file_map = _freeze_file_map(freeze)
    expected = _expected_provenance(freeze, corpus)
    return (
        len(expected["source_file_hashes"]) == 3
        and input_record.get("source_manifest_sha256") == file_map.get("data/reference_manifest.json")
        and input_record.get("source_file_hashes") == expected["source_file_hashes"]
        and input_record.get("code_hashes") == expected["code_hashes"]
        and input_record.get("test_hashes") == expected["test_hashes"]
        and input_record.get("frozen_file_hashes") == expected["frozen_file_hashes"]
    )


def _existing_output_path(root: Path, relative: Path) -> Path | None:
    current = root
    if current.is_symlink():
        return current
    for part in relative.parts[:-1]:
        current = current / part
        if current.is_symlink() or (current.exists() and not current.is_dir()):
            return current
    target = root / relative
    if os.path.lexists(target):
        return target
    return None


def preflight_outputs(project_root: Path = REPOSITORY_ROOT) -> tuple[Path, ...]:
    """Reject every fixed output, including symlinked parent components."""

    root = Path(project_root)
    if not root.is_dir():
        raise FileNotFoundError("project root is unavailable")
    for relative in ALL_OUTPUT_PATHS:
        if _existing_output_path(root, relative) is not None:
            raise FileExistsError("a fixed output already exists")
    return tuple(root / relative for relative in ALL_OUTPUT_PATHS)


def run_synthetic_tests(project_root: Path = REPOSITORY_ROOT) -> dict[str, Any]:
    """Run the 20 pairing and forced-edge tests before a control child."""

    command = [
        sys.executable,
        "-m",
        "unittest",
        "experiments.cyclic_pairing.test_pairing",
        "experiments.cyclic_pairing.test_forced",
        "-v",
    ]
    try:
        completed = subprocess.run(
            command,
            cwd=project_root,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=60,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise FreezeFailure("synthetic tests did not complete") from exc
    output = completed.stdout + completed.stderr
    match = re.search(rb"Ran\s+(\d+)\s+tests?", output)
    if completed.returncode != 0 or match is None or int(match.group(1)) != 20:
        raise FreezeFailure("synthetic tests failed or had the wrong count")
    return {"status": "pass", "count": 20, "returncode": 0}


def sample_rss_bytes(pid: int) -> int | None:
    """Read Linux resident-set size for a child process."""

    if os.name != "posix":
        return None
    try:
        status = Path(f"/proc/{pid}/status").read_text(encoding="ascii")
    except (FileNotFoundError, OSError, UnicodeDecodeError):
        return None
    for line in status.splitlines():
        if line.startswith("VmRSS:"):
            fields = line.split()
            if len(fields) >= 2 and fields[1].isdigit():
                return int(fields[1]) * 1024
    return None


def _signal_group(process: subprocess.Popen[Any], signum: int) -> None:
    try:
        if os.name == "posix":
            os.killpg(process.pid, signum)
        else:
            process.send_signal(signum)
    except (ProcessLookupError, OSError):
        pass


def monitor_process(
    process: subprocess.Popen[Any],
    *,
    wall_seconds: float,
    rss_limit_bytes: int,
    poll_interval_seconds: float,
    terminate_grace_seconds: float,
) -> dict[str, Any]:
    """Wait for one child and terminate its process group at a fixed limit."""

    started = time.monotonic()
    next_sample = started
    max_rss = 0
    sample_count = 0
    termination_reason: str | None = None
    while process.poll() is None:
        now = time.monotonic()
        if now >= next_sample:
            rss = sample_rss_bytes(process.pid)
            sample_count += 1
            if rss is not None:
                max_rss = max(max_rss, rss)
                if rss >= rss_limit_bytes:
                    termination_reason = "rss_limit"
                    _signal_group(process, signal.SIGTERM)
                    break
            next_sample = now + poll_interval_seconds
        if now - started >= wall_seconds:
            termination_reason = "wall_timeout"
            _signal_group(process, signal.SIGTERM)
            break
        time.sleep(min(0.05, poll_interval_seconds, max(0.001, next_sample - now)))
    if termination_reason is not None:
        try:
            process.wait(timeout=terminate_grace_seconds)
        except subprocess.TimeoutExpired:
            _signal_group(process, signal.SIGKILL)
            process.wait()
        finally:
            # The group can contain descendants after the leader exits.
            _signal_group(process, signal.SIGKILL)
    else:
        process.wait()
    return {
        "returncode": process.returncode,
        "termination_reason": termination_reason,
        "elapsed_seconds": time.monotonic() - started,
        "max_rss_bytes": max_rss,
        "rss_sample_count": sample_count,
    }


def launch_child(
    project_root: Path,
    corpus: str,
    *,
    resources: Mapping[str, Any] = EXPECTED_RESOURCES,
) -> dict[str, Any]:
    """Launch one fixed study module in a new process group."""

    if sys.platform != "linux":
        raise FreezeFailure("the resource monitor requires Linux")
    if corpus not in CORPORA:
        raise ValueError("unknown corpus")
    command = [
        sys.executable,
        "-m",
        "experiments.cyclic_pairing.study",
        "--corpus",
        corpus,
    ]
    process = subprocess.Popen(
        command,
        cwd=project_root,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
        close_fds=True,
    )
    return monitor_process(
        process,
        wall_seconds=float(resources["corpus_wall_seconds"]),
        rss_limit_bytes=int(resources["rss_limit_bytes"]),
        poll_interval_seconds=float(resources["poll_interval_seconds"]),
        terminate_grace_seconds=float(resources["terminate_grace_seconds"]),
    )


def _safe_public_tree(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if not isinstance(key, str) or key in FORBIDDEN_KEYS:
                return False
            if not _safe_public_tree(child):
                return False
        return True
    if isinstance(value, (list, tuple)):
        return all(_safe_public_tree(child) for child in value)
    if isinstance(value, Path):
        return False
    if isinstance(value, str) and PRIVATE_PATH_PATTERN.search(value):
        return False
    return True


def _read_json_object(path: Path) -> dict[str, Any] | None:
    if path.is_symlink() or not path.is_file():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _record_matches_common(value: Mapping[str, Any], corpus: str, freeze_hash: str) -> bool:
    if value.get("protocol") != PROTOCOL or value.get("corpus") != corpus:
        return False
    if value.get("input_scope") != "ciphertext_validation_only":
        return False
    manifest_hash = value.get("manifest_sha256", value.get("freeze_manifest_sha256"))
    return manifest_hash == freeze_hash


def _nonnegative_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _valid_digest(value: Any) -> bool:
    return isinstance(value, str) and SHA256_PATTERN.fullmatch(value) is not None


def _valid_hash_mapping(value: Any) -> bool:
    if not isinstance(value, Mapping) or not value:
        return False
    for name, digest in value.items():
        if (
            not isinstance(name, str)
            or not name
            or Path(name).is_absolute()
            or ".." in Path(name).parts
            or Path(name).as_posix() != name
            or not _valid_digest(digest)
        ):
            return False
    return True


def _valid_unit_pair(value: Any) -> bool:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or len(value) != 2:
        return False
    return (
        all(
            isinstance(unit, str)
            and re.fullmatch(r"c(?:0[0-9]|[1-4][0-9]|5[01])", unit)
            for unit in value
        )
        and value[0] < value[1]
    )


def _valid_witness(value: Any) -> bool:
    if not isinstance(value, list) or len(value) != 26:
        return False
    pairs: list[tuple[str, str]] = []
    for pair in value:
        if not _valid_unit_pair(pair):
            return False
        pairs.append((pair[0], pair[1]))
    return len(set(pairs)) == 26 and {
        unit for pair in pairs for unit in pair
    } == {f"c{index:02d}" for index in range(52)}


def _pair_set(value: Any) -> set[tuple[str, str]] | None:
    if not isinstance(value, list):
        return None
    pairs: set[tuple[str, str]] = set()
    for pair in value:
        if not _valid_unit_pair(pair):
            return None
        pairs.add((pair[0], pair[1]))
    return pairs


def _validate_pairing_record(
    value: Mapping[str, Any], input_record: Mapping[str, Any]
) -> bool:
    fixed_fields = (
        "family",
        "seed",
        "capacity",
        "declared_unit_count",
        "declared_units_sha256",
        "validation_stream_sha256",
        "word_count",
        "unit_token_count",
    )
    if any(value.get(field) != input_record.get(field) for field in fixed_fields):
        return False
    provenance_fields = (
        "source_manifest_sha256",
        "source_file_hashes",
        "code_hashes",
        "test_hashes",
        "frozen_file_hashes",
    )
    if any(value.get(field) != input_record.get(field) for field in provenance_fields):
        return False
    matching = value.get("matching")
    forced = value.get("forced")
    graph = value.get("graph")
    if (
        not isinstance(matching, Mapping)
        or not isinstance(forced, Mapping)
        or not isinstance(graph, Mapping)
    ):
        return False
    if matching.get("scope") != "full" or matching.get("node_budget") != 100_000:
        return False
    matching_status = matching.get("status")
    witness_count = matching.get("witness_count")
    witnesses = matching.get("witnesses")
    if matching_status not in {"unique", "multiple", "none", "unknown_budget"}:
        return False
    if not _nonnegative_int(witness_count) or witness_count > 2:
        return False
    if not _nonnegative_int(matching.get("nodes_visited")) or matching["nodes_visited"] > 100_000:
        return False
    if matching.get("scope_unit_count") != 52 or not _nonnegative_int(matching.get("unseen_unit_count")):
        return False
    if not isinstance(witnesses, list) or len(witnesses) != witness_count:
        return False
    for witness in witnesses:
        if not _valid_witness(witness):
            return False
    if matching_status == "unique" and witness_count != 1:
        return False
    if matching_status == "multiple" and witness_count < 2:
        return False
    if matching_status == "none" and witness_count != 0:
        return False
    if graph.get("vertex_count") != 52 or not _nonnegative_int(graph.get("edge_count")):
        return False
    if not _nonnegative_int(graph.get("observed_vertex_count")) or not _nonnegative_int(graph.get("unseen_vertex_count")):
        return False
    if graph["observed_vertex_count"] + graph["unseen_vertex_count"] != 52:
        return False
    if matching["unseen_unit_count"] != graph["unseen_vertex_count"]:
        return False
    edge_counts = graph.get("edge_counts_by_category")
    if not isinstance(edge_counts, Mapping) or set(edge_counts) != {
        "observed_observed", "observed_unseen", "unseen_unseen"
    }:
        return False
    if not all(_nonnegative_int(edge_counts.get(category)) for category in edge_counts):
        return False
    if sum(edge_counts.values()) != graph["edge_count"]:
        return False

    if forced.get("protocol_max_edge_queries") != 26:
        return False
    if forced.get("original_status") != matching_status:
        return False
    if forced.get("original_witness_count") != witness_count:
        return False
    if forced.get("original_node_budget") != 100_000:
        return False
    if forced.get("original_nodes_visited") != matching.get("nodes_visited"):
        return False
    forced_status = forced.get("status")
    queries_run = forced.get("queries_run")
    queries_skipped = forced.get("queries_skipped")
    evidence = forced.get("edge_evidence")
    selected = forced.get("selected_witness")
    if not _nonnegative_int(queries_run) or not _nonnegative_int(queries_skipped):
        return False
    if forced_status not in {"analyzed", "infeasible", "unknown_budget"}:
        return False
    if not isinstance(evidence, list) or queries_run != len(evidence) or queries_run > 26:
        return False
    if selected is not None and not _valid_witness(selected):
        return False
    if matching_status == "none":
        if forced_status != "infeasible" or selected is not None or evidence or queries_run or queries_skipped:
            return False
    elif matching_status in {"unique", "multiple"}:
        if selected is None or not witnesses or selected != witnesses[0]:
            return False
    elif forced_status != "unknown_budget":
        return False
    if selected is None:
        if evidence or queries_run or queries_skipped:
            return False
    else:
        if queries_run + queries_skipped != len(selected):
            return False
        selected_pairs = {(pair[0], pair[1]) for pair in selected}
        seen_edges: set[tuple[str, str]] = set()
        if queries_skipped > 0 and forced_status != "unknown_budget":
            return False
        for item in evidence:
            if not isinstance(item, Mapping):
                return False
            edge = item.get("edge")
            if not _valid_unit_pair(edge):
                return False
            edge_tuple = (edge[0], edge[1])
            if edge_tuple not in selected_pairs or edge_tuple in seen_edges:
                return False
            seen_edges.add(edge_tuple)
            item_status = item.get("status")
            query_status = item.get("query_status")
            witness_items = item.get("witness_count")
            if item_status not in {"forced", "not_forced", "unknown"}:
                return False
            if query_status not in MATCHING_STATUSES:
                return False
            if not _nonnegative_int(witness_items) or not _nonnegative_int(item.get("nodes_visited")):
                return False
            if item.get("nodes_visited") > 100_000 or item.get("node_budget") != 100_000:
                return False
            alternative = item.get("alternative_witness")
            if item_status == "forced":
                if query_status != "none" or witness_items != 0 or alternative is not None:
                    return False
            elif item_status == "unknown":
                if query_status != "unknown_budget" or witness_items != 0 or alternative is not None:
                    return False
            else:
                if query_status not in {"unique", "multiple", "unknown_budget"} or witness_items < 1:
                    return False
                if query_status == "unique" and witness_items != 1:
                    return False
                if query_status == "multiple" and witness_items < 2:
                    return False
                if not _valid_witness(alternative) or edge_tuple in {
                    (pair[0], pair[1]) for pair in alternative
                }:
                    return False
        if seen_edges != {tuple(pair) for pair in selected[:queries_run]}:
            return False
    if matching_status == "unknown_budget" and forced_status != "unknown_budget":
        return False
    category_counts = forced.get("category_counts")
    categories = {"observed_observed", "observed_unseen", "unseen_unseen"}
    if not isinstance(category_counts, Mapping) or set(category_counts) != categories:
        return False
    evidence_counts = {category: {status: 0 for status in ("forced", "not_forced", "unknown")} for category in categories}
    for item in evidence:
        category = item.get("category")
        if category not in categories or not _valid_unit_pair(item.get("edge")):
            return False
        evidence_counts[category][item["status"]] += 1
    if dict(category_counts) != evidence_counts:
        return False
    if forced_status == "analyzed" and any(item["status"] == "unknown" for item in evidence):
        return False
    if forced_status == "unknown_budget" and matching_status in {"unique", "multiple"}:
        if queries_skipped == 0 and not any(item["status"] == "unknown" for item in evidence):
            return False
    return True


def _validate_diagnostics_record(
    value: Mapping[str, Any], pairing: Mapping[str, Any]
) -> bool:
    matching = pairing["matching"]
    status = matching["status"]
    if value.get("status") != status or value.get("full_matching_status") != status:
        return False
    if value.get("matching_status") != status or value.get("matching_witness_count") != matching["witness_count"]:
        return False
    if value.get("source_manifest_sha256") != pairing.get("source_manifest_sha256"):
        return False
    if status not in {"unique", "multiple", "unknown_budget"}:
        return False
    if status == "unique":
        matching_witnesses = matching.get("witnesses")
        if (
            not isinstance(matching_witnesses, list)
            or len(matching_witnesses) != 1
            or _pair_set(matching_witnesses[0]) != set(EXPECTED_CONTROL_PAIRS)
        ):
            return False
    if value.get("control_pair_count") != 26:
        return False
    if value.get("control_pair_set_sha256") != EXPECTED_CONTROL_PAIR_SET_SHA256:
        return False
    overlap_count = value.get("graph_control_pair_overlap_count")
    overlap = _pair_set(value.get("graph_control_pair_overlap"))
    missing = value.get("graph_control_pair_missing")
    missing_set = _pair_set(missing)
    if (
        overlap != set(EXPECTED_CONTROL_PAIRS)
        or missing_set != set()
        or overlap_count != 26
    ):
        return False
    categories = {"observed_observed", "observed_unseen", "unseen_unseen"}
    category_counts = value.get("control_pair_counts_by_category")
    if not isinstance(category_counts, Mapping) or set(category_counts) != categories:
        return False
    if not all(_nonnegative_int(category_counts.get(category)) for category in categories):
        return False
    if sum(category_counts.values()) != 26:
        return False
    orientation = value.get("orientation")
    if not isinstance(orientation, Mapping):
        return False
    comparable = orientation.get("comparable_count")
    matches = orientation.get("match_count")
    mismatches = orientation.get("mismatch_count")
    if not all(_nonnegative_int(item) for item in (comparable, matches, mismatches)):
        return False
    if comparable != matches + mismatches or mismatches != 0 or matches != comparable:
        return False
    witnesses = value.get("witnesses")
    if not isinstance(witnesses, list) or len(witnesses) != matching["witness_count"]:
        return False
    for index, witness in enumerate(witnesses):
        if not isinstance(witness, Mapping) or witness.get("witness_index") != index:
            return False
        witness_overlap = _pair_set(witness.get("control_pairs_in_witness"))
        if witness_overlap is None or not witness_overlap.issubset(set(EXPECTED_CONTROL_PAIRS)):
            return False
        if status == "unique" and witness_overlap != set(EXPECTED_CONTROL_PAIRS):
            return False
        if witness.get("control_pair_overlap_count") != len(witness_overlap):
            return False
        if not _valid_digest(witness.get("pair_set_sha256")):
            return False
    return True


def validate_corpus_outputs(
    project_root: Path,
    corpus: str,
    freeze: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate safe child records and return hashes without exposing content."""

    root = Path(project_root)
    freeze_hash = freeze["manifest_sha256"]
    paths = {
        name: root / RESULTS_ROOT / corpus / name for name in CORPUS_OUTPUT_NAMES
    }
    records: dict[str, dict[str, Any] | None] = {}
    output_metadata: list[dict[str, Any]] = []
    complete = True
    for name, path in paths.items():
        value = _read_json_object(path)
        present = value is not None
        if not present:
            complete = False
        entry: dict[str, Any] = {"path": (RESULTS_ROOT / corpus / name).as_posix(), "present": present}
        if present:
            entry["sha256"] = sha256_path(path)
        output_metadata.append(entry)
        records[name] = value
    if not complete:
        return {"complete": False, "numeric_valid": False, "outputs": output_metadata}

    input_record = records["input.json"]
    pairing = records["pairing.json"]
    diagnostics = records["diagnostics.json"]
    if not all(
        isinstance(value, Mapping)
        and _safe_public_tree(value)
        and _record_matches_common(value, corpus, freeze_hash)
        for value in (input_record, pairing, diagnostics)
    ):
        return {"complete": True, "numeric_valid": False, "outputs": output_metadata}
    assert input_record is not None and pairing is not None and diagnostics is not None
    if (
        input_record.get("record_type") != "input"
        or pairing.get("record_type") != "pairing"
        or diagnostics.get("record_type") != "diagnostics"
    ):
        return {"complete": True, "numeric_valid": False, "outputs": output_metadata}
    fixed_input = {
        "family": "cap2",
        "seed": 7000,
        "capacity": 2,
        "declared_unit_count": 52,
        "declared_units_sha256": EXPECTED_DECLARED_UNITS_SHA256,
        "node_budget": 100_000,
        "max_edge_queries": 26,
    }
    input_ok = all(input_record.get(key) == expected for key, expected in fixed_input.items())
    input_ok = input_ok and input_record.get("validation_stream_sha256") == EXPECTED_VALIDATION_STREAM_HASHES[corpus]
    input_ok = input_ok and _nonnegative_int(input_record.get("word_count"))
    input_ok = input_ok and _nonnegative_int(input_record.get("unit_token_count"))
    input_ok = input_ok and _nonnegative_int(input_record.get("unit_type_count"))
    input_ok = input_ok and _valid_hash_mapping(input_record.get("source_file_hashes"))
    input_ok = input_ok and _valid_hash_mapping(input_record.get("code_hashes"))
    input_ok = input_ok and _valid_hash_mapping(input_record.get("test_hashes"))
    input_ok = input_ok and _valid_hash_mapping(input_record.get("frozen_file_hashes"))
    input_ok = input_ok and _provenance_matches(input_record, freeze, corpus)
    pairing_ok = _validate_pairing_record(pairing, input_record)
    diagnostics_ok = _validate_diagnostics_record(diagnostics, pairing) if pairing_ok else False
    numeric_valid = bool(input_ok and pairing_ok and diagnostics_ok)
    return {
        "complete": True,
        "numeric_valid": numeric_valid,
        "outputs": output_metadata,
    }


def _write_exclusive(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(canonical_json_bytes(value))


def _corpus_status(run: Mapping[str, Any], validation: Mapping[str, Any]) -> str:
    if run.get("termination_reason") in {"wall_timeout", "rss_limit"}:
        return "resource_abstain"
    if run.get("returncode") != 0 or not validation.get("numeric_valid"):
        return "implementation_failure"
    return "complete"


def run_controls(
    project_root: Path = REPOSITORY_ROOT,
    *,
    synthetic_runner: Any | None = None,
    child_runner: Any | None = None,
) -> dict[str, Any]:
    """Verify the freeze, run both controls sequentially, and write receipts."""

    if sys.platform != "linux":
        raise FreezeFailure("the resource monitor requires Linux")
    root = Path(project_root)
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
        except Exception as exc:
            run = {
                "returncode": None,
                "termination_reason": "launch_failure",
                "exception_type": type(exc).__name__,
                "elapsed_seconds": 0.0,
                "max_rss_bytes": 0,
            }
        validation = validate_corpus_outputs(root, corpus, freeze)
        status = _corpus_status(run, validation)
        corpus_results.append(
            {
                "corpus": corpus,
                "status": status,
                "numeric_outputs_valid": bool(status == "complete" and validation["numeric_valid"]),
                "outputs": validation["outputs"],
            }
        )
        private_results.append(
            {
                "corpus": corpus,
                "status": status,
                "run": dict(run),
                "validation": dict(validation),
            }
        )
    all_valid = all(item["numeric_outputs_valid"] for item in corpus_results)
    if all_valid:
        status = "complete"
    elif any(item["status"] == "resource_abstain" for item in corpus_results):
        status = "resource_abstain"
    else:
        status = "implementation_failure"
    supervision = {
        "status": status,
        "numeric_outputs_valid": all_valid,
        "limits": dict(EXPECTED_RESOURCES),
        "synthetic_tests": synthetic,
        "corpora": corpus_results,
    }
    public = {
        "schema_version": 1,
        "protocol": PROTOCOL,
        "command": list(EXPECTED_COMMAND),
        "child_command": list(EXPECTED_CHILD_COMMAND),
        "status": status,
        "numeric_outputs_valid": all_valid,
        "freeze": {
            "manifest_path": freeze["manifest_path"],
            "manifest_sha256": freeze["manifest_sha256"],
            "file_count": freeze["file_count"],
        },
        "limits": dict(EXPECTED_RESOURCES),
        "synthetic_tests": synthetic,
        "corpora": corpus_results,
        "supervision": supervision,
        "scope": "Numeric outputs are valid only after exit status 0 and all three safe corpus records pass validation.",
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
        "numeric_outputs_valid": all_valid,
        "freeze": freeze,
        "synthetic_tests": synthetic,
        "corpora": private_results,
    }
    _write_exclusive(root / PUBLIC_RECEIPT_PATH, public)
    _write_exclusive(root / PRIVATE_RECEIPT_PATH, private)
    return public


def _argument_parser() -> argparse.ArgumentParser:
    return argparse.ArgumentParser(description=__doc__)


def main(argv: Sequence[str] | None = None) -> int:
    _argument_parser().parse_args(argv)
    try:
        public = run_controls(REPOSITORY_ROOT)
    except FreezeFailure:
        public = {
            "schema_version": 1,
            "protocol": PROTOCOL,
            "status": "input_mismatch",
            "numeric_outputs_valid": False,
            "reason": "freeze_or_synthetic_verification_failed",
        }
    except FileExistsError:
        public = {
            "schema_version": 1,
            "protocol": PROTOCOL,
            "status": "output_exists",
            "numeric_outputs_valid": False,
            "reason": "fixed_output_exists",
        }
    except (FileNotFoundError, OSError):
        public = {
            "schema_version": 1,
            "protocol": PROTOCOL,
            "status": "implementation_failure",
            "numeric_outputs_valid": False,
            "reason": "output_preflight_failed",
        }
    print(canonical_json_bytes(public).decode("utf-8"), end="")
    return 0 if public.get("numeric_outputs_valid") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "ALL_OUTPUT_PATHS",
    "CORPORA",
    "CORPUS_OUTPUT_NAMES",
    "CORPUS_OUTPUT_PATHS",
    "EXPECTED_CHILD_COMMAND",
    "EXPECTED_CONTROL_PAIR_SET_SHA256",
    "EXPECTED_COMMAND",
    "EXPECTED_PARAMETERS",
    "EXPECTED_RESOURCES",
    "FREEZE_FILES",
    "FREEZE_MANIFEST_PATH",
    "FreezeFailure",
    "PRIVATE_RECEIPT_PATH",
    "PROTOCOL",
    "PUBLIC_RECEIPT_PATH",
    "RESULTS_ROOT",
    "canonical_json_bytes",
    "launch_child",
    "main",
    "monitor_process",
    "preflight_outputs",
    "run_controls",
    "run_synthetic_tests",
    "sample_rss_bytes",
    "sha256_bytes",
    "sha256_path",
    "validate_corpus_outputs",
    "verify_freeze_manifest",
]
