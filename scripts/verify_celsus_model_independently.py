#!/usr/bin/env python3
"""Verify the frozen Celsus model control with independent stdlib code."""

from collections import Counter
import hashlib
import json
from pathlib import Path
import string
import sys
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "celsus-model-control-v1-independent-audit.json"
FREEZE = "experiments/medical/control-freeze-v1.json"
FREEZE_BYTES = 7827
FREEZE_SHA256 = "63c862d19c6891d43257b36f2e0f15c88529d0929b1087022fc46260c1bc371f"
PARTITIONS = "results/celsus-reference-control-v1/partitions.private.json"
MANIFEST = "results/celsus-reference-control-v1/partition-manifest.json"
OUTPUT_PINS = {
    "results/celsus-reference-control-v1/model/cold.json": (
        12110,
        "62799634681c71cbe3c7c78ebfa4b2a47d3c77c82eb02f6d9553a1f251ab405d",
    ),
    "results/celsus-reference-control-v1/model/cold.keys.json": (
        725,
        "f3d291b907a5241dcc6ee350212bc3e1f0a25ba9cba9560bb167a5cdde022c4c",
    ),
    "results/celsus-reference-control-v1/model/supervision.json": (
        2019,
        "1a18b2a782794fe04402d21da0a4fa3d0493f64721be911f771aba5776ede6c2",
    ),
}
PARTITION_PINS = {
    PARTITIONS: (
        870217,
        "ca6209869b934958c04b9707c0c70652046abb118d365c9c9f272c6adb7802f1",
    ),
    MANIFEST: (
        8843,
        "634ed31c54e1147ee930c6261ed9261938ec120f310db2e22ed54bca630dc9e1",
    ),
}
ALPHABET = tuple(string.ascii_lowercase)
SPLITS = ("train", "validation", "test")


class AuditError(RuntimeError):
    """A fixed input or derived result failed an audit check."""


def need(condition: bool, message: str) -> None:
    if not condition:
        raise AuditError(message)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


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


