"""Build and search the fixed four-context substitution score."""

from collections import Counter
import math
import random


ALPHA = 0.1
WEIGHTS = (0.1, 0.2, 0.3, 0.4)
RESTARTS = 8
PROPOSALS_PER_RESTART = 2000
SEARCH_SEED = 408
DRIFT_ABS_TOLERANCE = 1e-8
DRIFT_REL_TOLERANCE = 1e-12


class NGramModel:
    """Store smoothed conditional costs for one training stream."""

    def __init__(self, alphabet, training_text):
        if not isinstance(alphabet, str) or len(alphabet) < 2:
            raise ValueError("The alphabet must contain at least two symbols.")
        if len(set(alphabet)) != len(alphabet):
            raise ValueError("The alphabet must not contain duplicate symbols.")
        if len(training_text) < 4:
            raise ValueError("The training stream must contain at least four symbols.")
        unknown = set(training_text).difference(alphabet)
        if unknown:
            raise ValueError("The training stream has symbols outside its alphabet.")

        self.alphabet = alphabet
        self.symbol_index = {symbol: index for index, symbol in enumerate(alphabet)}
        self.training_symbol_counts = Counter(training_text)
        self.ngram_counts = []
        self.context_totals = []
        self.conditional_costs = []

        size = len(alphabet)
        for context_length in range(4):
            counts = Counter(
                training_text[position - context_length:position + 1]
                for position in range(context_length, len(training_text))
            )
            totals = Counter()
            for gram, count in counts.items():
                totals[gram[:-1]] += count
            self.ngram_counts.append(counts)
            self.context_totals.append(totals)

            costs_by_context = {}
            for context, total in totals.items():
                denominator = total + ALPHA * size
                costs_by_context[context] = tuple(
                    -math.log2(
                        (counts.get(context + symbol, 0) + ALPHA) / denominator
                    )
                    for symbol in alphabet
                )
            self.conditional_costs.append(costs_by_context)

        self.window_costs = self._build_window_costs()

    def _build_window_costs(self):
        """Build a cost for each possible four-symbol plaintext window."""
        alphabet_size = len(self.alphabet)
        uniform_row = (-math.log2(1 / alphabet_size),) * alphabet_size
        uniform_costs = (uniform_row,) * 4
        table = []
        for first in range(alphabet_size):
            for second in range(alphabet_size):
                for third in range(alphabet_size):
                    contexts = (
                        "",
                        self.alphabet[third],
                        self.alphabet[second] + self.alphabet[third],
                        self.alphabet[first] + self.alphabet[second] + self.alphabet[third],
                    )
                    costs = tuple(
                        self.conditional_costs[index].get(context, uniform_costs[index])
                        for index, context in enumerate(contexts)
                    )
                    for fourth in range(alphabet_size):
                        table.append(sum(
                            weight * costs[index][fourth]
                            for index, weight in enumerate(WEIGHTS)
                        ))
        return table

    def indices(self, text):
        """Map a symbol stream to alphabet positions."""
        try:
            return tuple(self.symbol_index[symbol] for symbol in text)
        except KeyError as error:
            raise ValueError("A stream has symbols outside its alphabet.") from error

    def score_indices(self, symbols, key):
        """Return the sum of overlapping window costs after substitution."""
        if len(symbols) < 4:
            raise ValueError("A scored stream must contain at least four symbols.")
        if len(key) != len(self.alphabet) or set(key) != set(range(len(self.alphabet))):
            raise ValueError("The key must be a permutation of the alphabet positions.")

        size = len(self.alphabet)
        table = self.window_costs
        total = 0.0
        for offset in range(len(symbols) - 3):
            first, second, third, fourth = symbols[offset:offset + 4]
            index = (((key[first] * size + key[second]) * size + key[third])
                     * size + key[fourth])
            total += table[index]
        return total

    def score_text(self, text):
        """Calculate the plaintext score with the identity substitution."""
        return self.score_indices(
            self.indices(text), tuple(range(len(self.alphabet)))
        )

    def counts_record(self):
        """Return the private training counts needed to reproduce the model."""
        return {
            "alphabet": self.alphabet,
            "alpha": ALPHA,
            "weights": list(WEIGHTS),
            "context_policy": "Count each context only when its target follows.",
            "training_symbol_counts": {
                symbol: self.training_symbol_counts.get(symbol, 0)
                for symbol in self.alphabet
            },
            "ngram_counts": [
                {
                    "context_length": context_length,
                    "counts": dict(sorted(counts.items())),
                    "context_totals": dict(sorted(self.context_totals[context_length].items())),
                }
                for context_length, counts in enumerate(self.ngram_counts)
            ],
        }


def _frequency_key(model, fit_symbols):
    """Pair descending training and fitting symbol ranks."""
    cipher_counts = Counter(fit_symbols)
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
    """Build one distinct window list for each possible swap."""
    window_counts = Counter(
        symbols[start:start + 4] for start in range(len(symbols) - 3)
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
    """Return the flat cost-table index for one window."""
    return (((key[window[0]] * size + key[window[1]]) * size + key[window[2]])
            * size + key[window[3]])


def search_key(model, fit_ciphertext):
    """Fit a permutation with the fixed multi-start swap search."""
    fit_symbols = model.indices(fit_ciphertext)
    if len(fit_symbols) < 4:
        raise ValueError("The fitting stream must contain at least four symbols.")

    alphabet_size = len(model.alphabet)
    windows, multiplicities, affected = _affected_windows(fit_symbols, alphabet_size)
    window_count = len(fit_symbols) - 3
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

        current_cost = model.score_indices(fit_symbols, key)
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

        final_cost = model.score_indices(fit_symbols, key)
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

    exact_best_cost = model.score_indices(fit_symbols, best_key)
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
