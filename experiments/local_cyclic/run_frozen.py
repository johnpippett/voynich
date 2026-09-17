"""Run the fixed local-cyclic check after an external byte freeze."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import importlib
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
from typing import Any, Mapping


PROTOCOL = "vms-local-cyclic-falsification-v1"
FREEZE_RELATIVE = Path("experiments/local_cyclic/freeze-v1.json")
RESULTS_RELATIVE = Path("results/vms-local-cyclic-falsification-v1")
OUTPUT_RELATIVES = (
    "results/vms-local-cyclic-falsification-v1/ZL3b-n-raw_eva.json",
    "results/vms-local-cyclic-falsification-v1/ZL3b-n-visual_six.json",
    "results/vms-local-cyclic-falsification-v1/IT2a-n-raw_eva.json",
    "results/vms-local-cyclic-falsification-v1/IT2a-n-visual_six.json",
)
OUTPUT_PATHS = tuple(Path(value) for value in OUTPUT_RELATIVES)
CORPORA = (
    ("ZL3b-n", Path("data/raw/ZL3b-n.txt")),
    ("IT2a-n", Path("data/raw/IT2a-n.txt")),
)
TRACKS = (("raw_eva", "raw"), ("visual_six", "visual"))
FROZEN_FILES = (
    "docs/plans/vms-local-cyclic-falsification-v1.md",
    "experiments/local_cyclic/__init__.py",
    "experiments/local_cyclic/certificate.py",
    "experiments/local_cyclic/test_certificate.py",
    "experiments/local_cyclic/run_frozen.py",
    "experiments/local_cyclic/test_run_frozen.py",
    "experiments/homophonic/units.py",
    "experiments/homophonic/test_units.py",
    "src/voynich/__init__.py",
    "src/voynich/corpus.py",
    "data/source_manifest.json",
    "data/raw/ZL3b-n.txt",
    "data/raw/IT2a-n.txt",
)
EXPECTED_COMMAND = ["python", "-m", "experiments.local_cyclic.run_frozen"]
EXPECTED_SOURCE_IDS = ["ZL3b-n", "IT2a-n"]
EXPECTED_UNITIZATIONS = ["raw_eva", "visual_six"]
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
ROOT = Path(__file__).resolve().parents[2]
# Keep the names used by the other fixed runners available to freeze tooling.
REPOSITORY_ROOT = ROOT
FREEZE_MANIFEST_PATH = FREEZE_RELATIVE
ALL_OUTPUT_PATHS = OUTPUT_PATHS


class RunnerError(RuntimeError):
    """Base class for safe fixed-runner failures."""

    code = "runner_error"


class FreezeError(RunnerError):
    """The external freeze record or one pinned input is invalid."""

    code = "freeze_error"


class OutputExistsError(RunnerError):
    """An output or output path component already exists."""

    code = "output_exists"


class SyntheticControlError(RunnerError):
    """The frozen synthetic control tests did not pass."""

    code = "synthetic_controls_failed"


@dataclass(frozen=True)
class FreezeInfo:
    manifest: Mapping[str, Any]
    manifest_sha256: str
    file_hashes: Mapping[str, str]


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    try:
        return _sha256_bytes(path.read_bytes())
    except OSError as exc:
        raise FreezeError("cannot read a pinned freeze input") from exc


def _regular_file(root: Path, relative: str) -> Path:
    path = root / relative
    try:
        if path.is_symlink() or not path.is_file():
            raise FreezeError("a frozen input is not a regular file")
    except OSError as exc:
        raise FreezeError("cannot inspect a frozen input") from exc
    cursor = path.parent
    while cursor != root:
        if cursor.is_symlink():
            raise FreezeError("a frozen input has a symlinked parent")
        if cursor == cursor.parent:
            raise FreezeError("a frozen input is outside the project root")
        cursor = cursor.parent
    return path


def _relative_path(value: Any) -> str:
    if not isinstance(value, str) or not value or "\\" in value:
        raise FreezeError("freeze paths must be relative POSIX strings")
    path = Path(value)
    if path.is_absolute() or ".." in path.parts or path.as_posix() != value:
        raise FreezeError("freeze paths must be relative POSIX strings")
    return value


def _require_equal(manifest: Mapping[str, Any], key: str, expected: Any) -> None:
    if manifest.get(key) != expected:
        raise FreezeError("freeze parameters do not match the fixed protocol")


def verify_freeze(root: Path | str = ROOT) -> FreezeInfo:
    """Verify every allowlisted byte before importing source-processing code."""

    root = Path(root).resolve()
    freeze_path = _regular_file(root, FREEZE_RELATIVE.as_posix())
    try:
        freeze_bytes = freeze_path.read_bytes()
        manifest = json.loads(freeze_bytes.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, TypeError) as exc:
        raise FreezeError("freeze record is not valid UTF-8 JSON") from exc
    if not isinstance(manifest, dict):
        raise FreezeError("freeze record must be a JSON object")
    _require_equal(manifest, "schema_version", 1)
    _require_equal(manifest, "protocol", PROTOCOL)
    _require_equal(manifest, "command", EXPECTED_COMMAND)
    _require_equal(manifest, "uncertain_spaces", "split")
    _require_equal(manifest, "source_ids", EXPECTED_SOURCE_IDS)
    _require_equal(manifest, "unitizations", EXPECTED_UNITIZATIONS)
    _require_equal(manifest, "outputs", list(OUTPUT_RELATIVES))
    runtime = manifest.get("runtime")
    if not isinstance(runtime, dict) or not isinstance(runtime.get("python"), str):
        raise FreezeError("freeze runtime does not record a Python version")

    entries = manifest.get("files")
    if not isinstance(entries, list) or [item.get("path") for item in entries if isinstance(item, dict)] != list(FROZEN_FILES):
        raise FreezeError("freeze allowlist does not match the fixed input set")
    hashes: dict[str, str] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            raise FreezeError("freeze allowlist entries must be objects")
        relative = _relative_path(entry.get("path"))
        expected = entry.get("sha256")
        if relative in hashes or not isinstance(expected, str) or not SHA256_RE.fullmatch(expected):
            raise FreezeError("freeze allowlist contains an invalid digest")
        if relative not in FROZEN_FILES:
            raise FreezeError("freeze allowlist contains an unknown file")
        path = _regular_file(root, relative)
        actual = _sha256_file(path)
        if actual != expected:
            raise FreezeError("a frozen input digest does not match")
        hashes[relative] = actual
    if tuple(hashes) != FROZEN_FILES:
        raise FreezeError("freeze allowlist order is not fixed")
    return FreezeInfo(manifest, _sha256_bytes(freeze_bytes), hashes)


verify_freeze_manifest = verify_freeze


def _check_output_paths(root: Path) -> None:
    """Check all output names and every existing path component before parsing."""

    for relative in OUTPUT_RELATIVES:
        path = root / relative
        cursor = path
        while cursor != root:
            if cursor.is_symlink() or (
                cursor.exists() and cursor != path and not cursor.is_dir()
            ):
                raise OutputExistsError("an output path component already exists")
            if cursor == cursor.parent:
                raise OutputExistsError("an output path escapes the project root")
            cursor = cursor.parent
        if path.exists() or path.is_symlink():
            raise OutputExistsError("an output already exists")


def _run_synthetic_controls(root: Path) -> None:
    environment = dict(os.environ)
    source_path = root / "src"
    current = environment.get("PYTHONPATH", "")
    environment["PYTHONPATH"] = os.pathsep.join(
        item for item in (str(root), str(source_path), current) if item
    )
    command = [
        sys.executable,
        "-m",
        "unittest",
        "experiments.local_cyclic.test_certificate",
        "experiments.homophonic.test_units",
    ]
    try:
        completed = subprocess.run(
            command,
            cwd=root,
            env=environment,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise SyntheticControlError("synthetic control process failed") from exc
    if completed.returncode != 0:
        raise SyntheticControlError("synthetic control tests failed")
    if not re.search(r"Ran\s+21\s+tests?", completed.stderr + completed.stdout):
        raise SyntheticControlError("the expected synthetic control count did not run")


def _load_runtime(root: Path):
    source_root = root / "src"
    for path in (root, source_root):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))
    corpus = importlib.import_module("voynich.corpus")
    certificate = importlib.import_module("experiments.local_cyclic.certificate")
    units = importlib.import_module("experiments.homophonic.units")
    return corpus, certificate, units


def _empty_counts() -> dict[str, int]:
    return {
        "record_count": 0,
        "eligible_word_count": 0,
        "eligible_unit_count": 0,
        "adjacent_pair_count": 0,
        "certificate_count": 0,
        "affected_word_count": 0,
    }


def _run_track(
    *,
    source_id: str,
    source_relative: str,
    extracted_records: list[tuple[dict[str, Any], Any]],
    excluded: Mapping[str, int],
    representation: str,
    certificate: Any,
) -> dict[str, Any]:
    counts = _empty_counts()
    locations: list[dict[str, Any]] = []
    for record_index, (record, extraction) in enumerate(extracted_records):
        result = certificate.count_local_certificates(
            extraction.spans, representation=representation
        )
        counts["record_count"] += 1
        counts["eligible_word_count"] += result.eligible_word_count
        counts["eligible_unit_count"] += result.eligible_unit_count
        counts["adjacent_pair_count"] += result.adjacent_pair_count
        counts["certificate_count"] += result.certificate_count
        # Word indexes restart in every locus. Sum per-record values by design.
        counts["affected_word_count"] += result.affected_word_count
        for item in result.locations:
            location: dict[str, Any] = {
                "source_file": source_relative,
                "record_index": record_index,
                "folio": record.get("folio"),
                "locus": record.get("locus"),
                "transcriber": record.get("transcriber"),
                "candidate_word_index": item.word_index,
                "unit_index": item.unit_index,
                "unit": item.unit,
            }
            if item.unit_span is not None:
                location["unit_span"] = list(item.unit_span)
            locations.append(location)
    if counts["certificate_count"] != len(locations):
        raise RunnerError("certificate locations do not match the count")
    status = (
        "inconclusive_no_eligible_words"
        if counts["eligible_word_count"] == 0
        else "falsified_for_fixed_track"
        if counts["certificate_count"]
        else "not_falsified_by_local_check"
    )
    return {
        "schema_version": 1,
        "protocol": PROTOCOL,
        "source_id": source_id,
        "source_file": source_relative,
        "unitization": "raw_eva" if representation == "raw" else "visual_six",
        "representation": representation,
        "uncertain_spaces": "split",
        "model_contract": (
            "fixed cyclic emitter with disjoint preimage sets of k>=2 units, "
            "one distinct next unit per repeated symbol, and reset at each word"
        ),
        "counts": counts,
        "excluded_word_counts": dict(sorted(excluded.items())),
        "source_file_counts": {
            source_relative: {
                **counts,
                "excluded_word_counts": dict(sorted(excluded.items())),
            }
        },
        "status": status,
        "certificate_locations": locations,
        "image_review": "not_performed",
    }


def _attach_provenance(
    report: dict[str, Any], *, output_relative: str, info: FreezeInfo, units: Any
) -> dict[str, Any]:
    result = dict(report)
    result["output_file"] = output_relative
    result["unitization_version"] = units.VERSION
    result["freeze_manifest_sha256"] = info.manifest_sha256
    result["input_hashes"] = dict(info.file_hashes)
    result["runtime"] = {
        "python": platform.python_version(),
        "command": list(EXPECTED_COMMAND),
    }
    return result


def run_frozen(root: Path | str = ROOT) -> dict[tuple[str, str], dict[str, Any]]:
    """Run the four fixed source/track outputs under a verified freeze."""

    root = Path(root).resolve()
    info = verify_freeze(root)
    _check_output_paths(root)
    _run_synthetic_controls(root)
    corpus, certificate, units = _load_runtime(root)
    reports: dict[tuple[str, str], dict[str, Any]] = {}
    for source_id, source_relative_path in CORPORA:
        source_path = root / source_relative_path
        records = corpus.parse_ivtff(source_path, uncertain_spaces="split")
        source_relative = source_relative_path.as_posix()
        extracted_records = [
            (record, certificate.extract_word_spans(record["text_raw"]))
            for record in records
        ]
        excluded: dict[str, int] = {}
        for _, extraction in extracted_records:
            for reason, count in extraction.excluded_counts:
                excluded[reason] = excluded.get(reason, 0) + count
        for track_name, representation in TRACKS:
            report = _run_track(
                source_id=source_id,
                source_relative=source_relative,
                extracted_records=extracted_records,
                excluded=excluded,
                representation=representation,
                certificate=certificate,
            )
            output_relative = (
                RESULTS_RELATIVE / f"{source_id}-{track_name}.json"
            ).as_posix()
            reports[(source_id, track_name)] = _attach_provenance(
                report, output_relative=output_relative, info=info, units=units
            )
    for relative in OUTPUT_RELATIVES:
        report = next(item for item in reports.values() if item["output_file"] == relative)
        output_path = root / relative
        output_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with output_path.open("xb") as handle:
                handle.write(
                    (json.dumps(report, ensure_ascii=True, indent=2, sort_keys=True) + "\n").encode()
                )
        except FileExistsError as exc:
            raise OutputExistsError("an output already exists") from exc
    return reports


def main() -> int:
    """Run the fixed command without command-line options."""

    if len(sys.argv) != 1:
        print(json.dumps({"status": "blocked", "reason": "no_options"}, sort_keys=True))
        return 2
    try:
        reports = run_frozen(ROOT)
    except RunnerError as exc:
        print(json.dumps({"status": "blocked", "reason": exc.code}, sort_keys=True))
        return 1
    print(json.dumps({
        "status": "complete",
        "protocol": PROTOCOL,
        "outputs": [item["output_file"] for item in reports.values()],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
