"""Run the fixed common visual pilot or its synthetic fixture checks."""

from collections import Counter
from datetime import datetime, timezone
import argparse
import hashlib
import json
import math
from pathlib import Path
import random
import signal
import string
import sys
import time


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.common_visual.projection import project_record
from experiments.common_visual.search import (
    SEARCH_SEED,
    UNKNOWN_WINDOW_COST,
    score_with_unknown,
    search_key,
)
from experiments.spacefree_substitution.score import NGramModel


PROTOCOL = "common-visual-pilot-v1"
ALPHABET = string.ascii_lowercase
COMMON_UNITS = (
    "o", "y", "a", "e", "ch", "sh", "k", "t", "f", "p", "ckh",
    "cth", "cfh", "cph", "d", "s", "r", "l", "i", "n", "m", "g", "q",
)
COMMON_INDEX = {unit: index for index, unit in enumerate(COMMON_UNITS)}
CONTROL_SEEDS = (408, 409, 410, 411)
SHUFFLE_SEEDS = {
    "within_word_shuffle": {"train": 508, "validation": 509, "test": 510},
    "word_order_shuffle": {"train": 608, "validation": 609, "test": 610},
}
SPLITS = ("train", "validation", "test")
SOURCES = ("ZL", "IT")
SOURCE_RELATIVE_PATHS = {
    "ZL": "data/raw/ZL3b-n.txt",
    "IT": "data/raw/IT2a-n.txt",
}
MAX_RUNTIME_SECONDS = 1800
FREEZE_PATHS = (
    "docs/plans/common-visual-pilot-v1.md",
    "experiments/common_visual/check_e2e.py",
    "experiments/common_visual/projection.py",
    "experiments/common_visual/search.py",
    "experiments/common_visual/run.py",
    "experiments/spacefree_manuscript/run.py",
    "experiments/spacefree_substitution/score.py",
    "experiments/homophonic/units.py",
    "src/voynich/reference.py",
    "src/voynich/corpus.py",
    "src/voynich/groups.py",
    "data/reference_manifest.json",
    "data/source_manifest.json",
    "data/bifolio_manifest.json",
    "reports/spacefree-manuscript-pilot-v1.json",
)
PROGRAM_PATHS = (
    "experiments/common_visual/check_e2e.py",
    "experiments/common_visual/projection.py",
    "experiments/common_visual/search.py",
    "experiments/common_visual/run.py",
    "experiments/spacefree_substitution/score.py",
    "experiments/homophonic/units.py",
    "src/voynich/reference.py",
    "src/voynich/corpus.py",
    "src/voynich/groups.py",
)


class InputError(ValueError):
    """Raised when an input does not match the fixed method."""


def _sha256(data):
    return hashlib.sha256(data).hexdigest()


def _file_sha256(path):
    try:
        return _sha256(Path(path).read_bytes())
    except OSError as error:
        raise InputError("Cannot read a required input file.") from error


def _write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def _read_json(path, label):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise InputError(f"Cannot read {label} JSON.") from error


def _check_deadline(deadline):
    if time.monotonic() >= deadline:
        raise TimeoutError("The fixed 1,800-second run limit expired.")


def _alarm_handler(_signum, _frame):
    raise TimeoutError("The fixed 1,800-second run limit expired.")


def _resolve_input(root, value):
    path = Path(value)
    return path if path.is_absolute() else root / path


def _check_fixture_text(value, label, minimum=4):
    if not isinstance(value, str) or len(value) < minimum:
        raise InputError(f"{label} must contain at least {minimum} characters.")
    if any(char not in ALPHABET for char in value):
        raise InputError(f"{label} must contain only lower-case ASCII letters.")


def _load_fixture_config(path):
    value = _read_json(path, "fixture")
    if not isinstance(value, dict) or value.get("schema_version") != 1:
        raise InputError("Fixture schema_version must be 1.")
    words = value.get("reference_training_words")
    if (not isinstance(words, list) or not words
            or any(not isinstance(word, str) or not word for word in words)):
        raise InputError("reference_training_words must be a non-empty list of words.")
    training = "".join(words)
    _check_fixture_text(training, "Reference training stream")
    fit = value.get("control_fit_plaintext")
    test = value.get("control_test_plaintext")
    _check_fixture_text(fit, "control_fit_plaintext")
    _check_fixture_text(test, "control_test_plaintext")
    manuscript_name = value.get("manuscript_fixture_path")
    if (not isinstance(manuscript_name, str) or not manuscript_name
            or Path(manuscript_name).is_absolute()
            or ".." in Path(manuscript_name).parts):
        raise InputError("manuscript_fixture_path must be a relative file name.")
    return {
        "mode": "fixture",
        "alphabet": ALPHABET,
        "reference_training_words": list(words),
        "reference_training_stream": training,
        "control_fit_plaintext": fit,
        "control_test_plaintext": test,
        "fixture_path": Path(path),
        "fixture_name": Path(path).name,
        "fixture_sha256": _file_sha256(path),
        "manuscript_fixture_path": manuscript_name,
        "reference_metadata": {
            "source": "synthetic fixture",
            "training_word_count": len(words),
            "training_character_count": len(training),
        },
    }


