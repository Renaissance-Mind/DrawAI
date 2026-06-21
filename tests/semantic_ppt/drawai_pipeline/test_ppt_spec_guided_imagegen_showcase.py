from __future__ import annotations

import json
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_ROOT = REPO_ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from run_ppt_spec_guided_imagegen_showcase import (  # noqa: E402
    PAGE_CASES,
    build_case_payload,
    write_prompt_record,
)


def test_spec_guided_payload_contains_template_slot_and_reference_specs(tmp_path: Path) -> None:
    inputs = _fake_inputs(tmp_path)
    source_copy = tmp_path / "source_reference.jpg"
    source_copy.write_bytes(b"fake image")

    payload = build_case_payload(
        PAGE_CASES[0],
        inputs=inputs,
        source_copy=source_copy,
        original_source_image=source_copy,
    )

    assert payload["schema"] == "drawai.ppt_spec_guided_imagegen.case_payload.v1"
    assert payload["operation"] == "generate"
    assert payload["from_template_spec"]["slide_size"]["width_in"] == 13.333
    assert payload["from_slot_schema"]["selected_slots"]
    assert payload["from_reference_style_spec"]["reference_roles"]
    assert "PPT slide image" in payload["prompt"]
    assert "NOT a PPTX" in payload["prompt"]


def test_spec_guided_edit_payload_uses_source_image_path(tmp_path: Path) -> None:
    inputs = _fake_inputs(tmp_path)
    source_copy = tmp_path / "source_reference.jpg"
    original = tmp_path / "original.jpg"
    source_copy.write_bytes(b"fake image")
    original.write_bytes(b"fake image")
    edit_case = next(case for case in PAGE_CASES if case["operation"] == "edit")

    payload = build_case_payload(
        edit_case,
        inputs=inputs,
        source_copy=source_copy,
        original_source_image=original,
    )

    assert payload["operation"] == "edit"
    assert payload["source_image_path"] == str(source_copy)
    assert payload["original_source_image_path"] == str(original)
    assert payload["uses_local_image_input"] is True
    assert "LocalImageInput" in payload["prompt"]


def test_prompt_only_record_writes_payload_prompt_and_record(tmp_path: Path) -> None:
    inputs = _fake_inputs(tmp_path)
    source_copy = tmp_path / "source_reference.jpg"
    source_copy.write_bytes(b"fake image")
    case_dir = tmp_path / "case"

    record = write_prompt_record(
        PAGE_CASES[1],
        case_dir=case_dir,
        inputs=inputs,
        source_copy=source_copy,
        original_source_image=source_copy,
    )

    assert record["status"] == "prompt_only"
    assert record["operation"] == "edit"
    assert record["uses_local_image_input"] is True
    assert (case_dir / "payload.json").is_file()
    assert (case_dir / "prompt.txt").is_file()
    assert (case_dir / "record.json").is_file()
    payload = json.loads((case_dir / "payload.json").read_text(encoding="utf-8"))
    assert payload["from_template_spec"]
    assert payload["from_slot_schema"]
    assert payload["from_reference_style_spec"]


def _fake_inputs(tmp_path: Path) -> dict[str, object]:
    template_spec = {
        "schema": "drawai.ppt_template_spec.v1",
        "source_pptx": str(tmp_path / "template.pptx"),
        "slide_size": {"width_in": 13.333, "height_in": 7.5, "aspect_ratio": 1.7777},
        "design_tokens": {"palette": ["#ffffff", "#fbbf24"], "slot_roles": {"title": 1}},
        "spec_lock": {"lock_canvas": True, "lock_slot_geometry": True},
        "layouts": [
            {
                "id": "slide_01_blank",
                "name": "Blank",
                "slide_index": 0,
                "role_guess": "cover",
                "slot_summary": {"text_slot_count": 2},
            },
            {
                "id": "slide_03_blank",
                "name": "Blank",
                "slide_index": 2,
                "role_guess": "process_or_timeline",
                "slot_summary": {"text_slot_count": 4},
            },
        ],
    }
    slot_schema = {
        "schema": "drawai.ppt_template_slot_schema_preview.v1",
        "layouts": [
            {
                "layout_id": "slide_01_blank",
                "slide_index": 0,
                "role_guess": "cover",
                "slots": [
                    {"slot_id": "s01_shape_1", "name": "slot_cover_title", "role": "title"},
                    {"slot_id": "s01_shape_2", "name": "slot_cover_subtitle", "role": "subtitle"},
                ],
                "tables": [],
                "charts": [],
            },
            {
                "layout_id": "slide_03_blank",
                "slide_index": 2,
                "role_guess": "process_or_timeline",
                "slots": [
                    {"slot_id": "s03_shape_1", "name": "slot_flow_title", "role": "title"},
                    {"slot_id": "s03_shape_2", "name": "slot_flow_step_1", "role": "label"},
                ],
                "tables": [],
                "charts": [],
            },
        ],
    }
    reference_style_spec = {
        "schema": "drawai.reference_style_spec.v1",
        "source_image_path": str(tmp_path / "source_reference.jpg"),
        "reference_roles": [
            {"role": "layout_reference", "weight": 0.45, "locked_features": ["yellow top bars"]},
            {"role": "style_reference", "weight": 0.25, "locked_features": ["clean flowchart"]},
        ],
        "design_tokens": {"palette": {"header_bar": "#fbbf24"}},
        "spec_lock": {"lock_layout_archetype": True},
    }
    template_asset = {
        "id": "prisma_flow_diagram",
        "design_tokens": {"palette": {"header": "#fbbf24"}},
        "layout": {"archetype": "prisma_flow"},
        "slot_schema": {"flow_boxes": {"required": True}},
        "reference_roles": [{"role": "layout_reference"}],
    }
    return {
        "template_spec_path": str(tmp_path / "template_spec.json"),
        "slot_schema_path": str(tmp_path / "slot_schema_preview.json"),
        "reference_style_spec_path": str(tmp_path / "reference_style_spec.json"),
        "template_asset_path": str(tmp_path / "template.json"),
        "template_spec": template_spec,
        "slot_schema": slot_schema,
        "reference_style_spec": reference_style_spec,
        "template_asset": template_asset,
    }
