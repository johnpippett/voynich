"""Run the bounded homophonic search-development protocol.

The runner measures one fixed root pivot-group relaxation and two fixed local
search starts. It uses the reviewed finite-lexicon primitives. It does not
run a tree search, score a test partition, or claim a historical result.

The public callable stages are ``run_root_bound`` and ``run_local_search``.
``run_study`` runs both stages and writes two complete key records before it
writes the aggregate report. A supervisor can call the stages in separate
bounded processes. The command-line entry point accepts a private JSON input
file or the fixed Italian input and emits only small progress records to standard output.
"""

from __future__ import annotations

import argparse
from collections import Counter
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from hashlib import sha256
import json
import platform
from pathlib import Path
import sys
from types import MappingProxyType
from typing import Any, TypeAlias

from experiments.group_bound.bitset import (
    BitsetCompatibilityError,
    BitsetConstructionError,
    BitsetPivotGroupBound,
)
from experiments.homophonic.solver import (
    _normalise_cipher_counts,
    _normalise_word,
    _score_key,
)
from experiments.lexical_warmstart.warmstart import lexical_local_search


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
Word: TypeAlias = tuple[str, ...]
ProgressCallback: TypeAlias = Callable[[dict[str, Any]], None]

PROTOCOL_PATH = "docs/plans/homophonic-search-development-v1.md"
ALPHABET = "abcdefghijklmnopqrstuvwxyz"
CONTROL_FAMILY = "cap2"
ENCRYPTION_SEED = 7000
START_NAMES = ("cold_selected", "assisted_selected")
DEFAULT_OUTPUT_DIR = "reports/homophonic-search-development-v1"
LOCAL_STOP_STATUSES = frozenset(
    ("empty_input", "move_budget_exhausted", "no_improving_move")
)

# These values are the fixed inputs in the development design. They are not
# inferred from a result and they are not changed after a result is inspected.
PINNED_INPUT_ARTIFACT_HASHES = {
    "data/reference_manifest.json": "f261b781f150991e3305aae5057a94dc91afd8e59c58bb22ff199347f5ce3e6d",
    "docs/plans/visual-homophonic-pilot.md": "0e6a6edf5e0172f5e7a0f1fbf2f7ede8b9b181c7180aa616de58f44ae04d1249",
    "reports/homophonic-feasibility-v1/italian-cold.json": "4209022e13399bb7347b8f1d098f43c4d0922ae1b9c6df72382ed5553b44b0b3",
    "reports/homophonic-feasibility-v1/italian-cold.keys.json": "08a3b0b6cf76e013efb8175bd6fa1251fd1ae9ae1911a96420d123ae81198e50",
    "reports/homophonic-feasibility-v1/italian-assisted.json": "461ddb0d5f097227d7d521436a3a6ebb459b8d53de973ed2e1e913af3be42f31",
    "reports/homophonic-feasibility-v1/italian-assisted.keys.json": "df35fb2e7d1df309f60030d984e01a22837c92af37c72d0bf8d9c5a765b097fe",
}

PINNED_FROZEN_MODULE_HASHES = {
    "experiments/homophonic/solver.py": "5e5b0d1bd21dcdf850d9154c088065d2cd6174671083dc6b5b935282da0c2760",
    "experiments/homophonic/bitset_bound.py": "8ab50b9700497cc493e0ba79a9fc6d452cf95e5b8c7d9d19d0de08b567000f76",
    "experiments/homophonic/controls.py": "4845d1de4e766c5d63b23919bab2715db24b431ba502112494e477a1740fd896",
    "experiments/homophonic/run_controls.py": "65f81693336a3c705281ed711b45881a19a0adc34b715a29188dc1361d86be63",
    "experiments/lexicon/run_pilot.py": "2eb25cdeb4fdf8ef167a3f10c2463b1ef61c23b1dd7e34a3aea9368c6edf69e5",
    "src/voynich/corpus.py": "064c45794d523b5c07ea10621752e325d35709f619e0763ac6ba1561f0fa1dc2",
    "src/voynich/groups.py": "15b77e967ce296634a36a3deacba660c14a4d4615c99597949b5586d682bdef0",
    "src/voynich/substitution.py": "3c246844b9adcd003d593eff97b53c6a3d1f54bc1fd76bc8e5145345aadf3332",
    "src/voynich/reference.py": "97e173c761b137d3653a827315b62a68af3e96abd189afdecc46e9759d2b94d9",
    "experiments/group_bound/pivot.py": "8573d5d620c474ef24b5c5c875d26442ff8c7dcfbfd97fef98650d520d479d8b",
    "experiments/group_bound/bitset.py": "9587d8cfa67a8e174b24a23d83a4f392c54587efe1bdb5553c5d8352efb2693b",
    "experiments/lexical_warmstart/warmstart.py": "85c261e0c88e335321d0ae76b86878bc3798518c3e715295aef9d678305d36b0",
}

PINNED_START_SCORES = {
    "cold_selected": 90_866_594,
    "assisted_selected": 222_253_278,
}
PINNED_WEIGHTED_COUNTS_SHA256 = (
    "664b6498a147b5430695ec0f0ee276c654fabd6a9e567b4960eb7d1f56fad944"
)
PINNED_KEY_RECORD_HASHES = {
    "cold_selected": PINNED_INPUT_ARTIFACT_HASHES[
        "reports/homophonic-feasibility-v1/italian-cold.keys.json"
    ],
    "assisted_selected": PINNED_INPUT_ARTIFACT_HASHES[
        "reports/homophonic-feasibility-v1/italian-assisted.keys.json"
    ],
}
PINNED_REPORT_HASHES = {
    "cold_selected": PINNED_INPUT_ARTIFACT_HASHES[
        "reports/homophonic-feasibility-v1/italian-cold.json"
    ],
    "assisted_selected": PINNED_INPUT_ARTIFACT_HASHES[
        "reports/homophonic-feasibility-v1/italian-assisted.json"
    ],
}


class StudyError(RuntimeError):
    """Base class for fail-closed development-run errors."""


class InputMismatch(StudyError):
    """A pinned input, count, score, or map does not match."""


class ResourceAbstain(StudyError):
    """A declared construction or evaluation resource limit stopped the run."""


class ImplementationFailure(StudyError):
    """A frozen primitive or runner invariant failed."""


