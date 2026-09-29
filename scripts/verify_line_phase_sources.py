#!/usr/bin/env python3
"""Verify the fixed line-phase source rows and their integer certificates."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import platform
import re
import sys
import time
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
FREE_COMMENT_RE = re.compile(r"<![^>]*>")
CONTROL_RE = re.compile(r"<(?:%|\$|@[A-Z]=[A-Za-z0-9@])>")
WORD_LINE_RE = re.compile(r"[a-z]+(?:\.[a-z]+)*")
LOCUS_RE = re.compile(r"^[A-Za-z][A-Za-z0-9]*\.([0-9]+),([@+*=&~/!])")
SOURCES = {
    "ZL": "data/raw/ZL3b-n.txt",
    "IT": "data/raw/IT2a-n.txt",
}
LABELS = ("A", "B")
REPRESENTATIONS = ("visual", "raw")
EXPECTED_TRACKS = {
    f"{source}-{label}-{representation}"
    for source in SOURCES
    for label in LABELS
    for representation in REPRESENTATIONS
}
FROZEN_FILES = {
    "data/bifolio_manifest.json",
    "data/source_manifest.json",
    "docs/plans/line-phase-lattice-v1.md",
    "experiments/homophonic/units.py",
    "reports/line-triplet-boundary-certificates.json",
    "scripts/run_line_phase_lattice.py",
    "scripts/line_phase_lattice.py",
    "scripts/check_line_phase_lattice.py",
    "scripts/check_line_phase_freeze.py",
    "scripts/verify_line_phase_sources.py",
    "src/voynich/__init__.py",
    "src/voynich/corpus.py",
    "src/voynich/groups.py",
}
BASELINE_PATH = "reports/line-triplet-boundary-certificates.json"
MANIFEST_PATH = "data/source_manifest.json"
FREEZE_PATH = "experiments/line_phase/freeze-v1.json"
RESULTS_PATH = "reports/line-phase-lattice-v1"
EVIDENCE_PATH = "results/line-phase-lattice-verification-v1"
MAX_INTEGER_BITS = 4096
MAX_CERTIFICATE_SECONDS = 600
COMMAND_TEMPLATE = (
    "python scripts/verify_line_phase_sources.py --freeze "
    "experiments/line_phase/freeze-v1.json --results "
    "reports/line-phase-lattice-v1 --output "
    "results/line-phase-lattice-verification-v1/receipt.json"
)


class VerificationError(RuntimeError):
    """A frozen input or verification check failed."""


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise VerificationError("JSON has a duplicate object key")
        value[key] = item
    return value


def json_value(path: Path, label: str) -> Any:
    try:
        return json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=lambda value: (_ for _ in ()).throw(
                VerificationError("JSON has a non-finite value")
            ),
        )
    except VerificationError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise VerificationError(f"Cannot read valid JSON: {label}") from error


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def file_sha256(path: Path) -> str:
    try:
        return sha256_bytes(path.read_bytes())
    except OSError as error:
        raise VerificationError("Cannot read a pinned file") from error


def object_sha256(value: Any) -> str:
    data = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256_bytes(data)


def same_json(left: Any, right: Any) -> bool:
    return object_sha256(left) == object_sha256(right)


def _repo_path(value: str, label: str, *, directory: bool = False) -> Path:
    if not isinstance(value, str) or not value or "\\" in value:
        raise VerificationError(f"Invalid repository path: {label}")
    relative = PurePosixPath(value)
    if relative.is_absolute() or any(part in {"", ".", ".."} for part in relative.parts):
        raise VerificationError(f"Unsafe repository path: {label}")
    path = ROOT.joinpath(*relative.parts)
    try:
        resolved = path.resolve(strict=True)
    except OSError as error:
        raise VerificationError(f"Missing repository path: {label}") from error
    if not resolved.is_relative_to(ROOT):
        raise VerificationError(f"Repository path leaves the project: {label}")
    if directory and not resolved.is_dir():
        raise VerificationError(f"Expected a directory: {label}")
    if not directory and not resolved.is_file():
        raise VerificationError(f"Expected a file: {label}")
    return resolved


def _repo_arg(value: str, label: str, *, directory: bool = False) -> tuple[str, Path]:
    path = _repo_path(value, label, directory=directory)
    return path.relative_to(ROOT).as_posix(), path


def _output_path(value: str) -> tuple[str, Path]:
    if not isinstance(value, str) or not value or "\\" in value:
        raise VerificationError("Invalid output path")
    relative = PurePosixPath(value)
    if relative.is_absolute() or any(part in {"", ".", ".."} for part in relative.parts):
        raise VerificationError("Unsafe output path")
    if relative.parts[: len(PurePosixPath(EVIDENCE_PATH).parts)] != PurePosixPath(EVIDENCE_PATH).parts:
        raise VerificationError("Output must be inside the ignored verification directory")
    output = ROOT.joinpath(*relative.parts)
    parent = output.parent.resolve()
    if not parent.is_relative_to(ROOT):
        raise VerificationError("Output path leaves the project")
    return relative.as_posix(), output


def _write_new_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, sort_keys=True, indent=2, allow_nan=False)
            handle.write("\n")
    except FileExistsError as error:
        raise VerificationError("Refusing to replace an existing output") from error
    except (OSError, TypeError, ValueError) as error:
        raise VerificationError("Cannot write the verification output") from error


def _write_new_text(path: Path, value: str) -> None:
    try:
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(value)
    except FileExistsError as error:
        raise VerificationError("Refusing to replace an existing output") from error
    except OSError as error:
        raise VerificationError("Cannot write the verification hash") from error


def _int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _check_integer_limit(value: int) -> None:
    if abs(value).bit_length() > MAX_INTEGER_BITS:
        raise VerificationError("Certificate input or arithmetic value exceeds 4,096 bits")


def _check_deadline(started: float) -> None:
    if time.monotonic() - started > MAX_CERTIFICATE_SECONDS:
        raise VerificationError("Certificate check exceeds 600 seconds")


def verify_certificate(
    rows: Sequence[Sequence[int]],
    certificate: Mapping[str, Any],
    references: Sequence[Mapping[str, Any]] | None = None,
) -> int:
    """Check the support rows and prove B A = I by direct multiplication."""

    started = time.monotonic()
    if not isinstance(certificate, Mapping):
        raise VerificationError("Certificate must be an object")
    if certificate.get("status") != "certified":
        raise VerificationError("Certificate is not certified")
    if not rows or not rows[0]:
        raise VerificationError("Integer matrix is empty")
    width = len(rows[0])
    for row in rows:
        _check_deadline(started)
        if len(row) != width or any(not _int(value) for value in row):
            raise VerificationError("Integer matrix has invalid rows")
        for value in row:
            _check_integer_limit(value)
    if certificate.get("original_input_row_count") != len(rows):
        raise VerificationError("Certificate input row count differs")
    if certificate.get("columns") != width:
        raise VerificationError("Certificate column count differs")

    indexes = certificate.get("support_indices")
    support_rows = certificate.get("support_rows")
    inverse = certificate.get("left_inverse")
    if not isinstance(indexes, list) or not indexes:
        raise VerificationError("Certificate support indexes are missing")
    if any(not _int(index) or index < 0 or index >= len(rows) for index in indexes):
        raise VerificationError("Certificate support index is invalid")
    if indexes != sorted(set(indexes)):
        raise VerificationError("Certificate support indexes are not sorted and unique")
    support_count = len(indexes)
    expected_rows = [list(rows[index]) for index in indexes]
    if (
        not isinstance(support_rows, list)
        or len(support_rows) != support_count
        or any(
            not isinstance(row, list)
            or len(row) != width
            or any(not _int(value) for value in row)
            for row in support_rows
        )
    ):
        raise VerificationError("Certificate support rows have invalid values")
    if not same_json(support_rows, expected_rows):
        raise VerificationError("Certificate support rows differ from source rows")
    for row in support_rows:
        for value in row:
            _check_integer_limit(value)
    if references is not None:
        if len(references) != len(rows):
            raise VerificationError("Source reference count differs from matrix rows")
        expected_references = [dict(references[index]) for index in indexes]
        if not same_json(certificate.get("source_references"), expected_references):
            raise VerificationError("Certificate source references differ")

    if support_count < width or not isinstance(inverse, list) or len(inverse) != width:
        raise VerificationError("Certificate left-inverse shape is invalid")
    if any(
        not isinstance(row, list)
        or len(row) != support_count
        or any(not _int(value) for value in row)
        for row in inverse
    ):
        raise VerificationError("Certificate left inverse has invalid values")
    for row in inverse:
        for value in row:
            _check_integer_limit(value)

    products = 0
    for left_row in range(width):
        for column in range(width):
            total = 0
            for support_index in range(support_count):
                _check_deadline(started)
                term = inverse[left_row][support_index] * support_rows[support_index][column]
                _check_integer_limit(term)
                total += term
                _check_integer_limit(total)
            expected = int(left_row == column)
            if total != expected:
                raise VerificationError("Direct integer product B A is not identity")
            products += 1
    return products


def _read_freeze(path: Path) -> tuple[dict[str, Any], dict[str, str], dict[str, dict[str, str]]]:
    freeze = json_value(path, "freeze")
    if not isinstance(freeze, dict):
        raise VerificationError("Freeze must be an object")
    files = freeze.get("files")
    sources = freeze.get("sources")
    if not isinstance(files, dict) or not isinstance(sources, dict):
        raise VerificationError("Freeze file or source pins are missing")
    if freeze.get("schema") != "line-phase-lattice-freeze-v1":
        raise VerificationError("Freeze schema differs")
    if set(files) != FROZEN_FILES:
        raise VerificationError("Freeze file set is incomplete or unexpected")
    file_hashes: dict[str, str] = {}
    for relative, expected in files.items():
        if not isinstance(relative, str) or not isinstance(expected, str):
            raise VerificationError("Freeze file pin is invalid")
        if re.fullmatch(r"[0-9a-f]{64}", expected) is None:
            raise VerificationError("Freeze file hash is invalid")
        pinned = _repo_path(relative, "freeze file")
        actual = file_sha256(pinned)
        if actual != expected:
            raise VerificationError(f"Frozen file hash differs: {relative}")
        file_hashes[relative] = actual

    if set(sources) != set(SOURCES):
        raise VerificationError("Freeze must pin exactly ZL and IT")
    source_hashes: dict[str, dict[str, str]] = {}
    manifest = json_value(ROOT / MANIFEST_PATH, "source manifest")
    entries = manifest.get("sources") if isinstance(manifest, dict) else None
    if not isinstance(entries, list):
        raise VerificationError("Source manifest is invalid")
    manifest_sources = {
        entry.get("id"): entry
        for entry in entries
        if isinstance(entry, dict) and isinstance(entry.get("id"), str)
    }
    for source, expected_path in SOURCES.items():
        pin = sources[source]
        manifest_pin = manifest_sources.get(source)
        if not isinstance(pin, dict) or not isinstance(manifest_pin, dict):
            raise VerificationError(f"Source pin is invalid: {source}")
        relative = pin.get("path")
        digest = pin.get("sha256")
        if relative != expected_path or manifest_pin.get("path") != expected_path:
            raise VerificationError(f"Source path differs from the source manifest: {source}")
        if digest != manifest_pin.get("sha256") or re.fullmatch(r"[0-9a-f]{64}", str(digest)) is None:
            raise VerificationError(f"Source hash differs from the source manifest: {source}")
        path_to_check = _repo_path(relative, f"source {source}")
        actual = file_sha256(path_to_check)
        if actual != digest:
            raise VerificationError(f"Source hash differs: {source}")
        source_hashes[source] = {"path": relative, "sha256": actual}
    return freeze, file_hashes, source_hashes


def _strict_words(record: Mapping[str, Any]) -> tuple[tuple[str, ...] | None, str | None]:
    if int(record.get("excluded_tokens", 0)):
        return None, "parser_rejection"
    clean = CONTROL_RE.sub("", FREE_COMMENT_RE.sub("", str(record.get("text_raw", ""))))
    if WORD_LINE_RE.fullmatch(clean) is None:
        return None, "strict_spelling"
    words = tuple(clean.split("."))
    if len(words) < 3:
        return None, "fewer_than_three_words"
    tokens = record.get("tokens")
    if not isinstance(tokens, (list, tuple)) or tuple(tokens) != words:
        return None, "parser_word_mismatch"
    return words, None


def _locus_parts(locus: Any) -> tuple[int, str] | None:
    match = LOCUS_RE.match(str(locus))
    if match is None:
        return None
    return int(match.group(1)), match.group(2)


def _reference(
    record: Mapping[str, Any], index: int, following: Mapping[str, Any], group: str, words: Sequence[str]
) -> dict[str, Any]:
    return {
        "folio": str(record["folio"]),
        "group": str(group),
        "line_sha256": object_sha256(words),
        "locus": str(record["locus"]),
        "next_kind": str(following["kind"]),
        "next_locus": str(following["locus"]),
        "source_record_index": index,
        "word_count": len(words),
    }


def select_records(records: Sequence[Mapping[str, Any]], group_functions: tuple[Any, Any, Any]) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Select lines with a local copy of the frozen format rules."""

    group_id, split_bucket, split_name = group_functions
    selected: list[dict[str, Any]] = []
    excluded: Counter[str] = Counter()
    for index, record in enumerate(records):
        following = records[index + 1] if index + 1 < len(records) else None
        current_locus = _locus_parts(record.get("locus"))
        following_locus = _locus_parts(following.get("locus")) if following is not None else None
        reason: str | None = None
        if record.get("kind") not in {"P0", "P1"}:
            reason = "non_paragraph_kind"
        elif record.get("metadata", {}).get("L") not in {"A", "B"}:
            reason = "missing_class"
        elif current_locus is None or current_locus[1] not in {"+", "*"}:
            reason = "current_locator"
        elif following is None or following.get("folio") != record.get("folio"):
            reason = "no_next_on_folio"
        elif following_locus is None or following_locus[0] != current_locus[0] + 1:
            reason = "nonconsecutive_next_locus"
        elif following_locus[1] not in {"+", "*"}:
            reason = "next_locator"
        else:
            words, reason = _strict_words(record)
        if reason is not None:
            excluded[reason] += 1
            continue

        group = group_id(str(record["folio"]))
        split = split_name(split_bucket(group))
        selected.append(
            {
                "L": str(record["metadata"]["L"]),
                "split": split,
                "words": words,
                "reference": _reference(record, index, following, group, words),
            }
        )
    return selected, dict(sorted(excluded.items()))


