"""Run end-to-end checks for the space-free runner with synthetic files only.

Fixture schema:
  {"schema_version": 1, "alphabet": "abcd",
   "reference_training_words": [...], "control_fit_plaintext": "...",
   "control_test_plaintext": "...", "manuscript_fixture_path": "..."}

The manuscript fixture has schema_version 1 and a loci list. Each locus has
source (ZL or IT), folio, kind, tokens, excluded_tokens, and text_raw fields.
The runner reads that file only after all four controls pass.
"""

from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import random
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / "experiments/spacefree_manuscript/run.py"
IMPLEMENTATION = ROOT / "results/spacefree-manuscript-2026-09-30/implementation"
ALPHABET = "abcd"
TRAINING_WORDS = ["a" * 80, "b" * 60, "c" * 40, "d" * 20, "abcd" * 10]
TRAINING_STREAM = "".join(TRAINING_WORDS)
CONTROL_FIXTURE = {
    "schema_version": 1,
    "alphabet": ALPHABET,
    "reference_training_words": TRAINING_WORDS,
    "control_fit_plaintext": TRAINING_STREAM,
    "control_test_plaintext": ("abcd" * 20) + ("aabbccdd" * 5),
    "manuscript_fixture_path": "manuscript.json",
}
FREEZE_PATHS = [
    "docs/plans/spacefree-manuscript-pilot-v1.md",
    "experiments/spacefree_manuscript/run.py",
    "experiments/spacefree_manuscript/check_e2e.py",
    "experiments/spacefree_substitution/score.py",
    "src/voynich/reference.py",
    "src/voynich/corpus.py",
    "src/voynich/groups.py",
    "data/reference_manifest.json",
    "data/source_manifest.json",
    "data/bifolio_manifest.json",
]


def _partition_folios():
    sys.path.insert(0, str(ROOT / "src"))
    from voynich.groups import group_id, split_bucket, split_name

    found = {}
    for number in range(1, 117):
        folio = f"f{number}r"
        try:
            split = split_name(split_bucket(group_id(folio)))
        except ValueError:
            continue
        found.setdefault(split, folio)
    assert set(found) == {"train", "validation", "test"}, found
    return found


def _record(source, folio, words, **extra):
    value = {
        "source": source,
        "folio": folio,
        "kind": "P0",
        "tokens": words,
        "excluded_tokens": 0,
        "text_raw": " ".join(words),
    }
    value.update(extra)
    return value


def _manuscript_fixture(test_suffix="abdc"):
    folios = _partition_folios()
    loci = [
        _record("ZL", folios["train"], ["abca", "bcab", "acab", "baab", "caba", "aabc"],
                locus="f1r.1,@P0;A", transcriber="A", metadata={"$H": "A"}),
        _record("ZL", folios["validation"], ["abba", "ccab", "acba"]),
        _record("ZL", folios["test"], ["abdc", "dabc", test_suffix]),
        _record("IT", folios["train"], ["caba", "abca"]),
        _record("IT", folios["validation"], ["bacb", "acba"]),
        _record("IT", folios["test"], ["adcb", "cabd"]),
        _record("ZL", folios["train"], ["abcd"], kind="H0"),
        _record("ZL", folios["train"], [], text_raw=""),
        _record("ZL", folios["train"], ["ab"], excluded_tokens=1),
        _record("ZL", folios["train"], ["abca"], text_raw="abca <->"),
        _record("ZL", folios["train"], ["bcab"], text_raw="bcab <~>"),
    ]
    return {"schema_version": 1, "loci": loci}


def _write_json(path, value):
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def _run(fixture, output, cwd, timeout=120):
    fixture_path = cwd / "fixture.json"
    _write_json(fixture_path, fixture)
    command = [sys.executable, str(RUNNER), "--fixture", str(fixture_path),
               "--output", str(output)]
    completed = subprocess.run(command, cwd=ROOT, capture_output=True,
                               text=True, timeout=timeout)
    return completed, command


def _hash_files(directory):
    return {
        path.relative_to(directory).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(directory.rglob("*")) if path.is_file()
    }


