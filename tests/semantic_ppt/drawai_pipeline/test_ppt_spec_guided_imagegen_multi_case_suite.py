from __future__ import annotations

import json
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_ROOT = REPO_ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from run_ppt_spec_guided_imagegen_multi_case_suite import (  # noqa: E402
    SUITE_CASES,
    build_case_payload,
    build_feature_matrix,
    write_prompt_record,
)


def test_multi_case_payload_is_spec_guided_not_prompt_only(tmp_path: Path) -> None:
    inputs = _fake_inputs(tmp_path)
    source_copy = tmp_path / "source_reference.jpg"
    source_copy.write_bytes(b"fake")

    payload = build_case_payload(
        SUITE_CASES[0],
        inputs=inputs,
        source_copy=source_copy,
        original_source_image=source_copy,
    )

    assert payload["schema"] == "drawai.ppt_spec_guided_imagegen.multi_case_payload.v1"
    assert payload["provider"] == "codex"
    assert payload["from_template_spec"]["design_tokens"]
    assert payload["from_template_spec"]["spec_lock"]["lock_canvas"] is True
    assert payload["from_slot_schema"]["selected_slots"]
    assert payload["from_reference_style_spec"]["reference_roles"]
    assert "template/spec/slot/design lock" in payload["prompt"]


def test_multi_case_edit_payload_has_local_image_and_workbench_fields(tmp_path: Path) -> None:
    inputs = _fake_inputs(tmp_path)
    source_copy = tmp_path / "source_reference.jpg"
    original = tmp_path / "original.jpg"
    source_copy.write_bytes(b"fake")
    original.write_bytes(b"fake")
    edit_case = next(case for case in SUITE_CASES if case.get("workbench_request"))

    payload = build_case_payload(
        edit_case,
        inputs=inputs,
        source_copy=source_copy,
        original_source_image=original,
    )

    assert payload["operation"] == "edit"
    assert payload["source_image_path"] == str(source_copy)
    assert payload["reference_image_path"] == str(source_copy)
    assert payload["reference_image_paths"] == [str(source_copy)]
    assert payload["uses_local_image_input"] is True
    assert payload["workbench_request"]["provider"] == "codex"
    assert payload["workbench_request"]["source_image_path"] == str(source_copy)


def test_multi_case_feature_matrix_covers_required_capabilities() -> None:
    records = [
        {"case_id": case["id"], "features": case["features"], "uses_local_image_input": case["operation"] == "edit", "reference_roles_used": ["layout_reference"]}
        for case in SUITE_CASES
    ]

    matrix = build_feature_matrix(records)

    assert matrix["spec_guided"]
    assert len(matrix["reference_image_edit"]) >= 3
    assert matrix["source_grounded"]
    assert matrix["data_driven"]
    assert matrix["safe_ip_cartoon"]
    assert matrix["template_vs_prompt_only"] == ["x1_template_vs_prompt_only_contrast"]
    assert "a2_kb_agent_workflow_edit" in matrix["workbench_reference_request"]


def test_multi_case_prompt_only_record_writes_artifacts(tmp_path: Path) -> None:
    inputs = _fake_inputs(tmp_path)
    source_copy = tmp_path / "source_reference.jpg"
    source_copy.write_bytes(b"fake")
    case_dir = tmp_path / "case"

    record = write_prompt_record(
        SUITE_CASES[1],
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
    return {
        "template_spec_path": str(tmp_path / "template_spec.json"),
        "slot_schema_path": str(tmp_path / "slot_schema_preview.json"),
        "reference_style_spec_path": str(tmp_path / "reference_style_spec.json"),
        "template_asset_path": str(tmp_path / "template.json"),
        "template_spec": {
            "schema": "drawai.ppt_template_spec.v1",
            "source_pptx": str(tmp_path / "template.pptx"),
            "slide_size": {"width_in": 13.333, "height_in": 7.5, "aspect_ratio": 1.7777},
            "design_tokens": {"palette": ["#ffffff", "#fbbf24"], "slot_roles": {"title": 1}},
            "spec_lock": {"lock_canvas": True, "lock_slot_geometry": True},
            "layouts": [
                {"id": "slide_01_blank", "name": "Blank", "slide_index": 0, "role_guess": "cover", "slot_summary": {"text_slot_count": 2}},
                {"id": "slide_02_blank", "name": "Blank", "slide_index": 1, "role_guess": "content", "slot_summary": {"text_slot_count": 4}},
                {"id": "slide_03_blank", "name": "Blank", "slide_index": 2, "role_guess": "process_or_timeline", "slot_summary": {"text_slot_count": 4}},
                {"id": "slide_04_blank", "name": "Blank", "slide_index": 3, "role_guess": "data_page", "slot_summary": {"text_slot_count": 2}},
            ],
        },
        "slot_schema": {
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
                    "layout_id": "slide_02_blank",
                    "slide_index": 1,
                    "role_guess": "content",
                    "slots": [
                        {"slot_id": "s02_shape_1", "name": "slot_content_title", "role": "title"},
                        {"slot_id": "s02_shape_2", "name": "slot_card_1", "role": "body"},
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
                {
                    "layout_id": "slide_04_blank",
                    "slide_index": 3,
                    "role_guess": "data_page",
                    "slots": [{"slot_id": "s04_shape_1", "name": "slot_data_title", "role": "title"}],
                    "tables": [{"table_id": "s04_table_1", "name": "native_table_capability_matrix"}],
                    "charts": [{"chart_id": "s04_chart_1", "name": "native_chart_phase_coverage"}],
                },
            ],
        },
        "reference_style_spec": {
            "schema": "drawai.reference_style_spec.v1",
            "source_image_path": str(tmp_path / "source_reference.jpg"),
            "reference_roles": [
                {"role": "layout_reference", "weight": 0.45, "locked_features": ["two-column flow"]},
                {"role": "style_reference", "weight": 0.25, "locked_features": ["academic flowchart"]},
                {"role": "color_reference", "weight": 0.15, "locked_features": ["yellow top bars"]},
                {"role": "typography_reference", "weight": 0.1, "locked_features": ["readable labels"]},
                {"role": "content_reference", "weight": 0.05, "locked_features": ["workflow only"]},
            ],
            "design_tokens": {"palette": {"header_bar": "#fbbf24"}},
            "spec_lock": {"lock_layout_archetype": True},
        },
        "template_asset": {
            "id": "prisma_flow_diagram",
            "design_tokens": {"palette": {"header": "#fbbf24"}},
            "layout": {"archetype": "prisma_flow"},
            "slot_schema": {"flow_boxes": {"required": True}},
            "reference_roles": [{"role": "layout_reference"}],
        },
    }
