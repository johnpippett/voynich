#!/usr/bin/env python3
"""Decompose the frozen same-tail expectation by target initial unit set."""
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src"), str(ROOT / "scripts")]
from check_boundary_same_tail import arrange, fit, score, score_rows  # noqa: E402
from run_local_memory_diagnostic import PINS, digest, write_new  # noqa: E402
from experiments.homophonic.units import units  # noqa: E402
from voynich.context import _prepare_lines  # noqa: E402
from voynich.corpus import parse_ivtff  # noqa: E402

SAME_TAIL = ROOT / "results/boundary-prediction-v1/same-tail.json"
OLD_BOUNDARY = ROOT / "scripts/check_boundary_prediction.py"
SAME_SCRIPT = ROOT / "scripts/check_boundary_same_tail.py"


def cell_stats(rows, cell, probabilities, alphabet):
    previous = [rows[i][2] for i in cell]
    baseline, observed, expected = [], [], []
    for i in cell:
        _, position, actual_previous, target = rows[i]
        p0, p1 = probabilities(position, actual_previous, target)
        baseline.append(-math.log2(p0))
        observed.append(-math.log2(p1))
        expected.append(math.fsum(-math.log2(probabilities(position, value, target)[1])
                                  for value in previous) / len(previous))
    return {
        "cell_count": 1, "target_count": len(cell),
        "observed_gain_bits": math.fsum(baseline) - math.fsum(observed),
        "expected_gain_bits": math.fsum(baseline) - math.fsum(expected),
    }


def run(source, published):
    filename, source_hash = PINS[source]
    source_path = ROOT / "data/raw" / filename
    old_path = ROOT / "results/boundary-prediction-v1" / f"{source}.json"
    old = json.loads(old_path.read_text())
    if digest(source_path) != source_hash or published["source_sha256"] != source_hash:
        raise ValueError("source hash mismatch")
    if published["script_sha256"] != digest(SAME_SCRIPT):
        raise ValueError("same-tail script hash mismatch")
    if published["preceding_result_sha256"] != digest(old_path):
        raise ValueError("same-tail preceding result hash mismatch")
    for name, value in old["dependency_sha256"].items():
        if digest(ROOT / name) != value:
            raise ValueError(f"dependency hash mismatch: {name}")
    parts, _ = _prepare_lines(parse_ivtff(source_path, uncertain_spaces="split"))
    output = {"source": source, "source_sha256": source_hash,
              "same_tail_result_sha256": digest(SAME_TAIL),
              "same_tail_script_sha256": digest(SAME_SCRIPT),
              "method_script_sha256": digest(OLD_BOUNDARY), "exploratory": True,
              "limit": "Descriptive decomposition of an observed-minus-exact-null contrast; no causal rule.",
              "representations": {}}
    for representation in ("visual", "raw"):
        convert = lambda rows: [(r.group, tuple(units(w, representation=representation) for w in r.tokens)) for r in rows]
        train, test = convert(parts["train"]), convert(parts["test"])
        rows, buckets, active, excluded = arrange(test, parts["test"])
        published_rep = published["representations"][representation]
        counts = (len(rows), excluded, len(buckets), len(active), sum(map(len, active)))
        expected_counts = (published_rep["eligible_targets"], published_rep["excluded_empty_target_tail"],
                           published_rep["strata"], published_rep["strata_variable_in_both_endpoints"],
                           published_rep["variable_targets"])
        if counts != expected_counts:
            raise ValueError(f"same-tail active counts mismatch: {source}/{representation}")
        probabilities, alphabet = fit(train)
        full = score(test, probabilities, alphabet)
        if abs(full["gain_bits_per_target"] - old["representations"][representation]["observed"]["gain_bits_per_target"]) > 1e-10:
            raise ValueError(f"original fit mismatch: {source}/{representation}")
        indices = [i for cell in active for i in cell]
        observed = score_rows([rows[i] for i in indices], probabilities, alphabet)
        if abs(observed["gain_bits_per_target"] - published_rep["observed_variable_subset"]["gain_bits_per_target"]) > 1e-10:
            raise ValueError(f"active fit mismatch: {source}/{representation}")
        aggregate = defaultdict(lambda: {"cell_count": 0, "target_count": 0,
                                         "observed_gain_bits": 0.0, "expected_gain_bits": 0.0})
        for cell in active:
            stats = cell_stats(rows, cell, probabilities, alphabet)
            key = tuple(sorted({rows[i][3] for i in cell}))
            item = aggregate[key]
            for name in ("cell_count", "target_count", "observed_gain_bits", "expected_gain_bits"):
                item[name] += stats[name]
        total = {name: sum(item[name] for item in aggregate.values())
                 for name in ("cell_count", "target_count", "observed_gain_bits", "expected_gain_bits")}
        total["excess_bits"] = total["observed_gain_bits"] - total["expected_gain_bits"]
        direct_observed = math.fsum(cell_stats(rows, cell, probabilities, alphabet)["observed_gain_bits"] for cell in active)
        direct_expected = math.fsum(cell_stats(rows, cell, probabilities, alphabet)["expected_gain_bits"] for cell in active)
        if total["cell_count"] != len(active) or total["target_count"] != len(indices):
            raise ValueError("active total count mismatch")
        if abs(total["observed_gain_bits"] - direct_observed) > 1e-10 or abs(total["expected_gain_bits"] - direct_expected) > 1e-10:
            raise ValueError("active total bit mismatch")
        components = []
        for key in sorted(aggregate):
            item = dict(aggregate[key]); item["target_initial_units"] = list(key)
            item["excess_bits"] = item["observed_gain_bits"] - item["expected_gain_bits"]
            components.append(item)
        output["representations"][representation] = {
            "eligible_targets": len(rows), "excluded_empty_target_tail": excluded,
            "active_cell_count": len(active), "active_target_count": len(indices),
            "active_totals": total, "components": components,
        }
    return output


if __name__ == "__main__":
    if SAME_TAIL.exists() is False:
        raise ValueError("same-tail result is missing")
    published = {row["source"]: row for row in json.loads(SAME_TAIL.read_text())["sources"]}
    output = ROOT / "results/boundary-prediction-v1/same-tail-components.json"
    if output.exists():
        raise ValueError("output exists")
    write_new(output, {"schema": "boundary-same-tail-components-v1",
                       "header": "This decomposes same-tail association by target initial-unit set.",
                       "sources": [run(source, published[source]) for source in ("ZL", "IT")]})
