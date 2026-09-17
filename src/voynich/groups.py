"""Map IVTFF folio identifiers to source-backed Q/B groups.

The manifest is the source of this embedded map. Keeping the map in this
small standard-library module makes the split deterministic when a caller
runs from a directory that does not contain the repository.
"""

from copy import deepcopy
import hashlib
import re


_GROUPING_VERSION = "ivtff-bifolio-metadata-v3"
_MANIFEST_PATH = "data/bifolio_manifest.json"
_MANIFEST_SCHEMA_VERSION = "bifolio-manifest-v1"
_MANIFEST_SHA256 = "998cb3d6c8327ff0bdf786d52968fa3bec9f5fa9b05ba7ae56065fc9639fad72"
_SPLIT_HASH_SALT = "voynich-bifolio-408-v3:"

_SOURCE_SHA256 = {
    "data/raw/ZL3b-n.txt": "bf5b6d4ac1e3a51b1847a9c388318d609020441ccd56984c901c32b09beccafc",
    "data/raw/IT2a-n.txt": "7f27a8b0feed8f6de0a99900df6bf912dd1d295c38e5f830bac8b41c3f536fb5",
}

# (group key, minimum numeric folio, numeric folios present)
_COMPONENTS = (
    ("A/1", 1, (1, 8)),
    ("A/2", 2, (2, 7)),
    ("A/3", 3, (3, 6)),
    ("A/4", 4, (4, 5)),
    ("B/1", 9, (9, 16)),
    ("B/2", 10, (10, 15)),
    ("B/3", 11, (11, 14)),
    ("B/4", 13, (13,)),
    ("C/1", 17, (17, 24)),
    ("C/2", 18, (18, 23)),
    ("C/3", 19, (19, 22)),
    ("C/4", 20, (20, 21)),
    ("D/1", 25, (25, 32)),
    ("D/2", 26, (26, 31)),
    ("D/3", 27, (27, 30)),
    ("D/4", 28, (28, 29)),
    ("E/1", 33, (33, 40)),
    ("E/2", 34, (34, 39)),
    ("E/3", 35, (35, 38)),
    ("E/4", 36, (36, 37)),
    ("F/1", 41, (41, 48)),
    ("F/2", 42, (42, 47)),
    ("F/3", 43, (43, 46)),
    ("F/4", 44, (44, 45)),
    ("G/1", 49, (49, 56)),
    ("G/2", 50, (50, 55)),
    ("G/3", 51, (51, 54)),
    ("G/4", 52, (52, 53)),
    ("H/1", 57, (57, 66)),
    ("H/2", 58, (58, 65)),
    ("I/1", 67, (67, 68)),
    ("J/1", 69, (69, 70)),
    ("K/1", 71, (71, 72)),
    ("L/1", 73, (73,)),
    ("M/1", 75, (75, 84)),
    ("M/2", 76, (76, 83)),
    ("M/3", 77, (77, 82)),
    ("M/4", 78, (78, 81)),
    ("M/5", 79, (79, 80)),
    ("N/1", 85, (85, 86)),
    ("O/1", 87, (87, 90)),
    ("O/2", 88, (88, 89)),
    ("Q/1", 93, (93, 96)),
    ("Q/2", 94, (94, 95)),
    ("S/1", 99, (99, 102)),
    ("S/2", 100, (100, 101)),
    ("T/1", 103, (103, 116)),
    ("T/2", 104, (104, 115)),
    ("T/3", 105, (105, 114)),
    ("T/4", 106, (106, 113)),
    ("T/5", 107, (107, 112)),
    ("T/6", 108, (108, 111)),
)

_FOLIO_TO_GROUP = {
    str(number): str(representative)
    for _group_key, representative, numbers in _COMPONENTS
    for number in numbers
}
_GROUP_IDS = frozenset(_FOLIO_TO_GROUP.values())
_GROUP_KEYS = {
    str(representative): group_key
    for group_key, representative, _numbers in _COMPONENTS
}

# These were used by the exploratory foldout review. They remain in the
# configuration as historical metadata; they do not define the main map.
_LEGACY_FOLDOUT_COMPONENTS = (
    (69, 70),
    (71, 72),
    (85, 86),
    (88, 89, 90),
    (94, 95),
    (100, 101, 102),
)


