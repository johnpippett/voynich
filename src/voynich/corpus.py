"""Parse original Voynich IVTFF transliteration files.

The parser keeps the IVTFF text controls in ``text_raw``.  It emits only
basic lower-case EVA words in ``tokens``.  A word with an uncertain reading,
an unreadable character, a high-ASCII code, an apostrophe, or another rare
construct is excluded and counted.  This gives downstream analysis a small,
explicit token universe without changing the source text.
"""

from __future__ import annotations

from pathlib import Path
import re


_HEADER_RE = re.compile(
    r"^#=(?:IVTFF|VDBTF)\s+(?P<alphabet>\S+)\s+"
)
_PAGE_RE = re.compile(
    r"^<(?P<folio>[A-Za-z][A-Za-z0-9]*)>(?:\s*<!\s*(?P<variables>[^>]*)>)?\s*$"
)
_LOCUS_RE = re.compile(
    r"^<(?P<folio>[A-Za-z][A-Za-z0-9]*)\.(?P<number>\d+),"
    r"(?P<locator>[@+*=&~/!])(?P<kind>[PLCR][a-z0-9])"
    r"(?:;(?P<transcriber>[A-Za-z0-9]))?>\s*(?P<text>.*)$"
)
_ALT_LOCUS_RE = re.compile(r"^<[A-Z]{2}\d{3}(?:;[A-Za-z0-9])?>")
_PAGE_VARIABLE_RE = re.compile(r"\$([A-Z])=([A-Za-z0-9@])")
_TEXT_TAG_RE = re.compile(r"<@([A-Z])=([A-Za-z0-9@])>")
_HIGH_ASCII_RE = re.compile(r"@[0-9]{3};")
_BASIC_EVA_RE = re.compile(r"^[a-z]+$")
_KNOWN_SOURCE_IDS = ("ZL", "IT", "TT", "GC", "CD", "FG", "RF")


def parse_ivtff(path: str | Path, uncertain_spaces: str = "split") -> list[dict]:
    """Parse one IVTFF file into independent locus records.

    ``uncertain_spaces='split'`` treats a comma as a token boundary.  The
    ``'join'`` mode joins text on both sides of a comma for sensitivity runs.
    In both modes ``text_raw`` remains unchanged.  The parser never combines
    loci or transcribers.

    The returned records have these keys: ``folio``, ``locus``, ``kind``,
    ``transcriber``, ``text_raw``, ``tokens``, ``metadata``,
    ``excluded_tokens``, ``paragraph_start``, and ``paragraph_end``.
    """

    if uncertain_spaces not in {"split", "join"}:
        raise ValueError("uncertain_spaces must be 'split' or 'join'")

    source_path = Path(path)
    try:
        source_text = source_path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"{source_path} is not valid UTF-8") from exc

    lines = source_text.splitlines()
    if not lines:
        raise ValueError(f"{source_path} is empty")
    header_match = _HEADER_RE.match(lines[0])
    if not header_match:
        raise ValueError(f"{source_path}: first line is not an IVTFF header")
    if header_match.group("alphabet") not in {"Eva-", "EvaT"}:
        raise ValueError(
            f"{source_path}: unsupported transliteration alphabet "
            f"{header_match.group('alphabet')!r}; expected Eva- or EvaT"
        )

    source_id = _source_id_for_path(source_path)
    records: list[dict] = []
    page_metadata: dict[str, str] = {}
    text_tags: dict[str, str] = {}
    current_page: str | None = None
    line_index = 1

    while line_index < len(lines):
        line = lines[line_index]
        line_number = line_index + 1

        if not line.strip():
            line_index += 1
            continue
        if line.startswith("#"):
            line_index += 1
            continue
        if line.startswith("/"):
            raise ValueError(f"{source_path}:{line_number}: unexpected continuation line")

        page_match = _PAGE_RE.match(line)
        if page_match:
            current_page = page_match.group("folio")
            page_metadata = _parse_page_variables(
                page_match.group("variables") or "", source_path, line_number
            )
            text_tags = {}
            line_index += 1
            continue

        locus_match = _LOCUS_RE.match(line)
        if not locus_match:
            if _ALT_LOCUS_RE.match(line):
                raise ValueError(
                    f"{source_path}:{line_number}: alternative locus identifiers do not include a kind"
                )
            raise ValueError(f"{source_path}:{line_number}: unexpected IVTFF line")

        logical_text, next_index = _read_logical_locus_text(
            lines, line_index, locus_match.group("text"), source_path
        )
        folio = locus_match.group("folio")
        if current_page is not None and folio != current_page:
            raise ValueError(
                f"{source_path}:{line_number}: locus page {folio!r} differs from {current_page!r}"
            )

        line_tags = _find_text_tags(logical_text, source_path, line_number)
        for key, value in line_tags.items():
            text_tags[key] = value

        metadata = dict(page_metadata)
        metadata.update(text_tags)
        tokens, excluded = _extract_tokens(
            logical_text, uncertain_spaces, source_path, line_number
        )
        paragraph_start, paragraph_end = _paragraph_flags(logical_text)
        records.append(
            {
                "folio": folio,
                "locus": _locus_without_brackets(locus_match),
                "kind": locus_match.group("kind"),
                "transcriber": locus_match.group("transcriber") or source_id,
                "text_raw": logical_text,
                "tokens": tokens,
                "metadata": metadata,
                "excluded_tokens": excluded,
                "paragraph_start": paragraph_start,
                "paragraph_end": paragraph_end,
            }
        )
        line_index = next_index

    return records


