from __future__ import annotations

from dataclasses import replace

import pytest

from drawai.v2.refine import (
    CodexElementRefiner,
    RefineConfig,
    RefinementValidationError,
    codex_analysis_to_v2_element_plans,
    validate_refined_elements,
)
from drawai.v2.schema import ElementPlan, ProcessingIntent


def _plan(
    element_id: str,
    source_ids: tuple[str, ...],
    processing_type: str = "crop",
) -> ElementPlan:
    return ElementPlan(
        element_id=element_id,
        source_candidate_ids=source_ids,
        element_type="icon",
        bbox=(1.0, 2.0, 20.0, 30.0),
        geometry={"kind": "bbox", "bbox": [1, 2, 20, 30]},
        z_order=0,
        confidence="high",
        processing_intent=ProcessingIntent(
            object_type="icon",
            processing_type=processing_type,
        ),
        review_status="agent_refined",
        created_by_stage="refine_elements",
        change_reason="Agent kept this element.",
    )


def _legacy_analysis() -> dict[str, object]:
    return {
        "schema": "drawai.codex_element_analysis.v1",
        "elements": [
            {
                "box_id": "B001",
                "source_candidate_ids": ["B001"],
                "refinement_action": "unchanged",
                "category": "crop",
                "confidence": "high",
                "visual_role": "masked icon",
                "reason": "Kept as source crop.",
                "bbox": [1, 2, 21, 32],
                "type": "icon",
                "geometry": {
                    "kind": "mask",
                    "mask_path": "sam3/masks/B001.png",
                    "bbox": [1, 2, 21, 32],
                },
                "geometry_locked": True,
            }
        ],
    }


def _legacy_analysis_with_removal() -> dict[str, object]:
    return {
        "schema": "drawai.codex_element_analysis.v1",
        "elements": [
            {
                "box_id": "B001",
                "source_candidate_ids": ["B001"],
                "refinement_action": "unchanged",
                "category": "crop",
                "confidence": "high",
                "visual_role": "masked icon",
                "reason": "Kept as source crop.",
                "bbox": [1, 2, 21, 32],
                "type": "icon",
            },
            {
                "box_id": "B002",
                "source_candidate_ids": ["B002"],
                "refinement_action": "merged",
                "reason": "Merged into B001 because it is a duplicate mask.",
            },
        ],
    }


def _legacy_analysis_with_added_element() -> dict[str, object]:
    return {
        "schema": "drawai.codex_element_analysis.v1",
        "elements": [
            {
                "box_id": "N001",
                "source_candidate_ids": [],
                "refinement_action": "added",
                "category": "crop",
                "confidence": "medium",
                "visual_role": "new icon",
                "reason": "Added because the parser missed this icon.",
                "bbox": [1, 2, 21, 32],
                "type": "icon",
            }
        ],
    }


def _legacy_analysis_with_added_element_claiming_source() -> dict[str, object]:
    analysis = _legacy_analysis_with_added_element()
    element = analysis["elements"][0]
    assert isinstance(element, dict)
    element["source_candidate_ids"] = ["B001"]
    return analysis


def test_refine_validation_requires_source_coverage() -> None:
    with pytest.raises(RefinementValidationError, match="missing source candidates"):
        validate_refined_elements(
            [_plan("E001", ("sam3:B001",))],
            expected_candidate_ids={"sam3:B001", "ocr:T001"},
            locked_geometry_by_candidate={},
        )


def test_refine_validation_rejects_unexpected_source_candidate_ids() -> None:
    with pytest.raises(RefinementValidationError, match="unexpected source candidates"):
        validate_refined_elements(
            [_plan("E001", ("sam3:B001", "rogue:X001"))],
            expected_candidate_ids={"sam3:B001"},
            locked_geometry_by_candidate={},
        )


def test_refine_validation_rejects_retained_and_removed_same_source() -> None:
    with pytest.raises(RefinementValidationError, match="both retained and removed"):
        validate_refined_elements(
            [
                _plan("E001", ("sam3:B001",)),
                {
                    "action": "merged",
                    "source_candidate_ids": ["sam3:B001"],
                    "reason": "Duplicate covered by the retained element.",
                },
            ],
            expected_candidate_ids={"sam3:B001"},
            locked_geometry_by_candidate={},
        )


def test_refine_validation_rejects_locked_mask_bbox_change() -> None:
    changed = _plan("E001", ("sam3:B001",))
    changed = replace(changed, bbox=(0.0, 0.0, 40.0, 40.0))
    with pytest.raises(RefinementValidationError, match="locked geometry"):
        validate_refined_elements(
            [changed],
            expected_candidate_ids={"sam3:B001"},
            locked_geometry_by_candidate={
                "sam3:B001": {"kind": "mask", "bbox": [1, 2, 21, 32]}
            },
        )


def test_refine_validation_rejects_locked_mask_geometry_kind_change() -> None:
    changed = _plan("E001", ("sam3:B001",))
    changed = replace(changed, geometry={"kind": "bbox", "bbox": [1, 2, 21, 32]})

    with pytest.raises(RefinementValidationError, match="locked geometry"):
        validate_refined_elements(
            [changed],
            expected_candidate_ids={"sam3:B001"},
            locked_geometry_by_candidate={
                "sam3:B001": {
                    "kind": "mask",
                    "mask_path": "sam3/masks/B001.png",
                    "bbox": [1, 2, 21, 32],
                }
            },
        )


