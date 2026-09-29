#!/usr/bin/env python3
"""Run source-free end-to-end checks for the line-phase lattice command."""

from __future__ import annotations

import hashlib
import json
import platform
import re
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_DIR = ROOT / "results" / "line-phase-lattice-e2e-v1"
CLI = ROOT / "scripts" / "line_phase_lattice.py"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str | None:
    try:
        return sha256_bytes(path.read_bytes())
    except FileNotFoundError:
        return None


def write_exclusive(path: Path, contents: str) -> None:
    with path.open("x", encoding="utf-8") as handle:
        handle.write(contents)


def write_run_receipt(prefix: str, contents: str) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    for suffix in range(1000):
        tail = "" if suffix == 0 else f"-{suffix:03d}"
        path = ARTIFACT_DIR / f"{prefix}-{stamp}{tail}.json"
        try:
            write_exclusive(path, contents)
            return path
        except FileExistsError:
            continue
    raise RuntimeError("could not create a unique E2E receipt")


def run_command(args: list[str], cwd: Path) -> dict[str, Any]:
    start = time.monotonic()
    try:
        completed = subprocess.run(
            args,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
            timeout=610,
        )
        returncode = completed.returncode
        stdout = _sanitize_text(completed.stdout)
        stderr = _sanitize_text(completed.stderr)
        timed_out = False
    except subprocess.TimeoutExpired as exc:
        returncode = 124
        stdout = _sanitize_text(_decode_output(exc.stdout))
        stderr = _sanitize_text(_decode_output(exc.stderr))
        timed_out = True
    command_parts = ["python" if args[0] == sys.executable else args[0]]
    for part in args[1:]:
        if part == str(CLI):
            command_parts.append("scripts/line_phase_lattice.py")
        elif Path(part).is_absolute():
            command_parts.append(f"<temporary>/{Path(part).name}")
        else:
            command_parts.append(part)
    return {
        "command": command_parts,
        "returncode": returncode,
        "stdout": stdout,
        "stderr": stderr,
        "stdout_sha256": sha256_bytes(stdout.encode("utf-8")),
        "stderr_sha256": sha256_bytes(stderr.encode("utf-8")),
        "timed_out": timed_out,
        "elapsed_seconds": round(time.monotonic() - start, 6),
    }


