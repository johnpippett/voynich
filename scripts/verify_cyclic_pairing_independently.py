"""Audit frozen cyclic pairing records with independent standard-library code."""
from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from experiments.homophonic.controls import encrypt_words, seeded_control_key  # noqa: E402
from voynich.reference import load_reference_partitions  # noqa: E402

CORPORA = ("latin_llct", "italian_old")
UNITS = tuple(f"c{index:02d}" for index in range(52))
INPUT_ROOT = ROOT / "results" / "cyclic-pairing-control-v1"
FREEZE_PATH = ROOT / "experiments/cyclic_pairing/freeze-v1.json"
OUTPUT_PATH = ROOT / "results/cyclic-pairing-control-v1-independent-audit.json"
MATCHING_NODE_LIMIT = 1_000_000
CATEGORIES = ("observed_observed", "observed_unseen", "unseen_unseen")
EXPECTED_FREEZE_SHA256 = "66c2cdeb461278804ff3be16d592940711a450a33ac8db7f46e12d38c8eca12b"
EXPECTED_RECORD_HASHES = {
    "latin_llct": {
        "input.json": "ba8d74a8ccaa11b2bfc0c665877df295c5a758b1eb7bf1b2912391fb87efcd06",
        "pairing.json": "672960dd6f9a791f806b4e8c93b6e4df3bc966479c6c0960ceaa1124d214a4ee",
        "diagnostics.json": "de6c7b97a9f0d493ab08c3998e37857d34f066db7e54d803ac28ec2b0795fee9",
    },
    "italian_old": {
        "input.json": "6f6cad275f5c9feb3bd7dc80e5e7549b298c3731f713fc492f087eb0675984d3",
        "pairing.json": "e3f9e943caed5928a91ad9ea615af92cc8f6cea152639c91cd1a82c3eb18c830",
        "diagnostics.json": "cae9ece0fd3f843b85e7217150497230e2c4437e6dca160750472b5afde7d7b7",
    },
}


def digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def canonical_hash(value: Any) -> str:
    raw = (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()
    return digest_bytes(raw)


def read_pinned_json(path: Path, expected_hash: str) -> tuple[dict[str, Any], str]:
    raw = path.read_bytes()
    actual_hash = digest_bytes(raw)
    if actual_hash != expected_hash:
        raise ValueError("primary record hash mismatch")
    value = json.loads(raw.decode("utf-8"))
    if not isinstance(value, dict):
        raise ValueError("record is not an object")
    return value, actual_hash


def pair_value(value: Any) -> tuple[str, str]:
    if not isinstance(value, list) or len(value) != 2:
        raise ValueError("invalid pair")
    if any(not isinstance(unit, str) or unit not in UNITS for unit in value):
        raise ValueError("invalid pair unit")
    if value[0] == value[1]:
        raise ValueError("self pair")
    return tuple(sorted(value))  # type: ignore[return-value]


def matching_value(value: Any) -> tuple[tuple[str, str], ...]:
    if not isinstance(value, list):
        raise ValueError("invalid matching")
    result = tuple(sorted(pair_value(pair) for pair in value))
    if len(result) != 26 or len({unit for pair in result for unit in pair}) != 52:
        raise ValueError("matching does not cover the inventory")
    return result


def pairs_hash(pairs: Any) -> str:
    return canonical_hash([list(pair) for pair in sorted(pairs)])


def matching_set_hash(matchings: set[tuple[tuple[str, str], ...]]) -> str:
    return canonical_hash(sorted(pairs_hash(matching) for matching in matchings))


def graph_from_stream(stream: tuple[str, ...]) -> tuple[set[tuple[str, str]], frozenset[str]]:
    positions: dict[str, list[int]] = {unit: [] for unit in UNITS}
    for index, unit in enumerate(stream):
        if unit not in positions:
            raise ValueError("cipher stream contains an undeclared unit")
        positions[unit].append(index)
    observed = frozenset(unit for unit in UNITS if positions[unit])
    edges: set[tuple[str, str]] = set()
    for left_index, left in enumerate(UNITS):
        for right in UNITS[left_index + 1 :]:
            left_positions, right_positions = positions[left], positions[right]
            if abs(len(left_positions) - len(right_positions)) > 1:
                continue
            i = j = 0
            previous: str | None = None
            alternates = True
            while i < len(left_positions) or j < len(right_positions):
                if j == len(right_positions) or (i < len(left_positions) and left_positions[i] < right_positions[j]):
                    current = left
                    i += 1
                else:
                    current = right
                    j += 1
                if previous == current:
                    alternates = False
                    break
                previous = current
            if alternates:
                edges.add((left, right))
    return edges, observed


def enumerate_full(edges: set[tuple[str, str]]) -> tuple[set[tuple[tuple[str, str], ...]], int, bool]:
    index = {unit: number for number, unit in enumerate(UNITS)}
    adjacency = [0] * len(UNITS)
    for left, right in edges:
        adjacency[index[left]] |= 1 << index[right]
        adjacency[index[right]] |= 1 << index[left]
    found: set[tuple[tuple[str, str], ...]] = set()
    nodes = 0
    stopped = False

    def visit(remaining: int, pairs: tuple[tuple[str, str], ...]) -> None:
        nonlocal nodes, stopped
        if remaining == 0:
            found.add(tuple(sorted(pairs)))
            return
        if nodes >= MATCHING_NODE_LIMIT:
            stopped = True
            return
        choices = []
        bits = remaining
        while bits:
            bit = bits & -bits
            pivot = bit.bit_length() - 1
            choices.append(((adjacency[pivot] & remaining).bit_count(), pivot))
            bits ^= bit
        _, pivot = min(choices)
        nodes += 1
        partners = adjacency[pivot] & remaining
        while partners:
            bit = partners & -partners
            partner = bit.bit_length() - 1
            edge = tuple(sorted((UNITS[pivot], UNITS[partner])))
            visit(remaining & ~(1 << pivot) & ~bit, pairs + (edge,))
            if stopped:
                return
            partners ^= bit

    visit((1 << len(UNITS)) - 1, ())
    return found, nodes, stopped


def expected_status(count: int, stopped: bool) -> str:
    if stopped:
        return "unknown_budget"
    if count == 0:
        return "none"
    return "unique" if count == 1 else "multiple"


def edge_category(edge: tuple[str, str], observed: frozenset[str]) -> str:
    left, right = edge[0] in observed, edge[1] in observed
    return "observed_observed" if left and right else "observed_unseen" if left or right else "unseen_unseen"


def count_categories(edges: Any, observed: frozenset[str]) -> dict[str, int]:
    return dict(Counter(edge_category(edge, observed) for edge in edges)) | {name: 0 for name in CATEGORIES if name not in Counter(edge_category(edge, observed) for edge in edges)}


def source_and_ciphertext(corpus: str, loaded: dict[str, Any]) -> tuple[tuple[str, ...], str, dict[str, Any]]:
    data = loaded[corpus]
    key = seeded_control_key("cap2", 7000)
    ciphertext = tuple(encrypt_words(data["words"]["validation"], key))
    del key
    stream = tuple(unit for word in ciphertext for unit in word)
    return stream, canonical_hash([list(word) for word in ciphertext]), data["metadata"]


def load_verified_inputs() -> tuple[dict[str, Any], str, dict[str, Any], int]:
    freeze_raw = FREEZE_PATH.read_bytes()
    freeze_hash = digest_bytes(freeze_raw)
    if freeze_hash != EXPECTED_FREEZE_SHA256:
        raise ValueError("corrected freeze hash mismatch")
    freeze = json.loads(freeze_raw.decode("utf-8"))
    if not isinstance(freeze, dict) or not isinstance(freeze.get("files"), list):
        raise ValueError("freeze record is malformed")
    freeze_files = {item.get("path"): item.get("sha256") for item in freeze["files"] if isinstance(item, dict)}
    if len(freeze_files) != 28 or any(not isinstance(name, str) or not isinstance(digest, str) for name, digest in freeze_files.items()):
        raise ValueError("freeze file allowlist is not the reviewed 28-file set")
    if any(digest_bytes((ROOT / name).read_bytes()) != digest for name, digest in freeze_files.items()):
        raise ValueError("a frozen file hash does not match")
    loaded = load_reference_partitions(ROOT)
    return freeze, freeze_hash, loaded, len(freeze_files)


def provenance_checks(input_record: dict[str, Any], pairing_record: dict[str, Any], source_metadata: dict[str, Any], freeze: dict[str, Any], freeze_hash: str) -> dict[str, bool]:
    freeze_files = {item["path"]: item["sha256"] for item in freeze["files"]}
    source_files = {name: info["sha256"] for name, info in source_metadata["source_files"].items()}
    code_hashes = {name: digest for name, digest in freeze_files.items() if Path(name).suffix == ".py" and "test" not in Path(name).name}
    test_hashes = {name: digest for name, digest in freeze_files.items() if Path(name).suffix == ".py" and "test" in Path(name).name}
    return {
        "manifest": input_record.get("manifest_sha256") == freeze_hash,
        "source_manifest": input_record.get("source_manifest_sha256") == source_metadata["reference_manifest_sha256"],
        "source_files": input_record.get("source_file_hashes") == source_files,
        "code_hashes": input_record.get("code_hashes") == code_hashes,
        "test_hashes": input_record.get("test_hashes") == test_hashes,
        "frozen_file_hashes": input_record.get("frozen_file_hashes") == freeze_files,
        "pairing_provenance": all(pairing_record.get(field) == input_record.get(field) for field in ("manifest_sha256", "source_manifest_sha256", "source_file_hashes", "code_hashes", "test_hashes", "frozen_file_hashes")),
        "current_frozen_files": all(digest_bytes((ROOT / name).read_bytes()) == digest for name, digest in freeze_files.items()),
    }


def diagnostics_consistent(diagnostics: dict[str, Any], pairing: dict[str, Any]) -> bool:
    matching = pairing["matching"]
    if any(diagnostics.get(field) != matching.get("status") for field in ("status", "full_matching_status", "matching_status")):
        return False
    if diagnostics.get("matching_witness_count") != matching.get("witness_count"):
        return False
    raw_witnesses, witnesses = matching.get("witnesses"), diagnostics.get("witnesses")
    if not isinstance(raw_witnesses, list) or not isinstance(witnesses, list) or len(raw_witnesses) != len(witnesses):
        return False
    for index, item in enumerate(witnesses):
        if not isinstance(item, dict) or item.get("witness_index") != index:
            return False
        try:
            witness = matching_value(raw_witnesses[index])
        except ValueError:
            return False
        if item.get("pair_set_sha256") != pairs_hash(witness) or item.get("control_pair_overlap_count") != len(item.get("control_pairs_in_witness", [])):
            return False
    overlap, missing, orientation = diagnostics.get("graph_control_pair_overlap"), diagnostics.get("graph_control_pair_missing"), diagnostics.get("orientation")
    return isinstance(overlap, list) and isinstance(missing, list) and diagnostics.get("graph_control_pair_overlap_count") == len(overlap) and diagnostics.get("control_pair_count") == 26 and isinstance(orientation, dict) and orientation.get("comparable_count") == orientation.get("match_count", -1) + orientation.get("mismatch_count", -1) and orientation.get("mismatch_count") == 0


def audit_corpus(corpus: str, loaded: dict[str, Any], freeze: dict[str, Any], freeze_hash: str) -> dict[str, Any]:
    records, record_hashes = {}, {}
    for name in ("input", "pairing", "diagnostics"):
        record_name = f"{name}.json"
        records[name], record_hashes[record_name] = read_pinned_json(INPUT_ROOT / corpus / record_name, EXPECTED_RECORD_HASHES[corpus][record_name])
    input_record, pairing, diagnostics = records["input"], records["pairing"], records["diagnostics"]
    stream, stream_hash, source_metadata = source_and_ciphertext(corpus, loaded)
    validation_word_count = len(loaded[corpus]["words"]["validation"])
    edges, observed = graph_from_stream(stream)
    unseen = frozenset(UNITS) - observed
    exact, nodes, stopped = enumerate_full(edges)
    exact_status = expected_status(len(exact), stopped)
    matching = pairing["matching"]
    report_witnesses = tuple(matching_value(value) for value in matching.get("witnesses", []))
    exact_set = set(exact)
    witnesses_valid = all(witness in exact_set for witness in report_witnesses)
    selected = matching_value(pairing["forced"].get("selected_witness"))
    all_forced = set(next(iter(exact), ()))
    for witness in exact:
        all_forced.intersection_update(witness)
    evidence, reported_forced, evidence_edges = pairing["forced"].get("edge_evidence", []), set(), set()
    independent_category_counts = {name: {status: 0 for status in ("forced", "not_forced", "unknown")} for name in CATEGORIES}
    alternatives_valid = True
    for item in evidence:
        edge = pair_value(item.get("edge"))
        evidence_edges.add(edge)
        alternatives = [witness for witness in exact if edge not in witness]
        expected = "forced" if not alternatives else "not_forced"
        independent_category_counts[edge_category(edge, observed)][expected] += 1
        if item.get("status") != expected or edge not in set(selected) or edge not in edges:
            alternatives_valid = False
        if expected == "forced":
            reported_forced.add(edge)
            if item.get("alternative_witness") is not None:
                alternatives_valid = False
        else:
            try:
                alternative = matching_value(item.get("alternative_witness"))
            except ValueError:
                alternatives_valid = False
            else:
                alternatives_valid &= alternative in exact_set and edge not in alternative
    residual_units = tuple(unit for unit in UNITS if not any(unit in edge for edge in all_forced))
    residual_edges = {edge for edge in edges if set(edge) <= set(residual_units)}
    residual_matchings = {tuple(sorted(set(witness) - all_forced)) for witness in exact}
    signatures = {tuple(sorted(edge for edge in witness if set(edge) <= observed)) for witness in exact}
    graph_counts = {"vertex_count": 52, "observed_vertex_count": len(observed), "unseen_vertex_count": len(unseen), "edge_count": len(edges), "edge_counts_by_category": count_categories(edges, observed), "edge_set_sha256": pairs_hash(edges)}
    reported_graph = pairing.get("graph", {})
    checks = {
        "stream_hash": input_record.get("validation_stream_sha256") == stream_hash,
        "input_counts": input_record.get("word_count") == validation_word_count and input_record.get("unit_token_count") == len(stream) and input_record.get("unit_type_count") == len(observed),
        "graph_counts": all(reported_graph.get(field) == graph_counts[field] for field in ("vertex_count", "observed_vertex_count", "unseen_vertex_count", "edge_count", "edge_counts_by_category")),
        "matching_status": matching.get("status") == exact_status,
        "matching_witnesses": matching.get("witness_count") == len(report_witnesses) and witnesses_valid,
        "selected_witness": selected in exact_set and selected == report_witnesses[0],
        "forced_categories": pairing["forced"].get("category_counts") == independent_category_counts,
        "forced_edges": evidence_edges == set(selected) and reported_forced == all_forced,
        "forced_alternatives": alternatives_valid,
        "forced_queries": pairing["forced"].get("queries_run") == len(evidence) and pairing["forced"].get("queries_skipped") == 0,
        "diagnostic_record_consistency": diagnostics_consistent(diagnostics, pairing),
    }
    checks["all"] = all(checks.values()) and not stopped
    return {
        "record_hashes": record_hashes,
        "provenance": provenance_checks(input_record, pairing, source_metadata, freeze, freeze_hash),
        "source_reconstruction": {"word_count": validation_word_count, "unit_token_count": len(stream), "unit_type_count": len(observed), "validation_stream_sha256": stream_hash},
        "graph": graph_counts,
        "matching": {"independent_status": exact_status, "independent_full_matching_count": len(exact) if not stopped else None, "independent_nodes_visited": nodes, "search_exhausted": not stopped, "reported_status": matching.get("status"), "reported_witness_count": matching.get("witness_count"), "reported_witnesses_valid": witnesses_valid, "distinct_observed_relations": len(signatures) if not stopped else None, "full_matching_set_sha256": matching_set_hash(exact) if not stopped else None},
        "forced": {"reported_category_counts": pairing["forced"].get("category_counts"), "independent_category_counts": independent_category_counts, "reported_forced_edge_count": len(reported_forced), "independent_forced_edge_count": len(all_forced), "reported_edges_are_valid": alternatives_valid, "forced_edge_set_sha256": pairs_hash(all_forced)},
        "residual": {"unit_count": len(residual_units), "edge_count": len(residual_edges), "complete_simple_graph": len(residual_edges) == len(residual_units) * (len(residual_units) - 1) // 2, "matching_count": len(residual_matchings) if not stopped else None},
        "checks": checks,
    }


def main() -> int:
    freeze, freeze_hash, loaded, frozen_file_count = load_verified_inputs()
    corpora, failures = {}, []
    for corpus in CORPORA:
        try:
            corpora[corpus] = audit_corpus(corpus, loaded, freeze, freeze_hash)
            if not corpora[corpus]["checks"]["all"] or not all(corpora[corpus]["provenance"].values()):
                failures.append(corpus)
        except Exception as error:
            corpora[corpus] = {"checks": {"all": False}, "error_type": type(error).__name__}
            failures.append(corpus)
    result = {"schema_version": 1, "verification": "cyclic-pairing-control-v1-independent-audit", "status": "PASS" if not failures else "FAIL", "method": "Independent standard-library graph construction and exhaustive full matching enumeration. The pinned loader and fixed emitter only rebuild validation ciphertext.", "freeze": {"manifest_sha256": freeze_hash, "file_count": frozen_file_count, "all_frozen_files_match": True, "matching_node_limit": MATCHING_NODE_LIMIT}, "corpora": corpora}
    temporary = OUTPUT_PATH.with_suffix(".tmp")
    temporary.write_bytes((json.dumps(result, sort_keys=True, separators=(",", ":")) + "\n").encode())
    temporary.replace(OUTPUT_PATH)
    print(json.dumps({"status": result["status"], "corpora": {name: data.get("checks", {}).get("all", False) for name, data in corpora.items()}}, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
