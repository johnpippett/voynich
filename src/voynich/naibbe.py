"""Fixed-table Naibbe encoding and complete token candidate enumeration.

This module implements a small, deterministic research oracle. It keeps every
plaintext and table choice that the published table file permits. It does not
fit tables to the Voynich Manuscript or rank plaintext candidates.
"""

from __future__ import annotations

import csv
from collections import Counter, defaultdict
from dataclasses import dataclass
import hashlib
import random
from pathlib import Path
from types import MappingProxyType
import unicodedata
from typing import Iterable, Mapping, Sequence


TABLE_NAMES = ("alpha", "beta1", "beta2", "beta3", "gamma1", "gamma2")
STATES = ("unigram", "prefix", "suffix")
PUBLISHED_ALPHABET = tuple("abcdefghilmnopqrstuvxyz")

WEIGHTS_52 = (
    ("alpha", 20),
    ("beta1", 8),
    ("beta2", 8),
    ("beta3", 8),
    ("gamma1", 4),
    ("gamma2", 4),
)
WEIGHTS_78 = (
    ("alpha", 28),
    ("beta1", 14),
    ("beta2", 11),
    ("beta3", 11),
    ("gamma1", 7),
    ("gamma2", 7),
)


def sha256_file(path: str | Path) -> str:
    """Return the SHA-256 digest of one file."""

    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@dataclass(frozen=True)
class TableChoice:
    """One table and letter entry in a reverse lookup."""

    table: str
    letter: str


@dataclass(frozen=True)
class DecodeCandidate:
    """One complete token reading, including its latent table choice.

    ``table_choices`` has one item for a unigram and two items for a bigram.
    ``split`` is the character offset between a prefix and suffix. It is
    ``None`` for a unigram.
    """

    plaintext: str
    state: str
    table_choices: tuple[str, ...]
    split: int | None


