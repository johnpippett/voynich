#!/usr/bin/env python3
"""Audit frozen local-cyclic certificate arithmetic independently."""

from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "vms-local-cyclic-v1-independent-audit.json"
FREEZE = "experiments/local_cyclic/freeze-v1.json"
FREEZE_BYTES = 2812
FREEZE_SHA256 = "6514e43c78bccd5c6b26b8f68aaa973beb6181926d4135d8553c9d6501c0d79a"
OUTPUT_PINS = {
    "results/vms-local-cyclic-falsification-v1/ZL3b-n-raw_eva.json": (1975586, "2af91ca875012d417eb053dfeb2184eb9ac11ee3d035f7f203b397c2a3718365"),
    "results/vms-local-cyclic-falsification-v1/ZL3b-n-visual_six.json": (2391469, "02ed1bec32df7f2de2cac8c5dd506682e8730deb436cd89575d2fa8a1545f091"),
    "results/vms-local-cyclic-falsification-v1/IT2a-n-raw_eva.json": (2252106, "9d9b81693e42ad1583aee2b4aa36666c14808fc7aecf0464623f0358376cdfcf"),
    "results/vms-local-cyclic-falsification-v1/IT2a-n-visual_six.json": (2708314, "2c965e16c4c5d87d33e6b13785be8558ebd6f8f2baea0586a36b7a7763a1bc2a"),
}
SOURCES = {"ZL3b-n": "data/raw/ZL3b-n.txt", "IT2a-n": "data/raw/IT2a-n.txt"}
COMPOUNDS = tuple(sorted(("ch", "sh", "cth", "ckh", "cph", "cfh"), key=lambda item: (-len(item), item)))


class AuditError(RuntimeError):
    """A pinned input or derived result failed an audit check."""


