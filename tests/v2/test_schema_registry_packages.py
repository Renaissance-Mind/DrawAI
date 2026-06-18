from __future__ import annotations

import json
from pathlib import Path
from typing import get_args

import pytest

import drawai.v2.schema as v2_schema
from drawai.v2.packages import (
    classify_run_root,
    element_dir,
    read_run_package,
    write_asset_package,
    write_element_plan,
    write_run_package,
)
from drawai.v2.registry import DrawAiRegistry, default_registry
from drawai.v2.schema import (
    AssetPackage,
    AssetStatus,
    ElementCandidate,
    ElementPlan,
    ProcessingIntent,
    ReviewStatus,
    RunPackage,
    validate_element_candidate,
    validate_element_plan,
)


def _element_plan(
    *,
    element_id: str = "E001",
    source_candidate_ids: tuple[str, ...] = ("ocr:T001",),
    review_status: str = "deterministic",
    confidence: str = "high",
    geometry: dict[str, object] | None = None,
    processing_parameters: dict[str, object] | None = None,
) -> ElementPlan:
    return ElementPlan(
        element_id=element_id,
        source_candidate_ids=source_candidate_ids,
        element_type="text",
        bbox=(4.0, 5.0, 30.0, 18.0),
        geometry=geometry or {"kind": "bbox", "bbox": [4, 5, 30, 18]},
        z_order=1,
        confidence=confidence,
        processing_intent=ProcessingIntent(
            object_type="text",
            processing_type="svg_self_draw",
            parameters=processing_parameters or {},
        ),
        review_status=review_status,
        created_by_stage="fuse_elements",
        change_reason="Text from OCR.",
    )


def test_schema_literal_contracts_and_asset_package_default() -> None:
    assert get_args(AssetStatus) == (
        "pending",
        "running",
        "ok",
        "failed",
        "unsupported",
    )
    assert get_args(ReviewStatus) == ("deterministic", "agent_refined", "user_edited")

    package = AssetPackage.empty(
        asset_id="A001",
        element_id="E001",
        processor_type="svg_self_draw",
    )

    assert package.status == "pending"
    assert package.to_dict()["status"] == "pending"


def test_element_package_paths_reject_unsafe_element_ids(tmp_path: Path) -> None:
    root = tmp_path / "run"
    unsafe_element_ids = (
        "../escape",
        "nested/E001",
        str(tmp_path / "absolute"),
        "",
    )

    for element_id in unsafe_element_ids:
        with pytest.raises(ValueError, match="element_id"):
            element_dir(root, element_id)

        with pytest.raises(ValueError, match="element_id"):
            write_element_plan(root, _element_plan(element_id=element_id))

        package = AssetPackage.empty(
            asset_id="A001",
            element_id=element_id,
            processor_type="svg_self_draw",
        )
        with pytest.raises(ValueError, match="element_id"):
            write_asset_package(root, package)

    assert not (root / "escape").exists()
    assert not (root / "elements" / "nested").exists()


def test_asset_package_validation_rejects_invalid_status_and_missing_ids(tmp_path: Path) -> None:
    validate_asset_package = getattr(v2_schema, "validate_asset_package", None)
    assert callable(validate_asset_package)

    invalid_packages = (
        AssetPackage(
            asset_id="A001",
            element_id="E001",
            processor_type="svg_self_draw",
            status="bogus",
        ),
        AssetPackage(
            asset_id="",
            element_id="E001",
            processor_type="svg_self_draw",
        ),
        AssetPackage(
            asset_id="A001",
            element_id="",
            processor_type="svg_self_draw",
        ),
        AssetPackage(
            asset_id="A001",
            element_id="E001",
            processor_type="",
        ),
    )

    for package in invalid_packages:
        with pytest.raises(ValueError):
            validate_asset_package(package)
        with pytest.raises(ValueError):
            write_asset_package(tmp_path, package)


def test_element_plan_validation_rejects_invalid_review_status() -> None:
    plan = _element_plan(review_status="needs_review")

    with pytest.raises(ValueError, match="review_status"):
        validate_element_plan(plan, registry=default_registry())


def test_element_plan_validation_rejects_invalid_source_candidate_ids(tmp_path: Path) -> None:
    invalid_plans = (
        _element_plan(source_candidate_ids="ocr:T001"),
        _element_plan(source_candidate_ids=("ocr:T001", "")),
    )

    for plan in invalid_plans:
        with pytest.raises(ValueError, match="source_candidate_ids"):
            validate_element_plan(plan, registry=default_registry())
        with pytest.raises(ValueError, match="source_candidate_ids"):
            write_element_plan(tmp_path, plan)


def test_to_dict_recursively_normalizes_nested_json_values() -> None:
    plan = _element_plan(
        geometry={"kind": "polyline", "points": ((1, 2), (3, 4))},
        processing_parameters={"snapshots": ({"bbox": (1, 2, 3, 4)},)},
    )

    payload = plan.to_dict()

    assert payload["geometry"]["points"] == [[1, 2], [3, 4]]
    assert payload["processing_intent"]["parameters"]["snapshots"] == [
        {"bbox": [1, 2, 3, 4]}
    ]


