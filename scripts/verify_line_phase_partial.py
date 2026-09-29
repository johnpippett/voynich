#!/usr/bin/env python3
"""Verify all frozen line-phase matrices and report partial proof coverage."""

from __future__ import annotations

from datetime import datetime, timezone
import argparse
import hashlib
import json
from pathlib import Path
import platform
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
FROZEN_VERIFIER_SHA256 = "50b400580c1f190b03aa09201a0404da459a8efdd997dac1d12ade9c9c486efc"
RESOURCE_STOPS = {"IT-B-raw", "ZL-B-raw", "ZL-B-visual"}
RESOURCE_REASON = "an intermediate integer exceeded the 4,096-bit limit"
COMMAND = (
    "python scripts/verify_line_phase_partial.py --freeze "
    "experiments/line_phase/freeze-v1.json --results "
    "reports/line-phase-lattice-v1 --output "
    "results/line-phase-lattice-verification-v1/partial-receipt.json"
)


class PartialVerificationError(RuntimeError):
    pass


def verify(freeze_arg: str, results_arg: str, output_arg: str) -> dict[str, Any]:
    sys.path[:0] = [str(ROOT / "scripts"), str(ROOT), str(ROOT / "src")]
    import verify_line_phase_sources as checks
    from experiments.homophonic.units import units
    from voynich.corpus import parse_ivtff
    from voynich.groups import group_id, split_bucket, split_name

    if checks.file_sha256(ROOT / "scripts/verify_line_phase_sources.py") != FROZEN_VERIFIER_SHA256:
        raise PartialVerificationError("Frozen independent verifier hash differs")
    freeze_rel, freeze_path = checks._repo_arg(freeze_arg, "freeze")
    results_rel, results_dir = checks._repo_arg(results_arg, "results", directory=True)
    output_rel, output_path = checks._output_path(output_arg)
    if freeze_rel != checks.FREEZE_PATH or results_rel != checks.RESULTS_PATH:
        raise PartialVerificationError("Unexpected freeze or results path")
    if output_path.exists():
        raise PartialVerificationError("Refusing to replace an existing receipt")

    _, frozen_hashes, source_pins = checks._read_freeze(freeze_path)
    freeze_hash = checks.file_sha256(freeze_path)
    baseline_path = checks._repo_path(checks.BASELINE_PATH, "baseline")
    baseline = checks.json_value(baseline_path, "baseline")
    result_path = results_dir / "result.json"
    result = checks.json_value(result_path, "study result")
    if not isinstance(result, dict) or result.get("schema") != "line-phase-lattice-study-v1":
        raise PartialVerificationError("Study result schema differs")
    if result.get("freeze_sha256") != freeze_hash:
        raise PartialVerificationError("Study result freeze hash differs")
    baseline_sources = checks._baseline_maps(baseline)
    result_sources = checks._result_source_map(result)
    sources_out: list[dict[str, Any]] = []
    tracks_out: list[dict[str, Any]] = []

    for source, relative in checks.SOURCES.items():
        source_path = checks._repo_path(relative, f"source {source}")
        source_hash = source_pins[source]["sha256"]
        baseline_source, result_source = baseline_sources[source], result_sources[source]
        if source_hash != baseline_source.get("source_sha256") or source_hash != result_source.get("source_sha256"):
            raise PartialVerificationError(f"Source hash differs: {source}")
        records = parse_ivtff(source_path, uncertain_spaces="split")
        selected, exclusions = checks.select_records(
            records, (group_id, split_bucket, split_name)
        )
        if len(selected) != baseline_source.get("selected_lines") or len(selected) != result_source.get("selected_lines"):
            raise PartialVerificationError(f"Selected source-line count differs: {source}")
        if exclusions != baseline_source.get("exclusion_counts") or exclusions != result_source.get("exclusion_counts"):
            raise PartialVerificationError(f"Source exclusions differ: {source}")
        old_tracks = checks._baseline_track_map(baseline_source)
        new_tracks = checks._result_track_map(result_source)
        sources_out.append({"source": source, "path": relative, "sha256": source_hash,
                            "selected_lines": len(selected), "exclusion_counts": exclusions})

        for label in checks.LABELS:
            for representation in checks.REPRESENTATIONS:
                name = f"{source}-{label}-{representation}"
                training = [x for x in selected if x["L"] == label and x["split"] == "train"]
                counters = []
                for item in training:
                    counts = {}
                    for word in item["words"]:
                        for unit in units(word, representation=representation):
                            counts[unit] = counts.get(unit, 0) + 1
                    counters.append(counts)
                alphabet = sorted({unit for counts in counters for unit in counts})
                references = [dict(item["reference"]) for item in training]
                rows = [[counts.get(unit, 0) for unit in alphabet]
                        + [len(item["words"]) - 1, 1]
                        for item, counts in zip(training, counters)]
                selection_hash = checks.object_sha256(references)
                integer_hash = checks.object_sha256(rows)
                reduced = sorted({tuple(value % 3 for value in row) for row in rows})
                modulo_hash = checks.object_sha256(reduced)
                width = len(alphabet) + 2
                old, track = old_tracks[f"{label}-{representation}"], new_tracks[f"{label}-{representation}"]
                old_train = old.get("stages", {}).get("train", {})
                expected = {"training_lines": len(rows), "columns": width,
                            "selection_sha256": selection_hash, "integer_matrix_sha256": integer_hash,
                            "prior_modulo_three_matrix_sha256": modulo_hash}
                if (old_train.get("selected_lines") != len(rows)
                    or old_train.get("selection_sha256") != selection_hash
                    or old_train.get("matrix_sha256") != modulo_hash
                    or track.get("alphabet") != alphabet):
                    raise PartialVerificationError(f"Baseline selection or modulo-three matrix differs: {name}")
                for field, value in expected.items():
                    if track.get(field) != value:
                        raise PartialVerificationError(f"Study result differs for {field}: {name}")
                cert_name = track.get("certificate_file")
                if not isinstance(cert_name, str) or Path(cert_name).name != cert_name:
                    raise PartialVerificationError(f"Certificate name is invalid: {name}")
                cert_path = results_dir / cert_name
                if not cert_path.is_file() or not cert_path.resolve().is_relative_to(results_dir.resolve()):
                    raise PartialVerificationError(f"Certificate is missing: {name}")
                cert_hash = checks.file_sha256(cert_path)
                if track.get("certificate_sha256") != cert_hash:
                    raise PartialVerificationError(f"Certificate hash differs: {name}")
                cert = checks.json_value(cert_path, "certificate")
                metadata = {"source": source, "source_sha256": source_hash, "L": label,
                            "representation": representation, "alphabet": alphabet,
                            "columns": width, "space_column": len(alphabet),
                            "line_contribution_column": len(alphabet) + 1,
                            "original_input_row_count": len(rows)}
                if any(cert.get(key) != value for key, value in metadata.items()):
                    raise PartialVerificationError(f"Certificate metadata differs: {name}")

                if name in RESOURCE_STOPS:
                    if (track.get("status") != "not_certified" or cert.get("status") != "not_certified"
                        or cert.get("reason") != RESOURCE_REASON or cert.get("support_indices") != []
                        or track.get("support_rows") != 0):
                        raise PartialVerificationError(f"Resource-stop record differs: {name}")
                    tracks_out.append({"track": name, **expected, "status": "inconclusive_resource_stop",
                                       "reason": RESOURCE_REASON, "certificate_sha256": cert_hash,
                                       "support_rows": 0,
                                       "checks": ["source selection", "integer matrix hash",
                                                  "prior modulo-three hash", "stop metadata and certificate hash"]})
                else:
                    if track.get("status") != "certified":
                        raise PartialVerificationError(f"Unexpected non-certified track: {name}")
                    proof = checks._validate_track_certificate(
                        source, source_hash, label, representation, alphabet, rows, references,
                        track, old, results_dir,
                    )
                    tracks_out.append({"track": name, "status": "certified_integer_left_inverse",
                                       "certificate_sha256": cert_hash, "support_rows": proof["support_rows"],
                                       "identity_products_checked": proof["identity_products_checked"],
                                       "selection_sha256": selection_hash,
                                       "integer_matrix_sha256": integer_hash,
                                       "prior_modulo_three_matrix_sha256": modulo_hash,
                                       "checks": proof["checks"]})

    if {x["track"] for x in tracks_out} != checks.EXPECTED_TRACKS:
        raise PartialVerificationError("The verifier did not cover exactly eight tracks")
    if sum(x["status"] == "certified_integer_left_inverse" for x in tracks_out) != 5:
        raise PartialVerificationError("Expected exactly five verified integer proofs")
    if sum(x["status"] == "inconclusive_resource_stop" for x in tracks_out) != 3:
        raise PartialVerificationError("Expected exactly three inconclusive resource stops")

    receipt = {
        "schema": "line-phase-partial-independent-verification-v1", "status": "verified_partial",
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "setup": {"python_version": platform.python_version(), "command_template": COMMAND,
                  "method": "independent source reconstruction via frozen verifier helpers; direct integer certificate products",
                  "frozen_verifier_sha256": FROZEN_VERIFIER_SHA256,
                  "partial_driver_sha256": checks.file_sha256(Path(__file__))},
        "input_hashes": {"freeze_sha256": freeze_hash,
                         "result_sha256": checks.file_sha256(result_path),
                         "baseline_sha256": checks.file_sha256(baseline_path),
                         "frozen_files": dict(sorted(frozen_hashes.items())), "sources": source_pins},
        "coverage": {"matrices_verified": 8, "integer_proofs_verified": 5,
                     "resource_stops_inconclusive": 3},
        "verified_sources": sources_out, "verified_tracks": tracks_out,
        "limits": ["Resource stops give no integer-lattice conclusion.",
                   "The receipt does not establish glyph readings, a historical code, or plaintext."],
    }
    checks._write_new_json(output_path, receipt)
    digest = checks.file_sha256(output_path)
    checks._write_new_text(output_path.with_suffix(output_path.suffix + ".sha256"),
                           f"{digest}  {output_rel}\n")
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--freeze", required=True, help="Frozen study manifest")
    parser.add_argument("--results", required=True, help="Study result and certificate directory")
    parser.add_argument("--output", required=True, help="New receipt path in the ignored evidence directory")
    args = parser.parse_args()
    try:
        receipt = verify(args.freeze, args.results, args.output)
    except Exception as error:
        print(f"partial verification failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps({"status": receipt["status"], "output": args.output}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
