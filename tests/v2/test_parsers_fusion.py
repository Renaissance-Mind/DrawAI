from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from drawai.asset_geometry import geometry_bbox, normalize_asset_geometry
from drawai.v2.fusion import FusionConfig, fuse_candidates
from drawai.v2.parsers import ocr_payload_to_candidates, sam3_payload_to_candidates
from drawai.v2.schema import ElementCandidate


def _candidate(
    *,
    candidate_id: str,
    element_type: str = "icon",
    bbox: tuple[float, float, float, float] = (10.0, 10.0, 30.0, 30.0),
    confidence: float,
    parser_priority: int,
    source_parser: str = "sam3_structure_parser",
) -> ElementCandidate:
    return ElementCandidate(
        candidate_id=candidate_id,
        source_parser=source_parser,
        source_parser_version="v1",
        element_type=element_type,
        bbox=bbox,
        geometry={
            "kind": "bbox",
            "bbox": list(bbox),
            "coordinate_system": "figure_image_pixels",
        },
        confidence=confidence,
        z_hint=None,
        text="",
        evidence_files=(),
        provenance={"parser_priority": parser_priority},
        raw_ref={"test": candidate_id},
    )


def _iou(
    left_bbox: tuple[float, float, float, float],
    right_bbox: tuple[float, float, float, float],
) -> float:
    left_x, left_y, left_width, left_height = left_bbox
    right_x, right_y, right_width, right_height = right_bbox
    intersection_left = max(left_x, right_x)
    intersection_top = max(left_y, right_y)
    intersection_right = min(left_x + left_width, right_x + right_width)
    intersection_bottom = min(left_y + left_height, right_y + right_height)
    intersection_width = max(0.0, intersection_right - intersection_left)
    intersection_height = max(0.0, intersection_bottom - intersection_top)
    intersection_area = intersection_width * intersection_height
    left_area = left_width * left_height
    right_area = right_width * right_height
    return intersection_area / (left_area + right_area - intersection_area)


def test_sam3_and_ocr_payloads_convert_to_element_candidates(tmp_path: Path) -> None:
    image = tmp_path / "figure.png"
    Image.new("RGB", (100, 80), "white").save(image)
    sam_payload = {
        "raw_regions": [
            {
                "bbox": [10, 10, 40, 35],
                "score": 0.91,
                "label": "icon",
                "source_prompt": "icon",
            }
        ]
    }
    ocr_payload = {
        "ocr_text_boxes": [
            {
                "id": "T001",
                "bbox": [12, 42, 60, 55],
                "text": "Hello",
                "confidence": 0.88,
            }
        ]
    }

    sam_candidates = sam3_payload_to_candidates(sam_payload, source_image=image)
    ocr_candidates = ocr_payload_to_candidates(ocr_payload, source_image=image)

    assert sam_candidates[0].candidate_id == "sam3:B001"
    assert sam_candidates[0].element_type == "icon"
    assert sam_candidates[0].bbox == (10.0, 10.0, 30.0, 25.0)
    assert sam_candidates[0].provenance["parser_priority"] == 10
    assert ocr_candidates[0].candidate_id == "ocr:T001"
    assert ocr_candidates[0].element_type == "text"
    assert ocr_candidates[0].text == "Hello"
    assert ocr_candidates[0].bbox == (12.0, 42.0, 48.0, 13.0)
    assert ocr_candidates[0].provenance["parser_priority"] == 5


def test_non_default_parser_ids_are_stable_and_distinct() -> None:
    sam_default = sam3_payload_to_candidates(
        {"raw_regions": [{"bbox": [0, 0, 20, 20], "score": 0.8, "label": "icon"}]},
        source_image=Path("inputs/figure.png"),
    )[0]
    sam_custom = sam3_payload_to_candidates(
        {"raw_regions": [{"bbox": [0, 0, 20, 20], "score": 0.8, "label": "icon"}]},
        source_image=Path("inputs/figure.png"),
        parser_id="vision_layout_parser",
    )[0]
    ocr_default = ocr_payload_to_candidates(
        {
            "ocr_text_boxes": [
                {"id": "T001", "bbox": [0, 0, 20, 20], "text": "A", "confidence": 0.8}
            ]
        },
        source_image=Path("inputs/figure.png"),
    )[0]
    ocr_custom = ocr_payload_to_candidates(
        {
            "ocr_text_boxes": [
                {"id": "T001", "bbox": [0, 0, 20, 20], "text": "A", "confidence": 0.8}
            ]
        },
        source_image=Path("inputs/figure.png"),
        parser_id="local_paddleocr",
    )[0]

    assert sam_default.candidate_id == "sam3:B001"
    assert sam_custom.candidate_id == "vision_layout_parser:B001"
    assert ocr_default.candidate_id == "ocr:T001"
    assert ocr_custom.candidate_id == "local_paddleocr:T001"
    assert len(
        {
            sam_default.candidate_id,
            sam_custom.candidate_id,
            ocr_default.candidate_id,
            ocr_custom.candidate_id,
        }
    ) == 4


