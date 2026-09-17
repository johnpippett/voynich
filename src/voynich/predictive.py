"""Reproducible character prediction experiments for Voynich records."""

from __future__ import annotations

import json
import math
import random
from collections import Counter, defaultdict
from typing import Any, Iterable

from .groups import group_id, grouping_config, split_bucket, split_name


ADD_ALPHA = 0.1
START_SYMBOL = "<BOS>"
END_SYMBOL = "<EOS>"
UNKNOWN_SYMBOL = "<UNK>"
GROUPING_CONFIG = grouping_config()
SPLIT_HASH_SALT = GROUPING_CONFIG["split_hash_salt"]
NGRAM_ORDERS = (0, 1, 2, 3)

# These are declared transcription units. Matching uses the longest unit at
# each position, while preserving this declaration for the result report.
DECLARED_GROUPED_UNITS = ("cth", "ckh", "cph", "cfh", "ch", "sh", "iin", "in")
MATCHING_GROUPED_UNITS = tuple(
    sorted(DECLARED_GROUPED_UNITS, key=lambda unit: -len(unit))
)

_SPLIT_BUCKETS = {
    "test": (0, 1),
    "validation": (2,),
    "train": tuple(range(3, 10)),
}


def _group_from_folio(folio: Any) -> str:
    """Return the shared source-backed bifolio group for one folio identifier."""

    return group_id(folio)


# Compatibility aliases for local callers from the numeric-split prototype.
_leaf_from_folio = _group_from_folio


def _group_sort_key(group: str) -> tuple[int, int | str]:
    if group.isdigit():
        return (0, int(group))
    return (1, group)


_leaf_sort_key = _group_sort_key


def _split_bucket(group: str) -> int:
    return split_bucket(group)


def _split_name(bucket: int) -> str:
    return split_name(bucket)


def _token_text(token: Any) -> str:
    if token is None:
        return ""
    return token if isinstance(token, str) else str(token)


def _tokens_for_record(record: dict[str, Any]) -> list[str]:
    tokens = record.get("tokens", [])
    if tokens is None:
        return []
    return [_token_text(token) for token in tokens]


def _raw_eva_units(token: str) -> list[str]:
    return list(token)


def _grouped_units(token: str) -> list[str]:
    units: list[str] = []
    position = 0
    while position < len(token):
        for declared_unit in MATCHING_GROUPED_UNITS:
            if token.startswith(declared_unit, position):
                units.append(declared_unit)
                position += len(declared_unit)
                break
        else:
            units.append(token[position])
            position += 1
    return units


def _unitize(token: str, unitization: str) -> list[str]:
    if unitization == "raw_eva":
        return _raw_eva_units(token)
    if unitization == "grouped":
        return _grouped_units(token)
    raise ValueError(f"unknown unitization: {unitization}")


def _context_key(context: tuple[str, ...]) -> str:
    return json.dumps(list(context), ensure_ascii=False, separators=(",", ":"))


def _context_for(sequence: list[str], position: int, order: int) -> tuple[str, ...]:
    if order == 0:
        return ()
    prefix_length = max(0, order - position)
    history = tuple(sequence[max(0, position - order) : position])
    return (START_SYMBOL,) * prefix_length + history


def _safe_alphabet(training_sequences: Iterable[list[str]]) -> list[str]:
    reserved = {START_SYMBOL, END_SYMBOL, UNKNOWN_SYMBOL}
    alphabet = {
        symbol
        for sequence in training_sequences
        for symbol in sequence
        if symbol not in reserved
    }
    return sorted(alphabet)


