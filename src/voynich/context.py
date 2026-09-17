"""Exploratory held-out word-context scores.

This module measures next-word predictability.  It does not assign a language
or meaning to the transcription.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
import hashlib
import json
import math
import random
from typing import Iterable

from .groups import group_id, grouping_config, split_bucket, split_name


_GROUPING_CONFIG = grouping_config()
_SPLIT_HASH_PREFIX = _GROUPING_CONFIG["split_hash_salt"]
_UNKNOWN = "<UNK>"
_TAU = 10.0
_ADD_ALPHA = 0.1
_MIN_TRAINING_COUNT = 2
_SPLITS = ("train", "validation", "test")

__all__ = ["run_context"]


@dataclass(frozen=True)
class _Line:
    """One eligible paragraph line and its folio group."""

    group: str
    folio: str
    locus: str
    tokens: tuple[str, ...]


@dataclass
class _Model:
    """A smoothed unigram and interpolated word bigram model."""

    vocabulary: tuple[str, ...]
    known_words: frozenset[str]
    training_types: frozenset[str]
    unigram_counts: Counter[str]
    unigram_probabilities: dict[str, float]
    bigram_counts: dict[str, Counter[str]]
    context_counts: Counter[str]
    tau: float = _TAU

    def map_word(self, word: str) -> str:
        """Map a raw token to the training vocabulary or ``<UNK>``."""

        return word if word in self.known_words else _UNKNOWN

    def unigram_probability(self, target: str) -> float:
        """Return the add-alpha probability of one mapped target."""

        return self.unigram_probabilities[target]

    def bigram_probability(self, previous: str, target: str) -> float:
        """Return the fixed-tau interpolated probability of one pair."""

        context_count = self.context_counts.get(previous, 0)
        pair_count = self.bigram_counts.get(previous, {}).get(target, 0)
        return (pair_count + self.tau * self.unigram_probabilities[target]) / (
            context_count + self.tau
        )


def _group_id(record: dict) -> str:
    """Return the conservative folio group for one record."""

    return group_id(record.get("folio", ""))


def _bucket(group: str) -> int:
    return split_bucket(group)


def _split_for_group(group: str) -> str:
    return split_name(split_bucket(group))


def _group_sort_key(group: str) -> tuple[int, str]:
    if group.isdigit():
        return (0, f"{int(group):012d}")
    return (1, group)


def _sorted_groups(values: Iterable[str]) -> list[str]:
    return sorted(set(values), key=_group_sort_key)


def _record_token_count(record: dict) -> int:
    tokens = record.get("tokens", ())
    return len(tokens) if isinstance(tokens, (list, tuple)) else 0


def _manifest(records: list[dict]) -> tuple[dict, dict[str, str]]:
    """Build the conservative folio-group manifest and split map."""

    group_rows: dict[str, dict[str, object]] = {}
    split_records: dict[str, list[int]] = {split: [] for split in _SPLITS}
    record_splits: dict[str, str] = {}
    for index, record in enumerate(records):
        group = _group_id(record)
        split = _split_for_group(group)
        record_splits[str(index)] = split
        split_records[split].append(index)
        row = group_rows.setdefault(
            group,
            {
                "bucket": _bucket(group),
                "folios": set(),
                "record_indices": [],
                "split": split,
            },
        )
        row["folios"].add(str(record.get("folio", "")))  # type: ignore[union-attr]
        row["record_indices"].append(index)  # type: ignore[union-attr]

    manifest: dict[str, object] = {
        "grouping_config": dict(_GROUPING_CONFIG),
        "hash_prefix": _SPLIT_HASH_PREFIX,
        "rule": "conservative folio group; bucket 0/1=test, 2=validation, 3..9=train",
    }
    for split in _SPLITS:
        groups = [
            group
            for group in _sorted_groups(group_rows)
            if group_rows[group]["split"] == split
        ]
        folios = sorted(
            {
                folio
                for group in groups
                for folio in group_rows[group]["folios"]  # type: ignore[union-attr]
            }
        )
        record_indices = list(split_records[split])
        buckets = sorted({group_rows[group]["bucket"] for group in groups})
        group_manifest = [
            {
                "group": group,
                "leaf": group,
                "bucket": group_rows[group]["bucket"],
                "folios": sorted(group_rows[group]["folios"]),  # type: ignore[arg-type]
                "record_indices": list(group_rows[group]["record_indices"]),  # type: ignore[arg-type]
            }
            for group in groups
        ]
        manifest[split] = {
            "split": split,
            "groups": groups,
            # Keep the prior key as a compatibility alias. It now contains
            # Conservative folio groups are not a complete codicology map.
            "leaves": groups,
            "folios": folios,
            "buckets": buckets,
            "bucket": buckets[0] if len(buckets) == 1 else None,
            "record_indices": record_indices,
            "record_count": len(record_indices),
            "token_count": sum(_record_token_count(records[index]) for index in record_indices),
            "group_manifest": group_manifest,
            "leaf_manifest": group_manifest,
        }

    payload = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode("utf-8")
    manifest_hash = hashlib.sha256(payload).hexdigest()
    manifest["manifest_hash"] = manifest_hash
    return manifest, record_splits


def _prepare_lines(records: list[dict]) -> tuple[dict[str, list[_Line]], Counter[str]]:
    """Select complete paragraph lines and record each exclusion reason."""

    lines = {split: [] for split in _SPLITS}
    excluded: Counter[str] = Counter()
    for record in records:
        kind = str(record.get("kind", ""))
        if not kind.startswith("P"):
            excluded["not_paragraph"] += 1
            continue
        if record.get("excluded_tokens", 0):
            excluded["excluded_tokens"] += 1
            continue
        # The parser marks an interruption where a diagram breaks the line.
        # Such a line does not provide a clean word adjacency observation.
        if any(marker in str(record.get("text_raw", "")) for marker in ("<->", "<~>")):
            excluded["interrupted_line"] += 1
            continue
        tokens = record.get("tokens", ())
        if not isinstance(tokens, (list, tuple)) or not all(
            isinstance(token, str) and token for token in tokens
        ):
            excluded["malformed_tokens"] += 1
            continue
        if len(tokens) < 3:
            excluded["fewer_than_three_words"] += 1
            continue
        group = _group_id(record)
        split = _split_for_group(group)
        lines[split].append(
            _Line(
                group=group,
                folio=str(record.get("folio", "")),
                locus=str(record.get("locus", "")),
                tokens=tuple(tokens),
            )
        )
    return lines, excluded


def _fit_model(lines: list[_Line]) -> _Model:
    """Fit the declared vocabulary, unigram, and word bigram model."""

    raw_counts: Counter[str] = Counter(
        token for line in lines for token in line.tokens
    )
    known_words = frozenset(
        token for token, count in raw_counts.items() if count >= _MIN_TRAINING_COUNT
    )
    vocabulary = tuple(sorted(known_words)) + (_UNKNOWN,)
    mapped_counts: Counter[str] = Counter({word: 0 for word in vocabulary})
    for token, count in raw_counts.items():
        mapped_counts[token if token in known_words else _UNKNOWN] += count

    denominator = sum(mapped_counts.values()) + _ADD_ALPHA * len(vocabulary)
    unigram_probabilities = {
        word: (mapped_counts[word] + _ADD_ALPHA) / denominator for word in vocabulary
    }

    pair_counts: dict[str, Counter[str]] = defaultdict(Counter)
    context_counts: Counter[str] = Counter()
    for line in lines:
        mapped = [
            token if token in known_words else _UNKNOWN for token in line.tokens
        ]
        for previous, target in zip(mapped, mapped[1:]):
            pair_counts[previous][target] += 1
            context_counts[previous] += 1

    return _Model(
        vocabulary=vocabulary,
        known_words=known_words,
        training_types=frozenset(raw_counts),
        unigram_counts=mapped_counts,
        unigram_probabilities=unigram_probabilities,
        bigram_counts=dict(pair_counts),
        context_counts=context_counts,
    )


def _model_summary(model: _Model, line_count: int) -> dict:
    """Return deterministic, inspectable model counts and normalization checks."""

    conditional_sums = {}
    for previous in model.vocabulary:
        conditional_sums[previous] = math.fsum(
            model.bigram_probability(previous, target)
            for target in model.vocabulary
        )
    return {
        "training_line_count": line_count,
        "training_token_count": sum(model.unigram_counts.values()),
        "training_transition_count": sum(model.context_counts.values()),
        "tau": model.tau,
        "add_alpha": _ADD_ALPHA,
        "vocabulary_min_training_count": _MIN_TRAINING_COUNT,
        "vocabulary": list(model.vocabulary),
        "known_training_words": sorted(model.known_words),
        "training_types": sorted(model.training_types),
        "training_type_count": len(model.training_types),
        "unknown_symbol": _UNKNOWN,
        "unigram_counts": {
            word: model.unigram_counts[word] for word in model.vocabulary
        },
        "unigram_probabilities": {
            word: model.unigram_probabilities[word] for word in model.vocabulary
        },
        "unigram_probability_sum": math.fsum(model.unigram_probabilities.values()),
        "context_counts": {
            word: model.context_counts.get(word, 0) for word in model.vocabulary
        },
        "bigram_counts": {
            previous: {
                target: count
                for target, count in sorted(model.bigram_counts.get(previous, {}).items())
            }
            for previous in sorted(model.bigram_counts)
        },
        "conditional_probability_sums": conditional_sums,
        "probability_sums": conditional_sums,
    }


def _score_unigram(model: _Model, lines: list[_Line]) -> dict:
    return _score(model, lines, bigram=False)


def _score_bigram(model: _Model, lines: list[_Line]) -> dict:
    return _score(model, lines, bigram=True)


def _score(model: _Model, lines: list[_Line], *, bigram: bool) -> dict:
    total_bits = 0.0
    scored_words = 0
    unknown_targets = 0
    unseen_targets = 0
    per_group: dict[str, dict[str, float | int]] = defaultdict(
        lambda: {
            "scored_words": 0,
            "total_bits": 0.0,
            "unknown_target_count": 0,
            "unseen_target_count": 0,
        }
    )
    for line in lines:
        group_total = per_group[line.group]
        for previous, raw_target in zip(line.tokens, line.tokens[1:]):
            previous_mapped = model.map_word(previous)
            target_mapped = model.map_word(raw_target)
            probability = (
                model.bigram_probability(previous_mapped, target_mapped)
                if bigram
                else model.unigram_probability(target_mapped)
            )
            bits = -math.log2(probability)
            total_bits += bits
            scored_words += 1
            group_total["scored_words"] += 1  # type: ignore[operator]
            group_total["total_bits"] += bits  # type: ignore[operator]
            if raw_target not in model.known_words:
                unknown_targets += 1
                group_total["unknown_target_count"] += 1  # type: ignore[operator]
            if raw_target not in model.training_types:
                unseen_targets += 1
                group_total["unseen_target_count"] += 1  # type: ignore[operator]

    bits_per_word = total_bits / scored_words if scored_words else None
    return {
        "scored_words": scored_words,
        "predicted_targets": scored_words,
        "target_positions": scored_words,
        "total_bits": total_bits,
        "nll_bits": total_bits,
        "bits_per_word": bits_per_word,
        "unknown_target_count": unknown_targets,
        "unseen_target_count": unseen_targets,
        "unknown_target_rate": unknown_targets / scored_words if scored_words else None,
        "unseen_target_rate": unseen_targets / scored_words if scored_words else None,
        "line_count": len(lines),
        "groups": _sorted_groups(line.group for line in lines),
        "leaves": _sorted_groups(line.group for line in lines),
        "per_group": {
            group: dict(values)
            for group, values in sorted(per_group.items(), key=lambda x: _group_sort_key(x[0]))
        },
        "per_leaf": {
            group: dict(values)
            for group, values in sorted(per_group.items(), key=lambda x: _group_sort_key(x[0]))
        },
    }


def _difference(a: dict, b: dict, *, numerator: str) -> dict:
    """Return ``a - b`` in total bits and bits per scored target."""

    total = a["total_bits"] - b["total_bits"]
    words = a["scored_words"]
    return {
        "total_bits": total,
        "scored_words": words,
        "bits_per_word": total / words if words else None,
        "definition": numerator,
    }


def _score_split(
    original_model: _Model,
    shuffled_model: _Model,
    lines: list[_Line],
) -> dict:
    unigram = _score_unigram(original_model, lines)
    original = _score_bigram(original_model, lines)
    shuffled = _score_bigram(shuffled_model, lines)
    # Positive values mean that the first model in the name has lower NLL.
    improvement = _difference(
        unigram,
        original,
        numerator="unigram total bits minus original bigram total bits; positive favors the bigram",
    )
    order_effect = _difference(
        shuffled,
        original,
        numerator="shuffled-training total bits minus original-training total bits; positive favors original order",
    )
    return {
        "unigram": unigram,
        "bigram_original": original,
        "bigram_shuffled_train": shuffled,
        "differences": {
            "bigram_improvement_over_unigram": improvement,
            "original_order_improvement_over_shuffled": order_effect,
        },
        "target_positions_match": (
            unigram["target_positions"]
            == original["target_positions"]
            == shuffled["target_positions"]
        ),
    }


def _test_group_sums(test_scores: dict) -> dict[str, dict[str, float | int]]:
    groups = set(test_scores["unigram"]["per_group"])
    result = {}
    for group in _sorted_groups(groups):
        unigram = test_scores["unigram"]["per_group"][group]
        original = test_scores["bigram_original"]["per_group"][group]
        shuffled = test_scores["bigram_shuffled_train"]["per_group"][group]
        result[group] = {
            "scored_words": unigram["scored_words"],
            "unigram_total_bits": unigram["total_bits"],
            "bigram_original_total_bits": original["total_bits"],
            "bigram_shuffled_train_total_bits": shuffled["total_bits"],
            "unknown_target_count": unigram["unknown_target_count"],
            "unseen_target_count": unigram["unseen_target_count"],
            "unknown_target_rate": (
                unigram["unknown_target_count"] / unigram["scored_words"]
                if unigram["scored_words"]
                else None
            ),
            "unseen_target_rate": (
                unigram["unseen_target_count"] / unigram["scored_words"]
                if unigram["scored_words"]
                else None
            ),
        }
    return result


def _percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    index = int(fraction * (len(ordered) - 1))
    return ordered[index]


def _bootstrap(per_group: dict[str, dict[str, float | int]], seed: int, draws: int) -> dict:
    groups = _sorted_groups(per_group)
    if not groups:
        empty = {"estimate": None, "interval": None}
        return {
            "unit": "folio_group",
            "draws": draws,
            "seed": seed,
            "leaf_count": 0,
            "group_count": 0,
            "interval_percent": [2.5, 97.5],
            "bigram_improvement_over_unigram_bits_per_word": empty,
            "original_order_improvement_over_shuffled_bits_per_word": empty.copy(),
            "interval": None,
            "per_group_score_sums": per_group,
            "per_leaf_score_sums": per_group,
        }

    total_words = sum(int(per_group[group]["scored_words"]) for group in groups)
    estimate_improvement = (
        sum(
            float(per_group[group]["unigram_total_bits"])
            - float(per_group[group]["bigram_original_total_bits"])
            for group in groups
        )
        / total_words
        if total_words
        else None
    )
    estimate_order = (
        sum(
            float(per_group[group]["bigram_shuffled_train_total_bits"])
            - float(per_group[group]["bigram_original_total_bits"])
            for group in groups
        )
        / total_words
        if total_words
        else None
    )

    rng = random.Random(seed)
    improvements: list[float] = []
    order_effects: list[float] = []
    for _ in range(draws):
        sample = [rng.choice(groups) for _ in groups]
        words = sum(int(per_group[group]["scored_words"]) for group in sample)
        if not words:
            continue
        improvements.append(
            sum(
                float(per_group[group]["unigram_total_bits"])
                - float(per_group[group]["bigram_original_total_bits"])
                for group in sample
            )
            / words
        )
        order_effects.append(
            sum(
                float(per_group[group]["bigram_shuffled_train_total_bits"])
                - float(per_group[group]["bigram_original_total_bits"])
                for group in sample
            )
            / words
        )

    improvement_interval = (
        [_percentile(improvements, 0.025), _percentile(improvements, 0.975)]
        if improvements
        else None
    )
    order_interval = (
        [_percentile(order_effects, 0.025), _percentile(order_effects, 0.975)]
        if order_effects
        else None
    )
    return {
        "unit": "folio_group",
        "draws": draws,
        "seed": seed,
        "leaf_count": len(groups),
        "group_count": len(groups),
        "interval_percent": [2.5, 97.5],
        "bigram_improvement_over_unigram_bits_per_word": {
            "estimate": estimate_improvement,
            "interval": improvement_interval,
        },
        "original_order_improvement_over_shuffled_bits_per_word": {
            "estimate": estimate_order,
            "interval": order_interval,
        },
        "interval": improvement_interval,
        "per_group_score_sums": per_group,
        "per_leaf_score_sums": per_group,
    }


def run_context(records: list[dict], seed: int = 408, bootstraps: int = 499) -> dict:
    """Run the exploratory held-out word-context experiment.

    Eligible input records are complete paragraph lines with at least three
    tokens, zero excluded tokens, and no diagram interruption marker (`<->` or
    `<~>`).  The
    first token of each line is a context only; no transition crosses a line.
    """

    if not isinstance(records, list):
        records = list(records)
    seed = int(seed)
    bootstraps = int(bootstraps)
    if bootstraps < 1:
        raise ValueError("bootstraps must be positive")

    manifest, record_splits = _manifest(records)
    lines, exclusions = _prepare_lines(records)
    original_model = _fit_model(lines["train"])

    shuffled_lines: list[_Line] = []
    shuffle_rng = random.Random(seed)
    for line in lines["train"]:
        tokens = list(line.tokens)
        shuffle_rng.shuffle(tokens)
        shuffled_lines.append(
            _Line(line.group, line.folio, line.locus, tuple(tokens))
        )
    shuffled_model = _fit_model(shuffled_lines)

    scores = {
        split: _score_split(original_model, shuffled_model, lines[split])
        for split in ("validation", "test")
    }
    test_group_sums = _test_group_sums(scores["test"])
    bootstrap = _bootstrap(test_group_sums, seed, bootstraps)

    record_counts = {split: 0 for split in _SPLITS}
    group_sets = {split: set() for split in _SPLITS}
    for split in record_splits.values():
        record_counts[split] += 1
    for index, record in enumerate(records):
        split = record_splits[str(index)]
        group_sets[split].add(_group_id(record))

    eligible_line_counts = {split: len(lines[split]) for split in _SPLITS}
    target_counts = {
        split: sum(max(0, len(line.tokens) - 1) for line in lines[split])
        for split in _SPLITS
    }
    training_transitions = sum(max(0, len(line.tokens) - 1) for line in lines["train"])
    counts = {
        "records": {"all": len(records), **record_counts},
        "leaves": {
            "all": len(set().union(*group_sets.values())) if group_sets else 0,
            **{split: len(group_sets[split]) for split in _SPLITS},
        },
        "groups": {
            "all": len(set().union(*group_sets.values())) if group_sets else 0,
            **{split: len(group_sets[split]) for split in _SPLITS},
        },
        "folios": {
            "all": len({str(record.get("folio", "")) for record in records}),
            **{
                split: len(manifest[split]["folios"])
                for split in _SPLITS
            },
        },
        "tokens": {
            "all": sum(_record_token_count(record) for record in records),
            **{
                split: int(manifest[split]["token_count"])
                for split in _SPLITS
            },
        },
        "eligible_lines": {"all": sum(eligible_line_counts.values()), **eligible_line_counts},
        "target_positions": {"all": sum(target_counts.values()), **target_counts},
        "training_transitions": training_transitions,
        "filtered_lines": dict(sorted(exclusions.items())),
    }

    return {
        "config": {
            "seed": seed,
            "split_hash_salt": _SPLIT_HASH_PREFIX,
            "split_hash_algorithm": "sha256",
            "split_hash_bytes": 8,
            "split_bucket_modulus": 10,
            "split_buckets": {"test": [0, 1], "validation": [2], "train": list(range(3, 10))},
            "bootstraps": bootstraps,
            "grouping_config": dict(_GROUPING_CONFIG),
            "split_hash_prefix": _SPLIT_HASH_PREFIX,
            "split_rule": "conservative folio group; bucket 0/1=test, 2=validation, 3..9=train",
            "tau": _TAU,
            "bigram_tau": _TAU,
            "add_alpha": _ADD_ALPHA,
            "unigram_add_alpha": _ADD_ALPHA,
            "vocabulary_min_count": _MIN_TRAINING_COUNT,
            "vocabulary_min_training_count": _MIN_TRAINING_COUNT,
            "unknown_symbol": _UNKNOWN,
            "line_filter": "kind starts P, excluded_tokens is zero, no <-> or <~>, and at least three tokens",
            "target_positions": "tokens 1 through n-1 within each eligible line",
            "training_shuffle": "fixed-seed random within-line shuffle; heldout lines remain original",
            "heldout_permutation_null": False,
        },
        "counts": counts,
        "split_manifest": manifest,
        "split_manifest_hash": manifest["manifest_hash"],
        "models": {
            "original": _model_summary(original_model, len(lines["train"])),
            "shuffled_train": _model_summary(shuffled_model, len(shuffled_lines)),
        },
        "scores": scores,
        "per_group_score_sums": test_group_sums,
        "per_leaf_score_sums": test_group_sums,
        "bootstrap": bootstrap,
        "caution": (
            "This exploratory result measures conditional next-word predictability. "
            "It does not establish a language, meaning, authorship, or a translation. "
            "Conditioning on paragraph lines, tokenization, transcription choices, "
            "folio groups, and exclusion of diagram interruptions can confound "
            "the order comparison; the conservative folio groups do not provide a complete codicology map."
        ),
    }
