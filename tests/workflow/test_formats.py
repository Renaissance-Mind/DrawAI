from __future__ import annotations

import json
import zipfile
from pathlib import Path

from PIL import Image

from drawai.workflow.formats import default_format_registry, element_plans_from_payload, validate_format_file


def test_default_format_registry_contains_core_formats() -> None:
    registry = default_format_registry()

    assert "drawai.image.v1" in registry
    assert "drawai.element_candidates.v1" in registry
    assert "drawai.page_spec.v1" in registry
    assert "drawai.semantic_svg.v1" in registry
    assert "drawai.pptx.v1" in registry


def test_validate_image_format_accepts_openable_image(tmp_path: Path) -> None:
    image_path = tmp_path / "source.png"
    Image.new("RGB", (20, 10), "white").save(image_path)

    result = validate_format_file("drawai.image.v1", image_path)

    assert result.ok
    assert result.errors == ()


def test_validate_image_format_rejects_text_file(tmp_path: Path) -> None:
    image_path = tmp_path / "source.png"
    image_path.write_text("not an image", encoding="utf-8")

    result = validate_format_file("drawai.image.v1", image_path)

    assert not result.ok
    assert result.errors


def test_validate_element_candidates_accepts_required_candidate_fields(tmp_path: Path) -> None:
    candidates_path = tmp_path / "candidates.json"
    candidates_path.write_text(
        json.dumps(
            {
                "schema": "drawai.v2.parser_outputs.v1",
                "candidates": [
                    {
                        "schema": "drawai.element_candidate.v1",
                        "candidate_id": "sam:B001",
                        "source_parser": "sam3_structure_parser",
                        "source_parser_version": "v1",
                        "element_type": "icon",
                        "bbox": [1, 2, 10, 20],
                        "geometry": {
                            "kind": "bbox",
                            "bbox": [1, 2, 11, 22],
                            "coordinate_system": "figure_image_pixels",
                        },
                        "confidence": 0.9,
                        "z_hint": None,
                        "text": "",
                        "evidence_files": [],
                        "provenance": {"source": "fixture"},
                        "raw_ref": {"source": "fixture"},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    result = validate_format_file("drawai.element_candidates.v1", candidates_path)

    assert result.ok
    assert result.errors == ()


def test_validate_element_candidates_rejects_missing_required_fields(tmp_path: Path) -> None:
    candidates_path = tmp_path / "candidates.json"
    candidates_path.write_text(
        json.dumps({"candidates": [{"candidate_id": "sam:B001"}]}),
        encoding="utf-8",
    )

    result = validate_format_file("drawai.element_candidates.v1", candidates_path)

    assert not result.ok
    assert any("source_parser" in error for error in result.errors)


def test_element_plans_from_payload_accepts_legacy_codex_analysis() -> None:
    plans = element_plans_from_payload(
        {
            "schema": "drawai.codex_element_analysis.v1",
            "elements": [
                {
                    "box_id": "E001",
                    "source_candidate_ids": ["fixture:E001"],
                    "bbox": [2, 2, 14, 14],
                    "category": "crop",
                    "type": "picture",
                    "confidence": "high",
                    "reason": "legacy review fixture",
                }
            ],
        }
    )

    assert len(plans) == 1
    assert plans[0].element_id == "E001"
    assert plans[0].processing_intent.processing_type == "crop"


def test_validate_page_spec_accepts_canonical_page_elements(tmp_path: Path) -> None:
    page_spec_path = tmp_path / "page_spec.json"
    page_spec_path.write_text(
        json.dumps(
            {
                "schema": "drawai.page_spec.v1",
                "page_id": "page-1",
                "source": {"image": "source.png", "width_px": 100, "height_px": 80},
                "canvas": {"width_px": 100, "height_px": 80},
                "elements": [
                    {
                        "id": "E001",
                        "kind": "text",
                        "role": "title",
                        "box_px": [4, 6, 40, 10],
                        "z_index": 1,
                        "confidence": "high",
                        "text": "DrawAI",
                        "build": {"mode": "editable_text", "processing_type": "svg_self_draw"},
                        "source_refs": [{"kind": "candidate", "id": "ocr:T001"}],
                    },
                    {
                        "id": "G001",
                        "kind": "group",
                        "box_px": [0, 0, 100, 80],
                        "children": ["E001"],
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    result = validate_format_file("drawai.page_spec.v1", page_spec_path)

    assert result.ok
    assert result.errors == ()


def test_validate_page_spec_rejects_missing_children(tmp_path: Path) -> None:
    page_spec_path = tmp_path / "page_spec.json"
    page_spec_path.write_text(
        json.dumps(
            {
                "schema": "drawai.page_spec.v1",
                "page_id": "page-1",
                "elements": [
                    {
                        "id": "G001",
                        "kind": "group",
                        "box_px": [0, 0, 100, 80],
                        "children": ["E404"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    result = validate_format_file("drawai.page_spec.v1", page_spec_path)

    assert not result.ok
    assert any("missing child" in error for error in result.errors)


def test_validate_semantic_svg_accepts_svg_root(tmp_path: Path) -> None:
    svg_path = tmp_path / "semantic.svg"
    svg_path.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><rect width="10" height="10"/></svg>',
        encoding="utf-8",
    )

    result = validate_format_file("drawai.semantic_svg.v1", svg_path)

    assert result.ok


def test_validate_semantic_svg_rejects_non_svg_xml(tmp_path: Path) -> None:
    svg_path = tmp_path / "semantic.svg"
    svg_path.write_text("<html><body>nope</body></html>", encoding="utf-8")

    result = validate_format_file("drawai.semantic_svg.v1", svg_path)

    assert not result.ok
    assert any("svg" in error.lower() for error in result.errors)


def test_validate_pptx_accepts_minimal_presentation_package(tmp_path: Path) -> None:
    pptx_path = tmp_path / "deck.pptx"
    with zipfile.ZipFile(pptx_path, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("ppt/presentation.xml", "<p:presentation xmlns:p='http://schemas.openxmlformats.org/presentationml/2006/main'/>")

    result = validate_format_file("drawai.pptx.v1", pptx_path)

    assert result.ok


def test_validate_pptx_rejects_zip_without_presentation(tmp_path: Path) -> None:
    pptx_path = tmp_path / "deck.pptx"
    with zipfile.ZipFile(pptx_path, "w") as archive:
        archive.writestr("notes.txt", "not a pptx")

    result = validate_format_file("drawai.pptx.v1", pptx_path)

    assert not result.ok
    assert any("presentation" in error or "Content_Types" in error for error in result.errors)
