"""Reversible raw and six-compound unitization for canonical Basic EVA words."""

from dataclasses import dataclass
import re


VERSION = 'basic-eva-visual-six-v1'
COMPOUNDS = ('cth', 'ckh', 'cph', 'cfh', 'ch', 'sh')
MATCH_ORDER = tuple(sorted(COMPOUNDS, key=lambda value: (-len(value), value)))


@dataclass(frozen=True, slots=True)
class UnitSpan:
    unit: str
    raw: str
    start: int
    end: int


def tokenizer_config(representation):
    if representation not in ('raw', 'visual'):
        raise ValueError('representation must be raw or visual')
    return {
        'version': VERSION,
        'representation': representation,
        'input': 'One canonical Basic EVA word containing only ASCII a-z, or an empty word.',
        'compounds': list(MATCH_ORDER) if representation == 'visual' else [],
        'matching': 'Longest match; unmatched code points remain single units.',
        'normalization': 'None. Noncanonical input is rejected without conversion.',
        'word_boundaries': 'Caller supplies one word; internal separators are rejected.',
        'spans': 'Zero-based character offsets; end is exclusive.',
        'limits': [
            'The compounds are analysis choices based on written shapes.',
            'This conversion assigns no sounds, letters, or meanings.',
            'Source transcription uncertainty remains outside this word conversion.',
        ],
    }


def tokenize_word(word, *, representation):
    """Return exact source spans for each selected analysis unit."""
    config = tokenizer_config(representation)
    if not isinstance(word, str):
        raise TypeError('word must be a string')
    if re.fullmatch('[a-z]*', word) is None:
        raise ValueError('word must contain only canonical Basic EVA a-z code points')
    cursor = 0
    spans = []
    while cursor < len(word):
        value = next((compound for compound in config['compounds']
                      if word.startswith(compound, cursor)), word[cursor])
        end = cursor + len(value)
        spans.append(UnitSpan(unit=value, raw=word[cursor:end], start=cursor, end=end))
        cursor = end
    return tuple(spans)


def units(word, *, representation):
    """Return the cipher-unit tuple while keeping word boundaries external."""
    return tuple(span.unit for span in tokenize_word(word, representation=representation))