def _direct_score(training, text, alphabet):
    weights = (0.1, 0.2, 0.3, 0.4)
    totals = 0.0
    for end in range(3, len(text)):
        for context_length, weight in enumerate(weights):
            context = text[end - context_length:end] if context_length else ""
            target = text[end]
            gram = context + target
            counts = Counter(
                training[position - context_length:position + 1]
                for position in range(context_length, len(training))
            )
            context_total = sum(
                count for key, count in counts.items() if key[:-1] == context
            )
            probability = (counts[gram] + 0.1) / (context_total + 0.1 * len(alphabet))
            totals += -weight * math.log2(probability)
    return totals


def _direct_unknown_score(training, stream, key, alphabet):
    decoded = "".join(key.get(symbol, "?") for symbol in stream)
    unknown = Counter(symbol for symbol in stream if symbol not in key)
    unknown_windows = 0
    total_cost = 0.0
    for start in range(max(0, len(stream) - 3)):
        window = stream[start:start + 4]
        if any(symbol not in key for symbol in window):
            unknown_windows += 1
            total_cost += math.log2(len(alphabet))
        else:
            total_cost += _direct_score(training, decoded[start:start + 4], alphabet)
    count = max(0, len(stream) - 3)
    return {
        "decoded_text": decoded,
        "unknown_character_counts": dict(sorted(unknown.items())),
        "unknown_window_count": unknown_windows,
        "window_count": count,
        "total_cost": total_cost,
        "mean_cost": total_cost / count if count else None,
    }


def _known_key(alphabet, seed):
    plain = list(alphabet)
    random.Random(seed).shuffle(plain)
    return dict(zip(alphabet, plain, strict=True))


def _assert_control_results(result, private):
    calibration = result["calibration"]
    assert calibration["status"] == "passed", calibration
    assert calibration["accepted"] is True, calibration
    controls = calibration["controls"]
    assert [item["seed"] for item in controls] == [408, 409, 410, 411], controls
    assert all(item["passed"] for item in controls), controls
    private_controls = private["controls"]
    assert len(private_controls) == 4, private_controls
    for item in private_controls:
        known = _known_key(ALPHABET, item["seed"])
        assert item["known_cipher_to_plain"] == known, item
        assert item["fitted_cipher_to_plain"] == known, item
        assert item["fit_error_positions"] == [], item
        assert item["test_error_positions"] == [], item
        assert item["full_map_equal"] is True, item
        assert item["missing_fit_labels"] == [], item
        assert item["test_labels_absent_from_fit"] == [], item
        direct = _direct_score(TRAINING_STREAM, item["decoded_fit"], ALPHABET)
        assert math.isclose(item["fit_cost"], direct, rel_tol=1e-10, abs_tol=1e-9), item


