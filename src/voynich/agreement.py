"""Compare two normalized IVTFF transcription record streams.

The comparison aligns a folio with the numeric index in its locus. It does
not choose which transcription is correct or establish that the sources are
independent.
"""

from __future__ import annotations

from collections import Counter
import re
from typing import Any, Mapping, Sequence


Record = Mapping[str, Any]
AlignmentKey = tuple[str, int]

MAX_MISMATCH_EXAMPLES = 20

_LOCUS_INDEX_RE = re.compile(r"^(?:[^.]+\.)?(\d+)(?:,|$)")
_BASIC_TOKEN_RE = re.compile(r"^[a-z]+$")
_UNCERTAIN_RAW_RE = re.compile(r"\[[^\]]*:[^\]]*\]|\?|@[0-9]{3};|'")
_RARE_COMMENT_RE = re.compile(r"<!\s*[^>]*\brare\b", re.IGNORECASE)
_INTERRUPTED_RE = re.compile(r"<->|<~>|\binterrupted\b", re.IGNORECASE)


def _alignment_key(record: Record, side: str, position: int) -> AlignmentKey:
    folio = record.get("folio")
    locus = record.get("locus")
    if not isinstance(folio, str) or not folio:
        raise ValueError(f"{side} record {position} has no valid folio")
    if not isinstance(locus, str):
        raise ValueError(f"{side} record {position} has no valid locus")
    match = _LOCUS_INDEX_RE.match(locus)
    if match is None:
        raise ValueError(
            f"{side} record {position} has no numeric locus index: {locus!r}"
        )
    return folio, int(match.group(1))


def _index_records(records: Sequence[Record], side: str) -> dict[AlignmentKey, Record]:
    indexed: dict[AlignmentKey, Record] = {}
    duplicates: list[AlignmentKey] = []
    for position, record in enumerate(records):
        key = _alignment_key(record, side, position)
        if key in indexed:
            duplicates.append(key)
        else:
            indexed[key] = record
    if duplicates:
        labels = ", ".join(_key_label(key) for key in sorted(set(duplicates)))
        raise ValueError(f"duplicate alignment key in {side}: {labels}")
    return indexed


def _key_label(key: AlignmentKey) -> str:
    return f"{key[0]}.{key[1]}"


def _key_sort(key: AlignmentKey) -> tuple[Any, ...]:
    match = re.fullmatch(r"[A-Za-z]+(\d+)([A-Za-z].*)?", key[0])
    if match:
        return 0, int(match.group(1)), match.group(2) or "", key[1]
    return 1, 0, "", key[0], key[1]


def _raw(record: Record) -> str:
    value = record.get("text_raw", "")
    return value if isinstance(value, str) else str(value)


def _tokens(record: Record) -> list[str]:
    value = record.get("tokens", ())
    if value is None:
        return []
    if isinstance(value, str):
        raise ValueError("record tokens must be a sequence of tokens, not a string")
    try:
        return list(value)
    except TypeError as exc:
        raise ValueError("record tokens must be iterable") from exc


def _excluded_token_count(record: Record) -> int:
    value = record.get("excluded_tokens", 0)
    if value is None:
        return 0
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("record excluded_tokens must be an integer") from exc


def _eligibility_reasons(record: Record) -> list[str]:
    raw = _raw(record)
    tokens = _tokens(record)
    reasons: list[str] = []
    has_nonbasic_token = any(
        not isinstance(token, str) or _BASIC_TOKEN_RE.fullmatch(token) is None
        for token in tokens
    )
    if (
        _excluded_token_count(record) > 0
        or _UNCERTAIN_RAW_RE.search(raw) is not None
        or _RARE_COMMENT_RE.search(raw) is not None
        or has_nonbasic_token
    ):
        reasons.append("uncertain_or_rare_tokens")
    if _INTERRUPTED_RE.search(raw) is not None:
        reasons.append("interrupted")
    if not tokens:
        reasons.append("empty_tokens")
    return reasons