def group_id(folio):
    """Return the representative numeric folio for one known folio ID."""

    if folio == "fRos":
        return "85"
    if not isinstance(folio, str):
        raise ValueError(f"Unsupported folio identifier: {folio!r}")
    match = re.fullmatch(r"f(\d+)[rv]\d*", folio)
    if match is None:
        raise ValueError(f"Unsupported folio identifier: {folio!r}")
    number = str(int(match.group(1)))
    try:
        return _FOLIO_TO_GROUP[number]
    except KeyError as error:
        raise ValueError(f"Unsupported folio identifier: {folio!r}") from error


def _canonical_group(group):
    """Return a known representative, accepting a numeric member for compatibility."""

    group_text = str(group)
    if group_text in _GROUP_IDS:
        return group_text
    if group_text in _FOLIO_TO_GROUP:
        return _FOLIO_TO_GROUP[group_text]
    raise ValueError(f"Unsupported folio group: {group!r}")


def split_bucket(group):
    """Return the deterministic ten-way bucket for one physical Q/B group."""

    canonical = _canonical_group(group)
    digest = hashlib.sha256((_SPLIT_HASH_SALT + canonical).encode("ascii")).digest()
    return int.from_bytes(digest[:8], "big") % 10


def split_name(bucket):
    """Map a hash bucket to the experiment split."""

    if bucket in (0, 1):
        return "test"
    if bucket == 2:
        return "validation"
    if bucket in range(3, 10):
        return "train"
    raise ValueError("Split bucket must be between zero and nine")


_CONFIG = {
    "version": _GROUPING_VERSION,
    "manifest": {
        "path": _MANIFEST_PATH,
        "schema_version": _MANIFEST_SCHEMA_VERSION,
        "sha256": _MANIFEST_SHA256,
    },
    "manifest_path": _MANIFEST_PATH,
    "manifest_schema_version": _MANIFEST_SCHEMA_VERSION,
    "manifest_sha256": _MANIFEST_SHA256,
    "manifest_hash": _MANIFEST_SHA256,
    "group_key": "(Q,B)",
    "representative": "Minimum numeric folio in each (Q,B) group.",
    "group_count": len(_COMPONENTS),
    "numeric_folio_count": len(_FOLIO_TO_GROUP),
    "aliases": {"fRos": "85"},
    "folio_map": dict(sorted(_FOLIO_TO_GROUP.items(), key=lambda item: int(item[0]))),
    "components": [
        {
            "group": str(representative),
            "group_key": group_key,
            "representative_numeric_folio": representative,
            "numeric_folios": list(numbers),
        }
        for group_key, representative, numbers in _COMPONENTS
    ],
    "complete_provider_coverage": True,
    "independent_conservation_verification": False,
    "independent_conservation_verification_note": (
        "No independent conservation examination was performed; this grouping uses provider Q/B metadata."
    ),
    "evidence": {
        "manifest": _MANIFEST_PATH,
        "provider_scope": (
            "Complete for page headers and locus records in both source files."
        ),
        "format_specification": {
            "url": "https://voynich.nu/software/ivtt/IVTFF_format.pdf",
            "location": "Section 6.3, Table 6, PDF pages 19-20 (one-based), Q and B rows.",
        },
        "cross_corpus_agreement": {
            "shared_page_name_count": 225,
            "shared_page_QB_mismatches": [],
            "all_ZL3b_locus_records_have_QB": True,
            "all_IT2a_locus_records_have_QB": True,
        },
    },
    "source_sha256": dict(_SOURCE_SHA256),
    "source_files": [
        {
            "path": path,
            "sha256": digest,
        }
        for path, digest in _SOURCE_SHA256.items()
    ],
    "split_hash_salt": _SPLIT_HASH_SALT,
    "split_hash_algorithm": "sha256",
    "split_hash_bytes": 8,
    "split_bucket_modulus": 10,
    "legacy_foldout_metadata": {
        "components": [list(component) for component in _LEGACY_FOLDOUT_COMPONENTS],
        "confirmed_cross_number_foldout": [85, 86],
        "role": "Historical exploratory metadata only; the complete Q/B map above controls grouping.",
    },
    # Compatibility keys for reports written during the tentative grouping stage.
    "conservative_components": [list(component) for component in _LEGACY_FOLDOUT_COMPONENTS],
    "candidate_components": [
        list(component)
        for component in _LEGACY_FOLDOUT_COMPONENTS
        if component != (85, 86)
    ],
    "confirmed_cross_number_foldout": [85, 86],
}


def grouping_config():
    """Return an independent copy of the source-backed grouping configuration."""

    return deepcopy(_CONFIG)
