#!/usr/bin/env python3
"""Fetch the pinned Naibbe table into the manifest path."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


REPOSITORY_URL = "https://github.com/greshko/naibbe-cipher"
RAW_TABLE_URL = (
    "https://raw.githubusercontent.com/greshko/naibbe-cipher/"
    "{commit}/references/naibbe_tables.csv"
)
COMMIT_PATTERN = re.compile(r"^[0-9a-fA-F]{40}$")
SHA256_PATTERN = re.compile(r"^[0-9a-fA-F]{64}$")
DEFAULT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = DEFAULT_ROOT / "data" / "naibbe_source_manifest.json"


class FetchError(RuntimeError):
    """Report a pinned-source fetch error."""


def sha256_file(path: Path) -> str:
    """Return the SHA-256 digest for one file."""

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_manifest(path: Path) -> dict[str, object]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            manifest = json.load(handle)
    except (OSError, json.JSONDecodeError) as error:
        raise FetchError(f"could not read manifest {path}: {error}") from error
    if not isinstance(manifest, dict):
        raise FetchError("Naibbe source manifest must contain a JSON object")
    return manifest


def _pinned_source(manifest: dict[str, object]) -> tuple[str, str, str]:
    repository = manifest.get("repository")
    if not isinstance(repository, dict):
        raise FetchError("Naibbe source manifest has no repository object")
    if repository.get("url") != REPOSITORY_URL:
        raise FetchError("Naibbe source manifest has an unexpected repository URL")

    commit = repository.get("commit")
    table_file = repository.get("table_file")
    expected_sha256 = repository.get("table_sha256")
    if not isinstance(commit, str) or not COMMIT_PATTERN.fullmatch(commit):
        raise FetchError("repository commit must be a 40-character hexadecimal pin")
    if not isinstance(table_file, str) or not table_file or Path(table_file).is_absolute():
        raise FetchError("repository table_file must be a relative path")
    if not isinstance(expected_sha256, str) or not SHA256_PATTERN.fullmatch(expected_sha256):
        raise FetchError("repository table_sha256 must be a 64-character hexadecimal hash")
    return commit, table_file, expected_sha256.lower()


def _repository_path(root: Path, relative_path: str) -> Path:
    root = root.resolve()
    path = (root / relative_path).resolve()
    try:
        path.relative_to(root)
    except ValueError as error:
        raise FetchError(f"table_file escapes the repository root: {relative_path}") from error
    return path


def _existing_report(destination: Path, expected_sha256: str) -> dict[str, object]:
    if destination.is_symlink():
        raise FetchError(f"refusing symbolic-link table path: {destination}")
    if not destination.is_file():
        raise FetchError(f"table path is not a regular file: {destination}")
    actual_sha256 = sha256_file(destination)
    if actual_sha256 != expected_sha256:
        raise FetchError(
            f"existing table hash mismatch: expected {expected_sha256}, "
            f"got {actual_sha256}"
        )
    return {
        "status": "already_present",
        "sha256": actual_sha256,
        "bytes": destination.stat().st_size,
    }


def _download_atomic(
    url: str,
    destination: Path,
    expected_sha256: str,
    *,
    timeout: float,
) -> dict[str, object]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        request = Request(url, headers={"User-Agent": "voynich-naibbe-fetch/1"})
        with urlopen(request, timeout=timeout) as response:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                dir=destination.parent,
                prefix=f".{destination.name}.",
                delete=False,
            ) as temporary:
                temporary_path = Path(temporary.name)
                for block in iter(lambda: response.read(1024 * 1024), b""):
                    temporary.write(block)
                temporary.flush()
                os.fsync(temporary.fileno())

        actual_sha256 = sha256_file(temporary_path)
        if actual_sha256 != expected_sha256:
            raise FetchError(
                f"download hash mismatch: expected {expected_sha256}, "
                f"got {actual_sha256}"
            )

        if destination.exists() or destination.is_symlink():
            existing = _existing_report(destination, expected_sha256)
            return existing

        os.replace(temporary_path, destination)
        temporary_path = None
        return {
            "status": "downloaded",
            "sha256": actual_sha256,
            "bytes": destination.stat().st_size,
        }
    except FetchError:
        raise
    except (HTTPError, URLError, TimeoutError, OSError) as error:
        raise FetchError(f"could not fetch {url}: {error}") from error
    finally:
        if temporary_path is not None:
            try:
                temporary_path.unlink()
            except FileNotFoundError:
                pass


def fetch_table(
    manifest_path: Path,
    repo_root: Path,
    *,
    timeout: float = 60.0,
) -> dict[str, object]:
    """Fetch one pinned CSV and return a short verification report."""

    manifest = _load_manifest(manifest_path)
    commit, table_file, expected_sha256 = _pinned_source(manifest)
    destination = _repository_path(repo_root, table_file)
    if destination.exists() or destination.is_symlink():
        result = _existing_report(destination, expected_sha256)
    else:
        url = RAW_TABLE_URL.format(commit=commit)
        result = _download_atomic(
            url,
            destination,
            expected_sha256,
            timeout=timeout,
        )

    root = repo_root.resolve()
    try:
        relative_path = str(destination.relative_to(root))
    except ValueError:
        relative_path = str(destination)
    result.update(
        {
            "url": RAW_TABLE_URL.format(commit=commit),
            "commit": commit,
            "path": relative_path,
            "expected_sha256": expected_sha256,
        }
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=DEFAULT_ROOT,
        help="repository root (default: parent of scripts/)",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=None,
        help="source manifest (default: ROOT/data/naibbe_source_manifest.json)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=60.0,
        help="network timeout in seconds (default: 60)",
    )
    args = parser.parse_args()
    root = args.root.resolve()
    manifest_path = (args.manifest or root / "data" / "naibbe_source_manifest.json").resolve()
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    try:
        report = fetch_table(manifest_path, root, timeout=args.timeout)
    except FetchError as error:
        parser.error(str(error))
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
