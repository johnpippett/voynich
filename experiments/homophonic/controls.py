"""Planted synthetic controls for bounded homophonic-map experiments.

The controls use canonical lower-case ASCII words and atomic units such as
``c00``. They do not read a corpus or provide a key to a solver.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
import json
import random
import string
from typing import Any


ALPHABET = tuple(string.ascii_lowercase)
FAMILY_NAMES = ("injective", "cap2", "unlimited")


def _expected_unit_count(family: str) -> int:
    if family == "injective":
        return len(ALPHABET)
    if family in ("cap2", "unlimited"):
        return 2 * len(ALPHABET)
    raise ValueError(f"unknown control family: {family!r}")


def _unit_names(count: int) -> tuple[str, ...]:
    return tuple(f"c{index:02d}" for index in range(count))


VALID_CONTROL_UNITS = frozenset(_unit_names(52))


def _validate_seed(seed: int) -> int:
    if not isinstance(seed, int) or isinstance(seed, bool) or seed < 0:
        raise ValueError("seed must be a non-negative integer")
    return seed


def _normalise_units(values: Iterable[str], field: str) -> tuple[str, ...]:
    if isinstance(values, str):
        raise ValueError(f"{field} must be a sequence of atomic unit strings")
    units = tuple(values)
    if any(not isinstance(unit, str) or not unit for unit in units):
        raise ValueError(f"{field} must contain non-empty strings")
    if len(set(units)) != len(units):
        raise ValueError(f"{field} must not contain duplicates")
    return units


def _normalise_cycle(values: Iterable[str], field: str) -> tuple[str, ...]:
    return _normalise_units(values, field)


def _validate_key(key: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(key, Mapping):
        raise TypeError("key must be a mapping")
    try:
        family = key["family"]
        seed = key["seed"]
        alphabet = tuple(key["alphabet"])
        units = _normalise_units(key["units"], "key units")
        cipher_to_plain = dict(key["cipher_to_plain"])
        emission_order = dict(key["emission_order"])
    except KeyError as exc:
        raise ValueError(f"key is missing field {exc.args[0]!r}") from exc
    except TypeError as exc:
        raise TypeError("key fields must be iterable mappings") from exc

    if family not in FAMILY_NAMES:
        raise ValueError(f"unknown control family: {family!r}")
    _validate_seed(seed)
    if alphabet != ALPHABET:
        raise ValueError("key alphabet must be lowercase ASCII")

    expected_units = _unit_names(_expected_unit_count(family))
    if set(units) != set(expected_units) or len(units) != len(expected_units):
        raise ValueError("key units do not match the selected control family")
    if set(cipher_to_plain) != set(units):
        raise ValueError("cipher_to_plain keys must match key units")
    if any(
        not isinstance(unit, str)
        or not isinstance(letter, str)
        or letter not in ALPHABET
        for unit, letter in cipher_to_plain.items()
    ):
        raise ValueError("cipher_to_plain must map units to lowercase ASCII letters")

    counts = {letter: 0 for letter in ALPHABET}
    for letter in cipher_to_plain.values():
        counts[letter] += 1
    if family == "injective" and set(counts.values()) != {1}:
        raise ValueError("injective key must use each letter once")
    if family == "cap2" and set(counts.values()) != {2}:
        raise ValueError("cap2 key must use each letter twice")
    if family == "unlimited" and any(count == 0 for count in counts.values()):
        raise ValueError("unlimited key must cover every alphabet letter")

    if set(emission_order) != set(ALPHABET):
        raise ValueError("emission_order must contain every alphabet letter")
    normalised_cycles: dict[str, tuple[str, ...]] = {}
    cycle_units: list[str] = []
    for letter in ALPHABET:
        cycle = _normalise_cycle(emission_order[letter], f"emission_order[{letter!r}]")
        if not cycle:
            raise ValueError("every letter must have an emission cycle")
        if any(unit not in cipher_to_plain for unit in cycle):
            raise ValueError("emission cycles contain an unknown unit")
        if any(cipher_to_plain[unit] != letter for unit in cycle):
            raise ValueError("emission cycles disagree with cipher_to_plain")
        normalised_cycles[letter] = cycle
        cycle_units.extend(cycle)
    if len(cycle_units) != len(set(cycle_units)) or set(cycle_units) != set(units):
        raise ValueError("emission cycles must partition key units")

    return {
        "family": family,
        "seed": seed,
        "alphabet": ALPHABET,
        "units": units,
        "cipher_to_plain": {
            unit: cipher_to_plain[unit] for unit in units
        },
        "emission_order": normalised_cycles,
    }


def seeded_control_key(family: str, seed: int) -> dict[str, Any]:
    """Return one deterministic planted key for a named control family."""

    if family not in FAMILY_NAMES:
        raise ValueError(f"unknown control family: {family!r}")
    seed = _validate_seed(seed)
    rng = random.Random(seed)
    units = list(_unit_names(_expected_unit_count(family)))
    rng.shuffle(units)
    shuffled_letters = list(ALPHABET)
    rng.shuffle(shuffled_letters)

    if family == "injective":
        assigned_letters = shuffled_letters
    elif family == "cap2":
        assigned_letters = list(ALPHABET) * 2
        rng.shuffle(assigned_letters)
    else:
        # The first unit block covers every letter. Extra units receive
        # deterministic random letters and can create additional homophones.
        assigned_letters = shuffled_letters + [
            rng.choice(ALPHABET) for _ in range(len(ALPHABET))
        ]

    cipher_to_plain = dict(zip(units, assigned_letters, strict=True))
    cycles: dict[str, list[str]] = {letter: [] for letter in ALPHABET}
    for unit, letter in cipher_to_plain.items():
        cycles[letter].append(unit)
    for letter in ALPHABET:
        rng.shuffle(cycles[letter])

    return _validate_key(
        {
            "family": family,
            "seed": seed,
            "alphabet": ALPHABET,
            "units": tuple(units),
            "cipher_to_plain": cipher_to_plain,
            "emission_order": {
                letter: tuple(cycles[letter]) for letter in ALPHABET
            },
        }
    )


def _normalise_plaintext_words(words: Iterable[str]) -> tuple[str, ...]:
    result = tuple(words)
    if any(
        not isinstance(word, str) or any(letter not in ALPHABET for letter in word)
        for word in result
    ):
        raise ValueError("plaintext words must contain lowercase ASCII letters")
    return result


def _normalise_cipher_words(
    cipher_words: Iterable[Iterable[str]],
) -> tuple[tuple[str, ...], ...]:
    if isinstance(cipher_words, str):
        raise ValueError("cipher_words must preserve atomic unit boundaries")
    result: list[tuple[str, ...]] = []
    for word in cipher_words:
        if isinstance(word, str):
            raise ValueError("cipher_words must contain sequences of atomic units")
        units = tuple(word)
        if any(not isinstance(unit, str) or not unit for unit in units):
            raise ValueError("cipher words must contain non-empty unit strings")
        result.append(units)
    return tuple(result)


def encrypt_words(
    words: Iterable[str],
    key: Mapping[str, Any],
) -> list[tuple[str, ...]]:
    """Encrypt words with per-letter cycles reset at the call boundary."""

    normalised_key = _validate_key(key)
    plaintext_words = _normalise_plaintext_words(words)
    cycles = normalised_key["emission_order"]
    offsets = {letter: 0 for letter in ALPHABET}
    encrypted: list[tuple[str, ...]] = []
    for word in plaintext_words:
        cipher_word: list[str] = []
        for letter in word:
            cycle = cycles[letter]
            offset = offsets[letter]
            cipher_word.append(cycle[offset % len(cycle)])
            offsets[letter] = offset + 1
        encrypted.append(tuple(cipher_word))
    return encrypted


def decode_words(
    cipher_words: Iterable[Iterable[str]],
    key: Mapping[str, Any],
) -> list[str]:
    """Decode atomic cipher words with a complete planted key."""

    normalised_key = _validate_key(key)
    words = _normalise_cipher_words(cipher_words)
    mapping = normalised_key["cipher_to_plain"]
    decoded: list[str] = []
    for word in words:
        try:
            decoded.append("".join(mapping[unit] for unit in word))
        except KeyError as exc:
            raise ValueError(f"cipher word contains an unknown unit: {exc.args[0]!r}") from exc
    return decoded


def _recovered_mapping(
    recovered_key: Mapping[str, Any],
) -> dict[str, str]:
    if not isinstance(recovered_key, Mapping):
        raise TypeError("recovered_key must be a mapping")
    if "cipher_to_plain" in recovered_key:
        candidate = recovered_key["cipher_to_plain"]
        if not isinstance(candidate, Mapping):
            raise ValueError("cipher_to_plain must be a mapping")
        mapping = dict(candidate)
    else:
        mapping = dict(recovered_key)
    for unit, letter in mapping.items():
        if unit not in VALID_CONTROL_UNITS:
            raise ValueError("recovered_key contains an unknown unit")
        if not isinstance(letter, str) or letter not in ALPHABET:
            raise ValueError("recovered_key values must be lowercase ASCII letters")
    return mapping


def recovery_metrics(
    cipher_words: Iterable[Iterable[str]],
    plaintext_words: Iterable[str],
    recovered_key: Mapping[str, Any],
    fit_symbols: Iterable[str],
) -> dict[str, Any]:
    """Measure full and fit-observed recovery without guessing missing units."""

    words = _normalise_cipher_words(cipher_words)
    plain_words = _normalise_plaintext_words(plaintext_words)
    if len(words) != len(plain_words):
        raise ValueError("cipher_words and plaintext_words must have equal token counts")
    mapping = _recovered_mapping(recovered_key)
    if isinstance(fit_symbols, str):
        fit_units = (fit_symbols,)
    else:
        fit_units = tuple(fit_symbols)
    if any(not isinstance(unit, str) or unit not in VALID_CONTROL_UNITS for unit in fit_units):
        raise ValueError("fit_symbols must contain valid control unit names")
    fit_set = set(fit_units)
    # Ignore mappings outside the fit set. This prevents an accidental full
    # planted key from supplying guesses for positions outside the fit data.
    effective_mapping = {
        unit: letter for unit, letter in mapping.items() if unit in fit_set
    }

    full_char_total = 0
    full_char_correct = 0
    observed_position_total = 0
    observed_position_correct = 0
    unobserved_position_count = 0
    full_token_correct = 0
    fully_observed_token_total = 0
    fully_observed_token_correct = 0

    for cipher_word, plaintext_word in zip(words, plain_words, strict=True):
        if len(cipher_word) != len(plaintext_word):
            raise ValueError("cipher and plaintext words must have equal lengths")
        token_correct = True
        fully_observed = all(unit in fit_set for unit in cipher_word)
        if fully_observed:
            fully_observed_token_total += 1
        for unit, letter in zip(cipher_word, plaintext_word, strict=True):
            full_char_total += 1
            known_letter = effective_mapping.get(unit)
            correct = known_letter == letter
            if correct:
                full_char_correct += 1
            else:
                token_correct = False
            if unit in fit_set:
                observed_position_total += 1
                if correct:
                    observed_position_correct += 1
            else:
                unobserved_position_count += 1
        if token_correct:
            full_token_correct += 1
        if fully_observed and token_correct:
            fully_observed_token_correct += 1

    def rate(correct: int, total: int) -> float | None:
        return None if total == 0 else correct / total

    return {
        "fit_units": tuple(sorted(fit_set)),
        "fit_unit_count": len(fit_set),
        "full_char_correct": full_char_correct,
        "full_char_total": full_char_total,
        "full_char_accuracy": rate(full_char_correct, full_char_total),
        "full_token_correct": full_token_correct,
        "full_token_total": len(plain_words),
        "full_token_accuracy": rate(full_token_correct, len(plain_words)),
        "observed_position_correct": observed_position_correct,
        "observed_position_total": observed_position_total,
        "observed_position_accuracy": rate(
            observed_position_correct, observed_position_total
        ),
        "fully_observed_token_correct": fully_observed_token_correct,
        "fully_observed_token_total": fully_observed_token_total,
        "fully_observed_token_accuracy": rate(
            fully_observed_token_correct, fully_observed_token_total
        ),
        "unobserved_position_count": unobserved_position_count,
    }


def key_to_json(key: Mapping[str, Any]) -> str:
    """Serialize a validated key while preserving atomic unit strings."""

    normalised_key = _validate_key(key)
    return json.dumps(normalised_key, sort_keys=True, separators=(",", ":"))


def cipher_words_to_json(cipher_words: Iterable[Iterable[str]]) -> str:
    """Serialize cipher words as arrays of atomic unit strings."""

    words = _normalise_cipher_words(cipher_words)
    return json.dumps(words, separators=(",", ":"))


__all__ = [
    "ALPHABET",
    "FAMILY_NAMES",
    "cipher_words_to_json",
    "decode_words",
    "encrypt_words",
    "key_to_json",
    "recovery_metrics",
    "seeded_control_key",
]