def _source_id_for_path(path: Path) -> str | None:
    stem = path.stem.upper()
    for source_id in _KNOWN_SOURCE_IDS:
        if (
            stem == source_id
            or stem.startswith(source_id + "-")
            or stem.startswith(source_id + "_")
            or (stem.startswith(source_id) and len(stem) > len(source_id) and stem[len(source_id)].isdigit())
        ):
            return source_id
    return None


def _locus_without_brackets(match: re.Match[str]) -> str:
    """Return the exact locus body, including locator and optional ID."""

    value = (
        f"{match.group('folio')}.{match.group('number')},"
        f"{match.group('locator')}{match.group('kind')}"
    )
    if match.group("transcriber"):
        value += ";" + match.group("transcriber")
    return value


def _parse_page_variables(value: str, path: Path, line_number: int) -> dict[str, str]:
    """Parse the dedicated ``$X=y`` variables in a page header."""

    variables: dict[str, str] = {}
    cursor = 0
    for match in _PAGE_VARIABLE_RE.finditer(value):
        if value[cursor : match.start()].strip():
            raise ValueError(f"{path}:{line_number}: unexpected page-header markup")
        key, item = match.groups()
        if key in variables:
            raise ValueError(f"{path}:{line_number}: duplicate page variable ${key}")
        variables[key] = item
        cursor = match.end()
    if value[cursor:].strip():
        raise ValueError(f"{path}:{line_number}: unexpected page-header markup")
    return variables


def _find_text_tags(value: str, path: Path, line_number: int) -> dict[str, str]:
    """Read text tags before token extraction and reject duplicate settings."""

    tags: dict[str, str] = {}
    for match in _TEXT_TAG_RE.finditer(value):
        key, item = match.groups()
        if key in tags and tags[key] != item:
            raise ValueError(f"{path}:{line_number}: text tag @{key} changes twice on one line")
        tags[key] = item
    return tags


def _read_logical_locus_text(
    lines: list[str],
    line_index: int,
    first_text: str,
    path: Path,
) -> tuple[str, int]:
    """Join IVTFF slash-wrapped text and return the next unread line index."""

    parts: list[str] = []
    text = first_text
    index = line_index
    while True:
        stripped = text.rstrip()
        wrapped = stripped.endswith("/")
        if wrapped:
            stripped = stripped[:-1].rstrip()
        parts.append(stripped.strip())
        if not wrapped:
            return "".join(parts), index + 1

        index += 1
        if index >= len(lines) or not lines[index].startswith("/"):
            raise ValueError(f"{path}:{index + 1}: missing IVTFF continuation line")
        text = lines[index][1:]