def test_sam3_parser_preserves_mask_geometry() -> None:
    candidates = sam3_payload_to_candidates(
        {
            "raw_regions": [
                {
                    "bbox": [2, 3, 22, 33],
                    "score": 0.76,
                    "label": "symbol",
                    "geometry": {
                        "kind": "mask",
                        "bbox": [2, 3, 22, 33],
                        "mask_path": "masks/B001.png",
                    },
                }
            ]
        },
        source_image=Path("inputs/figure.png"),
    )

    assert candidates[0].geometry["kind"] == "mask"
    assert candidates[0].bbox == (2.0, 3.0, 20.0, 30.0)
    assert candidates[0].geometry["bbox"] == [2.0, 3.0, 22.0, 33.0]
    assert geometry_bbox(candidates[0].geometry) == [2.0, 3.0, 22.0, 33.0]
    assert normalize_asset_geometry(candidates[0].geometry)["bbox"] == [
        2.0,
        3.0,
        22.0,
        33.0,
    ]
    assert candidates[0].geometry["mask_path"] == "masks/B001.png"
    assert candidates[0].evidence_files == ("masks/B001.png",)


def test_sam3_parser_accepts_geometry_only_polygon_region(tmp_path: Path) -> None:
    image = tmp_path / "figure.png"
    Image.new("RGB", (100, 80), "white").save(image)

    candidates = sam3_payload_to_candidates(
        {
            "raw_regions": [
                {
                    "score": 0.82,
                    "label": "diagram",
                    "geometry": {
                        "kind": "polygon",
                        "points": [[10, 5], [50, 10], [45, 40], [12, 38]],
                    },
                }
            ]
        },
        source_image=image,
    )

    assert candidates[0].bbox == (10.0, 5.0, 40.0, 35.0)
    assert candidates[0].geometry["kind"] == "polygon"
    assert candidates[0].geometry["points"] == [
        [10.0, 5.0],
        [50.0, 10.0],
        [45.0, 40.0],
        [12.0, 38.0],
    ]
    assert candidates[0].geometry["bbox"] == [10.0, 5.0, 50.0, 40.0]
    assert geometry_bbox(candidates[0].geometry) == [10.0, 5.0, 50.0, 40.0]
    assert normalize_asset_geometry(candidates[0].geometry)["bbox"] == [
        10.0,
        5.0,
        50.0,
        40.0,
    ]


def test_parser_rejects_malformed_payload_shape() -> None:
    with pytest.raises(ValueError, match="raw_regions"):
        sam3_payload_to_candidates(
            {"raw_regions": {"bbox": [0, 0, 10, 10]}},
            source_image=Path("inputs/figure.png"),
        )

    with pytest.raises(ValueError, match="bbox"):
        ocr_payload_to_candidates(
            {"ocr_text_boxes": [{"id": "T001", "bbox": [0, 0, 0, 4], "text": "bad"}]},
            source_image=Path("inputs/figure.png"),
        )


def test_fusion_keeps_text_and_visual_candidates_separate() -> None:
    sam_candidates = sam3_payload_to_candidates(
        {
            "raw_regions": [
                {"bbox": [0, 0, 100, 100], "score": 0.8, "label": "picture"}
            ]
        },
        source_image=Path("inputs/figure.png"),
    )
    ocr_candidates = ocr_payload_to_candidates(
        {
            "ocr_text_boxes": [
                {
                    "id": "T001",
                    "bbox": [1, 1, 99, 99],
                    "text": "Title",
                    "confidence": 0.9,
                }
            ]
        },
        source_image=Path("inputs/figure.png"),
    )

    result = fuse_candidates([*sam_candidates, *ocr_candidates], config=FusionConfig.default())

    assert _iou(sam_candidates[0].bbox, ocr_candidates[0].bbox) >= (
        FusionConfig.default().duplicate_iou_threshold
    )
    assert [plan.element_type for plan in result.elements] == ["picture", "text"]
    assert [item["action"] for item in result.trace["decisions"]] == ["kept", "kept"]


