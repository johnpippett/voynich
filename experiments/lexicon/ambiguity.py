"""Count key completions that preserve every current positive-weight hit."""

from math import perm

from experiments.lexicon.solver import (
    _normalise_alphabet,
    _normalise_cipher_counts,
    _normalise_lexicon,
    _validate_initial_key,
)


def preserved_hit_completions(ciphertext_counts, plaintext_lexicon,
                              plaintext_alphabet, key):
    """Return a lower bound on keys with at least the supplied key's score.

    Fix all assignments used by positive-weight hits. Every injective
    completion preserves those hits. With a certified optimum score, all
    these completions also have an optimum score. Other ambiguities can exist.
    """
    counts = _normalise_cipher_counts(ciphertext_counts)
    alphabet = _normalise_alphabet(plaintext_alphabet)
    lexicon, *_ = _normalise_lexicon(plaintext_lexicon, alphabet)
    domain = tuple(sorted({symbol for word in counts for symbol in word}))
    validated = _validate_initial_key(key, domain, alphabet)
    if set(validated) != set(domain):
        raise ValueError('The key must cover every ciphertext symbol.')
    covered = set()
    score = 0
    for word, weight in counts.items():
        if weight > 0 and tuple(validated[symbol] for symbol in word) in lexicon:
            covered.update(word)
            score += weight
    free_cipher = len(domain) - len(covered)
    free_plain = len(alphabet) - len(covered)
    return {
        'incumbent_score': score,
        'cipher_symbol_count': len(domain),
        'plaintext_symbol_count': len(alphabet),
        'covered_symbol_count': len(covered),
        'symbols_outside_positive_hits': sorted(set(domain) - covered),
        'keys_preserving_current_hits': perm(free_plain, free_cipher),
        'guarantee': 'Every counted key scores at least as high as the supplied key.',
        'optimum_condition': 'If the supplied score is certified optimal, every counted key is also optimal.',
        'limit': 'This count can omit other keys with equal or higher scores. It does not identify a historical key.',
    }
