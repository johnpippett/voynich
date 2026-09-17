"""Conservative folio groups for train and test separation."""

import hashlib
import re


_COMPONENTS = ((69,70), (71,72), (85,86), (88,89,90), (94,95), (100,101,102))
_CANONICAL = {str(n): str(min(group)) for group in _COMPONENTS for n in group}


def group_id(folio):
    if folio == 'fRos':
        return '85'
    match = re.fullmatch(r'f(\d+)[rv]\d*', str(folio))
    if match is None:
        raise ValueError(f'Unsupported folio identifier: {folio!r}')
    number = str(int(match.group(1)))
    return _CANONICAL.get(number, number)


def split_bucket(group):
    digest = hashlib.sha256(('voynich-408-v1:' + str(group)).encode()).digest()
    return int.from_bytes(digest[:8], 'big') % 10


def split_name(bucket):
    if bucket in (0,1):
        return 'test'
    if bucket == 2:
        return 'validation'
    if bucket in range(3,10):
        return 'train'
    raise ValueError('Split bucket must be between zero and nine')


def grouping_config():
    return {
        'version': 'conservative-foldout-groups-v2',
        'representative': 'Minimum numeric folio in each component.',
        'conservative_components': [list(c) for c in _COMPONENTS],
        'confirmed_cross_number_foldout': [85,86],
        'aliases': {'fRos': '85'},
        'candidate_components': [list(c) for c in _COMPONENTS if c != (85,86)],
        'evidence': 'docs/research/physical-groups.md',
        'limitation': 'Candidate unions are conservative assumptions; a complete physical-sheet map is not established.',
        'split_hash_salt': 'voynich-408-v1:',
        'amendment': 'The first numeric split separated the confirmed 85/86 foldout. Reviewed results use these unions.',
    }
