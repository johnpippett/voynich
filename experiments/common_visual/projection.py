"""Project accepted parser words onto source characters and visual units."""

from copy import deepcopy
import re

from experiments.homophonic.units import tokenize_word


_BASIC_WORD_RE = re.compile(r"[a-z]+\Z")
_TEXT_TAG_RE = re.compile(r"<@([A-Z])=([A-Za-z0-9@])>")
_HIGH_ASCII_RE = re.compile(r"@[0-9]{3};")
_MARKUP_CHARS = frozenset(":;|()\"`#/=+*&!}%$>")


def _validate_fragment(value):
    """Make sure that a source-text fragment has valid syntax."""
    index = 0
    while index < len(value):
        char = value[index]
        if char.isalpha() and char.isascii():
            index += 1
            continue
        if char in "'?":
            index += 1
            continue
        if char == "{":
            end = value.find("}", index + 1)
            if end < 0 or not value[index + 1:end]:
                raise ValueError("Malformed ligature in IVTFF construct.")
            _validate_fragment(value[index + 1:end])
            index = end + 1
            continue
        if char == "}":
            raise ValueError("Unmatched ligature end in IVTFF construct.")
        match = _HIGH_ASCII_RE.match(value, index)
        if match:
            code = int(match.group()[1:-1])
            if not 128 <= code <= 255:
                raise ValueError("High-ASCII code is outside 128..255.")
            index = match.end()
            continue
        raise ValueError("Unexpected character in IVTFF construct.")


def _source_words(text_raw):
    """Return accepted source characters grouped by parser word."""
    words = []
    current = []
    text_tags = {}

    def finish():
        nonlocal current
        if current:
            words.append(current)
            current = []

    index = 0
    while index < len(text_raw):
        char = text_raw[index]

        if char.isspace():
            index += 1
            continue
        if char in ".,":
            finish()
            index += 1
            continue
        if char == "<":
            end = text_raw.find(">", index + 1)
            if end < 0:
                raise ValueError("Unclosed IVTFF inline control.")
            body = text_raw[index + 1:end]
            if body in {"-", "~"}:
                finish()
            elif body in {"%", "$"} or body.startswith("!"):
                pass
            elif body.startswith("@"):
                match = _TEXT_TAG_RE.fullmatch(text_raw[index:end + 1])
                if match is None:
                    raise ValueError("Malformed IVTFF text tag.")
                key, value = match.groups()
                if key in text_tags and text_tags[key] != value:
                    raise ValueError("An IVTFF text tag changes twice in one record.")
                text_tags[key] = value
            else:
                raise ValueError("Unsupported IVTFF inline control.")
            index = end + 1
            continue
        if char == "[":
            end = text_raw.find("]", index + 1)
            if end < 0:
                raise ValueError("Unclosed uncertain reading.")
            body = text_raw[index + 1:end]
            if ":" not in body or any(mark in body for mark in "[]<>"):
                raise ValueError("Malformed uncertain reading.")
            for alternative in body.split(":"):
                if alternative:
                    _validate_fragment(alternative)
            raise ValueError("An accepted record cannot contain an uncertain reading.")
        if char == "{":
            end = text_raw.find("}", index + 1)
            if end < 0:
                raise ValueError("Unclosed ligature.")
            body = text_raw[index + 1:end]
            if not body:
                raise ValueError("Empty ligature.")
            _validate_fragment(body)
            if not all(item.isalpha() and item.isascii() for item in body):
                raise ValueError("A ligature does not form accepted Basic EVA text.")
            for offset, original in enumerate(body, start=index + 1):
                current.append({
                    "normalized": original.lower(),
                    "original": original,
                    "position": offset,
                })
            index = end + 1
            continue
        if char == "@":
            match = _HIGH_ASCII_RE.match(text_raw, index)
            if match is None:
                raise ValueError("Malformed high-ASCII code.")
            code = int(match.group()[1:-1])
            if not 128 <= code <= 255:
                raise ValueError("High-ASCII code is outside 128..255.")
            raise ValueError("An accepted record cannot contain a high-ASCII code.")
        if char in "?'":
            raise ValueError("An accepted record cannot contain uncertain text.")
        if char.isalpha() and char.isascii():
            current.append({
                "normalized": char.lower(),
                "original": char,
                "position": index,
            })
            index += 1
            continue
        if char in _MARKUP_CHARS:
            raise ValueError("Unsupported IVTFF text markup.")
        raise ValueError("An accepted record cannot contain excluded text.")

    finish()
    return words


def _eligible_record(record):
    """Examine the fields that define an accepted parser record."""
    if not isinstance(record, dict):
        raise TypeError("record must be a parser record dictionary")
    text_raw = record.get("text_raw")
    tokens = record.get("tokens")
    if not isinstance(text_raw, str):
        raise ValueError("record text_raw must be a string")
    if not isinstance(tokens, (list, tuple)):
        raise ValueError("record tokens must be a word sequence")
    if not tokens:
        raise ValueError("An empty parser record is not eligible")
    if not isinstance(record.get("kind"), str) or not record["kind"].startswith("P"):
        raise ValueError("A non-paragraph parser record is not eligible")
    if record.get("excluded_tokens") != 0:
        raise ValueError("A parser record with excluded tokens is not eligible")
    if any(not isinstance(token, str) or _BASIC_WORD_RE.fullmatch(token) is None
           for token in tokens):
        raise ValueError("Parser tokens must be lowercase Basic EVA words")
    return text_raw, list(tokens)


def project_record(record):
    """Project one eligible parser record onto its source characters."""
    text_raw, tokens = _eligible_record(record)
    source_words = _source_words(text_raw)
    projected_tokens = [
        "".join(char["normalized"] for char in characters)
        for characters in source_words
    ]
    if projected_tokens != tokens:
        raise ValueError("Source projection does not match parser tokens")

    words = []
    for normalized_word, characters in zip(tokens, source_words, strict=True):
        units = []
        for span in tokenize_word(normalized_word, representation="visual"):
            selected = characters[span.start:span.end]
            units.append({
                "label": span.unit,
                "positions": [char["position"] for char in selected],
                "original": "".join(char["original"] for char in selected),
            })

        flattened = [position for unit in units for position in unit["positions"]]
        positions = [char["position"] for char in characters]
        if flattened != positions:
            raise ValueError("Visual units do not cover the source word in order")
        if "".join(unit["label"] for unit in units) != normalized_word:
            raise ValueError("Visual units do not reconstruct the parser word")

        words.append({
            "normalized_word": normalized_word,
            "characters": characters,
            "units": units,
        })

    return {
        "record": deepcopy(record),
        "text_raw": text_raw,
        "tokens": projected_tokens,
        "words": words,
    }


__all__ = ["project_record"]
