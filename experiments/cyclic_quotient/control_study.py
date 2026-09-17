"""Run the source-bound cyclic quotient control study.

The fit receives only the train lexicon and the encrypted validation stream.
The runner opens the test stream after it validates the durable fit key.
"""

from __future__ import annotations

import argparse
from collections.abc import Iterable, Mapping, Sequence
import hashlib
import json
from pathlib import Path
import string
import sys
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
if str(REPOSITORY_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from experiments.cyclic_pairing.study import (  # noqa: E402
    hash_cipher_partition,
)
from experiments.cyclic_quotient.study import (  # noqa: E402
    BOUND_ENGINE,
    CAPACITY as FIT_CAPACITY,
    FIT_FILENAME,
    KEY_FILENAME,
    QUOTIENT_FILENAME,
    QUOTIENT_NODE_BUDGET,
    SOLVER_NODE_BUDGET,
    run_study,
)
from experiments.homophonic.controls import (  # noqa: E402
    encrypt_words,
    seeded_control_key,
)
from voynich.reference import load_reference_partitions  # noqa: E402


PROTOCOL = "cyclic-quotient-recovery-v1"
CORPORA = ("latin", "italian")
SOURCE_CORPORA = {
    "latin": "latin_llct",
    "italian": "italian_old",
}
CONTROL_FAMILY = "cap2"
SEED = 7000
CAPACITY = 2
UNITS = tuple(f"c{index:02d}" for index in range(52))
OUTPUT_RELATIVE = Path("results/cyclic-quotient-recovery-v1")
FREEZE_RELATIVE = Path("experiments/cyclic_quotient/freeze-v1.json")
EXPECTED_VALIDATION_STREAM_HASHES = {
    "latin": "eb03e98b086b9f8bc883f349afaee968bfeaeee8c95be5f66bec320e54b419b2",
    "italian": "d7e9c6e0b716cf7ea1c7deb4f135ca2692ea70b4f927548e99668ab0c1428492",
}
_ALPHABET = frozenset(string.ascii_lowercase)
_OUTPUT_NAMES = (QUOTIENT_FILENAME, FIT_FILENAME, KEY_FILENAME, "diagnostics.json")
_CODE_RELATIVES = (
    Path("experiments/cyclic_quotient/control_study.py"),
    Path("experiments/cyclic_quotient/study.py"),
    Path("experiments/cyclic_quotient/quotient.py"),
    Path("experiments/cyclic_pairing/study.py"),
    Path("experiments/homophonic/controls.py"),
    Path("src/voynich/reference.py"),
)


def canonical_bytes(value: Any) -> bytes:
    """Return canonical JSON bytes with one final newline."""

    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode(
        "utf-8"
    )


def canonical_hash(value: Any) -> str:
    """Return the SHA-256 digest of canonical JSON bytes."""

    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def load_freeze_metadata(root: Path = REPOSITORY_ROOT) -> dict[str, Any]:
    """Read the external quotient freeze and bind its raw-byte hash."""

    path = Path(root) / FREEZE_RELATIVE
    if path.is_symlink() or not path.is_file():
        raise FileNotFoundError("the cyclic quotient freeze record is unavailable")
    raw = path.read_bytes()
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("the cyclic quotient freeze record is invalid") from error
    if not isinstance(value, Mapping):
        raise ValueError("the cyclic quotient freeze record is not an object")
    result = dict(value)
    result["manifest_sha256"] = _sha256_bytes(raw)
    return result


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_path(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _digest(value: Any, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"{field} must be a lowercase SHA-256 digest")
    return value


def _safe_relative_name(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} must be a relative path")
    path = Path(value)
    if path.is_absolute() or ".." in path.parts or path.as_posix() != value:
        raise ValueError(f"{field} must be a safe relative path")
    return value


def _source_identity(metadata: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(metadata, Mapping):
        raise TypeError("source metadata must be a mapping")
    source_manifest = metadata.get(
        "reference_manifest_sha256", metadata.get("source_manifest_sha256")
    )
    source_files = metadata.get("source_files")
    if not isinstance(source_files, Mapping) or not source_files:
        raise ValueError("source metadata has no source files")
    file_hashes: dict[str, str] = {}
    for raw_name, raw_info in source_files.items():
        name = _safe_relative_name(raw_name, "source file name")
        if Path(name).name != name or not isinstance(raw_info, Mapping):
            raise ValueError("source metadata contains an invalid source file")
        file_hashes[name] = _digest(raw_info.get("sha256"), f"source file {name}")
    return {
        "source_manifest_sha256": _digest(source_manifest, "source manifest hash"),
        "source_file_hashes": dict(sorted(file_hashes.items())),
    }


def _freeze_identity(metadata: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(metadata, Mapping):
        raise TypeError("freeze metadata must be a mapping")
    entries = metadata.get("files")
    if entries is None:
        entries = [
            {"path": name, "sha256": digest}
            for name, digest in (metadata.get("frozen_file_hashes") or {}).items()
        ]
    if not isinstance(entries, Sequence) or isinstance(entries, (str, bytes)):
        raise ValueError("freeze metadata has no file list")
    frozen: dict[str, str] = {}
    for entry in entries:
        if not isinstance(entry, Mapping):
            raise ValueError("freeze metadata contains a malformed file entry")
        name = _safe_relative_name(entry.get("path"), "freeze file name")
        if name in frozen:
            raise ValueError("freeze metadata contains a duplicate file")
        frozen[name] = _digest(entry.get("sha256"), f"freeze file {name}")
    return {
        "freeze_manifest_sha256": _digest(
            metadata.get("manifest_sha256"), "freeze manifest hash"
        ),
        "frozen_file_hashes": dict(sorted(frozen.items())),
        "frozen_code_hashes": {
            name: digest
            for name, digest in sorted(frozen.items())
            if name.endswith(".py")
        },
    }


def _code_hashes() -> dict[str, str]:
    root = Path(__file__).resolve().parents[2]
    result: dict[str, str] = {}
    for relative in _CODE_RELATIVES:
        path = root / relative
        if not path.is_file() or path.is_symlink():
            raise FileNotFoundError(f"required code file is unavailable: {relative}")
        result[relative.as_posix()] = _sha256_path(path)
    return result


def _normalise_source_words(value: Any, field: str) -> tuple[str, ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Iterable):
        raise ValueError(f"{field} must be a sequence of words")
    words = tuple(value)
    if any(not isinstance(word, str) or not word for word in words):
        raise ValueError(f"{field} must contain non-empty text words")
    return words


def _corpus_inputs(
    partitions: Mapping[str, Any], corpus: str
) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...], dict[str, Any]]:
    source_name = SOURCE_CORPORA[corpus]
    try:
        data = partitions[source_name]
        words = data["words"]
        metadata = data["metadata"]
        train = _normalise_source_words(words["train"], "train words")
        validation = _normalise_source_words(words["validation"], "validation words")
        test = _normalise_source_words(words["test"], "test words")
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("reference loader did not return the required partitions") from error
    if not train or not validation or not test:
        raise ValueError("reference partitions must contain train, validation, and test words")
    _source_identity(metadata)
    return train, validation, test, dict(metadata)


def _output_directory(output_root: Path, corpus: str) -> Path:
    if corpus not in CORPORA:
        raise ValueError(f"unsupported corpus: {corpus!r}")
    output_root = Path(output_root)
    if output_root.exists() and output_root.is_symlink():
        raise FileExistsError("output root is a symlink")
    # The public API accepts either the fixed corpus directory or its parent.
    # The supervisor passes ``.../<corpus>``; the parent form matches the
    # earlier child-study convention.
    corpus_dir = output_root if output_root.name == corpus else output_root / corpus
    if corpus_dir.is_symlink():
        raise FileExistsError("corpus output directory is a symlink")
    for name in _OUTPUT_NAMES:
        path = corpus_dir / name
        if path.exists() or path.is_symlink():
            raise FileExistsError(f"a fixed output already exists: {path}")
    return corpus_dir


def _read_json(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"required output is unavailable: {path.name}")
    try:
        value = json.loads(path.read_bytes().decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"invalid JSON output: {path.name}") from error
    if not isinstance(value, dict):
        raise ValueError(f"output is not a JSON object: {path.name}")
    return value


def _check_output_hashes(output: Path, result: Mapping[str, Any]) -> None:
    hashes = result.get("output_hashes")
    if hashes is None:
        return
    if not isinstance(hashes, Mapping):
        raise ValueError("study output hashes are malformed")
    for raw_name, raw_digest in hashes.items():
        name = _safe_relative_name(raw_name, "study output name")
        if Path(name).name != name or name not in _OUTPUT_NAMES:
            raise ValueError("study output hash names are invalid")
        path = output / name
        actual = _sha256_path(path) if path.is_file() and not path.is_symlink() else None
        if actual != _digest(raw_digest, f"study output hash {name}"):
            raise ValueError(f"study output hash mismatch: {name}")


def _class_name(members: Sequence[str]) -> str:
    return "+".join(sorted(members))


def _validate_saved_key(
    output: Path,
    result: Mapping[str, Any],
) -> tuple[dict[str, str], dict[str, Any], dict[str, Any]]:
    quotient_path = output / QUOTIENT_FILENAME
    key_path = output / KEY_FILENAME
    quotient = _read_json(quotient_path)
    key = _read_json(key_path)
    quotient_hash = _sha256_path(quotient_path)
    if quotient.get("protocol") != PROTOCOL or quotient.get("quotient_status") != "proved":
        raise ValueError("saved quotient is not proved by the fixed protocol")
    if (
        quotient.get("declared_unit_count") != len(UNITS)
        or quotient.get("declared_units_sha256") != canonical_hash(list(UNITS))
    ):
        raise ValueError("saved quotient has the wrong declared unit count")
    observed = quotient.get("observed_units")
    unseen = quotient.get("unseen_units")
    classes = quotient.get("classes")
    if not isinstance(observed, Sequence) or isinstance(observed, (str, bytes)):
        raise ValueError("saved quotient observed units are malformed")
    if not isinstance(unseen, Sequence) or isinstance(unseen, (str, bytes)):
        raise ValueError("saved quotient unseen units are malformed")
    if any(not isinstance(unit, str) for unit in (*observed, *unseen)):
        raise ValueError("saved quotient units are malformed")
    observed_set = set(observed)
    unseen_set = set(unseen)
    if len(observed_set) != len(observed) or len(unseen_set) != len(unseen):
        raise ValueError("saved quotient unit lists contain duplicates")
    if observed_set & unseen_set or observed_set | unseen_set != set(UNITS):
        raise ValueError("saved quotient unit coverage is inconsistent")
    if (
        quotient.get("observed_unit_count") != len(observed_set)
        or quotient.get("unseen_unit_count") != len(unseen_set)
    ):
        raise ValueError("saved quotient count metadata is inconsistent")
    if not isinstance(classes, Sequence) or isinstance(classes, (str, bytes)):
        raise ValueError("saved quotient classes are malformed")
    expected_members: dict[str, tuple[str, ...]] = {}
    class_units: set[str] = set()
    for raw_members in classes:
        if (
            not isinstance(raw_members, Sequence)
            or isinstance(raw_members, (str, bytes))
            or not raw_members
        ):
            raise ValueError("saved quotient contains an invalid class")
        members = tuple(raw_members)
        if len(members) > CAPACITY or any(
            not isinstance(unit, str) or unit not in observed_set for unit in members
        ):
            raise ValueError("saved quotient class violates capacity or coverage")
        if len(set(members)) != len(members) or class_units.intersection(members):
            raise ValueError("saved quotient classes overlap")
        name = _class_name(members)
        if name in expected_members:
            raise ValueError("saved quotient class names are duplicated")
        expected_members[name] = tuple(sorted(members))
        class_units.update(members)
    if class_units != observed_set:
        raise ValueError("saved quotient classes do not cover observed units")

    if (
        key.get("protocol") != PROTOCOL
        or key.get("record_kind") != "complete_observed_quotient_key"
    ):
        raise ValueError("saved key record is malformed")
    if key.get("quotient_evidence_sha256") != quotient_hash:
        raise ValueError("saved key is not bound to the saved quotient")
    if key.get("quotient_status") != "proved":
        raise ValueError("saved key does not bind a proved quotient")
    raw_names = key.get("class_names")
    raw_members = key.get("class_members")
    raw_class_key = key.get("class_key")
    raw_observed_key = key.get("observed_unit_key")
    if not isinstance(raw_names, Sequence) or isinstance(raw_names, (str, bytes)):
        raise ValueError("saved key class names are malformed")
    if list(raw_names) != sorted(expected_members):
        raise ValueError("saved key class names do not match the quotient")
    if not isinstance(raw_members, Mapping) or not isinstance(raw_class_key, Mapping):
        raise ValueError("saved key class maps are malformed")
    saved_members = {
        str(name): tuple(value)
        for name, value in raw_members.items()
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes))
    }
    if saved_members != expected_members or set(raw_members) != set(expected_members):
        raise ValueError("saved key class members do not match the quotient")
    if set(raw_class_key) != set(expected_members):
        raise ValueError("saved key class map is incomplete")
    class_key: dict[str, str] = {}
    for name in sorted(expected_members):
        letter = raw_class_key[name]
        if not isinstance(letter, str) or letter not in _ALPHABET:
            raise ValueError("saved key contains an invalid plaintext letter")
        class_key[name] = letter
    if len(set(class_key.values())) != len(class_key):
        raise ValueError("saved quotient class key violates capacity-one fitting")
    if not isinstance(raw_observed_key, Mapping):
        raise ValueError("saved observed-unit key is malformed")
    expected_observed_key = {
        unit: class_key[name]
        for name, members in expected_members.items()
        for unit in members
    }
    if dict(raw_observed_key) != expected_observed_key:
        raise ValueError("saved observed-unit key is not induced by the quotient key")
    expected_open_slots = sum(
        CAPACITY - len(members) for members in expected_members.values()
    )
    if key.get("open_slot_count") != expected_open_slots:
        raise ValueError("saved key capacity metadata is inconsistent")
    coverage = key.get("coverage")
    if not isinstance(coverage, Mapping):
        raise ValueError("saved key coverage is missing")
    expected_coverage = {
        "declared_unit_count": len(UNITS),
        "observed_unit_count": len(observed_set),
        "unseen_unit_count": len(unseen_set),
        "mapped_observed_units": len(expected_observed_key),
    }
    if {name: coverage.get(name) for name in expected_coverage} != expected_coverage:
        raise ValueError("saved key coverage is inconsistent")
    result_hashes = result.get("output_hashes")
    if isinstance(result_hashes, Mapping) and KEY_FILENAME in result_hashes:
        if _digest(result_hashes[KEY_FILENAME], "returned key hash") != _sha256_path(key_path):
            raise ValueError("returned key hash does not match the durable key")
    return dict(sorted(expected_observed_key.items())), quotient, key