def _main_green_checks(base):
    main_dir = base / "main"
    manuscript = _manuscript_fixture()
    manuscript_path = base / "manuscript.json"
    _write_json(manuscript_path, manuscript)
    fixture = dict(CONTROL_FIXTURE, manuscript_fixture_path=manuscript_path.name)
    completed, command = _run(fixture, main_dir, base)
    assert completed.returncode == 0, completed.stderr
    result = json.loads((main_dir / "result.json").read_text(encoding="utf-8"))
    calibration_private = json.loads((main_dir / "calibration/private.json").read_text(encoding="utf-8"))
    manuscript_private = json.loads((main_dir / "manuscript/private.json").read_text(encoding="utf-8"))
    _assert_control_results(result, calibration_private)
    for item in calibration_private["controls"]:
        frozen = json.loads((main_dir / "calibration" /
                             f"frozen-fit-key-seed-{item['seed']}.json").read_text())
        assert frozen["fitted_cipher_to_plain"] == item["fitted_cipher_to_plain"], frozen
        assert frozen["key_positions"] == item["key_positions"], frozen
    assert result["manuscript_stage"]["status"] == "run", result
    assert set(result["manuscript_stage"]["gates"].values()) <= {True, False}
    assert set(result["manuscript_stage"]["gates"]) == {
        "all_four_controls", "observed_at_or_below_latin",
        "below_both_shuffle_and_identity", "mapped_coverage_at_least_99_percent",
    }

    observed = manuscript_private["fits"]["observed"]
    observed_key = observed["observed_cipher_to_plain"]
    assert set(observed_key) == set("abc"), observed_key
    assert "d" not in observed_key, observed_key
    assert manuscript_private["full_permutations"]["observed"] == observed["key_positions"]
    assert manuscript_private["scores"]["observed"]["ZL"]["test"]["unknown_character_counts"] == {"d": 3}
    raw_test = manuscript_private["streams"]["ZL"]["test"]["text"]
    direct = _direct_unknown_score(TRAINING_STREAM, raw_test, observed_key, ALPHABET)
    scored = manuscript_private["scores"]["observed"]["ZL"]["test"]
    assert scored["decoded_text"] == direct["decoded_text"], scored
    assert scored["unknown_character_counts"] == direct["unknown_character_counts"], scored
    assert scored["unknown_window_count"] == direct["unknown_window_count"], scored
    assert scored["window_count"] == direct["window_count"], scored
    assert math.isclose(scored["total_cost"], direct["total_cost"], abs_tol=1e-9), scored
    assert math.isclose(scored["mean_cost"], direct["mean_cost"], abs_tol=1e-9), scored

    for split in ("train", "validation", "test"):
        it_stream = manuscript_private["streams"]["IT"][split]["text"]
        it_scored = manuscript_private["scores"]["observed"]["IT"][split]
        it_direct = _direct_unknown_score(TRAINING_STREAM, it_stream, observed_key, ALPHABET)
        assert it_scored["decoded_text"] == it_direct["decoded_text"], it_scored
        assert it_scored["unknown_character_counts"] == it_direct["unknown_character_counts"], it_scored
        assert it_scored["unknown_window_count"] == it_direct["unknown_window_count"], it_scored
        it_mapped = sum(count for symbol, count in Counter(it_stream).items()
                        if symbol in observed_key)
        assert it_scored["mapped_character_count"] == it_mapped, it_scored
        assert it_scored["unmapped_character_count"] == len(it_stream) - it_mapped, it_scored
        assert math.isclose(
            it_scored["mapped_coverage"], it_mapped / len(it_stream), abs_tol=1e-12
        ), it_scored
        assert math.isclose(it_scored["total_cost"], it_direct["total_cost"], abs_tol=1e-9), it_scored

    exclusions = manuscript_private["exclusions"]["ZL"]
    assert exclusions == {
        "non_paragraph": 1, "empty": 1, "excluded_token": 1,
        "interrupted": 2, "eligible": 3,
    }, exclusions
    folios = _partition_folios()
    assert manuscript_private["loci"]["ZL"]["eligible"][0]["partition"] == "train"
    assert manuscript_private["loci"]["ZL"]["eligible"][0]["folio"] == folios["train"]
    source_locus = manuscript_private["loci"]["ZL"]["eligible"][0]
    assert source_locus["locus"] == "f1r.1,@P0;A", source_locus
    assert source_locus["transcriber"] == "A", source_locus
    assert source_locus["metadata"] == {"$H": "A"}, source_locus

    seeds = {"train": 508, "validation": 509, "test": 510}
    within = manuscript_private["shuffles"]["within_word"]
    word_order = manuscript_private["shuffles"]["word_order"]
    original_words = manuscript_private["words"]["ZL"]
    for split, seed in seeds.items():
        entry = within[split]
        assert entry["seed"] == seed, entry
        original = original_words[split]
        shuffled = entry["words"]
        assert len(original) == len(shuffled), entry
        assert [len(word) for word in original] == [len(word) for word in shuffled], entry
        assert [sorted(word) for word in original] == [sorted(word) for word in shuffled], entry
        rng = random.Random(seed)
        expected = []
        for word in original:
            chars = list(word)
            rng.shuffle(chars)
            expected.append("".join(chars))
        assert shuffled == expected, entry
        order_entry = word_order[split]
        order_seed = 608 + (0 if split == "train" else 1 if split == "validation" else 2)
        assert order_entry["seed"] == order_seed, order_entry
        expected_words = list(original)
        random.Random(order_seed).shuffle(expected_words)
        assert order_entry["words"] == expected_words, order_entry
        assert Counter(order_entry["words"]) == Counter(original), order_entry
        assert sum(map(len, order_entry["words"])) == sum(map(len, original)), order_entry

    output_hashes = _hash_files(main_dir)
    observed_mean = scored["mean_cost"]
    within_mean = manuscript_private["scores"]["within_word_shuffle"]["ZL"]["test"]["mean_cost"]
    order_mean = manuscript_private["scores"]["word_order_shuffle"]["ZL"]["test"]["mean_cost"]
    identity_mean = manuscript_private["scores"]["identity"]["ZL"]["test"]["mean_cost"]
    latin_mean = result["manuscript_stage"]["latin_test_baseline"]["mean_cost"]
    mapped_coverage = scored["mapped_character_count"] / scored["character_count"]
    expected_gates = {
        "all_four_controls": all(item["passed"] for item in result["calibration"]["controls"]),
        "observed_at_or_below_latin": observed_mean <= latin_mean,
        "below_both_shuffle_and_identity": observed_mean < min(
            within_mean, order_mean, identity_mean),
        "mapped_coverage_at_least_99_percent": mapped_coverage >= 0.99,
    }
    assert result["manuscript_stage"]["gates"] == expected_gates, result["manuscript_stage"]["gates"]
    return {
        "command": "python experiments/spacefree_manuscript/run.py --fixture FIXTURE.json --output NEW_DIRECTORY",
        "returncode": completed.returncode,
        "checks": [
            "Four seeded control maps have cipher-to-plain orientation and recover fit and test text.",
            "An independent context-count sum matches the stored fit score.",
            "Unseen test signs use question marks and every affected window uses the fixed fixture penalty.",
            "Folio metadata assigns synthetic loci to the source split.",
            "Exclusions are sequential and count both interruption markers.",
            "Both shuffles preserve their specified word and character invariants and seeds.",
        ],
        "output_hashes": output_hashes,
        "fit_keys": {name: fit["observed_cipher_to_plain"]
                     for name, fit in manuscript_private["fits"].items()},
        "test_score": scored,
        "gate_values": result["manuscript_stage"]["gates"],
        "independently_calculated_gate_values": expected_gates,
        "known_control_map": calibration_private["controls"][0]["known_cipher_to_plain"],
    }