def _decode_output(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def _sanitize_text(value: str) -> str:
    value = value.replace(str(CLI), "scripts/line_phase_lattice.py")
    value = value.replace(str(ROOT) + "/", "<workspace>/")
    return re.sub(
        r"[/\\]tmp[/\\]line-phase-lattice-e2e-[^/\\\s']+[/\\]",
        "<temporary>/",
        value,
    )


def run_e2e() -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    all_passed = True

    def record(name: str, passed: bool, expected: Any, actual: Any) -> None:
        nonlocal all_passed
        all_passed = all_passed and passed
        checks.append(
            {
                "name": name,
                "passed": passed,
                "expected": expected,
                "actual": actual,
            }
        )

    with tempfile.TemporaryDirectory(prefix="line-phase-lattice-e2e-") as temp_name:
        temp_dir = Path(temp_name)

        def write_input(name: str, data: bytes) -> tuple[Path, Path]:
            input_path = temp_dir / f"{name}.input.json"
            output_path = temp_dir / f"{name}.certificate.json"
            input_path.write_bytes(data)
            return input_path, output_path

        def build_case(
            name: str,
            rows: list[list[int]],
            expected_status: str,
            *,
            expect_pivots: list[int] | None = None,
        ) -> dict[str, Any] | None:
            payload = json.dumps({"rows": rows}, separators=(",", ":")).encode(
                "utf-8"
            )
            input_path, output_path = write_input(name, payload)
            cmd = [sys.executable, str(CLI), "build", str(input_path), str(output_path)]
            result = run_command(cmd, ROOT)
            output_hash = sha256_file(output_path)
            expected = {
                "returncode": 0,
                "status": expected_status,
                "pivots": expect_pivots,
                "output_exists": True,
            }
            actual: dict[str, Any] = {
                **result,
                "input_sha256": sha256_bytes(payload),
                "output_sha256": output_hash,
                "output_exists": output_path.exists(),
            }
            valid = (
                CLI.is_file()
                and result["returncode"] == 0
                and result["stdout"] == f"built: {expected_status}\n"
                and output_path.exists()
            )
            certificate = None
            if valid:
                try:
                    certificate = json.loads(output_path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError) as exc:
                    valid = False
                    actual["certificate_error"] = str(exc)
            if valid:
                actual["status"] = certificate.get("status")
                actual["pivots"] = certificate.get("pivots")
                valid = actual["status"] == expected_status
                if expect_pivots is not None:
                    valid = valid and actual["pivots"] == expect_pivots
            record(name, valid, expected, actual)
            return certificate if isinstance(certificate, dict) else None

        def verify_case(
            name: str,
            certificate: dict[str, Any],
            should_pass: bool,
        ) -> None:
            proof_path = temp_dir / f"{name}.proof.json"
            proof_bytes = (
                json.dumps(certificate, separators=(",", ":")) + "\n"
            ).encode("utf-8")
            proof_path.write_bytes(proof_bytes)
            result = run_command(
                [sys.executable, str(CLI), "verify", str(proof_path)], ROOT
            )
            if should_pass:
                passed = (
                    CLI.is_file()
                    and result["returncode"] == 0
                    and result["stdout"] == "verified\n"
                )
            else:
                passed = (
                    CLI.is_file()
                    and result["returncode"] == 2
                    and result["stderr"].startswith("error:")
                )
            record(
                name,
                passed,
                {"verify_accepts": should_pass},
                {
                    **result,
                    "proof_sha256": sha256_bytes(proof_bytes),
                },
            )

        coprime = build_case("coprime_rows", [[2], [3]], "certified", expect_pivots=[1])
        if coprime is not None:
            verify_case("verify_coprime_rows", coprime, True)

        unimodular = build_case(
            "unimodular_matrix",
            [[2, 1], [1, 1]],
            "certified",
            expect_pivots=[1, 1],
        )
        if unimodular is not None:
            verify_case("verify_unimodular_matrix", unimodular, True)

        no_unit_minor = build_case(
            "full_lattice_without_unit_minor",
            [[2, 0], [0, 3], [1, 1]],
            "certified",
            expect_pivots=[1, 1],
        )
        if no_unit_minor is not None:
            verify_case("verify_full_lattice_without_unit_minor", no_unit_minor, True)

        proper = build_case(
            "proper_sublattice", [[2]], "not_certified", expect_pivots=[2]
        )
        if proper is not None:
            verify_case("verify_proper_sublattice", proper, False)

        proper_mod_three = build_case(
            "proper_sublattice_full_rank_mod_three",
            [[2, 0], [0, 2], [1, 1]],
            "not_certified",
            expect_pivots=[1, 2],
        )
        if proper_mod_three is not None:
            verify_case(
                "verify_proper_sublattice_full_rank_mod_three", proper_mod_three, False
            )

        deficient = build_case(
            "rank_deficient", [[1, 2], [2, 4]], "not_certified", expect_pivots=[1]
        )
        if deficient is not None:
            verify_case("verify_rank_deficient", deficient, False)

        negative = build_case("negative_entries", [[-2], [3]], "certified", expect_pivots=[1])
        if negative is not None:
            verify_case("verify_negative_entries", negative, True)

        limit_rows = [[1 << 4096]]
        limit_cert = build_case(
            "bit_limit", limit_rows, "not_certified", expect_pivots=[]
        )
        if limit_cert is not None:
            has_reason = isinstance(limit_cert.get("reason"), str) and bool(
                limit_cert["reason"]
            )
            record(
                "bit_limit_reason",
                has_reason,
                {"noncertified_reason_present": True},
                {"reason": limit_cert.get("reason")},
            )

        large_n = 1 << 2048
        builder_product_limit = build_case(
            "builder_product_limit",
            [[large_n, large_n - 1], [large_n + 1, large_n]],
            "not_certified",
            expect_pivots=[1, 1],
        )
        if builder_product_limit is not None:
            has_product_limit_reason = "4,096-bit" in str(
                builder_product_limit.get("reason", "")
            )
            record(
                "builder_product_limit_reason",
                has_product_limit_reason,
                {"noncertified_bit_limit_reason": True},
                {"reason": builder_product_limit.get("reason")},
            )
            verify_case(
                "verify_builder_product_limit",
                builder_product_limit,
                False,
            )

        malformed_payloads = {
            "malformed_json": b"{broken\n",
            "empty_rows": b'{"rows":[]}',
            "ragged_rows": b'{"rows":[[1],[1,2]]}',
            "boolean_entry": b'{"rows":[[true]]}',
            "float_entry": b'{"rows":[[1.0]]}',
        }
        for name, payload in malformed_payloads.items():
            input_path, output_path = write_input(name, payload)
            result = run_command(
                [sys.executable, str(CLI), "build", str(input_path), str(output_path)],
                ROOT,
            )
            passed = (
                CLI.is_file()
                and result["returncode"] == 2
                and result["stderr"].startswith("error:")
                and not output_path.exists()
            )
            record(
                name,
                passed,
                {"returncode_nonzero": True, "output_exists": False},
                {
                    **result,
                    "input_sha256": sha256_bytes(payload),
                    "output_exists": output_path.exists(),
                },
            )

        known_proof = {
            "status": "certified",
            "original_input_row_count": 2,
            "columns": 1,
            "support_indices": [0, 1],
            "support_rows": [[2], [3]],
            "left_inverse": [[-1, 1]],
            "pivots": [1],
        }
        verify_case("verify_hand_checked_proof", known_proof, True)
        large_k = 1 << 2048
        large_t = 1 << 2047
        large_product_proof = {
            "status": "certified",
            "original_input_row_count": 2,
            "columns": 1,
            "support_indices": [0, 1],
            "support_rows": [[large_k], [large_k - 1]],
            "left_inverse": [[
                1 + large_t * (large_k - 1),
                -1 - large_t * large_k,
            ]],
            "pivots": [1],
        }
        verify_case("verify_bounded_products", large_product_proof, False)
        changed_proof = json.loads(json.dumps(known_proof))
        changed_proof["left_inverse"][0][1] = 2
        verify_case("verify_tampered_proof", changed_proof, False)

        existing_input, existing_output = write_input(
            "existing_output", b'{"rows":[[1]]}'
        )
        existing_output.write_text("keep-this-file\n", encoding="utf-8")
        old_hash = sha256_file(existing_output)
        result = run_command(
            [
                sys.executable,
                str(CLI),
                "build",
                str(existing_input),
                str(existing_output),
            ],
            ROOT,
        )
        new_hash = sha256_file(existing_output)
        record(
            "exclusive_output",
            CLI.is_file()
            and result["returncode"] == 2
            and result["stderr"].startswith("error:")
            and old_hash == new_hash,
            {"returncode_nonzero": True, "output_unchanged": True},
            {
                **result,
                "before_sha256": old_hash,
                "after_sha256": new_hash,
            },
        )

    code_hashes = {
        "scripts/line_phase_lattice.py": sha256_file(CLI),
        "scripts/check_line_phase_lattice.py": sha256_file(Path(__file__)),
        "results/line-phase-lattice-e2e-v1/failure-modes.md": sha256_file(
            ARTIFACT_DIR / "failure-modes.md"
        ),
    }
    receipt: dict[str, Any] = {
        "format": "line-phase-lattice-e2e-v1",
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "passed": all_passed,
        "setup": {
            "command": "python scripts/check_line_phase_lattice.py",
            "runtime": platform.python_version(),
            "dependencies": "Python standard library only",
            "source_data_used": False,
            "tie_rule": "lowest active row slot breaks equal-absolute-pivot ties",
            "resource_limits": {
                "integer_bits": 4096,
                "seconds_per_build": 600,
            },
        },
        "checks": checks,
        "code_sha256": code_hashes,
    }
    return receipt


def main() -> int:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    receipt = run_e2e()
    serialized = json.dumps(receipt, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
    if receipt["passed"]:
        initial = ARTIFACT_DIR / "initial-failure.json"
        receipt["initial_failure_sha256"] = sha256_file(initial)
        serialized = json.dumps(receipt, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
        destination = write_run_receipt("passed-run", serialized)
        print(f"PASS: {len(receipt['checks'])} checks")
        print(f"RECEIPT: {destination.relative_to(ROOT)}")
        return 0

    initial = ARTIFACT_DIR / "initial-failure.json"
    if not initial.exists():
        try:
            write_exclusive(initial, serialized)
            destination = initial
        except FileExistsError:
            destination = write_run_receipt("failed-run", serialized)
    else:
        destination = write_run_receipt("failed-run", serialized)
    failed = [item["name"] for item in receipt["checks"] if not item["passed"]]
    print(f"FAIL: {len(failed)} of {len(receipt['checks'])} checks: {', '.join(failed)}")
    print(f"RECEIPT: {destination.relative_to(ROOT)}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