def canonical_bytes(value: Any) -> bytes:
    """Serialize JSON values with stable key and separator order."""

    return (
        json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")


def canonical_hash(value: Any) -> str:
    """Return the SHA-256 digest of canonical JSON bytes."""

    return sha256(canonical_bytes(value)).hexdigest()


def sha256_path(path: Path) -> str:
    """Return a file digest without exposing the path in a report."""

    return sha256(path.read_bytes()).hexdigest()


def _freeze_mapping(value: Mapping[str, Any]) -> MappingProxyType:
    return MappingProxyType(dict(value))


def _validate_optional_nonnegative(value: int | None, name: str) -> None:
    if value is not None and (
        isinstance(value, bool) or not isinstance(value, int) or value < 0
    ):
        raise ValueError(f"{name} must be a non-negative integer or None")


@dataclass(frozen=True, slots=True)
class DevelopmentConfig:
    """Fixed parameters and resource guards for one development run."""

    protocol_name: str = "homophonic-search-development-v1"
    protocol_path: str = PROTOCOL_PATH
    control_family: str = CONTROL_FAMILY
    encryption_seed: int = ENCRYPTION_SEED
    capacity: int | None = 2
    alphabet: Iterable[str] | str = ALPHABET
    move_budget: int = 8
    max_candidate_rows: int = 12_600_000
    max_estimated_storage_bytes: int = 2_000_000_000
    per_start_evaluation_limit: int = 11_000
    total_evaluation_limit: int = 22_000
    root_timeout_seconds: int = 1_200
    total_timeout_seconds: int = 1_500
    rss_limit_bytes: int = 7 * 1024**3
    expected_validation_token_count: int | None = 31_681
    expected_validation_type_count: int | None = 14_170
    expected_training_lexicon_type_count: int | None = 6_273
    expected_cipher_unit_count: int | None = 47
    expected_candidate_row_count: int | None = 12_549_021
    expected_storage_estimate_bytes: int | None = 1_759_288_862
    expected_stream_sha256: str | None = (
        "d7e9c6e0b716cf7ea1c7deb4f135ca2692ea70b4f927548e99668ab0c1428492"
    )
    expected_training_lexicon_sha256: str | None = (
        "29d94e0de2a154071c15a9c524a1bb0b73ba2c3a618935be8716e8d3a32824ef"
    )
    expected_weighted_counts_sha256: str | None = PINNED_WEIGHTED_COUNTS_SHA256
    expected_input_artifact_hashes: Mapping[str, str] = field(
        default_factory=lambda: PINNED_INPUT_ARTIFACT_HASHES
    )
    expected_frozen_module_hashes: Mapping[str, str] = field(
        default_factory=lambda: PINNED_FROZEN_MODULE_HASHES
    )
    expected_start_scores: Mapping[str, int] = field(
        default_factory=lambda: PINNED_START_SCORES
    )
    expected_key_record_hashes: Mapping[str, str] = field(
        default_factory=lambda: PINNED_KEY_RECORD_HASHES
    )
    expected_report_hashes: Mapping[str, str] = field(
        default_factory=lambda: PINNED_REPORT_HASHES
    )

    def __post_init__(self) -> None:
        if not isinstance(self.protocol_name, str) or not self.protocol_name:
            raise ValueError("protocol_name must be a non-empty string")
        if not isinstance(self.protocol_path, str) or not self.protocol_path:
            raise ValueError("protocol_path must be a non-empty string")
        if self.control_family != CONTROL_FAMILY:
            raise ValueError(f"control_family must be {CONTROL_FAMILY!r}")
        if (
            isinstance(self.encryption_seed, bool)
            or not isinstance(self.encryption_seed, int)
            or self.encryption_seed != ENCRYPTION_SEED
        ):
            raise ValueError(f"encryption_seed must be {ENCRYPTION_SEED}")
        if self.capacity is not None and (
            isinstance(self.capacity, bool)
            or not isinstance(self.capacity, int)
            or self.capacity < 1
        ):
            raise ValueError("capacity must be a positive integer or None")
        alphabet = tuple(self.alphabet) if isinstance(self.alphabet, str) else tuple(self.alphabet)
        if not alphabet or any(not isinstance(symbol, str) or not symbol for symbol in alphabet):
            raise ValueError("alphabet must contain non-empty symbols")
        if len(set(alphabet)) != len(alphabet):
            raise ValueError("alphabet symbols must be unique")
        if (
            isinstance(self.move_budget, bool)
            or not isinstance(self.move_budget, int)
            or self.move_budget < 0
        ):
            raise ValueError("move_budget must be a non-negative integer")
        for name in (
            "max_candidate_rows",
            "max_estimated_storage_bytes",
            "per_start_evaluation_limit",
            "total_evaluation_limit",
            "root_timeout_seconds",
            "total_timeout_seconds",
            "rss_limit_bytes",
        ):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be a non-negative integer")
        for name in (
            "expected_validation_token_count",
            "expected_validation_type_count",
            "expected_training_lexicon_type_count",
            "expected_cipher_unit_count",
            "expected_candidate_row_count",
            "expected_storage_estimate_bytes",
        ):
            _validate_optional_nonnegative(getattr(self, name), name)
        object.__setattr__(self, "alphabet", tuple(sorted(alphabet)))
        object.__setattr__(
            self,
            "expected_input_artifact_hashes",
            _freeze_mapping(self.expected_input_artifact_hashes),
        )
        object.__setattr__(
            self,
            "expected_frozen_module_hashes",
            _freeze_mapping(self.expected_frozen_module_hashes),
        )
        object.__setattr__(
            self,
            "expected_start_scores",
            _freeze_mapping(self.expected_start_scores),
        )
        object.__setattr__(
            self,
            "expected_key_record_hashes",
            _freeze_mapping(self.expected_key_record_hashes),
        )
        object.__setattr__(
            self,
            "expected_report_hashes",
            _freeze_mapping(self.expected_report_hashes),
        )

    def public(self) -> dict[str, Any]:
        """Return configuration fields safe for the aggregate report."""

        return {
            "protocol_name": self.protocol_name,
            "protocol_path": self.protocol_path,
            "control_family": self.control_family,
            "encryption_seed": self.encryption_seed,
            "capacity": self.capacity,
            "alphabet": list(self.alphabet),
            "objective": "integer weighted exact lexicon word hits",
            "objective_weight_formula": "count(word) * T + N",
            "objective_denominator_formula": "2 * T * N",
            "expected_weighted_counts_sha256": self.expected_weighted_counts_sha256,
            "move_budget": self.move_budget,
            "move_kinds": ["single_unit_reassignment", "two_unit_swap"],
            "trace_mode": "summary",
            "root_bound": "static_min_symbol pivot-group relaxation",
            "max_candidate_rows": self.max_candidate_rows,
            "max_estimated_storage_bytes": self.max_estimated_storage_bytes,
            "per_start_evaluation_limit": self.per_start_evaluation_limit,
            "total_evaluation_limit": self.total_evaluation_limit,
            "root_timeout_seconds": self.root_timeout_seconds,
            "total_timeout_seconds": self.total_timeout_seconds,
            "rss_limit_bytes": self.rss_limit_bytes,
            "supervisor_owns_time_and_rss_enforcement": True,
        }


@dataclass(frozen=True, slots=True)
class StudyInputs:
    """Private normalized inputs for the two-stage runner.

    The object retains normalized words for the fitting primitives. The
    ``run_study`` aggregate never serializes this object or its word values.
    """

    weighted_counts: Mapping[Word, int]
    training_lexicon: tuple[Word, ...]
    starts: Mapping[str, Mapping[str, str]]
    pinned_scores: Mapping[str, int]
    validation_token_count: int
    validation_type_count: int
    training_lexicon_type_count: int
    raw_counts: Mapping[Word, int] | None = None
    validation_stream_sha256: str | None = None
    training_lexicon_sha256: str | None = None
    input_artifact_hashes: Mapping[str, str] = field(default_factory=dict)
    input_key_hashes: Mapping[str, str] = field(default_factory=dict)
    input_report_hashes: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        weighted = _normalise_cipher_counts(self.weighted_counts)
        lexicon_values = tuple(sorted({_normalise_word(word) for word in self.training_lexicon}))
        if self.raw_counts is None:
            raw = None
        else:
            raw = _normalise_cipher_counts(self.raw_counts)
        starts = {
            str(name): dict(sorted(key.items()))
            for name, key in self.starts.items()
        }
        pinned = dict(self.pinned_scores)
        for field_name, value in (
            ("validation_token_count", self.validation_token_count),
            ("validation_type_count", self.validation_type_count),
            ("training_lexicon_type_count", self.training_lexicon_type_count),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{field_name} must be a non-negative integer")
        for name, score in pinned.items():
            if not isinstance(name, str) or not isinstance(score, int) or isinstance(score, bool) or score < 0:
                raise ValueError("pinned scores must be non-negative integers")
        object.__setattr__(self, "weighted_counts", MappingProxyType(weighted))
        object.__setattr__(self, "training_lexicon", lexicon_values)
        object.__setattr__(
            self,
            "starts",
            MappingProxyType({name: MappingProxyType(key) for name, key in starts.items()}),
        )
        object.__setattr__(self, "pinned_scores", MappingProxyType(pinned))
        object.__setattr__(self, "raw_counts", None if raw is None else MappingProxyType(raw))
        object.__setattr__(self, "input_artifact_hashes", _freeze_mapping(self.input_artifact_hashes))
        object.__setattr__(self, "input_key_hashes", _freeze_mapping(self.input_key_hashes))
        object.__setattr__(self, "input_report_hashes", _freeze_mapping(self.input_report_hashes))

    @classmethod
    def from_raw_counts(
        cls,
        validation_counts: Mapping[str | Word, int],
        training_lexicon: Iterable[str | Word],
        *,
        starts: Mapping[str, Mapping[str, str]],
        pinned_scores: Mapping[str, int],
        validation_stream_sha256: str | None = None,
        training_lexicon_sha256: str | None = None,
        input_artifact_hashes: Mapping[str, str] | None = None,
        input_key_hashes: Mapping[str, str] | None = None,
        input_report_hashes: Mapping[str, str] | None = None,
    ) -> "StudyInputs":
        """Build exact ``count * T + N`` weights from raw validation counts."""

        raw = _normalise_cipher_counts(validation_counts)
        lexicon_values = tuple(training_lexicon)
        token_count = sum(raw.values())
        type_count = len(raw)
        weighted = {
            word: count * type_count + token_count
            for word, count in raw.items()
        }
        return cls(
            weighted_counts=weighted,
            raw_counts=raw,
            training_lexicon=lexicon_values,
            starts=starts,
            pinned_scores=pinned_scores,
            validation_token_count=token_count,
            validation_type_count=type_count,
            training_lexicon_type_count=len({_normalise_word(word) for word in lexicon_values}),
            validation_stream_sha256=validation_stream_sha256,
            training_lexicon_sha256=training_lexicon_sha256,
            input_artifact_hashes=input_artifact_hashes or {},
            input_key_hashes=input_key_hashes or {},
            input_report_hashes=input_report_hashes or {},
        )

    @classmethod
    def from_weighted_counts(
        cls,
        weighted_counts: Mapping[str | Word, int],
        training_lexicon: Iterable[str | Word],
        *,
        validation_token_count: int,
        validation_type_count: int,
        starts: Mapping[str, Mapping[str, str]],
        pinned_scores: Mapping[str, int],
        training_lexicon_type_count: int | None = None,
        validation_stream_sha256: str | None = None,
        training_lexicon_sha256: str | None = None,
        input_artifact_hashes: Mapping[str, str] | None = None,
        input_key_hashes: Mapping[str, str] | None = None,
        input_report_hashes: Mapping[str, str] | None = None,
    ) -> "StudyInputs":
        """Build inputs when a caller already computed the integer weights."""

        lexicon = tuple(training_lexicon)
        unique_count = len({_normalise_word(word) for word in lexicon})
        return cls(
            weighted_counts=weighted_counts,
            training_lexicon=lexicon,
            starts=starts,
            pinned_scores=pinned_scores,
            validation_token_count=validation_token_count,
            validation_type_count=validation_type_count,
            training_lexicon_type_count=(
                unique_count if training_lexicon_type_count is None
                else training_lexicon_type_count
            ),
            validation_stream_sha256=validation_stream_sha256,
            training_lexicon_sha256=training_lexicon_sha256,
            input_artifact_hashes=input_artifact_hashes or {},
            input_key_hashes=input_key_hashes or {},
            input_report_hashes=input_report_hashes or {},
        )

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "StudyInputs":
        """Decode the private JSON input format used by the CLI."""

        if not isinstance(payload, Mapping):
            raise TypeError("study input must be a JSON object")
        raw_rows = payload.get("validation_counts", payload.get("ciphertext_counts"))
        if raw_rows is None:
            weighted_rows = payload.get("weighted_counts")
            if weighted_rows is None:
                raise ValueError("input must contain validation_counts or weighted_counts")
            counts = _decode_word_rows(weighted_rows)
            metadata = payload.get("metadata", {})
            return cls.from_weighted_counts(
                counts,
                _decode_training_lexicon(payload.get("training_lexicon", ())),
                validation_token_count=metadata["validation_token_count"],
                validation_type_count=metadata["validation_type_count"],
                training_lexicon_type_count=metadata.get("training_lexicon_type_count"),
                starts=payload["starts"],
                pinned_scores=payload["pinned_scores"],
                validation_stream_sha256=metadata.get("validation_stream_sha256"),
                training_lexicon_sha256=metadata.get("training_lexicon_sha256"),
                input_artifact_hashes=metadata.get("input_artifact_hashes", {}),
                input_key_hashes=metadata.get("input_key_hashes", {}),
                input_report_hashes=metadata.get("input_report_hashes", {}),
            )
        return cls.from_raw_counts(
            _decode_word_rows(raw_rows),
            _decode_training_lexicon(payload.get("training_lexicon", ())),
            starts=payload["starts"],
            pinned_scores=payload["pinned_scores"],
            validation_stream_sha256=payload.get("metadata", {}).get("validation_stream_sha256"),
            training_lexicon_sha256=payload.get("metadata", {}).get("training_lexicon_sha256"),
            input_artifact_hashes=payload.get("metadata", {}).get("input_artifact_hashes", {}),
            input_key_hashes=payload.get("metadata", {}).get("input_key_hashes", {}),
            input_report_hashes=payload.get("metadata", {}).get("input_report_hashes", {}),
        )


def _decode_json_word(value: Any) -> Word:
    """Decode a JSON word string or a JSON array of atomic units."""

    if isinstance(value, list):
        value = tuple(value)
    return _normalise_word(value)


def _decode_training_lexicon(values: Any) -> tuple[Word, ...]:
    if isinstance(values, (str, bytes)) or not isinstance(values, Iterable):
        raise TypeError("training_lexicon must be an iterable of words")
    return tuple(_decode_json_word(value) for value in values)


def _decode_word_rows(rows: Any) -> dict[Word, int]:
    if isinstance(rows, Mapping):
        # JSON object keys can encode atomic strings. Tuple words use the row
        # form below because a compound unit may itself contain punctuation.
        result: dict[Word, int] = {}
        for raw_word, count in rows.items():
            word = _decode_json_word(raw_word)
            if word in result:
                raise ValueError("word rows contain duplicate normalized words")
            result[word] = count
        return result
    if isinstance(rows, (str, bytes)) or not isinstance(rows, Iterable):
        raise TypeError("word rows must be an iterable")
    result = {}
    for row in rows:
        if not isinstance(row, Mapping) or "word" not in row or "count" not in row:
            raise ValueError("word rows must contain word and count")
        word = _decode_json_word(row["word"])
        if word in result:
            raise ValueError("word rows contain duplicate normalized words")
        result[word] = row["count"]
    return result


DEFAULT_CONFIG = DevelopmentConfig()


def _emit(progress: ProgressCallback | None, event: dict[str, Any]) -> None:
    if progress is not None:
        progress(dict(event))


def _counts_payload(counts: Mapping[Word, int]) -> list[dict[str, Any]]:
    return [
        {"word": list(word), "count": counts[word]}
        for word in sorted(counts)
    ]


def _lexicon_hash(lexicon: Iterable[Word]) -> str:
    # The frozen control records hash normalized plaintext words as strings.
    values = {
        word if isinstance(word, str) else "".join(word)
        for word in lexicon
    }
    return canonical_hash(sorted(values))


def _validate_map(
    key: Mapping[str, str],
    cipher_symbols: tuple[str, ...],
    config: DevelopmentConfig,
) -> dict[str, str]:
    if not isinstance(key, Mapping):
        raise InputMismatch("selected key must be a mapping")
    normalized = dict(sorted(key.items()))
    if set(normalized) != set(cipher_symbols):
        raise InputMismatch("selected key is not a total map over the fit units")
    alphabet = set(config.alphabet)
    if any(
        not isinstance(cipher, str)
        or not isinstance(plain, str)
        or plain not in alphabet
        for cipher, plain in normalized.items()
    ):
        raise InputMismatch("selected key contains a value outside the plaintext alphabet")
    usage = Counter(normalized.values())
    if config.capacity is not None and any(
        count > config.capacity for count in usage.values()
    ):
        raise InputMismatch("selected key exceeds plaintext capacity")
    return normalized


def _input_symbols(counts: Mapping[Word, int]) -> tuple[str, ...]:
    return tuple(sorted({symbol for word in counts for symbol in word}))


def validate_inputs(
    inputs: StudyInputs,
    config: DevelopmentConfig = DEFAULT_CONFIG,
) -> dict[str, Any]:
    """Validate pinned counts, weights, hashes, start names, and maps."""

    if not isinstance(inputs, StudyInputs):
        raise TypeError("inputs must be StudyInputs")
    counts = dict(inputs.weighted_counts)
    lexicon = set(inputs.training_lexicon)
    symbols = _input_symbols(counts)
    weighted_counts_hash = canonical_hash(_counts_payload(counts))
    training_lexicon_hash = _lexicon_hash(lexicon)
    token_count = inputs.validation_token_count
    type_count = inputs.validation_type_count
    if len(counts) != type_count:
        raise InputMismatch("validation type count does not match weighted counts")
    if inputs.raw_counts is not None:
        raw = dict(inputs.raw_counts)
        if len(raw) != type_count or sum(raw.values()) != token_count:
            raise InputMismatch("raw validation counts do not match pinned N and T")
        expected_weights = {
            word: count * type_count + token_count
            for word, count in raw.items()
        }
        if expected_weights != counts:
            raise InputMismatch("integer objective weights do not match count * T + N")
    if token_count and type_count:
        denominator = 2 * token_count * type_count
        if sum(counts.values()) != denominator:
            raise InputMismatch("integer objective weights do not match denominator")
    if config.expected_validation_token_count is not None and token_count != config.expected_validation_token_count:
        raise InputMismatch("validation token count does not match the pinned input")
    if config.expected_validation_type_count is not None and type_count != config.expected_validation_type_count:
        raise InputMismatch("validation type count does not match the pinned input")
    if config.expected_training_lexicon_type_count is not None and inputs.training_lexicon_type_count != config.expected_training_lexicon_type_count:
        raise InputMismatch("training lexicon type count does not match the pinned input")
    if len(lexicon) != inputs.training_lexicon_type_count:
        raise InputMismatch("training lexicon type count does not match normalized lexicon")
    if (
        inputs.training_lexicon_sha256 is not None
        and inputs.training_lexicon_sha256 != training_lexicon_hash
    ):
        raise InputMismatch("training lexicon hash does not match normalized data")
    if any(set(word) - set(config.alphabet) for word in lexicon):
        raise InputMismatch("training lexicon contains a symbol outside the plaintext alphabet")
    if config.expected_cipher_unit_count is not None and len(symbols) != config.expected_cipher_unit_count:
        raise InputMismatch("cipher unit count does not match the pinned input")
    if config.capacity is not None and config.capacity * len(config.alphabet) < len(symbols):
        raise InputMismatch("capacity cannot support a total map over the fit units")
    if config.expected_stream_sha256 is not None and inputs.validation_stream_sha256 != config.expected_stream_sha256:
        raise InputMismatch("validation stream hash does not match the pinned input")
    if (
        config.expected_training_lexicon_sha256 is not None
        and training_lexicon_hash != config.expected_training_lexicon_sha256
    ):
        raise InputMismatch("training lexicon hash does not match the pinned input")
    if (
        config.expected_weighted_counts_sha256 is not None
        and weighted_counts_hash != config.expected_weighted_counts_sha256
    ):
        raise InputMismatch("weighted counts hash does not match the pinned input")
    for path, expected in config.expected_input_artifact_hashes.items():
        if inputs.input_artifact_hashes.get(path) != expected:
            raise InputMismatch(f"input artifact hash does not match: {path}")
    if set(inputs.starts) != set(START_NAMES):
        raise InputMismatch("inputs must contain cold_selected and assisted_selected starts")
    if set(inputs.pinned_scores) != set(START_NAMES):
        raise InputMismatch("inputs must contain two pinned start scores")
    for name in START_NAMES:
        expected_score = config.expected_start_scores.get(name)
        if expected_score is not None and inputs.pinned_scores[name] != expected_score:
            raise InputMismatch(f"pinned score does not match: {name}")
        _validate_map(inputs.starts[name], symbols, config)
        expected_key_hash = config.expected_key_record_hashes.get(name)
        if expected_key_hash is not None and inputs.input_key_hashes.get(name) != expected_key_hash:
            raise InputMismatch(f"selected key record hash does not match: {name}")
        expected_report_hash = config.expected_report_hashes.get(name)
        if expected_report_hash is not None and inputs.input_report_hashes.get(name) != expected_report_hash:
            raise InputMismatch(f"selected report hash does not match: {name}")
    return {
        "validation_token_count": token_count,
        "validation_type_count": type_count,
        "training_lexicon_type_count": inputs.training_lexicon_type_count,
        "cipher_unit_count": len(symbols),
        "objective_denominator": 2 * token_count * type_count if token_count and type_count else 0,
        "weighted_total": sum(counts.values()),
        "weighted_counts_hash": weighted_counts_hash,
        "training_lexicon_sha256": training_lexicon_hash,
        "validation_stream_sha256": inputs.validation_stream_sha256,
    }


def _normalise_for_config(
    ciphertext_counts: Mapping[str | Word, int],
    plaintext_lexicon: Iterable[str | Word],
    config: DevelopmentConfig,
) -> tuple[dict[Word, int], set[Word]]:
    counts = _normalise_cipher_counts(ciphertext_counts)
    raw_lexicon = tuple(_normalise_word(word) for word in plaintext_lexicon)
    alphabet = set(config.alphabet)
    if any(set(word) - alphabet for word in raw_lexicon):
        raise InputMismatch("training lexicon contains a symbol outside the plaintext alphabet")
    lexicon = set(raw_lexicon)
    return counts, lexicon


def _public_metadata(metadata: Mapping[str, Any]) -> dict[str, Any]:
    allowed = {
        "capacity",
        "cipher_type_count",
        "cipher_symbol_count",
        "candidate_count_total",
        "candidate_type_count",
        "missing_candidate_count",
        "group_count",
        "ungrouped_type_count",
        "grouping",
        "max_candidate_rows",
        "lexicon_raw_entry_count",
        "lexicon_unique_normalized_count",
        "lexicon_usable_count",
        "lexicon_rejected_out_of_alphabet_count",
        "candidate_rows_complete",
        "engine",
        "source_sha256",
        "slot_count",
        "estimated_storage_upper_bound_bytes",
        "max_estimated_storage_bytes",
        "storage_estimate_is_not_os_memory_limit",
        "frozen_estimated_storage_bytes",
    }
    return {
        key: metadata[key]
        for key in sorted(allowed)
        if key in metadata and isinstance(metadata[key], (str, int, bool, type(None)))
    }


def run_root_bound(
    ciphertext_counts_or_inputs: Mapping[str | Word, int] | StudyInputs,
    plaintext_lexicon: Iterable[str | Word] | None = None,
    *,
    config: DevelopmentConfig = DEFAULT_CONFIG,
    bound_factory: Callable[..., Any] = BitsetPivotGroupBound,
    progress: ProgressCallback | None = None,
) -> dict[str, Any]:
    """Build and query the complete static pivot-group root bound.

    The returned dictionary contains aggregate values only. It does not
    contain group word arrays, candidate rows, or normalized word values.
    """

    if isinstance(ciphertext_counts_or_inputs, StudyInputs):
        validate_inputs(ciphertext_counts_or_inputs, config)
        counts = dict(ciphertext_counts_or_inputs.weighted_counts)
        lexicon = set(ciphertext_counts_or_inputs.training_lexicon)
    else:
        if plaintext_lexicon is None:
            raise TypeError("plaintext_lexicon is required")
        counts, lexicon = _normalise_for_config(
            ciphertext_counts_or_inputs,
            plaintext_lexicon,
            config,
        )
    symbols = _input_symbols(counts)
    if config.expected_cipher_unit_count is not None and len(symbols) != config.expected_cipher_unit_count:
        raise InputMismatch("cipher unit count does not match the pinned input")
    _emit(progress, {
        "stage": "root_bound",
        "event": "start",
        "cipher_type_count": len(counts),
        "cipher_unit_count": len(symbols),
    })
    try:
        bound_object = bound_factory(
            counts,
            lexicon,
            config.alphabet,
            capacity=config.capacity,
            groups=None,
            max_candidate_rows=config.max_candidate_rows,
            max_estimated_storage_bytes=config.max_estimated_storage_bytes,
        )
        result = bound_object.bound({})
    except BitsetCompatibilityError as exc:
        raise ImplementationFailure(f"root bound compatibility failed: {exc}") from exc
    except BitsetConstructionError as exc:
        message = str(exc)
        if any(term in message.lower() for term in ("limit", "storage", "rows")):
            raise ResourceAbstain(f"root bound construction stopped: {message}") from exc
        raise ImplementationFailure(f"root bound construction failed: {message}") from exc
    except (MemoryError, TimeoutError) as exc:
        raise ResourceAbstain("root bound construction exceeded available resources") from exc
    except (ValueError, RuntimeError) as exc:
        raise ImplementationFailure(f"root bound construction failed: {exc}") from exc
    if not isinstance(result, Mapping):
        raise ImplementationFailure("root bound did not return a mapping")
    metadata = result.get("metadata")
    if not isinstance(metadata, Mapping):
        raise ImplementationFailure("root bound did not return metadata")
    if result.get("status") != "complete" or not result.get("feasible"):
        raise ImplementationFailure("root bound did not complete a feasible cache")
    if result.get("candidate_rows_complete") is not True:
        raise ImplementationFailure("root bound candidate rows are not complete")
    candidate_rows = metadata.get("candidate_count_total", result.get("candidate_count_total"))
    if isinstance(candidate_rows, bool) or not isinstance(candidate_rows, int) or candidate_rows < 0:
        raise ImplementationFailure("root bound candidate row count is invalid")
    if config.expected_candidate_row_count is not None and candidate_rows != config.expected_candidate_row_count:
        raise InputMismatch("candidate row count does not match the pinned input")
    storage_estimate = metadata.get("frozen_estimated_storage_bytes")
    if storage_estimate is None:
        storage_estimate = metadata.get("estimated_storage_bytes")
    if storage_estimate is not None and (
        isinstance(storage_estimate, bool) or not isinstance(storage_estimate, int) or storage_estimate < 0
    ):
        raise ImplementationFailure("root bound storage estimate is invalid")
    if config.expected_storage_estimate_bytes is not None and storage_estimate != config.expected_storage_estimate_bytes:
        raise InputMismatch("bitset storage estimate does not match the pinned input")
    group_bound = result.get("group_bound")
    independent_bound = result.get("independent_bound")
    if (
        isinstance(group_bound, bool)
        or not isinstance(group_bound, int)
        or isinstance(independent_bound, bool)
        or not isinstance(independent_bound, int)
        or group_bound < 0
        or independent_bound < 0
        or group_bound > independent_bound
    ):
        raise ImplementationFailure("root group and independent bounds are invalid")
    residual_words = result.get("ungrouped_words", ())
    groups = result.get("groups", ())
    if not isinstance(residual_words, Sequence) or not isinstance(groups, Sequence):
        raise ImplementationFailure("root bound group metadata is invalid")
    public_metadata = _public_metadata(metadata)
    output = {
        "status": "complete",
        "engine": "BitsetPivotGroupBound",
        "candidate_row_count": candidate_rows,
        "candidate_type_count": public_metadata.get("candidate_type_count"),
        "cipher_type_count": public_metadata.get("cipher_type_count", len(counts)),
        "cipher_unit_count": public_metadata.get("cipher_symbol_count", len(symbols)),
        "group_count": len(groups),
        "residual_type_count": len(residual_words),
        "group_bound": group_bound,
        "independent_bound": independent_bound,
        "independent_minus_group_bound": independent_bound - group_bound,
        "storage_estimate_bytes": storage_estimate,
        "metadata": public_metadata,
        "scope_limits": [
            "The bound covers the supplied finite weighted lexicon objective.",
            "It uses fixed word boundaries and one total cipher-unit map.",
            "Group conflicts and cross-group capacity conflicts are relaxed.",
            "It does not certify a unique key or a language result.",
        ],
    }
    _emit(progress, {
        "stage": "root_bound",
        "event": "complete",
        "candidate_row_count": candidate_rows,
        "group_bound": group_bound,
        "independent_bound": independent_bound,
    })
    return output


def run_local_search(
    ciphertext_counts: Mapping[str | Word, int],
    plaintext_lexicon: Iterable[str | Word],
    initial_key: Mapping[str, str],
    *,
    pinned_score: int,
    start_name: str,
    config: DevelopmentConfig = DEFAULT_CONFIG,
    search_fn: Callable[..., Mapping[str, Any]] = lexical_local_search,
    progress: ProgressCallback | None = None,
) -> dict[str, Any]:
    """Run one fixed eight-move local search and validate its exact score."""

    if start_name not in START_NAMES:
        raise InputMismatch("unknown local-search start")
    if isinstance(pinned_score, bool) or not isinstance(pinned_score, int) or pinned_score < 0:
        raise InputMismatch("pinned score must be a non-negative integer")
    counts, lexicon = _normalise_for_config(
        ciphertext_counts,
        plaintext_lexicon,
        config,
    )
    symbols = _input_symbols(counts)
    key = _validate_map(initial_key, symbols, config)
    initial_score, initial_hit_types = _score_key(key, counts, lexicon)
    if initial_score != pinned_score:
        raise InputMismatch(f"initial score does not match the pinned score: {start_name}")
    _emit(progress, {
        "stage": "local_search",
        "event": "start",
        "start": start_name,
        "initial_score": initial_score,
    })
    try:
        result = search_fn(
            counts,
            lexicon,
            config.alphabet,
            capacity=config.capacity,
            initial_key=key,
            move_budget=config.move_budget,
            trace_mode="summary",
        )
    except (MemoryError, TimeoutError) as exc:
        raise ResourceAbstain(f"local search stopped for {start_name}") from exc
    except (ValueError, TypeError) as exc:
        raise ImplementationFailure(f"local search rejected validated inputs: {exc}") from exc
    if not isinstance(result, Mapping):
        raise ImplementationFailure("local search did not return a mapping")
    returned_key = result.get("key")
    if not isinstance(returned_key, Mapping):
        raise ImplementationFailure("local search did not return a key")
    try:
        final_key = _validate_map(returned_key, symbols, config)
    except InputMismatch as exc:
        raise ImplementationFailure(
            f"local search returned an invalid complete map: {start_name}"
        ) from exc
    final_score, final_hit_types = _score_key(final_key, counts, lexicon)
    result_score = result.get("score")
    if isinstance(result_score, bool) or not isinstance(result_score, int) or result_score != final_score:
        raise ImplementationFailure(f"local search score disagrees with exact rescoring: {start_name}")
    result_initial = result.get("initial_score")
    if (
        isinstance(result_initial, bool)
        or not isinstance(result_initial, int)
        or result_initial != initial_score
    ):
        raise ImplementationFailure(f"local search initial score disagrees: {start_name}")
    evaluation_count = result.get("evaluation_count")
    if isinstance(evaluation_count, bool) or not isinstance(evaluation_count, int) or evaluation_count < 0:
        raise ImplementationFailure("local search evaluation count is invalid")
    if evaluation_count > config.per_start_evaluation_limit:
        raise ResourceAbstain(f"local search evaluation limit exceeded: {start_name}")
    accepted_move_count = result.get("accepted_move_count")
    if (
        isinstance(accepted_move_count, bool)
        or not isinstance(accepted_move_count, int)
        or accepted_move_count < 0
        or accepted_move_count > config.move_budget
    ):
        raise ImplementationFailure("local search accepted move count is invalid")
    if final_score < initial_score:
        raise ImplementationFailure(f"local search decreased the exact score: {start_name}")
    stop_status = result.get("status")
    if not isinstance(stop_status, str) or stop_status not in LOCAL_STOP_STATUSES:
        raise ImplementationFailure(f"local search returned an invalid stop status: {start_name}")
    local_neighborhood_checked = result.get("local_neighborhood_checked")
    if not isinstance(local_neighborhood_checked, bool):
        raise ImplementationFailure("local search neighborhood status is invalid")
    if stop_status == "no_improving_move" and not local_neighborhood_checked:
        raise ImplementationFailure(
            f"local search did not check its neighborhood before stopping: {start_name}"
        )
    if stop_status in ("move_budget_exhausted", "empty_input") and local_neighborhood_checked:
        raise ImplementationFailure(
            f"local search reported an inconsistent neighborhood status: {start_name}"
        )
    output = {
        "status": "complete",
        "start": start_name,
        "initial_score": initial_score,
        "final_score": final_score,
        "score_improvement": final_score - initial_score,
        "initial_hit_type_count": initial_hit_types,
        "final_hit_type_count": final_hit_types,
        "accepted_move_count": accepted_move_count,
        "evaluation_count": evaluation_count,
        "stop_status": stop_status,
        "local_neighborhood_checked": local_neighborhood_checked,
        "key": dict(sorted(final_key.items())),
        "key_sha256": canonical_hash(dict(sorted(final_key.items()))),
        "scope_limits": [
            "The result is a feasible local-search lower bound.",
            "The search checks single-unit reassignments and two-unit swaps only.",
            "The move budget does not certify a global optimum.",
        ],
    }
    _emit(progress, {
        "stage": "local_search",
        "event": "complete",
        "start": start_name,
        "final_score": final_score,
        "evaluation_count": evaluation_count,
    })
    return output


def _source_paths() -> tuple[str, ...]:
    return (
        PROTOCOL_PATH,
        *PINNED_INPUT_ARTIFACT_HASHES,
        *PINNED_FROZEN_MODULE_HASHES,
        "experiments/search_development/run_study.py",
        "experiments/search_development/test_run_study.py",
    )


def source_hash_receipts(
    project_root: Path = ROOT,
    *,
    config: DevelopmentConfig = DEFAULT_CONFIG,
    require_pinned_sources: bool = True,
) -> dict[str, Any]:
    """Collect actual source hashes and optionally enforce the pinned set."""

    root = Path(project_root)
    actual: dict[str, str | None] = {}
    missing: list[str] = []
    for relative in _source_paths():
        path = root / relative
        if path.is_file():
            actual[relative] = sha256_path(path)
        else:
            actual[relative] = None
            missing.append(relative)
    expected = {
        **dict(config.expected_input_artifact_hashes),
        **dict(config.expected_frozen_module_hashes),
    }
    mismatches = {
        relative: {
            "expected": expected_value,
            "actual": actual.get(relative),
        }
        for relative, expected_value in expected.items()
        if actual.get(relative) != expected_value
    }
    if require_pinned_sources and (missing or mismatches):
        details = ", ".join(sorted(mismatches or {name: {} for name in missing}))
        raise InputMismatch(f"pinned source verification failed: {details}")
    return {
        "protocol_sha256": actual.get(PROTOCOL_PATH),
        "files": dict(sorted(actual.items())),
        "expected_pinned_files": len(expected),
        "pinned_mismatch_count": len(mismatches),
        "missing_file_count": len(missing),
        "pinned_verification": "enforced" if require_pinned_sources else "recorded_only",
    }


def _write_exclusive_json(path: Path, value: Mapping[str, Any]) -> str:
    payload = canonical_bytes(value)
    with path.open("xb") as handle:
        handle.write(payload)
    return sha256(payload).hexdigest()


def _key_record(
    stage: Mapping[str, Any],
    config: DevelopmentConfig,
) -> dict[str, Any]:
    return {
        "kind": "homophonic_search_development_fit_key",
        "protocol": config.protocol_name,
        "control_family": config.control_family,
        "encryption_seed": config.encryption_seed,
        "start": stage["start"],
        "capacity": config.capacity,
        "alphabet": list(config.alphabet),
        "objective": "integer weighted exact lexicon word hits",
        "initial_score": stage["initial_score"],
        "final_score": stage["final_score"],
        "score_improvement": stage["score_improvement"],
        "accepted_move_count": stage["accepted_move_count"],
        "evaluation_count": stage["evaluation_count"],
        "stop_status": stage["stop_status"],
        "local_neighborhood_checked": stage["local_neighborhood_checked"],
        "key": dict(stage["key"]),
        "scope_limits": list(stage["scope_limits"]),
    }


def _manifest(
    config: DevelopmentConfig,
    inputs: StudyInputs,
    input_summary: Mapping[str, Any],
    source_receipts: Mapping[str, Any],
    output_dir: Path,
) -> dict[str, Any]:
    return {
        "kind": "homophonic_search_development_manifest",
        "status": "started",
        "protocol": {
            "name": config.protocol_name,
            "path": config.protocol_path,
            "sha256": source_receipts.get("protocol_sha256"),
        },
        "command": ["python", "-m", "experiments.search_development.run_study"],
        "runtime": {
            "python": platform.python_version(),
            "implementation": platform.python_implementation(),
            "platform": platform.platform(),
        },
        "config": config.public(),
        "input_summary": {
            key: value
            for key, value in input_summary.items()
            if key not in {"weighted_counts_hash"}
            or isinstance(value, str)
        },
        "input_hashes": {
            "validation_stream_sha256": inputs.validation_stream_sha256,
            "training_lexicon_sha256": inputs.training_lexicon_sha256,
            "input_artifacts": dict(sorted(inputs.input_artifact_hashes.items())),
            "input_key_records": dict(sorted(inputs.input_key_hashes.items())),
            "input_reports": dict(sorted(inputs.input_report_hashes.items())),
        },
        "source_receipts": source_receipts,
        "resource_limits": {
            "root_timeout_seconds": config.root_timeout_seconds,
            "total_timeout_seconds": config.total_timeout_seconds,
            "rss_limit_bytes": config.rss_limit_bytes,
            "max_candidate_rows": config.max_candidate_rows,
            "max_estimated_storage_bytes": config.max_estimated_storage_bytes,
            "per_start_evaluation_limit": config.per_start_evaluation_limit,
            "total_evaluation_limit": config.total_evaluation_limit,
        },
        "output_paths": {
            "manifest": "manifest.json",
            "cold_selected_key": "cold_selected.key.json",
            "assisted_selected_key": "assisted_selected.key.json",
            "aggregate": "aggregate.json",
        },
        "output_directory_name": output_dir.name,
        "no_test_score": True,
    }


def _assert_public_aggregate(value: Mapping[str, Any]) -> None:
    forbidden = {
        "words",
        "ciphertext",
        "ciphertext_counts",
        "weighted_counts",
        "training_lexicon",
        "lexicon",
        "candidate_rows",
        "candidate_cache",
        "groups",
        "ungrouped_words",
        "evaluations",
        "accepted_moves",
    }

    def visit(item: Any) -> None:
        if isinstance(item, Mapping):
            for key, child in item.items():
                if key in forbidden:
                    raise ImplementationFailure(
                        f"public aggregate contains forbidden field: {key}"
                    )
                visit(child)
        elif isinstance(item, (list, tuple)):
            for child in item:
                visit(child)

    visit(value)


def run_study(
    inputs: StudyInputs | Mapping[str, Any],
    *,
    output_dir: Path | str,
    project_root: Path = ROOT,
    config: DevelopmentConfig = DEFAULT_CONFIG,
    require_pinned_sources: bool = True,
    progress: ProgressCallback | None = None,
) -> dict[str, Any]:
    """Run root bound and both starts, then write the aggregate report.

    The output directory uses four exclusive files. A partial run leaves no
    aggregate report. A supervisor can classify the raised ``StudyError`` and
    apply its own time and resident-memory limits.
    """

    if not isinstance(inputs, StudyInputs):
        inputs = StudyInputs.from_mapping(inputs)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    fixed_paths = {
        "manifest": output_path / "manifest.json",
        "cold_selected": output_path / "cold_selected.key.json",
        "assisted_selected": output_path / "assisted_selected.key.json",
        "aggregate": output_path / "aggregate.json",
    }
    existing = [str(path.name) for path in fixed_paths.values() if path.exists()]
    if existing:
        raise FileExistsError(
            "fixed development output exists: " + ", ".join(sorted(existing))
        )
    input_summary = validate_inputs(inputs, config)
    receipts = source_hash_receipts(
        project_root,
        config=config,
        require_pinned_sources=require_pinned_sources,
    )
    manifest_value = _manifest(
        config,
        inputs,
        input_summary,
        receipts,
        output_path,
    )
    manifest_hash = _write_exclusive_json(fixed_paths["manifest"], manifest_value)
    _emit(progress, {"stage": "study", "event": "manifest_written"})

    root = run_root_bound(inputs, config=config, progress=progress)
    start_results: dict[str, dict[str, Any]] = {}
    total_evaluations = 0
    for name in START_NAMES:
        stage = run_local_search(
            inputs.weighted_counts,
            inputs.training_lexicon,
            inputs.starts[name],
            pinned_score=inputs.pinned_scores[name],
            start_name=name,
            config=config,
            progress=progress,
        )
        total_evaluations += stage["evaluation_count"]
        if total_evaluations > config.total_evaluation_limit:
            raise ResourceAbstain("total local-search evaluation limit exceeded")
        record = _key_record(stage, config)
        key_hash = _write_exclusive_json(fixed_paths[name], record)
        start_results[name] = {
            key: value
            for key, value in stage.items()
            if key != "key"
        }
        start_results[name]["key_record_sha256"] = key_hash
        _emit(progress, {
            "stage": "study",
            "event": "key_written",
            "start": name,
            "final_score": stage["final_score"],
        })

    best_lower_bound = max(
        start_results[name]["final_score"] for name in START_NAMES
    )
    if best_lower_bound > root["group_bound"]:
        raise ImplementationFailure(
            "a complete local map exceeds the static root group bound"
        )
    root_public = dict(root)
    root_public["gap_to_best_lower_bound"] = root["group_bound"] - best_lower_bound
    root_public["finite_objective_value_certified"] = (
        root["group_bound"] == best_lower_bound
    )
    public = {
        "status": "development_only",
        "kind": "homophonic_search_development_v1",
        "protocol": {
            "name": config.protocol_name,
            "path": config.protocol_path,
            "sha256": receipts.get("protocol_sha256"),
        },
        "manifest_sha256": manifest_hash,
        "config": config.public(),
        "input": {
            "control_family": config.control_family,
            "encryption_seed": config.encryption_seed,
            "validation_token_count": input_summary["validation_token_count"],
            "validation_type_count": input_summary["validation_type_count"],
            "training_lexicon_type_count": input_summary["training_lexicon_type_count"],
            "cipher_unit_count": input_summary["cipher_unit_count"],
            "objective_denominator": input_summary["objective_denominator"],
            "weighted_counts_sha256": input_summary["weighted_counts_hash"],
            "validation_stream_sha256": inputs.validation_stream_sha256,
            "fit_splits": {
                "lexicon_split": "train",
                "ciphertext_split": "validation",
                "test_scored": False,
            },
            "training_lexicon_sha256": inputs.training_lexicon_sha256,
            "input_artifact_hashes": dict(sorted(inputs.input_artifact_hashes.items())),
            "input_key_record_hashes": dict(sorted(inputs.input_key_hashes.items())),
            "input_report_hashes": dict(sorted(inputs.input_report_hashes.items())),
        },
        "source_receipts": receipts,
        "root": root_public,
        "starts": start_results,
        "best_lower_bound": best_lower_bound,
        "comparison": {
            "best_lower_bound": best_lower_bound,
            "group_bound": root["group_bound"],
            "gap": root["group_bound"] - best_lower_bound,
            "finite_objective_value_certified": root["group_bound"] == best_lower_bound,
            "key_uniqueness_certified": False,
        },
        "resource": {
            "limits": {
                "root_timeout_seconds": config.root_timeout_seconds,
                "total_timeout_seconds": config.total_timeout_seconds,
                "rss_limit_bytes": config.rss_limit_bytes,
                "max_candidate_rows": config.max_candidate_rows,
                "max_estimated_storage_bytes": config.max_estimated_storage_bytes,
                "per_start_evaluation_limit": config.per_start_evaluation_limit,
                "total_evaluation_limit": config.total_evaluation_limit,
            },
            "observed_rss_enforced_by": "supervisor",
            "observed_time_enforced_by": "supervisor",
            "total_evaluation_count": total_evaluations,
        },
        "scope_limits": [
            "This is a development-only finite Italian control result.",
            "The root value is a static pivot-group relaxation.",
            "The two starts use local single-unit and two-unit moves only.",
            "The result does not score the test partition.",
            "The result does not claim language, translation, decipherment, or a manuscript reading.",
        ],
    }
    _assert_public_aggregate(public)
    _write_exclusive_json(fixed_paths["aggregate"], public)
    _emit(progress, {
        "stage": "study",
        "event": "aggregate_written",
        "best_lower_bound": best_lower_bound,
        "gap": root["group_bound"] - best_lower_bound,
    })
    return json.loads(canonical_bytes(public))


# Explicit names for supervisors that run each stage in a bounded child.
run_root_stage = run_root_bound
run_local_stage = run_local_search


def load_pinned_italian_inputs(project_root: Path = ROOT) -> StudyInputs:
    """Load fixed Italian train and validation inputs without scoring test data."""

    from experiments.homophonic.controls import encrypt_words, seeded_control_key
    from experiments.lexicon.run_pilot import canonical_hash, count_words, objective_weights
    from voynich.reference import load_reference_partitions

    root = Path(project_root)
    data = load_reference_partitions(root)["italian_old"]
    train_words = list(data["words"]["train"])
    validation_words = list(data["words"]["validation"])
    planted = seeded_control_key(CONTROL_FAMILY, ENCRYPTION_SEED)
    encrypted_validation = encrypt_words(validation_words, planted)
    raw_counts = count_words(encrypted_validation)
    _weights, _tokens, _types, _denominator = objective_weights(raw_counts)
    starts: dict[str, dict[str, str]] = {}
    pinned_scores: dict[str, int] = {}
    key_hashes: dict[str, str] = {}
    report_hashes: dict[str, str] = {}
    report_paths = {
        "cold_selected": root / "reports/homophonic-feasibility-v1/italian-cold.json",
        "assisted_selected": root / "reports/homophonic-feasibility-v1/italian-assisted.json",
    }
    key_paths = {
        "cold_selected": root / "reports/homophonic-feasibility-v1/italian-cold.keys.json",
        "assisted_selected": root / "reports/homophonic-feasibility-v1/italian-assisted.keys.json",
    }
    for name in START_NAMES:
        key_record = json.loads(key_paths[name].read_text(encoding="utf-8"))
        report = json.loads(report_paths[name].read_text(encoding="utf-8"))
        starts[name] = dict(key_record["key"])
        pinned_scores[name] = report["objective"]["score_from_key"]
        key_hashes[name] = sha256_path(key_paths[name])
        report_hashes[name] = sha256_path(report_paths[name])
        if report.get("key_record_sha256") != key_hashes[name]:
            raise InputMismatch(f"selected key record hash disagrees with report: {name}")
    input_artifacts = {
        relative: sha256_path(root / relative)
        for relative in PINNED_INPUT_ARTIFACT_HASHES
    }
    return StudyInputs.from_raw_counts(
        raw_counts,
        train_words,
        starts=starts,
        pinned_scores=pinned_scores,
        validation_stream_sha256=canonical_hash(encrypted_validation),
        training_lexicon_sha256=_lexicon_hash(
            tuple(_normalise_word(word) for word in train_words)
        ),
        input_artifact_hashes=input_artifacts,
        input_key_hashes=key_hashes,
        input_report_hashes=report_hashes,
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        help="Private synthetic JSON input. Omit for the fixed Italian input.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help=f"Exclusive output directory; default: {DEFAULT_OUTPUT_DIR}",
    )
    parser.add_argument("--project-root", type=Path, default=ROOT)
    parser.add_argument(
        "--allow-unpinned-inputs",
        action="store_true",
        help="Record source hashes without enforcing the fixed development set.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run one fixed-input study and emit only five safe progress events."""

    args = _build_parser().parse_args(argv)
    if (args.input is None) != (args.output_dir is None):
        # An explicit output path selects private input mode. An explicit input
        # path without an output would make output placement ambiguous.
        _build_parser().error("--input and --output-dir must be supplied together")

    progress_state = {
        "local_started": False,
        "local_completed": False,
        "phase": None,
    }

    def progress(event: dict[str, Any]) -> None:
        # Keep child stdout to the supervisor protocol. Do not print aggregate
        # values here because the supervisor treats every line as private
        # progress and must not ingest scores or bounds.
        stage = event.get("stage")
        event_name = event.get("event")
        output_event: dict[str, str] | None = None
        if stage == "root_bound" and event_name in {"start", "complete"}:
            progress_state["phase"] = "root_bound"
            output_event = {
                "event": "progress",
                "phase": "root_bound",
                "state": "running" if event_name == "start" else "complete",
            }
        elif stage == "local_search" and event_name == "start" and not progress_state["local_started"]:
            progress_state["phase"] = "local_search"
            progress_state["local_started"] = True
            output_event = {
                "event": "progress",
                "phase": "local_search",
                "state": "running",
            }
        elif (
            stage == "local_search"
            and event_name == "complete"
            and event.get("start") == "assisted_selected"
            and not progress_state["local_completed"]
        ):
            progress_state["local_completed"] = True
            output_event = {
                "event": "progress",
                "phase": "local_search",
                "state": "complete",
            }
        elif stage == "study" and event_name == "aggregate_written":
            output_event = {"event": "complete", "status": "development_only"}
        if output_event is not None:
            print(json.dumps(output_event, sort_keys=True, separators=(",", ":")), flush=True)

    try:
        if args.input is not None:
            payload = json.loads(args.input.read_text(encoding="utf-8"))
            inputs: StudyInputs = StudyInputs.from_mapping(payload)
            output_dir = args.output_dir
            require_pinned_sources = not args.allow_unpinned_inputs
        else:
            inputs = load_pinned_italian_inputs(args.project_root)
            output_dir = args.project_root / DEFAULT_OUTPUT_DIR
            require_pinned_sources = True
        run_study(
            inputs,
            output_dir=output_dir,
            project_root=args.project_root,
            require_pinned_sources=require_pinned_sources,
            progress=progress,
        )
    except (ResourceAbstain, InputMismatch, ImplementationFailure, FileExistsError) as exc:
        if isinstance(exc, ResourceAbstain):
            kind = "resource_abstain"
        elif isinstance(exc, InputMismatch):
            kind = "input_mismatch"
        elif isinstance(exc, FileExistsError):
            kind = "output_exists"
        else:
            kind = "implementation_failure"
        error_event: dict[str, str] = {"event": "error", "kind": kind}
        if progress_state["phase"] is not None:
            error_event["phase"] = progress_state["phase"]
        print(json.dumps(error_event, separators=(",", ":")), flush=True)
        return 2
    except (ValueError, TypeError, OSError, KeyError):
        error_event = {"event": "error", "kind": "input_mismatch"}
        if progress_state["phase"] is not None:
            error_event["phase"] = progress_state["phase"]
        print(json.dumps(error_event, separators=(",", ":")), flush=True)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "ALPHABET",
    "CONTROL_FAMILY",
    "DEFAULT_CONFIG",
    "DEFAULT_OUTPUT_DIR",
    "DevelopmentConfig",
    "ENCRYPTION_SEED",
    "InputMismatch",
    "ImplementationFailure",
    "PINNED_FROZEN_MODULE_HASHES",
    "PINNED_INPUT_ARTIFACT_HASHES",
    "ResourceAbstain",
    "START_NAMES",
    "StudyError",
    "StudyInputs",
    "canonical_bytes",
    "canonical_hash",
    "load_pinned_italian_inputs",
    "run_local_search",
    "run_local_stage",
    "run_root_bound",
    "run_root_stage",
    "run_study",
    "sha256_path",
    "source_hash_receipts",
    "validate_inputs",
]