@dataclass(frozen=True)
class TokenCandidates:
    """All fixed-table readings for one emitted token."""

    token: str
    candidates: tuple[DecodeCandidate, ...]

    @property
    def no_parse(self) -> bool:
        return not self.candidates

    @property
    def plaintexts(self) -> tuple[str, ...]:
        return tuple(sorted({candidate.plaintext for candidate in self.candidates}))

    @property
    def plaintext_ambiguity(self) -> bool:
        """True when at least two different plaintext strings are possible."""

        return len(self.plaintexts) > 1

    @property
    def same_plaintext_ambiguity(self) -> bool:
        """True when one plaintext has more than one complete reading."""

        grouped: dict[str, set[tuple[str, tuple[str, ...], int | None]]]
        grouped = defaultdict(set)
        for candidate in self.candidates:
            grouped[candidate.plaintext].add(
                (candidate.state, candidate.table_choices, candidate.split)
            )
        return any(len(readings) > 1 for readings in grouped.values())

    @property
    def latent_table_choice_ambiguity(self) -> bool:
        """True when one plaintext has more than one table choice."""

        grouped: dict[str, set[tuple[str, ...]]] = defaultdict(set)
        for candidate in self.candidates:
            grouped[candidate.plaintext].add(candidate.table_choices)
        return any(len(choices) > 1 for choices in grouped.values())

    def by_plaintext(self) -> dict[str, tuple[DecodeCandidate, ...]]:
        """Group candidates by plaintext without discarding table choices."""

        grouped: dict[str, list[DecodeCandidate]] = defaultdict(list)
        for candidate in self.candidates:
            grouped[candidate.plaintext].append(candidate)
        return {
            plaintext: tuple(values)
            for plaintext, values in sorted(grouped.items())
        }

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable summary without raw source context."""

        return {
            "token": self.token,
            "candidate_count": len(self.candidates),
            "plaintext_count": len(self.plaintexts),
            "no_parse": self.no_parse,
            "plaintext_ambiguity": self.plaintext_ambiguity,
            "same_plaintext_ambiguity": self.same_plaintext_ambiguity,
            "latent_table_choice_ambiguity": self.latent_table_choice_ambiguity,
            "candidates": [
                {
                    "plaintext": candidate.plaintext,
                    "state": candidate.state,
                    "table_choices": list(candidate.table_choices),
                    "split": candidate.split,
                }
                for candidate in self.candidates
            ],
        }


@dataclass(frozen=True)
class TableBook:
    """A validated Naibbe table set and its reverse indexes."""

    alphabet: tuple[str, ...]
    glyphs: Mapping[tuple[str, str, str], str]
    reverse: Mapping[str, Mapping[str, tuple[TableChoice, ...]]]
    unigram_glyphs: frozenset[str]
    bigram_catalog: Mapping[str, tuple[tuple[str, str, str, str], ...]]
    source_sha256: str | None = None

    def glyph(self, state: str, table: str, letter: str) -> str:
        """Return one validated forward mapping."""

        try:
            return self.glyphs[(state, table, letter)]
        except KeyError as exc:
            raise ValueError(
                f"unknown Naibbe entry state={state!r}, table={table!r}, "
                f"letter={letter!r}"
            ) from exc

    def candidates(self, token: str) -> TokenCandidates:
        """Enumerate all unigram and bigram readings for ``token``."""

        if not isinstance(token, str):
            raise ValueError("token must be a string")

        candidates: set[DecodeCandidate] = set()
        for choice in self.reverse["unigram"].get(token, ()):
            candidates.add(
                DecodeCandidate(
                    plaintext=choice.letter,
                    state="unigram",
                    table_choices=(choice.table,),
                    split=None,
                )
            )

        for split in range(1, len(token)):
            prefixes = self.reverse["prefix"].get(token[:split], ())
            suffixes = self.reverse["suffix"].get(token[split:], ())
            for prefix in prefixes:
                for suffix in suffixes:
                    candidates.add(
                        DecodeCandidate(
                            plaintext=prefix.letter + suffix.letter,
                            state="bigram",
                            table_choices=(prefix.table, suffix.table),
                            split=split,
                        )
                    )

        ordered = tuple(sorted(candidates, key=_candidate_sort_key))
        return TokenCandidates(token=token, candidates=ordered)


def _candidate_sort_key(candidate: DecodeCandidate) -> tuple[object, ...]:
    state_order = 0 if candidate.state == "unigram" else 1
    split = -1 if candidate.split is None else candidate.split
    return (
        state_order,
        candidate.plaintext,
        candidate.table_choices,
        split,
    )


def _mapping_proxy(
    value: Mapping[str, Mapping[str, tuple[TableChoice, ...]]]
) -> Mapping[str, Mapping[str, tuple[TableChoice, ...]]]:
    return MappingProxyType(
        {
            state: MappingProxyType(dict(entries))
            for state, entries in value.items()
        }
    )


def _build_table_book(
    rows: Mapping[tuple[str, str, str], str],
    alphabet: tuple[str, ...],
    source_sha256: str | None,
) -> TableBook:
    reverse_lists: dict[str, dict[str, list[TableChoice]]] = {
        state: defaultdict(list) for state in STATES
    }
    for (state, table, letter), glyph in rows.items():
        reverse_lists[state][glyph].append(TableChoice(table=table, letter=letter))

    reverse = _mapping_proxy(
        {
            state: {
                glyph: tuple(sorted(choices, key=lambda item: (item.table, item.letter)))
                for glyph, choices in entries.items()
            }
            for state, entries in reverse_lists.items()
        }
    )

    unigram_glyphs = frozenset(reverse["unigram"])
    catalog: dict[str, set[tuple[str, str, str, str]]] = defaultdict(set)
    for prefix_table in TABLE_NAMES:
        for prefix_letter in alphabet:
            prefix = rows[("prefix", prefix_table, prefix_letter)]
            for suffix_table in TABLE_NAMES:
                for suffix_letter in alphabet:
                    suffix = rows[("suffix", suffix_table, suffix_letter)]
                    catalog[prefix + suffix].add(
                        (prefix_table, prefix_letter, suffix_table, suffix_letter)
                    )

    catalog_proxy = MappingProxyType(
        {
            token: tuple(sorted(choices))
            for token, choices in catalog.items()
        }
    )
    return TableBook(
        alphabet=alphabet,
        glyphs=MappingProxyType(dict(rows)),
        reverse=reverse,
        unigram_glyphs=unigram_glyphs,
        bigram_catalog=catalog_proxy,
        source_sha256=source_sha256,
    )


def load_table_csv(
    path: str | Path,
    *,
    alphabet: Sequence[str] = PUBLISHED_ALPHABET,
    expected_sha256: str | None = None,
) -> TableBook:
    """Load and validate a complete Naibbe CSV table set.

    The expected alphabet defaults to the 23-letter alphabet in the published
    CSV. Duplicate glyph strings are valid. Duplicate code rows, missing rows,
    unknown states or tables, and empty glyph strings are rejected.
    """

    source_path = Path(path)
    digest = sha256_file(source_path)
    if expected_sha256 is not None and digest.lower() != expected_sha256.lower():
        raise ValueError(
            f"table SHA-256 mismatch: expected {expected_sha256}, got {digest}"
        )

    expected_alphabet = tuple(alphabet)
    if not expected_alphabet or len(set(expected_alphabet)) != len(expected_alphabet):
        raise ValueError("alphabet must contain unique letters")
    if any(not isinstance(letter, str) or len(letter) != 1 for letter in expected_alphabet):
        raise ValueError("alphabet entries must be one-character strings")

    rows: dict[tuple[str, str, str], str] = {}
    with source_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != ["code", "glyphs"]:
            raise ValueError("table CSV must have exactly code,glyphs columns")
        for line_number, row in enumerate(reader, start=2):
            if row.get("code") is None or row.get("glyphs") is None:
                raise ValueError(f"table CSV line {line_number} has a missing value")
            code = row["code"]
            glyphs = row["glyphs"]
            parts = code.split("_")
            if len(parts) != 3:
                raise ValueError(f"invalid code on table CSV line {line_number}: {code!r}")
            state, table, letter = parts
            if state not in STATES or table not in TABLE_NAMES:
                raise ValueError(f"unknown state or table on line {line_number}: {code!r}")
            if letter not in expected_alphabet:
                raise ValueError(f"unknown alphabet letter on line {line_number}: {code!r}")
            if not glyphs or glyphs != glyphs.strip() or any(char.isspace() for char in glyphs):
                raise ValueError(f"empty or spaced glyph string on line {line_number}")
            key = (state, table, letter)
            if key in rows:
                raise ValueError(f"duplicate code on table CSV line {line_number}: {code!r}")
            rows[key] = glyphs

    expected_keys = {
        (state, table, letter)
        for state in STATES
        for table in TABLE_NAMES
        for letter in expected_alphabet
    }
    actual_keys = set(rows)
    missing = sorted(expected_keys - actual_keys)
    extra = sorted(actual_keys - expected_keys)
    if missing or extra or len(rows) != len(expected_keys):
        detail = []
        if missing:
            detail.append(f"missing {missing[:3]!r}")
        if extra:
            detail.append(f"extra {extra[:3]!r}")
        raise ValueError("incomplete table CSV: " + "; ".join(detail))

    return _build_table_book(rows, expected_alphabet, digest)


@dataclass(frozen=True)
class ForwardConfig:
    """Explicit parameters for the deterministic forward oracle."""

    weights: tuple[tuple[str, int], ...] = WEIGHTS_52
    respacing_numerator: int = 17
    respacing_denominator: int = 36
    collision_policy: str = "unigram"
    max_retries: int = 10_000
    normalize: bool = True

    def __post_init__(self) -> None:
        names = [name for name, _ in self.weights]
        if tuple(names) != TABLE_NAMES or len(set(names)) != len(names):
            raise ValueError("weights must list each Naibbe table once in table order")
        if any(
            isinstance(count, bool) or not isinstance(count, int) or count <= 0
            for _, count in self.weights
        ):
            raise ValueError("deck weights must be positive integers")
        if isinstance(self.respacing_numerator, bool) or not isinstance(
            self.respacing_numerator, int
        ):
            raise ValueError("respacing_numerator must be an integer")
        if isinstance(self.respacing_denominator, bool) or not isinstance(
            self.respacing_denominator, int
        ):
            raise ValueError("respacing_denominator must be an integer")
        if not 0 <= self.respacing_numerator <= self.respacing_denominator:
            raise ValueError("respacing numerator must be between zero and denominator")
        if self.respacing_denominator <= 0:
            raise ValueError("respacing denominator must be positive")
        if self.collision_policy not in {"none", "unigram", "full"}:
            raise ValueError("collision_policy must be none, unigram, or full")
        if isinstance(self.max_retries, bool) or not isinstance(self.max_retries, int):
            raise ValueError("max_retries must be an integer")
        if self.max_retries <= 0:
            raise ValueError("max_retries must be positive")

    @property
    def deck_size(self) -> int:
        return sum(count for _, count in self.weights)

    def to_dict(self) -> dict[str, object]:
        """Return the fixed oracle configuration as JSON data."""

        return {
            "weights": {name: count for name, count in self.weights},
            "deck_size": self.deck_size,
            "respacing_numerator": self.respacing_numerator,
            "respacing_denominator": self.respacing_denominator,
            "collision_policy": self.collision_policy,
            "max_retries": self.max_retries,
            "normalize": self.normalize,
        }


@dataclass(frozen=True)
class ForwardEmission:
    """One oracle output token and the state that generated it."""

    plaintext_unit: str
    token: str
    state: str
    table_choices: tuple[str, ...]


@dataclass(frozen=True)
class ForwardResult:
    """A complete deterministic forward-oracle result."""

    seed: int
    normalized_text: str
    units: tuple[str, ...]
    emissions: tuple[ForwardEmission, ...]
    config: ForwardConfig

    @property
    def tokens(self) -> tuple[str, ...]:
        return tuple(emission.token for emission in self.emissions)

    def to_dict(self) -> dict[str, object]:
        """Return an auditable result without hidden random state."""

        return {
            "seed": self.seed,
            "normalized_text": self.normalized_text,
            "units": list(self.units),
            "tokens": list(self.tokens),
            "emissions": [
                {
                    "plaintext_unit": emission.plaintext_unit,
                    "token": emission.token,
                    "state": emission.state,
                    "table_choices": list(emission.table_choices),
                }
                for emission in self.emissions
            ],
            "config": self.config.to_dict(),
        }


def normalize_plaintext(text: str) -> str:
    """Apply the published Python implementation's plaintext normalization."""

    if not isinstance(text, str):
        raise ValueError("plaintext must be a string")
    normalized = unicodedata.normalize("NFD", text)
    no_diacritics = "".join(
        char for char in normalized if unicodedata.category(char) != "Mn"
    )
    replacements = {
        "æ": "ae",
        "Æ": "ae",
        "œ": "oe",
        "Œ": "oe",
        "ð": "d",
        "Ð": "d",
        "þ": "th",
        "Þ": "th",
        "ł": "l",
        "Ł": "l",
        "ß": "ss",
        "ø": "o",
        "Ø": "o",
    }
    replaced = "".join(replacements.get(char, char) for char in no_diacritics)
    cleaned = "".join(char for char in replaced if char.isalpha()).upper()
    cleaned = cleaned.replace("W", "UU").replace("J", "I").replace("K", "C")
    return cleaned.lower()


