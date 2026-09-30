"""Search fixed substitution keys with unknown cipher values."""

from collections import Counter
import math
import random

from experiments.spacefree_substitution.score import NGramModel


ALPHA = 0.1
WEIGHTS = (0.1, 0.2, 0.3, 0.4)
RESTARTS = 8
PROPOSALS_PER_RESTART = 2000
SEARCH_SEED = 408
DRIFT_ABS_TOLERANCE = 1e-8
DRIFT_REL_TOLERANCE = 1e-12
UNKNOWN_WINDOW_COST = math.log2(26)


def _cipher_positions(model, symbols):
    """Return valid cipher indices and unknown entries."""
    if isinstance(symbols, str):
        positions = model.indices(symbols)
    else:
        try:
            positions = tuple(symbols)
        except TypeError as error:
            raise ValueError("Cipher symbols must be a string or a sequence.") from error

    alphabet_size = len(model.alphabet)
    for position in positions:
        if position is None:
            continue
        if isinstance(position, bool) or not isinstance(position, int):
            raise ValueError("Cipher positions must be integers or None.")
        if not 0 <= position < alphabet_size:
            raise ValueError("Cipher positions must be inside the model alphabet.")
    return positions


def _validate_key(model, key):
    """Make sure that the key is a full alphabet permutation."""
    try:
        valid = (len(key) == len(model.alphabet)
                 and set(key) == set(range(len(model.alphabet))))
    except TypeError:
        valid = False
    if not valid:
        raise ValueError("The key must be a permutation of the alphabet positions.")


def score_with_unknown(model, symbols, key):
    """Score every overlapping window, including windows with unknowns."""
    positions = _cipher_positions(model, symbols)
    if len(positions) < 4:
        raise ValueError("A scored stream must contain at least four symbols.")
    _validate_key(model, key)

    size = len(model.alphabet)
    table = model.window_costs
    total = 0.0
    unknown_window_count = 0
    for offset in range(len(positions) - 3):
        window = positions[offset:offset + 4]
        if any(position is None for position in window):
            total += UNKNOWN_WINDOW_COST
            unknown_window_count += 1
            continue

        first, second, third, fourth = window
        index = (((key[first] * size + key[second]) * size + key[third])
                 * size + key[fourth])
        total += table[index]

    window_count = len(positions) - 3
    return {
        "total_cost": total,
        "mean_cost": total / window_count,
        "window_count": window_count,
        "unknown_window_count": unknown_window_count,
        "mapped_window_count": window_count - unknown_window_count,
    }


def _frequency_key(model, fit_symbols):
    """Pair known cipher symbols and training symbols by descending frequency."""
    cipher_counts = Counter(
        symbol for symbol in fit_symbols if symbol is not None
    )
    alphabet = model.alphabet
    plain_rank = sorted(
        range(len(alphabet)),
        key=lambda index: (-model.training_symbol_counts.get(alphabet[index], 0), index),
    )
    cipher_rank = sorted(
        range(len(alphabet)),
        key=lambda index: (-cipher_counts.get(index, 0), index),
    )
    key = [0] * len(alphabet)
    for cipher_index, plain_index in zip(cipher_rank, plain_rank):
        key[cipher_index] = plain_index
    return key


def _affected_windows(symbols, alphabet_size):
    """Build distinct fully mapped windows and their swap dependencies."""
    window_counts = Counter(
        symbols[start:start + 4]
        for start in range(len(symbols) - 3)
        if all(symbol is not None for symbol in symbols[start:start + 4])
    )
    windows = tuple(window_counts)
    multiplicities = tuple(window_counts.values())
    by_symbol = [set() for _ in range(alphabet_size)]
    for window_index, window in enumerate(windows):
        for symbol in set(window):
            by_symbol[symbol].add(window_index)

    unions = {}
    for first in range(alphabet_size):
        for second in range(first + 1, alphabet_size):
            unions[(first, second)] = tuple(sorted(by_symbol[first] | by_symbol[second]))
    return windows, multiplicities, unions


def _window_index(window, key, size):
    """Return the flat cost-table index for one four-symbol window."""
    return (((key[window[0]] * size + key[window[1]]) * size + key[window[2]])
            * size + key[window[3]])


