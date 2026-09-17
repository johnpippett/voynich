#!/usr/bin/env python3
"""Build the public Stage 2 report from aggregate JSON artifacts."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
BIFOLIO_NAMES = ("zl-split", "zl-join", "it-split")
SUBSTITUTION_NAMES = ("latin-zl", "latin-it", "italian-zl", "italian-it")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def interval(value: dict) -> str:
    low, high = value["interval"]
    return f"{value['estimate']:+.3f} [{low:+.3f}, {high:+.3f}]"


def percent(value: float, digits: int = 1) -> str:
    return f"{value * 100:.{digits}f}%"


def language_label(language: str) -> str:
    return {
        "latin_llct": "Latin",
        "italian_old": "Old Italian",
    }[language]


def grouping_summary(result: dict) -> tuple[dict, dict]:
    config = result["predictive"]["config"]
    return config["grouping_config"], result["predictive"]["counts"]


def build_report() -> str:
    bifolio = {
        name: load_json(REPORTS / "bifolio-v3" / f"{name}.json")
        for name in BIFOLIO_NAMES
    }
    controls = {
        language: load_json(REPORTS / "substitution" / f"{name}.json")
        for language, name in (
            ("latin_llct", "latin-32keys"),
            ("italian_old", "italian-32keys"),
        )
    }
    substitutions = {
        name: load_json(REPORTS / "substitution" / f"{name}.json")
        for name in SUBSTITUTION_NAMES
    }
    naibbe = {
        mode: load_json(REPORTS / f"naibbe-{mode}.json")
        for mode in ("split", "join")
    }
    inventory = load_json(REPORTS / "substitution-inventory.json")
    invariants = load_json(REPORTS / "reference-invariants.json")

    first_grouping, _ = grouping_summary(bifolio["zl-split"])
    global_groups = first_grouping["group_count"]
    global_split = bifolio["zl-split"]["context"]["counts"]["groups"]
    prediction_counts = bifolio["zl-split"]["predictive"]["counts"]["groups"]
    manifest_hash = first_grouping["manifest_sha256"]
    split_salt = bifolio["zl-split"]["predictive"]["config"]["split_hash_salt"]

    text = [
        "# Stage 2 aggregate findings",
        "",
        "**The project has not deciphered the Voynich manuscript.**",
        "",
        "These results measure written structure and constrained model fits.",
        "They do not identify a language, a translation, or a plaintext.",
        "The experiments are exploratory.",
        "",
        "## Reproduction and provenance",
        "",
        "The [Stage 2 methods](../docs/research/stage2-methods.md) document defines the",
        "reference partitions, models, controls, and runner limits.",
        "Run these aggregate checks from the repository root:",
        "",
        "```text",
        "python scripts/build_stage2_summary.py",
        "python scripts/check_substitution_inventory.py",
        "python scripts/compare_reference_invariants.py",
        "```",
        "",
        "The report reads the aggregate JSON files and writes this file.",
        "The result files record source hashes, code hashes, and configuration.",
        "The [verification record](stage2-verification.json) records the execution and reproduction checks.",
        "Use the [README](../README.md) to fetch inputs and repeat the structural runs.",
        "Run the remaining searches in Bash with new output paths:",
        "",
        "```bash",
        "mkdir -p results/reproduction-stage2",
        "for language in latin_llct italian_old; do",
        '  python scripts/run_substitution_pilot.py --language "$language" --words 20000 --seeds {500..531} --output "results/reproduction-stage2/$language-controls.json"',
        "  for source in ZL3b-n.txt IT2a-n.txt; do",
        '    python scripts/run_voynich_substitution.py --language "$language" --source "$source" --output "results/reproduction-stage2/$language-$source.json"',
        "  done",
        "done",
        "python scripts/check_naibbe_compatibility.py --output results/reproduction-stage2/naibbe-split.json",
        "python scripts/check_naibbe_compatibility.py --uncertain-spaces join --output results/reproduction-stage2/naibbe-join.json",
        "```",
        "",
        "## Grouping and sampling",
        "",
        f"The global map has {global_groups} source-backed groups with {global_split['train']} train, {global_split['validation']} validation, and {global_split['test']} test groups.",
        f"The prediction artifacts use {prediction_counts['train'] + prediction_counts['validation'] + prediction_counts['test']} paragraph groups with {prediction_counts['train']} train, {prediction_counts['validation']} validation, and {prediction_counts['test']} test groups.",
        "Groups 71 and 73 have no eligible paragraph loci in these artifacts.",
        "The prior version 2 grouping is superseded for prediction.",
        "The `fRos` identifier maps to group 85.",
        f"The grouping version is `{first_grouping['version']}`. The split salt is `{split_salt}`.",
        f"The physical map manifest hash is `{manifest_hash}`.",
        "The map uses provider Q/B metadata. It has no independent conservation examination.",
        "",
        "The substitution runs select complete nonempty paragraph loci.",
        "They exclude records with excluded tokens and `<->` or `<~>` diagram interruptions.",
        "Each excluded locus appears in the first applicable category.",
        "Whole-locus filters remove 10,224 otherwise accepted ZL words and 5,911 IT words from paragraph loci.",
        "This selection can change the sample's word distribution.",
        "The `split` and `join` spacing policies remain separate runs.",
        "",
        "| Source | Not paragraph | No accepted tokens | Excluded tokens | Diagram interruptions | Eligible loci | Eligible words |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for source, name in (("ZL3b", "latin-zl"), ("IT2a", "latin-it")):
        filter_counts = substitutions[name]["sample_filter"]["counts"]
        text.append(
            f"| {source} | {filter_counts['not_paragraph']['records']:,} | "
            f"{filter_counts['no_accepted_tokens']['records']:,} | "
            f"{filter_counts['excluded_tokens']['records']:,} | "
            f"{filter_counts['diagram_interruption']['records']:,} | "
            f"{filter_counts['eligible']['records']:,} | "
            f"{filter_counts['eligible']['accepted_words']:,} |"
        )
    text.extend(
        [
            "",
            "## Character prediction",
            "",
            "The table gives order-three loss in bits per predicted unit.",
            "Loss denominators include the end-of-word symbol.",
            "Each value is a point estimate. These artifacts have no character confidence interval.",
            "Compare each observed value with the shuffled value in the same unitization.",
            "Raw-EVA and grouped-unit bits use different units and are not directly comparable.",
            "",
            "| Run | Raw observed | Raw shuffled | Grouped observed | Grouped shuffled |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for name in BIFOLIO_NAMES:
        scores = bifolio[name]["predictive"]["scores"]
        observed = scores["observed"]
        shuffled = scores["shuffled_null"]
        text.append(
            f"| {name} | {observed['raw_eva']['order_3']['bits_per_symbol']:.4f} | "
            f"{shuffled['raw_eva']['order_3']['bits_per_symbol']:.4f} | "
            f"{observed['grouped']['order_3']['bits_per_symbol']:.4f} | "
            f"{shuffled['grouped']['order_3']['bits_per_symbol']:.4f} |"
        )
    text.extend(
        [
            "",
            "In each unitization, the observed order-three loss is lower than its shuffled baseline.",
            "This result describes sequence structure. It does not identify meaning or language.",
            "",
            "## Word-context prediction",
            "",
            "The table gives test loss in bits per word.",
            "Unknown targets share one symbol. These losses do not score complete word identity.",
            "The intervals use 499 group-bootstrap draws and the 2.5 and 97.5 percentiles.",
            "The first delta is unigram loss minus original-order bigram loss.",
            "The second delta is shuffled-training loss minus original-order loss.",
            "",
            "| Run | Unigram | Original bigram | Shuffled-training bigram | Unigram - original [95% CI] | Shuffled - original [95% CI] |",
            "| --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for name in BIFOLIO_NAMES:
        result = bifolio[name]["context"]
        scores = result["scores"]["test"]
        bootstrap = result["bootstrap"]
        text.append(
            f"| {name} | {scores['unigram']['bits_per_word']:.4f} | "
            f"{scores['bigram_original']['bits_per_word']:.4f} | "
            f"{scores['bigram_shuffled_train']['bits_per_word']:.4f} | "
            f"{interval(bootstrap['bigram_improvement_over_unigram_bits_per_word'])} | "
            f"{interval(bootstrap['original_order_improvement_over_shuffled_bits_per_word'])} |"
        )
    text.extend(
        [
            "",
            "The original-order bigram has higher loss than the unigram in all three runs.",
            "The original-order bigram has lower loss than the shuffled-training bigram in all three runs.",
            "These comparisons do not show that the manuscript lacks language or word-order information.",
            "",
            "## Planted substitution controls",
            "",
            "The search recovered every held-out key assignment in 32 controls for each reference corpus.",
            "Each control uses the same sampled text and partition as the other keys in its corpus.",
            "The 32 keys are repeated controls on one partition, not 32 independent texts.",
            "The key measure covers symbol types that occur in held-out text.",
            "It does not claim recovery of unused alphabet entries.",
            "The pilot does not estimate a false-positive rate.",
            "",
            "| Reference corpus | Keys | Fit words | Held-out types | Held-out key assignment | Character recovery | Word recovery |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for language in ("latin_llct", "italian_old"):
        result = controls[language]
        metrics = [
            control["heldout"]["recovery_metrics"]
            for control in result["controls"]
        ]
        assert len(metrics) == 32
        assert all(
            metric[key] == 1.0
            for metric in metrics
            for key in (
                "key_assignment_accuracy",
                "exact_character_accuracy",
                "exact_word_accuracy",
            )
        )
        heldout_types = sorted({metric["key_assignment_total"] for metric in metrics})
        assert len(heldout_types) == 1
        text.append(
            f"| {language_label(language)} | {len(result['controls'])} | "
            f"{result['configuration']['fitting_words']:,} | {heldout_types[0]} | 32/32 (100%) | "
            "32/32 (100%) | 32/32 (100%) |"
        )
    text.extend(
        [
            "",
            "The controls calibrate recovery power for observed key assignments. They do not show that the Voynich text uses a substitution or a reference language.",
            f"The recovered Latin control has test loss {controls['latin_llct']['controls'][0]['heldout']['bits_per_symbol']:.4f} bits per symbol.",
            f"The recovered Old Italian control has test loss {controls['italian_old']['controls'][0]['heldout']['bits_per_symbol']:.4f} bits per symbol.",
            "These values describe different texts and symbol distributions. They are calibration values, not language-rejection thresholds.",
            "The reference texts contain Latin legal charters and Dante's poetry. Genre, date, spelling, and authorship differ from the unknown manuscript source.",
            "",
            "## Voynich substitution runs",
            "",
            "These runs use raw EVA units, fixed word boundaries, and an injective lowercase ASCII key.",
            "The key is fixed before test scoring.",
            "The runner fits the full eligible train partition and scores train, validation, and test.",
            "This report shows the test aggregates.",
            "The table reports test loss, lexicon hits, and the 32-key random-key range.",
            "All loss comparisons in this table use the same raw-EVA unit track for each source and language.",
            "",
            "| Language | Source | Test words | Observed bits/symbol | Within-word shuffle | Identity | Random-key range | Lexicon hits | Fully mapped |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for name in SUBSTITUTION_NAMES:
        result = substitutions[name]
        test = result["scores"]["test"]
        observed = test["observed"]
        random_baseline = result["random_key_test_baseline"]
        mapped = test["observed_lexicon"]["fully_mapped_tokens"]
        words = result["sample_words"]["test"]
        text.append(
            f"| {language_label(result['language'])} | `{result['source']}` | {words:,} | "
            f"{observed['bits_per_symbol']:.3f} | {test['shuffled']['bits_per_symbol']:.3f} | "
            f"{test['identity']['bits_per_symbol']:.3f} | "
            f"{random_baseline['minimum']:.3f}-{random_baseline['maximum']:.3f} | "
            f"{percent(test['observed_lexicon']['reference_vocabulary_hit_rate'])} | "
            f"{mapped:,}/{words:,} |"
        )
    text.extend(
        [
            "",
            "Observed test lexicon hits range from 8.6% to 11.3% in these four runs.",
            "The within-word shuffle hit rates are lower, from 5.3% to 7.2%.",
            "Each transcription has one unassigned test symbol type. One test occurrence remains partial.",
            "These runs do not reject all keys or all candidate languages.",
            "They do not produce a translation or a decipherment.",
            "",
            "## Naibbe table compatibility",
            "",
            "The 414 table rows encode 23 plaintext letters and produce 18,935 distinct bigram strings.",
            "The split runs accept about 78% of tokens. Join results differ by source.",
            "Compatibility measures whether a token has at least one reading under the fixed tables.",
            "Ambiguity counts full candidates, including table choices. Different candidates can share plaintext.",
            "Mean candidate counts include tokens with no reading, which contribute zero.",
            "",
            "| Mode | Source | Compatible tokens | Ambiguous tokens | Ambiguous types | Mean candidates | Maximum |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for mode in ("split", "join"):
        for source in ("ZL3b", "IT2a"):
            source_result = naibbe[mode]["sources"][source]
            compatible = source_result["parseable_token_count"]
            total = source_result["token_count"]
            text.append(
                f"| {mode} | {source} | {compatible:,}/{total:,} ({percent(compatible / total)}) | "
                f"{source_result['candidate_ambiguous_token_count']:,} | "
                f"{source_result['candidate_ambiguous_type_count']:,} | "
                f"{source_result['mean_candidate_count']:.3f} | "
                f"{source_result['max_candidate_count']} |"
            )
    text.extend(
        [
            "",
            "The table is fixed during this run. Its construction used Voynich features, so this compatibility test is circular.",
            "The run keeps candidate choices. It does not rank candidates or choose a language.",
            "The small `arma` control returned one candidate for each of `ar` and `ma`.",
            "That control does not recover plaintext from corpus tokens.",
            "The forward control does not simulate output space-removal joins.",
            "No corpus-wide unique plaintext result appears in this report.",
            "",
            "## Limits",
            "",
            "The inventory check finds 25 raw-EVA units for ZL3b and 21 for IT2a.",
            "The grouped unitizations have 33 and 29 units. An injective map to 26 lowercase ASCII letters is not feasible for those grouped counts.",
            "This is a conditional inventory result. It does not test another segmentation or encoding family.",
            "",
            "The reference invariant comparison uses finite vocabularies.",
            "It does not test one joint key, control every corpus difference, or reject a language.",
            "A failed heuristic search does not exhaust possible keys.",
            "No result in this report establishes a universal threshold.",
            "",
        ]
    )
    assert inventory["status"] == "conditional_inventory_constraint_not_decipherment"
    assert invariants["status"] == "exploratory_comparison_not_language_identification"
    return "\n".join(text).rstrip()


def main() -> None:
    path = REPORTS / "STAGE2.md"
    path.write_text(build_report() + "\n", encoding="utf-8")
    print(path)


if __name__ == "__main__":
    main()
