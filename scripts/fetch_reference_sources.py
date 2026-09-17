#!/usr/bin/env python3
"""Fetch pinned Universal Dependencies reference treebanks.

The manifest contains a hash for every downloaded file and every extracted
text file. Existing files with a different hash cause a hard failure.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import tempfile
import unicodedata
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


INTEGER_ID = re.compile(r"^[0-9]+$")
MWT_ID = re.compile(r"^([0-9]+)-([0-9]+)$")
EMPTY_ID = re.compile(r"^[0-9]+\.[0-9]+$")


class FetchError(RuntimeError):
    """Report a deterministic fetch or extraction failure."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_hash(path: Path, expected: str, description: str) -> None:
    actual = sha256_file(path)
    if actual != expected:
        raise FetchError(
            f"hash mismatch for {description}: expected {expected}, got {actual}"
        )


def download_verified(url: str, destination: Path, expected: str) -> None:
    """Download one file atomically after checking its expected hash."""

    if destination.exists():
        verify_hash(destination, expected, str(destination))
        return

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        request = Request(url, headers={"User-Agent": "voynich-reference-fetch/1"})
        with urlopen(request, timeout=60) as response:
            with tempfile.NamedTemporaryFile(
                mode="wb", dir=destination.parent, prefix=f".{destination.name}.", delete=False
            ) as temporary:
                temporary_path = Path(temporary.name)
                for block in iter(lambda: response.read(1024 * 1024), b""):
                    temporary.write(block)
        verify_hash(temporary_path, expected, url)
        temporary_path.replace(destination)
        temporary_path = None
    except (HTTPError, URLError, TimeoutError, OSError) as error:
        raise FetchError(f"could not fetch {url}: {error}") from error
    finally:
        if temporary_path is not None:
            try:
                temporary_path.unlink()
            except FileNotFoundError:
                pass


def is_word_like(text: str) -> bool:
    """Return true when a multiword surface form contains a letter or number."""

    return any(unicodedata.category(char)[0] in {"L", "N"} for char in text)


def extract_conllu(paths: list[Path]) -> tuple[str, dict[str, int]]:
    """Extract surface words from CoNLL-U files in the given split order.

    Comments are ignored. Multiword-token rows keep their surface FORM when it
    contains a letter or number. Integer component rows covered by a retained
    multiword-token range are skipped. Empty nodes and UPOS=PUNCT rows are
    skipped. Other integer rows keep their FORM value. One non-empty sentence
    is written per line, with one ASCII space between forms.
    """

    output_lines: list[str] = []
    counts = {
        "input_sentence_count": 0,
        "input_syntactic_rows": 0,
        "punctuation_rows_excluded": 0,
        "mwt_rows_retained": 0,
        "covered_component_rows_skipped": 0,
        "empty_nodes_skipped": 0,
        "output_sentence_count": 0,
        "output_token_count": 0,
    }

    for path in paths:
        rows: list[tuple[str, object, str, str]] = []

        def finish_sentence() -> None:
            if not rows:
                return
            counts["input_sentence_count"] += 1
            covered: set[int] = set()
            for kind, identifier, _form, _upos in rows:
                if kind == "mwt":
                    start, end = identifier  # type: ignore[misc]
                    covered.update(range(start, end + 1))

            forms: list[str] = []
            for kind, identifier, form, upos in rows:
                if kind == "mwt":
                    if form != "_" and is_word_like(form):
                        forms.append(form)
                        counts["mwt_rows_retained"] += 1
                elif kind == "empty":
                    counts["empty_nodes_skipped"] += 1
                else:
                    integer_id = identifier  # type: ignore[assignment]
                    counts["input_syntactic_rows"] += 1
                    if integer_id in covered:
                        counts["covered_component_rows_skipped"] += 1
                    elif upos == "PUNCT":
                        counts["punctuation_rows_excluded"] += 1
                    elif form != "_":
                        forms.append(form)

            if forms:
                output_lines.append(" ".join(forms))
                counts["output_sentence_count"] += 1
                counts["output_token_count"] += len(forms)

        try:
            with path.open("r", encoding="utf-8", newline="") as handle:
                for raw_line in handle:
                    line = raw_line.rstrip("\r\n")
                    if not line.strip():
                        finish_sentence()
                        rows = []
                        continue
                    if line.startswith("#"):
                        continue
                    fields = line.split("\t")
                    if len(fields) != 10:
                        raise FetchError(f"invalid CoNLL-U row in {path}: {line!r}")
                    identifier, form, upos = fields[0], fields[1], fields[3]
                    mwt_match = MWT_ID.fullmatch(identifier)
                    if mwt_match:
                        rows.append(
                            (
                                "mwt",
                                (int(mwt_match.group(1)), int(mwt_match.group(2))),
                                form,
                                upos,
                            )
                        )
                    elif EMPTY_ID.fullmatch(identifier):
                        rows.append(("empty", identifier, form, upos))
                    elif INTEGER_ID.fullmatch(identifier):
                        rows.append(("integer", int(identifier), form, upos))
                    else:
                        raise FetchError(
                            f"unsupported CoNLL-U ID in {path}: {identifier!r}"
                        )
            finish_sentence()
        except UnicodeDecodeError as error:
            raise FetchError(f"{path} is not valid UTF-8: {error}") from error

    text = "\n".join(output_lines) + "\n"
    return text, counts