def _invariance_and_failure_checks(base, main_info):
    original_fixture = dict(CONTROL_FIXTURE, manuscript_fixture_path="manuscript-a.json")
    changed_fixture = dict(CONTROL_FIXTURE, manuscript_fixture_path="manuscript-b.json")
    _write_json(base / "manuscript-a.json", _manuscript_fixture())
    _write_json(base / "manuscript-b.json", _manuscript_fixture(test_suffix="dcba"))
    first, _ = _run(original_fixture, base / "invariance-a", base)
    second, _ = _run(changed_fixture, base / "invariance-b", base)
    assert first.returncode == second.returncode == 0, (first.stderr, second.stderr)
    first_result = json.loads((base / "invariance-a/result.json").read_text())
    second_result = json.loads((base / "invariance-b/result.json").read_text())
    first_private = json.loads((base / "invariance-a/manuscript/private.json").read_text())
    second_private = json.loads((base / "invariance-b/manuscript/private.json").read_text())
    fits_a = {name: (fit["key_positions"], fit["fit_cost"])
              for name, fit in first_private["fits"].items()}
    fits_b = {name: (fit["key_positions"], fit["fit_cost"])
              for name, fit in second_private["fits"].items()}
    assert fits_a == fits_b, (fits_a, fits_b)
    assert first_result["calibration"] == second_result["calibration"]

    fail_fixture = dict(CONTROL_FIXTURE, control_fit_plaintext="a" * 80,
                        control_test_plaintext="abcd" * 20,
                        manuscript_fixture_path="must-not-open.json")
    failed, _ = _run(fail_fixture, base / "calibration-failed", base)
    assert failed.returncode == 0, failed.stderr
    failed_path = base / "calibration-failed"
    failed_result = json.loads((failed_path / "result.json").read_text())
    failed_private = json.loads((failed_path / "calibration/private.json").read_text())
    assert failed_result["calibration"]["accepted"] is False, failed_result
    assert failed_result["manuscript_stage"]["status"] == "blocked", failed_result
    assert len(failed_private["controls"]) == 4, failed_private
    for item in failed_private["controls"]:
        fit_ciphertext = item["fit_ciphertext"]
        test_ciphertext = item["test_ciphertext"]
        fit_truth = item["fit_plaintext"]
        test_truth = item["test_plaintext"]
        fitted = item["fitted_cipher_to_plain"]
        known = item["known_cipher_to_plain"]
        expected_fit_errors = [
            i for i, (cipher, truth) in enumerate(zip(fit_ciphertext, fit_truth, strict=True))
            if fitted[cipher] != truth
        ]
        expected_test_errors = [
            i for i, (cipher, truth) in enumerate(zip(test_ciphertext, test_truth, strict=True))
            if fitted[cipher] != truth
        ]
        expected_missing = [c for c in ALPHABET if c not in set(fit_ciphertext)]
        expected_absent_test = [c for c in ALPHABET if c in set(test_ciphertext) and c not in set(fit_ciphertext)]
        expected_fit_assignments_correct = all(
            fitted[cipher] == known[cipher] for cipher in set(fit_ciphertext)
        )
        expected_test_positions_correct = not expected_test_errors
        assert item["fit_error_positions"] == expected_fit_errors, item
        assert item["test_error_positions"] == expected_test_errors, item
        assert item["missing_fit_labels"] == expected_missing, item
        assert item["test_labels_absent_from_fit"] == expected_absent_test, item
        assert item["fit_error_count"] == len(expected_fit_errors), item
        assert item["test_error_count"] == len(expected_test_errors), item
        assert item["observed_fit_assignments_correct"] == expected_fit_assignments_correct, item
        assert item["test_positions_correct"] == expected_test_positions_correct, item
        assert item["passed"] == (expected_fit_assignments_correct and expected_test_positions_correct), item
        assert known == _known_key(ALPHABET, item["seed"]), item
    assert not (failed_path / "manuscript").exists(), "Failed calibration made manuscript artifacts"

    bad_late = dict(CONTROL_FIXTURE, manuscript_fixture_path="missing-after-calibration.json")
    late, _ = _run(bad_late, base / "late-manuscript-error", base)
    late_path = base / "late-manuscript-error"
    assert late.returncode != 0, "Missing manuscript fixture did not fail after calibration"
    late_result = json.loads((late_path / "result.json").read_text())
    assert late_result["calibration"]["accepted"] is True, late_result
    assert len(json.loads((late_path / "calibration/private.json").read_text())["controls"]) == 4
    assert (late_path / "error.json").is_file(), "Late failure did not preserve a partial receipt"

    return {
        "test_only_change": "Two manuscript test inputs differ; all three fitted keys and fit costs remain equal.",
        "calibration_failure": {
            "status": failed_result["calibration"]["status"],
            "accepted": failed_result["calibration"]["accepted"],
            "manuscript_stage": failed_result["manuscript_stage"]["status"],
            "control_count": len(failed_private["controls"]),
            "manuscript_directory_exists": (failed_path / "manuscript").exists(),
        },
        "unavailable_manuscript_after_pass": {
            "exit_nonzero": late.returncode != 0,
            "calibration_accepted": late_result["calibration"]["accepted"],
            "partial_calibration_files": _hash_files(late_path / "calibration"),
            "error_file": (late_path / "error.json").is_file(),
        },
    }