def search_key(model, fit_ciphertext):
    """Find a full key with the fixed multi-start swap search."""
    fit_symbols = _cipher_positions(model, fit_ciphertext)
    if len(fit_symbols) < 4:
        raise ValueError("The fitting stream must contain at least four symbols.")

    alphabet_size = len(model.alphabet)
    windows, multiplicities, affected = _affected_windows(fit_symbols, alphabet_size)
    window_count = len(fit_symbols) - 3
    mapped_window_count = sum(multiplicities)
    if mapped_window_count == 0:
        raise ValueError("The fitting stream must contain a fully mapped four-symbol window.")
    unknown_window_count = window_count - mapped_window_count

    table = model.window_costs
    rng = random.Random(SEARCH_SEED)
    best_key = None
    best_cost = math.inf
    restart_records = []

    for restart in range(RESTARTS):
        if restart == 0:
            key = _frequency_key(model, fit_symbols)
            start_kind = "frequency_rank"
        else:
            key = list(range(alphabet_size))
            rng.shuffle(key)
            start_kind = "random_permutation"

        current_cost = score_with_unknown(model, fit_symbols, key)["total_cost"]
        initial_cost = current_cost
        if current_cost < best_cost:
            best_cost = current_cost
            best_key = key.copy()

        accepted = 0
        uphill_proposals = 0
        for proposal in range(PROPOSALS_PER_RESTART):
            first, second = rng.sample(range(alphabet_size), 2)
            if first > second:
                first, second = second, first
            old_first = key[first]
            old_second = key[second]
            key[first], key[second] = old_second, old_first

            delta = 0.0
            for window_index in affected[(first, second)]:
                window = windows[window_index]
                old_values = tuple(
                    old_first if symbol == first else
                    old_second if symbol == second else key[symbol]
                    for symbol in window
                )
                old_index = (((old_values[0] * alphabet_size + old_values[1])
                              * alphabet_size + old_values[2])
                             * alphabet_size + old_values[3])
                new_index = _window_index(window, key, alphabet_size)
                delta += multiplicities[window_index] * (
                    table[new_index] - table[old_index]
                )

            temperature = (0.02 * window_count
                           * (1 - proposal / (PROPOSALS_PER_RESTART - 1)))
            if delta <= 0:
                accept = True
            elif temperature > 0:
                uphill_proposals += 1
                accept = rng.random() < math.exp(-delta / temperature)
            else:
                uphill_proposals += 1
                accept = False

            if accept:
                current_cost += delta
                accepted += 1
                if current_cost < best_cost:
                    best_cost = current_cost
                    best_key = key.copy()
            else:
                key[first], key[second] = old_first, old_second

        final_cost = score_with_unknown(model, fit_symbols, key)["total_cost"]
        drift = abs(final_cost - current_cost)
        if not math.isclose(
                final_cost, current_cost,
                rel_tol=DRIFT_REL_TOLERANCE,
                abs_tol=DRIFT_ABS_TOLERANCE):
            raise ArithmeticError("Incremental score drift exceeded its limit.")

        restart_records.append({
            "restart": restart,
            "start_kind": start_kind,
            "initial_cost": initial_cost,
            "accepted_moves": accepted,
            "uphill_proposals": uphill_proposals,
            "final_incremental_cost": current_cost,
            "final_recomputed_cost": final_cost,
            "final_drift": drift,
            "final_key_positions": list(key),
        })

    exact_best = score_with_unknown(model, fit_symbols, best_key)
    exact_best_cost = exact_best["total_cost"]
    best_drift = abs(exact_best_cost - best_cost)
    if not math.isclose(
            exact_best_cost, best_cost,
            rel_tol=DRIFT_REL_TOLERANCE,
            abs_tol=DRIFT_ABS_TOLERANCE):
        raise ArithmeticError("Best-key score drift exceeded its limit.")

    return {
        "key_positions": best_key,
        "best_incremental_cost": best_cost,
        "best_recomputed_cost": exact_best_cost,
        "best_score_drift": best_drift,
        "window_count": window_count,
        "unknown_window_count": unknown_window_count,
        "mapped_window_count": mapped_window_count,
        "temperature_start": 0.02 * window_count,
        "restarts": restart_records,
        "settings": {
            "search_seed": SEARCH_SEED,
            "restarts": RESTARTS,
            "proposals_per_restart": PROPOSALS_PER_RESTART,
            "temperature_start": 0.02 * window_count,
            "temperature_schedule": "T0 * (1 - proposal_index / 1999), proposal_index 0..1999.",
            "proposal_draw": "rng.sample(range(alphabet_size), 2).",
            "uphill_acceptance_draw": "Only uphill moves at positive temperature draw rng.random().",
            "zero_temperature": "Reject uphill proposals; accept equal and downhill proposals.",
            "restart_rng": "Fresh Random(408) per control; one stream across its restarts.",
            "tie_policy": "Keep the earlier key when costs are equal.",
            "drift_absolute_tolerance": DRIFT_ABS_TOLERANCE,
            "drift_relative_tolerance": DRIFT_REL_TOLERANCE,
        },
    }


__all__ = ["NGramModel", "score_with_unknown", "search_key"]
