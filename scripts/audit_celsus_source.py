#!/usr/bin/env python3
"""Audit a pinned Celsus TEI source.

The script downloads only the pinned source and its small metadata files.
It writes them and an aggregate receipt to an ignored output directory.
It does not create a projected corpus or run a model.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import sys
import unicodedata
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Iterable


COMMIT = "ae0fe427f56d7652efc3090af74a2663a4cbed60"
REPOSITORY_URL = "https://github.com/PerseusDL/canonical-latinLit"
RAW_BASE = f"https://raw.githubusercontent.com/PerseusDL/canonical-latinLit/{COMMIT}"
COMMIT_URL = f"{REPOSITORY_URL}/commit/{COMMIT}"
NS = "http://www.tei-c.org/ns/1.0"
XML_NS = "http://www.w3.org/XML/1998/namespace"
# Fixed date of this source review. It is not the execution date.
SOURCE_REVIEW_DATE = "2026-09-17"
EXCLUDED_ANCESTOR_TAGS = ("head", "note", "del", "figure", "foreign", "sic")
PROJECTION_DIAGNOSTIC_TAGS = (
    "add",
    "choice",
    "corr",
    "del",
    "figure",
    "foreign",
    "head",
    "hi",
    "milestone",
    "note",
    "pb",
    "sic",
)
DIRECT_DROP_TAGS = (
    "del",
    "figure",
    "foreign",
    "head",
    "milestone",
    "note",
    "pb",
    "sic",
)
RETAINED_CANDIDATE_TAGS = ("choice", "corr", "hi")

SOURCES = {
    "cts": {
        "role": "CTS work metadata",
        "url": f"{RAW_BASE}/data/phi0836/phi002/__cts__.xml",
        "file": "celsus-cts.xml",
        "bytes": 1694,
        "git_blob_sha1": "8490f544b0edee9edef9f24e1d9785e9eba6727d",
        "sha256": "497674650e7a74c9f42257a144583b955c8a8989b958abf7e72b9d51efa5aa1a",
    },
    "xml": {
        "role": "TEI source",
        "url": f"{RAW_BASE}/data/phi0836/phi002/phi0836.phi002.perseus-lat5.xml",
        "file": "celsus-lat5.xml",
        "bytes": 893899,
        "git_blob_sha1": "dead5082d1d181fd8e43dceeed4793f79213831c",
        "sha256": "a4a5194ba38a7efd5192d20f2a7b696f4fa64105010eb629aa7c35255a935145",
    },
    "readme": {
        "role": "Repository README",
        "url": f"{RAW_BASE}/README.md",
        "file": "canonical-latinLit-README.md",
        "bytes": 2334,
        "git_blob_sha1": "dc327f44bde676e16bb63cd223afa922d00045b5",
        "sha256": "7ea684aea5b084c38fc919da2adf0df8339490243a43bf744fb8e27384d82623",
    },
    "license": {
        "role": "Repository license",
        "url": f"{RAW_BASE}/license.md",
        "file": "canonical-latinLit-license.md",
        "bytes": 18625,
        "git_blob_sha1": "033217724f8631eeb12987b30d76e8a62f275ceb",
        "sha256": "ccf0e8ce183761bf82700126cc45a4e907b2cede024e65e3fef5c2338b9b7063",
    },
}

EVIDENCE_URLS = {
    "commit": COMMIT_URL,
    "repository_readme": SOURCES["readme"]["url"],
    "repository_license": SOURCES["license"]["url"],
    "dll_author": "https://catalog.digitallatin.org/dll-author/a5349",
    "dll_work": "https://catalog.digitallatin.org/dll-work/w2724",
    "scaife_edition": "https://atlas.perseus.tufts.edu/library/urn:cts:latinLit:phi0836.phi002.perseus-lat5/",
}


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def text_of(element: ET.Element | None) -> str:
    if element is None:
        return ""
    return "".join(element.itertext()).strip()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_blob_sha1(data: bytes) -> str:
    prefix = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(prefix + data).hexdigest()


def write_if_identical(path: Path, data: bytes) -> None:
    """Write a result only when it does not replace different existing data."""
    try:
        with path.open("xb") as stream:
            stream.write(data)
        return
    except FileExistsError:
        if not path.is_file():
            raise RuntimeError(f"output entry is not a file: {path.name}")
    existing = path.read_bytes()
    if existing != data:
        raise RuntimeError(f"refusing to overwrite changed output: {path.name}")


def observed_file(spec: dict[str, object], data: bytes) -> dict[str, object]:
    observed = {
        "role": spec["role"],
        "url": spec["url"],
        "file": spec["file"],
        "expected_bytes": spec["bytes"],
        "expected_git_blob_sha1": spec["git_blob_sha1"],
        "expected_sha256": spec["sha256"],
        "bytes": len(data),
        "git_blob_sha1": git_blob_sha1(data),
        "sha256": sha256(data),
    }
    for key in ("bytes", "git_blob_sha1", "sha256"):
        if observed[key] != spec[key]:
            raise RuntimeError(
                f"{spec['file']}: {key} mismatch; expected {spec[key]}, "
                f"got {observed[key]}"
            )
    observed["verified"] = True
    return observed


def fetch_or_check(spec: dict[str, object], output_dir: Path) -> dict[str, object]:
    path = output_dir / str(spec["file"])
    if path.exists():
        if not path.is_file():
            raise RuntimeError(f"source entry is not a file: {path.name}")
        data = path.read_bytes()
        return observed_file(spec, data)

    request = urllib.request.Request(
        str(spec["url"]),
        headers={"User-Agent": "voynich-celsus-source-audit/1.0"},
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        data = response.read()
    observed = observed_file(spec, data)
    try:
        with path.open("xb") as stream:
            stream.write(data)
    except FileExistsError:
        if not path.is_file():
            raise RuntimeError(f"source entry is not a file: {path.name}")
        return observed_file(spec, path.read_bytes())
    return observed


def children_by_local(element: ET.Element, name: str) -> list[ET.Element]:
    return [child for child in list(element) if local_name(child.tag) == name]


def collect_header(root: ET.Element) -> dict[str, object]:
    header = next((item for item in root.iter() if local_name(item.tag) == "teiHeader"), None)
    if header is None:
        raise RuntimeError("TEI header not found")
    title_stmt = header.find(".//tei:titleStmt", {"tei": NS})
    source_mono = header.find(".//tei:sourceDesc/tei:biblStruct/tei:monogr", {"tei": NS})
    publication = header.find(".//tei:publicationStmt", {"tei": NS})
    imprint = source_mono.find("tei:imprint", {"tei": NS}) if source_mono is not None else None

    def child_values(parent: ET.Element | None, name: str) -> list[str]:
        if parent is None:
            return []
        return [text_of(item) for item in children_by_local(parent, name) if text_of(item)]

    availability = header.findall(".//tei:availability", {"tei": NS})
    licence = header.findall(".//tei:licence", {"tei": NS})
    rights = header.findall(".//tei:rights", {"tei": NS})
    refs = header.findall(".//tei:refsDecl", {"tei": NS})
    return {
        "title": child_values(title_stmt, "title"),
        "author": child_values(title_stmt, "author"),
        "editor": child_values(title_stmt, "editor"),
        "source_title": child_values(source_mono, "title"),
        "source_editor": child_values(source_mono, "editor"),
        "source_publisher": child_values(imprint, "publisher"),
        "source_place": child_values(imprint, "pubPlace"),
        "source_date": child_values(imprint, "date"),
        "publication_publisher": child_values(publication, "publisher"),
        "publication_place": child_values(publication, "pubPlace"),
        "publication_date": child_values(publication, "date"),
        "availability_element_count": len(availability),
        "licence_element_count": len(licence),
        "rights_element_count": len(rights),
        "refs_decl_units": sorted(
            {
                state.get("unit")
                for ref in refs
                for state in ref.findall("tei:refState", {"tei": NS})
                if state.get("unit")
            }
        ),
    }


def count_values(elements: Iterable[ET.Element], attribute: str) -> dict[str, int]:
    counts: collections.Counter[str] = collections.Counter()
    for element in elements:
        value = element.get(attribute)
        if value is not None:
            counts[value] += 1
    return dict(sorted(counts.items()))


def duplicate_values(values: Iterable[str]) -> dict[str, int]:
    counts = collections.Counter(value for value in values if value)
    return dict(sorted((value, count) for value, count in counts.items() if count > 1))


def is_letter(character: str | None) -> bool:
    return bool(character) and unicodedata.category(character).startswith("L")


def last_nonspace(value: str) -> str | None:
    return next((char for char in reversed(value) if not char.isspace()), None)


def first_nonspace(value: str) -> str | None:
    return next((char for char in value if not char.isspace()), None)


def boundary_class(before: str, after: str) -> str:
    left = last_nonspace(before)
    right = first_nonspace(after)
    if left is None or right is None:
        return "missing_boundary"
    if is_letter(left) and is_letter(right):
        if before[-1:].isspace() or after[:1].isspace():
            return "letter_letter_with_whitespace"
        return "letter_letter_without_whitespace"
    if is_letter(left):
        return "letter_nonletter"
    if is_letter(right):
        return "nonletter_letter"
    return "nonletter_nonletter"


def boundary_stats(elements: Iterable[ET.Element], parents: dict[ET.Element, ET.Element]) -> dict[str, int]:
    counts: collections.Counter[str] = collections.Counter()
    for element in elements:
        parent = parents.get(element)
        if parent is None:
            counts["missing_parent"] += 1
            continue
        siblings = list(parent)
        index = siblings.index(element)
        before = (parent.text or "") if index == 0 else (siblings[index - 1].tail or "")
        after = element.tail or ""
        counts[boundary_class(before, after)] += 1
    return dict(sorted(counts.items()))


def ancestor_tag_path(
    element: ET.Element,
    parents: dict[ET.Element, ET.Element],
) -> tuple[str, ...]:
    path: list[str] = []
    current = parents.get(element)
    while current is not None:
        tag = local_name(current.tag)
        if tag in EXCLUDED_ANCESTOR_TAGS:
            path.append(tag)
        current = parents.get(current)
    return tuple(path)


def projection_scope_diagnostics(
    elements: Iterable[ET.Element],
    parents: dict[ET.Element, ET.Element],
    scope: str,
) -> dict[str, object]:
    scoped = list(elements)
    totals = collections.Counter(
        local_name(element.tag)
        for element in scoped
        if local_name(element.tag) in PROJECTION_DIAGNOSTIC_TAGS
    )
    paths: dict[str, collections.Counter[str]] = {
        tag: collections.Counter() for tag in PROJECTION_DIAGNOSTIC_TAGS
    }
    for element in scoped:
        tag = local_name(element.tag)
        if tag not in paths:
            continue
        path = ancestor_tag_path(element, parents)
        if path:
            paths[tag][">".join(path)] += 1

    ancestor_counts = {}
    for tag in PROJECTION_DIAGNOSTIC_TAGS:
        path_counts = dict(sorted(paths[tag].items()))
        with_ancestor = sum(path_counts.values())
        ancestor_counts[tag] = {
            "total_count": totals.get(tag, 0),
            "with_any_excluded_ancestor": with_ancestor,
            "without_excluded_ancestor": totals.get(tag, 0) - with_ancestor,
            "excluded_ancestor_paths": path_counts,
        }

    return {
        "scope": scope,
        "ancestor_exclusion_counts": ancestor_counts,
        "direct_drop_candidate_counts": {
            tag: sum(
                local_name(element.tag) == tag
                and not ancestor_tag_path(element, parents)
                for element in scoped
            )
            for tag in DIRECT_DROP_TAGS
        },
        "retained_candidate_counts": {
            tag: sum(
                local_name(element.tag) == tag
                and not ancestor_tag_path(element, parents)
                for element in scoped
            )
            for tag in RETAINED_CANDIDATE_TAGS
        },
    }


def audit_xml(data: bytes) -> dict[str, object]:
    try:
        root = ET.fromstring(data)
    except ET.ParseError as error:
        return {"well_formed": False, "parse_error": str(error)}

    all_elements = list(root.iter())
    body = next((item for item in all_elements if local_name(item.tag) == "body"), None)
    if body is None:
        raise RuntimeError("TEI body not found")
    body_elements = list(body.iter())
    parents = {child: parent for parent in all_elements for child in list(parent)}
    books = [
        item
        for item in body_elements
        if local_name(item.tag) == "div" and item.get("subtype") == "book"
    ]
    chapters = [
        item
        for item in body_elements
        if local_name(item.tag) == "div" and item.get("subtype") == "chapter"
    ]
    paragraphs = [item for item in body_elements if local_name(item.tag) == "p"]
    book_ids = [item.get("n", "") for item in books]
    chapter_ids = [item.get("n", "") for item in chapters]

    def ancestors(element: ET.Element) -> list[ET.Element]:
        result: list[ET.Element] = []
        current = parents.get(element)
        while current is not None:
            result.append(current)
            current = parents.get(current)
        return result

    def ancestor_with_subtype(element: ET.Element, subtype: str) -> ET.Element | None:
        return next(
            (item for item in ancestors(element) if item.get("subtype") == subtype),
            None,
        )

    paragraph_keys = {
        (
            ancestor_with_subtype(paragraph, "book").get("n", "")
            if ancestor_with_subtype(paragraph, "book") is not None
            else "",
            ancestor_with_subtype(paragraph, "chapter").get("n", "")
            if ancestor_with_subtype(paragraph, "chapter") is not None
            else "",
        )
        for paragraph in paragraphs
    }
    selected_paragraphs = [
        paragraph
        for paragraph in paragraphs
        if ancestor_with_subtype(paragraph, "book") is not None
        and ancestor_with_subtype(paragraph, "chapter") is not None
    ]
    selected_paragraph_set = set(selected_paragraphs)

    def inside_selected_paragraph(element: ET.Element) -> bool:
        return any(item in selected_paragraph_set for item in ancestors(element))

    selected_elements = [
        element
        for element in body_elements
        if inside_selected_paragraph(element)
    ]

    tags = collections.Counter(local_name(item.tag) for item in body_elements)
    selected_tags = collections.Counter(local_name(item.tag) for item in selected_elements)
    relevant_tags = {
        "choice",
        "foreign",
        "note",
        "del",
        "add",
        "head",
        "pb",
        "milestone",
        "figure",
        "hi",
    }
    source_relevant = {tag: tags.get(tag, 0) for tag in sorted(relevant_tags)}
    selected_relevant = {
        tag: selected_tags.get(tag, 0) for tag in sorted(relevant_tags)
    }
    outside_relevant = {
        tag: source_relevant[tag] - selected_relevant[tag]
        for tag in sorted(relevant_tags)
    }

    chapter_keys = [
        f"{ancestor_with_subtype(chapter, 'book').get('n', '')}:{chapter.get('n', '')}"
        for chapter in chapters
        if ancestor_with_subtype(chapter, "book") is not None
    ]
    chapters_by_book: dict[str, int] = {}
    paragraphs_by_book: dict[str, int] = {}
    chapters_with_paragraphs: set[str] = set()
    for book in books:
        book_id = book.get("n", "")
        chapters_by_book[book_id] = 0
        paragraphs_by_book[book_id] = 0
        for item in book.iter():
            if local_name(item.tag) == "div" and item.get("subtype") == "chapter":
                chapters_by_book[book_id] += 1
            if local_name(item.tag) == "p":
                paragraphs_by_book[book_id] += 1
                chapter = ancestor_with_subtype(item, "chapter")
                if chapter is not None:
                    chapters_with_paragraphs.add(f"{book_id}:{chapter.get('n', '')}")

    choices = [item for item in body_elements if local_name(item.tag) == "choice"]
    choice_patterns = collections.Counter(
        ",".join(local_name(child.tag) for child in list(choice))
        for choice in choices
    )
    foreign = [item for item in body_elements if local_name(item.tag) == "foreign"]
    xml_ids = [item.get(f"{{{XML_NS}}}id", "") for item in all_elements]
    empty_leaves = collections.Counter(
        local_name(item.tag)
        for item in body_elements
        if not text_of(item) and not list(item)
    )

    boundary_tags = ["choice", "foreign", "note", "del", "pb", "milestone"]
    mixed_boundaries: dict[str, dict[str, object]] = {}
    for tag in boundary_tags:
        source_elements = [item for item in body_elements if local_name(item.tag) == tag]
        selected = [item for item in source_elements if inside_selected_paragraph(item)]
        mixed_boundaries[tag] = {
            "source_count": len(source_elements),
            "selected_count": len(selected),
            "outside_selected_count": len(source_elements) - len(selected),
            "source_boundary_classes": boundary_stats(source_elements, parents),
            "selected_boundary_classes": boundary_stats(selected, parents),
        }

    return {
        "well_formed": True,
        "schema_validation": "not performed",
        "element_count": len(all_elements),
        "body_element_count": len(body_elements),
        "body_tag_counts": dict(sorted(tags.items())),
        "source_relevant_tag_counts": source_relevant,
        "selected_relevant_tag_counts": selected_relevant,
        "outside_selected_relevant_tag_counts": outside_relevant,
        "projection_diagnostics": {
            "status": "diagnostic only; no projection was run",
            "excluded_ancestor_tags": list(EXCLUDED_ANCESTOR_TAGS),
            "source_body": projection_scope_diagnostics(
                body_elements, parents, "source body"
            ),
            "selected_paragraph_subtree": projection_scope_diagnostics(
                selected_elements, parents, "selected paragraph subtree"
            ),
        },
        "mixed_content_boundary_method": (
            "The scan uses parent text or the immediate previous sibling tail "
            "before an element, and that element tail after it. It does not "
            "simulate removal of adjacent excluded siblings."
        ),
        "book_count": len(books),
        "book_ids": book_ids,
        "book_ids_complete_1_to_8": book_ids == [str(index) for index in range(1, 9)],
        "book_id_duplicates": duplicate_values(book_ids),
        "chapter_count": len(chapters),
        "chapter_ids_repeat_across_books": bool(duplicate_values(chapter_ids)),
        "chapter_key_count": len(chapter_keys),
        "chapter_key_duplicates": duplicate_values(chapter_keys),
        "chapters_by_book": chapters_by_book,
        "paragraph_count": len(paragraphs),
        "paragraphs_by_book": paragraphs_by_book,
        "paragraph_id_count": sum(
            bool(item.get(f"{{{XML_NS}}}id") or item.get("n")) for item in paragraphs
        ),
        "empty_paragraph_count": sum(not text_of(item) for item in paragraphs),
        "xml_id_count": sum(bool(value) for value in xml_ids),
        "xml_id_duplicates": duplicate_values(xml_ids),
        "choice_count": len(choices),
        "choice_patterns": dict(sorted(choice_patterns.items())),
        "foreign_count": len(foreign),
        "foreign_languages": count_values(foreign, f"{{{XML_NS}}}lang"),
        "note_count": tags.get("note", 0),
        "add_count": tags.get("add", 0),
        "del_count": tags.get("del", 0),
        "empty_leaf_counts": dict(sorted(empty_leaves.items())),
        "selected_projection_coverage": {
            "selected_paragraph_count": len(selected_paragraphs),
            "paragraphs_outside_book_chapter": len(paragraphs) - len(selected_paragraphs),
            "selected_book_count": len(
                {
                    ancestor_with_subtype(item, "book").get("n", "")
                    for item in selected_paragraphs
                    if ancestor_with_subtype(item, "book") is not None
                }
            ),
            "selected_chapter_count": len(paragraph_keys),
            "chapters_with_paragraphs": len(chapters_with_paragraphs),
            "all_books_have_prose": len(paragraphs_by_book) == 8
            and all(value > 0 for value in paragraphs_by_book.values()),
            "all_chapters_have_prose": len(chapters_with_paragraphs) == len(chapters),
            "chapter_key_count": len(paragraph_keys),
            "chapter_key_duplicates": duplicate_values(
                f"{book}:{chapter}" for book, chapter in paragraph_keys
            ),
            "selected_node_counts": dict(sorted(selected_tags.items())),
        },
        "mixed_content_boundaries": mixed_boundaries,
    }


def build_receipt(observed: dict[str, dict[str, object]], xml: bytes) -> dict[str, object]:
    root = ET.fromstring(xml)
    header = collect_header(root)
    audit = audit_xml(xml)
    return {
        "schema_version": 1,
        "source_review_date": SOURCE_REVIEW_DATE,
        "repository": {
            "url": REPOSITORY_URL,
            "branch": "master",
            "commit": COMMIT,
            "commit_url": COMMIT_URL,
        },
        "evidence_urls": EVIDENCE_URLS,
        "license_evidence": {
            "repository_statement": "CC BY-SA 4.0 unless otherwise indicated",
            "modification_request": "Offer Perseus any modifications",
            "tei_availability_element_count": header["availability_element_count"],
            "tei_licence_element_count": header["licence_element_count"],
            "tei_rights_element_count": header["rights_element_count"],
        },
        "files": [observed[key] for key in ("xml", "cts", "readme", "license")],
        "tei_header": header,
        "audit": audit,
        "checks": {
            "all_file_digests_match_pins": all(
                bool(item.get("verified")) for item in observed.values()
            ),
            "xml_well_formed": audit.get("well_formed") is True,
            "all_book_ids_1_to_8": audit.get("book_ids_complete_1_to_8") is True,
            "all_chapter_keys_unique": not audit.get("chapter_key_duplicates"),
            "all_selected_chapter_keys_unique": not audit[
                "selected_projection_coverage"
            ]["chapter_key_duplicates"],
            "all_books_have_prose": audit["selected_projection_coverage"][
                "all_books_have_prose"
            ],
            "all_chapters_have_prose": audit["selected_projection_coverage"][
                "all_chapters_have_prose"
            ],
            "choice_pattern_is_sic_corr": audit.get("choice_patterns") == {"sic,corr": 446},
            "foreign_text_is_greek": audit.get("foreign_languages") == {"grc": 276},
            "no_empty_paragraphs": audit.get("empty_paragraph_count") == 0,
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("results/celsus-source-audit"),
        help="ignored directory for pinned inputs and the aggregate receipt",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    observed: dict[str, dict[str, object]] = {}
    data: dict[str, bytes] = {}
    for key, spec in SOURCES.items():
        result = fetch_or_check(spec, output_dir)
        observed[key] = result
        data[key] = (output_dir / str(spec["file"])).read_bytes()
    receipt = build_receipt(observed, data["xml"])
    failed_checks = sorted(
        name for name, passed in receipt["checks"].items() if not passed
    )
    if failed_checks:
        raise RuntimeError("aggregate audit checks failed: " + ", ".join(failed_checks))
    receipt_bytes = (
        json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    write_if_identical(output_dir / "public-receipt.json", receipt_bytes)
    print(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ET.ParseError, urllib.error.URLError) as error:
        print(f"audit failed: {error}", file=sys.stderr)
        raise SystemExit(1)
