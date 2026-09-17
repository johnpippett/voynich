#!/usr/bin/env python3
"""Export aggregate metrics from one or more saved analysis runs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import tempfile
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from voynich.export import export_result


def _load_analysis(run_directory: Path) -> dict[str, Any]:
    if not run_directory.is_dir():
        raise FileNotFoundError(f"run directory does not exist: {run_directory}")
    analysis_path = run_directory / "analysis.json"
    if not analysis_path.is_file():
        raise FileNotFoundError(f"analysis.json does not exist: {analysis_path}")
    try:
        value = json.loads(analysis_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON: {analysis_path}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"analysis result is not an object: {analysis_path}")
    return value


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        prefix=f".{path.name}.",
        dir=path.parent,
        delete=False,
    ) as temporary:
        temporary_path = Path(temporary.name)
        json.dump(value, temporary, indent=2, ensure_ascii=False, sort_keys=True, allow_nan=False)
        temporary.write("\n")
    temporary_path.replace(path)


def export_runs(
    run_directories: list[Path], reports_directory: Path, replace: bool = False
) -> list[Path]:
    """Export each run to ``reports_directory/<run-name>.json``."""

    loaded: list[tuple[Path, Path, dict[str, Any]]] = []
    output_paths: set[Path] = set()
    for raw_directory in run_directories:
        run_directory = raw_directory.resolve()
        output_path = reports_directory.resolve() / f"{run_directory.name}.json"
        if output_path in output_paths:
            raise FileExistsError(f"duplicate output path: {output_path}")
        output_paths.add(output_path)
        if output_path.exists() and not replace:
            raise FileExistsError(
                f"report already exists: {output_path}; use --replace or choose another reports directory"
            )
        loaded.append((run_directory, output_path, export_result(_load_analysis(run_directory))))

    for _run_directory, output_path, exported in loaded:
        _write_json(output_path, exported)
    return [output_path for _run_directory, output_path, _exported in loaded]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "run_directories",
        type=Path,
        nargs="+",
        help="saved run directories that contain analysis.json",
    )
    parser.add_argument(
        "--reports-dir",
        type=Path,
        default=PROJECT_ROOT / "reports",
        help="output directory (default: reports)",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="replace existing aggregate report files",
    )
    args = parser.parse_args(argv)
    try:
        paths = export_runs(args.run_directories, args.reports_dir, replace=args.replace)
    except (FileExistsError, FileNotFoundError, OSError, ValueError, TypeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    for path in paths:
        print(f"exported: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