def pin_all_inputs() -> tuple[dict[str, Any], dict[str, bytes]]:
    freeze_raw = read_pinned(FREEZE, FREEZE_BYTES, FREEZE_SHA256)
    try:
        freeze = json.loads(freeze_raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise AuditError("control freeze is not valid JSON") from error
    need(isinstance(freeze, dict), "control freeze is not an object")
    entries = freeze.get("files")
    need(isinstance(entries, list) and len(entries) == 43, "freeze file count is not 43")
    pinned: dict[str, bytes] = {FREEZE: freeze_raw}
    seen: set[str] = set()
    for entry in entries:
        need(isinstance(entry, dict), "freeze entry is not an object")
        relative, expected = entry.get("path"), entry.get("sha256")
        need(isinstance(relative, str) and relative and not Path(relative).is_absolute(), "freeze path is invalid")
        need(relative not in seen, "freeze contains a duplicate path")
        need(isinstance(expected, str) and len(expected) == 64, "freeze hash is invalid")
        seen.add(relative)
        path = ROOT / relative
        need(not path.is_symlink() and path.is_file(), f"missing frozen file: {relative}")
        raw = path.read_bytes()
        need(sha256(raw) == expected, f"frozen hash mismatch: {relative}")
        pinned[relative] = raw
    need(PARTITIONS in seen and MANIFEST in seen, "partition files are outside the freeze")
    for relative, (size, expected) in {**PARTITION_PINS, **OUTPUT_PINS}.items():
        raw = read_pinned(relative, size, expected)
        pinned[relative] = raw
    return freeze, pinned


def encrypt(words: list[str], planted: Mapping[str, Any]) -> list[tuple[str, ...]]:
    offsets = {letter: 0 for letter in ALPHABET}
    cycles = planted["emission_order"]
    encrypted: list[tuple[str, ...]] = []
    for word in words:
        cipher_word: list[str] = []
        for letter in word:
            cycle = cycles[letter]
            offset = offsets[letter]
            cipher_word.append(cycle[offset % len(cycle)])
            offsets[letter] = offset + 1
        encrypted.append(tuple(cipher_word))
    return encrypted


def objective(cipher_words: list[tuple[str, ...]], key: Mapping[str, str], lexicon: set[str]) -> dict[str, Any]:
    counts = Counter(cipher_words)
    tokens, types = sum(counts.values()), len(counts)
    token_hits = type_hits = 0
    for cipher_word, count in counts.items():
        if all(unit in key for unit in cipher_word) and "".join(key[unit] for unit in cipher_word) in lexicon:
            token_hits += count
            type_hits += 1
    score = token_hits * types + type_hits * tokens
    return {
        "token_count": tokens,
        "type_count": types,
        "denominator": 2 * tokens * types,
        "token_hits": token_hits,
        "type_hits": type_hits,
        "score": score,
    }


def accuracy(cipher_words: list[tuple[str, ...]], plain_words: list[str], key: Mapping[str, str], fit_units: set[str]) -> dict[str, Any]:
    full_char_correct = full_char_total = full_token_correct = 0
    observed_correct = observed_total = fully_observed_correct = fully_observed_total = 0
    unobserved = 0
    for cipher_word, plain_word in zip(cipher_words, plain_words, strict=True):
        need(len(cipher_word) == len(plain_word), "cipher and plaintext lengths differ")
        fully_observed = all(unit in fit_units for unit in cipher_word)
        fully_observed_total += fully_observed
        token_correct = True
        for unit, letter in zip(cipher_word, plain_word, strict=True):
            full_char_total += 1
            correct = key.get(unit) == letter
            full_char_correct += correct
            token_correct = token_correct and correct
            if unit in fit_units:
                observed_total += 1
                observed_correct += correct
            else:
                unobserved += 1
        full_token_correct += token_correct
        fully_observed_correct += fully_observed and token_correct

    def rate(correct: int, total: int) -> float | None:
        return None if total == 0 else correct / total

    return {
        "full_char_correct": full_char_correct,
        "full_char_total": full_char_total,
        "full_char_accuracy": rate(full_char_correct, full_char_total),
        "full_token_correct": full_token_correct,
        "full_token_total": len(plain_words),
        "full_token_accuracy": rate(full_token_correct, len(plain_words)),
        "observed_position_correct": observed_correct,
        "observed_position_total": observed_total,
        "observed_position_accuracy": rate(observed_correct, observed_total),
        "fully_observed_token_correct": fully_observed_correct,
        "fully_observed_token_total": fully_observed_total,
        "fully_observed_token_accuracy": rate(fully_observed_correct, fully_observed_total),
        "unobserved_position_count": unobserved,
    }


def gates(metrics: Mapping[str, Any]) -> dict[str, bool | None]:
    return {
        "observed_positions_pass": metrics["observed_position_correct"] == metrics["observed_position_total"] if metrics["observed_position_total"] else None,
        "fully_observed_tokens_pass": metrics["fully_observed_token_correct"] == metrics["fully_observed_token_total"] if metrics["fully_observed_token_total"] else None,
        "full_decoding_pass": (metrics["full_char_correct"] == metrics["full_char_total"] and metrics["full_token_correct"] == metrics["full_token_total"]) if metrics["full_char_total"] and metrics["full_token_total"] else None,
    }


def compare_metrics(report: Mapping[str, Any], derived: Mapping[str, Any], name: str) -> None:
    for field, value in derived.items():
        need(report.get(field) == value, f"{name} metric mismatch: {field}")


def write_identical(raw: bytes) -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    try:
        with OUT.open("xb") as handle:
            handle.write(raw)
    except FileExistsError:
        need(OUT.read_bytes() == raw, "audit output exists with different bytes")


def main() -> int:
    try:
        freeze, pinned = pin_all_inputs()
        partitions = parse_object(pinned[PARTITIONS], "partitions")
        manifest = parse_object(pinned[MANIFEST], "partition manifest")
        cold = parse_object(pinned[next(path for path in OUTPUT_PINS if path.endswith("cold.json"))], "cold report")
        key_record = parse_object(pinned[next(path for path in OUTPUT_PINS if path.endswith("cold.keys.json"))], "key record")
        supervision = parse_object(pinned[next(path for path in OUTPUT_PINS if path.endswith("supervision.json"))], "supervision")
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        from experiments.homophonic.controls import seeded_control_key

        need(set(partitions) == set(SPLITS), "partition split set mismatch")
        words = {split: partitions[split] for split in SPLITS}
        need(all(isinstance(value, list) and all(isinstance(word, str) for word in value) for value in words.values()), "partition words are invalid")
        planted = seeded_control_key("cap2", 7000)
        cipher = {split: encrypt(words[split], planted) for split in SPLITS}
        lexicon = set(words["train"])
        validation_objective = objective(cipher["validation"], key_record["key"], lexicon)
        planted_objective = objective(cipher["validation"], planted["cipher_to_plain"], lexicon)
        fit_units = {unit for word in cipher["validation"] for unit in word}
        key = key_record["key"]
        metrics = {split: accuracy(cipher[split], words[split], key, fit_units) for split in ("validation", "test")}
        metric_gates = {split: gates(metrics[split]) for split in ("validation", "test")}
        stream_hashes = {
            "plaintext_train": canonical_hash(words["train"]),
            "plaintext_validation": canonical_hash(words["validation"]),
            "plaintext_test": canonical_hash(words["test"]),
            "cipher_train": canonical_hash(cipher["train"]),
            "cipher_validation": canonical_hash(cipher["validation"]),
            "cipher_test": canonical_hash(cipher["test"]),
        }
        expected_streams = cold.get("stream_sha256")
        need(expected_streams == stream_hashes, "stream hash mismatch")
        need(cold.get("fit_input", {}).get("token_count") == validation_objective["token_count"], "fit token count mismatch")
        need(cold.get("fit_input", {}).get("type_count") == validation_objective["type_count"], "fit type count mismatch")
        need(cold.get("fit_input", {}).get("unit_count") == len(fit_units), "fit unit count mismatch")
        need(cold.get("fit_input", {}).get("sha256") == stream_hashes["cipher_validation"], "fit stream hash mismatch")
        need(cold.get("train_lexicon", {}).get("type_count") == len(lexicon), "training type count mismatch")
        need(cold.get("train_lexicon", {}).get("sha256") == canonical_hash(sorted(lexicon)), "training lexicon hash mismatch")
        for report, derived, name in ((cold.get("objective", {}), validation_objective, "fitted objective"), (cold.get("oracle", {}).get("objective", {}), planted_objective, "planted objective")):
            need(report.get("N_token_count") == derived["token_count"] and report.get("T_type_count") == derived["type_count"], f"{name} counts mismatch")
            need(report.get("denominator") == derived["denominator"] and report.get("weights_total") == derived["denominator"], f"{name} denominator mismatch")
            need(report.get("score_from_key") == derived["score"], f"{name} score mismatch")
            need(report.get("fit_hits", {}).get("token_hits") == derived["token_hits"] and report.get("fit_hits", {}).get("type_hits") == derived["type_hits"], f"{name} hits mismatch")
        for split in ("validation", "test"):
            compare_metrics(cold.get("accuracy", {}).get(split, {}), metrics[split], split)
            need(cold.get("gates", {}).get(split) == metric_gates[split], f"{split} gate mismatch")
        need(cold.get("test_fully_observed") is (metrics["test"]["unobserved_position_count"] == 0), "test observation flag mismatch")
        need(key_record.get("family") == "cap2" and key_record.get("seed") == 7000, "key provenance mismatch")
        need(set(key) == fit_units and len(key) == 48, "fitted key does not cover exactly 48 units")
        preimages = Counter(key.values())
        need(all(letter in ALPHABET for letter in key.values()) and max(preimages.values(), default=0) <= 2, "fitted key exceeds capacity")
        correct_key = sum(key[unit] == planted["cipher_to_plain"][unit] for unit in fit_units)
        need(correct_key == cold.get("fitted_key_accuracy", {}).get("correct") == 14, "fitted key accuracy mismatch")
        need(cold.get("fitted_key_accuracy", {}).get("total") == 48, "fitted key total mismatch")
        solver = cold.get("solver", {})
        need(solver.get("feasible") is True and solver.get("score") == validation_objective["score"], "reported solver score mismatch")
        need(solver.get("lower_bound") == 16202725 and solver.get("upper_bound") == 170919175, "reported solver bounds mismatch")
        need(planted_objective["score"] <= solver["upper_bound"], "planted score exceeds reported upper bound")
        need(solver.get("status") == "budget_exhausted" and solver.get("score_certified") is False and solver.get("search_exhausted") is False, "solver status mismatch")
        need(supervision.get("numeric_outputs_valid") is True and supervision.get("status") == "incomplete_search", "supervision status mismatch")
        need(sha256(pinned[next(path for path in OUTPUT_PINS if path.endswith("cold.keys.json"))]) == cold.get("key_record_sha256"), "key record hash mismatch")
        need(manifest.get("schema_version") == 1 and manifest.get("raw_text_included") is False, "partition manifest scope mismatch")
        checks = {
            "control_freeze_pinned": len(freeze["files"]) == 43,
            "partition_pins": True,
            "model_output_pins": True,
            "stream_hashes": True,
            "training_lexicon": True,
            "integer_fit_objective": validation_objective["score"] == 16202725,
            "integer_planted_objective": planted_objective["score"] == 166472985,
            "fit_units_and_capacity": True,
            "accuracy_and_gates": True,
            "key_accuracy_14_of_48": correct_key == 14,
            "known_score_within_upper_bound": planted_objective["score"] <= solver["upper_bound"],
            "incomplete_search_status": supervision.get("status") == "incomplete_search",
        }
        need(all(checks.values()), "independent model audit check failed")
        safe_metrics = {split: {field: metrics[split][field] for field in ("full_char_correct", "full_char_total", "full_char_accuracy", "full_token_correct", "full_token_total", "full_token_accuracy")} for split in ("validation", "test")}
        public = {
            "schema_version": 1,
            "verification": "celsus-model-control-independent-audit",
            "status": "PASS",
            "model_status": "incomplete_search",
            "inputs": {
                "control_freeze": {"bytes": FREEZE_BYTES, "sha256": FREEZE_SHA256},
                "freeze_file_count": 43,
                "frozen_file_hashes_verified": True,
                "partitions": {"bytes": PARTITION_PINS[PARTITIONS][0], "sha256": PARTITION_PINS[PARTITIONS][1]},
                "partition_manifest": {"bytes": PARTITION_PINS[MANIFEST][0], "sha256": PARTITION_PINS[MANIFEST][1]},
                "model_outputs": {path: {"bytes": size, "sha256": expected} for path, (size, expected) in OUTPUT_PINS.items()},
            },
            "result": {
                "token_count": validation_objective["token_count"],
                "type_count": validation_objective["type_count"],
                "objective_denominator": validation_objective["denominator"],
                "fit": {"token_hits": validation_objective["token_hits"], "type_hits": validation_objective["type_hits"], "score": validation_objective["score"]},
                "planted": {"token_hits": planted_objective["token_hits"], "type_hits": planted_objective["type_hits"], "score": planted_objective["score"]},
                "reported_upper_bound": solver["upper_bound"],
                "score_within_upper_bound": planted_objective["score"] <= solver["upper_bound"],
                "train_lexicon_type_count": len(lexicon),
                "train_lexicon_sha256": canonical_hash(sorted(lexicon)),
                "streams_sha256": stream_hashes,
                "fit_key": {"unit_count": len(fit_units), "key_unit_count": len(key), "capacity": 2, "maximum_preimage_count": max(preimages.values(), default=0), "capacity_valid": True, "correct_count": correct_key, "total_count": 48},
                "accuracy": safe_metrics,
                "gates": metric_gates,
            },
            "checks": checks,
            "limitations": [
                "This audit verifies a known-cipher Celsus control only.",
                "It does not rerun the solver or score the Voynich manuscript.",
                "The reported search remains incomplete. The upper bound is not an optimum certificate.",
                "The planted score is feasible within the reported upper bound.",
            ],
        }
        write_identical((json.dumps(public, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8"))
        print("Celsus model audit: PASS")
        print(f"audit_sha256={sha256(OUT.read_bytes())}")
        return 0
    except AuditError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