def _check_freeze(root, path):
    freeze = _read_json(path, "freeze")
    if not isinstance(freeze, dict) or freeze.get("schema_version") != 1:
        raise InputError("Freeze schema_version must be 1.")
    files = freeze.get("files")
    if not isinstance(files, dict) or set(files) != set(FREEZE_PATHS):
        raise InputError("Freeze files must list the 15 required paths exactly.")
    for relative in FREEZE_PATHS:
        expected = files[relative]
        if (not isinstance(expected, str) or len(expected) != 64
                or any(char not in "0123456789abcdef" for char in expected)):
            raise InputError(f"Invalid SHA-256 value for {relative}.")
        actual = _file_sha256(root / relative)
        if actual != expected:
            raise InputError(f"Freeze hash mismatch: {relative}")
    return {
        "schema_version": 1,
        "files": dict(files),
        "freeze_sha256": _file_sha256(path),
    }


def _program_hashes(root):
    return {relative: _file_sha256(root / relative) for relative in PROGRAM_PATHS}


def _initial_result(context, program_hashes):
    return {
        "schema_version": 1,
        "protocol": PROTOCOL,
        "status": "running",
        "mode": context["mode"],
        "alphabet": ALPHABET,
        "common_units": list(COMMON_UNITS),
        "freeze": (
            {"sha256": context["freeze"]["freeze_sha256"],
             "files": context["freeze"]["files"]}
            if context.get("freeze") is not None else None
        ),
        "program_hashes": program_hashes,
        "python_version": sys.version,
        "reference_provenance": context.get("reference_metadata"),
        "fixture": (
            {"name": context["fixture_name"], "sha256": context["fixture_sha256"]}
            if context["mode"] == "fixture" else None
        ),
        "calibration": {"status": "not_started", "accepted": None, "controls": []},
        "manuscript_stage": {"status": "not_started", "eligible": None, "gates": None},
        "method_limits": [
            "The common-unit list is a fixed analysis choice, not a source of letter values.",
            "The normalized labels do not keep every original case distinction.",
            "Three permutation positions have no manuscript unit and remain unused.",
            "An unknown unit gives every window that contains it a constant cost.",
            "The score is a composite cost, not a sequence probability or language confidence.",
            "The finite search does not prove a global optimum.",
            "The source stream crosses word, locus, folio, and group boundaries.",
            "Coverage shows assignment availability, not reading accuracy.",
            "The two shuffles do not give a false-positive estimate or significance test.",
            "A passing gate does not supply a complete key, language, grammar, meanings, or translation.",
        ],
    }


def _write_state(output, result, stage, error=None):
    result["status"] = "error" if error else result.get("status", "running")
    result["current_stage"] = stage
    _write_json(output / "result.json", result)
    if error is not None:
        _write_json(output / "error.json", {
            "stage": stage,
            "error_type": type(error).__name__,
            "message": str(error),
        })


def _key_for_seed(seed):
    plain = list(ALPHABET)
    random.Random(seed).shuffle(plain)
    return dict(zip(ALPHABET, plain, strict=True))


def _encode(plaintext, cipher_to_plain):
    plain_to_cipher = {plain: cipher for cipher, plain in cipher_to_plain.items()}
    if len(plain_to_cipher) != len(ALPHABET):
        raise ValueError("Control key is not a full permutation.")
    return "".join(plain_to_cipher[char] for char in plaintext)


def _map_from_positions(positions):
    if len(positions) != len(ALPHABET) or set(positions) != set(range(len(ALPHABET))):
        raise ValueError("Search returned a non-permutation key.")
    return {cipher: ALPHABET[positions[index]]
            for index, cipher in enumerate(ALPHABET)}


def _stream_hash(text):
    return _sha256(text.encode("utf-8"))


