"""Run the fixed space-free known-key substitution controls."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import signal
import sys
import time


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from voynich.reference import load_reference_partitions

from score import (
    ALPHA,
    PROPOSALS_PER_RESTART,
    RESTARTS,
    SEARCH_SEED,
    WEIGHTS,
    NGramModel,
    search_key,
)


PROTOCOL = "spacefree-substitution-control-v1"
ALPHABET = "abcdefghilmnopqrstuvxyz"
MANIFEST_SHA256 = "f261b781f150991e3305aae5057a94dc91afd8e59c58bb22ff199347f5ce3e6d"
PARTITION_PREFIX_LENGTH = 8192
PLANTED_SEEDS = (408, 409, 410, 411)
TIME_LIMIT_SECONDS = 600
SUBSTITUTIONS = {"j": "i", "k": "c", "w": "uu"}
REQUIRED_FREEZE_FILES = (
    "docs/plans/spacefree-substitution-control-v1.md",
    "experiments/spacefree_substitution/score.py",
    "experiments/spacefree_substitution/run_control.py",
    "experiments/spacefree_substitution/check_e2e.py",
    "src/voynich/reference.py",
    "data/reference_manifest.json",
)
FIXTURE_FIELDS = {
    "alphabet", "train", "fit_plaintext", "test_plaintext", "known_key"
}


class ControlTimeout(Exception):
    """End the fixed control when its time limit expires."""


def _timeout_handler(_signal_number, _frame):
    raise ControlTimeout("The fixed 600-second control limit elapsed.")


def _sha256(data):
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path):
    return _sha256(path.read_bytes())


def _write_json(path, value):
    """Create a new JSON file and keep existing evidence."""
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, ensure_ascii=True, indent=2, sort_keys=True,
                  allow_nan=False)
        stream.write("\n")


def _write_text(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(value)
        stream.write("\n")


def _read_json(path, label):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError(f"Cannot read the {label} JSON file.") from error


def _check_output_path(path):
    if path.exists() or path.is_symlink():
        raise ValueError("The output path already exists.")


def _check_freeze(freeze_path):
    """Compare the fixed source and reference hashes before corpus loading."""
    freeze = _read_json(freeze_path, "freeze")
    if not isinstance(freeze, dict) or set(freeze) != {"schema_version", "files"}:
        raise ValueError("The freeze file has an invalid schema.")
    if freeze["schema_version"] != 1 or not isinstance(freeze["files"], dict):
        raise ValueError("The freeze file has an invalid schema.")
    files = freeze["files"]
    if set(files) != set(REQUIRED_FREEZE_FILES):
        raise ValueError("The freeze file does not name the required files.")

    for relative_path in REQUIRED_FREEZE_FILES:
        expected = files[relative_path]
        if not isinstance(expected, str) or re.fullmatch(r"[0-9a-f]{64}", expected) is None:
            raise ValueError("The freeze file has an invalid SHA-256 value.")
        source_path = ROOT / relative_path
        try:
            actual = _sha256_file(source_path)
        except OSError as error:
            raise ValueError("A frozen source file is unavailable.") from error
        if actual != expected:
            raise ValueError("Frozen source hash mismatch.")

    if files["data/reference_manifest.json"] != MANIFEST_SHA256:
        raise ValueError("The reference manifest does not match the fixed hash.")
    return {
        "schema_version": 1,
        "files": dict(files),
        "freeze_sha256": _sha256_file(freeze_path),
    }


def _validate_alphabet(alphabet):
    if not isinstance(alphabet, str) or len(alphabet) < 2:
        raise ValueError("The alphabet must contain at least two symbols.")
    if len(set(alphabet)) != len(alphabet):
        raise ValueError("The alphabet must not contain duplicate symbols.")


def _validate_stream(text, alphabet, label, minimum_length=0):
    if not isinstance(text, str) or len(text) < minimum_length:
        raise ValueError(f"The {label} stream has an invalid length or type.")
    if set(text).difference(alphabet):
        raise ValueError(f"The {label} stream has symbols outside its alphabet.")


def _validate_key(alphabet, value):
    if not isinstance(value, dict) or set(value) != set(alphabet):
        raise ValueError("The known key must map every alphabet symbol.")
    if any(not isinstance(symbol, str) or len(symbol) != 1 for symbol in value.values()):
        raise ValueError("The known key has an invalid symbol.")
    if set(value.values()) != set(alphabet):
        raise ValueError("The known key must be a permutation.")
    return {symbol: value[symbol] for symbol in alphabet}


def _encode(plaintext, key):
    """Encode text with a decoding key that maps cipher to plaintext."""
    inverse = {plain: cipher for cipher, plain in key.items()}
    return "".join(inverse[symbol] for symbol in plaintext)


def _decode(ciphertext, key):
    return "".join(key[symbol] for symbol in ciphertext)


def _key_positions(alphabet, key):
    index = {symbol: position for position, symbol in enumerate(alphabet)}
    return [index[key[symbol]] for symbol in alphabet]


def _positions_key(alphabet, positions):
    return {symbol: alphabet[positions[position]]
            for position, symbol in enumerate(alphabet)}


def _mapping_errors(alphabet, observed_labels, fitted_key, known_key):
    errors = [
        {"cipher": cipher, "expected": known_key[cipher], "fitted": fitted_key[cipher]}
        for cipher in observed_labels
        if fitted_key[cipher] != known_key[cipher]
    ]
    complete_errors = [
        {"cipher": cipher, "expected": known_key[cipher], "fitted": fitted_key[cipher]}
        for cipher in alphabet
        if fitted_key[cipher] != known_key[cipher]
    ]
    return errors, complete_errors


def _character_errors(expected, actual):
    if len(expected) != len(actual):
        raise ValueError("Expected and decoded streams have different lengths.")
    return [
        {"position": position, "expected": expected[position], "decoded": actual[position]}
        for position in range(len(expected))
        if expected[position] != actual[position]
    ]


def _stream_record(text, alphabet):
    counts = Counter(text)
    return {
        "sha256": _sha256(text.encode("ascii")),
        "length": len(text),
        "symbol_counts": {symbol: counts.get(symbol, 0) for symbol in alphabet},
    }


def _fixture_inputs(fixture_path):
    fixture = _read_json(fixture_path, "fixture")
    if not isinstance(fixture, dict) or set(fixture) != FIXTURE_FIELDS:
        raise ValueError("The fixture has an invalid schema.")
    alphabet = fixture["alphabet"]
    _validate_alphabet(alphabet)
    known_key = _validate_key(alphabet, fixture["known_key"])
    train = fixture["train"]
    fit_plaintext = fixture["fit_plaintext"]
    test_plaintext = fixture["test_plaintext"]
    _validate_stream(train, alphabet, "training", minimum_length=4)
    _validate_stream(fit_plaintext, alphabet, "fitting", minimum_length=4)
    _validate_stream(test_plaintext, alphabet, "test", minimum_length=1)

    model = NGramModel(alphabet, train)
    fit_ciphertext = _encode(fit_plaintext, known_key)
    inputs = {
        "mode": "synthetic_fixture",
        "alphabet": alphabet,
        "model": model,
        "training_text": train,
        "fit_plaintext": fit_plaintext,
        "fit_ciphertext": fit_ciphertext,
        "test_plaintext": test_plaintext,
        "known_key": known_key,
        "stream_records": {
            "training": _stream_record(train, alphabet),
            "fitting_plaintext": _stream_record(fit_plaintext, alphabet),
            "fitting_ciphertext": _stream_record(fit_ciphertext, alphabet),
            "test_plaintext": _stream_record(test_plaintext, alphabet),
        },
        "source_metadata": {"kind": "synthetic fixture"},
        "freeze": None,
    }
    return inputs


def _normalize_reference_words(words):
    normalized = []
    for word in words:
        for symbol in word:
            normalized.append(SUBSTITUTIONS.get(symbol, symbol))
    stream = "".join(normalized)
    if set(stream).difference(ALPHABET):
        raise ValueError("A reference partition has symbols outside the fixed alphabet.")
    return stream


def _planted_key(seed):
    import random

    plaintext_positions = list(ALPHABET)
    random.Random(seed).shuffle(plaintext_positions)
    return {cipher: plain for cipher, plain in zip(ALPHABET, plaintext_positions)}


def _reference_inputs(freeze_path):
    freeze = _check_freeze(freeze_path)
    manifest_path = ROOT / "data" / "reference_manifest.json"
    if _sha256_file(manifest_path) != MANIFEST_SHA256:
        raise ValueError("The reference manifest does not match the fixed hash.")

    partitions = load_reference_partitions(ROOT)
    reference = partitions.get("latin_llct")
    if not isinstance(reference, dict) or not isinstance(reference.get("words"), dict):
        raise ValueError("The Latin reference partitions are unavailable.")
    metadata = reference.get("metadata")
    if not isinstance(metadata, dict) or metadata.get("reference_manifest_sha256") != MANIFEST_SHA256:
        raise ValueError("The reference loader returned a different manifest hash.")

    full_streams = {
        split: _normalize_reference_words(reference["words"][split])
        for split in ("train", "validation", "test")
    }
    if len(full_streams["validation"]) < PARTITION_PREFIX_LENGTH:
        raise ValueError("The validation partition is shorter than the fixed prefix.")
    if len(full_streams["test"]) < PARTITION_PREFIX_LENGTH:
        raise ValueError("The test partition is shorter than the fixed prefix.")
    fit_plaintext = full_streams["validation"][:PARTITION_PREFIX_LENGTH]
    test_plaintext = full_streams["test"][:PARTITION_PREFIX_LENGTH]
    model = NGramModel(ALPHABET, full_streams["train"])

    controls = []
    for seed in PLANTED_SEEDS:
        known_key = _planted_key(seed)
        controls.append({
            "seed": seed,
            "known_key": known_key,
            "fit_ciphertext": _encode(fit_plaintext, known_key),
            "test_plaintext": test_plaintext,
        })

    selected_streams = {
        "training": full_streams["train"],
        "fitting_plaintext": fit_plaintext,
        "test_plaintext": test_plaintext,
    }
    stream_records = {
        "training": _stream_record(full_streams["train"], ALPHABET),
        "validation_full": _stream_record(full_streams["validation"], ALPHABET),
        "fitting_plaintext": _stream_record(fit_plaintext, ALPHABET),
        "test_full": _stream_record(full_streams["test"], ALPHABET),
        "test_plaintext": _stream_record(test_plaintext, ALPHABET),
    }
    return {
        "mode": "known_key_control",
        "alphabet": ALPHABET,
        "model": model,
        "training_text": full_streams["train"],
        "fit_plaintext": fit_plaintext,
        "controls": controls,
        "test_plaintext": test_plaintext,
        "stream_records": stream_records,
        "selected_streams": selected_streams,
        "source_metadata": metadata,
        "freeze": freeze,
    }


def _run_one_control(inputs, control, output_dir, fixture=False):
    alphabet = inputs["alphabet"]
    model = inputs["model"]
    fit_ciphertext = control["fit_ciphertext"]
    search = search_key(model, fit_ciphertext)
    fitted_key = _positions_key(alphabet, search["key_positions"])
    key_path = output_dir / "frozen-key.json"
    _write_json(key_path, {
        "schema_version": 1,
        "seed": control.get("seed"),
        "key": fitted_key,
        "key_positions": search["key_positions"],
        "fit_cost": search["best_recomputed_cost"],
    })

    # Create test ciphertext only after the fitted key is stored.
    test_plaintext = control["test_plaintext"]
    known_key = control["known_key"]
    test_ciphertext = _encode(test_plaintext, known_key)
    decoded_test = _decode(test_ciphertext, fitted_key)
    fit_plaintext = inputs["fit_plaintext"]
    decoded_fit = _decode(fit_ciphertext, fitted_key)

    observed = set(fit_ciphertext)
    observed_labels = [symbol for symbol in alphabet if symbol in observed]
    missing_fit_labels = [symbol for symbol in alphabet if symbol not in observed]
    test_labels_absent_from_fit = [
        symbol for symbol in alphabet
        if symbol in set(test_ciphertext) and symbol not in observed
    ]
    fit_mapping_errors, complete_key_errors = _mapping_errors(
        alphabet, observed_labels, fitted_key, known_key
    )
    fit_character_errors = _character_errors(fit_plaintext, decoded_fit)
    test_character_errors = _character_errors(test_plaintext, decoded_test)
    fit_cost = model.score_indices(
        model.indices(fit_ciphertext), search["key_positions"]
    )
    fit_windows = len(fit_ciphertext) - 3
    accepted = not fit_mapping_errors and not test_character_errors

    result = {
        "schema_version": 1,
        "protocol": PROTOCOL,
        "status": "completed",
        "accepted": accepted,
        "seed": control.get("seed"),
        "alphabet": alphabet,
        "fitted_key": fitted_key,
        "known_key": known_key,
        "complete_key_errors": complete_key_errors,
        "complete_key_exact": not complete_key_errors,
        "observed_fit_labels": observed_labels,
        "missing_fit_labels": missing_fit_labels,
        "fit_mapping_errors": fit_mapping_errors,
        "fit_errors": len(fit_mapping_errors),
        "observed_fit_mapping_exact": not fit_mapping_errors,
        "fit_character_errors": fit_character_errors,
        "decoded_fit": decoded_fit,
        "test_labels_absent_from_fit": test_labels_absent_from_fit,
        "test_character_errors": test_character_errors,
        "test_errors": len(test_character_errors),
        "decoded_test": decoded_test,
        "fit_ciphertext": fit_ciphertext,
        "test_ciphertext": test_ciphertext,
        "fit_plaintext": fit_plaintext,
        "test_plaintext": test_plaintext,
        "fit_cost": fit_cost,
        "mean_fit_cost_per_window": fit_cost / fit_windows,
        "fit_window_count": fit_windows,
        "temperature_start": search["temperature_start"],
        "search": search,
    }
    if fixture:
        return result
    return result


def _run_fixture(inputs, output):
    model = inputs["model"]
    _write_json(output / "run-config.json", {
        "protocol": PROTOCOL,
        "mode": inputs["mode"],
        "alphabet": inputs["alphabet"],
        "score": {
            "alpha": ALPHA,
            "weights": list(WEIGHTS),
            "context_lengths": [0, 1, 2, 3],
            "window_length": 4,
            "window_policy": "Overlapping; no boundary symbols or padding.",
        },
        "search": {
            "seed": SEARCH_SEED,
            "restarts": RESTARTS,
            "proposals_per_restart": PROPOSALS_PER_RESTART,
        },
    })
    _write_json(output / "stream-records.json", inputs["stream_records"])
    _write_json(output / "model-counts.json", model.counts_record())
    _write_text(output / "training-stream.txt", inputs["training_text"])
    _write_text(output / "fitting-plaintext.txt", inputs["fit_plaintext"])
    result = _run_one_control(inputs, {
        "fit_ciphertext": inputs["fit_ciphertext"],
        "known_key": inputs["known_key"],
        "test_plaintext": inputs["test_plaintext"],
    }, output, fixture=True)
    _write_text(output / "fitting-ciphertext.txt", result["fit_ciphertext"])
    _write_text(output / "decoded-fitting.txt", result["decoded_fit"])
    _write_text(output / "test-plaintext.txt", result["test_plaintext"])
    _write_text(output / "test-ciphertext.txt", result["test_ciphertext"])
    _write_text(output / "decoded-test.txt", result["decoded_test"])
    _write_json(output / "result.json", result)
    return result["accepted"]


def _run_real(inputs, output):
    _write_json(output / "run-config.json", {
        "protocol": PROTOCOL,
        "mode": inputs["mode"],
        "alphabet": inputs["alphabet"],
        "normalization": {
            "j": "i",
            "k": "c",
            "w": "uu",
            "partition_stream": "Join normalized words without spaces.",
            "validation_characters": PARTITION_PREFIX_LENGTH,
            "test_characters": PARTITION_PREFIX_LENGTH,
        },
        "planted_seeds": list(PLANTED_SEEDS),
        "score": {
            "alpha": ALPHA,
            "weights": list(WEIGHTS),
            "context_lengths": [0, 1, 2, 3],
            "window_length": 4,
            "window_policy": "Overlapping; no boundary symbols or padding.",
        },
        "search": {
            "seed": SEARCH_SEED,
            "restarts": RESTARTS,
            "proposals_per_restart": PROPOSALS_PER_RESTART,
            "first_start": "Pair descending training and fitting symbol counts; ties use alphabet order.",
            "later_starts": "Shuffle alphabet positions with the search RNG.",
            "proposal_draw": "rng.sample(range(alphabet_size), 2).",
            "uphill_acceptance_draw": "Only uphill moves at positive temperature draw rng.random().",
            "temperature_schedule": "0.02 * all fitting windows, linear to zero at proposal 1999.",
            "restart_rng": "Fresh Random(408) per control; one stream across its restarts.",
            "time_limit_seconds": TIME_LIMIT_SECONDS,
        },
        "freeze": {
            "sha256": inputs["freeze"]["freeze_sha256"],
            "files": inputs["freeze"]["files"],
        },
    })
    _write_json(output / "stream-records.json", inputs["stream_records"])
    _write_json(output / "reference-metadata.json", inputs["source_metadata"])
    _write_json(output / "model-counts.json", inputs["model"].counts_record())
    for name, text in inputs["selected_streams"].items():
        _write_text(output / f"{name.replace('_', '-')}.txt", text)

    results = []
    for control in inputs["controls"]:
        control_dir = output / f"seed-{control['seed']}"
        control_dir.mkdir()
        result = _run_one_control(inputs, control, control_dir)
        _write_text(control_dir / "fitting-ciphertext.txt", result["fit_ciphertext"])
        _write_text(control_dir / "decoded-fitting.txt", result["decoded_fit"])
        _write_text(control_dir / "test-ciphertext.txt", result["test_ciphertext"])
        _write_text(control_dir / "decoded-test.txt", result["decoded_test"])
        _write_json(control_dir / "result.json", result)
        results.append({
            "seed": control["seed"],
            "accepted": result["accepted"],
            "fit_errors": result["fit_errors"],
            "test_errors": result["test_errors"],
            "complete_key_exact": result["complete_key_exact"],
            "missing_fit_labels": result["missing_fit_labels"],
            "test_labels_absent_from_fit": result["test_labels_absent_from_fit"],
            "result_file": f"seed-{control['seed']}/result.json",
        })

    accepted = all(result["accepted"] for result in results)
    _write_json(output / "result.json", {
        "schema_version": 1,
        "protocol": PROTOCOL,
        "status": "completed",
        "accepted": accepted,
        "controls": results,
        "acceptance_rule": "Observed fit assignments and every test character must be correct.",
        "scope": "Artificial permutation controls only.",
    })
    return accepted


def _parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Run the fixed space-free substitution control.")
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--fixture", type=Path)
    source.add_argument("--freeze", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv=None):
    started = time.monotonic()
    previous_handler = None
    timer_active = False
    try:
        args = _parse_args(argv)
        _check_output_path(args.output)
        if args.fixture is not None:
            inputs = _fixture_inputs(args.fixture)
            output = args.output
            output.mkdir(parents=True, exist_ok=False)
            accepted = _run_fixture(inputs, output)
        else:
            if args.freeze is None:
                raise ValueError("A freeze file is required for a real control.")
            if not hasattr(signal, "SIGALRM"):
                raise ValueError("The fixed time limit is unavailable on this platform.")
            previous_handler = signal.signal(signal.SIGALRM, _timeout_handler)
            signal.alarm(TIME_LIMIT_SECONDS)
            timer_active = True
            inputs = _reference_inputs(args.freeze)
            output = args.output
            output.mkdir(parents=True, exist_ok=False)
            accepted = _run_real(inputs, output)
        print(json.dumps({
            "status": "completed",
            "accepted": accepted,
            "elapsed_seconds": round(time.monotonic() - started, 6),
        }, sort_keys=True))
        return 0
    except Exception as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    finally:
        if timer_active:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, previous_handler)


if __name__ == "__main__":
    raise SystemExit(main())
