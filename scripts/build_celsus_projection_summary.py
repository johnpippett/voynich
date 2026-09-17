#!/usr/bin/env python3
"""Build aggregate public results for the frozen Celsus projection."""

from __future__ import annotations

import hashlib
import io
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results" / "celsus-projection-v1"
REPLAY_INPUT = ROOT / "results" / "celsus-projection-v1-replay-verification.json"
ADDENDUM_INPUT = RESULTS / "manual-review-batch2-addendum.json"
REPORTS = ROOT / "reports"
PUBLIC_DIR = REPORTS / "celsus-projection-v1"

PROTOCOL = "celsus-projection-v1"
SCHEMA_VERSION = 1
FROZEN_COMMIT = "c1753fc1f71836f50ff7c6946d722dead07441a9"
FIRST_PROJECTION_CI_CUTOFF = "2026-09-17T09:59:43.718620Z"
CI_RUN_URL = "https://github.com/johnpippett/voynich/actions/runs/35207958885"
FEATURES = (
    "location_fields",
    "source_spelling",
    "xml_whitespace",
    "choice_correction",
    "excluded_content",
    "tails",
    "transparent_markers",
    "empty_status",
)
FEATURE_STATUSES = ("PASS", "FEATURE_NOT_PRESENT", "FAIL")
TEI = "http://www.tei-c.org/ns/1.0"
XML_LANG = "http://www.w3.org/XML/1998/namespace"

EXPECTED_SOURCE = {
    "bytes": 893899,
    "sha256": "a4a5194ba38a7efd5192d20f2a7b696f4fa64105010eb629aa7c35255a935145",
    "commit": "ae0fe427f56d7652efc3090af74a2663a4cbed60",
    "audit_revision": "f26874c",
    "audit_receipt_sha256": "aebba00a41c120e4101d94c67f4783e9de55106051d158f3ccd41246d960e6de",
    "url": "https://raw.githubusercontent.com/PerseusDL/canonical-latinLit/ae0fe427f56d7652efc3090af74a2663a4cbed60/data/phi0836/phi002/phi0836.phi002.perseus-lat5.xml",
    "repository": "https://github.com/PerseusDL/canonical-latinLit",
}
EXPECTED_BOOKS = tuple(str(value) for value in range(1, 9))
EXPECTED_CHAPTERS_BY_BOOK = {
    "1": 11,
    "2": 34,
    "3": 27,
    "4": 32,
    "5": 29,
    "6": 19,
    "7": 34,
    "8": 25,
}
EXPECTED_PARAGRAPHS_BY_BOOK = {
    "1": 28,
    "2": 45,
    "3": 45,
    "4": 35,
    "5": 204,
    "6": 80,
    "7": 74,
    "8": 39,
}
EXPECTED_SOURCE_COUNTS = {
    "body": 1,
    "choice": 446,
    "corr": 446,
    "del": 10,
    "div": 220,
    "figure": 5,
    "foreign": 276,
    "head": 217,
    "hi": 525,
    "milestone": 1807,
    "note": 628,
    "p": 550,
    "pb": 361,
    "sic": 446,
}
EXPECTED_SELECTED_COUNTS = {
    "choice": 446,
    "corr": 446,
    "del": 7,
    "figure": 4,
    "foreign": 276,
    "head": 4,
    "hi": 525,
    "milestone": 1804,
    "note": 626,
    "p": 550,
    "pb": 308,
    "sic": 446,
}
EXPECTED_FREEZE_FILES = {
    "docs/plans/celsus-projection-v1.md": "3f9dcb864c9302d220d0fe1cafbc869ef9422724221fe38860f9481e3ff28efa",
    "experiments/medical/tei_projection.py": "d736f77a172854de0ada730d1775d36ae02691e5e0ee547931e8208120dfbadc",
    "experiments/medical/run_projection.py": "810f9083c1f38ddae272e38e68b494295527c0bed95dd7be2e6f93dfb18f6581",
    "experiments/medical/test_tei_projection.py": "c190fe6a748a4df77a2d1e55faf21f0232c0fb64a68ee41d2d752cdcb2f937ed",
    "experiments/medical/test_run_projection.py": "09e54635b7c2fe618e874661548b426b9b2698f1e7c5f98d1fb35e7dfcb3a4ff",
}
EXPECTED_OUTPUT_PATHS = (
    "results/celsus-projection-v1/public-receipt.json",
    "results/celsus-projection-v1/module-paragraphs.jsonl",
    "results/celsus-projection-v1/independent-paragraphs.jsonl",
    "results/celsus-projection-v1/manual-checklist.json",
    "results/celsus-projection-v1/manual-context.jsonl",
)
EXPECTED_INPUT_PINS = {
    "results/celsus-projection-v1/public-receipt.json": {
        "bytes": 16074,
        "sha256": "f9333cdac5f45742f23ffb76b8600421635296fa1b855ab54412f3b94300be91",
    },
    "results/celsus-projection-v1/module-paragraphs.jsonl": {
        "bytes": 747194,
        "sha256": "f37d99f5ad0771c32c4d71934b58df00438ca7dadf870f89dc93b181c1d373f2",
    },
    "results/celsus-projection-v1/independent-paragraphs.jsonl": {
        "bytes": 747194,
        "sha256": "f37d99f5ad0771c32c4d71934b58df00438ca7dadf870f89dc93b181c1d373f2",
    },
    "results/celsus-projection-v1/manual-checklist.json": {
        "bytes": 15401,
        "sha256": "32bdec1422e4b80d25139b275b3810bff2f5ffb2818e2c628bebb5f886402aca",
    },
    "results/celsus-projection-v1/manual-context.jsonl": {
        "bytes": 183880,
        "sha256": "1e5186bcbac24ae86e52aae46dbc249732473752fdeb73908003b8e697ee44f5",
    },
    "results/celsus-projection-v1-replay-verification.json": {
        "bytes": 2476,
        "sha256": "13c1daf30d9cb95cf4ea8131d9eb88fe683002ab392a7d5a3c0309a190eb0e63",
    },
    "results/celsus-projection-v1/manual-review-batch1.json": {
        "bytes": 22948,
        "sha256": "9e6cd2a406d97d3783ced93e613ec221fd25746d0a4fe35af33524b2fcaaa4ea",
    },
    "results/celsus-projection-v1/manual-review-batch2.json": {
        "bytes": 34144,
        "sha256": "f81465266f6db30c4be32a7a99bb7e9bba9bba1851f6314c911eb0254b02abf0",
    },
    "results/celsus-projection-v1/manual-review-batch3.json": {
        "bytes": 29705,
        "sha256": "f85c36b52c87ae2236f3a5451f0bee0d3cf974773c766057d2cb4bca48296fa2",
    },
}
EXPECTED_ADDENDUM_BYTES = 6391
EXPECTED_ADDENDUM_SHA256 = "a48343da05329a331e21c8835b481e56b8be86cbc872944fd425591587935747"


class BuildError(RuntimeError):
    """Raised when an input or an existing public output is unsafe."""


def fail(message: str) -> None:
    raise BuildError(message)


def require(condition: bool, message: str) -> None:
    if not condition:
        fail(message)


def read_bytes(path: Path) -> bytes:
    try:
        return path.read_bytes()
    except OSError as exc:
        fail(f"cannot read required input: {relative(path)} ({exc})")
    raise AssertionError


