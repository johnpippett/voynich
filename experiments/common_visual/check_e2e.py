"""Run synthetic end-to-end checks for the common visual pilot."""

from collections import Counter
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import random
import shutil
import string
import subprocess
import sys
import traceback


ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / "experiments/common_visual/run.py"
PLAN = ROOT / "docs/plans/common-visual-pilot-v1.md"
OLD_SCORE = ROOT / "experiments/spacefree_substitution/score.py"
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
ALPHABET = string.ascii_lowercase
COMMON = (
    "o", "y", "a", "e", "ch", "sh", "k", "t", "f", "p", "ckh",
    "cth", "cfh", "cph", "d", "s", "r", "l", "i", "n", "m", "g", "q",
)
CONTROL_SEEDS = (408, 409, 410, 411)


def _sha256(data):
    return hashlib.sha256(data).hexdigest()


def _json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _write_json(path, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def _load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"Cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _find_folios():
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


def _records(test_suffix="xqoe", short_test=False):
    folios = _find_folios()
    common_words = list(COMMON)
    return [
        {"source": "ZL", "folio": folios["train"], "locus": "f1r.1,@P0;A",
         "transcriber": "A", "kind": "P0", "metadata": {"$H": "A"},
         "text_raw": ".".join(common_words + ["oaye"]), "tokens": common_words + ["oaye"],
         "excluded_tokens": 0, "paragraph_start": False, "paragraph_end": False},
        {"source": "ZL", "folio": folios["validation"], "locus": "fixture.validation",
         "transcriber": "A", "kind": "P0", "metadata": {},
         "text_raw": "oaye.x.q", "tokens": ["oaye", "x", "q"], "excluded_tokens": 0,
         "paragraph_start": False, "paragraph_end": False},
        {"source": "ZL", "folio": folios["test"], "locus": "fixture.test",
         "transcriber": "A", "kind": "P0", "metadata": {},
         "text_raw": "o.a.y" if short_test else f"oaye.{test_suffix}.x",
         "tokens": ["o", "a", "y"] if short_test else ["oaye", test_suffix, "x"],
         "excluded_tokens": 0, "paragraph_start": False, "paragraph_end": False},
        {"source": "IT", "folio": folios["train"], "locus": "fixture.it.train",
         "transcriber": "B", "kind": "P0", "metadata": {},
         "text_raw": "oaye.shckhcth", "tokens": ["oaye", "shckhcth"],
         "excluded_tokens": 0, "paragraph_start": False, "paragraph_end": False},
        {"source": "IT", "folio": folios["validation"], "locus": "fixture.it.validation",
         "transcriber": "B", "kind": "P0", "metadata": {},
         "text_raw": "oaye.x.q", "tokens": ["oaye", "x", "q"], "excluded_tokens": 0,
         "paragraph_start": False, "paragraph_end": False},
        {"source": "IT", "folio": folios["test"], "locus": "fixture.it.test",
         "transcriber": "B", "kind": "P0", "metadata": {},
         "text_raw": "oaye.x.q", "tokens": ["oaye", "x", "q"], "excluded_tokens": 0,
         "paragraph_start": False, "paragraph_end": False},
        {"source": "ZL", "folio": folios["train"], "locus": "fixture.nonparagraph",
         "transcriber": "A", "kind": "H0", "metadata": {},
         "text_raw": "oaye", "tokens": ["oaye"], "excluded_tokens": 0,
         "paragraph_start": False, "paragraph_end": False},
        {"source": "ZL", "folio": folios["train"], "locus": "fixture.empty",
         "transcriber": "A", "kind": "P0", "metadata": {},
         "text_raw": "", "tokens": [], "excluded_tokens": 0,
         "paragraph_start": False, "paragraph_end": False},
        {"source": "ZL", "folio": folios["train"], "locus": "fixture.excluded",
         "transcriber": "A", "kind": "P0", "metadata": {},
         "text_raw": "oaye.[a:b]", "tokens": ["oaye"], "excluded_tokens": 1,
         "paragraph_start": False, "paragraph_end": False},
        {"source": "ZL", "folio": folios["train"], "locus": "fixture.interrupted1",
         "transcriber": "A", "kind": "P0", "metadata": {},
         "text_raw": "oaye<->", "tokens": ["oaye"], "excluded_tokens": 0,
         "paragraph_start": False, "paragraph_end": False},
        {"source": "ZL", "folio": folios["train"], "locus": "fixture.interrupted2",
         "transcriber": "A", "kind": "P0", "metadata": {},
         "text_raw": "oaye<~>", "tokens": ["oaye"], "excluded_tokens": 0,
         "paragraph_start": False, "paragraph_end": False},
    ]


def _fixture(test_suffix="xqoe", manuscript_name="manuscript.json",
             control_fit=None, control_test=None):
    training = "".join(
        char * count
        for char, count in zip(ALPHABET[:23], range(23, 0, -1), strict=True)
    )
    return {
        "schema_version": 1,
        "reference_training_words": [training],
        "control_fit_plaintext": control_fit or training,
        "control_test_plaintext": control_test or training,
        "manuscript_fixture_path": manuscript_name,
    }


def _run(fixture_path, output, timeout=180, log_path=None):
    completed = subprocess.run(
        [sys.executable, str(RUNNER), "--fixture", str(fixture_path), "--output", str(output)],
        cwd=ROOT, capture_output=True, text=True, timeout=timeout,
    )
    if log_path is not None:
        _write_json(log_path, {
            "command": "python experiments/common_visual/run.py --fixture FIXTURE.json --output OUTPUT_DIR",
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        })
    return completed


def _tree_hashes(directory):
    return {
        path.relative_to(directory).as_posix(): _sha256(path.read_bytes())
        for path in sorted(Path(directory).rglob("*")) if path.is_file()
    }


def _known_key(seed):
    plain = list(ALPHABET)
    random.Random(seed).shuffle(plain)
    return dict(zip(ALPHABET, plain, strict=True))


def _position_key(alphabet, positions):
    assert len(positions) == len(alphabet) and set(positions) == set(range(len(alphabet)))
    return {cipher: alphabet[positions[index]] for index, cipher in enumerate(alphabet)}


def _control_stream(plaintext, key):
    inverse = {plain: cipher for cipher, plain in key.items()}
    return "".join(inverse[char] for char in plaintext)


def _literal_visual_score(model, symbols, key):
    total = 0.0
    unknown_windows = 0
    for start in range(len(symbols) - 3):
        window = symbols[start:start + 4]
        if None in window:
            unknown_windows += 1
            total += math.log2(26)
        else:
            a, b, c, d = (key[index] for index in window)
            flat = (((a * 26 + b) * 26 + c) * 26 + d)
            total += model.window_costs[flat]
    return total, unknown_windows


def _fit_search_checks():
    sys.path.insert(0, str(ROOT))
    old = _load_module("common_visual_old_score", OLD_SCORE)
    new = _load_module("common_visual_search", ROOT / "experiments/common_visual/search.py")
    model = old.NGramModel(ALPHABET, "aabacadaeafagahaiajakalamanapaoapaqara" * 8)

    # The independent loop uses the frozen model table and literal four-unit windows.
    symbols = [0, 1, 2, None, 4, 5, 6, 7, 8, None]
    key = tuple(reversed(range(len(ALPHABET))))
    result = new.score_with_unknown(model, symbols, key)
    total, unknown_windows = _literal_visual_score(model, symbols, key)
    assert result["window_count"] == len(symbols) - 3, result
    assert result["unknown_window_count"] == unknown_windows, result
    assert math.isclose(result["total_cost"], total, rel_tol=1e-12, abs_tol=1e-9), result
    assert math.isclose(result["mean_cost"], total / (len(symbols) - 3),
                        rel_tol=1e-12, abs_tol=1e-9), result

    edge_cases = {
        "first": [None, 1, 2, 3, 4, 5, 6],
        "middle": [0, 1, 2, None, 4, 5, 6],
        "final": [0, 1, 2, 3, 4, 5, None],
        "overlap": [0, None, 2, 3, 4, 5, 6],
        "all_unknown": [None, None, None, None, None],
    }
    edge_results = {}
    for label, stream in edge_cases.items():
        scored = new.score_with_unknown(model, stream, key)
        expected, expected_unknown = _literal_visual_score(model, stream, key)
        assert math.isclose(scored["total_cost"], expected, rel_tol=1e-12, abs_tol=1e-9), scored
        assert scored["unknown_window_count"] == expected_unknown, scored
        edge_results[label] = scored["unknown_window_count"]

    mixed = [0, 1, None, 2, 3, 4, 5, 6]
    assert any(value is None for value in mixed)
    assert len(mixed) - 3 - sum(
        None in mixed[start:start + 4] for start in range(len(mixed) - 3)
    ) > 0
    fitted = new.search_key(model, mixed)
    fitted_key = fitted.get("key_positions")
    assert len(fitted_key) == 26 and set(fitted_key) == set(range(26)), fitted
    literal_total, literal_unknown_windows = _literal_visual_score(model, mixed, fitted_key)
    literal_mapped_windows = len(mixed) - 3 - literal_unknown_windows
    assert fitted["unknown_window_count"] == literal_unknown_windows, fitted
    assert fitted["mapped_window_count"] == literal_mapped_windows, fitted
    assert math.isclose(fitted["best_recomputed_cost"], literal_total,
                        rel_tol=1e-12, abs_tol=1e-8), (fitted, literal_total)

    for no_known_window in ([0, 1, None, 2, 3], [None] * 8, [], [0, 1, 2]):
        try:
            new.search_key(model, no_known_window)
        except ValueError:
            pass
        else:
            raise AssertionError("Search accepted input with no mapped four-unit window")
    for too_short in ([], [0, None, 2]):
        try:
            new.score_with_unknown(model, too_short, key)
        except ValueError:
            pass
        else:
            raise AssertionError("Scorer accepted fewer than four positions")

    known_text = "aabacadaeafagahaiajakalamanapaoapaqara" * 2
    old_result = old.search_key(model, known_text)
    new_result = new.search_key(model, model.indices(known_text))
    without_count = {key_name: value for key_name, value in new_result.items()
                     if key_name not in {"unknown_window_count", "mapped_window_count"}}
    assert without_count == old_result, "Known-only search differs from frozen search"
    known_score = new.score_with_unknown(model, model.indices(known_text), old_result["key_positions"])
    old_score = model.score_indices(model.indices(known_text), old_result["key_positions"])
    assert math.isclose(known_score["total_cost"], old_score,
                        rel_tol=1e-12, abs_tol=1e-8)
    return {
        "mixed_unknown_search": {"window_count": fitted["window_count"],
                                 "unknown_window_count": fitted["unknown_window_count"],
                                 "mapped_window_count": fitted["mapped_window_count"],
                                 "independent_total": literal_total},
        "unknown_window_cases": edge_results,
        "no_mapped_window_refused": True,
        "known_search_equal": True,
        "extra_slots_unassigned": True,
    }


def _assert_projection_coverage(record, projected):
    assert projected["text_raw"] == record["text_raw"], projected
    assert projected["tokens"] == record["tokens"], projected
    assert [word["normalized_word"] for word in projected["words"]] == record["tokens"], projected
    for word in projected["words"]:
        chars = word["characters"]
        positions = [char["position"] for char in chars]
        assert positions == sorted(positions), word
        assert len(set(positions)) == len(positions) == len(word["normalized_word"]), word
        assert "".join(char["normalized"] for char in chars) == word["normalized_word"], word
        assert all(record["text_raw"][char["position"]] == char["original"] for char in chars), word
        units = word["units"]
        assert "".join(unit["label"] for unit in units) == word["normalized_word"], word
        flattened = [position for unit in units for position in unit["positions"]]
        assert flattened == positions, word
        assert all(unit["label"] == unit["original"].lower() for unit in units), word


def _literal_units(word):
    compounds = ("cth", "ckh", "cph", "cfh", "ch", "sh")
    output = []
    index = 0
    while index < len(word):
        match = next((compound for compound in compounds if word.startswith(compound, index)), None)
        if match is None:
            output.append(word[index])
            index += 1
        else:
            output.append(match)
            index += len(match)
    return output


def _projection_checks(base):
    sys.path.insert(0, str(ROOT))
    sys.path.insert(0, str(ROOT / "src"))
    from voynich.corpus import parse_ivtff

    projection = _load_module("common_visual_projection", ROOT / "experiments/common_visual/projection.py")
    source = "#=IVTFF Eva- 2.0\n<f1r>\n<f1r.1,@P0;A> Sh{CKh}<!note>cth. C<-> th<~>Q\n"
    source_path = base / "projection.ivtff"
    source_path.write_text(source, encoding="utf-8")
    record = parse_ivtff(source_path, uncertain_spaces="split")[0]
    assert record["tokens"] == ["shckhcth", "c", "th", "q"], record
    projected = projection.project_record(record)
    _assert_projection_coverage(record, projected)
    words = projected["words"]
    assert [unit["label"] for unit in words[0]["units"]] == ["sh", "ckh", "cth"], words[0]
    assert [unit["positions"] for unit in words[0]["units"]] == [[0, 1], [3, 4, 5], [14, 15, 16]], words[0]
    assert [unit["original"] for unit in words[0]["units"]] == ["Sh", "CKh", "cth"], words[0]
    assert words[1]["units"][0]["positions"] == [19], words[1]
    assert [unit["label"] for unit in words[2]["units"]] == ["t", "h"], words[2]
    assert [unit["positions"] for unit in words[2]["units"]] == [[24], [25]], words[2]
    assert words[3]["units"][0]["positions"] == [29], words[3]
    assert projected["text_raw"] == record["text_raw"], projected

    bad = dict(record, tokens=["wrong"] + record["tokens"][1:])
    try:
        projection.project_record(bad)
    except ValueError:
        pass
    else:
        raise AssertionError("Projection accepted disagreement with parser tokens")
    malformed = dict(record, text_raw="a<unsupported>", tokens=["a"])
    try:
        projection.project_record(malformed)
    except ValueError:
        pass
    else:
        raise AssertionError("Projection accepted unsupported IVTFF syntax")
    return {
        "parser_tokens": record["tokens"],
        "expected_source_positions": [[0, 1], [3, 4, 5], [14, 15, 16], [19], [24], [25], [29]],
        "raw_record_kept": True,
        "mismatch_and_unsupported_syntax_refused": True,
    }


def _check_main_output(base):
    manuscript = {"schema_version": 1, "records": _records()}
    manuscript_path = base / "manuscript.json"
    _write_json(manuscript_path, manuscript)
    fixture_path = base / "fixture.json"
    _write_json(fixture_path, _fixture())
    out = base / "main"
    completed = _run(fixture_path, out, log_path=base / "logs/main.json")
    assert completed.returncode == 0, completed.stderr
    result = _json(out / "result.json")
    private = _json(out / "manuscript/private.json")
    assert result["calibration"]["accepted"] is True, result["calibration"]
    assert result["manuscript_stage"]["status"] == "run", result["manuscript_stage"]
    assert len(result["calibration"]["controls"]) == 4, result["calibration"]
    assert [item["seed"] for item in result["calibration"]["controls"]] == [408, 409, 410, 411], result
    calibration_private = _json(out / "calibration/private.json")
    assert len(calibration_private["controls"]) == 4, calibration_private
    assert [item["seed"] for item in calibration_private["controls"]] == [408, 409, 410, 411], calibration_private
    model_module = _load_module("common_visual_control_score", OLD_SCORE)
    fixture_config = _fixture()
    model = model_module.NGramModel(ALPHABET, "".join(fixture_config["reference_training_words"]))
    assert {item["fit_plaintext"] for item in calibration_private["controls"]} == {
        fixture_config["control_fit_plaintext"]
    }
    assert {item["test_plaintext"] for item in calibration_private["controls"]} == {
        fixture_config["control_test_plaintext"]
    }
    for control in result["calibration"]["controls"]:
        assert control["seed"] in CONTROL_SEEDS and control["passed"], control
    for control in calibration_private["controls"]:
        seed = control["seed"]
        known = _known_key(seed)
        assert control["known_cipher_to_plain"] == known, control
        fit_cipher = _control_stream(control["fit_plaintext"], known)
        test_cipher = _control_stream(control["test_plaintext"], known)
        assert control["fit_ciphertext"] == fit_cipher, control
        assert control["test_ciphertext"] == test_cipher, control
        fitted = control["fitted_cipher_to_plain"]
        observed_cipher = set(fit_cipher)
        assert all(fitted[symbol] == known[symbol] for symbol in observed_cipher), control
        fit_decoded = "".join(fitted[symbol] for symbol in fit_cipher)
        test_decoded = "".join(fitted[symbol] for symbol in test_cipher)
        fit_errors = [i for i, (actual, expected) in enumerate(
            zip(fit_decoded, control["fit_plaintext"], strict=True)
        ) if actual != expected]
        test_errors = [i for i, (actual, expected) in enumerate(
            zip(test_decoded, control["test_plaintext"], strict=True)
        ) if actual != expected]
        assert control["fit_error_positions"] == fit_errors == [], control
        assert control["test_error_positions"] == test_errors == [], control
        assert control["missing_fit_labels"] == [c for c in ALPHABET if c not in observed_cipher], control
        absent_test = set(test_cipher).difference(observed_cipher)
        assert control["test_labels_absent_from_fit"] == [c for c in ALPHABET if c in absent_test], control
        assert control["full_map_equal"] is (fitted == known), control
        unobserved_errors = [cipher for cipher in ALPHABET
                             if cipher not in observed_cipher and fitted[cipher] != known[cipher]]
        assert control["unobserved_assignment_errors"] == unobserved_errors, control
        positions = control["key_positions"]
        assert _position_key(ALPHABET, positions) == fitted, control
        frozen = _json(out / "calibration" / f"frozen-fit-key-seed-{seed}.json")
        assert frozen["key_positions"] == positions, frozen
        assert frozen["fitted_cipher_to_plain"] == fitted, frozen
        fit_score = model.score_indices(model.indices(fit_cipher), positions)
        assert math.isclose(control["fit_cost"], fit_score, rel_tol=1e-12, abs_tol=1e-8), control
        test_score = model.score_indices(model.indices(test_cipher), positions)
        assert math.isclose(control["test_cost"], test_score, rel_tol=1e-12, abs_tol=1e-8), control
    fits = private["fits"]
    assert set(fits) == {"observed", "within_word_shuffle", "word_order_shuffle"}, fits
    observed = fits["observed"]["observed_cipher_to_plain"]
    assert set(observed) <= set(COMMON) and len(observed) == len(set(observed)), observed
    assert "x" not in observed and "z" not in observed, observed
    assert all(len(fit["key_positions"]) == 26 for fit in fits.values()), fits
    assert all(set(fit["key_positions"]) == set(range(26)) for fit in fits.values()), fits

    projection_module = _load_module(
        "common_visual_projection_audit", ROOT / "experiments/common_visual/projection.py"
    )
    projection_records = private["projections"]
    assert projection_records, private
    all_fixture_records = _records()
    expected_eligible = [record for record in all_fixture_records
                         if record["kind"].startswith("P") and record["tokens"]
                         and record["excluded_tokens"] == 0
                         and "<->" not in record["text_raw"]
                         and "<~>" not in record["text_raw"]]
    assert len(expected_eligible) == 6, expected_eligible
    assert len(projection_records) == len(expected_eligible), projection_records
    projection_valid = True
    partition_by_folio = {folio: split for split, folio in _find_folios().items()}
    expected_words = {
        source: {split: [] for split in ("train", "validation", "test")}
        for source in ("ZL", "IT")
    }
    for item, expected_record in zip(projection_records, expected_eligible, strict=True):
        record = item["record"]
        for field in ("source", "folio", "locus", "kind", "transcriber", "metadata",
                      "text_raw", "tokens", "excluded_tokens"):
            assert record[field] == expected_record[field], (field, record, expected_record)
        actual = projection_module.project_record(record)
        assert item["projection"] == actual, item
        _assert_projection_coverage(record, actual)
        literal_word_units = [_literal_units(token) for token in expected_record["tokens"]]
        actual_word_units = [[unit["label"] for unit in word["units"]]
                             for word in actual["words"]]
        assert actual_word_units == literal_word_units, (actual_word_units, literal_word_units)
        expected_words[record["source"]][partition_by_folio[record["folio"]]].extend(
            literal_word_units
        )
        projection_valid &= actual["tokens"] == record["tokens"]
    for source in ("ZL", "IT"):
        for split in ("train", "validation", "test"):
            assert private["words"][source][split] == expected_words[source][split], (
                source, split, private["words"][source][split], expected_words[source][split]
            )

    all_literal_scores = {}
    variant_words = {"observed": private["words"]["ZL"]}
    variant_words["within_word_shuffle"] = {
        split: private["shuffles"]["within_word_shuffle"][split]["words"]
        for split in ("train", "validation", "test")
    }
    variant_words["word_order_shuffle"] = {
        split: private["shuffles"]["word_order_shuffle"][split]["words"]
        for split in ("train", "validation", "test")
    }
    # Recalculate all ZL and IT window costs from literal streams.
    for variant in fits:
        key_positions = fits[variant]["key_positions"]
        audited_sources = ("ZL", "IT") if variant == "observed" else ("ZL",)
        for source in audited_sources:
            for split in ("train", "validation", "test"):
                words = variant_words[variant][split] if source == "ZL" else private["words"]["IT"][split]
                labels = [unit for word in words for unit in word]
                indices = [COMMON.index(unit) if unit in COMMON else None for unit in labels]
                literal_total, literal_unknown = _literal_visual_score(
                    model, indices, key_positions
                )
                score = private["scores"][variant][source][split]
                windows = len(indices) - 3
                mapped_windows = windows - literal_unknown
                mapped_units = sum(unit in COMMON for unit in labels)
                mapped_eva = sum(len(unit) for unit in labels if unit in COMMON)
                eva_total = sum(len(unit) for unit in labels)
                decoded = [None if index is None else ALPHABET[key_positions[index]]
                           for index in indices]
                assert score["decoded_units"] == decoded, score
                assert score["window_count"] == windows, score
                assert score["unknown_window_count"] == literal_unknown, score
                assert score["mapped_window_count"] == mapped_windows, score
                assert math.isclose(score["total_cost"], literal_total,
                                    rel_tol=1e-12, abs_tol=1e-8), score
                assert math.isclose(score["mean_cost"], literal_total / windows,
                                    rel_tol=1e-12, abs_tol=1e-8), score
                assert score["unit_count"] == len(labels), score
                assert score["mapped_unit_count"] == mapped_units, score
                assert score["normalized_eva_codepoint_count"] == eva_total, score
                assert score["mapped_normalized_eva_codepoint_count"] == mapped_eva, score
                assert math.isclose(score["unit_coverage"], mapped_units / len(labels), abs_tol=1e-12), score
                assert math.isclose(score["eva_codepoint_coverage"], mapped_eva / eva_total, abs_tol=1e-12), score
                all_literal_scores[(variant, source, split)] = score

    # Compare the IT result with direct application of the saved observed ZL map.
    # Calculate every fixed gate again from reported values.
    metrics = result["manuscript_stage"]["metrics"]
    training_labels = [unit for word in private["words"]["ZL"]["train"] for unit in word]
    observed_test = all_literal_scores[("observed", "ZL", "test")]
    within_test = all_literal_scores[("within_word_shuffle", "ZL", "test")]
    order_test = all_literal_scores[("word_order_shuffle", "ZL", "test")]
    common_in_training = set(COMMON) <= set(training_labels)
    assert metrics["common_units_in_zl_training"] == sum(unit in set(training_labels) for unit in COMMON), metrics
    assert metrics["all_projections_valid"] is projection_valid, metrics
    assert metrics["observed_zl_test_mean"] == observed_test["mean_cost"], metrics
    assert metrics["within_word_shuffle_test_mean"] == within_test["mean_cost"], metrics
    assert metrics["word_order_shuffle_test_mean"] == order_test["mean_cost"], metrics
    expected_gates = {
        "all_four_controls": all(
            item["fit_error_positions"] == [] and item["test_error_positions"] == []
            for item in calibration_private["controls"]
        ),
        "all_common_units_in_training_and_projection_valid": (
            common_in_training and projection_valid
        ),
        "observed_zl_test_at_or_below_latin": (
            observed_test["mean_cost"] <= metrics["latin_test_mean"]
        ),
        "observed_zl_test_below_both_shuffles": (
            observed_test["mean_cost"] < within_test["mean_cost"]
            and observed_test["mean_cost"] < order_test["mean_cost"]
        ),
        "both_zl_test_coverages_at_least_99_percent": (
            observed_test["unit_coverage"] >= 0.99
            and observed_test["eva_codepoint_coverage"] >= 0.99
        ),
    }
    assert result["manuscript_stage"]["gates"] == expected_gates, result["manuscript_stage"]
    latin_positions = model.indices(fixture_config["control_test_plaintext"])
    latin_sum = model.score_indices(latin_positions, tuple(range(26)))
    latin_mean = latin_sum / (len(latin_positions) - 3)
    assert math.isclose(metrics["latin_test_mean"], latin_mean, rel_tol=1e-12, abs_tol=1e-8), metrics
    assert private["exclusions"]["ZL"] == {
        "non_paragraph": 1, "empty": 1, "excluded_token": 1,
        "interrupted": 2, "eligible": 3,
    }, private["exclusions"]
    assert private["exclusions"]["IT"] == {
        "non_paragraph": 0, "empty": 0, "excluded_token": 0,
        "interrupted": 0, "eligible": 3,
    }, private["exclusions"]

    # Compare both shuffles with the fixed random operation, and keep unknowns.
    shuffle = private["shuffles"]
    original_words = private["words"]["ZL"]
    for split, seed in zip(("train", "validation", "test"), (508, 509, 510), strict=True):
        original = original_words[split]
        actual = shuffle["within_word_shuffle"][split]["words"]
        expected = []
        rng = random.Random(seed)
        for units in original:
            moved = list(units)
            rng.shuffle(moved)
            expected.append(moved)
        assert actual == expected, actual
        assert Counter(unit for word in original for unit in word) == Counter(
            unit for word in actual for unit in word
        ), actual
        assert any(unit not in COMMON for word in original for unit in word) == any(
            unit not in COMMON for word in actual for unit in word
        ), actual
    for split, seed in zip(("train", "validation", "test"), (608, 609, 610), strict=True):
        expected = list(original_words[split])
        random.Random(seed).shuffle(expected)
        actual = shuffle["word_order_shuffle"][split]["words"]
        assert actual == expected, actual
        assert Counter(tuple(word) for word in actual) == Counter(
            tuple(word) for word in original_words[split]
        ), actual

    replay = base / "replay"
    replay_run = _run(fixture_path, replay, log_path=base / "logs/replay.json")
    assert replay_run.returncode == 0, replay_run.stderr
    main_hashes = _tree_hashes(out)
    replay_hashes = _tree_hashes(replay)
    deterministic_main = {name: digest for name, digest in main_hashes.items()
                          if name != "execution.json"}
    deterministic_replay = {name: digest for name, digest in replay_hashes.items()
                            if name != "execution.json"}
    assert deterministic_main == deterministic_replay, (deterministic_main, deterministic_replay)
    return {"controls": len(result["calibration"]["controls"]),
            "gates": expected_gates, "fit_names": sorted(fits),
            "unknown_outside_labels_absent_from_observed_map": True,
            "byte_replay_equal_except_execution_receipt": True,
            "deterministic_output_hashes": deterministic_main}


def _invariance_and_failure_checks(base):
    a_path = base / "fixture-a.json"
    b_path = base / "fixture-b.json"
    _write_json(base / "manuscript-a.json", {"schema_version": 1, "records": _records("xqoe")})
    _write_json(base / "manuscript-b.json", {"schema_version": 1, "records": _records("qoxe")})
    _write_json(a_path, _fixture(manuscript_name="manuscript-a.json"))
    _write_json(b_path, _fixture(manuscript_name="manuscript-b.json"))
    out_a, out_b = base / "invariance-a", base / "invariance-b"
    run_a = _run(a_path, out_a, log_path=base / "logs/invariance-a.json")
    run_b = _run(b_path, out_b, log_path=base / "logs/invariance-b.json")
    assert run_a.returncode == run_b.returncode == 0, (run_a.stderr, run_b.stderr)
    private_a = _json(out_a / "manuscript/private.json")
    private_b = _json(out_b / "manuscript/private.json")
    fit_a = {name: (item["key_positions"], item["fit_score"])
             for name, item in private_a["fits"].items()}
    fit_b = {name: (item["key_positions"], item["fit_score"])
             for name, item in private_b["fits"].items()}
    assert fit_a == fit_b, (fit_a, fit_b)

    # This fixture must fail before the unavailable manuscript path is opened.
    fail_config = _fixture(control_fit="a" * 276, control_test="xyz" * 92,
                           manuscript_name="does-not-exist.json")
    fail_path = base / "failure-fixture.json"
    _write_json(fail_path, fail_config)
    failed_out = base / "calibration-failed"
    failed = _run(fail_path, failed_out, log_path=base / "logs/calibration-failed.json")
    assert failed.returncode == 0, failed.stderr
    result = _json(failed_out / "result.json")
    assert result["calibration"]["accepted"] is False, result
    assert result["manuscript_stage"]["status"] == "blocked", result
    assert len(result["calibration"]["controls"]) == 4, result
    assert [item["seed"] for item in result["calibration"]["controls"]] == [408, 409, 410, 411], result
    failed_controls = _json(failed_out / "calibration/private.json")["controls"]
    assert any(not item["passed"] for item in failed_controls), failed_controls
    assert not (failed_out / "manuscript").exists(), "Failed calibration opened manuscript stage"

    # A short held-out stream fails after all three training maps are saved.
    short_fixture_path = base / "short-heldout-fixture.json"
    short_manuscript_path = base / "short-heldout-manuscript.json"
    _write_json(short_manuscript_path, {"schema_version": 1, "records": _records(short_test=True)})
    _write_json(short_fixture_path, _fixture(manuscript_name=short_manuscript_path.name))
    short_out = base / "short-heldout-error"
    short = _run(short_fixture_path, short_out, log_path=base / "logs/short-heldout-error.json")
    assert short.returncode != 0, short.stderr
    short_result = _json(short_out / "result.json")
    assert short_result["calibration"]["accepted"] is True, short_result
    assert short_result["manuscript_stage"]["status"] == "error", short_result
    assert short_result["current_stage"] == "manuscript_scoring", short_result
    saved_maps = sorted((short_out / "manuscript").glob("frozen-fit-key-*.json"))
    assert len(saved_maps) == 3, [path.name for path in saved_maps]
    assert (short_out / "error.json").is_file(), "Held-out scoring failure did not preserve an error record"
    short_error = _json(short_out / "error.json")
    assert short_error["stage"] == "manuscript_scoring", short_error
    assert "four" in str(short_error).lower() or "4" in str(short_error), short_error

    # A missing manuscript file after successful controls keeps all calibration evidence.
    late_fixture = _fixture(manuscript_name="missing-after-calibration.json")
    late_fixture_path = base / "late-fixture.json"
    _write_json(late_fixture_path, late_fixture)
    late_out = base / "late-manuscript-error"
    late = _run(late_fixture_path, late_out, log_path=base / "logs/late-manuscript-error.json")
    assert late.returncode != 0, late.stderr
    late_result = _json(late_out / "result.json")
    assert late_result["calibration"]["accepted"] is True, late_result
    assert len(_json(late_out / "calibration/private.json")["controls"]) == 4
    assert (late_out / "error.json").is_file(), "Late input error did not preserve a partial receipt"
    late_error = _json(late_out / "error.json")
    assert late_error["stage"] == "manuscript_loading", late_error
    assert "manuscript" in str(late_error).lower(), late_error
    return {"test_only_fit_invariance": True,
            "failed_controls": len(result["calibration"]["controls"]),
            "manuscript_stage": result["manuscript_stage"]["status"],
            "heldout_error_saved_all_three_maps": len(saved_maps) == 3,
            "missing_manuscript_after_pass_kept_calibration": late_result["calibration"]["accepted"] is True}


def _refusal_checks(base):
    # A pre-existing directory must remain byte-for-byte unchanged.
    existing = base / "existing-output"
    existing.mkdir()
    (existing / "keep.txt").write_text("keep\n", encoding="utf-8")
    before = _tree_hashes(existing)
    fixture = base / "existing-fixture.json"
    _write_json(fixture, _fixture())
    refused = _run(fixture, existing, log_path=base / "logs/existing-output-refused.json")
    after = _tree_hashes(existing)
    assert refused.returncode != 0 and before == after, (refused.stderr, before, after)
    assert refused.stderr == "error: Output directory already exists.\n", refused.stderr

    # Stop before output creation if a frozen file hash differs.
    freeze = {
        "schema_version": 1,
        "files": {
            name: _sha256((ROOT / name).read_bytes()) for name in FREEZE_PATHS
        },
    }
    freeze["files"]["src/voynich/groups.py"] = "0" * 64
    freeze_path = base / "bad-freeze.json"
    _write_json(freeze_path, freeze)
    bad_out = base / "bad-freeze-output"
    bad = subprocess.run(
        [sys.executable, str(RUNNER), "--freeze", str(freeze_path), "--output", str(bad_out)],
        cwd=ROOT, capture_output=True, text=True, timeout=30,
    )
    assert bad.returncode != 0 and not bad_out.exists(), bad.stderr
    assert bad.stderr == "error: Freeze hash mismatch: src/voynich/groups.py\n", bad.stderr
    return {"existing_output_unchanged": before == after,
            "freeze_mismatch_refused_before_output": not bad_out.exists()}


def _source_free_real_flag_check(base):
    """Exercise real-mode setup with a valid freeze and no source data."""
    isolated_root = (base / "isolated-real-project").resolve()
    for relative in FREEZE_PATHS:
        target = isolated_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, target)
    freeze = {
        "schema_version": 1,
        "files": {
            relative: _sha256((isolated_root / relative).read_bytes())
            for relative in FREEZE_PATHS
        },
    }
    freeze_path = (base / "isolated-valid-freeze.json").resolve()
    _write_json(freeze_path, freeze)
    output = (base / "isolated-real-output").resolve()
    command = [
        sys.executable,
        str(isolated_root / "experiments/common_visual/run.py"),
        "--freeze", str(freeze_path),
        "--output", str(output),
    ]
    completed = subprocess.run(
        command, cwd=isolated_root, capture_output=True, text=True, timeout=30
    )
    assert completed.returncode == 1, (completed.returncode, completed.stderr)
    assert output.is_dir(), completed.stderr
    result = _json(output / "result.json")
    error = _json(output / "error.json")
    assert result["mode"] == "real", result
    assert result["freeze"]["files"] == freeze["files"], result
    assert result["reference_provenance"] is None, result
    assert result["calibration"]["status"] == "not_started", result
    assert result["calibration"]["accepted"] is None, result
    assert result["manuscript_stage"]["status"] == "not_started", result
    assert result["current_stage"] == "reference", result
    assert error["stage"] == "reference", error
    assert error["message"] == "Cannot read the pinned Latin reference files.", error
    assert not (isolated_root / "data/raw").exists(), "The isolated project has no source data."
    return {
        "valid_freeze_accepted": True,
        "result_created_before_missing_reference_stop": True,
        "current_stage": result["current_stage"],
        "calibration_not_started": result["calibration"]["status"] == "not_started",
        "source_and_reference_data_absent": True,
    }


