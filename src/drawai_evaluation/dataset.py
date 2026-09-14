from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from collections import Counter
from pathlib import Path, PurePosixPath
from typing import Any

from PIL import Image

DEFAULT_REPO = "caopu/DrawAI-Bench-Lite"
DEFAULT_REVISION = "8d99285ca440a8e96096103d96bcac704a6a9cc0"
DEFAULT_DATASET_VERSION = "2.0.0"
SCHEMA = "drawai.evaluation_dataset.v1"
KINDS = {"text", "image", "shape", "connector", "formula", "table"}
DEFAULT_LOCAL_DIR = Path("data/DrawAI-Bench-Lite")


def resolve_dataset_root(explicit: Path | None = None) -> Path:
    """Use a configured dataset, a local download, or the pinned Hub snapshot."""
    configured = explicit or os.environ.get("DRAWAI_EVALUATION_DATASET")
    if configured:
        return Path(configured).expanduser().resolve(strict=True)
    if DEFAULT_LOCAL_DIR.exists():
        local_manifest = DEFAULT_LOCAL_DIR / "manifest.json"
        local = (
            json.loads(local_manifest.read_text(encoding="utf-8"))
            if local_manifest.is_file()
            else {}
        )
        if (
            local.get("dataset_id") != DEFAULT_REPO
            or local.get("version") == DEFAULT_DATASET_VERSION
        ):
            return DEFAULT_LOCAL_DIR.resolve(strict=True)
        print(
            f"Using published dataset version {DEFAULT_DATASET_VERSION}; update the local copy with drawai-dataset download.",
            flush=True,
        )

    from huggingface_hub import snapshot_download
    from huggingface_hub.errors import LocalEntryNotFoundError

    try:
        cached = Path(
            snapshot_download(
                DEFAULT_REPO, repo_type="dataset", revision=DEFAULT_REVISION, local_files_only=True
            )
        )
    except LocalEntryNotFoundError:
        cached = None
    if cached and (cached / "manifest.json").is_file():
        manifest = json.loads((cached / "manifest.json").read_text(encoding="utf-8"))
        if all(
            (cached / row[key]).is_file()
            for row in manifest["cases"]
            for key in ("image", "annotation")
        ):
            return cached
    print(
        f"Downloading private dataset {DEFAULT_REPO}@{DEFAULT_REVISION}; authenticate with hf auth login if needed.",
        flush=True,
    )
    return Path(
        snapshot_download(
            DEFAULT_REPO,
            repo_type="dataset",
            revision=DEFAULT_REVISION,
            allow_patterns=[
                "manifest.json",
                "images/**",
                "annotations/**",
                "README.md",
                "SHA256SUMS",
            ],
        )
    )


