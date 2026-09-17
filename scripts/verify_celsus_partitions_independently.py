#!/usr/bin/env python3
"""Verify the frozen Celsus partition outputs with independent stdlib code."""

from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sys
import unicodedata

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "celsus-reference-control-v1-independent-audit.json"
SPLITS = ("train", "validation", "test")
FIELDS = ("book_id", "chapter_id", "chapter_key", "local_paragraph_ordinal", "text")
ROMAN = re.compile(r"^[ivxlcdm]+$")
PINS = {
    "reports/celsus-projection-v1/acceptance.json": (12935, "8067be5cb874a8e53472d11e3188be0eb92b7c30c3def9f31de2451e06fc6faf"),
    "results/celsus-projection-v1/celsus-lat5.xml": (893899, "a4a5194ba38a7efd5192d20f2a7b696f4fa64105010eb629aa7c35255a935145"),
    "results/celsus-projection-v1/module-paragraphs.jsonl": (747194, "f37d99f5ad0771c32c4d71934b58df00438ca7dadf870f89dc93b181c1d373f2"),
    "results/celsus-reference-control-v1/partitions.private.json": (870217, "ca6209869b934958c04b9707c0c70652046abb118d365c9c9f272c6adb7802f1"),
    "results/celsus-reference-control-v1/paragraphs.private.jsonl": (973283, "6bc2af80bc11f728b81e218b0dd6a0c51878aec075c0f2bbd4415fb4df0e4f93"),
    "results/celsus-reference-control-v1/partition-manifest.json": (8843, "634ed31c54e1147ee930c6261ed9261938ec120f310db2e22ed54bca630dc9e1"),
}


class AuditError(RuntimeError):
    pass


def fail(message: str) -> None:
    raise AuditError(message)


def need(condition: bool, message: str) -> None:
    if not condition:
        fail(message)


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def load_pins() -> dict[str, bytes]:
    pinned: dict[str, bytes] = {}
    for name, (size, expected) in PINS.items():
        try:
            raw = (ROOT / name).read_bytes()
        except OSError as error:
            fail(f"missing pinned input: {name}")
        need(len(raw) == size, f"pinned byte count mismatch: {name}")
        need(digest(raw) == expected, f"pinned SHA-256 mismatch: {name}")
        pinned[name] = raw
    return pinned


def parse_json(raw: bytes, name: str) -> dict:
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        fail(f"invalid JSON: {name}")
    need(isinstance(value, dict), f"JSON object required: {name}")
    return value