def _refusal_checks(base):
    invalid_fixture = dict(CONTROL_FIXTURE)
    invalid_fixture["alphabet"] = "aabc"
    invalid, _ = _run(invalid_fixture, base / "invalid", base)
    assert invalid.returncode != 0 and not (base / "invalid").exists(), "Invalid fixture created output"

    existing = base / "existing"
    existing.mkdir()
    marker = existing / "keep.txt"
    marker.write_text("keep\n")
    before = _hash_files(existing)
    refused, _ = _run(CONTROL_FIXTURE, existing, base)
    after = _hash_files(existing)
    assert refused.returncode != 0 and before == after, "Existing output changed"

    hashes = {
        path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
        for path in FREEZE_PATHS
    }
    hashes["experiments/spacefree_substitution/score.py"] = "0" * 64
    freeze = base / "bad-freeze.json"
    _write_json(freeze, {"schema_version": 1, "files": hashes})
    output = base / "bad-freeze-output"
    bad = subprocess.run(
        [sys.executable, str(RUNNER), "--freeze", str(freeze), "--output", str(output)],
        cwd=ROOT, capture_output=True, text=True, timeout=30,
    )
    assert bad.returncode != 0 and not output.exists(), "Bad freeze created output"
    assert "hash" in bad.stderr.lower() or "mismatch" in bad.stderr.lower(), bad.stderr
    return {
        "invalid_fixture": {"exit_nonzero": invalid.returncode != 0, "output_created": (base / "invalid").exists()},
        "existing_output": {"exit_nonzero": refused.returncode != 0, "all_files_unchanged": before == after},
        "freeze_hash_mismatch": {"exit_nonzero": bad.returncode != 0, "output_created": output.exists(),
                                 "stderr_contains_hash_error": True},
    }