def _score_partition(
    cipher_words: Iterable[Iterable[str]],
    plaintext_words: Sequence[str],
    observed_key: Mapping[str, str],
    train_lexicon: frozenset[str],
) -> dict[str, Any]:
    cipher = tuple(tuple(word) for word in cipher_words)
    plain = tuple(plaintext_words)
    if len(cipher) != len(plain):
        raise ValueError("cipher and plaintext partitions have different token counts")
    character_total = 0
    character_correct = 0
    mapped_positions = 0
    unexplained_positions = 0
    word_correct = 0
    complete_words = 0
    dictionary_hits = 0
    for cipher_word, plaintext in zip(cipher, plain, strict=True):
        if len(cipher_word) != len(plaintext):
            raise ValueError("cipher and plaintext words have different lengths")
        decoded: list[str] = []
        complete = True
        for unit, target in zip(cipher_word, plaintext, strict=True):
            character_total += 1
            letter = observed_key.get(unit)
            if letter is None:
                complete = False
                unexplained_positions += 1
                continue
            mapped_positions += 1
            decoded.append(letter)
            if letter == target:
                character_correct += 1
        if complete:
            complete_words += 1
            decoded_word = "".join(decoded)
            if decoded_word == plaintext:
                word_correct += 1
            if decoded_word in train_lexicon:
                dictionary_hits += 1
    token_count = len(plain)
    return {
        "character": {
            "correct": character_correct,
            "denominator": character_total,
        },
        "word": {
            "correct": word_correct,
            "denominator": token_count,
        },
        "coverage": {
            "mapped_positions": mapped_positions,
            "total_positions": character_total,
            "unexplained_positions": unexplained_positions,
            "complete_words": complete_words,
            "word_denominator": token_count,
        },
        "dictionary_hits": {
            "hits": dictionary_hits,
            "denominator": token_count,
            "complete_word_denominator": complete_words,
        },
    }