def need(condition: bool, message: str) -> None:
    if not condition:
        raise AuditError(message)


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def canonical(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def canonical_hash(value: Any) -> str:
    return sha256(canonical(value))


def read_pinned(relative: str, size: int, expected: str) -> bytes:
    path = ROOT / relative
    need(not path.is_symlink() and path.is_file(), f"missing pinned file: {relative}")
    raw = path.read_bytes()
    need(len(raw) == size and sha256(raw) == expected, f"pinned hash mismatch: {relative}")
    return raw


def parse_object(raw: bytes, name: str) -> dict[str, Any]:
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise AuditError(f"invalid JSON: {name}") from error
    need(isinstance(value, dict), f"JSON object required: {name}")
    return value


def pin_all() -> tuple[dict[str, Any], dict[str, bytes], dict[str, str]]:
    freeze_raw = read_pinned(FREEZE, FREEZE_BYTES, FREEZE_SHA256)
    freeze = parse_object(freeze_raw, "freeze")
    entries = freeze.get("files")
    need(isinstance(entries, list) and len(entries) == 13, "freeze file count is not 13")
    pinned = {FREEZE: freeze_raw}
    hashes: dict[str, str] = {}
    for entry in entries:
        need(isinstance(entry, dict), "freeze entry is invalid")
        relative, expected = entry.get("path"), entry.get("sha256")
        need(isinstance(relative, str) and relative and not Path(relative).is_absolute(), "freeze path is invalid")
        need(relative not in hashes and isinstance(expected, str) and len(expected) == 64, "freeze digest is invalid")
        raw = read_pinned(relative, (ROOT / relative).stat().st_size, expected)
        pinned[relative], hashes[relative] = raw, expected
    for relative, (size, expected) in OUTPUT_PINS.items():
        pinned[relative] = read_pinned(relative, size, expected)
    return freeze, pinned, hashes


def unitize(surface: str, visual: bool) -> list[tuple[str, str, int, int]]:
    units: list[tuple[str, str, int, int]] = []
    cursor = 0
    while cursor < len(surface):
        value = next((item for item in COMPOUNDS if visual and surface.startswith(item, cursor)), surface[cursor])
        end = cursor + len(value)
        units.append((value, surface[cursor:end], cursor, end))
        cursor = end
    need("".join(item[1] for item in units) == surface, "unit spans do not reconstruct source word")
    return units


def audit_track(source_id: str, source_file: str, records: list[dict[str, Any]], extracted: list[Any], visual: bool) -> dict[str, Any]:
    counts = {"record_count": len(records), "eligible_word_count": 0, "eligible_unit_count": 0, "adjacent_pair_count": 0, "certificate_count": 0, "affected_word_count": 0}
    excluded: Counter[str] = Counter()
    locations: list[dict[str, Any]] = []
    for record_index, (record, extraction) in enumerate(zip(records, extracted, strict=True)):
        for reason, value in extraction.excluded_counts:
            excluded[reason] += value
        affected: set[int] = set()
        for word in extraction.eligible:
            source_slice = record["text_raw"][word.source_start:word.source_end]
            need(source_slice == word.surface, "eligible span does not roundtrip source text")
            units = unitize(word.surface, visual)
            counts["eligible_word_count"] += 1
            counts["eligible_unit_count"] += len(units)
            counts["adjacent_pair_count"] += max(0, len(units) - 1)
            for unit_index, left_right in enumerate(zip(units, units[1:])):
                left, right = left_right
                if left[0] != right[0]:
                    continue
                affected.add(word.word_index)
                location = {"source_file": source_file, "record_index": record_index, "folio": record.get("folio"), "locus": record.get("locus"), "transcriber": record.get("transcriber"), "candidate_word_index": word.word_index, "unit_index": unit_index, "unit": left[0]}
                if visual:
                    location["unit_span"] = [left[2], left[3]]
                locations.append(location)
        counts["affected_word_count"] += len(affected)
    counts["certificate_count"] = len(locations)
    status = "inconclusive_no_eligible_words" if not counts["eligible_word_count"] else "falsified_for_fixed_track" if counts["certificate_count"] else "not_falsified_by_local_check"
    return {"counts": counts, "excluded": dict(sorted(excluded.items())), "locations": locations, "status": status}


def expected_record(source_id: str, source_file: str, result: dict[str, Any], visual: bool, freeze_hash: str, input_hashes: dict[str, str], output_file: str) -> dict[str, Any]:
    representation = "visual" if visual else "raw"
    counts = result["counts"]
    return {
        "schema_version": 1, "protocol": "vms-local-cyclic-falsification-v1", "source_id": source_id, "source_file": source_file,
        "unitization": "visual_six" if visual else "raw_eva", "representation": representation, "uncertain_spaces": "split",
        "model_contract": "fixed cyclic emitter with disjoint preimage sets of k>=2 units, one distinct next unit per repeated symbol, and reset at each word",
        "counts": counts, "excluded_word_counts": result["excluded"], "source_file_counts": {source_file: {**counts, "excluded_word_counts": result["excluded"]}},
        "status": result["status"], "certificate_locations": result["locations"], "image_review": "not_performed",
        "output_file": output_file, "unitization_version": "basic-eva-visual-six-v1", "freeze_manifest_sha256": freeze_hash, "input_hashes": input_hashes,
    }


def write_identical(raw: bytes) -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    try:
        with OUT.open("xb") as handle:
            handle.write(raw)
    except FileExistsError:
        need(OUT.read_bytes() == raw, "audit output exists with different bytes")


def main() -> int:
    try:
        freeze, pinned, input_hashes = pin_all()
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        if str(ROOT / "src") not in sys.path:
            sys.path.insert(0, str(ROOT / "src"))
        from experiments.local_cyclic.certificate import extract_word_spans
        from voynich.corpus import parse_ivtff

        source_reports: dict[str, dict[str, Any]] = {}
        aggregate: dict[str, Any] = {}
        for source_id, source_file in SOURCES.items():
            records = parse_ivtff(ROOT / source_file, uncertain_spaces="split")
            extracted = [extract_word_spans(record["text_raw"]) for record in records]
            for track_name, visual in (("raw_eva", False), ("visual_six", True)):
                result = audit_track(source_id, source_file, records, extracted, visual)
                output_file = f"results/vms-local-cyclic-falsification-v1/{source_id}-{track_name}.json"
                report = parse_object(pinned[output_file], output_file)
                expected = expected_record(source_id, source_file, result, visual, sha256(pinned[FREEZE]), input_hashes, output_file)
                for field, value in expected.items():
                    need(report.get(field) == value, f"{output_file} mismatch: {field}")
                source_reports[f"{source_id}/{track_name}"] = {"artifact_bytes": len(pinned[output_file]), "artifact_sha256": sha256(pinned[output_file]), "source_id": source_id, "unitization": track_name, "counts": result["counts"], "excluded_word_counts": result["excluded"], "status": result["status"], "certificate_location_count": len(result["locations"]), "certificate_locations_sha256": canonical_hash(result["locations"])}
        aggregate = {
            "schema_version": 1, "verification": "vms-local-cyclic-falsification-independent-audit", "status": "PASS",
            "shared_eligibility": "Eligibility uses the frozen IVTFF parser and strict extract_word_spans. Unitization and adjacency arithmetic are independent.",
            "inputs": {"freeze": {"bytes": FREEZE_BYTES, "sha256": FREEZE_SHA256}, "frozen_file_count": len(input_hashes), "frozen_file_hashes_verified": True, "source_hashes": {source_id: input_hashes[source_file] for source_id, source_file in SOURCES.items()}, "output_hashes": {path: {"bytes": size, "sha256": expected} for path, (size, expected) in OUTPUT_PINS.items()}},
            "records": source_reports,
            "checks": {"freeze_pins": True, "source_identity": True, "all_ordered_locations": True, "eligible_span_roundtrip": True, "independent_longest_match": True, "adjacency_is_word_local": True, "counts_exclusions_status": True, "output_hash_pins": True},
            "limitations": ["This is an independent arithmetic audit, not an independent eligibility audit.", "It uses no source data outside the frozen files.", "The result tests only the declared local certificate and two fixed unitizations."],
        }
        write_identical((json.dumps(aggregate, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8"))
        print("Local cyclic audit: PASS")
        print(f"audit_sha256={sha256(OUT.read_bytes())}")
        return 0
    except AuditError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