def _build_model(training_sequences: list[list[str]], order: int) -> dict[str, Any]:
    """Fit one fixed-order add-alpha model from training unit sequences."""

    alphabet = _safe_alphabet(training_sequences)
    vocabulary = [*alphabet, UNKNOWN_SYMBOL, END_SYMBOL]
    vocabulary_set = set(vocabulary)
    context_counts: defaultdict[tuple[str, ...], Counter[str]] = defaultdict(Counter)
    start_context = (START_SYMBOL,) * order
    context_counts[start_context]
    symbol_counts: Counter[str] = Counter({symbol: 0 for symbol in vocabulary})
    training_unit_count = 0

    for sequence in training_sequences:
        mapped = [
            symbol if symbol in vocabulary_set and symbol != END_SYMBOL else UNKNOWN_SYMBOL
            for symbol in sequence
        ]
        training_unit_count += len(mapped)
        predicted = [*mapped, END_SYMBOL]
        for position, symbol in enumerate(predicted):
            context = _context_for(mapped, position, order)
            context_counts[context][symbol] += 1
            symbol_counts[symbol] += 1

    counts: dict[str, dict[str, int]] = {}
    context_totals: dict[str, int] = {}
    probabilities: dict[str, dict[str, float]] = {}
    probability_sums: dict[str, float] = {}
    context_rows: list[dict[str, Any]] = []

    ordered_contexts = sorted(context_counts, key=_context_key)
    for context in ordered_contexts:
        key = _context_key(context)
        row_counts = {symbol: int(context_counts[context].get(symbol, 0)) for symbol in vocabulary}
        total = sum(row_counts.values())
        denominator = total + ADD_ALPHA * len(vocabulary)
        row_probabilities = {
            symbol: (count + ADD_ALPHA) / denominator
            for symbol, count in row_counts.items()
        }
        counts[key] = row_counts
        context_totals[key] = total
        probabilities[key] = row_probabilities
        probability_sums[key] = sum(row_probabilities.values())
        context_rows.append(
            {
                "key": key,
                "context": list(context),
                "counts": row_counts,
                "probabilities": row_probabilities,
            }
        )

    return {
        "order": order,
        "add_alpha": ADD_ALPHA,
        "start_symbol": START_SYMBOL,
        "start_context": list(start_context),
        "start_context_key": _context_key(start_context),
        "end_symbol": END_SYMBOL,
        "unknown_symbol": UNKNOWN_SYMBOL,
        "alphabet": alphabet,
        "vocabulary": vocabulary,
        "training_token_count": len(training_sequences),
        "training_unit_count": training_unit_count,
        "symbol_counts": {symbol: int(symbol_counts[symbol]) for symbol in vocabulary},
        "counts": counts,
        "context_totals": context_totals,
        "probabilities": probabilities,
        "probability_sums": probability_sums,
        "contexts": context_rows,
    }


def _score_sequences(test_sequences: list[list[str]], model: dict[str, Any]) -> dict[str, Any]:
    vocabulary = list(model["vocabulary"])
    vocabulary_set = set(vocabulary)
    alphabet = set(model["alphabet"])
    order = int(model["order"])
    counts = model["counts"]
    context_totals = model["context_totals"]
    nll_bits = 0.0
    predicted_symbols = 0
    unknown_symbols = 0
    symbol_counts: Counter[str] = Counter({symbol: 0 for symbol in vocabulary})

    for sequence in test_sequences:
        mapped: list[str] = []
        for symbol in sequence:
            if symbol in alphabet and symbol in vocabulary_set:
                mapped.append(symbol)
            else:
                mapped.append(UNKNOWN_SYMBOL)
                unknown_symbols += 1

        predicted = [*mapped, END_SYMBOL]
        for position, symbol in enumerate(predicted):
            context = _context_for(mapped, position, order)
            key = _context_key(context)
            row = counts.get(key, {})
            total = context_totals.get(key, 0)
            probability = (row.get(symbol, 0) + ADD_ALPHA) / (
                total + ADD_ALPHA * len(vocabulary)
            )
            nll_bits -= math.log2(probability)
            predicted_symbols += 1
            symbol_counts[symbol] += 1

    if predicted_symbols:
        bits_per_symbol = nll_bits / predicted_symbols
        try:
            perplexity = 2.0**bits_per_symbol
        except OverflowError:
            perplexity = math.inf
    else:
        bits_per_symbol = None
        perplexity = None

    return {
        "nll_bits": nll_bits,
        "predicted_symbols": predicted_symbols,
        "bits_per_symbol": bits_per_symbol,
        "perplexity": perplexity,
        "test_token_count": len(test_sequences),
        "unknown_symbols": unknown_symbols,
        "unknown_symbol_count": unknown_symbols,
        "eos_count": len(test_sequences),
        "end_symbol_count": len(test_sequences),
        "symbol_counts": {symbol: int(symbol_counts[symbol]) for symbol in vocabulary},
    }


