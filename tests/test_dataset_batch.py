import hashlib
import json
from pathlib import Path

import pytest
from PIL import Image

from drawai_evaluation.batch import load_completed_candidates
from drawai_evaluation.dataset import (
    dataset_path,
    load_dataset_manifest,
    remove_obsolete_dataset_files,
    resolve_dataset_root,
)
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


def test_dataset_location_can_be_configured_once(dataset: Path, tmp_path: Path, monkeypatch):
    monkeypatch.setenv("DRAWAI_EVALUATION_DATASET", str(dataset))
    assert resolve_dataset_root() == dataset
    explicit = tmp_path / "explicit"
    explicit.mkdir()
    assert resolve_dataset_root(explicit) == explicit
    with pytest.raises(FileNotFoundError):
        resolve_dataset_root(tmp_path / "missing")


def test_default_local_dataset_is_used_without_network(dataset: Path, tmp_path: Path, monkeypatch):
    monkeypatch.delenv("DRAWAI_EVALUATION_DATASET", raising=False)
    monkeypatch.chdir(tmp_path)
    local = tmp_path / "data/DrawAI-Bench-Lite"
    local.parent.mkdir()
    local.symlink_to(dataset, target_is_directory=True)
    assert resolve_dataset_root() == dataset


def test_declared_continuous_ids_reject_gaps(dataset: Path):
    path = dataset / "manifest.json"
    value = json.loads(path.read_text())
    value["id_scheme"] = "sequential_4_digit"
    value["cases"][0]["bench_id"] = "0002"
    path.write_text(json.dumps(value))
    with pytest.raises(ValueError, match="continuous four-digit"):
        load_dataset_manifest(dataset)


def test_download_cleanup_removes_only_unchanged_obsolete_files(tmp_path: Path):
    old = tmp_path / "images/previous/image.png"
    changed = tmp_path / "annotations/previous/image.json"
    old.parent.mkdir(parents=True)
    changed.parent.mkdir(parents=True)
    old.write_bytes(b"original-image")
    changed.write_text("original-annotation")
    previous = {
        "dataset_id": "test-dataset",
        "cases": [
            {
                "image": old.relative_to(tmp_path).as_posix(),
                "annotation": changed.relative_to(tmp_path).as_posix(),
                "image_sha256": hashlib.sha256(old.read_bytes()).hexdigest(),
                "annotation_sha256": hashlib.sha256(changed.read_bytes()).hexdigest(),
            }
        ],
    }
    changed.write_text("local-change")
    current = {
        "dataset_id": "test-dataset",
        "cases": [
            {
                "image": "images/0001.png",
                "annotation": "annotations/0001.json",
            }
        ],
    }
    assert remove_obsolete_dataset_files(tmp_path, previous, current) == 1
    assert not old.exists() and not old.parent.exists()
    assert changed.read_text() == "local-change"


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