def _red_receipt(receipt_path):
    receipt = {
        "status": "red",
        "expected_failure": "The harness runs before run.py exists.",
        "runner_exists": RUNNER.is_file(),
        "setup": "No source corpus or real reference data is opened. The E2E harness uses only synthetic text.",
        "command": "python experiments/common_visual/check_e2e.py --receipt results/common-visual-pilot-2026-09-30/implementation/e2e-red.json",
        "plan_sha256": _sha256(PLAN.read_bytes()),
        "harness_sha256": _sha256(Path(__file__).read_bytes()),
        "steps": [
            "Create a synthetic common-unit cohort and synthetic Latin controls.",
            "Check source projection and unit positions against literal values.",
            "Check unknown-window scores against a literal loop.",
            "Run the pilot command after implementation.",
        ],
    }
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    with receipt_path.open("x", encoding="utf-8") as stream:
        json.dump(receipt, stream, sort_keys=True, indent=2)
        stream.write("\n")
    print(json.dumps(receipt, sort_keys=True, indent=2))
    return 2


def _green(receipt_path):
    if receipt_path.exists():
        raise FileExistsError(f"Receipt already exists: {receipt_path}")
    artifact_dir = receipt_path.parent / f"{receipt_path.stem}-artifacts"
    artifact_dir.mkdir(parents=True, exist_ok=False)
    base = artifact_dir
    try:
        projection = _projection_checks(base)
        search = _fit_search_checks()
        source_free_real = _source_free_real_flag_check(base)
        main_run = _check_main_output(base)
        invariance = _invariance_and_failure_checks(base)
        refusals = _refusal_checks(base)
        receipt = {
            "status": "passed",
            "setup": "Python standard library and synthetic fixtures only; no manuscript or real reference source is loaded.",
            "command": "python experiments/common_visual/check_e2e.py --receipt NEW_RECEIPT.json",
            "artifact_directory": artifact_dir.name,
            "plan_sha256": _sha256(PLAN.read_bytes()),
            "harness_sha256": _sha256(Path(__file__).read_bytes()),
            "runner_sha256": _sha256(RUNNER.read_bytes()),
            "projection_sha256": _sha256((ROOT / "experiments/common_visual/projection.py").read_bytes()),
            "search_sha256": _sha256((ROOT / "experiments/common_visual/search.py").read_bytes()),
            "fixture": {
                "alphabet": ALPHABET,
                "common_unit_count": len(COMMON),
                "control_seeds": list(CONTROL_SEEDS),
                "synthetic_record_count": len(_records()),
            },
            "steps": [
                "Compare parsed source tokens and every source position with literal values.",
                "Compare unknown-window costs and known-only search with the frozen scorer.",
                "Run all four synthetic controls and three common-unit manuscript fits.",
                "Check both fixed shuffles, the saved observed map on IT, and each gate value.",
                "Replay identical fixture input and compare every deterministic output byte.",
                "Change held-out test data and compare all fitted maps and fit scores.",
                "Confirm failed calibration does not read a missing manuscript fixture.",
                "Check refusal of an existing output directory and a mismatched freeze.",
                "Run real-mode setup with a valid freeze and no source or reference data.",
            ],
            "projection": projection,
            "search": search,
            "source_free_real_flag": source_free_real,
            "main_run": main_run,
            "invariance_and_failure": invariance,
            "refusals": refusals,
            "artifact_tree_hashes": _tree_hashes(artifact_dir),
            "limits": [
                "This test uses synthetic data only.",
                "It does not test a historical reference or manuscript source.",
            ],
        }
        receipt_path.parent.mkdir(parents=True, exist_ok=True)
        with receipt_path.open("x", encoding="utf-8") as stream:
            json.dump(receipt, stream, sort_keys=True, indent=2)
            stream.write("\n")
        print(json.dumps(receipt, sort_keys=True, indent=2))
        return 0
    except Exception as error:
        receipt = {
            "status": "failed",
            "setup": "Synthetic fixture run; no manuscript source or real reference is loaded.",
            "artifact_directory": artifact_dir.name,
            "plan_sha256": _sha256(PLAN.read_bytes()),
            "harness_sha256": _sha256(Path(__file__).read_bytes()),
            "runner_sha256": _sha256(RUNNER.read_bytes()) if RUNNER.exists() else None,
            "failure_type": type(error).__name__,
            "failure": str(error),
            "traceback": traceback.format_exc(),
            "artifact_tree_hashes": _tree_hashes(artifact_dir),
        }
        receipt_path.parent.mkdir(parents=True, exist_ok=True)
        with receipt_path.open("x", encoding="utf-8") as stream:
            json.dump(receipt, stream, sort_keys=True, indent=2)
            stream.write("\n")
        print(json.dumps(receipt, sort_keys=True, indent=2), file=sys.stderr)
        return 1


def main():
    if len(sys.argv) != 3 or sys.argv[1] != "--receipt":
        print("Usage: python experiments/common_visual/check_e2e.py --receipt NEW_RECEIPT.json",
              file=sys.stderr)
        return 2
    receipt_path = Path(sys.argv[2])
    if not RUNNER.is_file():
        return _red_receipt(receipt_path)
    try:
        return _green(receipt_path)
    except FileExistsError as error:
        print(str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