def parse_jsonl(raw: bytes, name: str) -> list[dict]:
    rows: list[dict] = []
    for index, line in enumerate(raw.splitlines(), 1):
        need(line != b"", f"blank JSONL line: {name}:{index}")
        try:
            value = json.loads(line.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            fail(f"invalid JSONL row: {name}:{index}")
        need(isinstance(value, dict), f"JSONL object required: {name}:{index}")
        rows.append(value)
    return rows


def runs(text: str) -> list[str]:
    result: list[str] = []
    index = 0
    while index < len(text):
        if not text[index].isalpha():
            index += 1
            continue
        start = index
        index += 1
        while index < len(text) and (text[index].isalpha() or unicodedata.category(text[index]).startswith("M")):
            index += 1
        result.append(text[start:index])
    return result


def normalize(candidate: str) -> str | None:
    value = unicodedata.normalize("NFKD", candidate).casefold()
    value = "".join(char for char in value if not unicodedata.combining(char))
    return value if value and all("a" <= char <= "z" for char in value) else None


def tokenize(text: str) -> tuple[list[str], int, int]:
    tokens: list[str] = []
    rejected = 0
    roman_like = 0
    for candidate in runs(text):
        word = normalize(candidate)
        if word is None:
            rejected += 1
        else:
            tokens.append(word)
            roman_like += int(ROMAN.fullmatch(word) is not None)
    return tokens, rejected, roman_like


def location_key(row: dict) -> tuple[str, str, str, int]:
    return row["book_id"], row["chapter_id"], row["chapter_key"], row["local_paragraph_ordinal"]


def build_reference(records: list[dict]) -> tuple[list[dict], dict[str, list[str]], dict]:
    need(len(records) == 550, "projection record count is not 550")
    chapters: list[str] = []
    chapter_books: dict[str, str] = {}
    chapter_counts: Counter[str] = Counter()
    book_counts: Counter[str] = Counter()
    seen_books: set[str] = set()
    seen_chapters: set[str] = set()
    current_book = current_chapter = None
    expected_local = 1
    for index, row in enumerate(records):
        need(tuple(row) == FIELDS, f"projection fields differ at record {index + 1}")
        book, chapter, key = row["book_id"], row["chapter_id"], row["chapter_key"]
        need(all(isinstance(value, str) and value for value in (book, chapter, key)), f"invalid location at record {index + 1}")
        need(key == f"{book}:{chapter}", f"chapter key mismatch at record {index + 1}")
        need(isinstance(row["local_paragraph_ordinal"], int) and row["local_paragraph_ordinal"] >= 1, f"invalid ordinal at record {index + 1}")
        need(key == current_chapter or key not in seen_chapters, f"non-contiguous chapter at record {index + 1}")
        if key != current_chapter:
            seen_chapters.add(key)
            chapters.append(key)
            chapter_books[key] = book
            chapter_counts[key] = 0
            expected_local = 1
            if book != current_book:
                need(book not in seen_books, f"non-contiguous book at record {index + 1}")
                seen_books.add(book)
                current_book = book
            current_chapter = key
        need(row["local_paragraph_ordinal"] == expected_local, f"ordinal gap at record {index + 1}")
        expected_local += 1
        chapter_counts[key] += 1
        book_counts[book] += 1
    need(tuple(sorted(seen_books, key=int)) == tuple(str(i) for i in range(1, 9)), "book IDs differ")
    need(len(chapters) == 211, "chapter count is not 211")
    assignments: dict[str, str] = {}
    chapter_lists = {split: [] for split in SPLITS}
    for book in sorted(seen_books, key=int):
        keys = [key for key in chapters if chapter_books[key] == book]
        train_count = len(keys) * 60 // 100
        validation_count = len(keys) * 20 // 100
        for index, key in enumerate(keys):
            split = "train" if index < train_count else "validation" if index < train_count + validation_count else "test"
            assignments[key] = split
            chapter_lists[split].append(key)
    items: list[dict] = []
    for row in records:
        tokens, rejected, roman_like = tokenize(row["text"])
        items.append({
            "book_id": row["book_id"], "chapter_id": row["chapter_id"], "chapter_key": row["chapter_key"],
            "local_paragraph_ordinal": row["local_paragraph_ordinal"], "split": assignments[row["chapter_key"]],
            "tokens": tokens, "retained": bool(tokens), "exclusion": None if tokens else "empty_after_normalization",
            "rejected_run_count": rejected, "roman_like_count": roman_like,
        })
    prior: set[tuple[str, ...]] = set()
    streams = {split: [] for split in SPLITS}
    for split in SPLITS:
        current = [item for item in items if item["split"] == split]
        current_sequences = {tuple(item["tokens"]) for item in current if item["tokens"]}
        for item in current:
            sequence = tuple(item["tokens"])
            if sequence and sequence in prior:
                item["retained"] = False
                item["exclusion"] = "duplicate_cross_partition"
            if item["retained"]:
                streams[split].extend(item["tokens"])
        prior.update(current_sequences)
    by_split = {split: [item for item in items if item["split"] == split] for split in SPLITS}
    summary = {}
    for split in SPLITS:
        selected = by_split[split]
        tokens = streams[split]
        summary[split] = {
            "paragraph_count": len(selected), "retained_paragraph_count": sum(item["retained"] for item in selected),
            "token_count": len(tokens), "type_count": len(set(tokens)), "token_stream_sha256": digest(canonical(tokens)),
            "retained_paragraph_sequence_sha256": digest(canonical([item["tokens"] for item in selected if item["retained"]])),
        }
    metadata = [{key: item[key] for key in ("book_id", "chapter_id", "chapter_key", "local_paragraph_ordinal", "split", "tokens", "retained", "exclusion", "rejected_run_count", "roman_like_count") if key != "tokens"} | {"token_count": len(item["tokens"])} for item in items]
    source_record_sha = digest(canonical([{key: row[key] for key in sorted(FIELDS)} for row in records]))
    manifest = {
        "schema_version": 1,
        "normalization": "normalize_word: NFKD casefold, remove combining marks, accept complete ASCII a-z forms",
        "tokenization": "maximal alphabetic runs plus adjacent Unicode combining marks",
        "split": {"unit": "book_id:chapter_id", "chapter_order": "input source order within each book", "integer_fractions": {"train": "60/100", "validation": "20/100", "test": "remainder"}, "duplicate_priority": list(SPLITS), "within_split_duplicates_preserved": True, "chapter_assignments": chapter_lists},
        "source": {"record_count": len(records), "book_count": 8, "book_ids": sorted(seen_books, key=int), "chapter_count": len(chapter_counts), "paragraphs_by_book": dict(book_counts), "paragraphs_by_chapter": dict(chapter_counts), "source_record_sha256": source_record_sha, "paragraph_metadata_sha256": digest(canonical(metadata))},
        "partitions": summary,
        "exclusions": {
            "duplicate_cross_partition_by_split": {split: sum(item["exclusion"] == "duplicate_cross_partition" for item in by_split[split]) for split in SPLITS},
            "empty_after_normalization_by_split": {split: sum(item["exclusion"] == "empty_after_normalization" for item in by_split[split]) for split in SPLITS},
            "rejected_run_count_by_split": {split: sum(item["rejected_run_count"] for item in by_split[split]) for split in SPLITS},
            "roman_like_token_count_by_split": {split: sum(item["roman_like_count"] for item in by_split[split]) for split in SPLITS},
        },
        "raw_text_included": False,
    }
    return items, streams, {"manifest": manifest, "chapter_lists": chapter_lists, "book_counts": dict(book_counts), "chapter_counts": dict(chapter_counts)}


def write_identical(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as stream:
            stream.write(raw)
    except FileExistsError:
        need(path.read_bytes() == raw, "audit output exists with different bytes")


def main() -> int:
    try:
        pinned = load_pins()
        need(normalize("a\u034f") is None, "class-zero combining mark was removed")
        acceptance = parse_json(pinned["reports/celsus-projection-v1/acceptance.json"], "acceptance")
        need(acceptance.get("status") == "COMPLETE" and acceptance.get("result") == "PASS" and acceptance.get("manual_acceptance") == "ACCEPTED", "accepted projection status mismatch")
        records = parse_jsonl(pinned["results/celsus-projection-v1/module-paragraphs.jsonl"], "projection")
        items, streams, built = build_reference(records)
        private_partitions = parse_json(pinned["results/celsus-reference-control-v1/partitions.private.json"], "private partitions")
        private_paragraphs = parse_jsonl(pinned["results/celsus-reference-control-v1/paragraphs.private.jsonl"], "private paragraphs")
        expected_rows = items
        need(private_partitions == streams, "private partition arrays differ")
        need(private_paragraphs == expected_rows, "private paragraph metadata differs")
        manifest = parse_json(pinned["results/celsus-reference-control-v1/partition-manifest.json"], "public manifest")
        adapter = manifest.get("adapter", {}).get("manifest")
        need(adapter == built["manifest"], "public adapter manifest differs")
        need(manifest.get("raw_text_included") is False, "public manifest raw-text flag is set")
        need(manifest.get("source", {}).get("sha256") == PINS["results/celsus-projection-v1/celsus-lat5.xml"][1], "public source hash differs")
        need(manifest.get("projection", {}).get("module", {}).get("sha256") == PINS["results/celsus-projection-v1/module-paragraphs.jsonl"][1], "public module hash differs")
        need(manifest.get("projection", {}).get("independent", {}).get("sha256") == PINS["results/celsus-projection-v1/module-paragraphs.jsonl"][1], "public independent hash differs")
        private_hashes = {"partitions.private.json": digest(pinned["results/celsus-reference-control-v1/partitions.private.json"]), "paragraphs.private.jsonl": digest(pinned["results/celsus-reference-control-v1/paragraphs.private.jsonl"])}
        for name, expected in private_hashes.items():
            item = manifest.get("private_outputs", {}).get(name, {})
            need(item.get("sha256") == expected and item.get("bytes") == len(pinned["results/celsus-reference-control-v1/" + name]), f"private output manifest mismatch: {name}")
        duplicates = adapter["exclusions"]["duplicate_cross_partition_by_split"]
        need(duplicates == {split: 0 for split in SPLITS}, "cross-partition duplicate found")
        checks = {
            "source_pins": True, "accepted_projection": True, "books": built["manifest"]["source"]["book_count"] == 8,
            "chapters": built["manifest"]["source"]["chapter_count"] == 211, "paragraphs": built["manifest"]["source"]["record_count"] == 550,
            "floor_split_rule": True, "private_partition_arrays_exact": True, "private_paragraph_rows_exact": True,
            "public_adapter_manifest_exact": True,
            "combining_class_zero_mark_rejected": True,
            "cross_partition_duplicates_zero": True,
        }
        need(all(checks.values()), "independent audit check failed")
        public = {
            "schema_version": 1, "verification": "celsus-reference-control-independent-audit", "status": "PASS",
            "method": "Independent stdlib tokenization, split assignment, normalization, deduplication, hashing, and comparison. No project adapter or partition runner was imported.",
            "inputs": {name: {"bytes": size, "sha256": expected} for name, (size, expected) in PINS.items()},
            "source": {"book_count": 8, "chapter_count": 211, "record_count": 550, "book_ids": [str(i) for i in range(1, 9)], "chapter_count_by_split": {split: len(built["chapter_lists"][split]) for split in SPLITS}, "paragraph_count_by_split": {split: built["manifest"]["partitions"][split]["paragraph_count"] for split in SPLITS}},
            "split": {"unit": "book_id:chapter_id", "fractions": {"train": "floor(60/100)", "validation": "floor(20/100)", "test": "remainder"}, "chapter_order": "source order within each book", "floor_rule_match": True},
            "partitions": {split: {"paragraph_count": built["manifest"]["partitions"][split]["paragraph_count"], "retained_paragraph_count": built["manifest"]["partitions"][split]["retained_paragraph_count"], "token_count": built["manifest"]["partitions"][split]["token_count"], "type_count": built["manifest"]["partitions"][split]["type_count"], "rejected_run_count": built["manifest"]["exclusions"]["rejected_run_count_by_split"][split], "roman_like_count": built["manifest"]["exclusions"]["roman_like_token_count_by_split"][split], "empty_count": built["manifest"]["exclusions"]["empty_after_normalization_by_split"][split], "cross_partition_duplicate_count": duplicates[split], "token_stream_sha256": built["manifest"]["partitions"][split]["token_stream_sha256"], "retained_paragraph_sequence_sha256": built["manifest"]["partitions"][split]["retained_paragraph_sequence_sha256"]} for split in SPLITS},
            "private_outputs": {name: {"bytes": len(pinned["results/celsus-reference-control-v1/" + name]), "sha256": digest(pinned["results/celsus-reference-control-v1/" + name]), "exact_match": True} for name in ("partitions.private.json", "paragraphs.private.jsonl")},
            "comparisons": {"private_partition_arrays": True, "private_paragraph_rows": True, "public_adapter_manifest": True, "module_projection_pin": True, "independent_projection_pin": True, "cross_partition_duplicates_zero": True},
            "checks": checks,
            "limitations": ["This audit verifies one frozen Celsus source and one fixed chapter split.", "It does not test a cipher, a model, or the Voynich manuscript.", "Near duplicates within or across chapters remain possible and are not removed."],
        }
        raw = (json.dumps(public, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
        write_identical(OUT, raw)
        print("Celsus partition audit: PASS")
        print(f"audit_sha256={digest(raw)}")
        return 0
    except AuditError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
