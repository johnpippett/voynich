"""Finite-window word-similarity scores for declared unit words.

The model uses only immutable tuples supplied by the caller. It fits a
smoothed unigram distribution from training lines, then scores later lines
with exact-copy and exact-edit context kernels. It is a finite metric. It
makes no translation or historical-process claim.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
import math
from typing import TypeAlias


Word: TypeAlias = tuple[str, ...]
VocabularyItem: TypeAlias = Word | str

UNK = "<UNK>"
ALPHA = 0.1
WINDOWS = (1, 4, 16)
LAMBDAS = (0.0, 0.1, 0.25, 0.5, 0.75)
FAMILIES = ("exact", "edit")


def _validate_word(word: object, *, name: str = "word") -> Word:
    """Validate one immutable unit-word tuple without changing its units."""

    if not isinstance(word, tuple):
        raise TypeError(f"{name} must be a tuple of unit strings")
    for unit in word:
        if not isinstance(unit, str) or not unit:
            raise ValueError(f"{name} units must be non-empty strings")
    return word


def _normalise_lines(lines: Iterable[object], *, name: str) -> tuple[tuple[Word, ...], ...]:
    """Validate lines and words, while keeping line boundaries explicit."""

    if isinstance(lines, (str, bytes)):
        raise TypeError(f"{name} must contain lines")
    try:
        iterator = iter(lines)
    except TypeError as exc:
        raise TypeError(f"{name} must be iterable") from exc
    normalised: list[tuple[Word, ...]] = []
    for line_number, line in enumerate(iterator):
        if not isinstance(line, tuple):
            raise TypeError(f"{name} line {line_number} must be a tuple")
        words: list[Word] = []
        for word_number, word in enumerate(line):
            words.append(
                _validate_word(
                    word,
                    name=f"{name} line {line_number} word {word_number}",
                )
            )
        normalised.append(tuple(words))
    return tuple(normalised)


def _validate_model(model: object) -> "UnigramModel":
    if not isinstance(model, UnigramModel):
        raise TypeError("model must be a UnigramModel")
    return model


def _validate_family(family: object) -> str:
    if family not in ("baseline", "exact", "edit"):
        raise ValueError("family must be baseline, exact, or edit")
    return family


def _validate_window(window: object) -> int:
    if not isinstance(window, int) or isinstance(window, bool) or window < 1:
        raise ValueError("window must be a positive integer")
    return window


def _validate_lambda(lambda_: object) -> float:
    if isinstance(lambda_, bool) or not isinstance(lambda_, (int, float)):
        raise ValueError("lambda_ must be a finite number from 0 through 0.75")
    value = float(lambda_)
    if not math.isfinite(value) or value < 0.0 or value > 0.75:
        raise ValueError("lambda_ must be a finite number from 0 through 0.75")
    return value


@dataclass(frozen=True, slots=True)
class UnigramModel:
    """Frozen unigram counts and probabilities fitted from training lines."""

    real_vocabulary: tuple[Word, ...]
    vocabulary: tuple[VocabularyItem, ...]
    count_items: tuple[tuple[VocabularyItem, int], ...]
    p0_items: tuple[tuple[VocabularyItem, float], ...]
    train_word_count: int
    train_line_count: int
    singleton_type_count: int
    alpha: float
    status: str

    @property
    def counts(self) -> dict[VocabularyItem, int]:
        """Return mapped training counts as a new dictionary."""

        return dict(self.count_items)

    @property
    def p0(self) -> dict[VocabularyItem, float]:
        """Return the smoothed unigram distribution as a new dictionary."""

        return dict(self.p0_items)

    def map_target(self, word: Word) -> VocabularyItem:
        """Map a target word to its repeated training type or ``UNK``."""

        _validate_word(word)
        return word if word in self.real_vocabulary else UNK


def fit_unigram(train_lines: Iterable[object]) -> UnigramModel:
    """Fit the fixed-alpha mapped unigram model from training lines only."""

    lines = _normalise_lines(train_lines, name="train_lines")
    raw_counts: Counter[Word] = Counter(
        word for line in lines for word in line
    )
    real_vocabulary = tuple(
        sorted(word for word, count in raw_counts.items() if count >= 2)
    )
    real_set = set(real_vocabulary)
    singleton_total = sum(
        count for word, count in raw_counts.items() if word not in real_set
    )
    counts: dict[VocabularyItem, int] = {
        word: raw_counts[word] for word in real_vocabulary
    }
    counts[UNK] = singleton_total
    vocabulary: tuple[VocabularyItem, ...] = (*real_vocabulary, UNK)
    total = sum(counts.values())
    denominator = total + ALPHA * len(vocabulary)
    if total == 0:
        p0 = {item: (1.0 if item == UNK else 0.0) for item in vocabulary}
    else:
        p0 = {
            item: (counts[item] + ALPHA) / denominator
            for item in vocabulary
        }
    return UnigramModel(
        real_vocabulary=real_vocabulary,
        vocabulary=vocabulary,
        count_items=tuple((item, counts[item]) for item in vocabulary),
        p0_items=tuple((item, p0[item]) for item in vocabulary),
        train_word_count=total,
        train_line_count=len(lines),
        singleton_type_count=sum(
            1 for word, count in raw_counts.items() if word not in real_set
        ),
        alpha=ALPHA,
        status=("ok" if real_vocabulary else "degenerate_no_real_vocabulary"),
    )


def levenshtein_distance(left: Word, right: Word) -> int:
    """Return standard insertion, deletion, and substitution distance."""

    left = _validate_word(left, name="left")
    right = _validate_word(right, name="right")
    if len(left) < len(right):
        left, right = right, left
    previous = list(range(len(right) + 1))
    for left_unit_index, left_unit in enumerate(left, start=1):
        current = [left_unit_index]
        for right_unit_index, right_unit in enumerate(right, start=1):
            current.append(
                min(
                    current[-1] + 1,
                    previous[right_unit_index] + 1,
                    previous[right_unit_index - 1]
                    + (left_unit != right_unit),
                )
            )
        previous = current
    return previous[-1]


def _zero_distribution(model: UnigramModel) -> dict[VocabularyItem, float]:
    return {item: 0.0 for item in model.vocabulary}


def k0_distribution(model: UnigramModel, context: Word) -> dict[VocabularyItem, float]:
    """Return the exact-copy kernel for one raw context word."""

    model = _validate_model(model)
    context = _validate_word(context, name="context")
    if context not in model.real_vocabulary:
        return model.p0
    result = _zero_distribution(model)
    result[context] = 1.0
    return result


def k1_distribution(model: UnigramModel, context: Word) -> dict[VocabularyItem, float]:
    """Return the exact-distance-one kernel for one raw context word."""

    model = _validate_model(model)
    context = _validate_word(context, name="context")
    neighbours = tuple(
        word
        for word in model.real_vocabulary
        if levenshtein_distance(word, context) == 1
    )
    if not neighbours:
        return model.p0
    p0 = model.p0
    normalizer = math.fsum(p0[word] for word in neighbours)
    result = _zero_distribution(model)
    for word in neighbours:
        result[word] = p0[word] / normalizer
    return result


def fixed_mixture(
    model: UnigramModel,
    contexts: Iterable[object],
    *,
    family: str,
    lambda_: float,
) -> dict[VocabularyItem, float]:
    """Mix the baseline with a uniform kernel over the supplied contexts."""

    model = _validate_model(model)
    family = _validate_family(family)
    lambda_value = _validate_lambda(lambda_)
    if family == "baseline":
        return model.p0
    context_words = tuple(
        _validate_word(context, name="context") for context in contexts
    )
    if not context_words or lambda_value == 0.0:
        return model.p0
    kernel = k0_distribution if family == "exact" else k1_distribution
    distributions = [kernel(model, context) for context in context_words]
    result: dict[VocabularyItem, float] = {}
    p0 = model.p0
    for item in model.vocabulary:
        mean_kernel = math.fsum(
            distribution[item] for distribution in distributions
        ) / len(distributions)
        result[item] = (1.0 - lambda_value) * p0[item] + lambda_value * mean_kernel
    return result


def _score_record(
    *,
    family: str,
    window: int,
    lambda_value: float,
    line_count: int,
    target_count: int,
    target_unk_count: int,
    context_count: int,
    context_oov_count: int,
    total_bits: float | None,
    model_status: str,
) -> dict[str, object]:
    bits_per_target = (
        total_bits / target_count if target_count else None
    )
    return {
        "status": "ok" if target_count else "no_targets",
        "family": family,
        "window": window,
        "lambda": lambda_value,
        "line_count": line_count,
        "group_count": None,
        "target_count": target_count,
        "target_unk_count": target_unk_count,
        "target_unk_rate": (
            target_unk_count / target_count if target_count else None
        ),
        "context_count": context_count,
        "context_oov_count": context_oov_count,
        "context_oov_rate": (
            context_oov_count / context_count if context_count else None
        ),
        "total_bits": total_bits,
        "mapped_target_loss_bits": total_bits,
        "bits_per_target": bits_per_target,
        "model_status": model_status,
    }


def score_lines(
    model: UnigramModel,
    lines: Iterable[object],
    *,
    family: str,
    window: int,
    lambda_: float,
    cache: bool = True,
) -> dict[str, object]:
    """Score positions after line starts with one fixed model setting."""

    model = _validate_model(model)
    family = _validate_family(family)
    window = _validate_window(window)
    lambda_value = _validate_lambda(lambda_)
    if not isinstance(cache, bool):
        raise TypeError("cache must be a boolean")
    normalised_lines = _normalise_lines(lines, name="lines")
    p0 = model.p0
    distribution_cache: dict[Word, dict[VocabularyItem, float]] = {}
    losses: list[float] = []
    target_count = 0
    target_unk_count = 0
    context_count = 0
    context_oov_count = 0
    for line in normalised_lines:
        for position in range(1, len(line)):
            target = model.map_target(line[position])
            target_count += 1
            target_unk_count += int(target == UNK)
            contexts = line[max(0, position - window) : position]
            context_count += len(contexts)
            context_oov_count += sum(
                context not in model.real_vocabulary for context in contexts
            )
            if family == "baseline" or lambda_value == 0.0:
                probability = p0[target]
            else:
                kernel = k0_distribution if family == "exact" else k1_distribution
                distributions: list[dict[VocabularyItem, float]] = []
                for context in contexts:
                    if cache and context in distribution_cache:
                        distribution = distribution_cache[context]
                    else:
                        distribution = kernel(model, context)
                        if cache:
                            distribution_cache[context] = distribution
                    distributions.append(distribution)
                mean_kernel = math.fsum(
                    distribution[target] for distribution in distributions
                ) / len(distributions)
                probability = (
                    (1.0 - lambda_value) * p0[target]
                    + lambda_value * mean_kernel
                )
            if not math.isfinite(probability) or probability <= 0.0:
                raise AssertionError("model produced a non-positive probability")
            losses.append(-math.log2(probability))
    total_bits = math.fsum(losses) if losses else None
    return _score_record(
        family=family,
        window=window,
        lambda_value=lambda_value,
        line_count=len(normalised_lines),
        target_count=target_count,
        target_unk_count=target_unk_count,
        context_count=context_count,
        context_oov_count=context_oov_count,
        total_bits=total_bits,
        model_status=model.status,
    )


def _choice_from_score(score: dict[str, object]) -> dict[str, object]:
    return {
        "family": score["family"],
        "window": score["window"],
        "lambda": score["lambda"],
        "total_bits": score["total_bits"],
        "bits_per_target": score["bits_per_target"],
        "target_count": score["target_count"],
    }


def select_settings(
    model: UnigramModel,
    validation_lines: Iterable[object],
) -> dict[str, object]:
    """Select each fixed kernel family from the predeclared validation grid."""

    model = _validate_model(model)
    lines = _normalise_lines(validation_lines, name="validation_lines")
    validation_grid: list[dict[str, object]] = []
    choices: dict[str, dict[str, object] | None] = {}
    for family in FAMILIES:
        family_scores: list[dict[str, object]] = []
        for window in WINDOWS:
            for lambda_value in LAMBDAS:
                score = score_lines(
                    model,
                    lines,
                    family=family,
                    window=window,
                    lambda_=lambda_value,
                )
                family_scores.append(score)
                validation_grid.append(score)
        if not family_scores or family_scores[0]["target_count"] == 0:
            choices[family] = None
        else:
            best = min(
                family_scores,
                key=lambda score: (
                    score["total_bits"],
                    score["lambda"],
                    score["window"],
                ),
            )
            choices[family] = _choice_from_score(best)
    target_count = int(validation_grid[0]["target_count"]) if validation_grid else 0
    return {
        "status": (
            "selected" if target_count else "abstain_no_validation_targets"
        ),
        "validation_line_count": len(lines),
        "validation_target_count": target_count,
        "validation_grid": validation_grid,
        "choice": choices,
        "windows": list(WINDOWS),
        "lambdas": list(LAMBDAS),
        "families": list(FAMILIES),
        "tie_break": ["smaller_lambda", "smaller_window"],
        "model_status": model.status,
    }
