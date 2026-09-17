"""Run the fixed Celsus known-cipher control core.

This module validates the frozen partition bytes, then delegates fitting and
test ordering to the unchanged homophonic control runner. It does not read
the manuscript or select a model.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import string
from typing import Any, Mapping

from experiments.homophonic.run_controls import run_control as frozen_run_control


ROOT = Path(__file__).resolve().parents[2]
PARTITION_DIR = ROOT / "results/celsus-reference-control-v1"
PARTITIONS_PATH = PARTITION_DIR / "partitions.private.json"
MANIFEST_PATH = PARTITION_DIR / "partition-manifest.json"
OUTPUT_PATH = PARTITION_DIR / "model/cold.json"
KEY_PATH = PARTITION_DIR / "model/cold.keys.json"
PROTOCOL = "celsus-reference-control-v1"
FAMILY = "cap2"
SEED = 7000
NODE_BUDGET = 1000
BOUND_ENGINE = "bitset"
WARM_START = "none"
ASCII_LOWER = frozenset(string.ascii_lowercase)
PARTITIONS_SHA256 = "ca6209869b934958c04b9707c0c70652046abb118d365c9c9f272c6adb7802f1"
PARAGRAPHS_SHA256 = "6bc2af80bc11f728b81e218b0dd6a0c51878aec075c0f2bbd4415fb4df0e4f93"
MANIFEST_SHA256 = "634ed31c54e1147ee930c6261ed9261938ec120f310db2e22ed54bca630dc9e1"


class ControlStudyFailure(ValueError):
    """A fixed input or output failure before the solver call."""

    def __init__(self, kind: str, message: str) -> None:
        super().__init__(message)
        self.kind, self.message = kind, message


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read_pinned(path: Path, expected: str, name: str) -> bytes:
    try:
        data = path.read_bytes()
    except OSError as error:
        raise ControlStudyFailure("input_missing", f"{name} is unavailable") from error
    if _sha256(data) != expected:
        raise ControlStudyFailure("input_hash_mismatch", f"{name} hash does not match")
    return data


def _parse_manifest(data: bytes) -> dict[str, Any]:
    try:
        value = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ControlStudyFailure("manifest_json", "partition manifest is not valid JSON") from error
    if not isinstance(value, dict):
        raise ControlStudyFailure("manifest_schema", "partition manifest is not an object")
    if value.get("schema_version") != 1 or value.get("protocol") != PROTOCOL:
        raise ControlStudyFailure("manifest_schema", "partition manifest identity does not match")
    if value.get("raw_text_included") is not False:
        raise ControlStudyFailure("manifest_scope", "partition manifest scope is not public-safe")
    private = value.get("private_outputs")
    if not isinstance(private, dict):
        raise ControlStudyFailure("manifest_schema", "private output hashes are missing")
    for name, expected in (
        ("partitions.private.json", PARTITIONS_SHA256),
        ("paragraphs.private.jsonl", PARAGRAPHS_SHA256),
    ):
        item = private.get(name)
        if not isinstance(item, dict) or item.get("sha256") != expected:
            raise ControlStudyFailure("manifest_pin", f"{name} hash is not pinned")
    return value


def _parse_partitions(data: bytes) -> dict[str, list[str]]:
    try:
        value = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ControlStudyFailure("partition_json", "partition file is not valid JSON") from error
    if not isinstance(value, dict) or set(value) != {"train", "validation", "test"}:
        raise ControlStudyFailure("partition_schema", "partition file must contain three splits")
    result: dict[str, list[str]] = {}
    for split in ("train", "validation", "test"):
        words = value[split]
        if not isinstance(words, list) or not words:
            raise ControlStudyFailure("partition_empty", f"{split} partition is empty")
        if any(
            not isinstance(word, str) or not word or not word.isascii()
            or any(letter not in ASCII_LOWER for letter in word)
            for word in words
        ):
            raise ControlStudyFailure("partition_word", f"{split} contains a non-ASCII word")
        result[split] = words
    return result


def _require_outputs_absent() -> None:
    for path in (OUTPUT_PATH, KEY_PATH):
        if path.exists() or path.is_symlink():
            raise ControlStudyFailure("output_exists", "fixed control output already exists")


def _metadata(manifest_hash: str, partitions_hash: str, manifest: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "language": "celsus",
        "reference": "Celsus projected paragraphs",
        "partition_manifest_path": "results/celsus-reference-control-v1/partition-manifest.json",
        "partition_manifest_sha256": manifest_hash,
        "partitions_private_path": "results/celsus-reference-control-v1/partitions.private.json",
        "partitions_private_sha256": partitions_hash,
        "partition_protocol": manifest["protocol"],
        "scope": "one ancient medical author and work; descriptive known-cipher control",
    }


def run_celsus_control() -> dict[str, Any]:
    """Validate pinned partitions and run one fixed cold control."""
    partition_bytes = _read_pinned(PARTITIONS_PATH, PARTITIONS_SHA256, "partitions.private.json")
    manifest_bytes = _read_pinned(MANIFEST_PATH, MANIFEST_SHA256, "partition-manifest.json")
    manifest = _parse_manifest(manifest_bytes)
    partitions = _parse_partitions(partition_bytes)
    _require_outputs_absent()
    metadata = _metadata(MANIFEST_SHA256, PARTITIONS_SHA256, manifest)
    return frozen_run_control(
        partitions,
        family=FAMILY,
        seed=SEED,
        node_budget=NODE_BUDGET,
        output_path=OUTPUT_PATH,
        bound_engine=BOUND_ENGINE,
        warm_start=WARM_START,
        metadata=metadata,
    )


def main() -> int:
    try:
        report = run_celsus_control()
    except ControlStudyFailure as error:
        print(f"{error.kind}: fixed control input failed", file=sys.stderr)
        return 2
    except Exception as error:  # pragma: no cover - outer runner owns diagnostics
        print(f"control_failure: {type(error).__name__}", file=sys.stderr)
        return 1
    status = report.get("solver", {}).get("status", "unknown")
    print(json.dumps({"family": FAMILY, "status": status}, sort_keys=True))
    return 0


__all__ = [
    "BOUND_ENGINE", "ControlStudyFailure", "FAMILY", "KEY_PATH", "MANIFEST_PATH",
    "MANIFEST_SHA256", "NODE_BUDGET", "OUTPUT_PATH", "PARTITIONS_PATH",
    "PARTITIONS_SHA256", "SEED", "WARM_START", "main", "run_celsus_control",
]


if __name__ == "__main__":
    raise SystemExit(main())
