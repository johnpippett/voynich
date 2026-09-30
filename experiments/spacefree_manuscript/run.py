"""Run the fixed space-free substitution pilot or a small synthetic fixture."""

import argparse
from collections import Counter
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import random
import signal
import string
import sys
import time


FREEZE_PATHS = (
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
)
ALPHABET = string.ascii_lowercase
CONTROL_SEEDS = (408, 409, 410, 411)
WEIGHTS = (0.1, 0.2, 0.3, 0.4)
SHUFFLE_SEEDS = {
    "within_word_shuffle": {"train": 508, "validation": 509, "test": 510},
    "word_order_shuffle": {"train": 608, "validation": 609, "test": 610},
}
MAX_RUNTIME_SECONDS = 1800


class InputError(ValueError):
    """Raised when input does not match the fixed command schema."""


def _sha256(data):
    return hashlib.sha256(data).hexdigest()


def _file_sha256(path):
    return _sha256(Path(path).read_bytes())


def _check_deadline(deadline):
    if time.monotonic() >= deadline:
        raise TimeoutError("The fixed 1,800-second run limit expired.")


def _write_json(path, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def _read_json(path, label):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise InputError(f"Cannot read {label} JSON: {error}") from error


def _load_scorer(root):
    path = root / "experiments/spacefree_substitution/score.py"
    spec = importlib.util.spec_from_file_location("spacefree_fixed_score", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Cannot load the fixed scorer.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _check_alphabet(alphabet, label):
    if (not isinstance(alphabet, str) or len(alphabet) < 2
            or any(char not in string.ascii_lowercase for char in alphabet)
            or len(set(alphabet)) != len(alphabet)):
        raise InputError(f"{label} must contain unique lower-case ASCII letters.")


def _check_text(value, alphabet, label, minimum=0):
    if not isinstance(value, str) or len(value) < minimum:
        raise InputError(f"{label} must be text with at least {minimum} characters.")
    if set(value).difference(alphabet):
        raise InputError(f"{label} contains a character outside its alphabet.")


def _load_fixture_config(path):
    value = _read_json(path, "fixture")
    if not isinstance(value, dict) or value.get("schema_version") != 1:
        raise InputError("Fixture schema_version must be 1.")
    alphabet = value.get("alphabet")
    _check_alphabet(alphabet, "Fixture alphabet")
    words = value.get("reference_training_words")
    if (not isinstance(words, list) or not words
            or any(not isinstance(word, str) or not word for word in words)):
        raise InputError("reference_training_words must be a non-empty list of words.")
    training = "".join(words)
    _check_text(training, alphabet, "Reference training stream", minimum=4)
    fit = value.get("control_fit_plaintext")
    test = value.get("control_test_plaintext")
    _check_text(fit, alphabet, "control_fit_plaintext", minimum=4)
    _check_text(test, alphabet, "control_test_plaintext", minimum=4)
    manuscript_path = value.get("manuscript_fixture_path")
    if not isinstance(manuscript_path, str) or not manuscript_path:
        raise InputError("manuscript_fixture_path must be a non-empty path string.")
    return {
        "mode": "fixture",
        "alphabet": alphabet,
        "reference_training_words": words,
        "reference_training_stream": training,
        "control_fit_plaintext": fit,
        "control_test_plaintext": test,
        "manuscript_fixture_path": manuscript_path,
        "fixture_path": Path(path).resolve(),
        "fixture_sha256": _file_sha256(path),
        "reference_metadata": {"source": "synthetic fixture", "training_word_count": len(words)},
    }


def _check_freeze(root, path):
    freeze = _read_json(path, "freeze")
    if not isinstance(freeze, dict) or freeze.get("schema_version") != 1:
        raise InputError("Freeze schema_version must be 1.")
    files = freeze.get("files")
    if not isinstance(files, dict) or set(files) != set(FREEZE_PATHS):
        raise InputError("Freeze files must list the ten required paths exactly.")
    for relative in FREEZE_PATHS:
        expected = files[relative]
        if (not isinstance(expected, str) or len(expected) != 64
                or any(char not in "0123456789abcdef" for char in expected)):
            raise InputError(f"Invalid SHA-256 value for {relative}.")
        path_on_disk = root / relative
        try:
            actual = _file_sha256(path_on_disk)
        except OSError as error:
            raise InputError(f"Cannot read frozen file {relative}: {error}") from error
        if actual != expected:
            raise InputError(f"Freeze hash mismatch: {relative}")
    return {
        "schema_version": 1,
        "files": dict(files),
        "freeze_sha256": _file_sha256(path),
        "freeze_path": Path(path).resolve(),
    }


def _prepare_real_context(root, freeze, deadline):
    _check_deadline(deadline)
    sys.path.insert(0, str(root / "src"))
    from voynich.reference import load_reference_partitions

    reference = load_reference_partitions(root)
    _check_deadline(deadline)
    if "latin_llct" not in reference:
        raise RuntimeError("The pinned Latin LLCT reference is not available.")
    partitions = reference["latin_llct"]["words"]
    training_words = partitions["train"]
    training_stream = "".join(training_words)
    fit_plaintext = "".join(partitions["validation"])[:8192]
    test_plaintext = "".join(partitions["test"])[:8192]
    if len(training_stream) < 4 or len(fit_plaintext) != 8192 or len(test_plaintext) != 8192:
        raise RuntimeError("The pinned reference partitions do not meet the fixed sample sizes.")
    if set(training_stream + fit_plaintext + test_plaintext).difference(ALPHABET):
        raise RuntimeError("The pinned Latin reference contains a symbol outside a-z.")
    return {
        "mode": "real",
        "alphabet": ALPHABET,
        "reference_training_words": training_words,
        "reference_training_stream": training_stream,
        "control_fit_plaintext": fit_plaintext,
        "control_test_plaintext": test_plaintext,
        "freeze": freeze,
        "reference_metadata": reference["latin_llct"]["metadata"],
        "reference_partitions": partitions,
    }


def _encode(plaintext, cipher_to_plain, alphabet):
    plain_to_cipher = {plain: cipher for cipher, plain in cipher_to_plain.items()}
    if len(plain_to_cipher) != len(alphabet):
        raise ValueError("Control key is not a full permutation.")
    return "".join(plain_to_cipher[char] for char in plaintext)


def _key_for_seed(alphabet, seed):
    shuffled_plain = list(alphabet)
    random.Random(seed).shuffle(shuffled_plain)
    return dict(zip(alphabet, shuffled_plain, strict=True))


def _map_from_positions(alphabet, positions):
    if len(positions) != len(alphabet) or set(positions) != set(range(len(alphabet))):
        raise ValueError("Search returned a non-permutation key.")
    return {cipher: alphabet[positions[index]] for index, cipher in enumerate(alphabet)}


def _score_plain_window(model, plaintext):
    symbols = model.indices(plaintext)
    size = len(model.alphabet)
    index = (((symbols[0] * size + symbols[1]) * size + symbols[2]) * size + symbols[3])
    return model.window_costs[index]


def _stream_hash(value):
    return _sha256(value.encode("utf-8"))


def _run_controls(context, model, scorer, output, deadline):
    alphabet = context["alphabet"]
    fit_plaintext = context["control_fit_plaintext"]
    test_plaintext = context["control_test_plaintext"]
    controls = []
    for seed in CONTROL_SEEDS:
        _check_deadline(deadline)
        known = _key_for_seed(alphabet, seed)
        fit_ciphertext = _encode(fit_plaintext, known, alphabet)
        search = scorer.search_key(model, fit_ciphertext)
        positions = search["key_positions"]
        fitted = _map_from_positions(alphabet, positions)
        _write_json(output / "calibration" / f"frozen-fit-key-seed-{seed}.json", {
            "seed": seed,
            "key_positions": positions,
            "fitted_cipher_to_plain": fitted,
        })
        _check_deadline(deadline)
        test_ciphertext = _encode(test_plaintext, known, alphabet)
        decoded_fit = "".join(fitted[char] for char in fit_ciphertext)
        decoded_test = "".join(fitted[char] for char in test_ciphertext)
        fit_errors = [index for index, (actual, expected) in enumerate(
            zip(decoded_fit, fit_plaintext, strict=True)) if actual != expected]
        test_errors = [index for index, (actual, expected) in enumerate(
            zip(decoded_test, test_plaintext, strict=True)) if actual != expected]
        fit_labels = set(fit_ciphertext)
        test_labels = set(test_ciphertext)
        missing_fit = [symbol for symbol in alphabet if symbol not in fit_labels]
        absent_test = [symbol for symbol in alphabet if symbol in test_labels and symbol not in fit_labels]
        observed_fit_correct = all(known[symbol] == fitted[symbol] for symbol in fit_labels)
        test_positions_correct = not test_errors
        full_map_equal = known == fitted
        passed = observed_fit_correct and test_positions_correct
        record = {
            "seed": seed,
            "known_cipher_to_plain": known,
            "fitted_cipher_to_plain": fitted,
            "key_positions": positions,
            "full_map_equal": full_map_equal,
            "observed_fit_assignments_correct": observed_fit_correct,
            "test_positions_correct": test_positions_correct,
            "passed": passed,
            "fit_plaintext": fit_plaintext,
            "fit_ciphertext": fit_ciphertext,
            "test_plaintext": test_plaintext,
            "test_ciphertext": test_ciphertext,
            "decoded_fit": decoded_fit,
            "decoded_test": decoded_test,
            "observed_fit_labels": [symbol for symbol in alphabet if symbol in fit_labels],
            "missing_fit_labels": missing_fit,
            "test_labels_absent_from_fit": absent_test,
            "fit_error_positions": fit_errors,
            "fit_error_count": len(fit_errors),
            "test_error_positions": test_errors,
            "test_error_count": len(test_errors),
            "fit_character_count": len(fit_ciphertext),
            "test_character_count": len(test_ciphertext),
            "fit_window_count": search["window_count"],
            "test_window_count": len(test_ciphertext) - 3,
            "fit_cost": search["best_recomputed_cost"],
            "test_cost": model.score_indices(model.indices(test_ciphertext), positions),
            "fit_sha256": _stream_hash(fit_ciphertext),
            "test_sha256": _stream_hash(test_ciphertext),
            "search": search,
        }
        controls.append(record)
        _write_json(output / "calibration" / f"control-seed-{seed}.json", record)
        _check_deadline(deadline)
    return controls


def _control_summary(item):
    return {
        "seed": item["seed"],
        "passed": item["passed"],
        "observed_fit_assignments_correct": item["observed_fit_assignments_correct"],
        "test_positions_correct": item["test_positions_correct"],
        "full_map_equal": item["full_map_equal"],
        "missing_fit_label_count": len(item["missing_fit_labels"]),
        "test_label_absent_from_fit_count": len(item["test_labels_absent_from_fit"]),
        "fit_error_count": item["fit_error_count"],
        "test_error_count": item["test_error_count"],
        "fit_character_count": item["fit_character_count"],
        "test_character_count": item["test_character_count"],
        "fit_window_count": item["fit_window_count"],
        "test_window_count": item["test_window_count"],
        "fit_cost": item["fit_cost"],
        "test_cost": item["test_cost"],
        "fit_sha256": item["fit_sha256"],
        "test_sha256": item["test_sha256"],
    }


def _initial_result(context, program_hashes):
    return {
        "schema_version": 1,
        "protocol": "spacefree-manuscript-pilot-v1",
        "status": "running",
        "mode": context["mode"],
        "alphabet": context["alphabet"],
        "freeze": (
            {
                "sha256": context["freeze"]["freeze_sha256"],
                "files": context["freeze"]["files"],
            }
            if context.get("freeze") is not None else None
        ),
        "program_hashes": program_hashes,
        "calibration": {"status": "running", "accepted": None, "controls": []},
        "manuscript_stage": {"status": "not_started", "eligible": None, "gates": None},
        "method_limits": [
            "This is an exploratory Latin test with prior source exposure.",
            "EVA code points describe written shapes and need not be letters.",
            "The parser lowercases EVA connection notation. This pilot does not keep that case distinction.",
            "Smoothing defines costs for absent reference labels but gives no historical support.",
            "The finite search does not prove a global optimum.",
            "The character stream crosses word, line, folio, and group boundaries.",
            "A passing gate does not show word boundaries, grammar, meanings, a key, or a translation.",
        ],
    }


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


def _validate_manuscript_fixture(value, alphabet):
    if not isinstance(value, dict) or value.get("schema_version") != 1:
        raise InputError("Manuscript fixture schema_version must be 1.")
    records = value.get("loci")
    if not isinstance(records, list):
        raise InputError("Manuscript fixture loci must be a list.")
    for index, record in enumerate(records):
        label = f"Manuscript locus {index}"
        if not isinstance(record, dict):
            raise InputError(f"{label} must be an object.")
        if record.get("source") not in {"ZL", "IT"}:
            raise InputError(f"{label} source must be ZL or IT.")
        if not isinstance(record.get("folio"), str) or not record["folio"]:
            raise InputError(f"{label} folio must be a non-empty string.")
        if not isinstance(record.get("kind"), str):
            raise InputError(f"{label} kind must be a string.")
        words = record.get("tokens")
        if (not isinstance(words, list)
                or any(not isinstance(word, str) for word in words)):
            raise InputError(f"{label} tokens must be a list of strings.")
        for word in words:
            if word and (set(word).difference(alphabet)
                         or any(char not in string.ascii_lowercase for char in word)):
                raise InputError(f"{label} has a token outside the fixture alphabet.")
        excluded = record.get("excluded_tokens")
        if not isinstance(excluded, int) or isinstance(excluded, bool) or excluded < 0:
            raise InputError(f"{label} excluded_tokens must be a non-negative integer.")
        if not isinstance(record.get("text_raw"), str):
            raise InputError(f"{label} text_raw must be a string.")


def _make_internal_records(source_records, source_name):
    records = []
    for index, original in enumerate(source_records):
        if source_name == "fixture":
            record = dict(original)
            record.setdefault("locus", f"fixture.{index}")
            record.setdefault("transcriber", "synthetic")
            record.setdefault("metadata", {})
        else:
            record = {
                "folio": original["folio"],
                "locus": original["locus"],
                "transcriber": original["transcriber"],
                "metadata": dict(original["metadata"]),
                "kind": original["kind"],
                "tokens": list(original["tokens"]),
                "excluded_tokens": original["excluded_tokens"],
                "text_raw": original["text_raw"],
            }
        record["source_order"] = index
        records.append(record)
    return records


def _load_manuscript_records(root, context):
    deadline = context["deadline"]
    _check_deadline(deadline)
    if context["mode"] == "fixture":
        original_path = context["fixture_path"].parent / context["manuscript_fixture_path"]
        value = _read_json(original_path, "manuscript fixture")
        _validate_manuscript_fixture(value, context["alphabet"])
        digest = _file_sha256(original_path)
        _check_deadline(deadline)
        records = _make_internal_records(value["loci"], "fixture")
        return {"ZL": [r for r in records if r["source"] == "ZL"],
                "IT": [r for r in records if r["source"] == "IT"]}, {
                    "manuscript_fixture_sha256": digest,
                    "manuscript_fixture_name": original_path.name,
                }

    sys.path.insert(0, str(root / "src"))
    from voynich.corpus import parse_ivtff
    from voynich.groups import grouping_config

    config = grouping_config()
    source_paths = {
        "ZL": "data/raw/ZL3b-n.txt",
        "IT": "data/raw/IT2a-n.txt",
    }
    expected_hashes = config["source_sha256"]
    source_hashes = {}
    for source, relative in source_paths.items():
        _check_deadline(deadline)
        actual = _file_sha256(root / relative)
        expected = expected_hashes.get(relative)
        if actual != expected:
            raise InputError(f"Manuscript source hash mismatch: {relative}")
        source_hashes[relative] = actual
    _check_deadline(deadline)
    by_source = {}
    for source, relative in source_paths.items():
        parsed = parse_ivtff(root / relative, uncertain_spaces="split")
        by_source[source] = _make_internal_records(parsed, "real")
        _check_deadline(deadline)
    return by_source, {"manuscript_source_sha256": source_hashes}


def _partition_records(root, by_source, alphabet, deadline):
    sys.path.insert(0, str(root / "src"))
    from voynich.groups import group_id, split_bucket, split_name

    output = {}
    for source, records in by_source.items():
        counts = {name: 0 for name in (
            "non_paragraph", "empty", "excluded_token", "interrupted", "eligible")}
        partitions = {
            split: {"words": [], "records": []}
            for split in ("train", "validation", "test")
        }
        eligible = []
        for original in records:
            _check_deadline(deadline)
            record = {
                "folio": original["folio"],
                "locus": original["locus"],
                "transcriber": original["transcriber"],
                "metadata": dict(original["metadata"]),
                "kind": original["kind"],
                "tokens": list(original["tokens"]),
                "excluded_tokens": original["excluded_tokens"],
                "text_raw": original["text_raw"],
                "source_order": original["source_order"],
            }
            category = _classification(record)
            counts[category] += 1
            if category != "eligible":
                continue
            group = group_id(record["folio"])
            partition = split_name(split_bucket(group))
            destination = partitions[partition]
            start = sum(len(word) for word in destination["words"])
            offsets = []
            cursor = start
            for word in record["tokens"]:
                offsets.append({"start": cursor, "end": cursor + len(word)})
                cursor += len(word)
            output_record = {
                "source_order": record["source_order"],
                "folio": record["folio"],
                "locus": record["locus"],
                "transcriber": record["transcriber"],
                "metadata": record["metadata"],
                "group": group,
                "partition": partition,
                "kind": record["kind"],
                "token_count": len(record["tokens"]),
                "token_lengths": [len(word) for word in record["tokens"]],
                "token_offsets": offsets,
                "stream_offset_start": start,
                "stream_offset_end": cursor,
                "character_count": cursor - start,
                "excluded_token_count": record["excluded_tokens"],
                "tokens": record["tokens"],
            }
            destination["records"].append(output_record)
            destination["words"].extend(record["tokens"])
            eligible.append(output_record)
        output[source] = {"exclusions": counts, "partitions": partitions, "eligible": eligible}
    return output


def _stream_record(words):
    stream = "".join(words)
    return {
        "text": stream,
        "sha256": _stream_hash(stream),
        "character_count": len(stream),
        "codepoint_counts": dict(sorted(Counter(stream).items())),
        "word_count": len(words),
        "word_lengths": [len(word) for word in words],
    }


def _make_shuffles(words_by_split, deadline):
    output = {}
    for name, seeds in SHUFFLE_SEEDS.items():
        control = {}
        for split, seed in seeds.items():
            _check_deadline(deadline)
            original = list(words_by_split[split])
            shuffled = list(original)
            rng = random.Random(seed)
            if name == "within_word_shuffle":
                shuffled = []
                for word in original:
                    chars = list(word)
                    rng.shuffle(chars)
                    shuffled.append("".join(chars))
            else:
                rng.shuffle(shuffled)
            control[split] = {
                "seed": seed,
                "original_words": original,
                "words": shuffled,
                "stream": _stream_record(shuffled),
                "word_multiset_preserved": Counter(original) == Counter(shuffled),
                "total_length_preserved": sum(map(len, original)) == sum(map(len, shuffled)),
                "character_multisets_preserved": (
                    [Counter(word) for word in original] == [Counter(word) for word in shuffled]
                    if name == "within_word_shuffle" else None
                ),
            }
        output[name] = control
    return output


def _score_stream(model, stream, key, alphabet, deadline):
    decoded = "".join(key.get(symbol, "?") for symbol in stream)
    unknown = Counter(symbol for symbol in stream if symbol not in key)
    window_count = max(0, len(stream) - 3)
    unknown_windows = 0
    total_cost = 0.0
    penalty = math.log2(len(alphabet))
    for start in range(window_count):
        if start % 1024 == 0:
            _check_deadline(deadline)
        source_window = stream[start:start + 4]
        if any(symbol not in key for symbol in source_window):
            unknown_windows += 1
            total_cost += penalty
        else:
            total_cost += _score_plain_window(model, decoded[start:start + 4])
    mapped_count = len(stream) - sum(unknown.values())
    return {
        "decoded_text": decoded,
        "character_count": len(stream),
        "mapped_character_count": mapped_count,
        "unmapped_character_count": len(stream) - mapped_count,
        "mapped_coverage": mapped_count / len(stream) if stream else None,
        "unknown_character_counts": dict(sorted(unknown.items())),
        "window_count": window_count,
        "fully_mapped_window_count": window_count - unknown_windows,
        "unknown_window_count": unknown_windows,
        "unknown_window_cost": penalty,
        "total_cost": total_cost,
        "mean_cost": total_cost / window_count if window_count else None,
    }


def _fit_variants(model, scorer, alphabet, streams, shuffles, output, deadline):
    variant_streams = {
        "observed": streams["ZL"],
        "within_word_shuffle": {
            split: shuffles["within_word_shuffle"][split]["stream"]["text"]
            for split in ("train", "validation", "test")
        },
        "word_order_shuffle": {
            split: shuffles["word_order_shuffle"][split]["stream"]["text"]
            for split in ("train", "validation", "test")
        },
    }
    fits = {}
    for name, partition_streams in variant_streams.items():
        _check_deadline(deadline)
        training = partition_streams["train"]
        search = scorer.search_key(model, training)
        positions = search["key_positions"]
        full_map = _map_from_positions(alphabet, positions)
        observed_labels = [symbol for symbol in alphabet if symbol in set(training)]
        observed_map = {symbol: full_map[symbol] for symbol in observed_labels}
        fits[name] = {
            "training_stream": _stream_record([training]),
            "key_positions": positions,
            "full_permutation": full_map,
            "observed_labels": observed_labels,
            "observed_cipher_to_plain": observed_map,
            "fit_window_count": search["window_count"],
            "fit_cost": search["best_recomputed_cost"],
            "search": search,
        }
    _write_json(output / "manuscript" / "fitted-keys.json", {
        name: {"key_positions": fit["key_positions"],
               "full_permutation": fit["full_permutation"],
               "observed_labels": fit["observed_labels"],
               "observed_cipher_to_plain": fit["observed_cipher_to_plain"]}
        for name, fit in fits.items()
    })
    return fits, variant_streams


def _score_manuscript(model, alphabet, streams, shuffles, fits,
                      latin_test, controls, deadline):
    scores = {name: {"ZL": {}} for name in (
        "observed", "within_word_shuffle", "word_order_shuffle")}
    scores["identity"] = {"ZL": {}}
    for name in ("observed", "within_word_shuffle", "word_order_shuffle"):
        for split in ("train", "validation", "test"):
            if name == "observed":
                text = streams["ZL"][split]
            else:
                text = shuffles[name][split]["stream"]["text"]
            mapping = fits[name]["observed_cipher_to_plain"]
            scores[name]["ZL"][split] = _score_stream(
                model, text, mapping, alphabet, deadline
            )

    scores["observed"]["IT"] = {
        split: _score_stream(
            model, streams["IT"][split],
            fits["observed"]["observed_cipher_to_plain"], alphabet, deadline,
        )
        for split in ("train", "validation", "test")
    }

    identity = {
        symbol: symbol for symbol in fits["observed"]["observed_labels"]
    }
    scores["identity"]["ZL"] = {
        split: _score_stream(
            model, streams["ZL"][split], identity, alphabet, deadline
        )
        for split in ("train", "validation", "test")
    }
    latin_baseline = _score_stream(
        model, latin_test, {symbol: symbol for symbol in alphabet}, alphabet, deadline
    )
    observed_test = scores["observed"]["ZL"]["test"]
    within_test = scores["within_word_shuffle"]["ZL"]["test"]
    order_test = scores["word_order_shuffle"]["ZL"]["test"]
    identity_test = scores["identity"]["ZL"]["test"]
    gates = {
        "all_four_controls": len(controls) == len(CONTROL_SEEDS)
        and all(item["passed"] for item in controls),
        "observed_at_or_below_latin": observed_test["mean_cost"] <= latin_baseline["mean_cost"],
        "below_both_shuffle_and_identity": observed_test["mean_cost"] < min(
            within_test["mean_cost"], order_test["mean_cost"], identity_test["mean_cost"]),
        "mapped_coverage_at_least_99_percent": observed_test["mapped_coverage"] >= 0.99,
    }
    return scores, latin_baseline, gates


def _program_hashes(root, fixture_hash=None, manuscript_hash=None):
    paths = (
        "experiments/spacefree_manuscript/run.py",
        "experiments/spacefree_manuscript/check_e2e.py",
        "experiments/spacefree_substitution/score.py",
        "src/voynich/reference.py",
        "src/voynich/corpus.py",
        "src/voynich/groups.py",
    )
    hashes = {relative: _file_sha256(root / relative) for relative in paths}
    if fixture_hash is not None:
        hashes["fixture_json_sha256"] = fixture_hash
    if manuscript_hash is not None:
        hashes["manuscript_fixture_sha256"] = manuscript_hash
    return hashes


def _record_error(output, stage, error):
    _write_json(output / "error.json", {
        "stage": stage,
        "error_type": type(error).__name__,
        "message": str(error),
    })


def _execute(root, output, context):
    deadline = context["deadline"]
    output.mkdir(parents=True, exist_ok=False)
    _write_json(output / "execution.json", {
        "python_version": sys.version,
        "deterministic": True,
    })
    result = _initial_result(context, {})
    result["reference"] = {
        "training_character_count": len(context["reference_training_stream"]),
        "training_distinct_label_count": len(set(context["reference_training_stream"])),
        "control_fit_character_count": len(context["control_fit_plaintext"]),
        "control_fit_distinct_label_count": len(set(context["control_fit_plaintext"])),
        "control_test_character_count": len(context["control_test_plaintext"]),
        "control_test_distinct_label_count": len(set(context["control_test_plaintext"])),
        "metadata": context["reference_metadata"],
    }
    _write_json(output / "result.json", result)
    try:
        _check_deadline(deadline)
        program_hashes = _program_hashes(root, context.get("fixture_sha256"), None)
        result["program_hashes"] = program_hashes
        _write_json(output / "result.json", result)
        scorer = _load_scorer(root)
        model = scorer.NGramModel(
            context["alphabet"], context["reference_training_stream"]
        )
        _check_deadline(deadline)
        _write_json(output / "calibration" / "reference-counts.json", model.counts_record())
        controls = _run_controls(context, model, scorer, output, deadline)
        accepted = all(item["passed"] for item in controls)
        _write_json(output / "calibration" / "private.json", {
            "alphabet": context["alphabet"],
            "reference_training_stream": context["reference_training_stream"],
            "reference_training_words": context["reference_training_words"],
            "control_fit_plaintext": context["control_fit_plaintext"],
            "control_test_plaintext": context["control_test_plaintext"],
            "controls": controls,
        })
        result["calibration"] = {
            "status": "passed" if accepted else "failed",
            "accepted": accepted,
            "controls": [_control_summary(item) for item in controls],
            "settings": {
                "search_seed": 408,
                "control_key_seeds": list(CONTROL_SEEDS),
                "restart_count": 8,
                "proposals_per_restart": 2000,
                "fit_sample_policy": "Use the complete supplied fit stream.",
                "test_sample_policy": "Use the complete supplied test stream.",
            },
        }
        result["status"] = "calibration_failed" if not accepted else "running"
        if not accepted:
            result["manuscript_stage"] = {
                "status": "blocked", "eligible": None, "gates": None,
            }
            _write_json(output / "result.json", result)
            return 0
        result["manuscript_stage"] = {
            "status": "not_started", "eligible": None, "gates": None,
        }
        _write_json(output / "result.json", result)

        _check_deadline(deadline)
        by_source, source_hashes = _load_manuscript_records(root, context)
        _validate_manuscript_records(
            by_source, context["alphabet"], context["deadline"]
        )
        _check_deadline(deadline)
        partitioned = _partition_records(
            root, by_source, context["alphabet"], deadline
        )
        words = {
            source: {
                split: list(partitioned[source]["partitions"][split]["words"])
                for split in ("train", "validation", "test")
            }
            for source in ("ZL", "IT")
        }
        streams = {
            source: {split: "".join(words[source][split])
                     for split in ("train", "validation", "test")}
            for source in ("ZL", "IT")
        }
        for source in ("ZL", "IT"):
            for split in ("train", "validation", "test"):
                if len(streams[source][split]) < 4:
                    raise InputError(f"{source} {split} stream has fewer than four characters.")
        shuffles = _make_shuffles(words["ZL"], deadline)
        fits, variant_streams = _fit_variants(
            model, scorer, context["alphabet"], streams, shuffles, output, deadline
        )
        _check_deadline(deadline)
        scores, latin_baseline, gates = _score_manuscript(
            model, context["alphabet"], streams, shuffles, fits,
            context["control_test_plaintext"], controls, deadline,
        )
        stream_records = {
            source: {split: _stream_record(words[source][split])
                     for split in ("train", "validation", "test")}
            for source in ("ZL", "IT")
        }
        _write_json(output / "manuscript" / "private.json", {
            "source_hashes": source_hashes,
            "exclusions": {source: partitioned[source]["exclusions"] for source in ("ZL", "IT")},
            "loci": {source: {"eligible": partitioned[source]["eligible"],
                              "partitions": partitioned[source]["partitions"]}
                     for source in ("ZL", "IT")},
            "words": words,
            "streams": stream_records,
            "shuffles": {
                "within_word": shuffles["within_word_shuffle"],
                "word_order": shuffles["word_order_shuffle"],
            },
            "fits": fits,
            "full_permutations": {name: fit["key_positions"] for name, fit in fits.items()},
            "scores": scores,
            "latin_test_baseline": latin_baseline,
            "boundary_policy": "Join accepted words in file order within each partition, without spaces. Streams can cross token, locus, folio, and group boundaries.",
            "unseen_sign_policy": "Use ? for any sign absent from the fit-observed map. Never use its latent full-permutation assignment.",
        })
        result["source_hashes"] = source_hashes
        result["manuscript_stage"] = {
            "status": "run",
            "eligible": all(gates.values()),
            "gates": gates,
            "latin_test_baseline": latin_baseline,
            "observed_zl_test": scores["observed"]["ZL"]["test"],
            "within_word_zl_test": scores["within_word_shuffle"]["ZL"]["test"],
            "word_order_zl_test": scores["word_order_shuffle"]["ZL"]["test"],
            "identity_zl_test": scores["identity"]["ZL"]["test"],
            "it_uses_observed_zl_map_without_refitting": True,
        }
        result["status"] = "complete"
        _write_json(output / "result.json", result)
        return 0
    except KeyboardInterrupt as error:
        _record_error(output, "interrupted", error)
        print("error: run interrupted; partial evidence remains", file=sys.stderr)
        return 130
    except Exception as error:
        _record_error(output, "runtime", error)
        print(f"error: {error}", file=sys.stderr)
        return 1


def _validate_manuscript_records(by_source, alphabet, deadline):
    for source, records in by_source.items():
        for index, record in enumerate(records):
            _check_deadline(deadline)
            if not isinstance(record.get("kind"), str):
                raise InputError(f"{source} locus {index} has no valid kind.")
            if not isinstance(record.get("tokens"), list):
                raise InputError(f"{source} locus {index} has no valid token list.")
            if not isinstance(record.get("excluded_tokens"), int):
                raise InputError(f"{source} locus {index} has no valid exclusion count.")
            if not isinstance(record.get("text_raw"), str):
                raise InputError(f"{source} locus {index} has no raw text.")
            for word in record["tokens"]:
                if not isinstance(word, str) or set(word).difference(alphabet):
                    raise InputError(f"{source} locus {index} has a sign outside the fixed alphabet.")


def _parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description=(
            "Run the fixed space-free pilot. Use --freeze for pinned inputs or --fixture for synthetic files. "
            "Fixture JSON has schema_version, alphabet, reference_training_words, control_fit_plaintext, "
            "control_test_plaintext, and manuscript_fixture_path. The separate manuscript JSON has "
            "schema_version and loci records. The runner opens that file only after all four controls pass."
        )
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--fixture", metavar="JSON")
    source.add_argument("--freeze", metavar="JSON")
    parser.add_argument("--output", required=True, metavar="NEW_DIRECTORY")
    return parser.parse_args(argv)


def _run_cli(argv=None):
    deadline = time.monotonic() + MAX_RUNTIME_SECONDS
    root = Path(__file__).resolve().parents[2]
    args = _parse_args(argv)
    output = Path(args.output)
    if not output.is_absolute():
        output = Path.cwd() / output
    if output.exists():
        print("error: output directory already exists", file=sys.stderr)
        return 2
    try:
        if args.fixture:
            context = _load_fixture_config(args.fixture)
        else:
            _check_deadline(deadline)
            freeze = _check_freeze(root, args.freeze)
            _check_deadline(deadline)
            context = _prepare_real_context(root, freeze, deadline)
        _check_deadline(deadline)
        context["deadline"] = deadline
    except (InputError, OSError, RuntimeError, TimeoutError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        return _execute(root, output, context)
    except TimeoutError as error:
        if output.is_dir():
            _record_error(output, "timeout", error)
        print(f"error: {error}", file=sys.stderr)
        return 1


def _timeout_handler(signum, frame):
    raise TimeoutError("The fixed 1,800-second run limit expired.")


def main(argv=None):
    prior_handler = signal.signal(signal.SIGALRM, _timeout_handler)
    prior_alarm = signal.alarm(MAX_RUNTIME_SECONDS)
    try:
        return _run_cli(argv)
    except TimeoutError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, prior_handler)
        if prior_alarm:
            signal.alarm(prior_alarm)


if __name__ == "__main__":
    raise SystemExit(main())