def _control_record(model, context, output, seed, deadline):
    _check_deadline(deadline)
    known = _key_for_seed(seed)
    fit_plaintext = context["control_fit_plaintext"]
    fit_ciphertext = _encode(fit_plaintext, known)
    search = search_key(model, fit_ciphertext)
    positions = list(search["key_positions"])
    fitted = _map_from_positions(positions)

    # Save the fitted key before the held-out control stream is encoded.
    _write_json(output / "calibration" / f"frozen-fit-key-seed-{seed}.json", {
        "seed": seed,
        "key_positions": positions,
        "fitted_cipher_to_plain": fitted,
        "observed_fit_labels": sorted(set(fit_ciphertext)),
    })

    _check_deadline(deadline)
    test_plaintext = context["control_test_plaintext"]
    test_ciphertext = _encode(test_plaintext, known)
    decoded_fit = "".join(fitted[symbol] for symbol in fit_ciphertext)
    decoded_test = "".join(fitted[symbol] for symbol in test_ciphertext)
    observed = set(fit_ciphertext)
    fit_errors = [index for index, (actual, expected) in enumerate(
        zip(decoded_fit, fit_plaintext, strict=True)
    ) if actual != expected]
    test_errors = [index for index, (actual, expected) in enumerate(
        zip(decoded_test, test_plaintext, strict=True)
    ) if actual != expected]
    missing = [symbol for symbol in ALPHABET if symbol not in observed]
    test_absent = [symbol for symbol in ALPHABET
                   if symbol in set(test_ciphertext) and symbol not in observed]
    unobserved_errors = [symbol for symbol in ALPHABET
                         if symbol not in observed and fitted[symbol] != known[symbol]]
    fit_assignments_correct = all(fitted[symbol] == known[symbol] for symbol in observed)
    test_positions_correct = not test_errors
    fit_score = model.score_indices(model.indices(fit_ciphertext), positions)
    test_score = model.score_indices(model.indices(test_ciphertext), positions)
    record = {
        "seed": seed,
        "known_cipher_to_plain": known,
        "fitted_cipher_to_plain": fitted,
        "key_positions": positions,
        "fit_plaintext": fit_plaintext,
        "test_plaintext": test_plaintext,
        "fit_ciphertext": fit_ciphertext,
        "test_ciphertext": test_ciphertext,
        "decoded_fit": decoded_fit,
        "decoded_test": decoded_test,
        "observed_fit_labels": [symbol for symbol in ALPHABET if symbol in observed],
        "missing_fit_labels": missing,
        "test_labels_absent_from_fit": test_absent,
        "fit_error_positions": fit_errors,
        "test_error_positions": test_errors,
        "fit_error_count": len(fit_errors),
        "test_error_count": len(test_errors),
        "observed_fit_assignments_correct": fit_assignments_correct,
        "test_positions_correct": test_positions_correct,
        "full_map_equal": fitted == known,
        "unobserved_assignment_errors": unobserved_errors,
        "fit_character_count": len(fit_ciphertext),
        "test_character_count": len(test_ciphertext),
        "fit_window_count": len(fit_ciphertext) - 3,
        "test_window_count": len(test_ciphertext) - 3,
        "fit_cost": fit_score,
        "test_cost": test_score,
        "fit_sha256": _stream_hash(fit_ciphertext),
        "test_sha256": _stream_hash(test_ciphertext),
        "passed": fit_assignments_correct and test_positions_correct,
        "search": search,
    }
    _write_json(output / "calibration" / f"control-seed-{seed}.json", record)
    return record


def _control_summary(record):
    return {
        "seed": record["seed"],
        "passed": record["passed"],
        "observed_fit_assignments_correct": record["observed_fit_assignments_correct"],
        "test_positions_correct": record["test_positions_correct"],
        "full_map_equal": record["full_map_equal"],
        "observed_fit_label_count": len(record["observed_fit_labels"]),
        "missing_fit_label_count": len(record["missing_fit_labels"]),
        "test_label_absent_from_fit_count": len(record["test_labels_absent_from_fit"]),
        "fit_error_count": record["fit_error_count"],
        "test_error_count": record["test_error_count"],
        "unobserved_assignment_error_count": len(record["unobserved_assignment_errors"]),
        "fit_character_count": record["fit_character_count"],
        "test_character_count": record["test_character_count"],
        "fit_window_count": record["fit_window_count"],
        "test_window_count": record["test_window_count"],
        "fit_cost": record["fit_cost"],
        "test_cost": record["test_cost"],
        "fit_sha256": record["fit_sha256"],
        "test_sha256": record["test_sha256"],
    }


def _run_controls(model, context, output, result, deadline):
    controls = []
    _write_json(output / "calibration" / "private.json", {"controls": controls})
    result["calibration"] = {"status": "running", "accepted": None, "controls": []}
    _write_state(output, result, "calibration")
    for seed in CONTROL_SEEDS:
        _check_deadline(deadline)
        record = _control_record(model, context, output, seed, deadline)
        controls.append(record)
        _write_json(output / "calibration" / "private.json", {"controls": controls})
        result["calibration"]["controls"] = [_control_summary(item) for item in controls]
        _write_state(output, result, "calibration")
    accepted = all(item["passed"] for item in controls)
    failed_seeds = [item["seed"] for item in controls if not item["passed"]]
    result["calibration"] = {
        "status": "passed" if accepted else "failed",
        "accepted": accepted,
        "controls": [_control_summary(item) for item in controls],
        "failed_seeds": failed_seeds,
        "failure_reason": None if accepted else "One or more fixed controls failed.",
    }
    _write_json(output / "calibration" / "private.json", {"controls": controls})
    _write_state(output, result, "calibration")
    return controls, accepted