def load_manifest(path: Path) -> dict[str, object]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            manifest = json.load(handle)
    except (OSError, json.JSONDecodeError) as error:
        raise FetchError(f"could not read manifest {path}: {error}") from error
    if not isinstance(manifest, dict) or not isinstance(manifest.get("corpora"), list):
        raise FetchError("manifest must contain a corpora list")
    return manifest


def output_path(root: Path, relative_path: str) -> Path:
    path = (root / relative_path).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as error:
        raise FetchError(f"path escapes repository root: {relative_path}") from error
    return path


def run(manifest_path: Path, repo_root: Path) -> None:
    manifest = load_manifest(manifest_path)
    raw_root = output_path(repo_root, str(manifest.get("raw_output_dir", "data/raw/reference")))

    for corpus in manifest["corpora"]:
        if not isinstance(corpus, dict):
            raise FetchError("each corpus entry must be an object")
        corpus_id = corpus.get("id")
        if not isinstance(corpus_id, str) or not corpus_id:
            raise FetchError("each corpus must have a non-empty id")
        corpus_root = output_path(raw_root, corpus_id)
        files = corpus.get("files")
        if not isinstance(files, list):
            raise FetchError(f"{corpus_id} must contain a files list")
        data_paths: dict[str, Path] = {}
        for source_file in files:
            if not isinstance(source_file, dict):
                raise FetchError(f"{corpus_id} has an invalid file entry")
            name = source_file.get("name")
            url = source_file.get("url")
            expected = source_file.get("sha256")
            if not all(isinstance(value, str) and value for value in (name, url, expected)):
                raise FetchError(f"{corpus_id} has an incomplete file entry")
            destination = output_path(corpus_root, name)
            download_verified(url, destination, expected)
            role = source_file.get("role")
            split = source_file.get("split")
            if role == "conllu":
                if not isinstance(split, str) or not split:
                    raise FetchError(f"{corpus_id}/{name} has no split")
                data_paths[split] = destination

        extraction = corpus.get("extraction")
        if not isinstance(extraction, dict):
            raise FetchError(f"{corpus_id} must contain extraction metadata")
        split_order = extraction.get("split_order")
        if not isinstance(split_order, list) or not all(
            isinstance(split, str) for split in split_order
        ):
            raise FetchError(f"{corpus_id} has an invalid split order")
        try:
            conllu_paths = [data_paths[split] for split in split_order]
        except KeyError as error:
            raise FetchError(f"{corpus_id} is missing split {error.args[0]}") from error

        text, counts = extract_conllu(conllu_paths)
        output = extraction.get("output")
        if not isinstance(output, dict):
            raise FetchError(f"{corpus_id} must contain extraction output metadata")
        relative_text = output.get("path")
        expected_text_hash = output.get("sha256")
        if not isinstance(relative_text, str) or not isinstance(expected_text_hash, str):
            raise FetchError(f"{corpus_id} has incomplete output metadata")
        actual_text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if actual_text_hash != expected_text_hash:
            raise FetchError(
                f"extraction hash mismatch for {corpus_id}: expected "
                f"{expected_text_hash}, got {actual_text_hash}"
            )
        for key, expected_value in output.get("counts", {}).items():
            if counts.get(key) != expected_value:
                raise FetchError(
                    f"extraction count mismatch for {corpus_id}/{key}: "
                    f"expected {expected_value}, got {counts.get(key)}"
                )
        text_destination = output_path(corpus_root, relative_text)
        if text_destination.exists():
            verify_hash(text_destination, expected_text_hash, str(text_destination))
        else:
            text_destination.parent.mkdir(parents=True, exist_ok=True)
            temporary_path: Path | None = None
            try:
                with tempfile.NamedTemporaryFile(
                    mode="wb", dir=text_destination.parent, prefix=f".{text_destination.name}.", delete=False
                ) as temporary:
                    temporary_path = Path(temporary.name)
                    temporary.write(text.encode("utf-8"))
                verify_hash(temporary_path, expected_text_hash, str(text_destination))
                temporary_path.replace(text_destination)
                temporary_path = None
            finally:
                if temporary_path is not None:
                    try:
                        temporary_path.unlink()
                    except FileNotFoundError:
                        pass
        print(
            f"{corpus_id}: {counts['output_sentence_count']} sentences, "
            f"{counts['output_token_count']} tokens; hashes verified"
        )


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    script_root = Path(__file__).resolve().parents[1]
    parser.add_argument(
        "--manifest",
        type=Path,
        default=script_root / "data" / "reference_manifest.json",
        help="path to the pinned source manifest",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=script_root,
        help="repository root that contains data/raw/reference",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        run(args.manifest.resolve(), args.repo_root.resolve())
    except FetchError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
