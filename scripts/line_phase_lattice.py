#!/usr/bin/env python3
"""Build and verify exact integer certificates for row lattices."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any


MAX_INTEGER_BITS = 4096
MAX_BUILD_SECONDS = 600


class _LimitExceeded(Exception):
    pass


def _is_integer(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _validate_rows(
    rows: Any, start: float
) -> tuple[list[list[int]], int, int]:
    if not isinstance(rows, list) or not rows:
        raise ValueError("rows must be a non-empty list")
    _check_time(start)
    for row in rows:
        _check_time(start)
        if not isinstance(row, list):
            raise ValueError("each row must be a list")
    columns = len(rows[0])
    if columns == 0:
        raise ValueError("rows must contain at least one column")
    copied_rows = []
    for row_index, row in enumerate(rows):
        _check_time(start)
        if len(row) != columns:
            raise ValueError("all rows must have the same column count")
        copied_row = []
        for column_index, value in enumerate(row):
            _check_time(start)
            if not _is_integer(value):
                raise ValueError(
                    f"entry at row {row_index}, column {column_index} must be an integer"
                )
            copied_row.append(value)
        copied_rows.append(copied_row)
    _check_time(start)
    return copied_rows, len(rows), columns


def _check_time(start: float) -> None:
    if time.monotonic() - start > MAX_BUILD_SECONDS:
        raise _LimitExceeded("calculation exceeded the 600-second limit")


def _check_bits(value: int) -> None:
    if abs(value).bit_length() > MAX_INTEGER_BITS:
        raise _LimitExceeded("an intermediate integer exceeded the 4,096-bit limit")


def _noncertified(
    row_count: int,
    columns: int,
    pivots: list[int],
    reason: str,
) -> dict[str, Any]:
    return {
        "status": "not_certified",
        "original_input_row_count": row_count,
        "columns": columns,
        "support_indices": [],
        "support_rows": [],
        "left_inverse": [],
        "pivots": pivots,
        "reason": reason,
    }


def _add_row(
    matrix: list[list[int]],
    transform: list[dict[int, int]],
    target_index: int,
    source_index: int,
    multiplier: int,
    start: float,
) -> None:
    _check_bits(multiplier)
    target = matrix[target_index]
    source = matrix[source_index]
    for column_index, source_value in enumerate(source):
        _check_time(start)
        product = multiplier * source_value
        _check_bits(product)
        value = target[column_index] + product
        _check_bits(value)
        target[column_index] = value

    target_transform = transform[target_index]
    source_transform = transform[source_index]
    for source_row, source_value in source_transform.items():
        _check_time(start)
        product = multiplier * source_value
        _check_bits(product)
        value = target_transform.get(source_row, 0) + product
        _check_bits(value)
        if value:
            target_transform[source_row] = value
        else:
            target_transform.pop(source_row, None)


def _swap_rows(
    matrix: list[list[int]],
    transform: list[dict[int, int]],
    first: int,
    second: int,
) -> None:
    matrix[first], matrix[second] = matrix[second], matrix[first]
    transform[first], transform[second] = transform[second], transform[first]


def _negate_row(
    matrix: list[list[int]],
    transform: list[dict[int, int]],
    row_index: int,
) -> None:
    matrix[row_index] = [-value for value in matrix[row_index]]
    transform[row_index] = {
        source_row: -value for source_row, value in transform[row_index].items()
    }


def _direct_product_is_identity(
    left_inverse: list[list[int]],
    support_rows: list[list[int]],
    columns: int,
    start: float,
) -> bool:
    if len(left_inverse) != columns:
        return False
    support_count = len(support_rows)
    for row in left_inverse:
        _check_time(start)
        if len(row) != support_count:
            return False
    for row in support_rows:
        _check_time(start)
        if len(row) != columns:
            return False
    for left_row in range(columns):
        for right_column in range(columns):
            value = 0
            for support_index in range(support_count):
                _check_time(start)
                product = (
                    left_inverse[left_row][support_index]
                    * support_rows[support_index][right_column]
                )
                _check_bits(product)
                value += product
                _check_bits(value)
            if value != (1 if left_row == right_column else 0):
                return False
    _check_time(start)
    return True


def build_certificate(rows: list[list[int]]) -> dict[str, Any]:
    """Build an exact left-inverse certificate for an integer row matrix."""
    start = time.monotonic()
    try:
        original_rows, row_count, columns = _validate_rows(rows, start)
    except _LimitExceeded as exc:
        if isinstance(rows, list) and rows and isinstance(rows[0], list) and rows[0]:
            return _noncertified(len(rows), len(rows[0]), [], str(exc))
        raise
    pivots: list[int] = []
    try:
        for row in original_rows:
            for value in row:
                _check_time(start)
                _check_bits(value)
        matrix = []
        for row in original_rows:
            _check_time(start)
            matrix.append(list(row))
        transform = []
        for row_index in range(row_count):
            _check_time(start)
            transform.append({row_index: 1})
        _check_time(start)
    except _LimitExceeded as exc:
        return _noncertified(row_count, columns, pivots, str(exc))

    try:
        for pivot_index in range(columns):
            _check_time(start)
            pivot_row = None
            pivot_abs = None
            for row_index in range(pivot_index, row_count):
                _check_time(start)
                value = matrix[row_index][pivot_index]
                if value == 0:
                    continue
                magnitude = abs(value)
                if pivot_abs is None or magnitude < pivot_abs:
                    pivot_row = row_index
                    pivot_abs = magnitude

            if pivot_row is None:
                _check_time(start)
                return _noncertified(
                    row_count,
                    columns,
                    pivots,
                    f"rank deficient: found {len(pivots)} pivots for {columns} columns",
                )

            if pivot_row != pivot_index:
                _swap_rows(matrix, transform, pivot_index, pivot_row)
            if matrix[pivot_index][pivot_index] < 0:
                _negate_row(matrix, transform, pivot_index)

            for row_index in range(pivot_index + 1, row_count):
                while matrix[row_index][pivot_index] != 0:
                    _check_time(start)
                    pivot = matrix[pivot_index][pivot_index]
                    value = matrix[row_index][pivot_index]
                    quotient, remainder = divmod(value, pivot)
                    _check_bits(quotient)
                    _add_row(
                        matrix,
                        transform,
                        row_index,
                        pivot_index,
                        -quotient,
                        start,
                    )
                    if remainder:
                        _swap_rows(matrix, transform, row_index, pivot_index)

            pivot = matrix[pivot_index][pivot_index]
            if pivot < 0:
                _negate_row(matrix, transform, pivot_index)
                pivot = -pivot
            pivots.append(pivot)

        all_unit = True
        for pivot in pivots:
            _check_time(start)
            if pivot != 1:
                all_unit = False
        if not all_unit:
            _check_time(start)
            return _noncertified(
                row_count,
                columns,
                pivots,
                "full-rank row lattice has a non-unit diagonal pivot",
            )

        for pivot_index in range(columns - 1, -1, -1):
            _check_time(start)
            for row_index in range(pivot_index):
                multiplier = -matrix[row_index][pivot_index]
                if multiplier:
                    _add_row(
                        matrix,
                        transform,
                        row_index,
                        pivot_index,
                        multiplier,
                        start,
                    )

        for row_index in range(columns):
            for column_index in range(columns):
                _check_time(start)
                expected = 1 if row_index == column_index else 0
                if matrix[row_index][column_index] != expected:
                    raise RuntimeError("row reduction did not produce the identity")

        support_set = set()
        for row_transform in transform[:columns]:
            _check_time(start)
            for source_row, coefficient in row_transform.items():
                _check_time(start)
                if coefficient:
                    support_set.add(source_row)
        support_indices = sorted(support_set)
        _check_time(start)
        support_rows = []
        for index in support_indices:
            _check_time(start)
            support_rows.append(original_rows[index])
        left_inverse = []
        for row_transform in transform[:columns]:
            _check_time(start)
            inverse_row = []
            for source_row in support_indices:
                _check_time(start)
                inverse_row.append(row_transform.get(source_row, 0))
            left_inverse.append(inverse_row)
        certificate: dict[str, Any] = {
            "status": "certified",
            "original_input_row_count": row_count,
            "columns": columns,
            "support_indices": support_indices,
            "support_rows": support_rows,
            "left_inverse": left_inverse,
            "pivots": pivots,
        }
        if not _direct_product_is_identity(
            left_inverse, support_rows, columns, start
        ):
            raise RuntimeError("direct multiplication did not produce the identity")
        _check_time(start)
        return certificate
    except _LimitExceeded as exc:
        return _noncertified(row_count, columns, pivots, str(exc))


def _required_integer(value: Any, name: str, minimum: int = 0) -> int:
    if not _is_integer(value) or value < minimum:
        raise ValueError(f"{name} must be an integer greater than or equal to {minimum}")
    return value


def _verify_certificate(value: dict[str, Any], start: float) -> None:
    if not isinstance(value, dict):
        raise ValueError("certificate must be an object")
    if value.get("status") != "certified":
        raise ValueError("certificate status is not certified")

    _check_time(start)
    row_count = _required_integer(
        value.get("original_input_row_count"), "original_input_row_count", 1
    )
    columns = _required_integer(value.get("columns"), "columns", 1)
    support_indices = value.get("support_indices")
    support_rows = value.get("support_rows")
    left_inverse = value.get("left_inverse")

    if not isinstance(support_indices, list):
        raise ValueError("support_indices must be a list")
    if not isinstance(support_rows, list):
        raise ValueError("support_rows must be a list")
    if not isinstance(left_inverse, list):
        raise ValueError("left_inverse must be a list")
    if len(support_indices) != len(support_rows):
        raise ValueError("support_indices and support_rows must have equal lengths")

    previous_index = -1
    for index in support_indices:
        _check_time(start)
        index = _required_integer(index, "support index")
        if index <= previous_index:
            raise ValueError("support_indices must be sorted and unique")
        if index >= row_count:
            raise ValueError("support index is outside the original input")
        previous_index = index

    for row in support_rows:
        _check_time(start)
        if not isinstance(row, list) or len(row) != columns:
            raise ValueError("each support row must have exactly columns entries")
        for entry in row:
            _check_time(start)
            if not _is_integer(entry):
                raise ValueError("support rows must contain integers")
            _check_bits(entry)

    support_count = len(support_indices)
    if len(left_inverse) != columns:
        raise ValueError("left_inverse must have exactly columns rows")
    for row in left_inverse:
        _check_time(start)
        if not isinstance(row, list) or len(row) != support_count:
            raise ValueError("each left_inverse row must match the support size")
        for entry in row:
            _check_time(start)
            if not _is_integer(entry):
                raise ValueError("left_inverse must contain integers")
            _check_bits(entry)

    for left_row in range(columns):
        for right_column in range(columns):
            value_sum = 0
            for support_index in range(support_count):
                _check_time(start)
                product = (
                    left_inverse[left_row][support_index]
                    * support_rows[support_index][right_column]
                )
                _check_bits(product)
                value_sum += product
                _check_bits(value_sum)
            expected = 1 if left_row == right_column else 0
            if value_sum != expected:
                raise ValueError("left_inverse multiplied by support_rows is not identity")
    _check_time(start)


def verify_certificate(value: dict[str, Any]) -> None:
    """Check certificate metadata and direct multiplication without row reduction."""
    start = time.monotonic()
    try:
        _verify_certificate(value, start)
    except _LimitExceeded as exc:
        raise ValueError(str(exc)) from None


def _read_json(path: str) -> Any:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _write_new_json(path: str, value: dict[str, Any]) -> None:
    content = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
    with Path(path).open("x", encoding="utf-8") as handle:
        handle.write(content)


def _make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build or verify an integer certificate for a row lattice."
    )
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("build", help="build a certificate from JSON rows")
    build.add_argument("input", help="JSON file with a rows array")
    build.add_argument("output", help="new certificate file; an existing file is refused")
    verify = commands.add_parser("verify", help="verify a certificate by direct multiplication")
    verify.add_argument("certificate", help="certificate JSON file")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _make_parser().parse_args(argv)
    try:
        if args.command == "build":
            payload = _read_json(args.input)
            if not isinstance(payload, dict) or "rows" not in payload:
                raise ValueError("input must be an object with a rows field")
            certificate = build_certificate(payload["rows"])
            _write_new_json(args.output, certificate)
            print(f"built: {certificate['status']}")
            return 0

        certificate = _read_json(args.certificate)
        verify_certificate(certificate)
        print("verified")
        return 0
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