def _baseline_maps(baseline: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    raw_sources = baseline.get("sources")
    if not isinstance(raw_sources, list):
        raise VerificationError("Three-digit baseline has no source list")
    sources: dict[str, dict[str, Any]] = {}
    for item in raw_sources:
        if not isinstance(item, dict) or item.get("source") not in SOURCES:
            raise VerificationError("Three-digit baseline has an invalid source")
        name = item["source"]
        if name in sources:
            raise VerificationError("Three-digit baseline has a duplicate source")
        sources[name] = item
    if set(sources) != set(SOURCES):
        raise VerificationError("Three-digit baseline source set differs")
    return sources


def _baseline_track_map(source: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    raw_tracks = source.get("tracks")
    if not isinstance(raw_tracks, list):
        raise VerificationError("Three-digit baseline track list is invalid")
    tracks: dict[str, dict[str, Any]] = {}
    for track in raw_tracks:
        if not isinstance(track, dict):
            raise VerificationError("Three-digit baseline track is invalid")
        key = f"{track.get('L')}-{track.get('representation')}"
        if key in tracks:
            raise VerificationError("Three-digit baseline has a duplicate track")
        tracks[key] = track
    expected = {f"{label}-{representation}" for label in LABELS for representation in REPRESENTATIONS}
    if set(tracks) != expected:
        raise VerificationError("Three-digit baseline track set differs")
    return tracks


def _result_source_map(result: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    raw_sources = result.get("sources")
    if not isinstance(raw_sources, list):
        raise VerificationError("Study result has no source list")
    sources: dict[str, dict[str, Any]] = {}
    for item in raw_sources:
        if not isinstance(item, dict) or item.get("source") not in SOURCES:
            raise VerificationError("Study result has an invalid source")
        name = item["source"]
        if name in sources:
            raise VerificationError("Study result has a duplicate source")
        sources[name] = item
    if set(sources) != set(SOURCES):
        raise VerificationError("Study result source set differs")
    return sources


def _result_track_map(source: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    raw_tracks = source.get("tracks")
    if not isinstance(raw_tracks, list):
        raise VerificationError("Study result track list is invalid")
    tracks: dict[str, dict[str, Any]] = {}
    for track in raw_tracks:
        if not isinstance(track, dict):
            raise VerificationError("Study result track is invalid")
        key = f"{track.get('L')}-{track.get('representation')}"
        if key in tracks:
            raise VerificationError("Study result has a duplicate track")
        tracks[key] = track
    expected = {f"{label}-{representation}" for label in LABELS for representation in REPRESENTATIONS}
    if set(tracks) != expected:
        raise VerificationError("Study result track set differs")
    return tracks


def _validate_track_certificate(
    source: str,
    source_hash: str,
    label: str,
    representation: str,
    alphabet: Sequence[str],
    rows: Sequence[Sequence[int]],
    references: Sequence[Mapping[str, Any]],
    track_result: Mapping[str, Any],
    baseline_track: Mapping[str, Any],
    result_dir: Path,
) -> dict[str, Any]:
    if track_result.get("status") != "certified":
        raise VerificationError(f"Study track is not certified: {source}-{label}-{representation}")
    if not same_json(track_result.get("alphabet"), list(alphabet)):
        raise VerificationError("Study result alphabet differs")
    width = len(alphabet) + 2
    selection_hash = object_sha256(list(references))
    integer_hash = object_sha256([list(row) for row in rows])
    reduced = sorted({tuple(value % 3 for value in row) for row in rows})
    modulo_three_hash = object_sha256(reduced)

    old_stage = baseline_track.get("stages", {}).get("train")
    if not isinstance(old_stage, dict):
        raise VerificationError("Three-digit baseline has no training record")
    if not same_json(baseline_track.get("alphabet"), list(alphabet)):
        raise VerificationError("Three-digit baseline alphabet differs")
    if old_stage.get("selected_lines") != len(rows):
        raise VerificationError("Three-digit training line count differs")
    if old_stage.get("selection_sha256") != selection_hash:
        raise VerificationError("Three-digit source selection hash differs")
    if old_stage.get("matrix_sha256") != modulo_three_hash:
        raise VerificationError("Three-digit matrix hash differs")

    expected_result = {
        "training_lines": len(rows),
        "columns": width,
        "selection_sha256": selection_hash,
        "integer_matrix_sha256": integer_hash,
        "prior_modulo_three_matrix_sha256": modulo_three_hash,
    }
    for field, expected in expected_result.items():
        if not same_json(track_result.get(field), expected):
            raise VerificationError(f"Study result field differs: {field}")

    certificate_name = track_result.get("certificate_file")
    if (
        not isinstance(certificate_name, str)
        or not certificate_name
        or "\\" in certificate_name
        or Path(certificate_name).name != certificate_name
    ):
        raise VerificationError("Certificate file name is invalid")
    certificate_path = result_dir / certificate_name
    if not certificate_path.is_file() or not certificate_path.resolve().is_relative_to(result_dir.resolve()):
        raise VerificationError("Certificate file is missing or outside the results directory")
    certificate_hash = file_sha256(certificate_path)
    if track_result.get("certificate_sha256") != certificate_hash:
        raise VerificationError("Certificate file hash differs from study result")
    certificate = json_value(certificate_path, "certificate")
    if not isinstance(certificate, dict):
        raise VerificationError("Certificate must be an object")

    expected_metadata = {
        "source": source,
        "source_sha256": source_hash,
        "L": label,
        "representation": representation,
        "alphabet": list(alphabet),
        "space_column": len(alphabet),
        "line_contribution_column": len(alphabet) + 1,
    }
    for field, expected in expected_metadata.items():
        if not same_json(certificate.get(field), expected):
            raise VerificationError(f"Certificate metadata differs: {field}")
    if track_result.get("support_rows") != len(certificate.get("support_indices", [])):
        raise VerificationError("Study result support row count differs")
    products = verify_certificate(rows, certificate, references)
    return {
        "source": source,
        "label": label,
        "representation": representation,
        "training_lines": len(rows),
        "columns": width,
        "support_rows": len(certificate["support_indices"]),
        "selection_sha256": selection_hash,
        "integer_matrix_sha256": integer_hash,
        "prior_modulo_three_matrix_sha256": modulo_three_hash,
        "certificate_path": f"{RESULTS_PATH}/{certificate_name}",
        "certificate_sha256": certificate_hash,
        "identity_products_checked": products,
        "checks": [
            "alphabet and nuisance-column order",
            "source-order integer matrix hash",
            "prior modulo-three unique matrix hash",
            "support indexes, rows, and source references",
            "direct integer multiplication B A = I",
        ],
    }


def verify_study(freeze_arg: str, results_arg: str, output_arg: str) -> dict[str, Any]:
    freeze_relative, freeze_path = _repo_arg(freeze_arg, "freeze")
    results_relative, results_dir = _repo_arg(results_arg, "results directory", directory=True)
    output_relative, output_path = _output_path(output_arg)
    if freeze_relative != FREEZE_PATH:
        raise VerificationError("Unexpected freeze path")
    if results_relative != RESULTS_PATH or not results_dir.is_dir():
        raise VerificationError("Unexpected or missing study results directory")
    if output_path.exists():
        raise VerificationError("Refusing to replace an existing output")

    freeze, frozen_hashes, source_hashes = _read_freeze(freeze_path)
    freeze_hash = file_sha256(freeze_path)
    baseline_path = _repo_path(BASELINE_PATH, "three-digit baseline")
    baseline = json_value(baseline_path, "three-digit baseline")
    if not isinstance(baseline, dict):
        raise VerificationError("Three-digit baseline is invalid")
    baseline_sources = _baseline_maps(baseline)
    result_path = results_dir / "result.json"
    result = json_value(result_path, "study result")
    if not isinstance(result, dict) or result.get("schema") != "line-phase-lattice-study-v1":
        raise VerificationError("Study result schema is invalid")
    result_hash = file_sha256(result_path)
    if result.get("freeze_sha256") != freeze_hash:
        raise VerificationError("Study result freeze hash differs")

    # Delay these imports until after the CLI checks and freeze validation.
    sys.path[:0] = [str(ROOT), str(ROOT / "src")]
    try:
        from experiments.homophonic.units import units
        from voynich.corpus import parse_ivtff
        from voynich.groups import group_id, split_bucket, split_name
    except ImportError as error:
        raise VerificationError("Required parser or unit dependency is unavailable") from error

    result_sources = _result_source_map(result)
    verified_sources = []
    verified_tracks = []
    for source, relative in SOURCES.items():
        source_path = _repo_path(relative, f"source {source}")
        pin_hash = source_hashes[source]["sha256"]
        baseline_source = baseline_sources[source]
        result_source = result_sources[source]
        if baseline_source.get("source_sha256") != pin_hash:
            raise VerificationError(f"Three-digit baseline source hash differs: {source}")
        if result_source.get("source_sha256") != pin_hash:
            raise VerificationError(f"Study result source hash differs: {source}")

        try:
            records = parse_ivtff(source_path, uncertain_spaces="split")
            selected, exclusions = select_records(
                records, (group_id, split_bucket, split_name)
            )
        except Exception as error:
            raise VerificationError(f"Independent source selection failed: {source}") from error
        if len(selected) != baseline_source.get("selected_lines"):
            raise VerificationError(f"Three-digit selected line count differs: {source}")
        if exclusions != baseline_source.get("exclusion_counts"):
            raise VerificationError(f"Three-digit exclusion counts differ: {source}")
        if result_source.get("selected_lines") != len(selected):
            raise VerificationError(f"Study selected line count differs: {source}")
        if not same_json(result_source.get("exclusion_counts"), exclusions):
            raise VerificationError(f"Study exclusion counts differ: {source}")

        previous_tracks = _baseline_track_map(baseline_source)
        output_tracks = _result_track_map(result_source)
        verified_sources.append(
            {
                "source": source,
                "source_path": relative,
                "source_sha256": pin_hash,
                "selected_lines": len(selected),
                "exclusion_counts": exclusions,
                "checks": [
                    "source hash",
                    "independent selected-line count",
                    "independent exclusion counts",
                    "baseline source identity",
                ],
            }
        )
        for label in LABELS:
            for representation in REPRESENTATIONS:
                track_key = f"{label}-{representation}"
                name = f"{source}-{track_key}"
                baseline_track = previous_tracks[track_key]
                output_track = output_tracks[track_key]
                training = [
                    item for item in selected
                    if item["L"] == label and item["split"] == "train"
                ]
                count_rows: list[list[int]] = []
                line_counters: list[Counter[str]] = []
                for item in training:
                    counter: Counter[str] = Counter()
                    for word in item["words"]:
                        counter.update(units(word, representation=representation))
                    line_counters.append(counter)
                alphabet = sorted({unit for counter in line_counters for unit in counter})
                references = [dict(item["reference"]) for item in training]
                for item, counter in zip(training, line_counters):
                    count_rows.append(
                        [counter.get(unit, 0) for unit in alphabet]
                        + [len(item["words"]) - 1, 1]
                    )
                verified = _validate_track_certificate(
                    source,
                    pin_hash,
                    label,
                    representation,
                    alphabet,
                    count_rows,
                    references,
                    output_track,
                    baseline_track,
                    results_dir,
                )
                verified["track"] = name
                verified_tracks.append(verified)

    receipt = {
        "schema": "line-phase-independent-verification-v1",
        "status": "verified",
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "setup": {
            "python_version": platform.python_version(),
            "method": "independent source selection, integer row reconstruction, and direct certificate multiplication",
            "command_template": COMMAND_TEMPLATE,
        },
        "input_hashes": {
            "freeze_sha256": freeze_hash,
            "result_sha256": result_hash,
            "baseline_sha256": file_sha256(baseline_path),
            "frozen_files": dict(sorted(frozen_hashes.items())),
            "sources": source_hashes,
        },
        "verified_sources": verified_sources,
        "verified_tracks": verified_tracks,
        "checks": [
            "freeze hashes match current code and manifests",
            "freeze and result source pins match the source manifest",
            "result freeze hash matches the frozen file",
            "exactly eight source, class, and representation tracks were checked",
            "all source-order integer row hashes and old reduced matrix hashes match",
            "all certificate hashes, support rows, indexes, and references match",
            "every direct integer product B A equals the identity",
        ],
        "limits": [
            "This receipt verifies a fixed source selection and its integer certificates.",
            "It does not validate glyph readings, physical line completeness, a historical code, or plaintext.",
        ],
    }
    if len(verified_tracks) != len(EXPECTED_TRACKS):
        raise VerificationError("Verified track count differs")
    _write_new_json(output_path, receipt)
    receipt_hash = file_sha256(output_path)
    sidecar = output_path.with_suffix(output_path.suffix + ".sha256")
    _write_new_text(sidecar, f"{receipt_hash}  {output_relative}\n")
    return receipt


def _synthetic_certificate(rows: list[list[int]], indexes: list[int], inverse: list[list[int]]) -> dict[str, Any]:
    return {
        "status": "certified",
        "original_input_row_count": len(rows),
        "columns": len(rows[0]),
        "support_indices": indexes,
        "support_rows": [list(rows[index]) for index in indexes],
        "left_inverse": inverse,
    }


def run_source_free_checks(output_arg: str) -> dict[str, Any]:
    output_relative, output_path = _output_path(output_arg)
    cases: list[tuple[str, list[list[int]], dict[str, Any], bool]] = [
        (
            "full_integer_lattice",
            [[1, 0], [0, 1]],
            _synthetic_certificate([[1, 0], [0, 1]], [0, 1], [[1, 0], [0, 1]]),
            True,
        ),
        (
            "proper_sublattice_false_proof",
            [[2, 0], [0, 1]],
            _synthetic_certificate([[2, 0], [0, 1]], [0, 1], [[0, 0], [0, 1]]),
            False,
        ),
        (
            "deficient_rank",
            [[1, 0], [0, 0]],
            _synthetic_certificate([[1, 0], [0, 0]], [0, 1], [[1, 0], [0, 1]]),
            False,
        ),
        (
            "negative_entries",
            [[-1, 0], [0, 1]],
            _synthetic_certificate([[-1, 0], [0, 1]], [0, 1], [[-1, 0], [0, 1]]),
            True,
        ),
    ]
    changed = _synthetic_certificate([[1, 0], [0, 1]], [0, 1], [[1, 0], [0, 1]])
    changed["left_inverse"][0][0] = 0
    cases.append(("changed_certificate", [[1, 0], [0, 1]], changed, False))

    results = []
    for name, rows, certificate, expected in cases:
        try:
            verify_certificate(rows, certificate)
            accepted = True
            outcome = "accepted"
            error_text = None
        except VerificationError as error:
            accepted = False
            outcome = "rejected"
            error_text = str(error)
        test_input = {"rows": rows, "certificate": certificate}
        passed = accepted is expected
        results.append(
            {
                "case": name,
                "expected": "accepted" if expected else "rejected",
                "actual": outcome,
                "passed": passed,
                "input_sha256": object_sha256(test_input),
                "error": error_text,
            }
        )

    receipt = {
        "schema": "line-phase-verifier-source-free-e2e-v1",
        "status": "passed" if all(case["passed"] for case in results) else "failed",
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "setup": {
            "command": f"python scripts/verify_line_phase_sources.py --self-check --output {output_relative}",
            "inputs": "synthetic integer matrices and certificates only",
            "manuscript_sources_read": False,
        },
        "cases": results,
    }
    _write_new_json(output_path, receipt)
    digest = file_sha256(output_path)
    _write_new_text(
        output_path.with_suffix(output_path.suffix + ".sha256"),
        f"{digest}  {output_relative}\n",
    )
    if receipt["status"] != "passed":
        raise VerificationError("One or more source-free certificate checks failed")
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--freeze", help="Frozen study manifest")
    parser.add_argument("--results", help="Study certificate directory")
    parser.add_argument("--output", required=True, help="New receipt path in the ignored evidence directory")
    parser.add_argument(
        "--self-check",
        action="store_true",
        help="Run synthetic certificate checks without opening manuscript sources",
    )
    args = parser.parse_args()
    try:
        if args.self_check:
            if args.freeze is not None or args.results is not None:
                raise VerificationError("Self-check does not accept source or result paths")
            receipt = run_source_free_checks(args.output)
        else:
            if args.freeze is None or args.results is None:
                raise VerificationError("Full verification requires --freeze and --results")
            receipt = verify_study(args.freeze, args.results, args.output)
    except VerificationError as error:
        print(f"verification failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps({"status": receipt["status"], "output": args.output}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
