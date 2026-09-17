"""Strict TEI paragraph projection for the Celsus control.

The projector accepts one TEI XML document and returns paragraph records plus
diagnostic counts. The caller supplies source bytes. This module does not fetch sources.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import re
import unicodedata
import xml.etree.ElementTree as ET
from typing import Any


TEI_NS = "http://www.tei-c.org/ns/1.0"
XML_NS = "http://www.w3.org/XML/1998/namespace"

BODY_TAGS = frozenset(
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
XML_WHITESPACE_RE = re.compile(r"[ \t\r\n]+")


class ProjectionError(ValueError):
    """Raised when the TEI input does not meet the fixed projection contract."""


@dataclass(frozen=True)
class ProjectedParagraph:
    """One projected source paragraph and its stable source location."""

    book_id: str
    chapter_id: str
    chapter_key: str
    local_paragraph_ordinal: int
    text: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "book_id": self.book_id,
            "chapter_id": self.chapter_id,
            "chapter_key": self.chapter_key,
            "local_paragraph_ordinal": self.local_paragraph_ordinal,
            "text": self.text,
        }


@dataclass(frozen=True)
class ProjectionResult:
    """Projected paragraphs and diagnostics for one TEI document."""

    paragraphs: tuple[ProjectedParagraph, ...]
    report: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "paragraphs": [paragraph.to_dict() for paragraph in self.paragraphs],
            "report": self.report,
        }


def _qname(local_name: str) -> str:
    return f"{{{TEI_NS}}}{local_name}"


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _parse_xml(source: bytes | str) -> ET.Element:
    if not isinstance(source, (bytes, str)):
        raise TypeError("source must be XML bytes or a string")
    try:
        root = ET.fromstring(source)
    except ET.ParseError as exc:
        raise ProjectionError(f"XML is not well formed: {exc}") from exc
    if root.tag != _qname("TEI"):
        raise ProjectionError("root element must be TEI in the exact TEI namespace")
    for element in root.iter():
        if not isinstance(element.tag, str) or not element.tag.startswith("{"):
            raise ProjectionError("all XML elements must use the exact TEI namespace")
        namespace, _separator, _local = element.tag[1:].partition("}")
        if namespace != TEI_NS:
            raise ProjectionError("all XML elements must use the exact TEI namespace")
    return root


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


def _identifier(element: ET.Element, kind: str) -> str:
    value = element.get("n")
    if value is None or not value:
        raise ProjectionError(f"{kind} must have a non-empty n identifier")
    return value


def _validate_body(
    body: ET.Element,
) -> tuple[
    dict[ET.Element, tuple[str, str, str]],
    tuple[ET.Element, ...],
    dict[ET.Element, ET.Element],
]:
    """Validate all body markup before selecting paragraph content."""

    elements = list(body.iter())
    parents = {
        child: parent
        for parent in elements
        for child in list(parent)
    }
    for element in elements:
        tag = _local_name(element.tag)
        if tag not in BODY_TAGS:
            raise ProjectionError(f"unsupported body tag: {tag}")

    books: list[ET.Element] = []
    book_ids: set[str] = set()
    chapter_keys: set[str] = set()
    chapter_info: dict[ET.Element, tuple[str, str, str]] = {}

    # The pinned source has one optional direct-body edition wrapper.  Resolve
    # its identity before division validation so all later parent checks use
    # the same structural rule.
    edition_wrapper: ET.Element | None = None
    for element in elements:
        if _local_name(element.tag) != "div":
            continue
        subtype = element.get("subtype")
        if subtype is not None:
            if element.get("type") == "edition":
                raise ProjectionError(
                    "edition div cannot have subtype or book/chapter structure"
                )
            continue
        if (
            parents.get(element) is not body
            or element.get("type") != "edition"
            or element.get(f"{{{XML_NS}}}lang") != "lat"
            or element.get("n") is not None
        ):
            raise ProjectionError(
                "edition div must be a single direct body wrapper with "
                "type='edition', xml:lang='lat', and no n or subtype"
            )
        if edition_wrapper is not None:
            raise ProjectionError("duplicate edition wrapper")
        edition_wrapper = element

    for element in elements:
        tag = _local_name(element.tag)
        if tag == "div":
            subtype = element.get("subtype")
            ancestors = _ancestors(element, parents)
            if subtype is None:
                continue
            if subtype not in {"book", "chapter"}:
                raise ProjectionError("body div must have subtype book or chapter")
            identifier = _identifier(element, subtype)
            if any(
                _local_name(ancestor.tag) in STRUCTURE_FORBIDDEN_ANCESTORS
                for ancestor in ancestors
            ):
                raise ProjectionError(
                    f"{subtype} div cannot be inside excluded or editorial content"
                )
            if subtype == "book":
                parent = parents.get(element)
                if parent is not body and parent is not edition_wrapper:
                    raise ProjectionError(
                        "book div must be a direct child of body or edition wrapper"
                    )
                if identifier in book_ids:
                    raise ProjectionError(f"duplicate book identifier: {identifier}")
                book_ids.add(identifier)
                books.append(element)
            else:
                book = parents.get(element)
                if (
                    book is None
                    or _local_name(book.tag) != "div"
                    or book.get("subtype") != "book"
                ):
                    raise ProjectionError(
                        "chapter div must be a direct child of book div"
                    )
                book_id = _identifier(book, "book")
                chapter_key = f"{book_id}:{identifier}"
                if chapter_key in chapter_keys:
                    raise ProjectionError(f"duplicate chapter key: {chapter_key}")
                chapter_keys.add(chapter_key)
                chapter_info[element] = (book_id, identifier, chapter_key)
        elif tag == "choice":
            children = list(element)
            if [_local_name(child.tag) for child in children] != ["sic", "corr"]:
                raise ProjectionError("choice must contain exactly sic followed by corr")
            if element.text and element.text.strip():
                raise ProjectionError("choice cannot contain direct non-whitespace text")
        elif tag == "foreign":
            if element.get(f"{{{XML_NS}}}lang") != "grc":
                raise ProjectionError("foreign must have xml:lang='grc'")
        elif tag in {"sic", "corr"}:
            parent = parents.get(element)
            if parent is None or _local_name(parent.tag) != "choice":
                raise ProjectionError(f"{tag} must be a direct child of choice")

    paragraphs: list[ET.Element] = []
    for element in elements:
        if _local_name(element.tag) != "p":
            continue
        ancestors = _ancestors(element, parents)
        if any(
            _local_name(ancestor.tag) in STRUCTURE_FORBIDDEN_ANCESTORS
            for ancestor in ancestors
        ):
            raise ProjectionError(
                "paragraph cannot be inside excluded or editorial content"
            )
        if any(_local_name(ancestor.tag) == "p" for ancestor in ancestors):
            raise ProjectionError("nested paragraph elements are not supported")
        chapter = parents.get(element)
        if (
            chapter is None
            or _local_name(chapter.tag) != "div"
            or chapter.get("subtype") != "chapter"
            or chapter not in chapter_info
        ):
            raise ProjectionError(
                "paragraph must be a direct child of chapter div"
            )
        paragraphs.append(element)

    # Keep this map separate from the paragraph list.  It gives each paragraph
    # its nearest chapter metadata without relying on mutable XML attributes.
    return chapter_info, tuple(paragraphs), parents


def _is_letter(character: str | None) -> bool:
    return bool(character) and unicodedata.category(character).startswith("L")


def _first_non_xml_whitespace(value: str) -> str | None:
    return next((char for char in value if char not in " \t\r\n"), None)


def _last_non_xml_whitespace(value: str) -> str | None:
    return next(
        (char for char in reversed(value) if char not in " \t\r\n"),
        None,
    )


def _collapse_xml_whitespace(value: str) -> str:
    return XML_WHITESPACE_RE.sub(" ", value).strip(" \t\r\n")


class _ParagraphState:
    def __init__(self) -> None:
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
                or self.raw_text[-1] in " \t\r\n"
                or value[0] in " \t\r\n"
            )
            if not separated and _is_letter(left) and _is_letter(right):
                raise ProjectionError(
                    "content exclusion joined adjacent letters; no space was inserted"
                )
            if _first_non_xml_whitespace(value) is not None:
                self.pending_exclusion = False
        self.parts.append(value)


def _excluded_path(
    element: ET.Element,
    root: ET.Element,
    parents: dict[ET.Element, ET.Element],
) -> tuple[str, ...]:
    chain: list[str] = []
    current: ET.Element | None = parents.get(element)
    while current is not None:
        tag = _local_name(current.tag)
        if tag in EXCLUDED_ANCESTOR_TAGS:
            chain.append(tag)
        if current is root:
            break
        current = parents.get(current)
    return tuple(reversed(chain))


def _record_excluded_subtree(
    element: ET.Element,
    state: _ParagraphState,
    parents: dict[ET.Element, ET.Element],
) -> None:
    tag = _local_name(element.tag)
    state.direct_excluded[tag] += 1
    for descendant in element.iter():
        if descendant is element:
            continue
        path = _excluded_path(descendant, element, parents)
        state.ancestor_excluded[_local_name(descendant.tag)] += 1
        state.ancestor_paths[f"{_local_name(descendant.tag)}|{'>'.join(path)}"] += 1
    state.pending_exclusion = True


def _projected_content(element: ET.Element) -> str:
    """Return selected content without diagnostics, for choice boundary checks."""

    tag = _local_name(element.tag)
    if tag in EXCLUDED_TAGS or tag == "sic":
        return ""
    if tag == "choice":
        sic, corr = list(element)
        # Mirror _visit exactly: choice text and the sic tail remain in the
        # stream, while the sic element is replaced by the corr branch.
        value = element.text or ""
        value += sic.tail or ""
        value += _projected_content(corr)
        value += corr.tail or ""
        return value
    value = element.text or ""
    for child in list(element):
        value += _projected_content(child)
        value += child.tail or ""
    return value


def _source_content(element: ET.Element) -> str:
    """Return raw element content, excluding the element tail."""

    value = element.text or ""
    for child in list(element):
        value += _source_content(child)
        value += child.tail or ""
    return value


def _visit(
    element: ET.Element,
    state: _ParagraphState,
    parents: dict[ET.Element, ET.Element],
) -> None:
    tag = _local_name(element.tag)
    if tag in EXCLUDED_TAGS:
        _record_excluded_subtree(element, state, parents)
        return
    if tag == "choice":
        state.actual_retained[tag] += 1
        state.append(element.text)
        sic, corr = list(element)
        before = state.pending_exclusion
        correction_has_content = _first_non_xml_whitespace(
            _projected_content(corr)
        ) is not None
        sic_has_content = _first_non_xml_whitespace(_source_content(sic)) is not None
        _record_excluded_subtree(sic, state, parents)
        state.pending_exclusion = (
            sic_has_content and not correction_has_content
        ) or before
        state.append(sic.tail)
        # The correction replaces the excluded sic branch.  A non-empty
        # correction therefore supplies the next retained segment directly.
        _visit(corr, state, parents)
        state.append(corr.tail)
        return

    state.actual_retained[tag] += 1
    state.append(element.text)
    for child in list(element):
        _visit(child, state, parents)
        state.append(child.tail)


def _counter_dict(counter: Counter[str]) -> dict[str, int]:
    return dict(sorted(counter.items()))


def _selected_counts(paragraphs: tuple[ET.Element, ...]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for paragraph in paragraphs:
        counts.update(_local_name(element.tag) for element in paragraph.iter())
    return _counter_dict(counts)


def project_tei(
    source: bytes | str,
    *,
    empty_policy: str = "include",
) -> ProjectionResult:
    """Project synthetic TEI paragraphs under the fixed Celsus rules.

    ``empty_policy`` is ``include`` or ``drop``.  Both policies report the
    source count and the number of empty projected paragraphs.
    """

    if empty_policy not in {"include", "drop"}:
        raise ValueError("empty_policy must be 'include' or 'drop'")
    root = _parse_xml(source)
    text_elements = [child for child in list(root) if child.tag == _qname("text")]
    if len(text_elements) != 1:
        raise ProjectionError("TEI must have exactly one direct text element")
    body_elements = [child for child in list(text_elements[0]) if child.tag == _qname("body")]
    if len(body_elements) != 1:
        raise ProjectionError("text must have exactly one direct body element")
    body = body_elements[0]
    chapter_info, source_paragraphs, parents = _validate_body(body)
    source_counts = _counter_dict(Counter(_local_name(element.tag) for element in body.iter()))
    selected_counts = _selected_counts(source_paragraphs)
    source_book_ids = sorted(
        {
            element.get("n")
            for element in body.iter()
            if _local_name(element.tag) == "div"
            and element.get("subtype") == "book"
            and element.get("n") is not None
        }
    )

    ordinals: Counter[str] = Counter()
    projected: list[ProjectedParagraph] = []
    actual_retained: Counter[str] = Counter()
    direct_excluded: Counter[str] = Counter()
    ancestor_excluded: Counter[str] = Counter()
    ancestor_paths: Counter[str] = Counter()
    empty_count = 0
    for paragraph in source_paragraphs:
        ancestors = _ancestors(paragraph, parents)
        chapter = next(
            ancestor
            for ancestor in ancestors
            if _local_name(ancestor.tag) == "div"
            and ancestor.get("subtype") == "chapter"
        )
        book_id, chapter_id, chapter_key = chapter_info[chapter]
        ordinals[chapter_key] += 1
        state = _ParagraphState()
        _visit(paragraph, state, parents)
        value = _collapse_xml_whitespace(state.raw_text)
        if not value:
            empty_count += 1
        actual_retained.update(state.actual_retained)
        direct_excluded.update(state.direct_excluded)
        ancestor_excluded.update(state.ancestor_excluded)
        ancestor_paths.update(state.ancestor_paths)
        record = ProjectedParagraph(
            book_id=book_id,
            chapter_id=chapter_id,
            chapter_key=chapter_key,
            local_paragraph_ordinal=ordinals[chapter_key],
            text=value,
        )
        if empty_policy == "include" or value:
            projected.append(record)

    report = {
        "empty_projected_paragraph_policy": empty_policy,
        "source_paragraph_count": len(source_paragraphs),
        "projected_paragraph_count": len(projected),
        "empty_projected_paragraph_count": empty_count,
        "dropped_empty_paragraph_count": (
            empty_count if empty_policy == "drop" else 0
        ),
        "book_ids": source_book_ids,
        "chapter_keys": sorted({info[2] for info in chapter_info.values()}),
        "source_counts": source_counts,
        "selected_subtree_counts": selected_counts,
        "actual_retained": _counter_dict(actual_retained),
        "direct_excluded": _counter_dict(direct_excluded),
        "ancestor_excluded": {
            "by_tag": _counter_dict(ancestor_excluded),
            "by_path": dict(sorted(ancestor_paths.items())),
        },
    }
    return ProjectionResult(tuple(projected), report)


__all__ = [
    "BODY_TAGS",
    "ProjectionError",
    "ProjectionResult",
    "ProjectedParagraph",
    "TEI_NS",
    "XML_NS",
    "project_tei",
]
