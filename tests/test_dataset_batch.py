import hashlib
import json
from pathlib import Path

import pytest
from PIL import Image

from drawai_evaluation.batch import load_completed_candidates
from drawai_evaluation.dataset import dataset_path, load_dataset_manifest
from drawai_evaluation.renderer import referenced_asset_hashes


@pytest.fixture
def dataset(tmp_path: Path) -> Path:
    root = tmp_path / "dataset"
    root.mkdir()
    image = root / "image.png"
    annotation = root / "annotation.json"
    Image.new("RGB", (32, 16), "white").save(image)
    spec = {
        "schema": "drawai.page_spec.v1",
        "page_id": "test/case/one",
        "canvas": {"width_px": 64, "height_px": 32},
        "elements": [],
    }
    annotation.write_text(json.dumps(spec))
    case = {
        "bench_id": spec["page_id"],
        "image": image.name,
        "annotation": annotation.name,
        "width": 32,
        "height": 16,
        "canvas_width": 64,
        "canvas_height": 32,
        "image_sha256": hashlib.sha256(image.read_bytes()).hexdigest(),
        "annotation_sha256": hashlib.sha256(annotation.read_bytes()).hexdigest(),
        "element_count": 0,
        "kind_counts": {},
    }
    (root / "manifest.json").write_text(
        json.dumps({"schema": "drawai.evaluation_dataset.v1", "case_count": 1, "cases": [case]})
    )
    return root


def test_dataset_preserves_distinct_image_and_coordinate_canvas(dataset: Path):
    assert load_dataset_manifest(dataset)["cases"][0]["canvas_width"] == 64


def test_dataset_rejects_tampered_annotation(dataset: Path):
    (dataset / "annotation.json").write_text("{}")
    with pytest.raises(ValueError, match="checksum mismatch"):
        load_dataset_manifest(dataset)


def test_dataset_rejects_path_escape(dataset: Path):
    with pytest.raises(ValueError, match="relative"):
        dataset_path(dataset, "../outside.json")


def test_batch_skips_unfinished_and_preserves_completed_identity(dataset: Path, tmp_path: Path):
    svg = tmp_path / "prediction.svg"
    svg.write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 32"/>')
    row = {
        "bench_id": "test/case/one",
        "method": "m",
        "model": "v",
        "candidate_svg": svg.name,
        "status": "completed",
    }
    manifest = tmp_path / "candidates.jsonl"
    manifest.write_text(json.dumps(row) + "\n" + json.dumps({"status": "running"}) + "\n")
    candidates, counts = load_completed_candidates(dataset, manifest, tmp_path / "results")
    assert len(candidates) == 1
    assert candidates[0].target_id == "m/v/test/case/one"
    assert candidates[0].candidate_svg == svg
    assert counts["skipped_unfinished_count"] == 1
    manifest.write_text(json.dumps([row, row]))
    manifest.rename(tmp_path / "candidates.json")
    with pytest.raises(ValueError, match="duplicate"):
        load_completed_candidates(dataset, tmp_path / "candidates.json", tmp_path / "results")


def test_asset_changes_invalidate_fingerprint(tmp_path: Path):
    svg = tmp_path / "candidate.svg"
    asset = tmp_path / "asset.png"
    svg.write_text('<svg xmlns="http://www.w3.org/2000/svg"><image href="asset.png"/></svg>')
    assert referenced_asset_hashes(svg) == {"asset.png": "missing"}
    Image.new("RGB", (4, 4), "red").save(asset)
    before = referenced_asset_hashes(svg)
    Image.new("RGB", (4, 4), "blue").save(asset)
    assert referenced_asset_hashes(svg) != before
