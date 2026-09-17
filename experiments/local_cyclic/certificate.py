"""Pure strict-word extraction and local cyclic-repeat certificates.

This module reads no files and does not assign language symbols.  It uses the
frozen Basic EVA tokenizer for both declared unitizations.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Iterable, Literal

from experiments.homophonic.units import UnitSpan, tokenize_word


Representation = Literal["raw", "visual"]
Status = Literal[
    "falsified_for_fixed_track",
    "not_falsified_by_local_check",
    "inconclusive_no_eligible_words",
]


@dataclass(frozen=True, slots=True)
class WordSpan:
    """One source word candidate with its original source offsets."""

    word_index: int
    source_start: int
    source_end: int
    surface: str
    exclusion_reason: str | None

    @property
    def eligible(self) -> bool:
        return self.exclusion_reason is None


@dataclass(frozen=True, slots=True)
class WordExtraction:
    """All word candidates and deterministic exclusion counts."""

    spans: tuple[WordSpan, ...]
    excluded_counts: tuple[tuple[str, int], ...]

    @property
    def eligible(self) -> tuple[WordSpan, ...]:
        return tuple(item for item in self.spans if item.eligible)


@dataclass(frozen=True, slots=True)
class CertificateLocation:
    """One adjacent-repeat location within one eligible word."""

    word_index: int
    unit_index: int
    unit: str
    unit_span: tuple[int, int] | None


@dataclass(frozen=True, slots=True)
class CertificateResult:
    """Aggregate local-repeat counts for one fixed unitization."""

    representation: Representation
    eligible_word_count: int
    eligible_unit_count: int
    adjacent_pair_count: int
    certificate_count: int
    affected_word_count: int
    locations: tuple[CertificateLocation, ...]
    status: Status


def _append_reason(current: str | None, reason: str) -> str:
    return current or reason


def extract_word_spans(text_raw: str) -> WordExtraction:
    """Extract strict word candidates without changing source spelling.

    Layout whitespace at a word edge is trimmed. Interior whitespace rejects
    the candidate. Periods split words. Commas split and invalidate both
    adjacent candidates. Other constructs stay in the candidate or invalidate
    the touching candidate, including diagram markers.
    """

    if not isinstance(text_raw, str):
        raise TypeError("text_raw must be a string")

    spans: list[WordSpan] = []
    chars: list[str] = []
    start: int | None = None
    end = 0
    reason: str | None = None
    pending_reason: str | None = None

    def begin(index: int, initial_reason: str | None = None) -> None:
        nonlocal start, end, reason, pending_reason
        start = index
        end = index
        chars.clear()
        reason = pending_reason or initial_reason
        pending_reason = None

    def append(source: str, source_start: int, source_end: int) -> None:
        nonlocal end
        chars.extend(source)
        end = source_end

    def mark(reason_value: str) -> None:
        nonlocal reason
        reason = _append_reason(reason, reason_value)

    def finish(reason_value: str | None = None) -> None:
        nonlocal start, end, reason, pending_reason
        if start is None:
            return
        mark(reason_value) if reason_value else None
        raw = "".join(chars)
        trailing = len(raw) - len(raw.rstrip())
        if trailing:
            raw = raw[:-trailing]
            end -= trailing
        if not raw:
            mark("empty")
        elif any(char.isspace() for char in raw):
            mark("interior_whitespace")
        if reason is None:
            if not raw.isascii():
                reason = "non_ascii"
            elif not raw.islower() or not raw.isalpha():
                reason = "other_construct"
        spans.append(
            WordSpan(
                word_index=len(spans),
                source_start=start,
                source_end=end,
                surface=raw,
                exclusion_reason=reason,
            )
        )
        start = None
        end = 0
        chars.clear()
        reason = None

    def set_pending(reason_value: str) -> None:
        nonlocal pending_reason
        pending_reason = _append_reason(pending_reason, reason_value)

    def consume_construct(index: int, closing: str, reason_value: str) -> int:
        close = text_raw.find(closing, index + 1)
        if close < 0:
            if start is None:
                begin(index, "incomplete_span")
            else:
                mark("incomplete_span")
            append(text_raw[index:], index, len(text_raw))
            return len(text_raw)
        if start is None:
            begin(index, reason_value)
        else:
            mark(reason_value)
        append(text_raw[index : close + 1], index, close + 1)
        return close + 1

    index = 0
    while index < len(text_raw):
        char = text_raw[index]
        if char.isspace():
            if start is not None:
                append(char, index, index + 1)
            index += 1
            continue
        if char == ".":
            finish()
            pending_reason = None
            index += 1
            continue
        if char == ",":
            finish("uncertain_space")
            set_pending("uncertain_space")
            index += 1
            continue
        if char == "<":
            close = text_raw.find(">", index + 1)
            if close < 0:
                index = consume_construct(index, ">", "incomplete_span")
                continue
            body = text_raw[index + 1 : close]
            if body in {"-", "~"}:
                if start is None:
                    set_pending("diagram_marker")
                else:
                    mark("diagram_marker")
                    append(text_raw[index : close + 1], index, close + 1)
            elif start is None:
                set_pending("inline_control")
            else:
                mark("inline_control")
                append(text_raw[index : close + 1], index, close + 1)
            index = close + 1
            continue
        if char == "[":
            index = consume_construct(index, "]", "uncertain_reading")
            continue
        if char == "{":
            index = consume_construct(index, "}", "ligature")
            continue
        if char == "@":
            close = text_raw.find(";", index + 1)
            if close >= 0:
                index = consume_construct(index, ";", "high_ascii")
            else:
                if start is None:
                    begin(index, "other_construct")
                else:
                    mark("other_construct")
                append(char, index, index + 1)
                index += 1
            continue
        if char == "?":
            if start is None:
                begin(index, "uncertain_reading")
            else:
                mark("uncertain_reading")
            append(char, index, index + 1)
            index += 1
            continue
        if char == "'":
            if start is None:
                begin(index, "apostrophe")
            else:
                mark("apostrophe")
            append(char, index, index + 1)
            index += 1
            continue
        if char.isascii() and char.isalpha() and char.islower():
            if start is None:
                begin(index)
            append(char, index, index + 1)
            pending_reason = None
            index += 1
            continue
        if not char.isascii():
            reason_value = "non_ascii"
        elif char.isalpha():
            reason_value = "uppercase"
        else:
            reason_value = "other_construct"
        if start is None:
            begin(index, reason_value)
        else:
            mark(reason_value)
        append(char, index, index + 1)
        index += 1

    finish()
    counts = Counter(item.exclusion_reason for item in spans if item.exclusion_reason)
    return WordExtraction(tuple(spans), tuple(sorted(counts.items())))


def unitize_word(
    word: WordSpan, *, representation: Representation = "raw"
) -> tuple[UnitSpan, ...]:
    """Apply one frozen unitization to one eligible strict word."""

    if not isinstance(word, WordSpan):
        raise TypeError("word must be a WordSpan")
    if not word.eligible:
        raise ValueError("cannot unitize an excluded word")
    if representation not in {"raw", "visual"}:
        raise ValueError("representation must be 'raw' or 'visual'")
    return tokenize_word(word.surface, representation=representation)


def count_local_certificates(
    words: Iterable[WordSpan],
    *,
    representation: Representation = "raw",
) -> CertificateResult:
    """Count adjacent equal units independently inside eligible words."""

    if representation not in {"raw", "visual"}:
        raise ValueError("representation must be 'raw' or 'visual'")
    candidates = tuple(words)
    if any(not isinstance(word, WordSpan) for word in candidates):
        raise TypeError("words must contain WordSpan values")
    eligible = tuple(word for word in candidates if word.eligible)
    locations: list[CertificateLocation] = []
    eligible_units = 0
    adjacent_pairs = 0
    affected: set[int] = set()
    for word in eligible:
        units = unitize_word(word, representation=representation)
        eligible_units += len(units)
        adjacent_pairs += max(0, len(units) - 1)
        for index, (left, right) in enumerate(zip(units, units[1:])):
            if left.unit != right.unit:
                continue
            affected.add(word.word_index)
            unit_span = (left.start, left.end) if representation == "visual" else None
            locations.append(CertificateLocation(word.word_index, index, left.unit, unit_span))
    count = len(locations)
    if not eligible:
        status: Status = "inconclusive_no_eligible_words"
    elif count:
        status = "falsified_for_fixed_track"
    else:
        status = "not_falsified_by_local_check"
    return CertificateResult(
        representation,
        len(eligible),
        eligible_units,
        adjacent_pairs,
        count,
        len(affected),
        tuple(locations),
        status,
    )


__all__ = [
    "CertificateLocation",
    "CertificateResult",
    "WordExtraction",
    "WordSpan",
    "count_local_certificates",
    "extract_word_spans",
    "unitize_word",
]