def _surface(record: Record) -> dict[str, Any]:
    return {
        "locus": record.get("locus"),
        "kind": record.get("kind"),
        "raw": _raw(record),
        "tokens": _tokens(record),
    }


def _unmatched_entry(key: AlignmentKey, record: Record) -> dict[str, Any]:
    return {
        "folio": key[0],
        "locus_index": key[1],
        "locus": record.get("locus"),
        "kind": record.get("kind"),
    }


def _levenshtein(left: Sequence[Any], right: Sequence[Any]) -> int:
    """Return Levenshtein edit distance between two token sequences."""

    if len(left) < len(right):
        left, right = right, left
    previous = list(range(len(right) + 1))
    for left_item in left:
        current = [previous[0] + 1]
        for right_index, right_item in enumerate(right, start=1):
            current.append(
                min(
                    current[-1] + 1,
                    previous[right_index] + 1,
                    previous[right_index - 1] + (left_item != right_item),
                )
            )
        previous = current
    return previous[-1]


def _ratio(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def _mismatch_example(
    key: AlignmentKey,
    left: Record,
    right: Record,
    left_reasons: list[str],
    right_reasons: list[str],
    token_edit_distance: int,
) -> dict[str, Any]:
    left_tokens = _tokens(left)
    right_tokens = _tokens(right)
    return {
        "folio": key[0],
        "locus_index": key[1],
        "locus": _key_label(key),
        "left_locus": left.get("locus"),
        "right_locus": right.get("locus"),
        "left_kind": left.get("kind"),
        "right_kind": right.get("kind"),
        "left_raw": _raw(left),
        "right_raw": _raw(right),
        "left_tokens": left_tokens,
        "right_tokens": right_tokens,
        "left_exclusion_reasons": left_reasons,
        "right_exclusion_reasons": right_reasons,
        "eligible": not left_reasons and not right_reasons,
        "token_edit_distance": token_edit_distance,
    }


def _focus_rows(
    keys: Sequence[AlignmentKey],
    left_index: Mapping[AlignmentKey, Record],
    right_index: Mapping[AlignmentKey, Record],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for key in keys:
        if key[0] != "f84r":
            continue
        left = left_index.get(key)
        right = right_index.get(key)
        rows.append(
            {
                "folio": key[0],
                "locus_index": key[1],
                "left": _surface(left) if left is not None else None,
                "right": _surface(right) if right is not None else None,
            }
        )
    return rows


def compare_transcriptions(
    left_records: Sequence[Record], right_records: Sequence[Record]
) -> dict[str, Any]:
    """Compare two IVTFF record streams using normalized folio and line keys.

    The numeric part of each locus selects the alignment key. Locator and kind
    differences remain visible in the result and do not change that key.
    Duplicate keys raise ``ValueError`` before any record is overwritten.
    """

    left_records = list(left_records)
    right_records = list(right_records)
    left_index = _index_records(left_records, "left")
    right_index = _index_records(right_records, "right")
    left_keys = set(left_index)
    right_keys = set(right_index)
    aligned_keys = sorted(left_keys & right_keys, key=_key_sort)
    all_keys = sorted(left_keys | right_keys, key=_key_sort)

    unmatched_left = sorted(left_keys - right_keys, key=_key_sort)
    unmatched_right = sorted(right_keys - left_keys, key=_key_sort)
    raw_identical = 0
    token_identical = 0
    eligible_count = 0
    token_distance_sum = 0
    token_distance_max = 0
    mismatch_total = 0
    mismatch_eligible = 0
    mismatch_examples: list[dict[str, Any]] = []
    excluded_pairs = Counter()
    excluded_by_side = Counter()
    kind_pairs = Counter()

    for key in aligned_keys:
        left = left_index[key]
        right = right_index[key]
        left_reasons = _eligibility_reasons(left)
        right_reasons = _eligibility_reasons(right)
        pair_reasons = sorted(set(left_reasons + right_reasons))
        for reason in pair_reasons:
            excluded_pairs[reason] += 1
        for reason in left_reasons:
            excluded_by_side[f"left:{reason}"] += 1
        for reason in right_reasons:
            excluded_by_side[f"right:{reason}"] += 1

        left_kind = left.get("kind")
        right_kind = right.get("kind")
        if left_kind != right_kind:
            kind_pairs[f"{left_kind}->{right_kind}"] += 1

        left_raw = _raw(left)
        right_raw = _raw(right)
        left_tokens = _tokens(left)
        right_tokens = _tokens(right)
        token_edit_distance = _levenshtein(left_tokens, right_tokens)
        if not pair_reasons:
            eligible_count += 1
            raw_identical += left_raw == right_raw
            token_identical += left_tokens == right_tokens
            token_distance_sum += token_edit_distance
            token_distance_max = max(token_distance_max, token_edit_distance)

        is_mismatch = (
            left_raw != right_raw
            or left_tokens != right_tokens
            or left_kind != right_kind
        )
        if is_mismatch:
            mismatch_total += 1
            if not pair_reasons:
                mismatch_eligible += 1
            if len(mismatch_examples) < MAX_MISMATCH_EXAMPLES:
                mismatch_examples.append(
                    _mismatch_example(
                        key,
                        left,
                        right,
                        left_reasons,
                        right_reasons,
                        token_edit_distance,
                    )
                )

    return {
        "status": "compared",
        "alignment": {
            "key": "folio plus numeric locus index",
            "assumption": "Inputs use the normalized common IVTFF locus convention.",
            "locator_and_kind": "Locator and kind differences are reported but do not change the key.",
            "duplicate_policy": "Raise ValueError before comparison.",
            "max_mismatch_examples": MAX_MISMATCH_EXAMPLES,
        },
        "counts": {
            "total": {
                "left": len(left_records),
                "right": len(right_records),
                "combined": len(left_records) + len(right_records),
            },
            "left_total": len(left_records),
            "right_total": len(right_records),
            "aligned": len(aligned_keys),
            "eligible": eligible_count,
            "unmatched": {
                "left": len(unmatched_left),
                "right": len(unmatched_right),
            },
            "ineligible": len(aligned_keys) - eligible_count,
            "kind_mismatches": sum(kind_pairs.values()),
        },
        "unmatched": {
            "left": [_unmatched_entry(key, left_index[key]) for key in unmatched_left],
            "right": [_unmatched_entry(key, right_index[key]) for key in unmatched_right],
        },
        "eligibility": {
            "eligible": eligible_count,
            "excluded": dict(sorted(excluded_pairs.items())),
            "excluded_by_side": dict(sorted(excluded_by_side.items())),
            "rules": [
                "Exclude aligned pairs with excluded_tokens, uncertain or rare markers, or non-basic tokens.",
                "Exclude aligned pairs whose raw text contains <->, <~>, or an interruption annotation.",
                "Exclude aligned pairs with no accepted tokens.",
            ],
        },
        "agreement": {
            "raw": {
                "identical": raw_identical,
                "coverage": _ratio(raw_identical, eligible_count),
            },
            "tokens": {
                "identical": token_identical,
                "coverage": _ratio(token_identical, eligible_count),
            },
            "token_edit_distance": {
                "method": "Levenshtein distance on token sequences",
                "sum": token_distance_sum,
                "mean": _ratio(token_distance_sum, eligible_count),
                "max": token_distance_max if eligible_count else None,
                "eligible_pairs": eligible_count,
            },
        },
        "kind_mismatches": {
            "count": sum(kind_pairs.values()),
            "pairs": dict(sorted(kind_pairs.items())),
        },
        "mismatch_counts": {
            "total": mismatch_total,
            "eligible": mismatch_eligible,
            "ineligible": mismatch_total - mismatch_eligible,
        },
        "mismatch_examples": mismatch_examples,
        "focus": {
            "folio": "f84r",
            "rows": _focus_rows(all_keys, left_index, right_index),
        },
        "interpretation_limits": [
            "Agreement does not identify an accurate transcription.",
            "Agreement does not establish source independence.",
            "Unmatched keys can reflect divergent numbering, coverage, or preservation.",
        ],
    }