def test_fusion_suppresses_lower_priority_duplicate_same_type() -> None:
    first = sam3_payload_to_candidates(
        {"raw_regions": [{"bbox": [10, 10, 40, 40], "score": 0.99, "label": "icon"}]},
        source_image=Path("inputs/figure.png"),
    )[0]
    second = sam3_payload_to_candidates(
        {"raw_regions": [{"bbox": [11, 11, 41, 41], "score": 0.7, "label": "icon"}]},
        source_image=Path("inputs/figure.png"),
        parser_id="vision_layout_parser",
        parser_priority=20,
    )[0]

    result = fuse_candidates([first, second], config=FusionConfig.default())

    assert len(result.elements) == 1
    assert result.elements[0].source_candidate_ids == ("vision_layout_parser:B001",)
    suppressed = next(
        item for item in result.trace["decisions"] if item["action"] == "suppressed"
    )
    assert suppressed["candidate_id"] == "sam3:B001"
    assert suppressed["other_candidate_id"] == "vision_layout_parser:B001"
    assert suppressed["candidate_source_parser"] == "sam3_structure_parser"
    assert suppressed["other_source_parser"] == "vision_layout_parser"
    assert suppressed["confidence"] == 0.99
    assert suppressed["other_confidence"] == 0.7
    assert suppressed["parser_priority"] == 10
    assert suppressed["other_parser_priority"] == 20


def test_fusion_uses_confidence_tie_break_for_same_priority_duplicates() -> None:
    lower_confidence = _candidate(
        candidate_id="sam3:B100",
        confidence=0.7,
        parser_priority=10,
    )
    higher_confidence = _candidate(
        candidate_id="sam3:B101",
        confidence=0.95,
        parser_priority=10,
    )

    result = fuse_candidates(
        [lower_confidence, higher_confidence],
        config=FusionConfig.default(),
    )

    assert len(result.elements) == 1
    assert result.elements[0].source_candidate_ids == ("sam3:B101",)
    suppressed = next(
        item for item in result.trace["decisions"] if item["action"] == "suppressed"
    )
    assert suppressed["candidate_id"] == "sam3:B100"
    assert suppressed["other_candidate_id"] == "sam3:B101"


def test_fusion_assigns_element_ids_in_output_order() -> None:
    candidates = sam3_payload_to_candidates(
        {
            "raw_regions": [
                {"bbox": [50, 10, 70, 30], "score": 0.8, "label": "icon", "z_hint": 2},
                {"bbox": [5, 20, 25, 40], "score": 0.8, "label": "picture", "z_hint": 1},
                {"bbox": [5, 5, 25, 18], "score": 0.8, "label": "symbol", "z_hint": 1},
            ]
        },
        source_image=Path("inputs/figure.png"),
    )

    result = fuse_candidates(candidates, config=FusionConfig.default())

    assert [(plan.element_id, plan.element_type) for plan in result.elements] == [
        ("E001", "symbol"),
        ("E002", "picture"),
        ("E003", "icon"),
    ]
    assert [plan.z_order for plan in result.elements] == [0, 1, 2]


def test_fusion_keeps_locked_mask_geometry_conflicts_unmerged() -> None:
    mask_candidate = sam3_payload_to_candidates(
        {
            "raw_regions": [
                {
                    "bbox": [0, 0, 20, 20],
                    "score": 0.7,
                    "label": "symbol",
                    "mask_path": "masks/symbol.png",
                }
            ]
        },
        source_image=Path("inputs/figure.png"),
    )[0]
    bbox_candidate = sam3_payload_to_candidates(
        {
            "raw_regions": [
                {"bbox": [0, 0, 20, 20], "score": 0.9, "label": "symbol"}
            ]
        },
        source_image=Path("inputs/figure.png"),
        parser_id="vision_layout_parser",
        parser_priority=20,
    )[0]

    result = fuse_candidates([mask_candidate, bbox_candidate], config=FusionConfig.default())

    assert [plan.source_candidate_ids for plan in result.elements] == [
        (mask_candidate.candidate_id,),
        (bbox_candidate.candidate_id,),
    ]
    assert any(
        item["action"] == "kept_separate"
        and item["reason"] == "locked_mask_geometry_conflict"
        for item in result.trace["decisions"]
    )