def test_refine_can_be_disabled_by_config() -> None:
    config = RefineConfig(enabled=False, provider="codex_element_refiner")
    assert config.enabled is False
    assert config.provider == "codex_element_refiner"


def test_refine_validation_rejects_duplicate_element_ids() -> None:
    with pytest.raises(RefinementValidationError, match="duplicate element_ids"):
        validate_refined_elements(
            [
                _plan("E001", ("sam3:B001",)),
                _plan("E001", ("ocr:T001",), processing_type="svg_self_draw"),
            ],
            expected_candidate_ids={"sam3:B001", "ocr:T001"},
            locked_geometry_by_candidate={},
        )


def test_refine_validation_exposes_invalid_processing_intent() -> None:
    invalid = _plan("E001", ("sam3:B001",), processing_type="vector_magic")
    with pytest.raises(RefinementValidationError, match="unregistered processing_type"):
        validate_refined_elements(
            [invalid],
            expected_candidate_ids={"sam3:B001"},
            locked_geometry_by_candidate={},
        )


def test_refine_validation_rejects_invalid_bbox() -> None:
    invalid = replace(_plan("E001", ("sam3:B001",)), bbox=(1.0, 2.0, 0.0, 30.0))

    with pytest.raises(RefinementValidationError, match="positive area"):
        validate_refined_elements(
            [invalid],
            expected_candidate_ids={"sam3:B001"},
            locked_geometry_by_candidate={},
        )


def test_refine_validation_rejects_non_finite_bbox() -> None:
    invalid = replace(_plan("E001", ("sam3:B001",)), bbox=(1.0, 2.0, float("inf"), 30.0))

    with pytest.raises(RefinementValidationError, match="finite"):
        validate_refined_elements(
            [invalid],
            expected_candidate_ids={"sam3:B001"},
            locked_geometry_by_candidate={},
        )


def test_refine_validation_rejects_malformed_removal_source_ids() -> None:
    with pytest.raises(ValueError, match="source_candidate_ids"):
        validate_refined_elements(
            [
                {
                    "action": "removed",
                    "source_candidate_ids": ["ocr:T001", ""],
                    "reason": "Duplicate OCR box.",
                }
            ],
            expected_candidate_ids={"ocr:T001"},
            locked_geometry_by_candidate={},
        )


def test_refine_validation_accepts_removal_records_with_reasons() -> None:
    retained = validate_refined_elements(
        [
            _plan("E001", ("sam3:B001",)),
            {
                "action": "removed",
                "removed_source_candidate_ids": ["ocr:T001"],
                "reason": "OCR box duplicates the retained icon crop.",
            },
        ],
        expected_candidate_ids={"sam3:B001", "ocr:T001"},
        locked_geometry_by_candidate={},
    )

    assert retained == (_plan("E001", ("sam3:B001",)),)


def test_codex_analysis_converts_legacy_xyxy_to_v2_element_plan() -> None:
    plans = codex_analysis_to_v2_element_plans(_legacy_analysis())

    assert len(plans) == 1
    plan = plans[0]
    assert plan.element_id == "B001"
    assert plan.source_candidate_ids == ("B001",)
    assert plan.bbox == (1.0, 2.0, 20.0, 30.0)
    assert plan.geometry["kind"] == "mask"
    assert plan.processing_intent.processing_type == "crop"
    validate_refined_elements(
        plans,
        expected_candidate_ids={"B001"},
        locked_geometry_by_candidate={
            "B001": {
                "kind": "mask",
                "mask_path": "sam3/masks/B001.png",
                "bbox": [1, 2, 21, 32],
            }
        },
    )


def test_codex_element_refiner_converts_and_validates_analysis() -> None:
    refiner = CodexElementRefiner(RefineConfig())

    plans = refiner.convert_analysis(
        _legacy_analysis(),
        expected_candidate_ids={"B001"},
        locked_geometry_by_candidate={
            "B001": {
                "kind": "mask",
                "mask_path": "sam3/masks/B001.png",
                "bbox": [1, 2, 21, 32],
            }
        },
    )

    assert plans[0].created_by_stage == "refine_elements"


def test_codex_analysis_preserves_added_element_empty_sources() -> None:
    plans = codex_analysis_to_v2_element_plans(_legacy_analysis_with_added_element())

    assert len(plans) == 1
    assert plans[0].element_id == "N001"
    assert plans[0].source_candidate_ids == ()
    validate_refined_elements(
        plans,
        expected_candidate_ids=set(),
        locked_geometry_by_candidate={},
    )


def test_codex_analysis_rejects_added_element_with_source_candidate_ids() -> None:
    with pytest.raises(ValueError, match="added.*source_candidate_ids"):
        codex_analysis_to_v2_element_plans(
            _legacy_analysis_with_added_element_claiming_source()
        )


def test_codex_analysis_rejects_non_string_confidence() -> None:
    analysis = _legacy_analysis()
    element = analysis["elements"][0]
    assert isinstance(element, dict)
    element["confidence"] = 0.5

    with pytest.raises(ValueError, match="confidence"):
        codex_analysis_to_v2_element_plans(analysis)


def test_codex_element_refiner_counts_removal_records_for_coverage() -> None:
    refiner = CodexElementRefiner(RefineConfig())

    plans = refiner.convert_analysis(
        _legacy_analysis_with_removal(),
        expected_candidate_ids={"B001", "B002"},
        locked_geometry_by_candidate={},
    )

    assert [plan.element_id for plan in plans] == ["B001"]