def _records_by_split(
    records: list[dict[str, Any]],
) -> tuple[dict[str, list[tuple[int, dict[str, Any]]]], dict[str, Any]]:
    split_records: dict[str, list[tuple[int, dict[str, Any]]]] = {
        "train": [],
        "validation": [],
        "test": [],
    }
    group_rows: defaultdict[str, dict[str, Any]] = defaultdict(
        lambda: {"bucket": None, "folios": set(), "record_indices": [], "split": None}
    )

    for record_index, record in enumerate(records):
        folio = "" if record.get("folio") is None else str(record.get("folio"))
        group = _group_from_folio(folio)
        bucket = _split_bucket(group)
        split = _split_name(bucket)
        split_records[split].append((record_index, record))
        row = group_rows[group]
        row["bucket"] = bucket
        row["split"] = split
        row["folios"].add(folio)
        row["record_indices"].append(record_index)

    manifests: dict[str, dict[str, Any]] = {}
    ordered_group_rows = sorted(group_rows.items(), key=lambda item: _group_sort_key(item[0]))
    for split in ("train", "validation", "test"):
        groups = [group for group, row in ordered_group_rows if row["split"] == split]
        folios = sorted(
            {folio for group in groups for folio in group_rows[group]["folios"]}
        )
        record_indices = [index for index, _record in split_records[split]]
        token_count = sum(
            len(_tokens_for_record(record)) for _index, record in split_records[split]
        )
        buckets = sorted({group_rows[group]["bucket"] for group in groups})
        group_manifest = [
            {
                "group": group,
                "leaf": group,
                "bucket": group_rows[group]["bucket"],
                "folios": sorted(group_rows[group]["folios"]),
                "record_indices": list(group_rows[group]["record_indices"]),
            }
            for group in groups
        ]
        manifests[split] = {
            "split": split,
            "buckets": buckets,
            "bucket": buckets[0] if len(buckets) == 1 else None,
            "groups": groups,
            "leaves": groups,
            "folios": folios,
            "record_indices": record_indices,
            "record_count": len(record_indices),
            "token_count": token_count,
            "group_manifest": group_manifest,
            "leaf_manifest": group_manifest,
        }

    manifests["grouping_config"] = dict(GROUPING_CONFIG)
    return split_records, manifests


def _unit_sequences(
    split_records: list[tuple[int, dict[str, Any]]],
    unitization: str,
) -> list[list[str]]:
    sequences: list[list[str]] = []
    for _record_index, record in split_records:
        sequences.extend(
            _unitize(token, unitization) for token in _tokens_for_record(record)
        )
    return sequences


def _shuffled_unit_sequences(
    split_records: list[tuple[int, dict[str, Any]]],
    unitization: str,
    seed: int,
) -> list[list[str]]:
    rng = random.Random(seed)
    sequences: list[list[str]] = []
    for _record_index, record in split_records:
        for token in _tokens_for_record(record):
            sequence = _unitize(token, unitization)
            shuffled = list(sequence)
            rng.shuffle(shuffled)
            sequences.append(shuffled)
    return sequences


