"""Descriptive measures and conditional word-order tests."""

from collections import Counter, defaultdict
from functools import lru_cache
import math
import random
import statistics


def entropy(counts):
    total = sum(counts.values())
    return -sum((n / total) * math.log2(n / total) for n in counts.values() if n) if total else 0.0


def within_word_entropy(tokens):
    characters = Counter(c for token in tokens for c in token)
    contexts = defaultdict(Counter)
    for token in tokens:
        for a, b in zip(token, token[1:]):
            contexts[a][b] += 1
    transitions = sum(sum(counts.values()) for counts in contexts.values())
    h2 = sum(sum(c.values()) * entropy(c) for c in contexts.values()) / transitions if transitions else 0.0
    return {
        'h1_bits_per_eva_character': entropy(characters),
        'h2_bits_per_within_word_transition': h2,
        'within_word_transitions': transitions,
        'note': 'Empirical estimates; word boundaries excluded. EVA characters are not established linguistic units.',
    }


@lru_cache(maxsize=262144)
def edit_distance_at_most_one(a, b):
    if abs(len(a) - len(b)) > 1:
        return False
    if len(a) == len(b):
        return sum(x != y for x, y in zip(a, b)) <= 1
    if len(a) > len(b):
        a, b = b, a
    i = j = errors = 0
    while i < len(a) and j < len(b):
        if a[i] == b[j]:
            i += 1
            j += 1
        else:
            errors += 1
            j += 1
            if errors > 1:
                return False
    return True


def holm_adjust(p_values):
    order = sorted(range(len(p_values)), key=lambda i: p_values[i])
    corrected = [0.0] * len(p_values)
    running = 0.0
    for rank, index in enumerate(order):
        running = max(running, min(1.0, p_values[index] * (len(order) - rank)))
        corrected[index] = running
    return corrected


def inventory(records):
    tokens = [t for r in records for t in r['tokens']]
    counts = Counter(tokens)
    groups = {}
    for field in ['I', 'L', 'H']:
        grouped = defaultdict(list)
        for r in records:
            grouped[r.get('metadata', {}).get(field, '?')].append(r)
        groups[field] = {
            label: {'records': len(rows), 'folios': len({r['folio'] for r in rows}),
                    'tokens': sum(len(r['tokens']) for r in rows)}
            for label, rows in sorted(grouped.items())
        }
    return {
        'records': len(records), 'folios': len({r['folio'] for r in records}),
        'tokens': len(tokens), 'types': len(counts),
        'excluded_tokens': sum(r.get('excluded_tokens', 0) for r in records),
        'eva_characters': sum(map(len, tokens)),
        'mean_word_length_eva_characters': statistics.fmean(map(len, tokens)) if tokens else None,
        'hapax_types': sum(n == 1 for n in counts.values()),
        'word_length_histogram': dict(sorted(Counter(map(len, tokens)).items())),
        'top_tokens': counts.most_common(25), 'groups': groups,
        **within_word_entropy(tokens),
    }


def _prepared_lines(records):
    lines = []
    for r in records:
        words = r['tokens']
        if (not r.get('kind', '').startswith('P') or r.get('excluded_tokens', 0)
                or any(marker in r.get('text_raw', '') for marker in ['<->', '<~>']) or len(words) < 3):
            continue
        n = len(words)
        near = [[edit_distance_at_most_one(a, b) for b in words] for a in words]
        equal = [[a == b for b in words] for a in words]
        lines.append((words, [len(t) for t in words], [t[0] in 'ktpf' for t in words], near, equal))
    return lines


def _sample(prepared, rng=None):
    initial = length = near = equal = pairs = 0
    for words, lengths, gallows, matrix, equal_matrix in prepared:
        order = list(range(len(words)))
        if rng is not None:
            rng.shuffle(order)
        initial += gallows[order[0]]
        length += lengths[order[0]] - (sum(lengths) - lengths[order[0]]) / (len(words) - 1)
        for a, b in zip(order, order[1:]):
            near += matrix[a][b]
            equal += equal_matrix[a][b]
        pairs += len(words) - 1
    n = len(prepared)
    return [initial / n, length / n, near / pairs, equal / pairs] if n else [0.0] * 4


def _expectation(prepared):
    if not prepared:
        return [0.0] * 4
    gallows = near = equal = pairs = 0
    for words, _, g, matrix, eq in prepared:
        n = len(words)
        gallows += sum(g) / n
        near += sum(matrix[i][j] for i in range(n) for j in range(n) if i != j) / n
        equal += sum(eq[i][j] for i in range(n) for j in range(n) if i != j) / n
        pairs += n - 1
    return [gallows / len(prepared), 0.0, near / pairs, equal / pairs]


def run_structure(records, permutations=499, seed=408):
    if not isinstance(seed, int):
        raise ValueError('seed must be an integer for reproducible sampling')
    if not isinstance(permutations, int) or permutations < 1:
        raise ValueError('permutations must be positive')
    if any(not isinstance(t, str) or not t for r in records for t in r['tokens']):
        raise ValueError('tokens must be non-empty strings')
    prepared = _prepared_lines(records)
    summary = inventory(records)
    base = {
        'inventory': summary,
        'config': {'seed': seed, 'permutations': permutations,
                   'null': 'Uniform word permutations within each complete paragraph line.',
                   'family': 'Four tests; Holm correction within this run.',
                   'status': 'Exploratory; significance is not evidence of a translation.'},
        'word_order_sample': {'lines': len(prepared),
                              'tokens': sum(len(x[0]) for x in prepared),
                              'adjacent_pairs': sum(len(x[0]) - 1 for x in prepared),
                              'filter': 'Paragraph loci, no excluded tokens or diagram interruptions, at least three accepted tokens.'},
        'word_order_tests': {},
    }
    if not prepared:
        return base
    observed = _sample(prepared)
    expected = _expectation(prepared)
    rng = random.Random(seed)
    nulls = [[] for _ in range(4)]
    for _ in range(permutations):
        for i, value in enumerate(_sample(prepared, rng)):
            nulls[i].append(value)
    p_values = []
    for i in range(4):
        stat = (lambda x: abs(x)) if i == 1 else (lambda x: x)
        extreme = sum(stat(value) >= stat(observed[i]) - 1e-12 for value in nulls[i])
        p_values.append((1 + extreme) / (1 + permutations))
    adjusted = holm_adjust(p_values)
    names = ['initial_gallows', 'initial_length_difference', 'adjacent_near', 'adjacent_equal']
    for i, name in enumerate(names):
        ordered = sorted(nulls[i])
        base['word_order_tests'][name] = {
            'observed': observed[i], 'null_expectation': expected[i],
            'effect': observed[i] - expected[i],
            'null_mean': statistics.fmean(nulls[i]),
            'null_sd': statistics.pstdev(nulls[i]),
            'null_95_percent_interval': [ordered[int(0.025 * (permutations - 1))],
                                         ordered[int(0.975 * (permutations - 1))]],
            'p_value': p_values[i], 'holm_p_value': adjusted[i],
            'tail': 'two-sided' if i == 1 else 'greater',
            'interpretation_limit': 'Rejects only the stated within-line exchangeability model.',
        }
    return base