def respace_plaintext(
    text: str,
    rng: random.Random,
    *,
    numerator: int = 17,
    denominator: int = 36,
) -> tuple[str, ...]:
    """Split text into one- and two-letter units with an explicit RNG."""

    if not isinstance(text, str):
        raise ValueError("text must be a string")
    if isinstance(numerator, bool) or isinstance(denominator, bool):
        raise ValueError("respacing values must be integers")
    if not isinstance(numerator, int) or not isinstance(denominator, int):
        raise ValueError("respacing values must be integers")
    if denominator <= 0 or not 0 <= numerator <= denominator:
        raise ValueError("invalid respacing probability")

    text = text.lower().replace(" ", "")
    index = 0
    units: list[str] = []
    while index < len(text):
        if index == len(text) - 1 or rng.random() < numerator / denominator:
            units.append(text[index])
            index += 1
        else:
            units.append(text[index : index + 2])
            index += 2
    return tuple(units)


def _validate_seed(seed: int) -> None:
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")


def _new_deck(config: ForwardConfig, rng: random.Random) -> list[str]:
    deck = [table for table, count in config.weights for _ in range(count)]
    rng.shuffle(deck)
    return deck


def _encrypt_normalized(
    normalized_text: str,
    book: TableBook,
    config: ForwardConfig,
    rng: random.Random,
) -> tuple[tuple[str, ...], tuple[ForwardEmission, ...]]:
    units = respace_plaintext(
        normalized_text,
        rng,
        numerator=config.respacing_numerator,
        denominator=config.respacing_denominator,
    )
    deck = _new_deck(config, rng)
    deck_index = 0

    def draw_table() -> str:
        nonlocal deck, deck_index
        if deck_index >= len(deck):
            deck = _new_deck(config, rng)
            deck_index = 0
        table = deck[deck_index]
        deck_index += 1
        return table

    emissions: list[ForwardEmission] = []
    for unit in units:
        if len(unit) == 1:
            table = draw_table()
            emissions.append(
                ForwardEmission(
                    plaintext_unit=unit,
                    token=book.glyph("unigram", table, unit),
                    state="unigram",
                    table_choices=(table,),
                )
            )
            continue

        accepted = False
        token = ""
        table_choices: tuple[str, ...] = ()
        for _ in range(config.max_retries):
            prefix_table = draw_table()
            suffix_table = draw_table()
            token = book.glyph("prefix", prefix_table, unit[0]) + book.glyph(
                "suffix", suffix_table, unit[1]
            )
            table_choices = (prefix_table, suffix_table)
            if config.collision_policy == "none":
                accepted = True
            elif config.collision_policy == "unigram":
                accepted = token not in book.unigram_glyphs
            else:
                accepted = (
                    token not in book.unigram_glyphs
                    and len(book.bigram_catalog.get(token, ())) == 1
                )
            if accepted:
                break
        if not accepted:
            raise ValueError(
                f"could not select an unambiguous encoding for plaintext unit {unit!r}"
            )
        emissions.append(
            ForwardEmission(
                plaintext_unit=unit,
                token=token,
                state="bigram",
                table_choices=table_choices,
            )
        )
    return units, tuple(emissions)