def _prepare_reference_context(root, freeze):
    src_path = str(root / "src")
    if src_path not in sys.path:
        sys.path.insert(0, src_path)
    from voynich.reference import load_reference_partitions

    try:
        reference = load_reference_partitions(root)
    except OSError as error:
        raise InputError("Cannot read the pinned Latin reference files.") from error
    if "latin_llct" not in reference:
        raise InputError("The pinned Latin reference is not available.")
    corpus = reference["latin_llct"]
    partitions = corpus["words"]
    training_words = partitions["train"]
    training = "".join(training_words)
    fit_plaintext = "".join(partitions["validation"])[:8192]
    test_plaintext = "".join(partitions["test"])[:8192]
    if len(training) < 4 or len(fit_plaintext) != 8192 or len(test_plaintext) != 8192:
        raise InputError("The pinned reference does not meet the fixed sample sizes.")
    if any(char not in ALPHABET for char in training + fit_plaintext + test_plaintext):
        raise InputError("The pinned reference contains a character outside a-z.")
    if len(set(fit_plaintext)) != 23:
        raise InputError("The fixed validation sample does not contain 23 observed labels.")
    return {
        "mode": "real",
        "alphabet": ALPHABET,
        "reference_training_words": training_words,
        "reference_training_stream": training,
        "control_fit_plaintext": fit_plaintext,
        "control_test_plaintext": test_plaintext,
        "reference_metadata": corpus["metadata"],
        "freeze": freeze,
    }


def _new_model(context):
    return NGramModel(ALPHABET, context["reference_training_stream"])


def _classification(record):
    if not record["kind"].startswith("P"):
        return "non_paragraph"
    if not record["tokens"]:
        return "empty"
    if record["excluded_tokens"]:
        return "excluded_token"
    if "<->" in record["text_raw"] or "<~>" in record["text_raw"]:
        return "interrupted"
    return "eligible"


def _validate_record(record, index):
    label = f"Manuscript record {index}"
    if not isinstance(record, dict):
        raise InputError(f"{label} must be an object.")
    for field in ("folio", "kind", "text_raw"):
        if not isinstance(record.get(field), str):
            raise InputError(f"{label} {field} must be text.")
    if not record["folio"] or not record["kind"]:
        raise InputError(f"{label} folio and kind must not be empty.")
    tokens = record.get("tokens")
    if (not isinstance(tokens, list)
            or any(not isinstance(token, str) or not token for token in tokens)):
        raise InputError(f"{label} tokens must be a list of non-empty strings.")
    excluded = record.get("excluded_tokens")
    if isinstance(excluded, bool) or not isinstance(excluded, int) or excluded < 0:
        raise InputError(f"{label} excluded_tokens must be a non-negative integer.")
    metadata = record.get("metadata", {})
    if not isinstance(metadata, dict):
        raise InputError(f"{label} metadata must be an object.")
    for field in ("locus", "transcriber"):
        if field in record and record[field] is not None and not isinstance(record[field], str):
            raise InputError(f"{label} {field} must be text.")
    return dict(record, metadata=dict(metadata))


def _load_fixture_records(context):
    path = context["fixture_path"].parent / context["manuscript_fixture_path"]
    value = _read_json(path, "manuscript fixture")
    if not isinstance(value, dict) or value.get("schema_version") != 1:
        raise InputError("Manuscript fixture schema_version must be 1.")
    records = value.get("records")
    if not isinstance(records, list):
        raise InputError("Manuscript fixture records must be a list.")
    output = {source: [] for source in SOURCES}
    source_counts = {source: 0 for source in SOURCES}
    for index, raw in enumerate(records):
        if not isinstance(raw, dict) or raw.get("source") not in SOURCES:
            raise InputError(f"Manuscript record {index} source must be ZL or IT.")
        record = _validate_record(raw, index)
        source = record["source"]
        record.setdefault("locus", f"fixture.{source}.{source_counts[source]}")
        record.setdefault("transcriber", "synthetic")
        record["source_order"] = source_counts[source]
        source_counts[source] += 1
        output[source].append(record)
    return output, {
        "manuscript_fixture_name": path.name,
        "manuscript_fixture_sha256": _file_sha256(path),
    }


def _load_real_records(root, deadline):
    src_path = str(root / "src")
    if src_path not in sys.path:
        sys.path.insert(0, src_path)
    from voynich.corpus import parse_ivtff
    from voynich.groups import grouping_config

    config = grouping_config()
    relative_paths = {"ZL": "data/raw/ZL3b-n.txt", "IT": "data/raw/IT2a-n.txt"}
    source_hashes = {}
    for source, relative in relative_paths.items():
        _check_deadline(deadline)
        actual = _file_sha256(root / relative)
        if config["source_sha256"].get(relative) != actual:
            raise InputError(f"Manuscript source hash mismatch: {relative}")
        source_hashes[relative] = actual
    records = {}
    for source, relative in relative_paths.items():
        _check_deadline(deadline)
        parsed = parse_ivtff(root / relative, uncertain_spaces="split")
        records[source] = []
        for index, original in enumerate(parsed):
            record = dict(original)
            record["source"] = source
            record["source_order"] = index
            records[source].append(record)
        _check_deadline(deadline)
    return records, {"manuscript_source_sha256": source_hashes}


