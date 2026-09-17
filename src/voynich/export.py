"""Select public aggregate fields from a saved Voynich analysis result."""

from __future__ import annotations

import math
import os
from pathlib import Path
import re
from typing import Any


_DROP = object()

_DENIED_KEYS = {
    "alphabet",
    "decoded",
    "decoded_string",
    "decoded_text",
    "decoded_word",
    "image_path",
    "models",
    "raw",
    "raw_records",
    "raw_text",
    "records_jsonl",
    "source_path",
    "source_url",
    "text",
    "text_raw",
    "top_tokens",
    "vocab",
    "vocabulary",
}

_SAFE_SYMBOLS = {
    "<BOS>",
    "<EOS>",
    "<UNK>",
    "cth",
    "ckh",
    "cph",
    "cfh",
    "ch",
    "sh",
    "iin",
    "in",
}

_TOP_LEVEL_KEYS = (
    "status",
    "provenance",
    "config",
    "structure",
    "predictive",
    "context",
)

_PROVENANCE_KEYS = (
    "source_path",
    "source_sha256",
    "created_utc",
    "python",
    "package_version",
    "code_sha256",
    "design_sha256",
)

_STRUCTURE_KEYS = (
    "inventory",
    "config",
    "word_order_sample",
    "word_order_tests",
)

_PREDICTIVE_KEYS = (
    "config",
    "counts",
    "split_manifest",
    "scores",
    "interpretation",
)

_CONTEXT_KEYS = (
    "config",
    "counts",
    "split_manifest",
    "split_manifest_hash",
    "scores",
    "per_leaf_score_sums",
    "bootstrap",
    "caution",
)


def _key_text(key: Any) -> str:
    return key if isinstance(key, str) else str(key)


def _is_denied_key(key: str) -> bool:
    normalized = key.casefold()
    if normalized in _DENIED_KEYS:
        return True
    if "decoded" in normalized:
        return True
    if "model" in normalized and normalized != "model":
        return True
    if normalized.endswith(("_path", "_url")):
        return True
    if normalized in {"input", "output"}:
        return True
    return False


def _looks_like_absolute_path(value: str) -> bool:
    return bool(
        value.startswith(("/", "\\"))
        or re.match(r"^[A-Za-z]:[\\/]", value)
        or "/home/" in value
        or "\\Users\\" in value
    )


def _safe_symbol_counts(value: Any) -> Any:
    if not isinstance(value, dict):
        return _DROP
    for symbol in value:
        if not isinstance(symbol, str):
            return _DROP
        if len(symbol) != 1 and symbol not in _SAFE_SYMBOLS:
            return _DROP
    return _copy_public(value)


def _copy_public(value: Any, key: str | None = None) -> Any:
    """Copy JSON-like aggregate data while dropping unsafe nested fields."""

    if key is not None:
        normalized = key.casefold()
        if normalized == "symbol_counts":
            return _safe_symbol_counts(value)
        if _is_denied_key(key):
            return _DROP
        if normalized in {"records", "tokens"} and isinstance(value, list):
            return _DROP

    if value is None or isinstance(value, (bool, int, str)):
        if isinstance(value, str) and _looks_like_absolute_path(value):
            return _DROP
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, dict):
        copied: dict[Any, Any] = {}
        for raw_key in sorted(value, key=lambda item: str(item)):
            check_key = _key_text(raw_key)
            child = _copy_public(value[raw_key], check_key)
            if child is not _DROP:
                public_key = raw_key if isinstance(raw_key, (str, int, float, bool)) else check_key
                copied[public_key] = child
        return copied
    if isinstance(value, (list, tuple)):
        copied_items: list[Any] = []
        for item in value:
            child = _copy_public(item)
            if child is not _DROP:
                copied_items.append(child)
        return copied_items
    if isinstance(value, set):
        copied_items = [_copy_public(item) for item in sorted(value, key=str)]
        return [item for item in copied_items if item is not _DROP]
    if isinstance(value, os.PathLike):
        return _DROP
    return _DROP


def _select_mapping(source: Any, keys: tuple[str, ...] | None = None) -> dict[str, Any]:
    if not isinstance(source, dict):
        return {}
    selected: dict[str, Any] = {}
    source_keys = keys if keys is not None else tuple(sorted(source))
    for key in source_keys:
        if key not in source:
            continue
        copied = _copy_public(source[key], key)
        if copied is not _DROP:
            selected[key] = copied
    return selected


def _basename(value: Any) -> Any:
    if value is None:
        return None
    text = str(value).rstrip("/\\")
    return re.split(r"[\\/]", text)[-1] if text else ""


def _copy_provenance(source: Any) -> dict[str, Any]:
    if not isinstance(source, dict):
        return {}
    copied: dict[str, Any] = {}
    for key in _PROVENANCE_KEYS:
        if key not in source:
            continue
        value = source[key]
        if key == "source_path":
            copied[key] = _basename(value)
        elif key == "code_sha256" and isinstance(value, dict):
            hashes: dict[str, Any] = {}
            for raw_path in sorted(value, key=lambda item: str(item)):
                safe_path = str(raw_path)
                if _looks_like_absolute_path(safe_path):
                    safe_path = Path(safe_path).name
                digest = _copy_public(value[raw_path], "sha256")
                if digest is not _DROP:
                    hashes[safe_path] = digest
            copied[key] = hashes
        else:
            child = _copy_public(value, key)
            if child is not _DROP:
                copied[key] = child
    return copied


def export_result(result: dict) -> dict:
    """Return a deterministic public aggregate view of one analysis result.

    The exporter selects configuration, hashes, split identities, and aggregate
    scores. It removes fitted models, raw records, complete vocabularies, and
    path values that could identify the local workspace.
    """

    if not isinstance(result, dict):
        raise TypeError("result must be a dictionary")

    exported: dict[str, Any] = {}
    if "status" in result:
        status = _copy_public(result["status"], "status")
        if status is not _DROP:
            exported["status"] = status
    if "provenance" in result:
        exported["provenance"] = _copy_provenance(result["provenance"])
    if "config" in result:
        exported["config"] = _select_mapping(result["config"])

    structure = result.get("structure")
    if isinstance(structure, dict):
        exported["structure"] = {
            key: (
                _select_mapping(structure[key])
                if key == "inventory"
                else _copy_public(structure[key], key)
            )
            for key in _STRUCTURE_KEYS
            if key in structure
        }
        exported["structure"] = {
            key: value
            for key, value in exported["structure"].items()
            if value is not _DROP
        }

    for section_name, allowed_keys in (
        ("predictive", _PREDICTIVE_KEYS),
        ("context", _CONTEXT_KEYS),
    ):
        section = result.get(section_name)
        if not isinstance(section, dict):
            continue
        selected = _select_mapping(section, allowed_keys)
        exported[section_name] = selected

    return exported


__all__ = ["export_result"]