def encrypt_fixed(
    plaintext: str,
    book: TableBook,
    *,
    config: ForwardConfig | None = None,
    seed: int = 0,
) -> ForwardResult:
    """Encrypt one normalized line with a fixed seed and configuration.

    The result includes the respaced units and the table choices. This makes it
    suitable for positive controls. It does not remove output spaces.
    """

    _validate_seed(seed)
    if config is None:
        config = ForwardConfig()
    if not isinstance(plaintext, str):
        raise ValueError("plaintext must be a string")
    normalized = (
        normalize_plaintext(plaintext)
        if config.normalize
        else plaintext.lower().replace(" ", "")
    )
    unknown = sorted(set(normalized) - set(book.alphabet))
    if unknown:
        raise ValueError(f"plaintext contains letters outside the table alphabet: {unknown}")
    units, emissions = _encrypt_normalized(normalized, book, config, random.Random(seed))
    return ForwardResult(
        seed=seed,
        normalized_text=normalized,
        units=units,
        emissions=emissions,
        config=config,
    )


def encrypt_lines(
    lines: Iterable[str],
    book: TableBook,
    *,
    config: ForwardConfig | None = None,
    seed: int = 0,
) -> tuple[ForwardResult, ...]:
    """Encrypt lines with a new deck for each line and one seeded RNG stream."""

    _validate_seed(seed)
    if config is None:
        config = ForwardConfig()
    rng = random.Random(seed)
    results: list[ForwardResult] = []
    for line in lines:
        if not isinstance(line, str):
            raise ValueError("each plaintext line must be a string")
        normalized = (
            normalize_plaintext(line)
            if config.normalize
            else line.lower().replace(" ", "")
        )
        unknown = sorted(set(normalized) - set(book.alphabet))
        if unknown:
            raise ValueError(
                f"plaintext contains letters outside the table alphabet: {unknown}"
            )
        units, emissions = _encrypt_normalized(normalized, book, config, rng)
        results.append(
            ForwardResult(
                seed=seed,
                normalized_text=normalized,
                units=units,
                emissions=emissions,
                config=config,
            )
        )
    return tuple(results)