def _partition_and_project(root, source_records, source_hashes, output, deadline):
    src_path = str(root / "src")
    if src_path not in sys.path:
        sys.path.insert(0, src_path)
    from voynich.groups import group_id, split_bucket, split_name

    if source_hashes:
        if set(source_hashes) != set(SOURCE_RELATIVE_PATHS.values()):
            raise InputError("Manuscript source hashes do not match the fixed input paths.")
        for relative, digest in source_hashes.items():
            if (not isinstance(digest, str) or len(digest) != 64
                    or any(char not in "0123456789abcdef" for char in digest)):
                raise InputError("A manuscript source hash is invalid.")

    words = {
        source: {split: [] for split in SPLITS}
        for source in SOURCES
    }
    raw_words = {
        source: {split: [] for split in SPLITS}
        for source in SOURCES
    }
    counts = {
        source: {name: 0 for name in (
            "non_paragraph", "empty", "excluded_token", "interrupted", "eligible"
        )}
        for source in SOURCES
    }
    loci = {source: {"eligible": [], "excluded": []} for source in SOURCES}
    projections = []
    stream_hashes = {source: {} for source in SOURCES}
    for source in SOURCES:
        for original in source_records[source]:
            _check_deadline(deadline)
            record = _validate_record(original, original.get("source_order", 0))
            record["source"] = source
            record.setdefault("source_order", len(loci[source]["eligible"])
                              + len(loci[source]["excluded"]))
            record.setdefault("locus", f"source.{source}.{record['source_order']}")
            record.setdefault("transcriber", None)
            category = _classification(record)
            counts[source][category] += 1
            if category != "eligible":
                loci[source]["excluded"].append({
                    "source_order": record["source_order"],
                    "folio": record["folio"],
                    "locus": record["locus"],
                    "category": category,
                    "record": record,
                })
                continue

            try:
                group = group_id(record["folio"])
                partition = split_name(split_bucket(group))
            except ValueError as error:
                raise InputError("A manuscript folio has no frozen source group.") from error
            record["group"] = group
            record["partition"] = partition
            source_digest = source_hashes.get(SOURCE_RELATIVE_PATHS[source]) if source_hashes else None
            if source_hashes and source_digest is None:
                raise InputError("An eligible record has no manuscript source hash.")
            record["source_sha256"] = source_digest
            projected = project_record(record)
            word_units = [[unit["label"] for unit in word["units"]]
                          for word in projected["words"]]
            if len(word_units) != len(record["tokens"]):
                raise InputError("A source projection changed the token count.")
            words[source][partition].extend(word_units)
            raw_words[source][partition].extend(record["tokens"])
            entry = {
                "source_order": record["source_order"],
                "folio": record["folio"],
                "locus": record["locus"],
                "transcriber": record["transcriber"],
                "metadata": record.get("metadata", {}),
                "group": group,
                "partition": partition,
                "kind": record["kind"],
                "tokens": list(record["tokens"]),
                "source_sha256": source_digest,
            }
            loci[source]["eligible"].append(entry)
            projections.append({"record": record, "projection": projected})
        for split in SPLITS:
            raw_stream = "".join(raw_words[source][split])
            stream_hashes[source][split] = {
                "sha256": _stream_hash(raw_stream),
                "word_count": len(raw_words[source][split]),
                "character_count": len(raw_stream),
            }
    return {
        "words": words,
        "raw_words": raw_words,
        "exclusions": counts,
        "loci": loci,
        "projections": projections,
        "raw_stream_hashes": stream_hashes,
    }


def _check_raw_stream_hashes(root, values):
    report = _read_json(root / "reports/spacefree-manuscript-pilot-v1.json", "prior aggregate")
    try:
        expected = report["manuscript"]["streams"]
        for source in SOURCES:
            for split in SPLITS:
                actual = values["raw_stream_hashes"][source][split]["sha256"]
                wanted = expected[source][split]["sha256"]
                if actual != wanted:
                    raise InputError(f"Source cohort hash mismatch: {source} {split}.")
    except (KeyError, TypeError) as error:
        raise InputError("The prior aggregate has no fixed source cohort hashes.") from error
    return {source: {split: expected[source][split]["sha256"] for split in SPLITS}
            for source in SOURCES}


def _make_shuffles(words, deadline):
    shuffled = {name: {} for name in SHUFFLE_SEEDS}
    for name, seeds in SHUFFLE_SEEDS.items():
        for split, seed in seeds.items():
            _check_deadline(deadline)
            original = [list(word) for word in words["ZL"][split]]
            if name == "within_word_shuffle":
                result = []
                rng = random.Random(seed)
                for word in original:
                    units = list(word)
                    rng.shuffle(units)
                    result.append(units)
            else:
                result = list(original)
                random.Random(seed).shuffle(result)
            shuffled[name][split] = {
                "seed": seed,
                "words": result,
                "word_count": len(result),
                "unit_count": sum(len(word) for word in result),
                "word_multiset_preserved": Counter(tuple(word) for word in original)
                == Counter(tuple(word) for word in result),
                "unit_multiset_preserved": Counter(unit for word in original for unit in word)
                == Counter(unit for word in result for unit in word),
            }
    return shuffled


def _unit_stream(words):
    labels = [unit for word in words for unit in word]
    indices = [COMMON_INDEX.get(unit) for unit in labels]
    return labels, indices