def pin_inputs() -> dict[str, bytes]:
    """Read and pin every reviewed result before any JSON parsing."""
    pinned: dict[str, bytes] = {}
    for relative_path, expected in EXPECTED_INPUT_PINS.items():
        raw = read_bytes(ROOT / relative_path)
        assert_field(len(raw), expected["bytes"], f"pinned byte count {relative_path}")
        assert_field(sha256(raw), expected["sha256"], f"pinned SHA-256 {relative_path}")
        pinned[relative_path] = raw
    addendum_raw = read_bytes(ADDENDUM_INPUT)
    assert_field(len(addendum_raw), EXPECTED_ADDENDUM_BYTES, "pinned addendum byte count")
    assert_field(sha256(addendum_raw), EXPECTED_ADDENDUM_SHA256, "pinned addendum SHA-256")
    pinned[relative(ADDENDUM_INPUT)] = addendum_raw
    for index in range(1, 4):
        relative_path = f"results/celsus-projection-v1/manual-review-batch{index}.json"
        require(relative_path in pinned, f"missing pinned review artifact: {relative_path}")
    return pinned


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(read_bytes(path).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        fail(f"invalid JSON input: {relative(path)} ({exc})")
    require(isinstance(value, dict), f"JSON input is not an object: {relative(path)}")
    return value


def read_jsonl(path: Path) -> tuple[bytes, list[dict[str, Any]]]:
    raw = read_bytes(path)
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(raw.splitlines(), 1):
        require(line != b"", f"blank JSONL line: {relative(path)}:{line_number}")
        try:
            value = json.loads(line.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            fail(f"invalid JSONL input: {relative(path)}:{line_number} ({exc})")
        require(isinstance(value, dict), f"JSONL row is not an object: {relative(path)}:{line_number}")
        rows.append(value)
    return raw, rows


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def pretty_json(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def relative(path: Path) -> str:
    try:
        value = path.resolve().relative_to(ROOT.resolve())
    except ValueError:
        return str(path)
    return value.as_posix()


def write_identical(path: Path, payload: bytes) -> None:
    """Create a public file, or accept an exact existing copy."""
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as handle:
            handle.write(payload)
    except FileExistsError:
        try:
            existing = path.read_bytes()
        except OSError as exc:
            fail(f"cannot read existing output: {relative(path)} ({exc})")
        if existing != payload:
            fail(f"existing output differs: {relative(path)}")


def assert_field(value: Any, expected: Any, label: str) -> None:
    require(value == expected, f"unexpected {label}: {value!r}")


def record_key(record: dict[str, Any]) -> tuple[str, str, str, int]:
    required = ("book_id", "chapter_id", "chapter_key", "local_paragraph_ordinal", "text")
    assert_field(tuple(record.keys()), required, "record key order")
    return (
        record["book_id"],
        record["chapter_id"],
        record["chapter_key"],
        record["local_paragraph_ordinal"],
    )


def record_hash(record: dict[str, Any]) -> str:
    return sha256(canonical_json(record))


def text_hash(record: dict[str, Any]) -> str:
    return sha256(record["text"].encode("utf-8"))


def source_location(book_id: str, chapter_id: str, local_ordinal: int, global_ordinal: int) -> dict[str, Any]:
    return {
        "book_id": book_id,
        "chapter_id": chapter_id,
        "chapter_key": f"{book_id}:{chapter_id}",
        "global_source_paragraph_ordinal": global_ordinal,
        "local_paragraph_ordinal": local_ordinal,
    }


def load_source(receipt: dict[str, Any]) -> tuple[bytes, list[dict[str, Any]], dict[str, Any]]:
    source = receipt["source"]
    for key, expected in EXPECTED_SOURCE.items():
        assert_field(source[key], expected, f"source.{key}")
    raw = read_bytes(RESULTS / "celsus-lat5.xml")
    assert_field(len(raw), EXPECTED_SOURCE["bytes"], "source byte count")
    assert_field(sha256(raw), EXPECTED_SOURCE["sha256"], "source SHA-256")
    try:
        root = ET.parse(io.BytesIO(raw)).getroot()
    except (ET.ParseError, OSError) as exc:
        fail(f"source XML is not readable: {exc}")
    ns = "{" + TEI + "}"
    body_nodes = [node for node in root.iter() if node.tag == ns + "body"]
    require(len(body_nodes) == 1, "source must have one body")
    body = body_nodes[0]
    wrappers = [
        node
        for node in list(body)
        if node.tag == ns + "div"
        and node.attrib.get("type") == "edition"
        and node.attrib.get("{" + XML_LANG + "}lang") == "lat"
    ]
    require(len(wrappers) == 1, "source must have one Latin edition wrapper")
    wrapper = wrappers[0]
    books = [
        node
        for node in list(wrapper)
        if node.tag == ns + "div"
        and node.attrib.get("type") == "textpart"
        and node.attrib.get("subtype") == "book"
    ]
    assert_field([node.attrib.get("n") for node in books], list(EXPECTED_BOOKS), "source book order")
    paragraphs: list[dict[str, Any]] = []
    chapter_keys: list[str] = []
    chapters_by_book: dict[str, int] = {}
    paragraphs_by_book: dict[str, int] = {}
    paragraphs_by_chapter: dict[str, int] = {}
    for book in books:
        book_id = book.attrib.get("n")
        require(book_id is not None, "source book has no n attribute")
        chapters = [
            node
            for node in list(book)
            if node.tag == ns + "div"
            and node.attrib.get("type") == "textpart"
            and node.attrib.get("subtype") == "chapter"
        ]
        chapters_by_book[book_id] = len(chapters)
        paragraphs_by_book[book_id] = 0
        for chapter in chapters:
            chapter_id = chapter.attrib.get("n")
            require(chapter_id is not None, "source chapter has no n attribute")
            chapter_key = f"{book_id}:{chapter_id}"
            require(chapter_key not in chapter_keys, f"duplicate source chapter key: {chapter_key}")
            chapter_keys.append(chapter_key)
            p_nodes = [node for node in list(chapter) if node.tag == ns + "p"]
            paragraphs_by_chapter[chapter_key] = len(p_nodes)
            for local_ordinal, p_node in enumerate(p_nodes, 1):
                global_ordinal = len(paragraphs) + 1
                location = source_location(book_id, chapter_id, local_ordinal, global_ordinal)
                paragraphs.append({"location": location, "source_xml": ET.tostring(p_node, encoding="unicode")})
                paragraphs_by_book[book_id] += 1
    assert_field(len(chapters_by_book), 8, "source book count")
    assert_field(chapters_by_book, EXPECTED_CHAPTERS_BY_BOOK, "source chapters by book")
    assert_field(paragraphs_by_book, EXPECTED_PARAGRAPHS_BY_BOOK, "source paragraphs by book")
    assert_field(len(chapter_keys), 211, "source chapter count")
    assert_field(len(paragraphs), 550, "source paragraph count")
    all_p_count = sum(1 for node in wrapper.iter() if node.tag == ns + "p")
    assert_field(all_p_count, 550, "all selected source paragraphs")
    structure = {
        "book_count": len(books),
        "chapter_count": len(chapter_keys),
        "paragraph_count": len(paragraphs),
        "chapters_by_book": chapters_by_book,
        "paragraphs_by_book": paragraphs_by_book,
        "paragraphs_by_chapter": paragraphs_by_chapter,
        "empty_source_paragraph_count": sum(
            1 for item in paragraphs if not (item["source_xml"] and item["source_xml"].strip())
        ),
    }
    assert_field(structure["empty_source_paragraph_count"], 0, "empty source paragraphs")
    return raw, paragraphs, structure


def verify_receipt(receipt: dict[str, Any], source_structure: dict[str, Any]) -> None:
    assert_field(receipt["schema_version"], SCHEMA_VERSION, "receipt schema")
    assert_field(receipt["protocol"], PROTOCOL, "receipt protocol")
    assert_field(receipt["status"], "PENDING_MANUAL_REVIEW", "initial receipt status")
    assert_field(receipt["manual_acceptance"], "PENDING", "initial receipt manual acceptance")
    assert_field(receipt["validation_scope"], "pinned_source", "validation scope")
    assert_field(receipt["empty_policy"], "include", "empty policy")
    assert_field(receipt["source_review_date"], "2026-09-17", "source review date")
    source = receipt["source"]
    require(all(source["audit_receipt_checks"].values()), "source audit receipt has a false check")
    structure = receipt["structure"]
    assert_field(structure["book_ids"], list(EXPECTED_BOOKS), "receipt book IDs")
    assert_field(structure["chapter_count"], source_structure["chapter_count"], "receipt chapter count")
    assert_field(structure["paragraph_count"], source_structure["paragraph_count"], "receipt paragraph count")
    assert_field(structure["chapters_by_book"], source_structure["chapters_by_book"], "receipt chapters by book")
    assert_field(structure["paragraphs_by_book"], source_structure["paragraphs_by_book"], "receipt paragraphs by book")
    assert_field(structure["paragraphs_by_chapter"], source_structure["paragraphs_by_chapter"], "receipt paragraphs by chapter")
    assert_field(structure["empty_source_paragraph_count"], 0, "receipt empty source count")
    assert_field(structure["paragraphs_outside_book_chapter"], 0, "receipt outside paragraph count")
    assert_field(structure["source_counts"], EXPECTED_SOURCE_COUNTS, "receipt source counts")
    assert_field(structure["selected_subtree_counts"], EXPECTED_SELECTED_COUNTS, "receipt selected counts")
    require(structure["wrapper_book_count"] == 8, "receipt wrapper book count is not eight")
    require(structure["edition_wrapper_count"] == 1, "receipt edition wrapper count is not one")
    require(structure["wrapper_pb_count"] == 7, "receipt wrapper page-break count is not seven")
    require(receipt["comparison"] == {
        "paragraph_hashes_equal": True,
        "records_equal": True,
        "reports_equal": True,
    }, "receipt comparison is not fully true")
    require(receipt["checks"]["source_pinned"] is True, "receipt source pin check failed")
    require(receipt["checks"]["audit_receipt_pinned"] is True, "receipt audit pin check failed")
    require(receipt["checks"]["source_structure_targets"] is True, "receipt structure check failed")
    assert_field(receipt["checks"]["source_structure_targets_status"], "PASS", "receipt structure status")
    freeze = receipt["freeze"]
    assert_field(freeze["protocol"], PROTOCOL, "receipt freeze protocol")
    assert_field(freeze["schema_version"], SCHEMA_VERSION, "receipt freeze schema")
    assert_field(freeze["manifest_path"], "experiments/medical/freeze-v1.json", "receipt freeze path")
    freeze_files = {item["path"]: item["sha256"] for item in freeze["files"]}
    assert_field(freeze_files, EXPECTED_FREEZE_FILES, "receipt freeze files")
    manifest_raw = read_bytes(ROOT / "experiments/medical/freeze-v1.json")
    assert_field(sha256(manifest_raw), freeze["manifest_sha256"], "freeze manifest SHA-256")
    manifest = read_json(ROOT / "experiments/medical/freeze-v1.json")
    assert_field(manifest.get("protocol"), PROTOCOL, "freeze manifest protocol")
    assert_field(manifest.get("schema_version"), SCHEMA_VERSION, "freeze manifest schema")
    manifest_files = {item["path"]: item["sha256"] for item in manifest.get("files", [])}
    assert_field(manifest_files, EXPECTED_FREEZE_FILES, "freeze manifest files")
    require(source_structure["book_count"] == 8, "source structure has the wrong book count")
    require(source_structure["chapter_count"] == 211, "source structure has the wrong chapter count")
    require(source_structure["paragraph_count"] == 550, "source structure has the wrong paragraph count")


def verify_projection(
    receipt: dict[str, Any],
    source_paragraphs: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    module_raw, module_rows = read_jsonl(RESULTS / "module-paragraphs.jsonl")
    independent_raw, independent_rows = read_jsonl(RESULTS / "independent-paragraphs.jsonl")
    for name, raw, rows, expected in (
        ("module", module_raw, module_rows, receipt["module"]),
        ("independent", independent_raw, independent_rows, receipt["independent"]),
    ):
        assert_field(len(rows), expected["record_count"], f"{name} record count")
        assert_field(len(raw), expected["bytes"], f"{name} byte count")
        assert_field(sha256(raw), expected["sha256"], f"{name} SHA-256")
        assert_field(len(rows), 550, f"{name} fixed record count")
    assert_field(module_rows, independent_rows, "module and independent records")
    assert_field(module_raw, independent_raw, "module and independent bytes")
    expected_keys = [
        (
            item["location"]["book_id"],
            item["location"]["chapter_id"],
            item["location"]["chapter_key"],
            item["location"]["local_paragraph_ordinal"],
        )
        for item in source_paragraphs
    ]
    rows_by_key: dict[tuple[str, str, str, int], dict[str, Any]] = {}
    for row in module_rows:
        key = record_key(row)
        require(key not in rows_by_key, f"duplicate projected record key: {key}")
        rows_by_key[key] = row
    assert_field(list(rows_by_key), expected_keys, "projected record order")
    module_report = receipt["module"]["report"]
    independent_report = receipt["independent"]["report"]
    assert_field(module_report, independent_report, "module and independent reports")
    assert_field(module_report["source_paragraph_count"], 550, "projection source paragraph count")
    assert_field(module_report["projected_paragraph_count"], 550, "projection paragraph count")
    assert_field(module_report["dropped_empty_paragraph_count"], 0, "dropped empty paragraph count")
    assert_field(module_report["empty_projected_paragraph_count"], 0, "empty projected paragraph count")
    assert_field(module_report["empty_projected_paragraph_policy"], "include", "projection empty policy")
    assert_field(module_report["projected_paragraphs_by_book"], EXPECTED_PARAGRAPHS_BY_BOOK, "projected paragraphs by book")
    assert_field(len(module_report["projected_paragraphs_by_chapter"]), 211, "projected chapter count")
    assert_field(module_report["projected_paragraphs_by_chapter"], receipt["structure"]["paragraphs_by_chapter"], "projected paragraphs by chapter")
    assert_field(module_report["selected_subtree_counts"], EXPECTED_SELECTED_COUNTS, "projection selected counts")
    assert_field(module_report["source_counts"], EXPECTED_SOURCE_COUNTS, "projection source counts")
    assert_field(module_report["boundary_validation"], {"status": "PASS"}, "projection boundary validation")
    report_summary = {
        "record_count": len(module_rows),
        "bytes": len(module_raw),
        "sha256": sha256(module_raw),
        "projected_paragraphs_by_book": module_report["projected_paragraphs_by_book"],
        "projected_chapter_count": len(module_report["projected_paragraphs_by_chapter"]),
        "empty_projected_paragraph_count": module_report["empty_projected_paragraph_count"],
        "dropped_empty_paragraph_count": module_report["dropped_empty_paragraph_count"],
        "actual_retained": module_report["actual_retained"],
        "direct_excluded": module_report["direct_excluded"],
        "ancestor_excluded": module_report["ancestor_excluded"],
        "boundary_validation": module_report["boundary_validation"],
    }
    return module_rows, independent_rows, report_summary


def verify_context(
    receipt: dict[str, Any],
    source_paragraphs: list[dict[str, Any]],
    module_rows: list[dict[str, Any]],
) -> tuple[bytes, list[dict[str, Any]]]:
    context_raw, context_rows = read_jsonl(RESULTS / "manual-context.jsonl")
    expected = receipt["manual_context"]
    assert_field(len(context_rows), expected["record_count"], "manual context record count")
    assert_field(len(context_raw), expected["bytes"], "manual context byte count")
    assert_field(sha256(context_raw), expected["sha256"], "manual context SHA-256")
    assert_field(len(context_rows), 30, "fixed manual context count")
    source_by_key = {
        (
            item["location"]["book_id"],
            item["location"]["chapter_id"],
            item["location"]["chapter_key"],
            item["location"]["local_paragraph_ordinal"],
        ): item
        for item in source_paragraphs
    }
    record_by_key = {record_key(row): row for row in module_rows}
    seen: set[tuple[str, str, str, int]] = set()
    for index, context in enumerate(context_rows, 1):
        require(set(context) == {"location", "source_xml", "module_record", "independent_record"}, f"manual context keys at {index}")
        location = context["location"]
        key = (
            location["book_id"],
            location["chapter_id"],
            location["chapter_key"],
            location["local_paragraph_ordinal"],
        )
        require(key not in seen, f"duplicate manual context location at {index}")
        seen.add(key)
        require(key in source_by_key, f"manual context location is not in source at {index}")
        source_item = source_by_key[key]
        assert_field(location, source_item["location"], f"manual context location {index}")
        assert_field(context["source_xml"], source_item["source_xml"], f"manual context source XML {index}")
        require(key in record_by_key, f"manual context record location is not projected at {index}")
        assert_field(context["module_record"], record_by_key[key], f"manual context module record {index}")
        assert_field(context["independent_record"], record_by_key[key], f"manual context independent record {index}")
    return context_raw, context_rows


def counts_template() -> dict[str, dict[str, int]]:
    return {feature: {status: 0 for status in FEATURE_STATUSES} for feature in FEATURES}


def normalize_reported_counts(value: dict[str, Any]) -> dict[str, dict[str, int]]:
    result = counts_template()
    for feature in FEATURES:
        require(feature in value, f"review aggregate has no feature: {feature}")
        raw = value[feature]
        require(isinstance(raw, dict), f"review aggregate feature is not an object: {feature}")
        for status in FEATURE_STATUSES:
            result[feature][status] = int(raw.get(status, 0))
        require(set(raw).issubset(set(FEATURE_STATUSES)), f"review aggregate has unknown status: {feature}")
    return result


def review_source_hash(item: dict[str, Any], batch_name: str) -> tuple[str, int]:
    if batch_name == "batch1":
        value = item["source_xml"]
        return value["sha256"], value["bytes_utf8"]
    if batch_name == "batch2":
        value = item["source_subtree"]
        return value["sha256"], value["bytes"]
    value = item["source_xml_sha256"]
    return value, item["counts"]["source_xml_bytes"]


def review_index(item: dict[str, Any], batch_name: str) -> int:
    return item["file_index"] if batch_name == "batch1" else item["batch_index"]


def review_record_hashes(item: dict[str, Any], batch_name: str) -> tuple[str, str]:
    if batch_name == "batch1":
        return item["module_record_sha256"], item["independent_record_sha256"]
    if batch_name == "batch2":
        value = item["records"]
        return value["module_record_sha256"], value["independent_record_sha256"]
    return item["module_text_sha256"], item["independent_text_sha256"]


def verify_batch_aggregate(data: dict[str, Any], batch_name: str, computed: dict[str, dict[str, int]], count: int) -> None:
    if batch_name == "batch1":
        aggregate = data["aggregate"]
        assert_field(aggregate["entries_total"], count, f"{batch_name} aggregate total")
        assert_field(aggregate["entries_pass"], count, f"{batch_name} aggregate pass count")
        assert_field(aggregate["entries_fail"], 0, f"{batch_name} aggregate fail count")
        reported = normalize_reported_counts(aggregate["feature_status_counts"])
    elif batch_name == "batch2":
        aggregate = data["aggregate"]
        assert_field(aggregate["entries_reviewed"], count, f"{batch_name} aggregate reviewed count")
        assert_field(aggregate["entries_pass"], count, f"{batch_name} aggregate pass count")
        assert_field(aggregate["entries_fail"], 0, f"{batch_name} aggregate fail count")
        reported = normalize_reported_counts(aggregate["feature_counts"])
    else:
        aggregate = data["aggregate"]
        assert_field(aggregate["record_count"], count, f"{batch_name} aggregate record count")
        assert_field(aggregate["overall_status"], "PASS", f"{batch_name} aggregate status")
        assert_field(aggregate["overall_status_counts"], {"PASS": count}, f"{batch_name} overall counts")
        reported = normalize_reported_counts(aggregate["feature_status_counts"])
        all_counts = {status: 0 for status in FEATURE_STATUSES}
        for feature_counts in computed.values():
            for status in FEATURE_STATUSES:
                all_counts[status] += feature_counts[status]
        assert_field(
            {key: value for key, value in aggregate["all_feature_status_counts"].items() if key in FEATURE_STATUSES},
            {key: value for key, value in all_counts.items() if value},
            f"{batch_name} all feature counts",
        )
    assert_field(reported, computed, f"{batch_name} computed feature counts")
    require(not data.get("issues"), f"{batch_name} has review issues")


def verify_batch2_addendum(
    original_data: dict[str, Any],
    original_raw: bytes,
    context_rows: list[dict[str, Any]],
    module_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    addendum_raw = read_bytes(ADDENDUM_INPUT)
    assert_field(len(addendum_raw), EXPECTED_ADDENDUM_BYTES, "batch 2 addendum byte count")
    assert_field(sha256(addendum_raw), EXPECTED_ADDENDUM_SHA256, "batch 2 addendum SHA-256")
    addendum = read_json(ADDENDUM_INPUT)
    assert_field(addendum["schema_version"], SCHEMA_VERSION, "batch 2 addendum schema")
    assert_field(addendum["protocol"], PROTOCOL, "batch 2 addendum protocol")
    assert_field(addendum["method"], "AI-assisted manual source inspection", "batch 2 addendum method")
    correction = addendum["correction"]
    assert_field(correction["type"], "feature-presence classification", "batch 2 addendum correction type")
    assert_field(correction["feature"], "tails", "batch 2 addendum correction feature")
    assert_field(correction["affected_batch_indices"], [11, 13, 18, 20], "batch 2 addendum indices")
    assert_field(correction["original_status"], "FEATURE_NOT_PRESENT", "batch 2 addendum original status")
    assert_field(correction["revised_status"], "PASS", "batch 2 addendum revised status")
    require(correction["projection_rules_changed"] is False, "batch 2 addendum changed projection rules")
    require(correction["model_or_source_computation_run"] is False, "batch 2 addendum ran an unapproved computation")
    original_report = correction["original_batch_report"]
    assert_field(original_report["path"], "results/celsus-projection-v1/manual-review-batch2.json", "batch 2 addendum original path")
    assert_field(original_report["bytes"], len(original_raw), "batch 2 addendum original byte count")
    assert_field(original_report["sha256"], sha256(original_raw), "batch 2 addendum original SHA-256")
    assert_field(len(original_raw), 34144, "batch 2 original report bytes")
    assert_field(sha256(original_raw), "f81465266f6db30c4be32a7a99bb7e9bba9bba1851f6314c911eb0254b02abf0", "batch 2 original report SHA-256")
    assert_field(addendum["scope"]["affected_entries"], 4, "batch 2 addendum affected count")
    require(addendum["scope"]["raw_paragraph_text_included"] is False, "batch 2 addendum includes raw text")
    assert_field(addendum["status"], "PASS", "batch 2 addendum status")
    assert_field(addendum["aggregate"]["affected_entries_reviewed"], 4, "batch 2 addendum reviewed count")
    assert_field(addendum["aggregate"]["revised_tails"], {"PASS": 4, "FAIL": 0, "FEATURE_NOT_PRESENT": 0}, "batch 2 addendum revised counts")
    assert_field(addendum["aggregate"]["full_batch_tails_after_addendum"], {"PASS": 10, "FAIL": 0, "FEATURE_NOT_PRESENT": 0}, "batch 2 addendum full counts")
    assert_field(addendum["aggregate"]["full_batch_overall_status"], "PASS", "batch 2 addendum full status")
    files = addendum["files"]
    expected_file_pins = {
        "source_xml": ("results/celsus-projection-v1/celsus-lat5.xml", 893899, EXPECTED_SOURCE["sha256"]),
        "manual_context": ("results/celsus-projection-v1/manual-context.jsonl", 183880, "1e5186bcbac24ae86e52aae46dbc249732473752fdeb73908003b8e697ee44f5"),
        "module_paragraphs": ("results/celsus-projection-v1/module-paragraphs.jsonl", 747194, "f37d99f5ad0771c32c4d71934b58df00438ca7dadf870f89dc93b181c1d373f2"),
        "independent_paragraphs": ("results/celsus-projection-v1/independent-paragraphs.jsonl", 747194, "f37d99f5ad0771c32c4d71934b58df00438ca7dadf870f89dc93b181c1d373f2"),
        "manual_checklist_unchanged_input": ("results/celsus-projection-v1/manual-checklist.json", 15401, "32bdec1422e4b80d25139b275b3810bff2f5ffb2818e2c628bebb5f886402aca"),
        "public_receipt_unchanged_input": ("results/celsus-projection-v1/public-receipt.json", 16074, "f9333cdac5f45742f23ffb76b8600421635296fa1b855ab54412f3b94300be91"),
    }
    for key, (expected_path, expected_bytes, expected_hash) in expected_file_pins.items():
        item = files[key]
        assert_field(item["path"], expected_path, f"batch 2 addendum {key} path")
        assert_field(item["bytes"], expected_bytes, f"batch 2 addendum {key} bytes")
        assert_field(item["sha256"], expected_hash, f"batch 2 addendum {key} SHA-256")
        raw = read_bytes(ROOT / expected_path)
        assert_field(len(raw), expected_bytes, f"batch 2 addendum actual {key} bytes")
        assert_field(sha256(raw), expected_hash, f"batch 2 addendum actual {key} SHA-256")
    affected = {11, 13, 18, 20}
    original_by_index = {item["batch_index"]: item for item in original_data["records"]}
    addendum_by_index = {item["batch_index"]: item for item in addendum["records"]}
    assert_field(set(addendum_by_index), affected, "batch 2 addendum record coverage")
    for index in sorted(affected):
        original = original_by_index[index]
        revised = addendum_by_index[index]
        assert_field(original["features"]["tails"]["status"], "FEATURE_NOT_PRESENT", f"batch 2 original tail status {index}")
        assert_field(revised["original_tails_status"], "FEATURE_NOT_PRESENT", f"batch 2 addendum original tail status {index}")
        assert_field(revised["revised_tails_status"], "PASS", f"batch 2 addendum revised tail status {index}")
        assert_field(revised["overall_status"], "PASS", f"batch 2 addendum overall status {index}")
        assert_field(revised["location"], context_rows[index - 1]["location"], f"batch 2 addendum location {index}")
        assert_field(revised["source_subtree"]["tag_counts"], original["source_subtree"]["tag_counts"], f"batch 2 addendum tag counts {index}")
        require(revised["source_subtree"]["module_independent_equal"] is True, f"batch 2 addendum record equality {index}")
        require(revised["source_subtree"]["raw_source_subtree_reviewed_fully"] is True, f"batch 2 addendum raw review {index}")
        source_root = ET.fromstring(context_rows[index - 1]["source_xml"])
        actual_tail_nodes: dict[str, int] = {}
        for node in source_root.iter():
            if node is source_root or not node.tail:
                continue
            tag = node.tag.rsplit("}", 1)[-1]
            actual_tail_nodes[tag] = actual_tail_nodes.get(tag, 0) + 1
        assert_field(actual_tail_nodes, revised["source_subtree"]["nonempty_tail_nodes"], f"batch 2 addendum tail nodes {index}")
    require(not addendum.get("issues"), "batch 2 addendum has issues")
    return {
        "path": "results/celsus-projection-v1/manual-review-batch2-addendum.json",
        "bytes": len(addendum_raw),
        "sha256": sha256(addendum_raw),
        "affected_entries": 4,
        "feature": "tails",
        "original_status": "FEATURE_NOT_PRESENT",
        "revised_status": "PASS",
        "projection_rules_changed": False,
    }


def verify_reviews(
    receipt: dict[str, Any],
    checklist: dict[str, Any],
    context_rows: list[dict[str, Any]],
    module_rows: list[dict[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    checklist_raw = read_bytes(RESULTS / "manual-checklist.json")
    assert_field(len(checklist_raw), receipt["manual_checklist"]["bytes"], "manual checklist byte count")
    assert_field(sha256(checklist_raw), receipt["manual_checklist"]["sha256"], "manual checklist SHA-256")
    assert_field(checklist["protocol"], PROTOCOL, "manual checklist protocol")
    assert_field(checklist["location_count"], 30, "manual checklist location count")
    assert_field(len(checklist["locations"]), 30, "manual checklist locations")
    assert_field(len(checklist["checks"]), 30, "manual checklist checks")
    assert_field(tuple(checklist["feature_names"]), FEATURES, "manual checklist features")
    assert_field(checklist["manual_acceptance"], "PENDING", "manual checklist initial status")
    require(set(checklist["allowed_feature_statuses"]) == {"PASS", "FAIL", "NOT_PRESENT"}, "manual checklist status set changed")
    assert_field([check["location"] for check in checklist["checks"]], checklist["locations"], "manual checklist location order")
    assert_field([row["location"] for row in context_rows], checklist["locations"], "manual context and checklist locations")
    review_files = ("manual-review-batch1.json", "manual-review-batch2.json", "manual-review-batch3.json")
    batch_raw = [read_bytes(RESULTS / name) for name in review_files]
    batch_data = [read_json(RESULTS / name) for name in review_files]
    all_items: list[dict[str, Any]] = []
    batch_summaries: list[dict[str, Any]] = []
    total_counts = counts_template()
    addendum_summary: dict[str, Any] | None = None
    module_by_key = {record_key(row): row for row in module_rows}
    for batch_name, data in zip(("batch1", "batch2", "batch3"), batch_data):
        assert_field(data["schema_version"], SCHEMA_VERSION, f"{batch_name} schema")
        assert_field(data["protocol"], PROTOCOL, f"{batch_name} protocol")
        assert_field(data["method"], "AI-assisted manual source inspection", f"{batch_name} method")
        if batch_name == "batch1":
            items = data["entries"]
            expected_indices = list(range(1, 11))
            assert_field(data["status"], "PASS", f"{batch_name} status")
        elif batch_name == "batch2":
            items = data["records"]
            expected_indices = list(range(11, 21))
            assert_field(data["status"], "PASS", f"{batch_name} status")
            assert_field(data["overall_status"], "PASS", f"{batch_name} overall status")
            assert_field(data["scope"]["manual_review_type"], "AI-assisted manual source inspection, not human or external validation", f"{batch_name} review type")
            require(data["scope"]["raw_paragraph_text_included"] is False, f"{batch_name} raw text flag changed")
        else:
            items = data["reviews"]
            expected_indices = list(range(21, 31))
            assert_field(data["aggregate"]["overall_status"], "PASS", f"{batch_name} overall status")
            pending = data["preserved_pending_files"]
            for filename, expected in (
                ("public-receipt.json", receipt["status"] if "status" in receipt else None),
                ("manual-checklist.json", checklist["manual_acceptance"]),
            ):
                item = pending[filename]
                raw = read_bytes(RESULTS / filename)
                assert_field(item["bytes"], len(raw), f"{batch_name} preserved {filename} bytes")
                assert_field(item["sha256"], sha256(raw), f"{batch_name} preserved {filename} SHA-256")
            assert_field(pending["public-receipt.json"]["status"], "PENDING_MANUAL_REVIEW", f"{batch_name} preserved receipt status")
            assert_field(pending["public-receipt.json"]["manual_acceptance"], "PENDING", f"{batch_name} preserved receipt acceptance")
            assert_field(pending["manual-checklist.json"]["manual_acceptance"], "PENDING", f"{batch_name} preserved checklist acceptance")
        assert_field([review_index(item, batch_name) for item in items], expected_indices, f"{batch_name} indices")
        computed = counts_template()
        for item in items:
            index = review_index(item, batch_name)
            require(1 <= index <= 30, f"{batch_name} index out of range")
            location = item["location"]
            assert_field(location, context_rows[index - 1]["location"], f"{batch_name} location {index}")
            assert_field(item["overall_status"], "PASS", f"{batch_name} overall status {index}")
            feature_map = item["features"]
            assert_field(set(feature_map.keys()), set(FEATURES), f"{batch_name} feature set {index}")
            for feature in FEATURES:
                feature_value = feature_map[feature]
                require(isinstance(feature_value, dict), f"{batch_name} feature is not an object: {feature} {index}")
                status = feature_value.get("status")
                require(status in ("PASS", "FEATURE_NOT_PRESENT"), f"{batch_name} feature status is not accepted: {feature} {index}")
                computed[feature][status] += 1
                total_counts[feature][status] += 1
            source_hash, source_bytes = review_source_hash(item, batch_name)
            context_source = context_rows[index - 1]["source_xml"]
            assert_field(source_hash, sha256(context_source.encode("utf-8")), f"{batch_name} source hash {index}")
            assert_field(source_bytes, len(context_source.encode("utf-8")), f"{batch_name} source bytes {index}")
            module_hash, independent_hash = review_record_hashes(item, batch_name)
            record_key_for_location = (
                location["book_id"],
                location["chapter_id"],
                location["chapter_key"],
                location["local_paragraph_ordinal"],
            )
            require(record_key_for_location in module_by_key, f"{batch_name} projected record location {index}")
            record = module_by_key[record_key_for_location]
            expected_record_hash = record_hash(record)
            expected_text_hash = text_hash(record)
            expected_review_hash = expected_text_hash if batch_name == "batch3" else expected_record_hash
            assert_field(module_hash, expected_review_hash, f"{batch_name} module record hash {index}")
            assert_field(independent_hash, expected_review_hash, f"{batch_name} independent record hash {index}")
            if batch_name == "batch1":
                text_hashes = item["text_sha256"]
                for field in ("independent_projection", "independent_record", "module_record"):
                    assert_field(text_hashes[field], expected_text_hash, f"{batch_name} text hash {field} {index}")
                require(item["source_resolution"]["matches_pinned_body_ordinal"] is True, f"{batch_name} source ordinal {index}")
                require(item["source_resolution"]["source_xml_matches_pinned_subtree"] is True, f"{batch_name} source XML {index}")
            elif batch_name == "batch2":
                subtree = item["source_subtree"]
                require(subtree["parsed_equal_to_pinned_source"] is True, f"{batch_name} parsed source {index}")
                require(subtree["global_source_paragraph_ordinal_matches"] is True, f"{batch_name} source ordinal {index}")
                require(item["records"]["module_independent_equal"] is True, f"{batch_name} record equality {index}")
                assert_field(item["records"]["retained_character_count"], len(record["text"]), f"{batch_name} retained characters {index}")
            else:
                counts = item["counts"]
                assert_field(counts["module_text_bytes"], len(record["text"].encode("utf-8")), f"{batch_name} module text bytes {index}")
                assert_field(counts["independent_text_bytes"], len(record["text"].encode("utf-8")), f"{batch_name} independent text bytes {index}")
                assert_field(counts["projected_text_bytes"], len(record["text"].encode("utf-8")), f"{batch_name} projected text bytes {index}")
        verify_batch_aggregate(data, batch_name, computed, len(items))
        if batch_name == "batch2":
            addendum_summary = verify_batch2_addendum(data, batch_raw[1], context_rows, module_rows)
            computed["tails"]["FEATURE_NOT_PRESENT"] -= addendum_summary["affected_entries"]
            computed["tails"]["PASS"] += addendum_summary["affected_entries"]
            total_counts["tails"]["FEATURE_NOT_PRESENT"] -= addendum_summary["affected_entries"]
            total_counts["tails"]["PASS"] += addendum_summary["affected_entries"]
            assert_field(
                computed["tails"],
                {"PASS": 10, "FEATURE_NOT_PRESENT": 0, "FAIL": 0},
                "batch 2 corrected tail counts",
            )
        batch_summaries.append({
            "name": batch_name,
            "first_index": expected_indices[0],
            "last_index": expected_indices[-1],
            "record_count": len(items),
            "status": "PASS",
            "method": data["method"],
            "manual_review_type": data.get("scope", {}).get("manual_review_type"),
            "path": f"results/celsus-projection-v1/manual-review-{batch_name}.json",
            "bytes": len(batch_raw[int(batch_name[-1]) - 1]),
            "sha256": sha256(batch_raw[int(batch_name[-1]) - 1]),
            "feature_status_counts": computed,
        })
        all_items.extend(items)
    assert_field(len(all_items), 30, "review record count")
    assert_field(sorted(review_index(item, "batch1") for item in batch_data[0]["entries"]), list(range(1, 11)), "batch1 coverage")
    assert_field(sum(total_counts[feature]["PASS"] + total_counts[feature]["FEATURE_NOT_PRESENT"] for feature in FEATURES), 240, "total feature review count")
    require(all(counts["FAIL"] == 0 for counts in total_counts.values()), "a review feature has FAIL")
    require(all(item["overall_status"] == "PASS" for item in all_items), "a review record does not pass")
    return {
        "locations_reviewed": len(all_items),
        "features_per_location": len(FEATURES),
        "overall_status_counts": {"PASS": len(all_items)},
        "feature_status_counts": total_counts,
        "fail_count": sum(counts["FAIL"] for counts in total_counts.values()),
        "batches": batch_summaries,
        "addendum": addendum_summary,
        "review_method": "AI-assisted manual source inspection",
        "human_or_external_validation_claim": False,
    }, all_items


def verify_replay(receipt: dict[str, Any], module_raw: bytes, context_raw: bytes) -> tuple[dict[str, Any], bytes]:
    replay_raw = read_bytes(REPLAY_INPUT)
    replay = read_json(REPLAY_INPUT)
    assert_field(replay["schema_version"], SCHEMA_VERSION, "replay schema")
    assert_field(replay["verification"], "celsus-projection-public-replay", "replay verification")
    checkout = replay["checkout"]
    assert_field(checkout["commit"], FROZEN_COMMIT, "replay checkout commit")
    require(checkout["detached"] is True, "replay checkout is not detached")
    require(checkout["tracked_clean_before"] is True, "replay checkout was not clean before run")
    require(checkout["tracked_clean_after"] is True, "replay checkout was not clean after run")
    assert_field(replay["command"], "python -m experiments.medical.run_projection --output-dir results/celsus-projection-v1", "replay command")
    run = replay["run"]
    assert_field(run["exit_status"], 0, "replay exit status")
    assert_field(run["source_bytes"], EXPECTED_SOURCE["bytes"], "replay source bytes")
    assert_field(run["source_sha256"], EXPECTED_SOURCE["sha256"], "replay source SHA-256")
    assert_field(run["module_record_count"], 550, "replay module count")
    assert_field(run["independent_record_count"], 550, "replay independent count")
    assert_field(run["validation_scope"], "pinned_source", "replay validation scope")
    assert_field(run["validation_status"], "PENDING_MANUAL_REVIEW", "replay validation status")
    assert_field(run["manual_acceptance"], "PENDING", "replay manual acceptance")
    require(run["public_stdout_contains_full_text"] is False, "replay stdout contains full text")
    assert_field(run["stdout_bytes"], len(read_bytes(RESULTS / "public-receipt.json")), "replay stdout bytes")
    assert_field(run["stdout_sha256"], sha256(read_bytes(RESULTS / "public-receipt.json")), "replay stdout SHA-256")
    assert_field(run["stderr_bytes"], 0, "replay stderr bytes")
    output_map = {
        "results/celsus-projection-v1/public-receipt.json": read_bytes(RESULTS / "public-receipt.json"),
        "results/celsus-projection-v1/module-paragraphs.jsonl": module_raw,
        "results/celsus-projection-v1/independent-paragraphs.jsonl": module_raw,
        "results/celsus-projection-v1/manual-checklist.json": read_bytes(RESULTS / "manual-checklist.json"),
        "results/celsus-projection-v1/manual-context.jsonl": context_raw,
    }
    outputs = replay["outputs"]
    assert_field([item["path"] for item in outputs], list(EXPECTED_OUTPUT_PATHS), "replay output paths")
    public_outputs: list[dict[str, Any]] = []
    for item in outputs:
        path = item["path"]
        raw = output_map[path]
        expected_hash = sha256(raw)
        expected_bytes = len(raw)
        require(item["byte_equal"] is True, f"replay output differs: {path}")
        assert_field(item["primary_bytes"], expected_bytes, f"replay primary bytes {path}")
        assert_field(item["replay_bytes"], expected_bytes, f"replay replay bytes {path}")
        assert_field(item["primary_sha256"], expected_hash, f"replay primary SHA-256 {path}")
        assert_field(item["replay_sha256"], expected_hash, f"replay replay SHA-256 {path}")
        public_outputs.append({
            "path": path,
            "bytes": expected_bytes,
            "sha256": expected_hash,
            "byte_equal": True,
        })
    public = {
        "schema_version": SCHEMA_VERSION,
        "verification": "celsus-projection-public-replay",
        "input": {
            "path": "results/celsus-projection-v1-replay-verification.json",
            "bytes": len(replay_raw),
            "sha256": sha256(replay_raw),
        },
        "checkout": {
            "commit": checkout["commit"],
            "detached": True,
            "tracked_clean_before": True,
            "tracked_clean_after": True,
        },
        "command": replay["command"],
        "run": {
            "exit_status": 0,
            "source_bytes": run["source_bytes"],
            "source_sha256": run["source_sha256"],
            "module_record_count": run["module_record_count"],
            "independent_record_count": run["independent_record_count"],
            "validation_scope": run["validation_scope"],
            "validation_status": run["validation_status"],
            "manual_acceptance": run["manual_acceptance"],
            "public_stdout_contains_full_text": False,
            "stdout_bytes": run["stdout_bytes"],
            "stdout_sha256": run["stdout_sha256"],
            "stderr_bytes": run["stderr_bytes"],
        },
        "outputs": public_outputs,
        "resource_fields": "omitted from this public receipt",
    }
    return public, pretty_json(public)


def build_acceptance(
    receipt: dict[str, Any],
    structure: dict[str, Any],
    projection: dict[str, Any],
    review: dict[str, Any],
    replay_public: dict[str, Any],
    initial_receipt_raw: bytes,
    manual_checklist_raw: bytes,
    context_raw: bytes,
) -> dict[str, Any]:
    initial_receipt_sha = sha256(initial_receipt_raw)
    module_raw = read_bytes(RESULTS / "module-paragraphs.jsonl")
    independent_raw = read_bytes(RESULTS / "independent-paragraphs.jsonl")
    acceptance = {
        "schema_version": SCHEMA_VERSION,
        "protocol": PROTOCOL,
        "status": "COMPLETE",
        "result": "PASS",
        "manual_acceptance": "ACCEPTED",
        "initial_receipt": {
            "path": "reports/celsus-projection-v1/initial-receipt.json",
            "source_path": "results/celsus-projection-v1/public-receipt.json",
            "bytes": len(initial_receipt_raw),
            "sha256": initial_receipt_sha,
            "source_status": receipt["status"],
            "source_manual_acceptance": receipt["manual_acceptance"],
            "byte_exact_copy": True,
        },
        "source": {
            "repository": EXPECTED_SOURCE["repository"],
            "commit": EXPECTED_SOURCE["commit"],
            "url": EXPECTED_SOURCE["url"],
            "bytes": EXPECTED_SOURCE["bytes"],
            "sha256": EXPECTED_SOURCE["sha256"],
            "audit_revision": EXPECTED_SOURCE["audit_revision"],
            "audit_receipt_sha256": EXPECTED_SOURCE["audit_receipt_sha256"],
        },
        "freeze": {
            "commit": FROZEN_COMMIT,
            "first_projection_ci_cutoff_utc": FIRST_PROJECTION_CI_CUTOFF,
            "ci_run_url": CI_RUN_URL,
            "manifest_path": receipt["freeze"]["manifest_path"],
            "manifest_sha256": receipt["freeze"]["manifest_sha256"],
            "files": receipt["freeze"]["files"],
        },
        "structure": {
            "book_count": structure["book_count"],
            "chapter_count": structure["chapter_count"],
            "paragraph_count": structure["paragraph_count"],
            "book_ids": list(EXPECTED_BOOKS),
            "chapters_by_book": structure["chapters_by_book"],
            "paragraphs_by_book": structure["paragraphs_by_book"],
            "source_counts": receipt["structure"]["source_counts"],
            "selected_subtree_counts": receipt["structure"]["selected_subtree_counts"],
        },
        "projection": {
            "empty_policy": "include",
            "module": {
                "path": "results/celsus-projection-v1/module-paragraphs.jsonl",
                "records": projection["record_count"],
                "bytes": len(module_raw),
                "sha256": sha256(module_raw),
            },
            "independent": {
                "path": "results/celsus-projection-v1/independent-paragraphs.jsonl",
                "records": projection["record_count"],
                "bytes": len(independent_raw),
                "sha256": sha256(independent_raw),
            },
            "records_equal": True,
            "reports_equal": True,
            "projected_paragraph_count": projection["record_count"],
            "projected_chapter_count": projection["projected_chapter_count"],
            "projected_paragraphs_by_book": projection["projected_paragraphs_by_book"],
            "empty_projected_paragraph_count": projection["empty_projected_paragraph_count"],
            "dropped_empty_paragraph_count": projection["dropped_empty_paragraph_count"],
            "boundary_validation": projection["boundary_validation"],
            "actual_retained": projection["actual_retained"],
            "direct_excluded": projection["direct_excluded"],
            "ancestor_excluded": projection["ancestor_excluded"],
        },
        "manual_review": {
            "locations_reviewed": review["locations_reviewed"],
            "features_per_location": review["features_per_location"],
            "overall_status_counts": review["overall_status_counts"],
            "feature_status_counts": review["feature_status_counts"],
            "fail_count": review["fail_count"],
            "batches": review["batches"],
            "addendum": review["addendum"],
            "review_method": review["review_method"],
            "human_or_external_validation_claim": review["human_or_external_validation_claim"],
            "empty_status_convention": {
                "batch1_and_batch3": "FEATURE_NOT_PRESENT for non-empty entries",
                "batch2": "PASS for the non-empty include-policy check",
                "preserved": True,
            },
            "tails_addendum_scope": "The batch 2 addendum changes four tail presence labels from FEATURE_NOT_PRESENT to PASS after full subtree checks. It changes no projection rule.",
        },
        "replay": {
            "path": "reports/celsus-projection-v1/replay-verification.json",
            "bytes": len(pretty_json(replay_public)),
            "sha256": sha256(pretty_json(replay_public)),
            "input": replay_public["input"],
            "checkout_commit": replay_public["checkout"]["commit"],
            "exit_status": replay_public["run"]["exit_status"],
            "all_outputs_byte_equal": all(item["byte_equal"] for item in replay_public["outputs"]),
        },
        "input_artifacts": {
            "manual_checklist": {
                "path": "results/celsus-projection-v1/manual-checklist.json",
                "bytes": len(manual_checklist_raw),
                "sha256": sha256(manual_checklist_raw),
                "source_manual_acceptance": "PENDING",
            },
            "manual_context": {
                "path": "results/celsus-projection-v1/manual-context.jsonl",
                "records": 30,
                "bytes": len(context_raw),
                "sha256": sha256(context_raw),
            },
        },
        "checks": {
            "source_pinned": True,
            "source_structure": True,
            "freeze_manifest_pinned": True,
            "module_independent_records_equal": True,
            "module_independent_reports_equal": True,
            "context_locations_and_hashes_match": True,
            "all_review_locations_covered_once": True,
            "all_review_overall_statuses_pass": True,
            "no_review_feature_failures": True,
            "replay_byte_equal": True,
            "public_output_has_no_raw_paragraphs": True,
        },
    }
    return acceptance


def build_report(acceptance: dict[str, Any], acceptance_sha: str) -> str:
    structure = acceptance["structure"]
    projection = acceptance["projection"]
    review = acceptance["manual_review"]
    source = acceptance["source"]
    feature_counts = review["feature_status_counts"]
    lines = [
        "# Celsus projection result",
        "",
        "The frozen Celsus projection completed with `PASS`.",
        "The two independent traversals produced the same 550 paragraph records.",
        "This result validates a fixed extraction procedure.",
        "It does not identify the language of the Voynich manuscript.",
        "",
        "The source is an ancient Latin medical edition of Celsus.",
        "It is a control for extraction work.",
        "Its date, genre, and editorial history differ from the Voynich manuscript.",
        "The result does not provide a translation or a decipherment.",
        "",
        "## Source and freeze",
        "",
        f"The source file has {source['bytes']:,} bytes and SHA-256 `{source['sha256']}`.",
        f"The source uses commit `{source['commit']}` in the [canonical-latinLit repository]({source['repository']}).",
        f"The source is available as the [pinned TEI source]({source['url']}).",
        f"The source audit revision is `{source['audit_revision']}`.",
        f"The audit receipt SHA-256 is `{source['audit_receipt_sha256']}`.",
        "See the [source audit](celsus-source-audit.json) for edition and rights evidence.",
        "",
        f"The frozen code commit is `{acceptance['freeze']['commit']}`.",
        f"It was published before the first projection. CI passed before {acceptance['freeze']['first_projection_ci_cutoff_utc']}.",
        f"See the [CI run]({acceptance['freeze']['ci_run_url']}).",
        f"The freeze manifest SHA-256 is `{acceptance['freeze']['manifest_sha256']}`.",
        "The [frozen protocol](../docs/plans/celsus-projection-v1.md) defines the source rules and stop conditions.",
        "",
        "The [initial receipt](celsus-projection-v1/initial-receipt.json) is a byte-exact copy of the pending run receipt.",
        "The [acceptance receipt](celsus-projection-v1/acceptance.json) records the final review result.",
        "The two receipts stay separate.",
        "",
        "## Structure",
        "",
        f"The source has {structure['book_count']} books, {structure['chapter_count']} chapters, and {structure['paragraph_count']} paragraphs.",
        "The run includes one Latin edition wrapper.",
        "It has no empty source paragraphs.",
        "",
        "| Book | Chapters | Paragraphs |",
        "| ---: | ---: | ---: |",
    ]
    for book_id in structure["book_ids"]:
        lines.append(f"| {book_id} | {structure['chapters_by_book'][book_id]} | {structure['paragraphs_by_book'][book_id]} |")
    lines.extend(
        [
            "",
            "The paragraph counts use direct chapter paragraph order.",
            "The public receipts publish counts and hashes.",
            "They do not publish paragraph text or individual review entries.",
            "",
            "## Projection",
            "",
            "The run uses `empty_policy=include`.",
            f"It emits {projection['projected_paragraph_count']} records across {projection['projected_chapter_count']} chapters.",
            f"It emits {projection['empty_projected_paragraph_count']} empty records and drops {projection['dropped_empty_paragraph_count']} empty records.",
            "The module and independent files have the same bytes and SHA-256.",
            "",
            "| Output | Records | Bytes | SHA-256 |",
            "| --- | ---: | ---: | --- |",
            f"| Module traversal | {projection['module']['records']:,} | {projection['module']['bytes']:,} | `{projection['module']['sha256']}` |",
            f"| Independent traversal | {projection['independent']['records']:,} | {projection['independent']['bytes']:,} | `{projection['independent']['sha256']}` |",
            "",
            f"The pending initial receipt has SHA-256 `{acceptance['initial_receipt']['sha256']}`.",
            f"The fixed review checklist has SHA-256 `{acceptance['input_artifacts']['manual_checklist']['sha256']}`.",
            f"The private review context has SHA-256 `{acceptance['input_artifacts']['manual_context']['sha256']}`.",
            "The public receipts publish these hashes without the review context text.",
            "",
            "The projector keeps `corr` content and excludes `sic`, `head`, `note`, `del`, `figure`, and `foreign` content.",
            "It keeps the tail of each excluded root at the parent level.",
            "It treats `pb` and `milestone` as transparent.",
            "It collapses XML whitespace after traversal.",
            "The independent traversal applies the same fixed rules.",
            "",
            "The following counters have separate scopes.",
            "Selected subtree counts include nodes that an ancestor can later exclude.",
            "Actual retained counts record the final traversal.",
            "Direct excluded counts record roots excluded at their parent.",
            "Ancestor excluded counts record nodes below an excluded ancestor.",
            "These scopes must not be subtracted as one table.",
            "",
            "| Scope | Choice | Corr | Hi | Milestone | Paragraph | Page break | Sic | Del | Foreign | Note |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
            f"| Selected subtree | {structure['selected_subtree_counts']['choice']} | {structure['selected_subtree_counts']['corr']} | {structure['selected_subtree_counts']['hi']} | {structure['selected_subtree_counts']['milestone']} | {structure['selected_subtree_counts']['p']} | {structure['selected_subtree_counts']['pb']} | {structure['selected_subtree_counts']['sic']} | {structure['selected_subtree_counts']['del']} | {structure['selected_subtree_counts']['foreign']} | {structure['selected_subtree_counts']['note']} |",
            f"| Actual retained | {projection['actual_retained'].get('choice', 0)} | {projection['actual_retained'].get('corr', 0)} | {projection['actual_retained'].get('hi', 0)} | {projection['actual_retained'].get('milestone', 0)} | {projection['actual_retained'].get('p', 0)} | {projection['actual_retained'].get('pb', 0)} | — | — | — | — |",
            f"| Direct excluded roots | — | — | — | — | — | — | {projection['direct_excluded'].get('sic', 0)} | {projection['direct_excluded'].get('del', 0)} | {projection['direct_excluded'].get('foreign', 0)} | {projection['direct_excluded'].get('note', 0)} |",
            "",
            "Ancestor exclusion counts by tag are `figure=4`, `foreign=8`, `head=4`, `hi=505`, `milestone=4`, `note=1`, and `pb=1`.",
            "The eight nested foreign nodes are below notes.",
            "The direct foreign count is 268.",
            "",
            "## Fixed review records",
            "",
            f"The review artifacts cover {review['locations_reviewed']} fixed locations.",
            f"Each location checks {review['features_per_location']} features.",
            "All overall statuses are `PASS`.",
            f"No feature has `FAIL` ({review['fail_count']} failures).",
            "",
            "| Feature | PASS | FEATURE_NOT_PRESENT | FAIL |",
            "| --- | ---: | ---: | ---: |",
        ]
    )
    for feature in FEATURES:
        counts = feature_counts[feature]
        lines.append(f"| `{feature}` | {counts['PASS']} | {counts['FEATURE_NOT_PRESENT']} | {counts['FAIL']} |")
    lines.extend(
        [
            "",
            "All three review files identify the method as AI-assisted manual source inspection.",
            "These records are not human or external validation.",
            "The report makes no human-review claim.",
            "",
            "A batch 2 addendum corrected four tail presence labels after full subtree checks.",
            "The addendum changed no projection rule.",
            "The final `tails` row records 30 `PASS` values and zero `FEATURE_NOT_PRESENT` values.",
            "The original batch 2 report remains unchanged.",
            "",
            "The `empty_status` counts preserve the reviewer convention.",
            "Batch 1 and batch 3 mark non-empty entries `FEATURE_NOT_PRESENT`.",
            "Batch 2 marks the same non-empty include-policy check `PASS`.",
            "The aggregate keeps both values.",
            "",
            "The addendum found parent-order tails after transparent markers and choices in the four affected records.",
            "The builder checks the addendum hash, locations, source subtree tail nodes, and unchanged projection files.",
            "",
            "## Replay",
            "",
            "The replay exited with status 0.",
            "It reproduced the five frozen result files byte for byte.",
            f"The replay used detached commit `{acceptance['replay']['checkout_commit']}`.",
            f"The original replay receipt has SHA-256 `{acceptance['replay']['input']['sha256']}`.",
            "The public replay receipt omits process resource fields.",
            f"See [replay verification](celsus-projection-v1/replay-verification.json) (SHA-256 `{acceptance['replay']['sha256']}`).",
            "",
            "## Limits",
            "",
            "This run validates a source projection and an independent comparison.",
            "It does not test a Voynich transcription, a cipher key, or a translation.",
            "The Celsus text is an ancient medical control.",
            "It cannot remove date, genre, edition, or orthography differences between corpora.",
            "",
            "The 30 fixed review records do not inspect all 550 paragraphs.",
            "AI-assisted inspection does not replace independent human review.",
            "The public result publishes no raw source or paragraph context.",
            "",
            "## Rebuild",
            "",
            "Run the builder from the repository root:",
            "",
            "```text",
            "python scripts/build_celsus_projection_summary.py",
            "```",
            "The builder checks all pinned inputs before it writes an output.",
            "An identical existing output is accepted.",
            "A changed existing output stops the build.",
            "The automated projection is publicly reproducible from the frozen source and code.",
            "The manual review artifacts are private and cannot be derived by this command.",
            "The builder requires the retained review files.",
            "Their hashes identify the reviewed evidence.",
            f"The acceptance receipt hash is `{acceptance_sha}`.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    try:
        pinned_inputs = pin_inputs()
        initial_receipt_raw = pinned_inputs["results/celsus-projection-v1/public-receipt.json"]
        receipt = read_json(RESULTS / "public-receipt.json")
        source_raw, source_paragraphs, source_structure = load_source(receipt)
        verify_receipt(receipt, source_structure)
        module_rows, independent_rows, projection = verify_projection(receipt, source_paragraphs)
        context_raw, context_rows = verify_context(receipt, source_paragraphs, module_rows)
        checklist = read_json(RESULTS / "manual-checklist.json")
        review, _review_items = verify_reviews(receipt, checklist, context_rows, module_rows)
        replay_public, replay_bytes = verify_replay(receipt, module_raw=read_bytes(RESULTS / "module-paragraphs.jsonl"), context_raw=context_raw)
        acceptance = build_acceptance(
            receipt,
            source_structure,
            projection,
            review,
            replay_public,
            initial_receipt_raw,
            read_bytes(RESULTS / "manual-checklist.json"),
            context_raw,
        )
        acceptance_bytes = pretty_json(acceptance)
        report = build_report(acceptance, sha256(acceptance_bytes))
        report_bytes = report.encode("utf-8")
        outputs = (
            (PUBLIC_DIR / "initial-receipt.json", initial_receipt_raw),
            (PUBLIC_DIR / "acceptance.json", acceptance_bytes),
            (PUBLIC_DIR / "replay-verification.json", replay_bytes),
            (REPORTS / "CELSUS_PROJECTION.md", report_bytes),
        )
        for path, payload in outputs:
            write_identical(path, payload)
        # Confirm the initial public receipt remained byte exact after the write.
        assert_field(read_bytes(PUBLIC_DIR / "initial-receipt.json"), initial_receipt_raw, "initial receipt copy")
        print("Celsus public summary built and validated.")
        print(f"  source: {sha256(source_raw)}")
        print(f"  acceptance: {sha256(acceptance_bytes)}")
        print(f"  replay receipt: {sha256(replay_bytes)}")
        print(f"  report: {sha256(report_bytes)}")
        return 0
    except BuildError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
