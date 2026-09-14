"""Resolve single-image and directory predictions against the benchmark index."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path, PurePosixPath
from typing import Any


def resolve_case_id(cases: list[dict[str, Any]], value: str) -> str:
    value = value.strip()
    ids = [case["bench_id"] for case in cases]
    if value in ids:
        return value
    matches = [case_id for case_id in ids if PurePosixPath(case_id).name == value]
    if len(matches) == 1:
        return matches[0]
    if matches:
        raise ValueError(f"ambiguous sample ID {value!r}; use one of: {', '.join(matches)}")
    raise ValueError(f"unknown sample ID {value!r}; see the dataset's manifest.json")


def prediction_entry(case_id: str, svg: Path, method: str, model: str) -> dict[str, str]:
    return {
        "bench_id": case_id,
        "candidate_svg": str(svg.resolve(strict=True)),
        "method": method,
        "model": model,
        "status": "completed",
    }


def folder_predictions(
    cases: list[dict[str, Any]],
    folder: Path,
    *,
    method: str,
    model: str,
    require_all: bool = False,
) -> tuple[list[dict[str, str]], dict[str, Any]]:
    folder = folder.expanduser().resolve(strict=True)
    if not folder.is_dir():
        raise ValueError(f"--svg-dir must be a directory: {folder}")
    names = Counter(PurePosixPath(case["bench_id"]).name for case in cases)
    entries = []
    matched_paths = set()
    missing = []
    for case in cases:
        case_id = case["bench_id"]
        relative = PurePosixPath(case_id)
        if relative.is_absolute() or ".." in relative.parts or "\\" in case_id:
            raise ValueError(f"invalid dataset case ID: {case_id!r}")
        mirrored = folder.joinpath(*relative.parts[:-1], f"{relative.name}.svg")
        flat = folder / f"{relative.name}.svg"
        if flat.is_file() and names[relative.name] > 1:
            raise ValueError(
                f"ambiguous flat filename {flat.name!r}; use the domain/split/ID.svg layout"
            )
        matches = [p for p in dict.fromkeys((mirrored, flat)) if p.is_file()]
        if len(matches) > 1:
            raise ValueError(f"multiple SVGs match {case_id}: {', '.join(str(p) for p in matches)}")
        if not matches:
            missing.append(case_id)
            continue
        entries.append(prediction_entry(case_id, matches[0], method, model))
        matched_paths.add(matches[0])
    ignored = sorted(
        p.relative_to(folder).as_posix()
        for p in folder.rglob("*")
        if p.is_file() and p.suffix.lower() == ".svg" and p not in matched_paths
    )
    if not entries:
        raise ValueError(
            f"no benchmark SVGs found in {folder}; expected <bench_id>.svg or <short-ID>.svg"
        )
    if require_all and missing:
        raise ValueError(f"missing {len(missing)} benchmark SVGs: {', '.join(missing)}")
    return entries, {
        "requested_case_count": len(cases),
        "matched_case_count": len(entries),
        "missing_case_ids": sorted(missing),
        "ignored_svg_paths": ignored,
    }


def default_output_root(source: Path, *, method: str, model: str, case_id: str = "") -> Path:
    identity = json.dumps([str(source.resolve()), method, model, case_id]).encode("utf-8")
    digest = hashlib.sha256(identity).hexdigest()[:10]
    name = PurePosixPath(case_id).name if case_id else source.stem
    return Path("results") / f"{(name or 'evaluation')[:80]}-{digest}"