def _fit_status(result: Mapping[str, Any]) -> tuple[Any, Any, Any, Any]:
    fit = result.get("fit")
    solver = fit.get("solver") if isinstance(fit, Mapping) else None
    if not isinstance(solver, Mapping):
        return result.get("status"), None, result.get("lower_bound"), result.get("upper_bound")
    return (
        solver.get("status", result.get("status")),
        solver.get("score_certified"),
        solver.get("lower_bound", result.get("lower_bound")),
        solver.get("upper_bound", result.get("upper_bound")),
    )


def _build_diagnostics(
    corpus: str,
    result: Mapping[str, Any],
    provenance: Mapping[str, Any],
    validation_cipher: Iterable[Iterable[str]],
    validation_plain: Sequence[str],
    test_cipher: Iterable[Iterable[str]],
    test_plain: Sequence[str],
    observed_key: Mapping[str, str],
    planted_key: Mapping[str, Any],
    train_words: Sequence[str],
) -> dict[str, Any]:
    fit_status, score_certified, lower_bound, upper_bound = _fit_status(result)
    planted_mapping = planted_key.get("cipher_to_plain")
    if not isinstance(planted_mapping, Mapping):
        raise ValueError("control key has no cipher-to-plain mapping")
    planted_correct = sum(
        observed_key[unit] == planted_mapping[unit]
        for unit in observed_key
        if unit in planted_mapping
    )
    mapped_planted_units = sum(unit in planted_mapping for unit in observed_key)
    source = dict(provenance)
    quotient_hash = result.get("output_hashes", {}).get(QUOTIENT_FILENAME)
    return {
        "record_type": "diagnostics",
        "protocol": PROTOCOL,
        "corpus": corpus,
        "family": CONTROL_FAMILY,
        "seed": SEED,
        "capacity": CAPACITY,
        "input_scope": "train_lexicon_and_validation_ciphertext_fit_then_postfit_test",
        "freeze_manifest_sha256": source.get("freeze_manifest_sha256"),
        "source_manifest_sha256": source.get("source_manifest_sha256"),
        "source_file_hashes": source.get("source_file_hashes", {}),
        # ``status`` records that post-fit diagnostics completed. The exact
        # solver status remains in ``fit_status`` and ``completion``.
        "status": "complete",
        "quotient_evidence_sha256": quotient_hash,
        "fit_status": fit_status,
        "completion": "complete" if score_certified else "incomplete_search",
        "score_certified": score_certified,
        "lower_bound": lower_bound,
        "upper_bound": upper_bound,
        "validation": _score_partition(
            validation_cipher,
            validation_plain,
            observed_key,
            frozenset(train_words),
        ),
        "test": _score_partition(
            test_cipher,
            test_plain,
            observed_key,
            frozenset(train_words),
        ),
        "postfit_planted_map": {
            "correct": planted_correct,
            "denominator": mapped_planted_units,
            "observed_unit_count": len(observed_key),
            "unseen_unit_count": len(UNITS) - len(observed_key),
        },
        "settings": {
            "bound_engine": BOUND_ENGINE,
            "fit_capacity": FIT_CAPACITY,
            "quotient_node_budget": QUOTIENT_NODE_BUDGET,
            "solver_node_budget": SOLVER_NODE_BUDGET,
            "fit_uses": "train lexicon and validation ciphertext only",
            "test_boundary": "saved induced observed-unit key validated before test encryption",
        },
        "provenance": source,
        "validation_stream_sha256": hash_cipher_partition(validation_cipher),
        "code_hashes": _code_hashes(),
    }