def _extract_tokens(
    value: str,
    uncertain_spaces: str,
    path: Path,
    line_number: int,
) -> tuple[list[str], int]:
    """Extract basic EVA words while validating IVTFF controls."""

    tokens: list[str] = []
    excluded = 0
    current: list[str] = []
    invalid = False
    seen = False
    index = 0

    def finish() -> None:
        nonlocal excluded, current, invalid, seen
        if not seen:
            current = []
            invalid = False
            return
        candidate = "".join(current)
        if not invalid and _BASIC_EVA_RE.fullmatch(candidate):
            tokens.append(candidate)
        else:
            excluded += 1
        current = []
        invalid = False
        seen = False

    while index < len(value):
        char = value[index]

        if char.isspace():
            # IVTFF whitespace is layout only.  Periods and commas define
            # token boundaries, even when spaces appear around them.
            index += 1
            continue
        if char in ".,":
            if char == "," and uncertain_spaces == "join":
                index += 1
                continue
            finish()
            index += 1
            continue
        if char == "<":
            end = value.find(">", index + 1)
            if end < 0:
                raise ValueError(f"{path}:{line_number}: unclosed IVTFF inline comment")
            body = value[index + 1 : end]
            if body in {"-", "~"}:
                finish()
            elif body in {"%", "$"}:
                # Paragraph markers carry structure, not token text.
                pass
            elif body.startswith("!"):
                pass
            elif body.startswith("@"):
                if not _TEXT_TAG_RE.fullmatch(value[index : end + 1]):
                    raise ValueError(f"{path}:{line_number}: malformed text tag")
            else:
                raise ValueError(f"{path}:{line_number}: unexpected inline comment <{body}>")
            index = end + 1
            continue
        if char == "[":
            end = value.find("]", index + 1)
            if end < 0:
                raise ValueError(f"{path}:{line_number}: unclosed uncertain reading")
            body = value[index + 1 : end]
            if ":" not in body or any(mark in body for mark in "[]<>"):
                raise ValueError(f"{path}:{line_number}: malformed uncertain reading")
            alternatives = body.split(":")
            for alternative in alternatives:
                if alternative:
                    _validate_eva_fragment(alternative, path, line_number)
            invalid = True
            seen = True
            index = end + 1
            continue
        if char == "{":
            end = value.find("}", index + 1)
            if end < 0:
                raise ValueError(f"{path}:{line_number}: unclosed ligature")
            body = value[index + 1 : end]
            if not body:
                raise ValueError(f"{path}:{line_number}: empty ligature")
            _validate_eva_fragment(body, path, line_number)
            if _HIGH_ASCII_RE.search(body) or "'" in body:
                invalid = True
            else:
                current.append(body.lower())
            seen = True
            index = end + 1
            continue
        if char == "@":
            match = _HIGH_ASCII_RE.match(value, index)
            if not match:
                raise ValueError(f"{path}:{line_number}: malformed high-ASCII code")
            code = int(match.group()[1:-1])
            if not 128 <= code <= 255:
                raise ValueError(f"{path}:{line_number}: high-ASCII code is outside 128..255")
            invalid = True
            seen = True
            index = match.end()
            continue
        if char == "?":
            seen = True
            invalid = True
            index += 1
            while index < len(value) and value[index] == "?":
                index += 1
            continue
        if char == "'":
            seen = True
            invalid = True
            index += 1
            continue
        if char.isalpha() and char.isascii():
            # Capitalised EVA marks a connected glyph.  Lower it for the
            # basic token stream; the original spelling remains in text_raw.
            current.append(char.lower())
            seen = True
            index += 1
            continue
        if char in ":;|()\"`#/=+*&!}%$>":
            raise ValueError(f"{path}:{line_number}: unexpected text markup {char!r}")

        # Digits and non-ASCII characters remain in the raw text but are
        # excluded from the conservative token stream.
        seen = True
        invalid = True
        index += 1

    finish()
    return tokens, excluded


def _paragraph_flags(value: str) -> tuple[bool, bool]:
    """Return dedicated paragraph marker flags, excluding free comments."""

    starts = ends = False
    index = 0
    while index < len(value):
        if value[index] != "<":
            index += 1
            continue
        closing = value.find(">", index + 1)
        if closing < 0:
            break
        body = value[index + 1 : closing]
        if body == "%":
            starts = True
        elif body == "$":
            ends = True
        index = closing + 1
    return starts, ends


def _validate_eva_fragment(value: str, path: Path, line_number: int) -> None:
    """Validate the contents of a bracket or ligature construct."""

    index = 0
    while index < len(value):
        char = value[index]
        if char.isalpha() and char.isascii():
            index += 1
            continue
        if char == "'":
            index += 1
            continue
        if char == "{":
            end = value.find("}", index + 1)
            if end < 0 or not value[index + 1 : end]:
                raise ValueError(f"{path}:{line_number}: malformed ligature in IVTFF construct")
            _validate_eva_fragment(value[index + 1 : end], path, line_number)
            index = end + 1
            continue
        if char == "}":
            raise ValueError(f"{path}:{line_number}: unmatched ligature end")
        match = _HIGH_ASCII_RE.match(value, index)
        if match:
            code = int(match.group()[1:-1])
            if not 128 <= code <= 255:
                raise ValueError(f"{path}:{line_number}: high-ASCII code is outside 128..255")
            index = match.end()
            continue
        if char == "?":
            index += 1
            continue
        raise ValueError(f"{path}:{line_number}: unexpected character in IVTFF construct {char!r}")


__all__ = ["parse_ivtff"]