def _stream_record(words):
    labels, indices = _unit_stream(words)
    normalized_codepoints = sum(len(unit) for unit in labels)
    encoded = json.dumps(labels, ensure_ascii=True, separators=(",", ":"))
    return {
        "unit_labels": labels,
        "unit_indices": indices,
        "unit_count": len(labels),
        "normalized_eva_codepoint_count": normalized_codepoints,
        "sha256": _stream_hash(encoded),
        "word_count": len(words),
        "word_lengths": [len(word) for word in words],
    }


def _observed_map(key_positions, labels):
    seen = set(labels)
    return {
        unit: ALPHABET[key_positions[index]]
        for index, unit in enumerate(COMMON_UNITS)
        if unit in seen
    }


def _fit_variants(model, words, shuffles, output, deadline):
    variant_words = {
        "observed": words["ZL"],
        "within_word_shuffle": {
            split: shuffles["within_word_shuffle"][split]["words"] for split in SPLITS
        },
        "word_order_shuffle": {
            split: shuffles["word_order_shuffle"][split]["words"] for split in SPLITS
        },
    }
    fits = {}
    for name, partitions in variant_words.items():
        _check_deadline(deadline)
        training = _stream_record(partitions["train"])
        if training["unit_count"] < 4:
            raise InputError("A manuscript fitting stream must contain at least four units.")
        search = search_key(model, training["unit_indices"])
        key_positions = list(search["key_positions"])
        observed_map = _observed_map(key_positions, training["unit_labels"])
        record = {
            "name": name,
            "key_positions": key_positions,
            "observed_labels": sorted(set(training["unit_labels"]) & set(COMMON_UNITS)),
            "observed_cipher_to_plain": observed_map,
            "fit_score": search["best_recomputed_cost"],
            "fit_window_count": search["window_count"],
            "unknown_window_count": search["unknown_window_count"],
            "mapped_window_count": search["mapped_window_count"],
            "training_stream": training,
            "search": search,
        }
        fits[name] = record
        _write_json(output / "manuscript" / f"frozen-fit-key-{name}.json", {
            "name": name,
            "key_positions": key_positions,
            "observed_labels": record["observed_labels"],
            "observed_cipher_to_plain": observed_map,
            "fit_score": record["fit_score"],
        })
    return fits, variant_words


def _score_words(model, words, key_positions):
    labels, indices = _unit_stream(words)
    score = score_with_unknown(model, indices, key_positions)
    mapped_units = sum(unit in COMMON_INDEX for unit in labels)
    normalized_codepoints = sum(len(unit) for unit in labels)
    mapped_codepoints = sum(len(unit) for unit in labels if unit in COMMON_INDEX)
    unknown_counts = Counter(unit for unit in labels if unit not in COMMON_INDEX)
    return {
        **score,
        "decoded_units": [None if index is None else ALPHABET[key_positions[index]]
                          for index in indices],
        "unit_count": len(labels),
        "mapped_unit_count": mapped_units,
        "unmapped_unit_count": len(labels) - mapped_units,
        "unit_coverage": mapped_units / len(labels) if labels else None,
        "normalized_eva_codepoint_count": normalized_codepoints,
        "mapped_normalized_eva_codepoint_count": mapped_codepoints,
        "eva_codepoint_coverage": (mapped_codepoints / normalized_codepoints
                                   if normalized_codepoints else None),
        "unknown_unit_counts": dict(sorted(unknown_counts.items())),
        "unknown_window_cost": UNKNOWN_WINDOW_COST,
    }


def _score_variants(model, words, variant_words, fits, output, deadline):
    scores = {name: {"ZL": {}} for name in fits}
    scores["observed"]["IT"] = {}
    for name in fits:
        key_positions = fits[name]["key_positions"]
        for split in SPLITS:
            _check_deadline(deadline)
            scores[name]["ZL"][split] = _score_words(
                model, variant_words[name][split], key_positions
            )
        _write_json(output / "manuscript" / f"scores-{name}.json", scores[name])
    observed_key = fits["observed"]["key_positions"]
    for split in SPLITS:
        _check_deadline(deadline)
        scores["observed"]["IT"][split] = _score_words(model, words["IT"][split], observed_key)
    _write_json(output / "manuscript" / "scores-observed-IT.json", scores["observed"]["IT"])
    return scores


def _baseline(model, context):
    plaintext = context["control_test_plaintext"]
    indices = model.indices(plaintext)
    positions = tuple(range(len(ALPHABET)))
    total = model.score_indices(indices, positions)
    window_count = len(indices) - 3
    return {
        "character_count": len(plaintext),
        "window_count": window_count,
        "total_cost": total,
        "mean_cost": total / window_count,
        "sha256": _stream_hash(plaintext),
    }


def _gate_metrics(words, projections, scores, baseline):
    training_labels = [unit for word in words["ZL"]["train"] for unit in word]
    observed = scores["observed"]["ZL"]["test"]
    within = scores["within_word_shuffle"]["ZL"]["test"]
    word_order = scores["word_order_shuffle"]["ZL"]["test"]
    return {
        "common_units_in_zl_training": sum(unit in set(training_labels) for unit in COMMON_UNITS),
        "all_projections_valid": all(
            item["projection"]["tokens"] == item["record"]["tokens"]
            for item in projections
        ),
        "observed_zl_test_mean": observed["mean_cost"],
        "within_word_shuffle_test_mean": within["mean_cost"],
        "word_order_shuffle_test_mean": word_order["mean_cost"],
        "latin_test_mean": baseline["mean_cost"],
        "observed_zl_test_unit_coverage": observed["unit_coverage"],
        "observed_zl_test_eva_codepoint_coverage": observed["eva_codepoint_coverage"],
    }