def _write_exclusive(path: Path, value: Mapping[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = canonical_bytes(value)
    with path.open("xb") as handle:
        handle.write(data)
    return _sha256_bytes(data)


def _resolve_output(root: Path, output_dir: Path) -> Path:
    output = Path(output_dir)
    return output if output.is_absolute() else Path(root) / output


def run_corpus(root: Path, corpus: str, output_dir: Path) -> dict[str, Any]:
    """Run one fixed source-bound quotient control corpus."""

    if corpus not in CORPORA:
        raise ValueError(f"unsupported corpus: {corpus!r}")
    root = Path(root)
    output = _output_directory(_resolve_output(root, Path(output_dir)), corpus)
    freeze = load_freeze_metadata(root)
    partitions = load_reference_partitions(root)
    train_words, validation_plain, test_plain, source_metadata = _corpus_inputs(
        partitions, corpus
    )
    source_identity = _source_identity(source_metadata)
    freeze_identity = _freeze_identity(freeze)
    planted_key = seeded_control_key(CONTROL_FAMILY, SEED)
    validation_cipher = tuple(encrypt_words(validation_plain, planted_key))
    stream_hash = hash_cipher_partition(validation_cipher)
    if stream_hash != EXPECTED_VALIDATION_STREAM_HASHES[corpus]:
        raise ValueError(f"validation stream hash mismatch for {corpus}")

    result = run_study(UNITS, validation_cipher, train_words, output)
    if not isinstance(result, Mapping):
        raise ValueError("quotient study did not return a result mapping")
    _check_output_hashes(output, result)
    if result.get("quotient_status") != "proved" or result.get("status") in {
        "abstained",
        "infeasible_capacity",
    }:
        return dict(result)
    if not result.get("verified") or not result.get("feasible"):
        return dict(result)
    observed_key, quotient, saved_key = _validate_saved_key(output, result)
    del quotient, saved_key

    test_cipher = tuple(encrypt_words(test_plain, planted_key))
    provenance = {
        **source_identity,
        **freeze_identity,
    }
    diagnostics = _build_diagnostics(
        corpus,
        result,
        provenance,
        validation_cipher,
        validation_plain,
        test_cipher,
        test_plain,
        observed_key,
        planted_key,
        train_words,
    )
    diagnostics_hash = _write_exclusive(output / "diagnostics.json", diagnostics)
    final = dict(result)
    final["diagnostics_sha256"] = diagnostics_hash
    final["output_files"] = [
        QUOTIENT_FILENAME,
        KEY_FILENAME,
        FIT_FILENAME,
        "diagnostics.json",
    ]
    return final


def main(argv: Sequence[str] | None = None) -> int:
    """Run one fixed corpus selected by ``--corpus``."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", choices=CORPORA, required=True)
    parser.add_argument("--output-dir")
    args = parser.parse_args(argv)
    output_dir = (
        Path(args.output_dir)
        if args.output_dir is not None
        else OUTPUT_RELATIVE / args.corpus
    )
    result = run_corpus(REPOSITORY_ROOT, args.corpus, output_dir)
    print(
        json.dumps(
            {
                "status": result.get("status"),
                "corpus": args.corpus,
                "output_files": result.get("output_files", []),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "BOUND_ENGINE",
    "CAPACITY",
    "CONTROL_FAMILY",
    "CORPORA",
    "EXPECTED_VALIDATION_STREAM_HASHES",
    "FIT_FILENAME",
    "FREEZE_RELATIVE",
    "KEY_FILENAME",
    "OUTPUT_RELATIVE",
    "PROTOCOL",
    "QUOTIENT_FILENAME",
    "QUOTIENT_NODE_BUDGET",
    "SEED",
    "SOLVER_NODE_BUDGET",
    "SOURCE_CORPORA",
    "UNITS",
    "canonical_bytes",
    "canonical_hash",
    "hash_cipher_partition",
    "main",
    "run_corpus",
]
