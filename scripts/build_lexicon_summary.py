#!/usr/bin/env python3
"""Build the public lexicon pilot report from aggregate JSON records."""

from __future__ import annotations

import json
from pathlib import Path
from fractions import Fraction
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_REPORTS = ROOT / "reports" / "lexicon-pilot-v1"
OUTPUT = ROOT / "reports" / "LEXICON.md"

REFERENCE_RUNS = {
    "latin-reference": "Latin",
    "italian-reference": "Old Italian",
}
MANUSCRIPT_RUNS = {
    "latin-zl": ("Latin", "ZL3b-n.txt"),
    "latin-it": ("Latin", "IT2a-n.txt"),
    "italian-zl": ("Old Italian", "ZL3b-n.txt"),
    "italian-it": ("Old Italian", "IT2a-n.txt"),
}


def load_json(name: str) -> dict[str, Any]:
    path = PUBLIC_REPORTS / f"{name}.json"
    if not path.is_file():
        raise FileNotFoundError(f"Missing public lexicon report: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"The public lexicon report is not an object: {path}")
    return value


def percent(value: float | None, digits: int = 1) -> str:
    if value is None:
        return "n/a"
    return f"{value * 100:.{digits}f}%"


def bound_percent(result: dict[str, Any], bound: str) -> str:
    solver = result["solver"]
    denominator = result["objective"]["denominator"]
    if not denominator:
        return "n/a"
    scaled_numerator = solver[bound] * 10000
    if bound == "lower_bound":
        scaled = scaled_numerator // denominator
    elif bound == "upper_bound":
        scaled = (scaled_numerator + denominator - 1) // denominator
    else:
        raise ValueError(f"Unknown bound: {bound}")
    return f"{scaled / 100:.2f}%"


def integer(value: int) -> str:
    return f"{value:,}"


def report_link(name: str) -> str:
    return f"[JSON](lexicon-pilot-v1/{name}.json)"


def key_link(name: str) -> str:
    return f"[key](lexicon-pilot-v1/{name}.keys.json)"


def validate_records(records: dict[str, dict[str, Any]]) -> None:
    for name, result in records.items():
        if result.get("node_budget") != 10000:
            raise ValueError(f"Unexpected node budget in {name}")
        if result.get("bound_engine") != "bitset":
            raise ValueError(f"Unexpected bound engine in {name}")
        solver = result["solver"]
        objective = result["objective"]
        if (
            objective["weights_total"] != objective["denominator"]
            or objective["weights_match_denominator"] is not True
        ):
            raise ValueError(f"Objective denominator mismatch in {name}")
        if solver["total_weight"] != objective["denominator"]:
            raise ValueError(f"Solver denominator mismatch in {name}")
        if not (PUBLIC_REPORTS / f"{name}.keys.json").is_file():
            raise FileNotFoundError(f"Missing public key record for {name}")
        if result.get("kind") == "reference":
            if not solver["score_certified"] or not solver["search_exhausted"]:
                raise ValueError(f"Reference score is not certified in {name}")
            if solver["lower_bound"] != solver["upper_bound"]:
                raise ValueError(f"Reference bounds differ in {name}")
        elif result.get("kind") == "manuscript":
            if (
                solver["nodes"] != 10000
                or solver["status"] != "budget_exhausted"
                or solver["search_exhausted"]
                or solver["score_certified"]
            ):
                raise ValueError(f"Unexpected manuscript status in {name}")
        else:
            raise ValueError(f"Unknown run kind in {name}")


def reference_table(records: dict[str, dict[str, Any]]) -> list[str]:
    lines = [
        "| Corpus | Fit mean score (reference validation) (token / type) | Test characters | Test tokens | Key assignments | Certified score | Optimal-key lower bound | Artifacts |",
        "| --- | ---: | ---: | ---: | ---: | --- | ---: | --- |",
    ]
    for name, label in REFERENCE_RUNS.items():
        result = records[name]
        objective = result["objective"]
        hits = objective["fit_hits"]
        test = result["reference_accuracy"]
        lines.append(
            f"| {label} | {percent(objective['normalized_score'])} "
            f"({percent(hits['token_hit_rate'])} / {percent(hits['type_hit_rate'])}) | "
            f"{percent(test['exact_character_accuracy'])} | "
            f"{percent(test['exact_word_accuracy'])} | "
            f"{integer(test['key_exact_correct'])}/{integer(test['key_exact_total'])} | "
            f"yes | {integer(result['ambiguity']['optimal_key_count_lower_bound'])} | "
            f"{report_link(name)}; {key_link(name)} |"
        )
    return lines


def manuscript_table(records: dict[str, dict[str, Any]]) -> list[str]:
    lines = [
        "| Lexicon | Source | Train lower score bound | Train upper score bound | Nodes | Optimum status | Test token hits | Test type hits | Test mapped / unmapped (tokens; types) | Artifacts |",
        "| --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: | --- |",
    ]
    for name, (language, source) in MANUSCRIPT_RUNS.items():
        result = records[name]
        solver = result["solver"]
        test = result["scores"]["test"]
        lines.append(
            f"| {language} | `{source}` | {bound_percent(result, 'lower_bound')} | "
            f"{bound_percent(result, 'upper_bound')} | {integer(solver['nodes'])} | "
            f"not certified; budget exhausted | {integer(test['token_hits'])}/{integer(test['token_count'])} | "
            f"{integer(test['type_hits'])}/{integer(test['type_count'])} | "
            f"{integer(test['mapped_token_count'])}/{integer(test['unmapped_token_count'])}; "
            f"{integer(test['mapped_type_count'])}/{integer(test['unmapped_type_count'])} | "
            f"{report_link(name)}; {key_link(name)} |"
        )
    return lines


def largest_upper_bound(records: dict[str, dict[str, Any]]) -> str:
    name = max(
        MANUSCRIPT_RUNS,
        key=lambda run: Fraction(
            records[run]["solver"]["upper_bound"],
            records[run]["objective"]["denominator"],
        ),
    )
    return bound_percent(records[name], "upper_bound")


def reproduction_commands() -> list[str]:
    return [
        "mkdir -p results/reproduction-lexicon-v1",
        "python experiments/lexicon/run_pilot.py --kind reference --language latin_llct --node-budget 10000 --seed 500 --bound-engine bitset --output results/reproduction-lexicon-v1/latin-reference.json",
        "python experiments/lexicon/run_pilot.py --kind reference --language italian_old --node-budget 10000 --seed 500 --bound-engine bitset --output results/reproduction-lexicon-v1/italian-reference.json",
        "python experiments/lexicon/run_pilot.py --kind manuscript --language latin_llct --source ZL3b-n.txt --node-budget 10000 --bound-engine bitset --output results/reproduction-lexicon-v1/latin-zl.json",
        "python experiments/lexicon/run_pilot.py --kind manuscript --language latin_llct --source IT2a-n.txt --node-budget 10000 --bound-engine bitset --output results/reproduction-lexicon-v1/latin-it.json",
        "python experiments/lexicon/run_pilot.py --kind manuscript --language italian_old --source ZL3b-n.txt --node-budget 10000 --bound-engine bitset --output results/reproduction-lexicon-v1/italian-zl.json",
        "python experiments/lexicon/run_pilot.py --kind manuscript --language italian_old --source IT2a-n.txt --node-budget 10000 --bound-engine bitset --output results/reproduction-lexicon-v1/italian-it.json",
    ]


def build_report() -> str:
    records = {
        name: load_json(name)
        for name in (*REFERENCE_RUNS, *MANUSCRIPT_RUNS)
    }
    validate_records(records)

    lines = [
        "# Lexicon pilot v1",
        "",
        "The pilot measures exact word hits for one fixed injective key.",
        "An injective key maps each input symbol to one different lowercase letter.",
        "The reference lexicons and manuscript partitions are finite.",
        "The pilot does not decipher the Voynich manuscript.",
        "It does not identify a language, a translation, or a plaintext.",
        "The manuscript runs are exploratory.",
        "",
        "## Scope and score",
        "",
        "The runner fits a key on reference validation counts or manuscript train counts.",
        "Each reference lexicon uses its train partition.",
        "The score is the mean of the token hit rate and the type hit rate.",
        "For a type with count `n`, the integer weight is `n*T + N`.",
        "`T` is the type count and `N` is the token count.",
        "The score denominator is `2*T*N`.",
        "The JSON records contain the integer scores and denominators.",
        "",
        "The solver keeps every pattern candidate.",
        "The bitset bound is valid for every key in the tested finite domain.",
        "Equal bounds certify the optimum score for that finite problem.",
        "Unequal bounds leave the finite optimum unknown.",
        "The bound does not reject all keys, all Latin, all Italian, or all cipher models.",
        "The report keeps score proof and key recovery as separate measures.",
        "",
        "## Reproduction and documents",
        "",
        "The [finite lexicon protocol](../docs/plans/lexicon-feasibility-v1.md) fixes the inputs and search settings.",
        "The [lexicon experiment notes](../experiments/lexicon/README.md) define the score and ambiguity calculation.",
        "The [stage methods](../docs/research/stage2-methods.md) describe the reference and manuscript data limits.",
        "Use new output paths because the runner refuses existing result and key files.",
        "Run these commands from the repository root:",
        "",
        "```sh",
        *reproduction_commands(),
        "```",
        "",
        "## Reference controls",
        "",
        "Each control uses one seeded key and the complete reference test partition.",
        "The solver does not receive the planted key.",
        "The test character and token values measure recovery for the observed test symbols.",
        "They do not measure recovery of unused alphabet symbols.",
        "",
        *reference_table(records),
        "",
        "Both controls recovered every test character and every test token.",
        "The Italian control recovered 21 of 24 fitted key assignments.",
        "At least 60 optimal key completions exist for the Italian control.",
        "A count of one does not prove key uniqueness.",
        "The Italian count of at least 60 demonstrates objective ambiguity.",
        "",
        "These controls are positive controls for the new lexicon runner.",
        "The earlier 32-key n-gram study is a separate experiment.",
        "These controls do not estimate a false-positive rate.",
        "",
        "## Manuscript runs",
        "",
        "The four manuscript runs used the two reference lexicons and two pinned transcriptions.",
        "Each run used all eligible v3 training words and a 10,000-node budget.",
        "Each run reached its node budget before score certification.",
        "The bound percentages use the integer score denominator.",
        "The test columns report exact finite-lexicon hits for the returned key.",
        "",
        *manuscript_table(records),
        "",
        "The displayed manuscript lower bounds range from 2.96% to 5.36%.",
        "The four upper bounds remain unequal to their lower bounds.",
        "Therefore, the runs do not certify an optimum score.",
        f"The largest outward-rounded training upper bound is {largest_upper_bound(records)}.",
        "Across these four finite training problems, every key has a score at or below 35.51% under its corresponding lexicon and partition.",
        "This conditional bound applies to the tested training partitions and finite lexicons.",
        "It does not apply to test scores, the full manuscript, other lexicons, or other models.",
        "Each test partition has one unmapped token and one unmapped type.",
        "The test hit rates are descriptive results for fixed inputs and returned keys.",
        "Reference corpus comparisons are descriptive because genre and vocabulary differ.",
        "",
        "Each public JSON record contains source, code, and key-record SHA-256 values.",
        "The key records contain the returned keys without corpus word arrays.",
        "The [verification receipt](lexicon-verification.json) records byte checks for the published artifacts.",
        "",
        "## Limits",
        "",
        "The manuscript runs provide no false-positive calibration.",
        "They do not reject all keys or all candidate languages.",
        "They do not provide a translation or a decipherment.",
        "A finite lexicon hit does not establish historical meaning.",
        "The results do not support a universal threshold.",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    OUTPUT.write_text(build_report(), encoding="utf-8")
    print(OUTPUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