def compatibility_aggregate(
    tokens: Iterable[str],
    book: TableBook,
) -> dict[str, int | float]:
    """Return aggregate fixed-table compatibility counts.

    The result contains no token list and performs no language-model ranking.
    """

    values = list(tokens)
    type_counts = Counter(values)
    token_results = [book.candidates(token) for token in values]
    type_results = {token: book.candidates(token) for token in type_counts}

    parseable_tokens = sum(not result.no_parse for result in token_results)
    parseable_types = sum(not result.no_parse for result in type_results.values())
    candidate_ambiguous_tokens = sum(len(result.candidates) > 1 for result in token_results)
    candidate_ambiguous_types = sum(len(result.candidates) > 1 for result in type_results.values())
    plaintext_ambiguous_tokens = sum(
        result.plaintext_ambiguity for result in token_results
    )
    latent_ambiguous_tokens = sum(
        result.latent_table_choice_ambiguity for result in token_results
    )
    all_candidate_counts = [len(result.candidates) for result in token_results]
    return {
        "token_count": len(values),
        "type_count": len(type_counts),
        "parseable_token_count": parseable_tokens,
        "parseable_type_count": parseable_types,
        "no_parse_token_count": len(values) - parseable_tokens,
        "no_parse_type_count": len(type_counts) - parseable_types,
        "candidate_ambiguous_token_count": candidate_ambiguous_tokens,
        "candidate_ambiguous_type_count": candidate_ambiguous_types,
        "plaintext_ambiguous_token_count": plaintext_ambiguous_tokens,
        "latent_table_ambiguous_token_count": latent_ambiguous_tokens,
        "mean_candidate_count": (
            sum(all_candidate_counts) / len(all_candidate_counts)
            if all_candidate_counts
            else 0.0
        ),
        "max_candidate_count": max(all_candidate_counts, default=0),
    }
