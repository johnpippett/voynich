"""Check the fixed Strong worksheet arithmetic; do not decode manuscript text."""

import json
import math
from pathlib import Path
import sys


def calculate(record):
    numeric = record["numeric"]
    sequence = "".join(numeric["groups"])
    unknown = numeric["unknown_marker"]
    cycle = numeric["candidate_cycle"]
    periods = []
    for period in range(1, len(sequence) + 1):
        classes = {}
        for index, value in enumerate(sequence):
            if value != unknown:
                classes.setdefault(index % period, set()).add(value)
        if all(len(values) == 1 for values in classes.values()):
            periods.append(period)
    mismatches = [
        {"position": index + 1, "observed": int(value),
         "expected": cycle[index % len(cycle)]}
        for index, value in enumerate(sequence)
        if value != unknown and int(value) != cycle[index % len(cycle)]
    ]

    shift = record["shift"]
    alphabet = shift["alphabet"]
    operations = {}
    for name, direction in (("add", 1), ("subtract", -1)):
        rows = []
        for item in shift["positions"]:
            outputs = [
                alphabet[(alphabet.index(letter) + direction * item["lower_digit"])
                         % len(alphabet)]
                for letter in item["candidate_columns"]
            ]
            rows.append({
                "position": item["position"], "outputs": outputs,
                "target_letters": item["target_letters"],
                "matching_targets": sorted(set(outputs) & set(item["target_letters"])),
            })
        operations[name] = {
            "positions": rows,
            "combination_count": math.prod(len(set(row["outputs"])) for row in rows),
            "all_targets_compatible": all(bool(row["matching_targets"]) for row in rows),
        }
    return {
        "numeric": {
            "sequence": sequence, "positions": len(sequence),
            "known_positions": sum(value != unknown for value in sequence),
            "unknown_positions": sum(value == unknown for value in sequence),
            "candidate_cycle_length": len(cycle), "mismatches": mismatches,
            "compatible_period_lengths": periods,
        },
        "shift": {"alphabet_length": len(alphabet), "operations": operations},
    }


def main():
    if len(sys.argv) != 2:
        raise SystemExit("Supply the public worksheet JSON file.")
    record = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    result = calculate(record)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if result != record["expected"]:
        raise SystemExit("Calculation differs from the recorded result.")


if __name__ == "__main__":
    main()