def _config(seed: int) -> dict[str, Any]:
    return {
        "seed": seed,
        "split_hash_salt": SPLIT_HASH_SALT,
        "split_hash_algorithm": "sha256",
        "split_bucket_modulus": 10,
        "split_buckets": {
            name: list(buckets) for name, buckets in _SPLIT_BUCKETS.items()
        },
        "split_group": "source Q/B bifolio group; complete provider metadata; no independent conservation examination",
        "grouping_config": dict(GROUPING_CONFIG),
        "fit_split": "train",
        "validation_split": "validation",
        "evaluation_split": "test",
        "character_input": {
            "source": "accepted parser tokens from all records, including records with excluded_tokens",
            "line_filter": "none beyond the selected split",
            "context_difference": "word-context analysis excludes an entire paragraph line when excluded_tokens is nonzero",
        },
        "model": {
            "orders": list(NGRAM_ORDERS),
            "add_alpha": ADD_ALPHA,
            "start_symbol": START_SYMBOL,
            "end_symbol": END_SYMBOL,
            "unknown_symbol": UNKNOWN_SYMBOL,
            "alphabet_source": "training units only, plus UNK and EOS",
            "hyperparameter_tuning": "none",
            "test_reuse": "none",
        },
        "shuffled_null": {
            "seed": seed,
            "within_word": True,
            "preserves_token_lengths": True,
            "preserves_character_multisets": True,
            "per_unitization": {
                "raw_eva": {
                    "shuffled_units": "single raw characters",
                    "within_token": True,
                    "preserves_token_lengths": True,
                    "preserves_unit_count": True,
                    "preserves_flattened_unit_count": True,
                    "preserves_flattened_character_length": True,
                    "preserves_raw_character_multiset": True,
                    "matches_raw_character_permutation_distribution": True,
                },
                "grouped": {
                    "shuffled_units": "declared grouped units",
                    "within_token": True,
                    "preserves_token_lengths": True,
                    "preserves_grouped_unit_count": True,
                    "preserves_flattened_unit_count": True,
                    "preserves_flattened_character_length": True,
                    "preserves_grouped_unit_multiset": True,
                    "preserves_raw_character_multiset": True,
                    "matches_raw_character_permutation_distribution": False,
                },
            },
            "fit_split": "train",
            "evaluation_split": "test",
        },
        "unitizations": {
            "raw_eva": {
                "description": "one Unicode code point per predicted unit",
                "units": "remaining characters are single code points",
            },
            "grouped": {
                "description": "declared multi-character units with remaining characters",
                "declared_units": list(DECLARED_GROUPED_UNITS),
                "matching_order": list(MATCHING_GROUPED_UNITS),
                "shuffled_null_units": "declared grouped units; flattened character lengths remain fixed",
                "truth_claim": "illustrative segmentation; not an asserted glyph truth",
            },
        },
        "natural_language_baseline": None,
        "downloads": False,
    }


def run_predictive(records: list[dict], seed: int = 408) -> dict:
    """Run fixed, train-only character prediction experiments.

    The result describes written sequence structure. It does not infer
    language identity or token meaning.
    """

    if not isinstance(records, list):
        records = list(records)
    seed = int(seed)
    split_records, split_manifest = _records_by_split(records)

    counts = {
        "records": {
            split: split_manifest[split]["record_count"]
            for split in ("train", "validation", "test")
        },
        "leaves": {
            split: len(split_manifest[split]["leaves"])
            for split in ("train", "validation", "test")
        },
        "groups": {
            split: len(split_manifest[split]["groups"])
            for split in ("train", "validation", "test")
        },
        "folios": {
            split: len(split_manifest[split]["folios"])
            for split in ("train", "validation", "test")
        },
        "tokens": {
            split: split_manifest[split]["token_count"]
            for split in ("train", "validation", "test")
        },
    }

    training_records = split_records["train"]
    test_records = split_records["test"]
    observed_models: dict[str, dict[str, dict[str, Any]]] = {}
    null_models: dict[str, dict[str, dict[str, Any]]] = {}
    observed_scores: dict[str, dict[str, dict[str, Any]]] = {}
    null_scores: dict[str, dict[str, dict[str, Any]]] = {}

    for unitization in ("raw_eva", "grouped"):
        training_sequences = _unit_sequences(training_records, unitization)
        test_sequences = _unit_sequences(test_records, unitization)
        shuffled_sequences = _shuffled_unit_sequences(training_records, unitization, seed)
        observed_models[unitization] = {}
        null_models[unitization] = {}
        observed_scores[unitization] = {}
        null_scores[unitization] = {}
        for order in NGRAM_ORDERS:
            order_name = f"order_{order}"
            observed_model = _build_model(training_sequences, order)
            null_model = _build_model(shuffled_sequences, order)
            observed_models[unitization][order_name] = observed_model
            null_models[unitization][order_name] = null_model
            observed_scores[unitization][order_name] = _score_sequences(
                test_sequences, observed_model
            )
            null_scores[unitization][order_name] = _score_sequences(
                test_sequences, null_model
            )

    return {
        "config": _config(seed),
        "split_manifest": split_manifest,
        "counts": counts,
        "models": {
            "observed": observed_models,
            "shuffled_null": null_models,
        },
        "scores": {
            "observed": observed_scores,
            "shuffled_null": null_scores,
        },
        "interpretation": {
            "purpose": "character prediction scores describe written sequence structure",
            "does_not_measure": ["language identity", "meaning"],
            "comparison_rule": "compare bit rates within one unitization; raw and grouped units differ",
        },
    }


__all__ = ["run_predictive"]
