#!/usr/bin/env python3
"""Score a frozen boundary model on word-type novelty strata."""
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src"), str(ROOT / "scripts")]
from check_boundary_prediction import fit, pairs, position, score_rows  # noqa: E402
from run_local_memory_diagnostic import PINS, digest, write_new  # noqa: E402
from experiments.homophonic.units import units  # noqa: E402
from voynich.context import _prepare_lines  # noqa: E402
from voynich.corpus import parse_ivtff  # noqa: E402

OLD_DEPS = ("scripts/run_local_memory_diagnostic.py", "src/voynich/context.py",
            "src/voynich/corpus.py", "src/voynich/groups.py",
            "experiments/homophonic/units.py")


def summary(rows, probabilities, alphabet):
    rows = list(rows)
    if not rows:
        return {"status": "missing", "targets": 0, "reason": "no_eligible_pairs"}
    return {"status": "scored", **score_rows(rows, probabilities, alphabet)}


def strata(converted, source_rows, train_types, train_pairs):
    categories, primary, ordered = defaultdict(list), [], defaultdict(list)
    for (group, words), source_row in zip(converted, source_rows):
        raw = source_row.tokens
        if len(words) != len(raw):
            raise ValueError("unitization changed complete word count")
        for t in range(1, len(words)):
            previous, target = raw[t - 1], raw[t]
            row = (group, position(t, len(words)), words[t - 1][-1], words[t][0])
            unseen = int(previous not in train_types) + int(target not in train_types)
            categories[unseen].append(row)
            if unseen == 2:
                primary.append(row)
            ordered["seen" if (previous, target) in train_pairs else "unseen"].append(row)
    return categories, primary, ordered


def synthetic_check():
    source_rows = [type("R", (), {"tokens": ("aa", "bb", "cc", "dd")})()]
    converted = [("g", (("a",), ("b",), ("c",), ("d",)))]
    categories, primary, _ = strata(converted, source_rows, {"aa", "dd"}, {("aa", "bb")})
    if [row[1] for row in categories[2]] != ["interior"] or len(primary) != 1:
        raise ValueError("novelty mask changed original positions")
    if {key: len(value) for key, value in categories.items()} != {1: 2, 2: 1}:
        raise ValueError("synthetic novelty strata mismatch")


def run(source):
    filename, source_hash = PINS[source]
    source_path = ROOT / "data/raw" / filename
    if digest(source_path) != source_hash:
        raise ValueError("source hash mismatch")
    existing_path = ROOT / "results/boundary-prediction-v1" / f"{source}.json"
    existing = json.loads(existing_path.read_text())
    old_script = digest(ROOT / "scripts/check_boundary_prediction.py")
    old_deps = {name: digest(ROOT / name) for name in OLD_DEPS}
    if existing.get("script_sha256") != old_script:
        raise ValueError("existing result script hash mismatch")
    if existing.get("dependency_sha256") != old_deps:
        raise ValueError("existing result dependency hash mismatch")
    records = parse_ivtff(source_path, uncertain_spaces="split")
    parts, excluded = _prepare_lines(records)
    train_types = {word for row in parts["train"] for word in row.tokens}
    train_pairs = {(words[t - 1], words[t]) for row in parts["train"]
                   for words in (row.tokens,) for t in range(1, len(words))}
    counts = {split: {"lines": len(rows), "words": sum(len(row.tokens) for row in rows),
                      "groups": len({row.group for row in rows})}
              for split, rows in parts.items()}
    output = {"header": "This compares familiar phrase contribution with a transferable unit relation.",
              "source": source, "source_sha256": source_hash, "spacing": "split",
              "exploratory": True, "validation_used": False,
              "selection": "Nested after the overall result; descriptive only, with no causal inference.",
              "command": "PYTHONPATH=src python scripts/check_boundary_novelty.py",
              "script_sha256": digest(Path(__file__)), "existing_result_sha256": digest(existing_path),
              "existing_method_script_sha256": old_script, "dependency_sha256": old_deps,
              "counts": counts, "excluded_lines": dict(excluded),
              "train_word_type_count": len(train_types),
              "train_ordered_pair_type_count": len(train_pairs), "representations": {}}
    for representation in ("visual", "raw"):
        converted = [(row.group, tuple(units(word, representation=representation) for word in row.tokens))
                     for row in parts["test"]]
        train_converted = [(row.group, tuple(units(word, representation=representation) for word in row.tokens))
                           for row in parts["train"]]
        probabilities, alphabet = fit(train_converted)
        full = summary(pairs(converted), probabilities, alphabet)
        old = existing["representations"][representation]["observed"]
        errors = [abs(full[key] - old[key]) for key in ("baseline_bits_per_target", "conditional_bits_per_target", "gain_bits_per_target")]
        if full["targets"] != old["targets"] or max(errors, default=0.0) > 1e-10:
            raise RuntimeError(f"full {source}/{representation} score mismatch")
        categories, primary, ordered = strata(converted, parts["test"], train_types, train_pairs)
        record = {"train_line_count": len(train_converted), "test_line_count": len(converted),
                  "training_input_sha256": hashlib.sha256(json.dumps(train_converted, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
                  "full_test_verification": {"status": "matched", "targets": full["targets"], "max_abs_error": max(errors, default=0.0)},
                  "full_test_score": full, "primary_novelty_subset": summary(primary, probabilities, alphabet),
                  "coverage_categories": {str(number): summary(categories[number], probabilities, alphabet) for number in range(3)},
                  "ordered_pair_train_coverage": {name: summary(ordered[name], probabilities, alphabet) for name in ("seen", "unseen")}}
        output["representations"][representation] = record
    return output


if __name__ == "__main__":
    synthetic_check()
    output = ROOT / "results/boundary-prediction-v1/novelty.json"
    if output.exists():
        raise RuntimeError("novelty output already exists")
    write_new(output, {"schema": "boundary-prediction-novelty-v1", "sources": [run("ZL"), run("IT")]})