def _fixed_gates(metrics, controls):
    return {
        "all_four_controls": len(controls) == 4 and all(item["passed"] for item in controls),
        "all_common_units_in_training_and_projection_valid": (
            metrics["common_units_in_zl_training"] == len(COMMON_UNITS)
            and metrics["all_projections_valid"]
        ),
        "observed_zl_test_at_or_below_latin": (
            metrics["observed_zl_test_mean"] <= metrics["latin_test_mean"]
        ),
        "observed_zl_test_below_both_shuffles": (
            metrics["observed_zl_test_mean"] < metrics["within_word_shuffle_test_mean"]
            and metrics["observed_zl_test_mean"] < metrics["word_order_shuffle_test_mean"]
        ),
        "both_zl_test_coverages_at_least_99_percent": (
            metrics["observed_zl_test_unit_coverage"] >= 0.99
            and metrics["observed_zl_test_eva_codepoint_coverage"] >= 0.99
        ),
    }


def _private_record(values, words, raw_hashes, shuffles, fits, variant_words, scores):
    observed_streams = {
        source: {split: _stream_record(words[source][split]) for split in SPLITS}
        for source in SOURCES
    }
    variant_streams = {
        name: {split: _stream_record(variant_words[name][split]) for split in SPLITS}
        for name in fits
    }
    return {
        "exclusions": values["exclusions"],
        "loci": values["loci"],
        "projections": values["projections"],
        "words": words,
        "streams": observed_streams,
        "variant_streams": variant_streams,
        "source_raw_stream_hashes": raw_hashes,
        "shuffles": shuffles,
        "fits": fits,
        "scores": scores,
    }


def _load_aggregate_hashes(root):
    aggregate = _read_json(root / "reports/spacefree-manuscript-pilot-v1.json", "prior aggregate")
    try:
        return aggregate["manuscript"]["streams"]
    except (KeyError, TypeError) as error:
        raise InputError("The prior aggregate has no source cohort hashes.") from error


def _run_manuscript(root, context, model, output, result, deadline):
    result["manuscript_stage"] = {"status": "loading", "eligible": None, "gates": None}
    _write_state(output, result, "manuscript_loading")
    if context["mode"] == "fixture":
        source_records, source_info = _load_fixture_records(context)
    else:
        source_records, source_info = _load_real_records(root, deadline)
    result["manuscript_stage"]["source_provenance"] = source_info
    _write_state(output, result, "manuscript_projection")
    values = _partition_and_project(root, source_records, source_info.get("manuscript_source_sha256", {}),
                                    output, deadline)
    raw_hashes = values["raw_stream_hashes"]
    if context["mode"] == "real":
        aggregate_hashes = _check_raw_stream_hashes(root, values)
        result["manuscript_stage"]["source_cohort_hashes"] = aggregate_hashes
        result["manuscript_stage"]["source_hashes_match_prior_aggregate"] = True
    else:
        aggregate_hashes = None
        result["manuscript_stage"]["source_hashes_match_prior_aggregate"] = None

    all_training_labels = {
        unit for word in values["words"]["ZL"]["train"] for unit in word
    }
    missing_common = [unit for unit in COMMON_UNITS if unit not in all_training_labels]
    result["manuscript_stage"]["exclusions"] = values["exclusions"]
    result["manuscript_stage"]["source_stream_hashes"] = raw_hashes
    result["manuscript_stage"]["missing_common_training_units"] = missing_common
    if missing_common:
        result["manuscript_stage"].update({
            "status": "blocked",
            "eligible": False,
            "reason": "One or more fixed common units do not occur in ZL training.",
        })
        result["status"] = "blocked"
        _write_json(output / "manuscript" / "partial.json", {
            "exclusions": values["exclusions"],
            "source_info": source_info,
            "missing_common_training_units": missing_common,
            "projections": values["projections"],
            "words": values["words"],
            "source_raw_stream_hashes": raw_hashes,
        })
        _write_state(output, result, "manuscript_precondition")
        return

    result["manuscript_stage"]["status"] = "fitting"
    _write_state(output, result, "manuscript_fitting")
    shuffles = _make_shuffles(values["words"], deadline)
    _write_json(output / "manuscript" / "shuffles.json", shuffles)
    fits, variant_words = _fit_variants(model, values["words"], shuffles, output, deadline)
    # All three maps exist before any validation or test stream is scored.
    _write_json(output / "manuscript" / "fits.json", fits)
    _write_state(output, result, "manuscript_scoring")
    scores = _score_variants(model, values["words"], variant_words, fits, output, deadline)
    baseline = _baseline(model, context)
    metrics = _gate_metrics(values["words"], values["projections"], scores, baseline)
    controls = _read_json(output / "calibration" / "private.json", "calibration")['controls']
    gates = _fixed_gates(metrics, controls)
    eligible = all(gates.values())
    private = _private_record(
        values, values["words"], raw_hashes, shuffles, fits, variant_words, scores
    )
    _write_json(output / "manuscript" / "private.json", private)
    result["manuscript_stage"].update({
        "status": "run",
        "eligible": eligible,
        "gates": gates,
        "metrics": metrics,
        "latin_test_baseline": baseline,
        "source_stream_hashes": raw_hashes,
        "source_hashes_match_prior_aggregate": True if context["mode"] == "real" else None,
        "source_cohort_hashes": aggregate_hashes,
        "limitations": [
            "The two shuffles are not significance tests or false-positive estimates.",
            "IT uses the observed ZL map and is not an independent historical test.",
            "A passing gate does not identify a language or supply a translation.",
        ],
    })
    result["status"] = "complete" if eligible else "stopped"
    _write_state(output, result, "complete")


