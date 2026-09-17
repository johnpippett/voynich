"""Run the frozen Celsus reference partition stage.

The runner hashes every pinned byte before it imports the adapter or parses
the projected JSONL. It does not read XML, use the network, or fit a model.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any, Mapping

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPOSITORY_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

PROTOCOL = "celsus-reference-control-v1"
FREEZE_RELATIVE = Path("experiments/medical/partition-freeze-v1.json")
OUTPUT_RELATIVE = Path("results/celsus-reference-control-v1")
ACCEPTANCE_RELATIVE = Path("reports/celsus-projection-v1/acceptance.json")
INITIAL_RELATIVE = Path("reports/celsus-projection-v1/initial-receipt.json")
SOURCE_RELATIVE = Path("results/celsus-projection-v1/celsus-lat5.xml")
MODULE_RELATIVE = Path("results/celsus-projection-v1/module-paragraphs.jsonl")
INDEPENDENT_RELATIVE = Path("results/celsus-projection-v1/independent-paragraphs.jsonl")
OUTPUT_FILES = ("partitions.private.json", "paragraphs.private.jsonl", "partition-manifest.json")
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}\Z")
EXPECTED_ACCEPTANCE_SHA256 = "8067be5cb874a8e53472d11e3188be0eb92b7c30c3def9f31de2451e06fc6faf"
EXPECTED_INITIAL_SHA256 = "f9333cdac5f45742f23ffb76b8600421635296fa1b855ab54412f3b94300be91"
EXPECTED_SOURCE_SHA256 = "a4a5194ba38a7efd5192d20f2a7b696f4fa64105010eb629aa7c35255a935145"
EXPECTED_PROJECTION_SHA256 = "f37d99f5ad0771c32c4d71934b58df00438ca7dadf870f89dc93b181c1d373f2"
EXPECTED_ORIGINAL_FREEZE_SHA256 = "5c48648f0098f1d303ddfc5309aa42d58899cd44b2b118a7cc55811f266f5631"

FREEZE_FILES = (
    Path("docs/plans/celsus-reference-control-v1.md"),
    Path("experiments/medical/reference_adapter.py"),
    Path("experiments/medical/test_reference_adapter.py"),
    Path("experiments/medical/run_partition.py"),
    Path("experiments/medical/test_run_partition.py"),
    Path("src/voynich/__init__.py"), Path("src/voynich/reference.py"),
    ACCEPTANCE_RELATIVE, INITIAL_RELATIVE,
    Path("experiments/medical/freeze-v1.json"),
    Path("docs/plans/celsus-projection-v1.md"),
    Path("experiments/medical/tei_projection.py"),
    Path("experiments/medical/run_projection.py"),
    Path("experiments/medical/test_tei_projection.py"),
    Path("experiments/medical/test_run_projection.py"),
    SOURCE_RELATIVE, MODULE_RELATIVE, INDEPENDENT_RELATIVE,
)
FIXED_HASHES = {
    ACCEPTANCE_RELATIVE.as_posix(): EXPECTED_ACCEPTANCE_SHA256,
    INITIAL_RELATIVE.as_posix(): EXPECTED_INITIAL_SHA256,
    SOURCE_RELATIVE.as_posix(): EXPECTED_SOURCE_SHA256,
    MODULE_RELATIVE.as_posix(): EXPECTED_PROJECTION_SHA256,
    INDEPENDENT_RELATIVE.as_posix(): EXPECTED_PROJECTION_SHA256,
    "experiments/medical/freeze-v1.json": EXPECTED_ORIGINAL_FREEZE_SHA256,
}


class PartitionFailure(ValueError):
    """A fixed input or output failure without source text in the message."""

    def __init__(self, kind: str, message: str) -> None:
        super().__init__(message)
        self.kind, self.message = kind, message


@dataclass(frozen=True)
class _Preflight:
    root: Path
    freeze_path: str
    freeze_sha256: str
    files_sha256: dict[str, str]
    bytes_by_path: dict[str, bytes]
    acceptance: dict[str, Any]


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def _relative_path(value: Any) -> Path:
    if not isinstance(value, str) or not value:
        raise PartitionFailure("freeze_manifest_files", "freeze path is invalid")
    path = Path(value)
    if path.is_absolute() or ".." in path.parts or path.as_posix() != value:
        raise PartitionFailure("freeze_manifest_files", "freeze path is invalid")
    return path


def _read_repo_file(root: Path, relative: Path) -> bytes:
    current = root
    for part in relative.parts:
        current /= part
        if current.is_symlink():
            raise PartitionFailure("pinned_symlink", "a pinned path is a symlink")
    if not current.is_file():
        raise PartitionFailure("pinned_file_missing", "a pinned file is unavailable")
    try:
        return current.read_bytes()
    except OSError as error:
        raise PartitionFailure("pinned_file_missing", "a pinned file is unavailable") from error


def _parse_freeze_manifest(data: bytes) -> dict[str, str]:
    try:
        manifest = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise PartitionFailure("freeze_manifest_json", "partition freeze is not valid JSON") from error
    if not isinstance(manifest, dict) or set(manifest) != {"schema_version", "protocol", "files"}:
        raise PartitionFailure("freeze_manifest_schema", "partition freeze fields do not match")
    if manifest.get("schema_version") != 1 or manifest.get("protocol") != PROTOCOL:
        raise PartitionFailure("freeze_manifest_schema", "partition freeze identity does not match")
    files = manifest.get("files")
    if not isinstance(files, list) or len(files) != len(FREEZE_FILES):
        raise PartitionFailure("freeze_manifest_files", "partition freeze file list does not match")
    expected = {path.as_posix() for path in FREEZE_FILES}
    entries: dict[str, str] = {}
    for item in files:
        if not isinstance(item, dict) or set(item) != {"path", "sha256"}:
            raise PartitionFailure("freeze_manifest_files", "partition freeze entry fields do not match")
        path, digest = _relative_path(item.get("path")), item.get("sha256")
        name = path.as_posix()
        if name not in expected or name in entries or not isinstance(digest, str) or SHA256_PATTERN.fullmatch(digest) is None:
            raise PartitionFailure("freeze_manifest_files", "partition freeze path or hash is invalid")
        entries[name] = digest
    if set(entries) != expected:
        raise PartitionFailure("freeze_manifest_files", "partition freeze path set does not match")
    return entries


def _verify_acceptance(data: bytes) -> dict[str, Any]:
    try:
        receipt = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise PartitionFailure("acceptance_json", "accepted projection receipt is not valid JSON") from error
    if not isinstance(receipt, dict) or any(
        receipt.get(key) != value for key, value in (
            ("protocol", "celsus-projection-v1"), ("status", "COMPLETE"),
            ("result", "PASS"), ("manual_acceptance", "ACCEPTED"),
        )
    ):
        raise PartitionFailure("acceptance_status", "accepted projection receipt is not accepted")
    source, projection = receipt.get("source"), receipt.get("projection")
    if (
        not isinstance(source, dict) or source.get("sha256") != EXPECTED_SOURCE_SHA256
        or not isinstance(projection, dict)
        or not isinstance(projection.get("module"), dict)
        or not isinstance(projection.get("independent"), dict)
        or projection["module"].get("sha256") != EXPECTED_PROJECTION_SHA256
        or projection["independent"].get("sha256") != EXPECTED_PROJECTION_SHA256
    ):
        raise PartitionFailure("acceptance_pin", "accepted projection receipt pins do not match")
    return receipt


def verify_freeze_manifest(
    freeze_path: Path = REPOSITORY_ROOT / FREEZE_RELATIVE, *, repository_root: Path = REPOSITORY_ROOT,
) -> _Preflight:
    """Verify the external allowlist and every pinned byte before parsing."""
    root, freeze = Path(repository_root).resolve(), Path(freeze_path)
    if not freeze.is_absolute():
        freeze = root / freeze
    if freeze.is_symlink():
        raise PartitionFailure("freeze_symlink", "partition freeze is a symlink")
    try:
        freeze_bytes = freeze.read_bytes()
    except OSError as error:
        raise PartitionFailure("freeze_manifest_missing", "partition freeze is unavailable") from error
    entries, bytes_by_path = _parse_freeze_manifest(freeze_bytes), {}
    for relative in FREEZE_FILES:
        name, data = relative.as_posix(), _read_repo_file(root, relative)
        actual = _sha256(data)
        if actual != entries[name]:
            raise PartitionFailure("freeze_hash_mismatch", "a pinned byte hash does not match")
        if name in FIXED_HASHES and actual != FIXED_HASHES[name]:
            raise PartitionFailure("freeze_fixed_pin", "a required source pin does not match")
        bytes_by_path[name] = data
    acceptance = _verify_acceptance(bytes_by_path[ACCEPTANCE_RELATIVE.as_posix()])
    try:
        display = freeze.resolve().relative_to(root).as_posix()
    except ValueError:
        display = freeze.as_posix()
    return _Preflight(root, display, _sha256(freeze_bytes), dict(entries), bytes_by_path, acceptance)


def _parse_module_records(data: bytes) -> tuple[dict[str, Any], ...]:
    try:
        lines = data.decode("utf-8").splitlines()
    except UnicodeDecodeError as error:
        raise PartitionFailure("projection_jsonl", "module projection is not UTF-8") from error
    if not lines:
        raise PartitionFailure("projection_jsonl", "module projection is empty")
    records: list[dict[str, Any]] = []
    for index, line in enumerate(lines, 1):
        if not line.strip():
            raise PartitionFailure("projection_jsonl", "module projection has a blank line")
        try:
            record = json.loads(line)
        except json.JSONDecodeError as error:
            raise PartitionFailure("projection_jsonl", f"module projection line {index} is invalid") from error
        if not isinstance(record, dict):
            raise PartitionFailure("projection_jsonl", "module projection record is not an object")
        records.append(record)
    return tuple(records)


def _load_adapter():
    from experiments.medical.reference_adapter import adapt_projected_paragraphs
    return adapt_projected_paragraphs


def _private_partition_bytes(partitions: Mapping[str, tuple[str, ...]]) -> bytes:
    return _canonical_json_bytes({name: list(partitions[name]) for name in ("train", "validation", "test")})


def _private_paragraph_bytes(paragraphs: Any) -> bytes:
    rows = []
    for item in paragraphs:
        row = dict(item.location)
        row.update(split=item.split, tokens=list(item.tokens), retained=item.retained, exclusion=item.exclusion,
                   rejected_run_count=item.rejected_run_count, roman_like_count=item.roman_like_count)
        rows.append(_canonical_json_bytes(row))
    return b"".join(rows)


def _public_manifest(preflight: _Preflight, adapter_manifest: dict[str, Any],
                     private_hashes: Mapping[str, str], private_sizes: Mapping[str, int]) -> dict[str, Any]:
    acceptance, source = preflight.acceptance, preflight.acceptance["source"]
    projection, adapter_name = acceptance["projection"], "experiments/medical/reference_adapter.py"
    adapter_bytes = _canonical_json_bytes(adapter_manifest)
    return {
        "schema_version": 1, "protocol": PROTOCOL,
        "freeze": {"path": preflight.freeze_path, "sha256": preflight.freeze_sha256, "files_sha256": dict(preflight.files_sha256)},
        "acceptance": {"path": ACCEPTANCE_RELATIVE.as_posix(), "sha256": EXPECTED_ACCEPTANCE_SHA256,
                        "status": acceptance["status"], "result": acceptance["result"], "manual_acceptance": acceptance["manual_acceptance"]},
        "source": {"path": SOURCE_RELATIVE.as_posix(), "sha256": source["sha256"], "bytes": len(preflight.bytes_by_path[SOURCE_RELATIVE.as_posix()])},
        "projection": {
            "module": {"path": MODULE_RELATIVE.as_posix(), "sha256": projection["module"]["sha256"], "bytes": len(preflight.bytes_by_path[MODULE_RELATIVE.as_posix()])},
            "independent": {"path": INDEPENDENT_RELATIVE.as_posix(), "sha256": projection["independent"]["sha256"], "bytes": len(preflight.bytes_by_path[INDEPENDENT_RELATIVE.as_posix()])}},
        "adapter": {"path": adapter_name, "sha256": preflight.files_sha256[adapter_name], "manifest_sha256": _sha256(adapter_bytes), "manifest": adapter_manifest},
        "private_outputs": {name: {"sha256": private_hashes[name], "bytes": private_sizes[name]} for name in sorted(private_hashes)},
        "raw_text_included": False,
    }


def _prepare_output_dir(path: Path, repository_root: Path = REPOSITORY_ROOT) -> None:
    root, target = Path(repository_root).resolve(), Path(path)
    if not target.is_absolute():
        target = root / target
    if ".." in target.parts:
        raise PartitionFailure("output_path", "output path contains parent traversal")
    try:
        relative = target.absolute().relative_to(root)
    except ValueError as error:
        raise PartitionFailure("output_path", "output path is outside the repository") from error
    current = root
    for index, part in enumerate(relative.parts):
        current /= part
        if current.is_symlink():
            raise PartitionFailure("output_symlink", "output path contains a symlink")
        if current.exists() and not current.is_dir():
            raise PartitionFailure("output_path", "output path contains a non-directory")
        if index == len(relative.parts) - 1 and current.exists():
            raise PartitionFailure("output_exists", "output directory already exists")
        if not current.exists():
            current.mkdir()


def _write_new(path: Path, data: bytes) -> None:
    if path.is_symlink() or path.exists():
        raise PartitionFailure("output_exists", "output file already exists")
    try:
        with path.open("xb") as stream:
            stream.write(data)
    except OSError as error:
        raise PartitionFailure("output_write", "output file could not be written") from error


def _run_partition(repository_root: Path, freeze_path: Path, output_dir: Path) -> dict[str, Any]:
    preflight = verify_freeze_manifest(freeze_path, repository_root=repository_root)
    records = _parse_module_records(preflight.bytes_by_path[MODULE_RELATIVE.as_posix()])
    adapted = _load_adapter()(records)
    private_data = {OUTPUT_FILES[0]: _private_partition_bytes(adapted.partitions), OUTPUT_FILES[1]: _private_paragraph_bytes(adapted.paragraphs)}
    private_hashes = {name: _sha256(data) for name, data in private_data.items()}
    public = _public_manifest(preflight, adapted.manifest, private_hashes, {name: len(data) for name, data in private_data.items()})
    _prepare_output_dir(output_dir, preflight.root)
    for name, data in private_data.items():
        _write_new(output_dir / name, data)
    _write_new(output_dir / OUTPUT_FILES[2], _canonical_json_bytes(public))
    return public


def run_partition() -> dict[str, Any]:
    """Run the fixed partition stage and return its public manifest."""
    return _run_partition(REPOSITORY_ROOT, REPOSITORY_ROOT / FREEZE_RELATIVE, REPOSITORY_ROOT / OUTPUT_RELATIVE)


def main() -> int:
    try:
        run_partition()
    except PartitionFailure as error:
        print(f"{error.kind}: {error.message}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
