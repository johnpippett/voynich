#!/usr/bin/env python3
"""Print aggregate fixed-table Naibbe compatibility counts.

The script does not fit table entries, rank plaintext candidates, or print raw
VMS tokens. It includes one short known-plaintext control.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from voynich.corpus import parse_ivtff  # noqa: E402
from voynich.naibbe import (  # noqa: E402
    ForwardConfig,
    WEIGHTS_52,
    compatibility_aggregate,
    encrypt_fixed,
    load_table_csv,
    sha256_file,
)


DEFAULT_MANIFEST = ROOT / "data/naibbe_source_manifest.json"
DEFAULT_TABLE = ROOT / "data/raw/naibbe/naibbe-cipher/references/naibbe_tables.csv"
DEFAULT_SOURCES = ("ZL3b", "IT2a")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_manifest(path: Path) -> dict[str, object]:
    with path.open("r", encoding="utf-8") as handle:
        manifest = json.load(handle)
    if not isinstance(manifest, dict):
        raise ValueError("Naibbe source manifest must contain a JSON object")
    return manifest


def _manifest_sources(manifest: dict[str, object]) -> dict[str, dict[str, str]]:
    values = manifest.get("vms_inputs")
    if not isinstance(values, list):
        raise ValueError("Naibbe source manifest has no vms_inputs list")
    sources: dict[str, dict[str, str]] = {}
    for value in values:
        if not isinstance(value, dict):
            raise ValueError("Naibbe source manifest contains an invalid VMS input")
        source_id = value.get("id")
        source_path = value.get("path")
        source_hash = value.get("sha256")
        if not all(isinstance(item, str) for item in (source_id, source_path, source_hash)):
            raise ValueError("Naibbe VMS input needs id, path, and sha256 strings")
        sources[source_id] = {"path": source_path, "sha256": source_hash}
    return sources


def _source_summary(
    source_id: str,
    source_path: Path,
    expected_hash: str,
    book,
    uncertain_spaces: str,
) -> dict[str, object]:
    actual_hash = _sha256(source_path)
    if actual_hash.lower() != expected_hash.lower():
        raise ValueError(
            f"source SHA-256 mismatch for {source_id}: expected {expected_hash}, "
            f"got {actual_hash}"
        )
    records = parse_ivtff(source_path, uncertain_spaces=uncertain_spaces)
    tokens = [token for record in records for token in record["tokens"]]
    result = compatibility_aggregate(tokens, book)
    result.update(
        {
            "source_sha256": actual_hash,
            "record_count": len(records),
            "excluded_token_count": sum(record["excluded_tokens"] for record in records),
            "uncertain_spaces": uncertain_spaces,
        }
    )
    return result


def _control(book) -> dict[str, object]:
    config = ForwardConfig(
        weights=WEIGHTS_52,
        respacing_numerator=17,
        respacing_denominator=36,
        collision_policy="unigram",
        normalize=True,
    )
    result = encrypt_fixed("arma", book, config=config, seed=0)
    return {
        "plaintext": "arma",
        "seed": 0,
        "units": list(result.units),
        "tokens": list(result.tokens),
        "candidate_counts": [
            len(book.candidates(token).candidates) for token in result.tokens
        ],
        "config": config.to_dict(),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--table", type=Path, default=DEFAULT_TABLE)
    parser.add_argument(
        "--source",
        action="append",
        dest="sources",
        choices=DEFAULT_SOURCES,
        help="VMS source id; repeat the option to select more than one source",
    )
    parser.add_argument(
        "--uncertain-spaces",
        choices=("split", "join"),
        default="split",
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.output is not None and args.output.exists():
        parser.error('The output file exists. Select a new output path.')

    manifest = _read_manifest(args.manifest)
    repository = manifest.get("repository")
    if not isinstance(repository, dict):
        raise ValueError("Naibbe source manifest has no repository object")
    expected_table_hash = repository.get("table_sha256")
    if not isinstance(expected_table_hash, str):
        raise ValueError("Naibbe source manifest has no table SHA-256")
    book = load_table_csv(args.table, expected_sha256=expected_table_hash)

    source_map = _manifest_sources(manifest)
    selected = tuple(args.sources or DEFAULT_SOURCES)
    source_results: dict[str, object] = {}
    for source_id in selected:
        if source_id not in source_map:
            raise ValueError(f"source {source_id!r} is not in the manifest")
        source_info = source_map[source_id]
        source_path = ROOT / source_info["path"]
        source_results[source_id] = _source_summary(
            source_id,
            source_path,
            source_info["sha256"],
            book,
            args.uncertain_spaces,
        )

    report = {
        "status": "fixed_table_compatibility_only",
        "manifest_sha256": _sha256(args.manifest),
        "code_sha256": {
            str(path.relative_to(ROOT)): _sha256(path)
            for path in [Path(__file__), ROOT / 'src/voynich/corpus.py',
                         ROOT / 'src/voynich/naibbe.py']
        },
        "table": {
            "path": str(args.table.relative_to(ROOT))
            if args.table.is_absolute() and args.table.is_relative_to(ROOT)
            else str(args.table),
            "sha256": sha256_file(args.table),
            "alphabet_size": len(book.alphabet),
            "row_count": len(book.glyphs),
            "bigram_catalog_size": len(book.bigram_catalog),
        },
        "sources": source_results,
        "controlled_example": _control(book),
        "limits": [
            "The table file is a fixed published artifact. This run does not fit it to VMS tokens.",
            "The published tables used Voynich features during construction. Compatibility is not independent evidence of a historical cipher.",
            "Counts test token compatibility. They do not select a plaintext language or prove a cipher.",
            "Candidate counts retain table choices. No language model ranks or removes candidates.",
            "The forward control does not simulate output space-removal joins.",
        ],
    }
    encoded = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output is None:
        print(encoded, end="")
    else:
        args.output.write_text(encoded, encoding="utf-8")
        print(args.output)


if __name__ == "__main__":
    main()
