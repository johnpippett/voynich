#!/usr/bin/env python3
"""Fetch the current original-provider IVTFF files and write a manifest."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import tempfile
from urllib.request import Request, urlopen


SOURCE_PAGE = "https://www.voynich.nu/transcr.html"
SOURCES = (
    {
        "id": "ZL",
        "filename": "ZL3b-n.txt",
        "url": "https://www.voynich.nu/data/ZL3b-n.txt",
        "description": "Zandbergen-Landini IVTFF transliteration, version 3b",
        "attribution": "René Zandbergen and Gabriel Landini; file header identifies the ZL transliteration.",
    },
    {
        "id": "IT",
        "filename": "IT2a-n.txt",
        "url": "https://www.voynich.nu/data/IT2a-n.txt",
        "description": "Takeshi Takahashi transliteration extracted from the Landini-Stolfi interlinear file, IVTFF version 2a",
        "attribution": "Takeshi Takahashi; IVTFF copy published by René Zandbergen and identified as IT.",
    },
)

USE_LIMITS = (
    "The source page does not state an open licence for these files. "
    "Keep source attribution and verify permission before redistribution."
)


def fetch_bytes(url: str) -> bytes:
    request = Request(url, headers={"User-Agent": "voynich-research-fetch/1.0"})
    with urlopen(request, timeout=60) as response:
        return response.read()


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _load_pinned_manifest(path: Path) -> dict:
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"cannot read pinned source manifest {path}") from exc
    entries = manifest.get("sources")
    if not isinstance(entries, list):
        raise RuntimeError(f"pinned source manifest {path} has no sources list")
    by_id = {entry.get("id"): entry for entry in entries if isinstance(entry, dict)}
    for source in SOURCES:
        entry = by_id.get(source["id"])
        if not entry or not isinstance(entry.get("sha256"), str):
            raise RuntimeError(
                f"source {source['id']} has no pinned hash; use --refresh-manifest"
            )
        if entry.get("path") != f"data/raw/{source['filename']}":
            raise RuntimeError(f"source {source['id']} has an unexpected pinned path")
    return manifest


def fetch_sources(root: Path, manifest_path: Path, refresh_manifest: bool = False) -> dict:
    """Fetch all configured sources and return the manifest object.

    A normal run verifies the existing manifest before it writes any file. Use
    ``refresh_manifest=True`` when a deliberate source update is required.
    """

    raw_dir = root / "data" / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    pinned = None
    if manifest_path.exists() and not refresh_manifest:
        pinned = _load_pinned_manifest(manifest_path)
    elif not manifest_path.exists() and not refresh_manifest:
        raise RuntimeError(
            f"source manifest {manifest_path} is missing; use --refresh-manifest"
        )

    fetched_at = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    entries = []
    downloaded: list[tuple[dict, bytes]] = []

    for source in SOURCES:
        data = fetch_bytes(source["url"])
        if pinned is not None:
            pinned_entry = next(
                entry for entry in pinned["sources"] if entry.get("id") == source["id"]
            )
            actual_hash = digest(data)
            if actual_hash != pinned_entry["sha256"]:
                raise RuntimeError(
                    f"source {source['id']} hash changed: expected {pinned_entry['sha256']}, "
                    f"got {actual_hash}; use --refresh-manifest"
                )
        downloaded.append((source, data))

    for source, data in downloaded:
        destination = raw_dir / source["filename"]
        # Write through a temporary file so an interrupted download cannot
        # leave a partial source file in the corpus.
        with tempfile.NamedTemporaryFile(
            mode="wb", prefix=f".{destination.name}.", dir=destination.parent, delete=False
        ) as temporary:
            temporary.write(data)
            temporary_path = Path(temporary.name)
        temporary_path.replace(destination)
        entries.append(
            {
                "id": source["id"],
                "path": str(destination.relative_to(root)),
                "source_url": source["url"],
                "source_page_url": SOURCE_PAGE,
                "retrieved_at_utc": fetched_at,
                "bytes": len(data),
                "sha256": digest(data),
                "description": source["description"],
                "attribution": source["attribution"],
                "use_limits": USE_LIMITS,
            }
        )

    if pinned is not None:
        return pinned

    manifest = {
        "schema": "voynich-source-manifest-v1",
        "generated_at_utc": fetched_at,
        "sources": entries,
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="repository root (default: parent of scripts/)",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=None,
        help="manifest path (default: ROOT/data/source_manifest.json)",
    )
    parser.add_argument(
        "--refresh-manifest",
        action="store_true",
        help="accept current source hashes and replace the pinned manifest",
    )
    args = parser.parse_args()
    root = args.root.resolve()
    manifest_path = (args.manifest or root / "data" / "source_manifest.json").resolve()
    try:
        manifest = fetch_sources(root, manifest_path, refresh_manifest=args.refresh_manifest)
    except RuntimeError as exc:
        parser.error(str(exc))
    for source in manifest["sources"]:
        print(f"{source['id']}: {source['bytes']} bytes {source['sha256']} -> {source['path']}")
    print(f"manifest: {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
