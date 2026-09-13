from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter
from pathlib import Path, PurePosixPath
from typing import Any

from PIL import Image

DEFAULT_REPO = "caopu/DrawAI-Bench-Lite"
DEFAULT_REVISION = "b53667b7cf0f1acd8a52aed33c22e952ab6eddd4"
SCHEMA = "drawai.evaluation_dataset.v1"
KINDS = {"text", "image", "shape", "connector", "formula", "table"}


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


def main() -> int:
    parser = argparse.ArgumentParser(description="Download or verify the evaluation dataset.")
    parser.add_argument("action", choices=("download", "verify"))
    parser.add_argument("--local-dir", type=Path, default=Path("data/DrawAI-Bench-Lite"))
    parser.add_argument("--repo-id", default=DEFAULT_REPO)
    parser.add_argument("--revision", default=DEFAULT_REVISION)
    args = parser.parse_args()
    if args.action == "download":
        from huggingface_hub import snapshot_download

        snapshot_download(
            repo_id=args.repo_id,
            repo_type="dataset",
            revision=args.revision,
            local_dir=args.local_dir,
        )
    manifest = load_dataset_manifest(args.local_dir.resolve(strict=True))
    print(
        json.dumps(
            {
                "dataset_id": manifest["dataset_id"],
                "cases": manifest["case_count"],
                "elements": sum(c["element_count"] for c in manifest["cases"]),
                "verified": True,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
