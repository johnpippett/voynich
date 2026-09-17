"""Adapt accepted projected paragraphs into fixed Celsus reference splits.

The module accepts projected records only. It does not read XML, fetch data,
encrypt words, or fit a model.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
import hashlib
import json
import re
import unicodedata
from typing import Any, Iterable, Mapping

from voynich.reference import normalize_word

SPLITS = ("train", "validation", "test")
_FIELDS = frozenset({"book_id", "chapter_id", "chapter_key",
                     "local_paragraph_ordinal", "text"})
_ROMAN_RE = re.compile(r"^[ivxlcdm]+$")
class ReferenceAdapterError(ValueError):
    """Projected records do not meet the adapter contract."""

@dataclass(frozen=True)
class NormalizedParagraph:
    """One projected paragraph after token extraction and assignment."""

    book_id: str
    chapter_id: str
    chapter_key: str
    local_paragraph_ordinal: int
    split: str
    tokens: tuple[str, ...]
    retained: bool
    exclusion: str | None
    rejected_run_count: int
    roman_like_count: int

    @property
    def location(self) -> dict[str, Any]:
        return {"book_id": self.book_id, "chapter_id": self.chapter_id,
                "chapter_key": self.chapter_key,
                "local_paragraph_ordinal": self.local_paragraph_ordinal}

@dataclass(frozen=True)
class AdaptedReference:
    """Token streams, paragraph metadata, and a public-safe manifest."""

    paragraphs: tuple[NormalizedParagraph, ...]
    partitions: dict[str, tuple[str, ...]]
    manifest: dict[str, Any]

def _json_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


def _hash(value: Any) -> str:
    return hashlib.sha256(_json_bytes(value)).hexdigest()

def _is_mark(char: str) -> bool:
    return unicodedata.category(char).startswith("M")


def _runs(text: str) -> tuple[str, ...]:
    """Return maximal alphabetic runs and adjacent combining marks."""

    result: list[str] = []
    index = 0
    while index < len(text):
        if not text[index].isalpha():
            index += 1
            continue
        start = index
        index += 1
        while index < len(text) and (text[index].isalpha() or _is_mark(text[index])):
            index += 1
        result.append(text[start:index])
    return tuple(result)

def normalize_projected_text(text: str) -> tuple[tuple[str, ...], int, int]:
    """Return normalized words, rejected-run count, and Roman-like count."""

    if not isinstance(text, str):
        raise TypeError("projected paragraph text must be a string")
    tokens: list[str] = []
    rejected = 0
    roman_like = 0
    for candidate in _runs(text):
        word = normalize_word(candidate)
        if word is None:
            rejected += 1
            continue
        tokens.append(word)
        roman_like += bool(_ROMAN_RE.fullmatch(word))
    return tuple(tokens), rejected, roman_like

def _validate_records(records: Iterable[Mapping[str, Any]]) -> tuple[
    tuple[Mapping[str, Any], ...], tuple[str, ...], dict[str, str]
]:
    if isinstance(records, (str, bytes, Mapping)):
        raise TypeError("records must be an iterable of projected paragraph mappings")
    source = tuple(records)
    if not source:
        raise ReferenceAdapterError("projected records must not be empty")
    chapters: list[str] = []
    chapter_books: dict[str, str] = {}
    seen_chapters: set[str] = set()
    seen_paragraphs: set[tuple[str, str, int]] = set()
    seen_books: set[str] = set()
    current_book = current_chapter = None
    expected_local = 1
    for index, record in enumerate(source):
        if not isinstance(record, Mapping):
            raise TypeError(f"record {index} must be a mapping")
        if set(record) != _FIELDS:
            raise ReferenceAdapterError(
                f"record {index} fields differ; expected {sorted(_FIELDS)}"
            )
        book, chapter, key = (record[name] for name in
                              ("book_id", "chapter_id", "chapter_key"))
        ordinal, text = record["local_paragraph_ordinal"], record["text"]
        if any(not isinstance(value, str) or not value
               for value in (book, chapter, key)):
            raise ReferenceAdapterError(f"record {index} has invalid location fields")
        if key != f"{book}:{chapter}":
            raise ReferenceAdapterError(f"record {index} has an invalid chapter_key")
        if (not isinstance(ordinal, int) or isinstance(ordinal, bool) or ordinal < 1):
            raise ReferenceAdapterError(f"record {index} has an invalid paragraph ordinal")
        if not isinstance(text, str):
            raise ReferenceAdapterError(f"record {index} text must be a string")
        paragraph_key = (book, chapter, ordinal)
        if paragraph_key in seen_paragraphs:
            raise ReferenceAdapterError(f"duplicate paragraph key at record {index}")
        seen_paragraphs.add(paragraph_key)
        if key != current_chapter:
            if key in seen_chapters:
                raise ReferenceAdapterError(f"chapter group is not contiguous: {key}")
            seen_chapters.add(key)
            chapters.append(key)
            chapter_books[key] = book
            current_chapter = key
            expected_local = 1
            if book != current_book:
                if book in seen_books:
                    raise ReferenceAdapterError(f"book group is not contiguous: {book}")
                seen_books.add(book)
                current_book = book
        if ordinal != expected_local:
            raise ReferenceAdapterError(
                f"record {index} ordinal {ordinal} does not follow source order "
                f"{expected_local} in {key}"
            )
        expected_local += 1
    return source, tuple(chapters), chapter_books


def _assign_splits(chapters: tuple[str, ...], chapter_books: Mapping[str, str]) -> dict[str, str]:
    by_book: dict[str, list[str]] = defaultdict(list)
    for key in chapters:
        by_book[chapter_books[key]].append(key)
    result: dict[str, str] = {}
    for keys in by_book.values():
        train_count = len(keys) * 60 // 100
        validation_count = len(keys) * 20 // 100
        for index, key in enumerate(keys):
            if index < train_count:
                result[key] = "train"
            elif index < train_count + validation_count:
                result[key] = "validation"
            else:
                result[key] = "test"
    return result


def _manifest(source: tuple[Mapping[str, Any], ...], paragraphs: tuple[NormalizedParagraph, ...],
              partitions: dict[str, tuple[str, ...]], assignments: dict[str, str]) -> dict[str, Any]:
    books: list[str] = []
    for item in paragraphs:
        if item.book_id not in books:
            books.append(item.book_id)
    chapter_counts = Counter(item.chapter_key for item in paragraphs)
    book_counts = Counter(item.book_id for item in paragraphs)
    chapter_splits = {split: [key for key, value in assignments.items() if value == split]
                      for split in SPLITS}
    by_split = {split: [item for item in paragraphs if item.split == split] for split in SPLITS}
    summary: dict[str, dict[str, Any]] = {}
    for split in SPLITS:
        items = by_split[split]
        tokens = partitions[split]
        summary[split] = {
            "paragraph_count": len(items),
            "retained_paragraph_count": sum(item.retained for item in items),
            "token_count": len(tokens),
            "type_count": len(set(tokens)),
            "token_stream_sha256": _hash(list(tokens)),
            "retained_paragraph_sequence_sha256": _hash([
                list(item.tokens) for item in items if item.retained
            ]),
        }
    metadata = [{**item.location, "split": item.split,
                 "token_count": len(item.tokens), "retained": item.retained,
                 "exclusion": item.exclusion,
                 "rejected_run_count": item.rejected_run_count,
                 "roman_like_count": item.roman_like_count} for item in paragraphs]
    duplicate_counts = {
        split: sum(item.exclusion == "duplicate_cross_partition" for item in by_split[split])
        for split in SPLITS
    }
    empty_counts = {
        split: sum(item.exclusion == "empty_after_normalization" for item in by_split[split])
        for split in SPLITS
    }
    return {
        "schema_version": 1,
        "normalization": "normalize_word: NFKD casefold, remove combining marks, accept complete ASCII a-z forms",
        "tokenization": "maximal alphabetic runs plus adjacent Unicode combining marks",
        "split": {
            "unit": "book_id:chapter_id",
            "chapter_order": "input source order within each book",
            "integer_fractions": {"train": "60/100", "validation": "20/100", "test": "remainder"},
            "duplicate_priority": list(SPLITS),
            "within_split_duplicates_preserved": True,
            "chapter_assignments": chapter_splits,
        },
        "source": {
            "record_count": len(source), "book_count": len(books), "book_ids": books,
            "chapter_count": len(chapter_counts), "paragraphs_by_book": dict(book_counts),
            "paragraphs_by_chapter": dict(chapter_counts),
            "source_record_sha256": _hash([
                {name: record[name] for name in sorted(_FIELDS)} for record in source
            ]),
            "paragraph_metadata_sha256": _hash(metadata),
        },
        "partitions": summary,
        "exclusions": {
            "duplicate_cross_partition_by_split": duplicate_counts,
            "empty_after_normalization_by_split": empty_counts,
            "rejected_run_count_by_split": {
                split: sum(item.rejected_run_count for item in by_split[split])
                for split in SPLITS
            },
            "roman_like_token_count_by_split": {
                split: sum(item.roman_like_count for item in by_split[split])
                for split in SPLITS
            },
        },
        "raw_text_included": False,
    }


def adapt_projected_paragraphs(records: Iterable[Mapping[str, Any]]) -> AdaptedReference:
    """Tokenize and split projected paragraphs without reading XML."""

    source, chapters, chapter_books = _validate_records(records)
    assignments = _assign_splits(chapters, chapter_books)
    grouped: dict[str, list[NormalizedParagraph]] = {split: [] for split in SPLITS}
    for record in source:
        tokens, rejected, roman_like = normalize_projected_text(record["text"])
        item = NormalizedParagraph(
            record["book_id"], record["chapter_id"], record["chapter_key"],
            record["local_paragraph_ordinal"], assignments[record["chapter_key"]],
            tokens, bool(tokens), None if tokens else "empty_after_normalization",
            rejected, roman_like,
        )
        grouped[item.split].append(item)

    prior: set[tuple[str, ...]] = set()
    revised: list[NormalizedParagraph] = []
    streams: dict[str, list[str]] = {split: [] for split in SPLITS}
    for split in SPLITS:
        current = grouped[split]
        current_sequences = {item.tokens for item in current if item.tokens}
        for item in current:
            retained = item.retained
            exclusion = item.exclusion
            if item.tokens and item.tokens in prior:
                retained = False
                exclusion = "duplicate_cross_partition"
            revised.append(NormalizedParagraph(
                item.book_id, item.chapter_id, item.chapter_key,
                item.local_paragraph_ordinal, item.split, item.tokens,
                retained, exclusion, item.rejected_run_count, item.roman_like_count,
            ))
            if retained:
                streams[split].extend(item.tokens)
        prior.update(current_sequences)

    order = {(record["book_id"], record["chapter_id"], record["local_paragraph_ordinal"]): i
             for i, record in enumerate(source)}
    revised.sort(key=lambda item: order[(item.book_id, item.chapter_id, item.local_paragraph_ordinal)])
    final = tuple(revised)
    partitions = {split: tuple(streams[split]) for split in SPLITS}
    return AdaptedReference(final, partitions, _manifest(source, final, partitions, assignments))


__all__ = ["AdaptedReference", "NormalizedParagraph", "ReferenceAdapterError",
           "SPLITS", "adapt_projected_paragraphs", "normalize_projected_text"]