def main():
    if not RUNNER.is_file():
        print(json.dumps({
            "status": "red",
            "expected": "The end-to-end check runs before the command exists.",
            "runner_exists": False,
            "check_e2e_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "next_step": "Implement run.py, then rerun this check.",
        }, sort_keys=True))
        return 2

    with tempfile.TemporaryDirectory(prefix="spacefree-e2e-") as temp:
        base = Path(temp)
        main_info = _main_green_checks(base)
        invariance = _invariance_and_failure_checks(base, main_info)
        refusals = _refusal_checks(base)
        receipt = {
            "status": "passed",
            "setup": "Python standard library; all corpus inputs are synthetic; no raw manuscript or reference loader is used.",
            "command": "python experiments/spacefree_manuscript/check_e2e.py",
            "source_hashes": {
                "runner_sha256": hashlib.sha256(RUNNER.read_bytes()).hexdigest(),
                "harness_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "plan_sha256": hashlib.sha256(
                    (ROOT / "docs/plans/spacefree-manuscript-pilot-v1.md").read_bytes()
                ).hexdigest(),
            },
            "fixture_schema": "schema_version, alphabet, reference_training_words, control_fit_plaintext, control_test_plaintext, manuscript_fixture_path; separate manuscript JSON has schema_version and loci.",
            "fixture_summary": {
                "alphabet": ALPHABET,
                "reference_training_word_lengths": [len(word) for word in TRAINING_WORDS],
                "control_fit_character_count": len(CONTROL_FIXTURE["control_fit_plaintext"]),
                "control_test_character_count": len(CONTROL_FIXTURE["control_test_plaintext"]),
                "locus_count": len(_manuscript_fixture()["loci"]),
            },
            "steps": [
                "Run the fixed CLI with the synthetic four-letter reference and manuscript files.",
                "Change only held-out ZL text and compare all fitted keys and fit costs.",
                "Use a failing calibration with an unavailable manuscript path and confirm no manuscript output appears.",
                "Use a passing calibration with an unavailable path and confirm partial calibration evidence remains.",
                "Check invalid input, existing-output refusal, and freeze-hash refusal.",
            ],
            "checks": main_info,
            "invariance_and_failure": invariance,
            "refusals": refusals,
            "limits": [
                "The four-symbol fixture checks command behavior only.",
                "It does not test the fixed method on a historical reference or manuscript text.",
            ],
        }
        print(json.dumps(receipt, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
