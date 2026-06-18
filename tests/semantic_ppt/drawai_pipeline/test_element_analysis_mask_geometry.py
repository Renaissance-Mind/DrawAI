from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from PIL import Image, ImageDraw

from drawai.workbench.assets import validate_asset_plan


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = REPO_ROOT / "scripts" / "run_codex_element_analysis.py"


def _load_run0_module():
    spec = importlib.util.spec_from_file_location("run_codex_element_analysis", SCRIPT_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _write_json(path: Path, payload: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_mask_case(module, case_dir: Path) -> dict:
    figure_path = case_dir / "inputs" / "figure.png"
    figure_path.parent.mkdir(parents=True)
    Image.new("RGBA", (20, 20), (180, 210, 245, 255)).save(figure_path)

    mask_path = case_dir / "sam3" / "masks" / "B001.png"
    mask_path.parent.mkdir(parents=True)
    mask = Image.new("L", (20, 20), 0)
    ImageDraw.Draw(mask).ellipse([4, 4, 15, 15], fill=255)
    mask.save(mask_path)

    _write_json(
        case_dir / "box_ir" / "box_ir.json",
        {
            "boxes": [
                {
                    "id": "B001",
                    "type": "icon",
                    "bbox": [4, 4, 16, 16],
                    "geometry": {
                        "kind": "mask",
                        "mask_path": "sam3/masks/B001.png",
                        "bbox": [4, 4, 16, 16],
                    },
                }
            ]
        },
    )
    return module.build_request(case_dir, case_dir / "reports" / "element_analysis_codex")


def test_run0_request_uses_mask_preview_and_enrichment_restores_mask_geometry(tmp_path: Path):
    module = _load_run0_module()
    case_dir = tmp_path / "case"
    output_dir = case_dir / "reports" / "element_analysis_codex"
    request = _write_mask_case(module, case_dir)
    candidate = request["candidates"][0]
    assert candidate["geometry_kind"] == "mask"
    assert candidate["geometry_locked"] is True
    assert candidate["geometry"]["kind"] == "mask"
    assert "mask_path" not in candidate["geometry"]
    preview_path = case_dir / candidate["geometry_preview"]
    assert preview_path.is_file()
    assert (case_dir / request["mask_preview_sheet"]).is_file()
    with Image.open(preview_path) as preview:
        assert preview.convert("RGBA").getpixel((0, 0))[3] == 0

    module.write_json(output_dir / "element_analysis_request.json", request)
    analysis = {
        "schema": module.SCHEMA_OUTPUT,
        "elements": [
            {
                "box_id": "B001",
                "source_candidate_ids": ["B001"],
                "refinement_action": "adjusted",
                "category": "crop",
                "confidence": "high",
                "visual_role": "masked icon",
                "reason": "Kept as source crop.",
                "bbox": [0, 0, 3, 3],
                "type": "icon",
            }
        ],
    }
    enriched = module.enrich_analysis_with_source_geometry(case_dir, analysis)
    element = enriched["elements"][0]
    assert element["bbox"] == [4.0, 4.0, 16.0, 16.0]
    assert element["geometry"]["kind"] == "mask"
    assert element["geometry"]["mask_path"] == "sam3/masks/B001.png"
    assert element["geometry_locked"] is True
    assert element["geometry_preview_relative_path"] == candidate["geometry_preview"]

    validated = validate_asset_plan({"elements": enriched["elements"]})
    draft_element = validated["elements"][0]
    assert draft_element["geometry"]["kind"] == "mask"
    assert draft_element["geometry_preview_relative_path"] == candidate["geometry_preview"]
    assert draft_element["geometry_locked"] is True

    v2_export = module.write_v2_element_plans_export(output_dir, enriched, request)
    assert (output_dir / "element_plans.v2.json").is_file()
    v2_element = v2_export["elements"][0]
    assert v2_element["element_id"] == "B001"
    assert v2_element["bbox"] == [4.0, 4.0, 12.0, 12.0]
    assert v2_element["geometry"]["kind"] == "mask"


def test_v2_export_counts_codex_removal_records_for_coverage(tmp_path: Path):
    module = _load_run0_module()
    output_dir = tmp_path / "reports" / "element_analysis_codex"
    analysis = {
        "schema": module.SCHEMA_OUTPUT,
        "elements": [
            {
                "box_id": "B001",
                "source_candidate_ids": ["B001"],
                "refinement_action": "unchanged",
                "category": "crop",
                "confidence": "high",
                "visual_role": "retained icon",
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
    request = {"candidates": [{"box_id": "B001"}, {"box_id": "B002"}]}

    validation = module.validate_analysis(analysis, request)
    assert validation["candidate_count"] == 2
    assert validation["removal_count"] == 1

    v2_export = module.write_v2_element_plans_export(output_dir, analysis, request)

    assert [element["element_id"] for element in v2_export["elements"]] == ["B001"]
    assert v2_export["validation"]["candidate_count"] == 2
    assert v2_export["validation"]["element_count"] == 1
    assert v2_export["validation"]["removal_count"] == 1
    assert v2_export["removals"] == [
        {
            "action": "merged",
            "source_candidate_ids": ["B002"],
            "reason": "Merged into B001 because it is a duplicate mask.",
        }
    ]


def test_v2_export_keeps_retained_merged_records_as_elements(tmp_path: Path):
    module = _load_run0_module()
    output_dir = tmp_path / "reports" / "element_analysis_codex"
    analysis = {
        "schema": module.SCHEMA_OUTPUT,
        "elements": [
            {
                "box_id": "B001_M01",
                "source_candidate_ids": ["B001", "B002"],
                "refinement_action": "merged",
                "category": "svg_self_draw",
                "confidence": "high",
                "visual_role": "merged frame",
                "reason": "Retained frame merged from duplicate parser candidates.",
                "bbox": [1, 2, 21, 32],
                "type": "frame",
            },
            {
                "box_id": "B001_S01",
                "source_candidate_ids": ["B001"],
                "refinement_action": "split",
                "category": "svg_self_draw",
                "confidence": "high",
                "visual_role": "split label",
                "reason": "Label split from the broad source candidate.",
                "bbox": [3, 4, 10, 12],
                "type": "text",
            },
        ],
    }
    request = {"candidates": [{"box_id": "B001"}, {"box_id": "B002"}]}

    validation = module.validate_analysis(analysis, request)
    assert validation["element_count"] == 2
    assert validation["removal_count"] == 0

    v2_export = module.write_v2_element_plans_export(output_dir, analysis, request)

    assert [element["element_id"] for element in v2_export["elements"]] == ["B001_M01", "B001_S01"]
    assert v2_export["removals"] == []


def test_finalize_analysis_outputs_counts_top_level_removal_records(tmp_path: Path):
    module = _load_run0_module()
    case_dir = tmp_path / "case"
    output_dir = case_dir / "reports" / "element_analysis_codex"
    output_path = output_dir / "element_analysis.json"
    _write_json(
        case_dir / "box_ir" / "box_ir.json",
        {
            "boxes": [
                {"id": "B001", "type": "icon", "bbox": [1, 2, 21, 32]},
                {"id": "B002", "type": "icon", "bbox": [30, 40, 50, 60]},
            ]
        },
    )
    request = {
        "candidates": [
            {"box_id": "B001", "type": "icon", "bbox": [1, 2, 21, 32]},
            {"box_id": "B002", "type": "icon", "bbox": [30, 40, 50, 60]},
        ]
    }
    _write_json(output_dir / "element_analysis_request.json", request)
    _write_json(
        output_path,
        {
            "schema": module.SCHEMA_OUTPUT,
            "elements": [
                {
                    "box_id": "B001",
                    "source_candidate_ids": ["B001"],
                    "refinement_action": "unchanged",
                    "category": "crop",
                    "confidence": "high",
                    "visual_role": "retained icon",
                    "reason": "Kept as source crop.",
                    "bbox": [1, 2, 21, 32],
                    "type": "icon",
                }
            ],
            "removal_records": [
                {
                    "box_id": "B002",
                    "source_candidate_ids": ["B002"],
                    "refinement_action": "merged",
                    "reason": "Merged into B001 because it is a duplicate.",
                }
            ],
        },
    )

    validation, v2_export = module.finalize_analysis_outputs(
        case_dir=case_dir,
        output_dir=output_dir,
        output_path=output_path,
        request=request,
    )

    saved = json.loads(output_path.read_text(encoding="utf-8"))
    assert [element["box_id"] for element in saved["elements"]] == ["B001"]
    assert validation["candidate_count"] == 2
    assert validation["element_count"] == 1
    assert validation["removal_count"] == 1
    assert v2_export["validation"]["element_count"] == 1
    assert v2_export["validation"]["removal_count"] == 1
    assert v2_export["removals"] == [
        {
            "action": "merged",
            "source_candidate_ids": ["B002"],
            "reason": "Merged into B001 because it is a duplicate.",
        }
    ]


def test_finalize_analysis_outputs_backfills_omitted_candidates_as_unchanged(tmp_path: Path):
    module = _load_run0_module()
    case_dir = tmp_path / "case"
    output_dir = case_dir / "reports" / "element_analysis_codex"
    output_path = output_dir / "element_analysis.json"
    _write_json(
        case_dir / "box_ir" / "box_ir.json",
        {
            "boxes": [
                {"id": "B001", "type": "icon", "bbox": [1, 2, 21, 32]},
                {"id": "B002", "type": "icon", "bbox": [30, 40, 50, 60]},
            ]
        },
    )
    request = {
        "candidates": [
            {
                "box_id": "B001",
                "type": "icon",
                "bbox": [1, 2, 21, 32],
                "current_pipeline_method": "crop",
            },
            {
                "box_id": "B002",
                "type": "icon",
                "bbox": [30, 40, 50, 60],
                "current_pipeline_method": "svg_self_draw",
            },
        ]
    }
    _write_json(output_dir / "element_analysis_request.json", request)
    _write_json(
        output_path,
        {
            "schema": module.SCHEMA_OUTPUT,
            "elements": [
                {
                    "box_id": "B001",
                    "source_candidate_ids": ["B001"],
                    "refinement_action": "unchanged",
                    "category": "crop",
                    "confidence": "high",
                    "visual_role": "retained icon",
                    "reason": "Kept as source crop.",
                    "bbox": [1, 2, 21, 32],
                    "type": "icon",
                }
            ],
        },
    )

    validation, v2_export = module.finalize_analysis_outputs(
        case_dir=case_dir,
        output_dir=output_dir,
        output_path=output_path,
        request=request,
    )

    saved = json.loads(output_path.read_text(encoding="utf-8"))
    backfilled = saved["elements"][1]
    assert validation["candidate_count"] == 2
    assert backfilled["box_id"] == "B002"
    assert backfilled["source_candidate_ids"] == ["B002"]
    assert backfilled["refinement_action"] == "unchanged"
    assert backfilled["category"] == "svg_self_draw"
    assert [element["element_id"] for element in v2_export["elements"]] == ["B001", "B002"]


def test_v2_export_preserves_added_element_empty_sources(tmp_path: Path):
    module = _load_run0_module()
    output_dir = tmp_path / "reports" / "element_analysis_codex"
    analysis = {
        "schema": module.SCHEMA_OUTPUT,
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

    v2_export = module.write_v2_element_plans_export(
        output_dir,
        analysis,
        {"candidates": []},
    )

    assert v2_export["elements"][0]["element_id"] == "N001"
    assert v2_export["elements"][0]["source_candidate_ids"] == []


def test_v2_export_normalizes_added_asset_meta_type(tmp_path: Path):
    module = _load_run0_module()
    output_dir = tmp_path / "reports" / "element_analysis_codex"
    analysis = {
        "schema": module.SCHEMA_OUTPUT,
        "elements": [
            {
                "box_id": "N001",
                "source_candidate_ids": [],
                "refinement_action": "added",
                "category": "crop_nobg",
                "confidence": "medium",
                "visual_role": "decorative robot at upper right",
                "reason": "Added because the parser missed this illustration.",
                "bbox": [1, 2, 21, 32],
                "type": "added_asset",
            },
            {
                "box_id": "N002",
                "source_candidate_ids": [],
                "refinement_action": "added",
                "category": "svg_self_draw",
                "confidence": "medium",
                "visual_role": "main title text line",
                "reason": "Added because the parser missed this title.",
                "bbox": [30, 40, 90, 60],
                "type": "added_asset",
            },
        ],
    }

    v2_export = module.write_v2_element_plans_export(
        output_dir,
        analysis,
        {"candidates": []},
    )

    assert [(item["element_id"], item["element_type"]) for item in v2_export["elements"]] == [
        ("N001", "picture"),
        ("N002", "text"),
    ]


def test_added_records_cannot_claim_existing_source_candidates(tmp_path: Path):
    module = _load_run0_module()
    output_dir = tmp_path / "reports" / "element_analysis_codex"
    analysis = {
        "schema": module.SCHEMA_OUTPUT,
        "elements": [
            {
                "box_id": "N001",
                "source_candidate_ids": ["B001"],
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
    request = {"candidates": [{"box_id": "B001"}]}

    with pytest.raises(ValueError, match="added.*source_candidate_ids"):
        module.validate_analysis(analysis, request)
    with pytest.raises(ValueError, match="added.*source_candidate_ids"):
        module.write_v2_element_plans_export(output_dir, analysis, request)


def test_mask_removal_records_are_not_enriched_as_retained_masks(tmp_path: Path):
    module = _load_run0_module()
    case_dir = tmp_path / "case"
    output_dir = case_dir / "reports" / "element_analysis_codex"
    request = _write_mask_case(module, case_dir)
    module.write_json(output_dir / "element_analysis_request.json", request)
    analysis = {
        "schema": module.SCHEMA_OUTPUT,
        "elements": [
            {
                "box_id": "B001",
                "source_candidate_ids": ["B001"],
                "refinement_action": "merged",
                "reason": "Merged into another retained element.",
            }
        ],
    }

    enriched = module.enrich_analysis_with_source_geometry(case_dir, analysis)
    element = enriched["elements"][0]
    assert "geometry" not in element
    assert "geometry_locked" not in element
    assert "Mask geometry is preserved" not in element["reason"]

    v2_export = module.write_v2_element_plans_export(output_dir, enriched, request)
    assert v2_export["elements"] == []
    assert v2_export["removals"] == [
        {
            "action": "merged",
            "source_candidate_ids": ["B001"],
            "reason": "Merged into another retained element.",
        }
    ]


def test_skip_existing_refreshes_v2_export_without_invoking_codex(tmp_path: Path):
    module = _load_run0_module()
    case_dir = tmp_path / "case"
    output_dir = case_dir / "reports" / "element_analysis_codex"
    _write_mask_case(module, case_dir)
    _write_json(
        output_dir / "element_analysis.json",
        {
            "schema": module.SCHEMA_OUTPUT,
            "elements": [
                {
                    "box_id": "B001",
                    "source_candidate_ids": ["B001"],
                    "refinement_action": "unchanged",
                    "category": "crop",
                    "confidence": "high",
                    "visual_role": "masked icon",
                    "reason": "Kept as source crop.",
                    "bbox": [4, 4, 16, 16],
                    "type": "icon",
                }
            ],
        },
    )

    result = module.run_case(
        case_dir,
        SimpleNamespace(skip_existing=True),
    )

    assert result["skipped"] is True
    assert (output_dir / "element_plans.v2.json").is_file()
    assert (output_dir / "validation.json").is_file()


def test_enrich_analysis_rejects_non_object_elements(tmp_path: Path):
    module = _load_run0_module()
    case_dir = tmp_path / "case"
    _write_json(case_dir / "box_ir" / "box_ir.json", {"boxes": []})

    with pytest.raises(ValueError, match="element analysis record 0"):
        module.enrich_analysis_with_source_geometry(
            case_dir,
            {
                "schema": module.SCHEMA_OUTPUT,
                "elements": ["malformed"],
            },
        )


def test_validate_analysis_rejects_malformed_source_candidate_ids(tmp_path: Path):
    module = _load_run0_module()
    analysis = {
        "schema": module.SCHEMA_OUTPUT,
        "elements": [
            {
                "box_id": "B001",
                "source_candidate_ids": ["B001", ""],
                "refinement_action": "unchanged",
                "category": "crop",
                "confidence": "high",
                "visual_role": "retained icon",
                "reason": "Kept as source crop.",
                "bbox": [1, 2, 21, 32],
                "type": "icon",
            }
        ],
    }

    with pytest.raises(ValueError, match="source_candidate_ids"):
        module.validate_analysis(analysis, {"candidates": [{"box_id": "B001"}]})
