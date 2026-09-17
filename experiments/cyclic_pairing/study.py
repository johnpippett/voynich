"""Run the bounded cyclic pairing control core.

This module keeps the ciphertext-only pairing stage separate from the planted
control diagnostic. It writes aggregate records and never writes word arrays.
The outer resource guard belongs to a separate entry point.
"""

from __future__ import annotations

import argparse
from collections.abc import Iterable, Mapping, Sequence
import hashlib
import json
from pathlib import Path
import sys
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
if str(REPOSITORY_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from experiments.cyclic_pairing.forced import forced_edges  # noqa: E402
from experiments.cyclic_pairing.pairing import (  # noqa: E402
    Compatibility,
    build_compatibility,
    enumerate_matchings,
)
from experiments.homophonic.controls import (  # noqa: E402
    encrypt_words,
    seeded_control_key,
)
from voynich.reference import load_reference_partitions  # noqa: E402


PROTOCOL = "cyclic-pairing-control-v1"
CORPORA = ("latin_llct", "italian_old")
CONTROL_FAMILY = "cap2"
SEED = 7000
CAPACITY = 2
NODE_BUDGET = 100_000
MAX_EDGE_QUERIES = 26
UNITS = tuple(f"c{index:02d}" for index in range(52))
OUTPUT_RELATIVE = Path("results/cyclic-pairing-control-v1")
FREEZE_RELATIVE = Path("experiments/cyclic_pairing/freeze-v1.json")
EXPECTED_VALIDATION_STREAM_HASHES = {
    "latin_llct": "eb03e98b086b9f8bc883f349afaee968bfeaeee8c95be5f66bec320e54b419b2",
    "italian_old": "d7e9c6e0b716cf7ea1c7deb4f135ca2692ea70b4f927548e99668ab0c1428492",
}


def canonical_bytes(value: Any) -> bytes:
    """Return the project's canonical JSON bytes with one final newline."""

    return (
        json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")


def canonical_hash(value: Any) -> str:
    """Return the SHA-256 hash of canonical JSON bytes."""

    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _normalise_partition(
    partition: Iterable[Iterable[str]],
    *,
    allowed_units: frozenset[str] | None = None,
) -> tuple[tuple[str, ...], ...]:
    if isinstance(partition, (str, bytes)):
        raise ValueError("ciphertext partition must contain atomic-unit words")
    words: list[tuple[str, ...]] = []
    for word in partition:
        if isinstance(word, (str, bytes)):
            raise ValueError("ciphertext words must preserve atomic-unit boundaries")
        units = tuple(word)
        if any(not isinstance(unit, str) or not unit for unit in units):
            raise ValueError("ciphertext words must contain non-empty unit strings")
        if allowed_units is not None and any(unit not in allowed_units for unit in units):
            raise ValueError("ciphertext words contain an undeclared unit")
        words.append(units)
    return tuple(words)


def hash_cipher_partition(partition: Iterable[Iterable[str]]) -> str:
    """Hash a partition with the existing canonical JSON stream contract."""

    normalised = _normalise_partition(partition)
    return canonical_hash([list(word) for word in normalised])


def _validate_inventory(units: Iterable[str]) -> tuple[str, ...]:
    if isinstance(units, (str, bytes)):
        raise ValueError("units must be a sequence")
    normalised = tuple(units)
    if normalised != UNITS:
        raise ValueError("the control inventory must contain exactly 52 units c00 through c51")
    if len(set(normalised)) != 52:
        raise ValueError("the control inventory must contain unique units")
    return normalised


def _non_negative_int(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a non-negative integer")
    return value


def _safe_relative_name(value: Any) -> str | None:
    if not isinstance(value, str) or not value:
        return None
    path = Path(value)
    if path.is_absolute() or ".." in path.parts or path.as_posix() != value:
        return None
    return value


def _safe_digest(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
        return None
    return value


def _required_hash_map(value: Any, field: str) -> dict[str, str]:
    if not isinstance(value, Mapping) or not value:
        raise ValueError(f"{field} must be a non-empty hash mapping")
    result: dict[str, str] = {}
    for raw_name, raw_digest in value.items():
        name = _safe_relative_name(raw_name)
        digest = _safe_digest(raw_digest)
        if name is None or digest is None:
            raise ValueError(f"{field} contains an invalid path or SHA-256 digest")
        result[name] = digest
    return dict(sorted(result.items()))


def _required_digest(value: Any, field: str) -> str:
    digest = _safe_digest(value)
    if digest is None:
        raise ValueError(f"{field} must be a lowercase SHA-256 digest")
    return digest


def _safe_source_metadata(metadata: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(metadata, Mapping):
        raise TypeError("source_metadata must be a mapping")
    result: dict[str, Any] = {
        "source_manifest_sha256": _required_digest(
            metadata.get("reference_manifest_sha256", metadata.get("source_manifest_sha256")),
            "source manifest hash",
        )
    }
    source_files = metadata.get("source_files")
    if not isinstance(source_files, Mapping) or not source_files:
        raise ValueError("source_files must be a non-empty mapping")
    file_hashes: dict[str, str] = {}
    for raw_name, raw_info in source_files.items():
        name = _safe_relative_name(raw_name)
        if name is None or Path(name).name != name or not isinstance(raw_info, Mapping):
            raise ValueError("source_files contains an invalid file entry")
        file_hashes[name] = _required_digest(
            raw_info.get("sha256"), f"source file hash for {name}"
        )
    result["source_file_hashes"] = dict(sorted(file_hashes.items()))
    return result


def _freeze_file_hashes(metadata: Mapping[str, Any]) -> dict[str, str]:
    direct = {}
    if "source_hashes" in metadata:
        direct.update(_required_hash_map(metadata["source_hashes"], "source_hashes"))
    files = metadata.get("files")
    if files is not None:
        if not isinstance(files, Sequence) or isinstance(files, (str, bytes)) or not files:
            raise ValueError("freeze files must be a non-empty list")
        seen: set[str] = set()
        for entry in files:
            if not isinstance(entry, Mapping):
                raise ValueError("freeze files contains a malformed entry")
            name = _safe_relative_name(entry.get("path"))
            digest = _safe_digest(entry.get("sha256"))
            if name is None or digest is None or name in seen:
                raise ValueError("freeze files contains a duplicate or invalid entry")
            seen.add(name)
            direct[name] = digest
    if not direct:
        raise ValueError("freeze metadata has no source file hashes")
    return dict(sorted(direct.items()))


def _safe_freeze_metadata(metadata: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(metadata, Mapping):
        raise TypeError("freeze_metadata must be a mapping")
    result: dict[str, Any] = {
        "freeze_manifest_sha256": _required_digest(
            metadata.get("manifest_sha256"), "freeze manifest hash"
        )
    }
    protocol_digest = metadata.get("protocol_sha256")
    if protocol_digest is not None:
        result["protocol_sha256"] = _required_digest(protocol_digest, "protocol hash")
    file_hashes = _freeze_file_hashes(metadata)
    result["frozen_file_hashes"] = file_hashes
    if "code_hashes" in metadata:
        code_hashes = _required_hash_map(metadata["code_hashes"], "code_hashes")
    elif "frozen_code_hashes" in metadata:
        code_hashes = _required_hash_map(metadata["frozen_code_hashes"], "frozen_code_hashes")
    else:
        code_hashes = {
            name: digest
            for name, digest in file_hashes.items()
            if name.endswith(".py") and "test" not in Path(name).name
        }
    if "test_hashes" in metadata:
        test_hashes = _required_hash_map(metadata["test_hashes"], "test_hashes")
    elif "frozen_test_hashes" in metadata:
        test_hashes = _required_hash_map(metadata["frozen_test_hashes"], "frozen_test_hashes")
    else:
        test_hashes = {
            name: digest
            for name, digest in file_hashes.items()
            if name.endswith(".py") and "test" in Path(name).name
        }
    if not code_hashes or not test_hashes:
        raise ValueError("freeze metadata must contain code and test hashes")
    result["frozen_code_hashes"] = code_hashes
    result["frozen_test_hashes"] = test_hashes
    return result


def build_input_record(
    corpus_id: str,
    *,
    source_metadata: Mapping[str, Any],
    freeze_metadata: Mapping[str, Any],
    ciphertext_partition: Iterable[Iterable[str]],
) -> dict[str, Any]:
    """Build the safe aggregate input record for one validation partition."""

    if corpus_id not in CORPORA:
        raise ValueError(f"unsupported corpus: {corpus_id!r}")
    partition = _normalise_partition(ciphertext_partition, allowed_units=frozenset(UNITS))
    source = _safe_source_metadata(source_metadata)
    freeze = _safe_freeze_metadata(freeze_metadata)
    provenance: dict[str, Any] = {**source, **freeze}
    record = {
        "record_type": "input",
        "protocol": PROTOCOL,
        "corpus": corpus_id,
        "family": CONTROL_FAMILY,
        "seed": SEED,
        "capacity": CAPACITY,
        "node_budget": NODE_BUDGET,
        "max_edge_queries": MAX_EDGE_QUERIES,
        "input_scope": "ciphertext_validation_only",
        "declared_unit_count": len(UNITS),
        "declared_units_sha256": canonical_hash(list(UNITS)),
        "validation_stream_sha256": hash_cipher_partition(partition),
        "word_count": len(partition),
        "unit_token_count": sum(len(word) for word in partition),
        "unit_type_count": len({unit for word in partition for unit in word}),
    }
    record.update(
        {
            "manifest_sha256": provenance.get("freeze_manifest_sha256"),
            "source_manifest_sha256": provenance.get("source_manifest_sha256"),
            "source_file_hashes": provenance.get("source_file_hashes", {}),
            "code_hashes": provenance.get("frozen_code_hashes", {}),
            "test_hashes": provenance.get("frozen_test_hashes", {}),
            "frozen_file_hashes": provenance.get("frozen_file_hashes", {}),
        }
    )
    return record


def _pair_to_list(pair: Sequence[str]) -> list[str]:
    return [pair[0], pair[1]]


def _witness_to_list(witness: Iterable[Sequence[str]]) -> list[list[str]]:
    return [_pair_to_list(pair) for pair in witness]


def _edge_category(
    pair: Sequence[str],
    observed: frozenset[str],
) -> str:
    left_observed = pair[0] in observed
    right_observed = pair[1] in observed
    if left_observed and right_observed:
        return "observed_observed"
    if left_observed or right_observed:
        return "observed_unseen"
    return "unseen_unseen"


def _matching_record(result: Any) -> dict[str, Any]:
    return {
        "scope": result.scope,
        "status": result.status,
        "witness_count": len(result.matchings),
        "witnesses": [_witness_to_list(witness) for witness in result.matchings],
        "nodes_visited": result.nodes_visited,
        "node_budget": result.node_budget,
        "max_results": 2,
        "scope_unit_count": len(result.scope_units),
        "unseen_unit_count": len(result.unseen_units),
        "certificate": result.certificate,
    }


def _forced_record(
    result: Any,
    observed: frozenset[str],
) -> dict[str, Any]:
    category_counts = {
        category: {status: 0 for status in ("forced", "not_forced", "unknown")}
        for category in ("observed_observed", "observed_unseen", "unseen_unseen")
    }
    evidence: list[dict[str, Any]] = []
    for item in result.edge_evidence:
        category = _edge_category(item.edge, observed)
        category_counts[category][item.status] += 1
        evidence.append(
            {
                "edge": _pair_to_list(item.edge),
                "category": category,
                "status": item.status,
                "query_status": item.query_status,
                "witness_count": item.witness_count,
                "nodes_visited": item.nodes_visited,
                "node_budget": item.node_budget,
                "alternative_witness": (
                    None
                    if item.alternative_witness is None
                    else _witness_to_list(item.alternative_witness)
                ),
                "certificate": item.certificate,
            }
        )
    return {
        "status": result.status,
        "original_status": result.original_status,
        "original_witness_count": result.original_witness_count,
        "original_nodes_visited": result.original_nodes_visited,
        "original_node_budget": result.original_node_budget,
        "selected_witness": (
            None
            if result.selected_witness is None
            else _witness_to_list(result.selected_witness)
        ),
        "edge_evidence": evidence,
        "category_counts": category_counts,
        "queries_run": result.queries_run,
        "queries_skipped": result.queries_skipped,
        "helper_max_edge_queries": result.max_edge_queries,
        "protocol_max_edge_queries": MAX_EDGE_QUERIES,
        "certificate": result.certificate,
    }


def _assert_pairing_consistency(matching: Any, forced: Any) -> None:
    """Reject disagreement between the outer and repeated base searches."""

    if forced.original_status != matching.status:
        raise ValueError("repeated matching status is inconsistent")
    if forced.original_witness_count != len(matching.matchings):
        raise ValueError("repeated matching witness count is inconsistent")
    if forced.original_nodes_visited != matching.nodes_visited:
        raise ValueError("repeated matching node count is inconsistent")
    if forced.original_node_budget != matching.node_budget:
        raise ValueError("repeated matching node budget is inconsistent")
    expected = matching.matchings[0] if matching.matchings else None
    if forced.selected_witness != expected:
        raise ValueError("repeated matching selected witness is inconsistent")


def _compute_pairing(
    ciphertext_partition: Iterable[Iterable[str]],
    *,
    units: Iterable[str],
    node_budget: int,
    max_edge_queries: int,
) -> tuple[Compatibility, dict[str, Any]]:
    normalised_units = _validate_inventory(units)
    node_budget = _non_negative_int(node_budget, "node_budget")
    max_edge_queries = _non_negative_int(max_edge_queries, "max_edge_queries")
    if max_edge_queries > MAX_EDGE_QUERIES:
        raise ValueError("the protocol edge query limit is 26")
    partition = _normalise_partition(
        ciphertext_partition, allowed_units=frozenset(normalised_units)
    )
    compatibility = build_compatibility(normalised_units, [partition])
    matching = enumerate_matchings(
        compatibility,
        scope="full",
        node_budget=node_budget,
        max_results=2,
    )
    forced = forced_edges(compatibility, node_budget=node_budget)
    _assert_pairing_consistency(matching, forced)
    if forced.queries_run > max_edge_queries:
        raise ValueError("forced edge search exceeded the protocol edge query limit")
    observed = frozenset(compatibility.observed_units)
    edge_counts = {
        category: 0
        for category in ("observed_observed", "observed_unseen", "unseen_unseen")
    }
    for edge in compatibility.edges:
        edge_counts[_edge_category(edge, observed)] += 1
    record = {
        "record_type": "pairing",
        "protocol": PROTOCOL,
        "family": CONTROL_FAMILY,
        "seed": SEED,
        "capacity": CAPACITY,
        "input_scope": "ciphertext_validation_only",
        "declared_unit_count": len(normalised_units),
        "declared_units_sha256": canonical_hash(list(normalised_units)),
        "validation_stream_sha256": hash_cipher_partition(partition),
        "word_count": len(partition),
        "unit_token_count": sum(len(word) for word in partition),
        "graph": {
            "vertex_count": len(compatibility.units),
            "observed_vertex_count": len(compatibility.observed_units),
            "unseen_vertex_count": len(compatibility.unseen_units),
            "edge_count": len(compatibility.edges),
            "edge_counts_by_category": edge_counts,
        },
        "matching": _matching_record(matching),
        "forced": _forced_record(forced, observed),
    }
    return compatibility, record


def run_pairing_stage(
    ciphertext_partition: Iterable[Iterable[str]],
    *,
    units: Iterable[str] = UNITS,
    node_budget: int = NODE_BUDGET,
    max_edge_queries: int = MAX_EDGE_QUERIES,
) -> dict[str, Any]:
    """Build and serialize the full-inventory ciphertext-only pairing result."""

    _compatibility, record = _compute_pairing(
        ciphertext_partition,
        units=units,
        node_budget=node_budget,
        max_edge_queries=max_edge_queries,
    )
    return record


def _control_pair_data(planted_key: Mapping[str, Any]) -> tuple[tuple[str, str], ...]:
    if not isinstance(planted_key, Mapping):
        raise TypeError("planted_key must be a mapping")
    mapping = planted_key.get("cipher_to_plain")
    cycles = planted_key.get("emission_order")
    if not isinstance(mapping, Mapping) or not isinstance(cycles, Mapping):
        raise ValueError("planted_key must contain a mapping and emission cycles")
    groups: dict[str, list[str]] = {}
    for raw_unit, raw_letter in mapping.items():
        if not isinstance(raw_unit, str) or not isinstance(raw_letter, str):
            raise ValueError("planted key contains an invalid unit or letter")
        groups.setdefault(raw_letter, []).append(raw_unit)
    if set(mapping) != set(UNITS) or len(groups) != 26 or any(
        len(values) != CAPACITY for values in groups.values()
    ):
        raise ValueError("planted key is not a complete capacity-two control key")
    if set(cycles) != set(groups):
        raise ValueError("planted key cycles do not cover the control letters")
    for letter, values in groups.items():
        cycle = cycles[letter]
        if not isinstance(cycle, Sequence) or isinstance(cycle, (str, bytes)):
            raise ValueError("planted key contains an invalid emission cycle")
        if tuple(cycle) != tuple(values) and set(cycle) != set(values):
            raise ValueError("planted key cycle does not match its pair")
    return tuple(sorted(tuple(sorted(values)) for values in groups.values()))


def _public_witness_pairs(value: Any) -> frozenset[tuple[str, str]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ValueError("pairing witness is invalid")
    result: set[tuple[str, str]] = set()
    for raw_pair in value:
        if not isinstance(raw_pair, Sequence) or isinstance(raw_pair, (str, bytes)):
            raise ValueError("pairing witness edge is invalid")
        pair = tuple(raw_pair)
        if len(pair) != 2 or any(not isinstance(unit, str) for unit in pair):
            raise ValueError("pairing witness edge is invalid")
        result.add(tuple(sorted(pair)))
    return frozenset(result)


def _public_pair(value: Any) -> tuple[str, str]:
    pairs = _public_witness_pairs([value])
    if len(pairs) != 1:
        raise ValueError("unit pair is invalid")
    return next(iter(pairs))


def _assert_positive_diagnostics(
    pairing_record: Mapping[str, Any],
    diagnostics: Mapping[str, Any],
    control_pairs: frozenset[tuple[str, str]],
) -> None:
    if diagnostics["graph_control_pair_overlap_count"] != len(control_pairs):
        raise ValueError("a planted control pair is missing from the graph")
    if diagnostics["graph_control_pair_missing"]:
        raise ValueError("a planted control pair is missing from the graph")
    orientation = diagnostics["orientation"]
    if orientation["mismatch_count"] != 0:
        raise ValueError("a comparable planted orientation does not match")
    if orientation["match_count"] != orientation["comparable_count"]:
        raise ValueError("planted orientation counts are inconsistent")

    status = pairing_record["matching"]["status"]
    if status not in {"unique", "multiple", "unknown_budget"}:
        raise ValueError("a known positive control produced an impossible matching status")
    if status == "unique":
        witnesses = pairing_record["matching"]["witnesses"]
        if len(witnesses) != 1 or _public_witness_pairs(witnesses[0]) != control_pairs:
            raise ValueError("the unique witness does not equal the planted pairing")

    forced = pairing_record.get("forced")
    if not isinstance(forced, Mapping):
        raise ValueError("forced evidence is missing")
    evidence = forced.get("edge_evidence")
    if not isinstance(evidence, Sequence) or isinstance(evidence, (str, bytes)):
        raise ValueError("forced edge evidence is malformed")
    for item in evidence:
        if not isinstance(item, Mapping):
            raise ValueError("forced edge evidence is malformed")
        if item.get("status") == "forced" and _public_pair(item.get("edge")) not in control_pairs:
            raise ValueError("a reported forced edge is not planted")


def build_control_diagnostics(
    pairing_record: Mapping[str, Any],
    *,
    compatibility: Compatibility,
    planted_key: Mapping[str, Any],
) -> dict[str, Any]:
    """Compare saved graph evidence with the known unit pair control.

    This function runs only after the pairing record is saved. It reports unit
    pairs and orientation counts. It does not write letters or the planted map.
    """

    if not isinstance(pairing_record, Mapping):
        raise TypeError("pairing_record must be a mapping")
    if not isinstance(compatibility, Compatibility):
        raise TypeError("compatibility must be a Compatibility instance")
    if pairing_record.get("record_type") != "pairing":
        raise ValueError("diagnostics require a saved pairing record")
    if tuple(compatibility.units) != UNITS:
        raise ValueError("diagnostics require the fixed 52-unit inventory")
    control_pairs = _control_pair_data(planted_key)
    control_pair_set = frozenset(control_pairs)
    graph_pair_set = frozenset(compatibility.edges)
    observed = frozenset(compatibility.observed_units)
    overlap = tuple(sorted(control_pair_set.intersection(graph_pair_set)))
    missing = tuple(sorted(control_pair_set.difference(graph_pair_set)))
    counts_by_category = {
        category: 0
        for category in ("observed_observed", "observed_unseen", "unseen_unseen")
    }
    for pair in control_pairs:
        counts_by_category[_edge_category(pair, observed)] += 1

    orientation_comparable = 0
    orientation_matches = 0
    orientation_mismatches = 0
    for pair in overlap:
        starts = compatibility.orientation_for(pair)
        # The cycle's first unit is the expected start. Letter names stay in memory.
        mapping = planted_key["cipher_to_plain"]
        cycle_letter = mapping[pair[0]]
        expected_start = planted_key["emission_order"][cycle_letter][0]
        for start in starts:
            if start is None:
                continue
            orientation_comparable += 1
            if start == expected_start:
                orientation_matches += 1
            else:
                orientation_mismatches += 1

    witnesses: list[dict[str, Any]] = []
    raw_witnesses = pairing_record.get("matching", {}).get("witnesses", ())
    if not isinstance(raw_witnesses, Sequence) or isinstance(raw_witnesses, (str, bytes)):
        raise ValueError("pairing record witnesses are invalid")
    for index, raw_witness in enumerate(raw_witnesses):
        witness_pairs = _public_witness_pairs(raw_witness)
        shared = tuple(sorted(control_pair_set.intersection(witness_pairs)))
        witnesses.append(
            {
                "witness_index": index,
                "pair_set_sha256": canonical_hash([list(pair) for pair in sorted(witness_pairs)]),
                "control_pair_overlap_count": len(shared),
                "control_pairs_in_witness": [list(pair) for pair in shared],
            }
        )
    diagnostics = {
        "record_type": "diagnostics",
        "protocol": PROTOCOL,
        "input_scope": "ciphertext_validation_only",
        "status": pairing_record["matching"]["status"],
        "full_matching_status": pairing_record["matching"]["status"],
        "matching_status": pairing_record["matching"]["status"],
        "matching_witness_count": pairing_record["matching"]["witness_count"],
        "control_pair_count": len(control_pairs),
        "control_pair_set_sha256": canonical_hash([list(pair) for pair in control_pairs]),
        "graph_control_pair_overlap_count": len(overlap),
        "graph_control_pair_overlap": [list(pair) for pair in overlap],
        "graph_control_pair_missing": [list(pair) for pair in missing],
        "control_pair_counts_by_category": counts_by_category,
        "orientation": {
            "comparable_count": orientation_comparable,
            "match_count": orientation_matches,
            "mismatch_count": orientation_mismatches,
        },
        "witnesses": witnesses,
        "diagnostic_scope": "post_pairing_known_control_unit_comparison",
        "limits": [
            "The diagnostic compares unit pairs after ciphertext-only pairing evidence is saved.",
            "It does not select a matching or assign plaintext letters.",
        ],
    }
    _assert_positive_diagnostics(pairing_record, diagnostics, control_pair_set)
    return diagnostics


def _write_new_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(canonical_bytes(value))


def _implementation_failure_diagnostics(
    corpus: str, input_record: Mapping[str, Any]
) -> dict[str, Any]:
    return {
        "record_type": "diagnostics",
        "protocol": PROTOCOL,
        "corpus": corpus,
        "family": CONTROL_FAMILY,
        "seed": SEED,
        "capacity": CAPACITY,
        "input_scope": "ciphertext_validation_only",
        "status": "implementation_failure",
        "full_matching_status": "implementation_failure",
        "matching_status": "implementation_failure",
        "matching_witness_count": 0,
        "control_pair_count": 26,
        "failure_reason": "post_pairing_control_validation_failed",
        "manifest_sha256": input_record.get("manifest_sha256"),
        "source_manifest_sha256": input_record.get("source_manifest_sha256"),
    }


def load_freeze_metadata(root: Path = REPOSITORY_ROOT) -> dict[str, Any]:
    """Read the fixed freeze and bind provenance to its raw-byte hash."""

    freeze_path = Path(root) / FREEZE_RELATIVE
    if freeze_path.is_symlink() or not freeze_path.is_file():
        raise FileNotFoundError("the reviewed cyclic control freeze record is unavailable")
    raw = freeze_path.read_bytes()
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("the reviewed cyclic control freeze record is invalid") from error
    if not isinstance(value, Mapping):
        raise ValueError("the reviewed cyclic control freeze record is not an object")
    metadata = dict(value)
    metadata["manifest_sha256"] = hashlib.sha256(raw).hexdigest()
    return metadata


def _check_output_dir(output_root: Path, corpus_id: str) -> Path:
    if corpus_id not in CORPORA:
        raise ValueError(f"unsupported corpus: {corpus_id!r}")
    corpus_dir = Path(output_root) / corpus_id
    if corpus_dir.is_symlink():
        raise FileExistsError("corpus output directory is a symlink")
    for name in ("input.json", "pairing.json", "diagnostics.json"):
        if (corpus_dir / name).exists() or (corpus_dir / name).is_symlink():
            raise FileExistsError("a corpus output record already exists")
    return corpus_dir


def run_one_corpus(
    root: Path,
    corpus: str,
    output: Path,
    freeze_meta: Mapping[str, Any],
) -> dict[str, Any]:
    """Create the three records for one fixed validation control corpus."""

    corpus_dir = _check_output_dir(Path(output), corpus)
    partitions = load_reference_partitions(Path(root))
    try:
        corpus_data = partitions[corpus]
        validation_words = corpus_data["words"]["validation"]
        source_metadata = corpus_data["metadata"]
    except (KeyError, TypeError) as error:
        raise ValueError("reference loader did not return the required validation corpus") from error

    planted_key = seeded_control_key(CONTROL_FAMILY, SEED)
    ciphertext = tuple(encrypt_words(validation_words, planted_key))
    stream_hash = hash_cipher_partition(ciphertext)
    expected_hash = EXPECTED_VALIDATION_STREAM_HASHES.get(corpus)
    if expected_hash is None or stream_hash != expected_hash:
        raise ValueError(f"validation stream hash mismatch for {corpus}")
    input_record = build_input_record(
        corpus,
        source_metadata=source_metadata,
        freeze_metadata=freeze_meta,
        ciphertext_partition=ciphertext,
    )
    _write_new_json(corpus_dir / "input.json", input_record)

    try:
        compatibility, pairing_record = _compute_pairing(
            ciphertext,
            units=UNITS,
            node_budget=NODE_BUDGET,
            max_edge_queries=MAX_EDGE_QUERIES,
        )
    except Exception as error:
        _write_new_json(
            corpus_dir / "diagnostics.json",
            _implementation_failure_diagnostics(corpus, input_record),
        )
        raise RuntimeError("pairing computation failed") from error
    pairing_record = {
        **pairing_record,
        "corpus": corpus,
    }
    for field in (
        "manifest_sha256",
        "source_manifest_sha256",
        "source_file_hashes",
        "code_hashes",
        "test_hashes",
        "frozen_file_hashes",
    ):
        pairing_record[field] = input_record[field]
    _write_new_json(corpus_dir / "pairing.json", pairing_record)

    try:
        diagnostics = build_control_diagnostics(
            pairing_record,
            compatibility=compatibility,
            planted_key=planted_key,
        )
    except Exception as error:
        _write_new_json(
            corpus_dir / "diagnostics.json",
            _implementation_failure_diagnostics(corpus, input_record),
        )
        raise RuntimeError("post-pairing control validation failed") from error
    diagnostics["corpus"] = corpus
    diagnostics["manifest_sha256"] = input_record["manifest_sha256"]
    diagnostics["source_manifest_sha256"] = input_record["source_manifest_sha256"]
    _write_new_json(corpus_dir / "diagnostics.json", diagnostics)
    return {
        "status": "complete",
        "protocol": PROTOCOL,
        "corpus": corpus,
        "output_files": ["input.json", "pairing.json", "diagnostics.json"],
    }


def main(argv: Sequence[str] | None = None) -> int:
    """Run one fixed child selected by ``--corpus``."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", choices=CORPORA, required=True)
    args = parser.parse_args(argv)
    try:
        freeze_metadata = load_freeze_metadata(REPOSITORY_ROOT)
    except (FileNotFoundError, OSError, ValueError) as error:
        raise SystemExit(str(error)) from error
    result = run_one_corpus(
        REPOSITORY_ROOT,
        args.corpus,
        REPOSITORY_ROOT / OUTPUT_RELATIVE,
        freeze_metadata,
    )
    print(json.dumps({"status": result["status"], "corpus": result["corpus"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "CAPACITY",
    "CONTROL_FAMILY",
    "CORPORA",
    "EXPECTED_VALIDATION_STREAM_HASHES",
    "FREEZE_RELATIVE",
    "MAX_EDGE_QUERIES",
    "NODE_BUDGET",
    "OUTPUT_RELATIVE",
    "PROTOCOL",
    "SEED",
    "UNITS",
    "build_control_diagnostics",
    "build_input_record",
    "canonical_bytes",
    "canonical_hash",
    "hash_cipher_partition",
    "load_freeze_metadata",
    "main",
    "run_one_corpus",
    "run_pairing_stage",
]
