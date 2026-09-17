"""Run the fixed Celsus projection validation.

The runner verifies the pinned source, runs the reviewed projector, and runs
an independent XML traversal. Full paragraph output stays in ignored files.
The public receipt contains aggregate counts, hashes, and failure status only.
"""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
import unicodedata
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from typing import Iterable


PROTOCOL = "celsus-projection-v1"
SOURCE_REVIEW_DATE = "2026-09-17"
AUDIT_REVISION = "f26874c"
AUDIT_RECEIPT_SHA256 = (
    "aebba00a41c120e4101d94c67f4783e9de55106051d158f3ccd41246d960e6de"
)
SOURCE_REPOSITORY = "https://github.com/PerseusDL/canonical-latinLit"
SOURCE_COMMIT = "ae0fe427f56d7652efc3090af74a2663a4cbed60"
SOURCE_URL = (
    "https://raw.githubusercontent.com/PerseusDL/canonical-latinLit/"
    f"{SOURCE_COMMIT}/data/phi0836/phi002/"
    "phi0836.phi002.perseus-lat5.xml"
)
SOURCE_FILENAME = "celsus-lat5.xml"
SOURCE_BYTES = 893899
SOURCE_SHA256 = "a4a5194ba38a7efd5192d20f2a7b696f4fa64105010eb629aa7c35255a935145"
AUDIT_RECEIPT_DEFAULT = Path("reports/celsus-source-audit.json")
DEFAULT_OUTPUT_DIR = Path("results/celsus-projection-v1")
FREEZE_MANIFEST_PATH = Path("experiments/medical/freeze-v1.json")
FREEZE_FILES = (
    Path("docs/plans/celsus-projection-v1.md"),
    Path("experiments/medical/tei_projection.py"),
    Path("experiments/medical/run_projection.py"),
    Path("experiments/medical/test_tei_projection.py"),
    Path("experiments/medical/test_run_projection.py"),
)
REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
IMPLEMENTATION_FILES = {
    "protocol": Path("docs/plans/celsus-projection-v1.md"),
    "projector": Path("experiments/medical/tei_projection.py"),
    "runner": Path("experiments/medical/run_projection.py"),
}
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}\Z")

TEI_NS = "http://www.tei-c.org/ns/1.0"
XML_NS = "http://www.w3.org/XML/1998/namespace"
XML_WHITESPACE = " \t\r\n"
XML_WHITESPACE_TRANSLATION = str.maketrans({"\t": " ", "\r": " ", "\n": " "})
ALLOWED_BODY_TAGS = frozenset(
    {
        "body",
        "choice",
        "corr",
        "del",
        "div",
        "figure",
        "foreign",
        "head",
        "hi",
        "milestone",
        "note",
        "p",
        "pb",
        "sic",
    }
)
EXCLUDED_TAGS = frozenset({"del", "figure", "foreign", "head", "note"})
EXCLUDED_ANCESTOR_TAGS = EXCLUDED_TAGS | {"sic"}
STRUCTURE_FORBIDDEN_ANCESTORS = EXCLUDED_TAGS | {"choice", "sic"}

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
    "choice": 446,
    "foreign": 276,
    "note": 628,
    "del": 10,
    "add": 0,
}
EXPECTED_SELECTED_COUNTS = {
    "choice": 446,
    "foreign": 276,
    "note": 626,
    "del": 7,
    "head": 4,
    "pb": 308,
    "milestone": 1804,
    "figure": 4,
    "hi": 525,
}
MANUAL_FEATURES = (
    "location_fields",
    "source_spelling",
    "xml_whitespace",
    "choice_correction",
    "excluded_content",
    "tails",
    "transparent_markers",
    "empty_status",
)


class RunnerFailure(ValueError):
    """A source-bound failure with no source text in its public form."""

    def __init__(
        self,
        kind: str,
        message: str,
        *,
        location: dict[str, object] | None = None,
        details: object | None = None,
    ) -> None:
        super().__init__(message)
        self.kind = kind
        self.message = message
        self.location = location
        self.details = details


@dataclass(frozen=True)
class ValidatedDocument:
    """Validated XML state used by both traversals."""

    root: ET.Element
    body: ET.Element
    parents: dict[ET.Element, ET.Element]
    paragraphs: tuple[ET.Element, ...]
    locations: tuple[dict[str, object], ...]
    report: dict[str, object]


@dataclass(frozen=True)
class TraversalResult:
    """Paragraph records and aggregate counters from one traversal."""

    records: tuple[dict[str, object], ...]
    report: dict[str, object]


def _qname(local_name: str) -> str:
    return f"{{{TEI_NS}}}{local_name}"


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _canonical_json_bytes(value: object) -> bytes:
    return (_canonical_json(value) + "\n").encode("utf-8")


def _jsonl_bytes(records: Iterable[dict[str, object]]) -> bytes:
    return b"".join(_canonical_json_bytes(record) for record in records)


def _implementation_pins() -> dict[str, dict[str, object]]:
    """Return repository-relative hashes for the frozen implementation files."""

    pins: dict[str, dict[str, object]] = {}
    for name, relative_path in IMPLEMENTATION_FILES.items():
        entry: dict[str, object] = {"path": relative_path.as_posix()}
        try:
            data = (REPOSITORY_ROOT / relative_path).read_bytes()
        except OSError:
            entry["available"] = False
        else:
            entry["available"] = True
            entry["sha256"] = _sha256(data)
        pins[name] = entry
    return pins


