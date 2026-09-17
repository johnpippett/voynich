"""Measure features preserved by a fixed bijective symbol substitution."""

from collections import Counter
import math


def _units(word):
    units = tuple(word)
    if not units or any(not isinstance(x, str) or not x for x in units):
        raise ValueError('Each word must contain nonempty string symbols.')
    return units


def _words(tokens):
    if isinstance(tokens, str):
        raise TypeError('Pass a sequence of words, not one text string.')
    return [_units(word) for word in tokens]


def word_pattern(word):
    """Assign integers in first-occurrence order to record symbol equality."""
    mapping = {}
    pattern = []
    for symbol in _units(word):
        if symbol not in mapping:
            mapping[symbol] = len(mapping)
        pattern.append(mapping[symbol])
    return tuple(pattern)


def _entropy(counts):
    total = sum(counts.values())
    if not total:
        return None
    return math.fsum(-n / total * math.log2(n / total)
                     for n in sorted(counts.values()) if n)


def _js(left, right):
    nl, nr = sum(left.values()), sum(right.values())
    if not nl or not nr:
        raise ValueError('Both distributions must contain observations.')
    terms = []
    for key in sorted(left.keys() | right.keys()):
        p, q = left.get(key, 0) / nl, right.get(key, 0) / nr
        midpoint = (p + q) / 2
        if p:
            terms.append(p * math.log2(p / midpoint) / 2)
        if q:
            terms.append(q * math.log2(q / midpoint) / 2)
    return math.fsum(terms)


def invariant_summary(tokens):
    """Return aggregate values without original words or named symbols."""
    words = _words(tokens)
    types = Counter(words)
    units = Counter(symbol for word in words for symbol in word)
    lengths = Counter(map(len, words))
    patterns = Counter(word_pattern(word) for word in words)
    transitions = Counter((a, b) for word in words for a, b in zip(word, word[1:]))
    contexts = Counter()
    for (a, _b), count in transitions.items():
        contexts[a] += count
    total_transitions = sum(transitions.values())
    conditional = None
    if total_transitions:
        terms = [-(n / total_transitions) * math.log2(n / contexts[a])
                 for (a, _b), n in transitions.items()]
        conditional = math.fsum(sorted(terms))
    return {
        'tokens': len(words),
        'types': len(types),
        'units': sum(units.values()),
        'alphabet_size': len(units),
        'mean_units_per_token': sum(units.values()) / len(words) if words else None,
        'length_counts': {str(k): lengths[k] for k in sorted(lengths)},
        'pattern_counts': {'.'.join(map(str, k)): patterns[k] for k in sorted(patterns)},
        'unit_frequency_ranks': sorted(units.values(), reverse=True),
        'token_frequency_ranks': sorted(types.values(), reverse=True),
        'unit_entropy_bits': _entropy(units),
        'word_entropy_bits': _entropy(types),
        'within_word_transitions': total_transitions,
        'within_word_conditional_entropy_bits': conditional,
    }


def compare_invariants(cipher_tokens, reference_tokens):
    """Compare fixed word boundaries and equality patterns without a key."""
    cipher, reference = _words(cipher_tokens), _words(reference_tokens)
    if not cipher or not reference:
        raise ValueError('Both samples must contain words.')
    cipher_patterns = Counter(word_pattern(word) for word in cipher)
    reference_patterns = Counter(word_pattern(word) for word in reference)
    supported = sum(count for pattern, count in cipher_patterns.items()
                    if pattern in reference_patterns)
    return {
        'cipher_tokens': len(cipher),
        'reference_tokens': len(reference),
        'pattern_supported_tokens': supported,
        'pattern_supported_token_rate': supported / len(cipher),
        'length_js_bits': _js(Counter(map(len, cipher)), Counter(map(len, reference))),
        'pattern_js_bits': _js(cipher_patterns, reference_patterns),
        'joint_key_consistency_tested': False,
        'limit': 'Pattern support is an upper bound for this finite reference vocabulary. It does not establish a consistent key or reject a language.',
    }