def test_element_candidate_and_plan_validate_core_fields(tmp_path: Path) -> None:
    candidate = ElementCandidate(
        candidate_id="sam3:B001",
        source_parser="sam3_structure_parser",
        source_parser_version="v1",
        element_type="icon",
        bbox=(1.0, 2.0, 20.0, 30.0),
        geometry={"kind": "bbox", "bbox": [1, 2, 20, 30]},
        confidence=0.82,
        z_hint=0,
        text="",
        evidence_files=[],
        provenance={"prompt": "icon"},
        raw_ref={"path": "reports/parser_outputs/sam3.json", "index": 0},
    )
    validate_element_candidate(candidate, registry=default_registry())

    plan = ElementPlan(
        element_id="E001",
        source_candidate_ids=("sam3:B001",),
        element_type="icon",
        bbox=(1.0, 2.0, 20.0, 30.0),
        geometry={"kind": "bbox", "bbox": [1, 2, 20, 30]},
        z_order=0,
        confidence="high",
        processing_intent=ProcessingIntent(object_type="icon", processing_type="crop_nobg"),
        review_status="agent_refined",
        created_by_stage="refine_elements",
        change_reason="Kept source candidate.",
    )
    validate_element_plan(plan, registry=default_registry())


def test_registry_rejects_unknown_types_until_registered() -> None:
    registry = DrawAiRegistry.core()
    plan = ElementPlan(
        element_id="E001",
        source_candidate_ids=("sam3:B001",),
        element_type="molecule",
        bbox=(0.0, 0.0, 10.0, 10.0),
        geometry={"kind": "bbox", "bbox": [0, 0, 10, 10]},
        z_order=0,
        confidence="medium",
        processing_intent=ProcessingIntent(object_type="molecule", processing_type="crop"),
        review_status="deterministic",
        created_by_stage="fuse_elements",
        change_reason="Extension type example.",
    )
    with pytest.raises(ValueError, match="unregistered element_type"):
        validate_element_plan(plan, registry=registry)

    registry.register_element_type("molecule", schema_version="drawai.extension.element.molecule.v1", capabilities=("crop",))
    validate_element_plan(plan, registry=registry)


def test_run_and_asset_packages_roundtrip(tmp_path: Path) -> None:
    root = tmp_path / "run"
    run = RunPackage.new(run_id="run_001", root=root, source_image="inputs/figure.png", canvas={"width": 100, "height": 80})
    run = write_run_package(root, run)
    loaded = read_run_package(root)
    assert loaded["schema"] == "drawai.run_package.v1"
    assert loaded["run_id"] == "run_001"

    plan = ElementPlan(
        element_id="E001",
        source_candidate_ids=("ocr:T001",),
        element_type="text",
        bbox=(4.0, 5.0, 30.0, 18.0),
        geometry={"kind": "bbox", "bbox": [4, 5, 30, 18]},
        z_order=1,
        confidence="high",
        processing_intent=ProcessingIntent(object_type="text", processing_type="svg_self_draw"),
        review_status="deterministic",
        created_by_stage="fuse_elements",
        change_reason="Text from OCR.",
    )
    write_element_plan(root, plan)
    assert (element_dir(root, "E001") / "element.json").is_file()

    package = AssetPackage.empty(asset_id="A001", element_id="E001", processor_type="svg_self_draw")
    write_asset_package(root, package)
    assert json.loads((element_dir(root, "E001") / "asset_package.json").read_text(encoding="utf-8"))["asset_id"] == "A001"
    assert classify_run_root(root).mode == "v2"


def test_read_run_package_rejects_schema_only_package(tmp_path: Path) -> None:
    root = tmp_path / "run"
    root.mkdir()
    (root / "drawai_package.json").write_text(
        json.dumps({"schema": "drawai.run_package.v1"}) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="run_id"):
        read_run_package(root)


def test_classify_run_root_does_not_accept_schema_only_package(tmp_path: Path) -> None:
    root = tmp_path / "run"
    root.mkdir()
    (root / "drawai_package.json").write_text(
        json.dumps({"schema": "drawai.run_package.v1"}) + "\n",
        encoding="utf-8",
    )

    assert classify_run_root(root).mode == "unknown"


def test_legacy_run_root_is_readonly_when_no_v2_package(tmp_path: Path) -> None:
    root = tmp_path / "legacy"
    (root / "svg").mkdir(parents=True)
    (root / "svg" / "semantic.svg").write_text("<svg />\n", encoding="utf-8")
    (root / "inputs").mkdir()
    (root / "inputs" / "figure.png").write_bytes(b"png")

    classification = classify_run_root(root)

    assert classification.mode == "legacy_readonly"
    assert classification.can_fork_from_source is True