def _verify_freeze_manifest(
    manifest_bytes: bytes,
    *,
    repository_root: Path = REPOSITORY_ROOT,
) -> dict[str, object]:
    """Verify the external five-file freeze manifest before projection."""

    try:
        manifest = json.loads(manifest_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RunnerFailure("freeze_manifest_json", "freeze manifest is not valid JSON") from error
    if not isinstance(manifest, dict):
        raise RunnerFailure("freeze_manifest_json", "freeze manifest is not an object")
    if set(manifest) != {"schema_version", "protocol", "files"}:
        raise RunnerFailure("freeze_manifest_schema", "freeze manifest fields do not match")
    if manifest.get("schema_version") != 1 or manifest.get("protocol") != PROTOCOL:
        raise RunnerFailure("freeze_manifest_schema", "freeze manifest identity does not match")
    files = manifest.get("files")
    if not isinstance(files, list) or len(files) != len(FREEZE_FILES):
        raise RunnerFailure("freeze_manifest_files", "freeze manifest file list does not match")
    expected_paths = {path.as_posix() for path in FREEZE_FILES}
    entries: dict[str, str] = {}
    for item in files:
        if not isinstance(item, dict) or set(item) != {"path", "sha256"}:
            raise RunnerFailure("freeze_manifest_files", "freeze manifest entry fields do not match")
        path = item.get("path")
        digest = item.get("sha256")
        if (
            not isinstance(path, str)
            or path not in expected_paths
            or path in entries
            or not isinstance(digest, str)
            or SHA256_PATTERN.fullmatch(digest) is None
        ):
            raise RunnerFailure("freeze_manifest_files", "freeze manifest path or hash is invalid")
        entries[path] = digest
    if set(entries) != expected_paths:
        raise RunnerFailure("freeze_manifest_files", "freeze manifest path set does not match")
    for relative_path in FREEZE_FILES:
        path = repository_root / relative_path
        try:
            actual = _sha256(path.read_bytes())
        except OSError as error:
            raise RunnerFailure("freeze_file_missing", "frozen file is unavailable") from error
        if actual != entries[relative_path.as_posix()]:
            raise RunnerFailure("freeze_hash_mismatch", "frozen file hash does not match")
    return {
        "manifest_path": FREEZE_MANIFEST_PATH.as_posix(),
        "manifest_sha256": _sha256(manifest_bytes),
        "schema_version": 1,
        "protocol": PROTOCOL,
        "files": [
            {"path": path.as_posix(), "sha256": entries[path.as_posix()]}
            for path in FREEZE_FILES
        ],
    }


def _load_freeze_manifest(path: Path = FREEZE_MANIFEST_PATH) -> dict[str, object]:
    try:
        manifest_bytes = path.read_bytes()
    except OSError as error:
        raise RunnerFailure("freeze_manifest_missing", "freeze manifest is unavailable") from error
    return _verify_freeze_manifest(manifest_bytes)


def _write_exclusive(path: Path, data: bytes) -> None:
    """Create a file or accept the same existing bytes. Never replace bytes."""

    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as stream:
            stream.write(data)
        return
    except FileExistsError:
        if not path.is_file():
            raise RunnerFailure("output_conflict", "output entry is not a file")
    if path.read_bytes() != data:
        raise RunnerFailure("output_conflict", "existing output differs")


def _first_non_xml_whitespace(value: str) -> str | None:
    return next((char for char in value if char not in XML_WHITESPACE), None)


def _last_non_xml_whitespace(value: str) -> str | None:
    return next((char for char in reversed(value) if char not in XML_WHITESPACE), None)


def _is_letter(value: str | None) -> bool:
    return bool(value) and unicodedata.category(value).startswith("L")


def _collapse_xml_whitespace(value: str) -> str:
    translated = value.translate(XML_WHITESPACE_TRANSLATION)
    collapsed = " ".join(part for part in translated.split(" ") if part)
    return collapsed.strip(XML_WHITESPACE)


def _ancestors(
    element: ET.Element,
    parents: dict[ET.Element, ET.Element],
) -> tuple[ET.Element, ...]:
    result: list[ET.Element] = []
    current = parents.get(element)
    while current is not None:
        result.append(current)
        current = parents.get(current)
    return tuple(result)


def _source_content(element: ET.Element) -> str:
    value = element.text or ""
    for child in list(element):
        value += _source_content(child)
        value += child.tail or ""
    return value


def _parent_map(root: ET.Element) -> dict[ET.Element, ET.Element]:
    elements = list(root.iter())
    return {child: parent for parent in elements for child in list(parent)}


def _parse_source(source: bytes | str) -> tuple[ET.Element, ET.Element, dict[ET.Element, ET.Element]]:
    try:
        root = ET.fromstring(source)
    except ET.ParseError as error:
        raise RunnerFailure("xml_not_well_formed", "XML is not well formed") from error
    if root.tag != _qname("TEI"):
        raise RunnerFailure("root_namespace", "root is not TEI in the exact namespace")
    for element in root.iter():
        if not isinstance(element.tag, str) or not element.tag.startswith("{"):
            raise RunnerFailure("element_namespace", "an element lacks the exact TEI namespace")
        namespace, _separator, _local = element.tag[1:].partition("}")
        if namespace != TEI_NS:
            raise RunnerFailure("element_namespace", "an element uses the wrong namespace")
    text_nodes = [child for child in list(root) if child.tag == _qname("text")]
    if len(text_nodes) != 1:
        raise RunnerFailure("text_structure", "TEI must have one direct text element")
    body_nodes = [child for child in list(text_nodes[0]) if child.tag == _qname("body")]
    if len(body_nodes) != 1:
        raise RunnerFailure("body_structure", "text must have one direct body element")
    body = body_nodes[0]
    return root, body, _parent_map(root)


def _ancestor_exclusion_path(
    element: ET.Element,
    excluded_root: ET.Element,
    parents: dict[ET.Element, ET.Element],
) -> tuple[str, ...]:
    chain: list[str] = []
    current: ET.Element | None = parents.get(element)
    while current is not None:
        tag = _local_name(current.tag)
        if tag in EXCLUDED_ANCESTOR_TAGS:
            chain.append(tag)
        if current is excluded_root:
            break
        current = parents.get(current)
    return tuple(reversed(chain))


def _counter_dict(counter: Counter[str]) -> dict[str, int]:
    return dict(sorted(counter.items()))


def _safe_record_location(
    record: object,
    record_index: int,
) -> dict[str, object]:
    location: dict[str, object] = {"record_index": record_index}
    if isinstance(record, dict):
        for key in (
            "book_id",
            "chapter_id",
            "chapter_key",
            "local_paragraph_ordinal",
        ):
            if key in record:
                location[key] = record[key]
    return location


def _first_record_difference(
    module_records: tuple[dict[str, object], ...],
    independent_records: tuple[dict[str, object], ...],
) -> tuple[dict[str, object], dict[str, object]] | None:
    limit = max(len(module_records), len(independent_records))
    for index in range(limit):
        module_record = module_records[index] if index < len(module_records) else None
        independent_record = (
            independent_records[index] if index < len(independent_records) else None
        )
        if module_record != independent_record:
            location = _safe_record_location(
                module_record if module_record is not None else independent_record,
                index,
            )
            return location, {
                "record_index": index,
                "module": module_record,
                "independent": independent_record,
            }
    return None


def _first_value_difference(
    module_value: object,
    independent_value: object,
    path: tuple[str, ...] = (),
) -> tuple[tuple[str, ...], object, object] | None:
    if isinstance(module_value, dict) and isinstance(independent_value, dict):
        keys = sorted(set(module_value) | set(independent_value), key=str)
        for key in keys:
            key_text = str(key)
            if key not in module_value or key not in independent_value:
                return path + (key_text,), module_value.get(key), independent_value.get(key)
            difference = _first_value_difference(
                module_value[key], independent_value[key], path + (key_text,)
            )
            if difference is not None:
                return difference
        return None
    if isinstance(module_value, list) and isinstance(independent_value, list):
        for index, (module_item, independent_item) in enumerate(
            zip(module_value, independent_value)
        ):
            difference = _first_value_difference(
                module_item,
                independent_item,
                path + (str(index),),
            )
            if difference is not None:
                return difference
        if len(module_value) != len(independent_value):
            index = min(len(module_value), len(independent_value))
            module_item = module_value[index] if index < len(module_value) else None
            independent_item = (
                independent_value[index] if index < len(independent_value) else None
            )
            return path + (str(index),), module_item, independent_item
        return None
    if module_value != independent_value:
        return path, module_value, independent_value
    return None


def _location(
    book_id: str,
    chapter_id: str,
    ordinal: int,
    *,
    global_ordinal: int | None = None,
) -> dict[str, object]:
    result: dict[str, object] = {
        "book_id": book_id,
        "chapter_id": chapter_id,
        "chapter_key": f"{book_id}:{chapter_id}",
        "local_paragraph_ordinal": ordinal,
    }
    if global_ordinal is not None:
        result["global_source_paragraph_ordinal"] = global_ordinal
    return result


def _validate_structure(
    source: bytes | str,
    *,
    require_source_shape: bool,
) -> ValidatedDocument:
    root, body, parents = _parse_source(source)
    body_elements = list(body.iter())
    for element in body_elements:
        tag = _local_name(element.tag)
        if tag not in ALLOWED_BODY_TAGS:
            raise RunnerFailure("unsupported_body_tag", f"unsupported body tag: {tag}")

    body_children = list(body)
    edition_candidates = [
        element
        for element in body_elements
        if _local_name(element.tag) == "div"
        and element.get("subtype") is None
    ]
    edition_wrapper: ET.Element | None = None
    for candidate in edition_candidates:
        if (
            parents.get(candidate) is not body
            or candidate.get("type") != "edition"
            or candidate.get(f"{{{XML_NS}}}lang") != "lat"
            or candidate.get("n") is not None
        ):
            raise RunnerFailure("edition_wrapper", "edition wrapper has invalid structure")
        if edition_wrapper is not None:
            raise RunnerFailure("duplicate_edition_wrapper", "duplicate edition wrapper")
        edition_wrapper = candidate

    if require_source_shape:
        if edition_wrapper is None or body_children != [edition_wrapper]:
            raise RunnerFailure("edition_wrapper", "pinned source lacks the exact edition wrapper")
    elif edition_wrapper is not None and body_children != [edition_wrapper]:
        raise RunnerFailure("edition_wrapper", "edition wrapper must be the only direct body child")

    books: list[ET.Element] = []
    chapters: list[ET.Element] = []
    book_ids: set[str] = set()
    chapter_keys: set[str] = set()
    chapter_info: dict[ET.Element, tuple[str, str, str]] = {}

    for element in body_elements:
        tag = _local_name(element.tag)
        if tag == "div":
            subtype = element.get("subtype")
            if element is edition_wrapper:
                if any(
                    child is not edition_wrapper
                    and not (
                        _local_name(child.tag) == "div"
                        and child.get("subtype") == "book"
                    )
                    and _local_name(child.tag) != "pb"
                    for child in list(element)
                ):
                    raise RunnerFailure("edition_children", "edition wrapper has unsupported children")
                continue
            if subtype not in {"book", "chapter"}:
                raise RunnerFailure("division_structure", "body div must be book or chapter")
            if require_source_shape and element.get("type") != "textpart":
                raise RunnerFailure("division_type", "source book or chapter lacks type=textpart")
            if any(
                _local_name(ancestor.tag) in STRUCTURE_FORBIDDEN_ANCESTORS
                for ancestor in _ancestors(element, parents)
            ):
                raise RunnerFailure("division_parent", "division is inside forbidden content")
            identifier = element.get("n")
            if identifier is None or not identifier:
                raise RunnerFailure("division_identifier", "book or chapter lacks n")
            parent = parents.get(element)
            if subtype == "book":
                valid_parent = parent is body or parent is edition_wrapper
                if not valid_parent:
                    raise RunnerFailure("book_parent", "book is not a direct structural child")
                if identifier in book_ids:
                    raise RunnerFailure("duplicate_book", "duplicate book identifier")
                book_ids.add(identifier)
                books.append(element)
            else:
                if (
                    parent is None
                    or _local_name(parent.tag) != "div"
                    or parent.get("subtype") != "book"
                ):
                    raise RunnerFailure("chapter_parent", "chapter is not a direct child of a book")
                book_id = parent.get("n")
                if book_id is None:
                    raise RunnerFailure("division_identifier", "chapter parent lacks book n")
                chapter_key = f"{book_id}:{identifier}"
                if chapter_key in chapter_keys:
                    raise RunnerFailure("duplicate_chapter", "duplicate chapter key")
                chapter_keys.add(chapter_key)
                chapters.append(element)
                chapter_info[element] = (book_id, identifier, chapter_key)
        elif tag == "choice":
            children = list(element)
            if [_local_name(child.tag) for child in children] != ["sic", "corr"]:
                raise RunnerFailure("choice_structure", "choice is not sic followed by corr")
            if element.text and element.text.strip():
                raise RunnerFailure("choice_structure", "choice has direct non-whitespace text")
        elif tag == "foreign":
            if element.get(f"{{{XML_NS}}}lang") != "grc":
                raise RunnerFailure("foreign_language", "foreign language is not grc")
        elif tag in {"sic", "corr"}:
            parent = parents.get(element)
            if parent is None or _local_name(parent.tag) != "choice":
                raise RunnerFailure("choice_structure", "sic or corr is not a choice child")

    if edition_wrapper is not None:
        wrapper_children = list(edition_wrapper)
        wrapper_books = [
            child
            for child in wrapper_children
            if _local_name(child.tag) == "div" and child.get("subtype") == "book"
        ]
        wrapper_pbs = [child for child in wrapper_children if _local_name(child.tag) == "pb"]
        if require_source_shape and (len(wrapper_books) != 8 or len(wrapper_pbs) != 7):
            raise RunnerFailure("edition_children", "source wrapper counts do not match")
        if require_source_shape and [book.get("n") for book in wrapper_books] != [
            str(index) for index in range(1, 9)
        ]:
            raise RunnerFailure("book_targets", "source book IDs do not match 1 through 8")

    paragraphs: list[ET.Element] = []
    locations: list[dict[str, object]] = []
    ordinals: Counter[str] = Counter()
    for element in body_elements:
        if _local_name(element.tag) != "p":
            continue
        ancestors = _ancestors(element, parents)
        if any(
            _local_name(ancestor.tag) in STRUCTURE_FORBIDDEN_ANCESTORS
            for ancestor in ancestors
        ):
            raise RunnerFailure("paragraph_parent", "paragraph is inside forbidden content")
        chapter = parents.get(element)
        if chapter not in chapter_info:
            raise RunnerFailure("paragraph_parent", "paragraph is not a direct child of chapter")
        book_id, chapter_id, chapter_key = chapter_info[chapter]
        ordinals[chapter_key] += 1
        paragraphs.append(element)
        locations.append(
            _location(book_id, chapter_id, ordinals[chapter_key], global_ordinal=len(paragraphs))
        )

    source_counts = _counter_dict(Counter(_local_name(element.tag) for element in body_elements))
    selected_counts = _counter_dict(
        Counter(_local_name(element.tag) for paragraph in paragraphs for element in paragraph.iter())
    )
    chapters_by_book = Counter(
        chapter_info[chapter][0]
        for chapter in chapters
    )
    paragraphs_by_book = Counter(location["book_id"] for location in locations)
    paragraphs_by_chapter = Counter(location["chapter_key"] for location in locations)
    div_type_counts = Counter(
        element.get("type")
        for element in body_elements
        if _local_name(element.tag) == "div" and element.get("type") is not None
    )
    div_subtype_counts = Counter(
        element.get("subtype")
        for element in body_elements
        if _local_name(element.tag) == "div" and element.get("subtype") is not None
    )
    empty_source_paragraphs = sum(
        not _collapse_xml_whitespace("".join(element.itertext()))
        for element in paragraphs
    )
    report: dict[str, object] = {
        "edition_wrapper_count": int(edition_wrapper is not None),
        "wrapper_book_count": (
            sum(
                _local_name(child.tag) == "div" and child.get("subtype") == "book"
                for child in list(edition_wrapper)
            )
            if edition_wrapper is not None
            else 0
        ),
        "wrapper_pb_count": (
            sum(_local_name(child.tag) == "pb" for child in list(edition_wrapper))
            if edition_wrapper is not None
            else 0
        ),
        "div_type_counts": dict(sorted(div_type_counts.items())),
        "div_subtype_counts": dict(sorted(div_subtype_counts.items())),
        "book_ids": [book.get("n") for book in books],
        "chapter_count": len(chapters),
        "chapter_keys": [chapter_info[chapter][2] for chapter in chapters],
        "paragraph_count": len(paragraphs),
        "paragraphs_outside_book_chapter": 0,
        "empty_source_paragraph_count": empty_source_paragraphs,
        "chapters_by_book": dict(sorted(chapters_by_book.items())),
        "paragraphs_by_book": dict(sorted(paragraphs_by_book.items())),
        "paragraphs_by_chapter": dict(sorted(paragraphs_by_chapter.items())),
        "source_counts": source_counts,
        "selected_subtree_counts": selected_counts,
    }
    if require_source_shape:
        _assert_source_targets(report)
    return ValidatedDocument(
        root=root,
        body=body,
        parents=parents,
        paragraphs=tuple(paragraphs),
        locations=tuple(locations),
        report=report,
    )


def _assert_source_targets(report: dict[str, object]) -> None:
    checks = {
        "edition_wrapper_count": report["edition_wrapper_count"] == 1,
        "wrapper_book_count": report["wrapper_book_count"] == 8,
        "wrapper_pb_count": report["wrapper_pb_count"] == 7,
        "book_ids": report["book_ids"] == [str(index) for index in range(1, 9)],
        "chapter_count": report["chapter_count"] == 211,
        "paragraph_count": report["paragraph_count"] == 550,
        "paragraphs_outside_book_chapter": report["paragraphs_outside_book_chapter"] == 0,
        "empty_source_paragraph_count": report["empty_source_paragraph_count"] == 0,
        "chapters_by_book": report["chapters_by_book"] == EXPECTED_CHAPTERS_BY_BOOK,
        "paragraphs_by_book": report["paragraphs_by_book"] == EXPECTED_PARAGRAPHS_BY_BOOK,
        "div_type_counts": report["div_type_counts"] == {"edition": 1, "textpart": 219},
        "div_subtype_counts": report["div_subtype_counts"] == {"book": 8, "chapter": 211},
    }
    source_counts = report["source_counts"]
    selected_counts = report["selected_subtree_counts"]
    checks.update(
        {f"source_{key}": source_counts.get(key, 0) == value for key, value in EXPECTED_SOURCE_COUNTS.items()}
    )
    checks.update(
        {f"selected_{key}": selected_counts.get(key, 0) == value for key, value in EXPECTED_SELECTED_COUNTS.items()}
    )
    failed = sorted(name for name, passed in checks.items() if not passed)
    if failed:
        raise RunnerFailure("source_structure", "source structure targets failed")


class _IndependentState:
    def __init__(self, location: dict[str, object]) -> None:
        self.location = location
        self.parts: list[str] = []
        self.pending_exclusion = False
        self.actual_retained: Counter[str] = Counter()
        self.direct_excluded: Counter[str] = Counter()
        self.ancestor_excluded: Counter[str] = Counter()
        self.ancestor_paths: Counter[str] = Counter()

    @property
    def raw_text(self) -> str:
        return "".join(self.parts)

    def append(self, value: str | None) -> None:
        if not value:
            return
        if self.pending_exclusion:
            left = _last_non_xml_whitespace(self.raw_text)
            right = _first_non_xml_whitespace(value)
            separated = (
                not self.raw_text
                or self.raw_text[-1] in XML_WHITESPACE
                or value[0] in XML_WHITESPACE
            )
            if not separated and _is_letter(left) and _is_letter(right):
                raise RunnerFailure(
                    "retained_boundary",
                    "retained letters joined after content exclusion",
                    location=self.location,
                )
            if right is not None:
                self.pending_exclusion = False
        self.parts.append(value)


def _independent_excluded_path(
    descendant: ET.Element,
    excluded_root: ET.Element,
    parents: dict[ET.Element, ET.Element],
) -> tuple[str, ...]:
    chain: list[str] = []
    current: ET.Element | None = parents.get(descendant)
    while current is not None:
        tag = _local_name(current.tag)
        if tag in EXCLUDED_ANCESTOR_TAGS:
            chain.append(tag)
        if current is excluded_root:
            break
        current = parents.get(current)
    return tuple(reversed(chain))


def _independent_record_excluded(
    element: ET.Element,
    state: _IndependentState,
    parents: dict[ET.Element, ET.Element],
) -> None:
    state.direct_excluded[_local_name(element.tag)] += 1
    for descendant in element.iter():
        if descendant is element:
            continue
        state.ancestor_excluded[_local_name(descendant.tag)] += 1
        path = _independent_excluded_path(descendant, element, parents)
        state.ancestor_paths[
            f"{_local_name(descendant.tag)}|{'>'.join(path)}"
        ] += 1
    state.pending_exclusion = True


def _independent_projected_content(element: ET.Element) -> str:
    tag = _local_name(element.tag)
    if tag in EXCLUDED_TAGS or tag == "sic":
        return ""
    if tag == "choice":
        sic, corr = list(element)
        return (sic.tail or "") + _independent_projected_content(corr) + (corr.tail or "")
    value = element.text or ""
    for child in list(element):
        value += _independent_projected_content(child)
        value += child.tail or ""
    return value


def _independent_visit(
    element: ET.Element,
    state: _IndependentState,
    parents: dict[ET.Element, ET.Element],
) -> None:
    tag = _local_name(element.tag)
    if tag in EXCLUDED_TAGS:
        _independent_record_excluded(element, state, parents)
        return
    if tag == "choice":
        state.actual_retained[tag] += 1
        state.append(element.text)
        sic, corr = list(element)
        previous_pending = state.pending_exclusion
        sic_has_content = _first_non_xml_whitespace(_source_content(sic)) is not None
        corr_has_content = _first_non_xml_whitespace(
            _independent_projected_content(corr)
        ) is not None
        _independent_record_excluded(sic, state, parents)
        state.pending_exclusion = previous_pending or (sic_has_content and not corr_has_content)
        state.append(sic.tail)
        _independent_visit(corr, state, parents)
        state.append(corr.tail)
        return
    state.actual_retained[tag] += 1
    state.append(element.text)
    for child in list(element):
        _independent_visit(child, state, parents)
        state.append(child.tail)


def _traverse_independently(document: ValidatedDocument) -> TraversalResult:
    records: list[dict[str, object]] = []
    ordinals: Counter[str] = Counter()
    actual_retained: Counter[str] = Counter()
    direct_excluded: Counter[str] = Counter()
    ancestor_excluded: Counter[str] = Counter()
    ancestor_paths: Counter[str] = Counter()
    projected_by_book: Counter[str] = Counter()
    projected_by_chapter: Counter[str] = Counter()
    empty_count = 0
    for paragraph, location in zip(document.paragraphs, document.locations):
        state = _IndependentState(location)
        _independent_visit(paragraph, state, document.parents)
        value = _collapse_xml_whitespace(state.raw_text)
        if not value:
            empty_count += 1
        actual_retained.update(state.actual_retained)
        direct_excluded.update(state.direct_excluded)
        ancestor_excluded.update(state.ancestor_excluded)
        ancestor_paths.update(state.ancestor_paths)
        ordinals[str(location["chapter_key"])] += 1
        if ordinals[str(location["chapter_key"])] != location["local_paragraph_ordinal"]:
            raise RunnerFailure("ordinal_mismatch", "paragraph ordinal mismatch", location=location)
        records.append(
            {
                key: location[key]
                for key in (
                    "book_id",
                    "chapter_id",
                    "chapter_key",
                    "local_paragraph_ordinal",
                )
            }
            | {"text": value}
        )
        projected_by_book[str(location["book_id"])] += 1
        projected_by_chapter[str(location["chapter_key"])] += 1
    report = {
        "empty_projected_paragraph_policy": "include",
        "source_paragraph_count": len(document.paragraphs),
        "projected_paragraph_count": len(records),
        "projected_paragraphs_by_book": _counter_dict(projected_by_book),
        "projected_paragraphs_by_chapter": _counter_dict(projected_by_chapter),
        "empty_projected_paragraph_count": empty_count,
        "dropped_empty_paragraph_count": 0,
        "book_ids": document.report["book_ids"],
        "chapter_keys": sorted(document.report["chapter_keys"]),
        "source_counts": document.report["source_counts"],
        "selected_subtree_counts": document.report["selected_subtree_counts"],
        "actual_retained": _counter_dict(actual_retained),
        "direct_excluded": _counter_dict(direct_excluded),
        "ancestor_excluded": {
            "by_tag": _counter_dict(ancestor_excluded),
            "by_path": dict(sorted(ancestor_paths.items())),
        },
        "boundary_validation": {"status": "PASS"},
    }
    return TraversalResult(tuple(records), report)


def _module_traverse(source: bytes) -> TraversalResult:
    try:
        try:
            from experiments.medical.tei_projection import project_tei
        except ModuleNotFoundError as error:
            if error.name not in {"experiments", "experiments.medical"}:
                raise
            from tei_projection import project_tei

        result = project_tei(source, empty_policy="include")
    except RunnerFailure:
        raise
    except Exception as error:
        raise RunnerFailure("module_projection", "reviewed projector failed") from error
    records = tuple(item.to_dict() for item in result.paragraphs)
    report = dict(result.report)
    projected_by_book: Counter[str] = Counter()
    projected_by_chapter: Counter[str] = Counter()
    for record in records:
        projected_by_book[str(record["book_id"])] += 1
        projected_by_chapter[str(record["chapter_key"])] += 1
    report["projected_paragraphs_by_book"] = _counter_dict(projected_by_book)
    report["projected_paragraphs_by_chapter"] = _counter_dict(projected_by_chapter)
    report["boundary_validation"] = {"status": "PASS"}
    return TraversalResult(records, report)


def _comparison_fields(report: dict[str, object]) -> dict[str, object]:
    return {
        key: report.get(key)
        for key in (
            "empty_projected_paragraph_policy",
            "source_paragraph_count",
            "projected_paragraph_count",
            "projected_paragraphs_by_book",
            "projected_paragraphs_by_chapter",
            "empty_projected_paragraph_count",
            "dropped_empty_paragraph_count",
            "book_ids",
            "chapter_keys",
            "source_counts",
            "selected_subtree_counts",
            "actual_retained",
            "direct_excluded",
            "ancestor_excluded",
            "boundary_validation",
        )
    }


def _check_projected_counts(
    document: ValidatedDocument,
    result: TraversalResult,
    traversal_name: str,
) -> None:
    if result.report.get("empty_projected_paragraph_policy") != "include":
        raise RunnerFailure(
            "projected_count_mismatch",
            f"{traversal_name} does not use the include policy",
        )
    expected_total = document.report["paragraph_count"]
    expected_by_book = document.report["paragraphs_by_book"]
    expected_by_chapter = document.report["paragraphs_by_chapter"]
    actual = (
        result.report.get("projected_paragraph_count"),
        result.report.get("projected_paragraphs_by_book"),
        result.report.get("projected_paragraphs_by_chapter"),
    )
    expected = (expected_total, expected_by_book, expected_by_chapter)
    if actual != expected:
        location = document.locations[0] if document.locations else None
        raise RunnerFailure(
            "projected_count_mismatch",
            f"{traversal_name} projected counts differ from source counts",
            location=location,
        )


def _manual_locations(
    locations: tuple[dict[str, object], ...],
) -> tuple[dict[str, object], ...]:
    selected: list[dict[str, object]] = []
    for book_id in [str(index) for index in range(1, 9)]:
        book_locations = [location for location in locations if location["book_id"] == book_id]
        if book_locations:
            selected.extend([book_locations[0], book_locations[-1]])
    targets = {1 + 36 * index for index in range(16)} | {550}
    selected.extend(
        location
        for location in locations
        if location["global_source_paragraph_ordinal"] in targets
    )
    unique: dict[tuple[object, ...], dict[str, object]] = {}
    for record in selected:
        key = (
            record["book_id"],
            record["chapter_id"],
            record["local_paragraph_ordinal"],
        )
        unique[key] = {
            key_name: record[key_name]
            for key_name in (
                "book_id",
                "chapter_id",
                "chapter_key",
                "local_paragraph_ordinal",
                "global_source_paragraph_ordinal",
            )
        }
    return tuple(unique.values())


def _manual_outputs(
    document: ValidatedDocument,
    module_records: tuple[dict[str, object], ...],
    independent_records: tuple[dict[str, object], ...],
) -> tuple[bytes, bytes]:
    locations = _manual_locations(document.locations)
    by_key = {
        (
            record["book_id"],
            record["chapter_id"],
            record["local_paragraph_ordinal"],
        ): record
        for record in module_records
    }
    independent_by_key = {
        (
            record["book_id"],
            record["chapter_id"],
            record["local_paragraph_ordinal"],
        ): record
        for record in independent_records
    }
    location_by_key = {
        (
            location["book_id"],
            location["chapter_id"],
            location["local_paragraph_ordinal"],
        ): (paragraph, location)
        for paragraph, location in zip(document.paragraphs, document.locations)
    }
    checklist = {
        "protocol": PROTOCOL,
        "manual_acceptance": "PENDING",
        "feature_names": list(MANUAL_FEATURES),
        "allowed_feature_statuses": ["PASS", "FAIL", "NOT_PRESENT"],
        "location_count": len(locations),
        "locations": list(locations),
        "checks": [
            {
                "location": location,
                "status": "PENDING",
                "features": {
                    feature: "PENDING" for feature in MANUAL_FEATURES
                },
            }
            for location in locations
        ],
    }
    contexts: list[dict[str, object]] = []
    for location in locations:
        key = (
            location["book_id"],
            location["chapter_id"],
            location["local_paragraph_ordinal"],
        )
        paragraph, _source_location = location_by_key[key]
        contexts.append(
            {
                "location": location,
                "source_xml": ET.tostring(paragraph, encoding="unicode"),
                "module_record": by_key[key],
                "independent_record": independent_by_key[key],
            }
        )
    return _canonical_json_bytes(checklist), _jsonl_bytes(contexts)


def _verify_audit_receipt(receipt_bytes: bytes) -> dict[str, object]:
    if _sha256(receipt_bytes) != AUDIT_RECEIPT_SHA256:
        raise RunnerFailure("audit_receipt_hash", "audit receipt hash does not match")
    try:
        receipt = json.loads(receipt_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RunnerFailure("audit_receipt_json", "audit receipt is not valid JSON") from error
    if not isinstance(receipt, dict):
        raise RunnerFailure("audit_receipt_json", "audit receipt is not a JSON object")
    if receipt.get("source_review_date") != SOURCE_REVIEW_DATE:
        raise RunnerFailure("audit_receipt_metadata", "audit receipt date does not match")
    repository = receipt.get("repository")
    if (
        not isinstance(repository, dict)
        or repository.get("url") != SOURCE_REPOSITORY
        or repository.get("commit") != SOURCE_COMMIT
    ):
        raise RunnerFailure("audit_receipt_metadata", "audit receipt repository does not match")
    files = receipt.get("files")
    if not isinstance(files, list):
        raise RunnerFailure("audit_receipt_metadata", "audit receipt files are not a list")
    xml_entries = [
        item
        for item in files
        if isinstance(item, dict) and item.get("role") == "TEI source"
    ]
    if len(xml_entries) != 1:
        raise RunnerFailure("audit_receipt_metadata", "audit receipt has no unique TEI source entry")
    xml_entry = xml_entries[0]
    if (
        xml_entry.get("url") != SOURCE_URL
        or xml_entry.get("bytes") != SOURCE_BYTES
        or xml_entry.get("sha256") != SOURCE_SHA256
        or xml_entry.get("expected_sha256") != SOURCE_SHA256
    ):
        raise RunnerFailure("audit_receipt_metadata", "audit receipt TEI source pins do not match")
    return receipt


def _verify_source(source: bytes) -> None:
    if len(source) != SOURCE_BYTES:
        raise RunnerFailure("source_bytes", "source byte count does not match")
    if _sha256(source) != SOURCE_SHA256:
        raise RunnerFailure("source_sha256", "source SHA-256 does not match")


def _load_source(output_dir: Path, source_path: Path | None) -> bytes:
    path = source_path or output_dir / SOURCE_FILENAME
    if path.exists():
        if not path.is_file():
            raise RunnerFailure("source_path", "source entry is not a file")
        source = path.read_bytes()
        _verify_source(source)
        return source
    request = urllib.request.Request(
        SOURCE_URL,
        headers={"User-Agent": "voynich-celsus-projection/1.0"},
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            source = response.read()
    except urllib.error.URLError as error:
        raise RunnerFailure("source_download", "pinned source download failed") from error
    _verify_source(source)
    _write_exclusive(path, source)
    return source


def _public_source_metadata(audit_receipt: dict[str, object]) -> dict[str, object]:
    return {
        "repository": SOURCE_REPOSITORY,
        "commit": SOURCE_COMMIT,
        "url": SOURCE_URL,
        "bytes": SOURCE_BYTES,
        "sha256": SOURCE_SHA256,
        "audit_revision": AUDIT_REVISION,
        "audit_receipt_sha256": AUDIT_RECEIPT_SHA256,
        "audit_receipt_checks": audit_receipt.get("checks", {}),
    }


def _failure_receipt(
    failure: RunnerFailure,
    *,
    audit_receipt_sha256: str = AUDIT_RECEIPT_SHA256,
    validation_scope: str = "pinned_source",
    freeze: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "protocol": PROTOCOL,
        "source_review_date": SOURCE_REVIEW_DATE,
        "validation_scope": validation_scope,
        "status": "FAILED",
        "manual_acceptance": "PENDING",
        "source": {
            "repository": SOURCE_REPOSITORY,
            "commit": SOURCE_COMMIT,
            "url": SOURCE_URL,
            "bytes": SOURCE_BYTES,
            "sha256": SOURCE_SHA256,
            "audit_revision": AUDIT_REVISION,
            "audit_receipt_sha256": audit_receipt_sha256,
        },
        "freeze": freeze or {"manifest_path": FREEZE_MANIFEST_PATH.as_posix()},
        "implementation": _implementation_pins(),
        "checks": {"automated_checks_pass": False},
        "failure": {
            "kind": failure.kind,
            "message": failure.message,
            "location": failure.location,
        },
    }


def _write_failure_detail(output_dir: Path, failure: RunnerFailure) -> None:
    if failure.details is None:
        return
    detail = {
        "schema_version": 1,
        "protocol": PROTOCOL,
        "kind": failure.kind,
        "location": failure.location,
        "details": failure.details,
    }
    _write_exclusive(output_dir / "mismatch-detail.json", _canonical_json_bytes(detail))


def _record_failure_detail(output_dir: Path, failure: RunnerFailure) -> RunnerFailure:
    try:
        _write_failure_detail(output_dir, failure)
    except (OSError, RunnerFailure):
        return RunnerFailure(
            "mismatch_detail_io",
            "private mismatch detail write failed",
        )
    return failure


def validate_bytes(
    source: bytes,
    *,
    require_source_shape: bool = False,
) -> tuple[ValidatedDocument, TraversalResult, TraversalResult]:
    """Validate and compare bytes without reading or writing project files."""

    document = _validate_structure(source, require_source_shape=require_source_shape)
    independent_result = _traverse_independently(document)
    _check_projected_counts(document, independent_result, "independent traversal")
    module_result = _module_traverse(source)
    _check_projected_counts(document, module_result, "module traversal")
    module_report = _comparison_fields(module_result.report)
    independent_report = _comparison_fields(independent_result.report)
    if module_result.records != independent_result.records:
        difference = _first_record_difference(
            module_result.records,
            independent_result.records,
        )
        if difference is None:
            raise RunnerFailure("traversal_mismatch", "module and independent records differ")
        location, details = difference
        raise RunnerFailure(
            "traversal_mismatch",
            "module and independent records differ",
            location=location,
            details={"type": "record", **details},
        )
    if module_report != independent_report:
        difference = _first_value_difference(module_report, independent_report)
        if difference is None:
            raise RunnerFailure("counter_mismatch", "module and independent counters differ")
        path, module_value, independent_value = difference
        counter_key = ".".join(path) or "root"
        raise RunnerFailure(
            "counter_mismatch",
            "module and independent counters differ",
            location={"counter_key": counter_key},
            details={
                "type": "counter",
                "counter_key": counter_key,
                "module": module_value,
                "independent": independent_value,
            },
        )
    return document, module_result, independent_result


def run_validation(
    source: bytes,
    audit_receipt_bytes: bytes,
    output_dir: Path,
    *,
    require_source_shape: bool = True,
) -> dict[str, object]:
    """Run validation and write private outputs plus a public receipt."""

    verified_freeze = None
    try:
        verified_freeze = _load_freeze_manifest()
        audit_receipt = _verify_audit_receipt(audit_receipt_bytes)
        _verify_source(source)
        document, module_result, independent_result = validate_bytes(
            source,
            require_source_shape=require_source_shape,
        )
        module_bytes = _jsonl_bytes(module_result.records)
        independent_bytes = _jsonl_bytes(independent_result.records)
        checklist_bytes, context_bytes = _manual_outputs(
            document,
            module_result.records,
            independent_result.records,
        )
        _write_exclusive(output_dir / "module-paragraphs.jsonl", module_bytes)
        _write_exclusive(output_dir / "independent-paragraphs.jsonl", independent_bytes)
        _write_exclusive(output_dir / "manual-checklist.json", checklist_bytes)
        _write_exclusive(output_dir / "manual-context.jsonl", context_bytes)
        checklist = json.loads(checklist_bytes.decode("utf-8"))
        receipt: dict[str, object] = {
            "schema_version": 1,
            "protocol": PROTOCOL,
            "source_review_date": SOURCE_REVIEW_DATE,
            "status": "PENDING_MANUAL_REVIEW",
            "manual_acceptance": "PENDING",
            "source": _public_source_metadata(audit_receipt),
            "freeze": verified_freeze,
            "implementation": _implementation_pins(),
            "validation_scope": (
                "pinned_source" if require_source_shape else "synthetic_unchecked"
            ),
            "empty_policy": "include",
            "structure": document.report,
            "module": {
                "record_count": len(module_result.records),
                "bytes": len(module_bytes),
                "sha256": _sha256(module_bytes),
                "report": module_result.report,
            },
            "independent": {
                "record_count": len(independent_result.records),
                "bytes": len(independent_bytes),
                "sha256": _sha256(independent_bytes),
                "report": independent_result.report,
            },
            "manual_context": {
                "record_count": len(context_bytes.splitlines()),
                "bytes": len(context_bytes),
                "sha256": _sha256(context_bytes),
            },
            "manual_checklist": {
                "record_count": checklist["location_count"],
                "bytes": len(checklist_bytes),
                "sha256": _sha256(checklist_bytes),
                "manual_acceptance": checklist["manual_acceptance"],
            },
            "comparison": {
                "records_equal": module_result.records == independent_result.records,
                "reports_equal": _comparison_fields(module_result.report)
                == _comparison_fields(independent_result.report),
                "paragraph_hashes_equal": _sha256(module_bytes) == _sha256(independent_bytes),
            },
            "checks": {
                "audit_receipt_pinned": True,
                "source_pinned": True,
                "source_structure_targets": require_source_shape,
                "source_structure_targets_status": (
                    "PASS" if require_source_shape else "NOT_RUN"
                ),
                "module_independent_records": True,
                "module_independent_counters": True,
                "manual_acceptance": "PENDING",
            },
        }
        receipt_bytes = _canonical_json_bytes(receipt)
        _write_exclusive(output_dir / "public-receipt.json", receipt_bytes)
        return receipt
    except RunnerFailure as failure:
        failure = _record_failure_detail(output_dir, failure)
        receipt = _failure_receipt(
            failure,
            validation_scope=(
                "pinned_source" if require_source_shape else "synthetic_unchecked"
            ),
            freeze=verified_freeze,
        )
        _write_exclusive(output_dir / "public-receipt.json", _canonical_json_bytes(receipt))
        return receipt
    except OSError:
        failure = RunnerFailure("runner_io", "runner input or output operation failed")
        failure = _record_failure_detail(output_dir, failure)
        receipt = _failure_receipt(
            failure,
            validation_scope=(
                "pinned_source" if require_source_shape else "synthetic_unchecked"
            ),
            freeze=verified_freeze,
        )
        _write_exclusive(output_dir / "public-receipt.json", _canonical_json_bytes(receipt))
        return receipt
    except Exception:
        failure = RunnerFailure("validation_error", "validation failed")
        failure = _record_failure_detail(output_dir, failure)
        receipt = _failure_receipt(
            failure,
            validation_scope=(
                "pinned_source" if require_source_shape else "synthetic_unchecked"
            ),
            freeze=verified_freeze,
        )
        _write_exclusive(output_dir / "public-receipt.json", _canonical_json_bytes(receipt))
        return receipt


def _argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--source-path", type=Path, default=None)
    parser.add_argument("--audit-receipt", type=Path, default=AUDIT_RECEIPT_DEFAULT)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _argument_parser().parse_args(argv)
    freeze_info: dict[str, object] | None = None
    try:
        freeze_info = _load_freeze_manifest()
        audit_bytes = args.audit_receipt.read_bytes()
        _verify_audit_receipt(audit_bytes)
        source = _load_source(args.output_dir, args.source_path)
        receipt = run_validation(
            source,
            audit_bytes,
            args.output_dir,
            require_source_shape=True,
        )
    except (OSError, RunnerFailure) as error:
        failure = error if isinstance(error, RunnerFailure) else RunnerFailure(
            "runner_io", "runner input or output operation failed"
        )
        receipt = _failure_receipt(failure, freeze=freeze_info)
        try:
            _write_exclusive(args.output_dir / "public-receipt.json", _canonical_json_bytes(receipt))
        except (OSError, RunnerFailure):
            return 1
    print(_canonical_json(receipt))
    return 0 if receipt.get("status") == "PENDING_MANUAL_REVIEW" else 1


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "AUDIT_RECEIPT_SHA256",
    "FREEZE_FILES",
    "FREEZE_MANIFEST_PATH",
    "PROTOCOL",
    "RunnerFailure",
    "SOURCE_COMMIT",
    "SOURCE_REPOSITORY",
    "SOURCE_SHA256",
    "SOURCE_URL",
    "TraversalResult",
    "ValidatedDocument",
    "_assert_source_targets",
    "_canonical_json_bytes",
    "_implementation_pins",
    "_manual_locations",
    "_sha256",
    "_validate_structure",
    "_verify_freeze_manifest",
    "run_validation",
    "validate_bytes",
]