def sha256_file(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def dataset_path(root: Path, relative: str) -> Path:
    value = PurePosixPath(relative)
    if value.is_absolute() or ".." in value.parts or "\\" in relative:
        raise ValueError(f"dataset paths must be relative: {relative}")
    path = root.joinpath(*value.parts).resolve(strict=True)
    if not path.is_relative_to(root.resolve()) or not path.is_file():
        raise ValueError(f"invalid dataset file: {relative}")
    return path


def load_dataset_manifest(root: Path, *, verify: bool = True) -> dict[str, Any]:
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    cases = manifest["cases"]
    if manifest.get("schema") != SCHEMA:
        raise ValueError("unsupported evaluation dataset schema")
    if len(cases) != manifest.get("case_count") or len({c["bench_id"] for c in cases}) != len(
        cases
    ):
        raise ValueError("dataset case count or identities are inconsistent")
    if manifest.get("id_scheme") == "sequential_4_digit":
        if [case["bench_id"] for case in cases] != [f"{i:04d}" for i in range(1, len(cases) + 1)]:
            raise ValueError(
                "dataset sample IDs must be continuous four-digit numbers starting at 0001"
            )
    for case in cases:
        image = dataset_path(root, case["image"])
        annotation = dataset_path(root, case["annotation"])
        if verify:
            if sha256_file(image) != case["image_sha256"]:
                raise ValueError(f"image checksum mismatch: {case['bench_id']}")
            if sha256_file(annotation) != case["annotation_sha256"]:
                raise ValueError(f"annotation checksum mismatch: {case['bench_id']}")
            with Image.open(image) as im:
                if im.size != (case["width"], case["height"]):
                    raise ValueError(f"image dimensions differ: {case['bench_id']}")
        spec = json.loads(annotation.read_text(encoding="utf-8"))
        if spec.get("schema") != "drawai.page_spec.v1" or spec.get("page_id") != case["bench_id"]:
            raise ValueError(f"invalid page annotation: {case['bench_id']}")
        elements = spec["elements"]
        ids = [e["id"] for e in elements]
        if len(ids) != len(set(ids)) or len(elements) != case["element_count"]:
            raise ValueError(f"invalid annotation element identities: {case['bench_id']}")
        if Counter(e["kind"] for e in elements) != Counter(case["kind_counts"]):
            raise ValueError(f"element kind counts differ: {case['bench_id']}")
        for element in elements:
            box = element["box_px"]
            if (
                element["kind"] not in KINDS
                or len(box) != 4
                or not all(math.isfinite(v) for v in box)
            ):
                raise ValueError(f"invalid element geometry: {case['bench_id']}/{element['id']}")
        canvas = spec["canvas"]
        if (
            canvas["width_px"] != case["canvas_width"]
            or canvas["height_px"] != case["canvas_height"]
        ):
            raise ValueError(f"annotation canvas differs: {case['bench_id']}")
    return manifest


def remove_obsolete_dataset_files(
    root: Path, previous: dict[str, Any], current: dict[str, Any]
) -> int:
    """Remove unchanged files managed by the replaced dataset manifest."""
    if not previous.get("dataset_id") or previous.get("dataset_id") != current.get("dataset_id"):
        return 0
    expected = {row[key] for row in current["cases"] for key in ("image", "annotation")}
    removed = 0
    parents = set()
    for row in previous["cases"]:
        for key in ("image", "annotation"):
            relative = row[key]
            if relative in expected:
                continue
            path = root / relative
            if not path.is_file():
                continue
            resolved = dataset_path(root, relative)
            if sha256_file(resolved) != row[f"{key}_sha256"]:
                continue
            path.unlink()
            removed += 1
            parents.update(
                parent for parent in path.parents if parent != root and parent.is_relative_to(root)
            )
    for parent in sorted(parents, key=lambda p: len(p.parts), reverse=True):
        if parent.is_dir() and not parent.is_symlink() and not any(parent.iterdir()):
            parent.rmdir()
    return removed


def main() -> int:
    parser = argparse.ArgumentParser(description="Download or verify the evaluation dataset.")
    parser.add_argument("action", choices=("download", "verify"))
    parser.add_argument("--local-dir", type=Path, default=DEFAULT_LOCAL_DIR)
    parser.add_argument("--repo-id", default=DEFAULT_REPO)
    parser.add_argument("--revision", default=DEFAULT_REVISION)
    args = parser.parse_args()
    previous_path = args.local_dir / "manifest.json"
    previous = (
        json.loads(previous_path.read_text(encoding="utf-8")) if previous_path.is_file() else {}
    )
    if args.action == "download":
        from huggingface_hub import snapshot_download

        snapshot_download(
            repo_id=args.repo_id,
            repo_type="dataset",
            revision=args.revision,
            local_dir=args.local_dir,
        )
    manifest = load_dataset_manifest(args.local_dir.resolve(strict=True))
    removed = (
        remove_obsolete_dataset_files(args.local_dir.resolve(strict=True), previous, manifest)
        if args.action == "download"
        else 0
    )
    print(
        json.dumps(
            {
                "dataset_id": manifest["dataset_id"],
                "cases": manifest["case_count"],
                "elements": sum(c["element_count"] for c in manifest["cases"]),
                "verified": True,
                "removed_obsolete_files": removed,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