def _execution_record(started, elapsed):
    return {
        "started_utc": started,
        "elapsed_seconds": elapsed,
        "python_version": sys.version,
        "external_limit_seconds": MAX_RUNTIME_SECONDS,
        "internal_alarm_seconds": MAX_RUNTIME_SECONDS,
    }


def _parser():
    parser = argparse.ArgumentParser(description="Run the fixed common visual pilot.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--freeze", metavar="FILE")
    mode.add_argument("--fixture", metavar="FILE")
    parser.add_argument("--output", required=True, metavar="NEW_DIRECTORY")
    return parser


def main(argv=None):
    args = _parser().parse_args(argv)
    root = ROOT
    output = _resolve_input(Path.cwd(), args.output)
    if output.exists():
        print("error: Output directory already exists.", file=sys.stderr)
        return 2

    try:
        if args.freeze:
            freeze_path = _resolve_input(root, args.freeze)
            freeze = _check_freeze(root, freeze_path)
            context = {"mode": "real", "freeze": freeze}
        else:
            fixture_path = _resolve_input(Path.cwd(), args.fixture)
            context = _load_fixture_config(fixture_path)
        program_hashes = _program_hashes(root)
    except (InputError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    try:
        output.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        print("error: Output directory already exists.", file=sys.stderr)
        return 2
    except OSError as error:
        print("error: Cannot create the output directory.", file=sys.stderr)
        return 2

    result = _initial_result(context, program_hashes)
    _write_state(output, result, "initializing")
    started_at = datetime.now(timezone.utc).isoformat()
    started_monotonic = time.monotonic()
    deadline = started_monotonic + MAX_RUNTIME_SECONDS
    signal_installed = hasattr(signal, "SIGALRM")
    if signal_installed:
        signal.signal(signal.SIGALRM, _alarm_handler)
        signal.alarm(MAX_RUNTIME_SECONDS)
    stage = "reference"
    _write_state(output, result, stage)
    try:
        if context["mode"] == "real":
            context.update(_prepare_reference_context(root, context["freeze"]))
        result["reference_provenance"] = context["reference_metadata"]
        _write_state(output, result, stage)
        model = _new_model(context)
        result["model"] = {
            "alphabet": ALPHABET,
            "training_word_count": len(context["reference_training_words"]),
            "training_character_count": len(context["reference_training_stream"]),
            "training_stream_sha256": _stream_hash(context["reference_training_stream"]),
            "alpha": 0.1,
            "weights": [0.1, 0.2, 0.3, 0.4],
            "context_lengths": [0, 1, 2, 3],
            "search_seed": SEARCH_SEED,
            "restarts": 8,
            "proposals_per_restart": 2000,
        }
        _write_state(output, result, "calibration")
        controls, accepted = _run_controls(model, context, output, result, deadline)
        if not accepted:
            result["manuscript_stage"] = {
                "status": "blocked",
                "eligible": False,
                "gates": None,
                "reason": "At least one fixed artificial control failed.",
            }
            result["status"] = "blocked"
            _write_state(output, result, "calibration_gate")
        else:
            stage = "manuscript_loading"
            _run_manuscript(root, context, model, output, result, deadline)
        elapsed = time.monotonic() - started_monotonic
        _write_json(output / "execution.json", _execution_record(started_at, elapsed))
        return 0
    except Exception as error:
        error_stage = result.get("current_stage") or stage
        result["status"] = "error"
        if error_stage.startswith("manuscript"):
            result["manuscript_stage"]["status"] = "error"
            result["manuscript_stage"]["eligible"] = False
        elif (error_stage == "calibration"
              and result["calibration"]["status"] in {"running", "not_started"}):
            result["calibration"]["status"] = "error"
            result["calibration"]["accepted"] = False
        _write_state(output, result, error_stage, error)
        elapsed = time.monotonic() - started_monotonic
        _write_json(output / "execution.json", _execution_record(started_at, elapsed))
        print(f"error: {error}", file=sys.stderr)
        return 1
    finally:
        if signal_installed:
            signal.alarm(0)


if __name__ == "__main__":
    raise SystemExit(main())
