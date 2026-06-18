from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from PIL import Image

from drawai.artifacts import DrawAiArtifactPaths, prepare_artifact_paths
from drawai.pipeline import run_drawai_pipeline_from_stage
from drawai.public_stages import PUBLIC_STAGE_ORDER, run_public_stage
from drawai.v2.schema import ElementPlan, ProcessingIntent
from drawai.v2.stages import (
    _merge_refined_plans_with_unexposed,
    _refinement_expected_source_candidate_ids,
    _translate_compat_analysis_source_ids,
)


def _config(
    tmp_path: Path,
    *,
    refine_enabled: bool | None = False,
    export_pptx: bool = False,
    compose_enabled: bool | None = None,
) -> Path:
    image = tmp_path / "input.png"
    Image.new("RGB", (80, 40), "white").save(image)
    config = tmp_path / "config.yaml"
    v2_lines: list[str] = []
    if refine_enabled is not None:
        v2_lines.append(
            f"""
  refine:
    enabled: {str(refine_enabled).lower()}
""".rstrip()
        )
    if compose_enabled is not None:
        v2_lines.append(
            f"""
  compose:
    enabled: {str(compose_enabled).lower()}
""".rstrip()
        )
    v2_body = "\n".join(v2_lines)
    v2_section = f"\nv2:\n{v2_body}\n" if v2_lines else ""
    config.write_text(
        f"""
input:
  image: {image.name}
  output_dir: out
  normalization:
    enabled: false
sam3:
  prompts:
    - id: icon
      text: icon
      confidence_threshold: 0.3
ocr:
  provider: fixture
  fixture:
    path: ocr_fixture.json
asset_materialization:
  rmbg:
    enabled: false
svg:
  max_attempts: 1
  staged_generation: false
  visual_review_rounds: []
svg_to_ppt:
  enabled: true
  export_pptx: {str(export_pptx).lower()}
{v2_section}
""",
        encoding="utf-8",
    )
    (tmp_path / "ocr_fixture.json").write_text(
        '{"ocr_text_boxes":[{"id":"T001","bbox":[4,5,20,14],"text":"Hello","confidence":0.9}]}',
        encoding="utf-8",
    )
    return config


def _write_fixture_refinement_artifact(paths: DrawAiArtifactPaths) -> None:
    paths.element_analysis_json.parent.mkdir(parents=True, exist_ok=True)
    paths.element_analysis_json.write_text(
        json.dumps(
            {
                "schema": "drawai.codex_element_analysis.v1",
                "elements": [
                    {
                        "element_id": "E001",
                        "source_candidate_ids": ["ocr:T001"],
                        "refinement_action": "unchanged",
                        "category": "svg_self_draw",
                        "confidence": "high",
                        "visual_role": "text",
                        "reason": "Keep the OCR text element.",
                        "bbox": [4, 5, 20, 14],
                        "type": "text",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )


def _write_compat_id_refinement_artifact(paths: DrawAiArtifactPaths) -> None:
    paths.element_analysis_json.parent.mkdir(parents=True, exist_ok=True)
    paths.element_analysis_json.write_text(
        json.dumps(
            {
                "schema": "drawai.codex_element_analysis.v1",
                "elements": [
                    {
                        "element_id": "E001",
                        "source_candidate_ids": ["E001"],
                        "refinement_action": "unchanged",
                        "category": "svg_self_draw",
                        "confidence": "high",
                        "visual_role": "text",
                        "reason": "Keep the OCR text element.",
                        "bbox": [4, 5, 20, 14],
                        "type": "text",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )


def _valid_fake_svg() -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 80 40" width="80" height="40">'
        "<desc>from fake invoker</desc>"
        '<rect x="0" y="0" width="80" height="40" fill="white"/>'
        '<text x="4" y="14" font-size="12" data-pb-role="label" '
        'data-pb-editable="true" data-pb-text-source="ocr" '
        'data-pb-orientation="horizontal">Hello</text>'
        "</svg>"
    )


def _fake_svg_invoker(calls: list[dict[str, object]] | None = None):
    def fake_svg_invoker(**kwargs):
        if calls is not None:
            calls.append(kwargs)
        return _valid_fake_svg()

    return fake_svg_invoker


def test_public_stage_order_uses_v2_main_path() -> None:
    assert PUBLIC_STAGE_ORDER == (
        "prepare",
        "parse_elements",
        "fuse_elements",
        "refine_elements",
        "plan_assets",
        "process_assets",
        "compose_svg",
        "export",
        "package_run",
    )


def test_v2_pipeline_writes_run_package_after_fusion(tmp_path: Path) -> None:
    summary = run_public_stage(_config(tmp_path), "fuse_elements")

    assert summary["status"] == "ok"
    package_path = Path(summary["artifacts"]["run_package"])
    assert package_path.is_file()
    payload = json.loads(package_path.read_text(encoding="utf-8"))
    assert payload["schema"] == "drawai.run_package.v1"
    assert payload["elements"]


def test_fusion_does_not_write_v2_derived_refinement_artifact_when_refine_enabled(
    tmp_path: Path,
) -> None:
    summary = run_public_stage(_config(tmp_path, refine_enabled=None), "fuse_elements")

    assert summary["status"] == "ok"
    paths = prepare_artifact_paths(tmp_path / "out")
    assert not paths.element_analysis_json.exists()


def test_refine_disabled_allows_deterministic_skip_trace(tmp_path: Path) -> None:
    summary = run_public_stage(_config(tmp_path, refine_enabled=False), "refine_elements")

    assert summary["status"] == "ok"
    trace = json.loads(Path(summary["artifacts"]["v2_refine_trace"]).read_text(encoding="utf-8"))
    assert trace["status"] == "skipped"
    assert trace["provider"] == "codex_element_refiner"


def test_refine_enabled_requires_refinement_artifact(tmp_path: Path) -> None:
    summary = run_public_stage(_config(tmp_path, refine_enabled=None), "refine_elements")

    assert summary["status"] == "failed"
    assert summary["failed_stage"] == "refine_elements"
    assert "Codex element refinement analysis" in summary["exception"]["message"]


def test_public_refine_stage_preserves_existing_codex_artifact(tmp_path: Path) -> None:
    config = _config(tmp_path, refine_enabled=None)
    paths = prepare_artifact_paths(tmp_path / "out")
    _write_fixture_refinement_artifact(paths)
    stale_v2_export = paths.element_analysis_dir / "element_plans.v2.json"
    stale_v2_export.write_text('{"schema":"stale"}', encoding="utf-8")

    summary = run_public_stage(config, "refine_elements")

    assert summary["status"] == "ok"
    trace = json.loads(paths.v2_refine_trace_json.read_text(encoding="utf-8"))
    assert trace["status"] == "agent_refined"
    assert not stale_v2_export.exists()


def test_refine_stage_consumes_existing_codex_artifact(tmp_path: Path) -> None:
    config = _config(tmp_path, refine_enabled=None)
    fusion_summary = run_public_stage(config, "fuse_elements")
    assert fusion_summary["status"] == "ok"

    paths = prepare_artifact_paths(tmp_path / "out")
    _write_fixture_refinement_artifact(paths)
    stale_v2_export = paths.element_analysis_dir / "element_plans.v2.json"
    stale_v2_export.write_text('{"schema":"stale"}', encoding="utf-8")

    summary = run_drawai_pipeline_from_stage(config, "refine_elements", to_stage="refine_elements")

    assert summary["status"] == "ok"
    trace = json.loads(paths.v2_refine_trace_json.read_text(encoding="utf-8"))
    assert trace["status"] == "agent_refined"
    package = json.loads(paths.run_package_json.read_text(encoding="utf-8"))
    assert package["metadata"]["last_stage"] == "refine_elements"
    assert package["elements"][0]["review_status"] == "agent_refined"
    assert not stale_v2_export.exists()


def test_refine_stage_translates_boxir_compat_ids_to_source_candidate_ids(
    tmp_path: Path,
) -> None:
    config = _config(tmp_path, refine_enabled=None)
    fusion_summary = run_public_stage(config, "fuse_elements")
    assert fusion_summary["status"] == "ok"

    paths = prepare_artifact_paths(tmp_path / "out")
    _write_compat_id_refinement_artifact(paths)

    summary = run_drawai_pipeline_from_stage(config, "refine_elements", to_stage="refine_elements")

    assert summary["status"] == "ok"
    package = json.loads(paths.run_package_json.read_text(encoding="utf-8"))
    assert package["elements"][0]["element_id"] == "E001"
    assert package["elements"][0]["source_candidate_ids"] == ["ocr:T001"]


def test_refine_stage_translates_top_level_removal_compat_ids() -> None:
    analysis = {
        "schema": "drawai.codex_element_analysis.v1",
        "elements": [
            {
                "element_id": "E001",
                "source_candidate_ids": ["E001"],
                "refinement_action": "unchanged",
                "category": "svg_self_draw",
                "confidence": "high",
                "visual_role": "text",
                "reason": "Keep text.",
                "bbox": [4, 5, 20, 14],
                "type": "text",
            }
        ],
        "removal_records": [
            {
                "box_id": "E002",
                "source_candidate_ids": ["E002"],
                "refinement_action": "merged",
                "reason": "Duplicate parser output.",
            }
        ],
    }
    plans = (
        ElementPlan(
            element_id="E001",
            source_candidate_ids=("ocr:T001",),
            element_type="text",
            bbox=(4, 5, 16, 9),
            geometry={"kind": "bbox", "bbox": [4, 5, 20, 14]},
            z_order=0,
            confidence="high",
            processing_intent=ProcessingIntent(
                object_type="text",
                processing_type="svg_self_draw",
            ),
            review_status="pending",
            created_by_stage="fuse_elements",
            change_reason="fixture",
        ),
        ElementPlan(
            element_id="E002",
            source_candidate_ids=("sam3:B113",),
            element_type="icon",
            bbox=(20, 5, 10, 10),
            geometry={"kind": "bbox", "bbox": [20, 5, 30, 15]},
            z_order=1,
            confidence="high",
            processing_intent=ProcessingIntent(
                object_type="icon",
                processing_type="svg_self_draw",
            ),
            review_status="pending",
            created_by_stage="fuse_elements",
            change_reason="fixture",
        ),
    )

    translated = _translate_compat_analysis_source_ids(analysis, plans)

    assert translated["elements"][0]["source_candidate_ids"] == ["ocr:T001"]
    assert translated["removal_records"][0]["source_candidate_ids"] == ["sam3:B113"]


def test_refine_expected_sources_can_be_limited_to_exposed_compat_plans() -> None:
    plans = (
        ElementPlan(
            element_id="E001",
            source_candidate_ids=("ocr:T001",),
            element_type="text",
            bbox=(4, 5, 16, 9),
            geometry={"kind": "bbox", "bbox": [4, 5, 20, 14]},
            z_order=0,
            confidence="high",
            processing_intent=ProcessingIntent(
                object_type="text",
                processing_type="svg_self_draw",
            ),
            review_status="pending",
            created_by_stage="fuse_elements",
            change_reason="fixture",
        ),
        ElementPlan(
            element_id="E002",
            source_candidate_ids=("sam3:B113",),
            element_type="icon",
            bbox=(20, 5, 10, 10),
            geometry={"kind": "bbox", "bbox": [20, 5, 30, 15]},
            z_order=1,
            confidence="high",
            processing_intent=ProcessingIntent(
                object_type="icon",
                processing_type="crop_nobg",
            ),
            review_status="pending",
            created_by_stage="fuse_elements",
            change_reason="fixture",
        ),
    )

    assert _refinement_expected_source_candidate_ids(plans, {"E002"}) == {"sam3:B113"}

    refined_icon = replace(plans[1], review_status="agent_refined")
    merged = _merge_refined_plans_with_unexposed(plans, (refined_icon,), {"E002"})

    assert [(plan.element_id, plan.review_status, plan.z_order) for plan in merged] == [
        ("E001", "pending", 0),
        ("E002", "agent_refined", 1),
    ]


def test_export_refuses_failed_asset_by_default(tmp_path: Path) -> None:
    config = _config(tmp_path)
    summary = run_drawai_pipeline_from_stage(
        config,
        "prepare",
        to_stage="compose_svg",
        svg_invoker=_fake_svg_invoker(),
    )
    assert summary["status"] == "ok"

    root = Path(summary["output_dir"])
    package_path = root / "elements" / "E001" / "asset_package.json"
    payload = json.loads(package_path.read_text(encoding="utf-8"))
    payload["status"] = "failed"
    payload["failure"] = "forced failure"
    package_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    export_summary = run_drawai_pipeline_from_stage(config, "export", to_stage="export")

    assert export_summary["status"] == "failed"
    assert export_summary["failed_stage"] == "export"
    report = json.loads((root / "reports" / "svg_to_ppt_export_report.json").read_text(encoding="utf-8"))
    assert report["failure_class"] == "v2_failed_assets"
    assert report["failed_assets"][0]["element_id"] == "E001"


def test_failed_export_clears_previous_export_outputs(tmp_path: Path) -> None:
    config = _config(tmp_path)
    compose_summary = run_drawai_pipeline_from_stage(
        config,
        "prepare",
        to_stage="compose_svg",
        svg_invoker=_fake_svg_invoker(),
    )
    assert compose_summary["status"] == "ok"

    export_summary = run_drawai_pipeline_from_stage(config, "export", to_stage="export")
    assert export_summary["status"] == "ok"

    root = Path(export_summary["output_dir"])
    package_path = root / "drawai_package.json"
    package = json.loads(package_path.read_text(encoding="utf-8"))
    assert "export_outputs" in package

    asset_path = root / "elements" / "E001" / "asset_package.json"
    asset_payload = json.loads(asset_path.read_text(encoding="utf-8"))
    asset_payload["status"] = "failed"
    asset_payload["failure"] = "forced failure after successful export"
    asset_path.write_text(json.dumps(asset_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    failed_summary = run_drawai_pipeline_from_stage(config, "export", to_stage="export")

    assert failed_summary["status"] == "failed"
    package = json.loads(package_path.read_text(encoding="utf-8"))
    assert package["metadata"]["last_stage"] == "export"
    assert "export_outputs" not in package
    assert package["compose_outputs"]["semantic_svg"] == "svg/semantic.svg"


def test_svg_to_ppt_failure_clears_previous_export_outputs(tmp_path: Path) -> None:
    config = _config(tmp_path, export_pptx=True)
    compose_summary = run_drawai_pipeline_from_stage(
        config,
        "prepare",
        to_stage="compose_svg",
        svg_invoker=_fake_svg_invoker(),
    )
    assert compose_summary["status"] == "ok"

    def successful_compiler(svg_path: Path, output_pptx: Path):
        output_pptx.write_bytes(b"pptx")
        return {"backend": "drawai_native_shapes", "editable_surface": "native_shapes"}

    export_summary = run_drawai_pipeline_from_stage(
        config,
        "export",
        to_stage="export",
        svg_to_ppt_compiler=successful_compiler,
    )
    assert export_summary["status"] == "ok"

    root = Path(export_summary["output_dir"])
    package_path = root / "drawai_package.json"
    package = json.loads(package_path.read_text(encoding="utf-8"))
    assert "export_outputs" in package

    def missing_pptx_compiler(svg_path: Path, output_pptx: Path):
        return {"backend": "drawai_native_shapes", "editable_surface": "native_shapes"}

    failed_summary = run_drawai_pipeline_from_stage(
        config,
        "export",
        to_stage="export",
        svg_to_ppt_compiler=missing_pptx_compiler,
    )

    assert failed_summary["status"] == "failed"
    package = json.loads(package_path.read_text(encoding="utf-8"))
    assert package["metadata"]["last_stage"] == "export"
    assert "export_outputs" not in package
    assert package["compose_outputs"]["semantic_svg"] == "svg/semantic.svg"


def test_compose_svg_uses_svg_generation_loop(tmp_path: Path) -> None:
    config = _config(tmp_path)
    calls: list[dict[str, object]] = []

    summary = run_drawai_pipeline_from_stage(
        config,
        "prepare",
        to_stage="compose_svg",
        svg_invoker=_fake_svg_invoker(calls),
    )

    assert summary["status"] == "ok"
    assert calls
    root = Path(summary["output_dir"])
    semantic_svg = root / "svg" / "semantic.svg"
    assert "from fake invoker" in semantic_svg.read_text(encoding="utf-8")
    package = json.loads((root / "drawai_package.json").read_text(encoding="utf-8"))
    assert package["compose_outputs"]["semantic_svg"] == "svg/semantic.svg"
    assert package["compose_outputs"]["validation_report"] == "reports/svg_validation_report.json"


def test_direct_compose_refuses_pending_raster_assets(tmp_path: Path) -> None:
    config = _config(tmp_path)
    plan_summary = run_drawai_pipeline_from_stage(config, "prepare", to_stage="plan_assets")
    assert plan_summary["status"] == "ok"

    root = Path(plan_summary["output_dir"])
    package_path = root / "drawai_package.json"
    package = json.loads(package_path.read_text(encoding="utf-8"))
    package["elements"][0]["element_type"] = "picture"
    package["elements"][0]["processing_intent"]["object_type"] = "picture"
    package["elements"][0]["processing_intent"]["processing_type"] = "crop"
    package["asset_packages"][0]["processor_type"] = "crop"
    package["asset_packages"][0]["status"] = "pending"
    package["asset_packages"][0]["active_result"] = None
    package_path.write_text(json.dumps(package, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    asset_package_path = root / "elements" / "E001" / "asset_package.json"
    asset_package = json.loads(asset_package_path.read_text(encoding="utf-8"))
    asset_package["processor_type"] = "crop"
    asset_package["status"] = "pending"
    asset_package["active_result"] = None
    asset_package_path.write_text(json.dumps(asset_package, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    compose_summary = run_drawai_pipeline_from_stage(
        config,
        "compose_svg",
        to_stage="compose_svg",
        svg_invoker=_fake_svg_invoker(),
    )

    assert compose_summary["status"] == "failed"
    assert compose_summary["failed_stage"] == "compose_svg"
    assert "process_assets" in compose_summary["exception"]["message"]
    assert "E001:crop:pending" in compose_summary["exception"]["message"]


def test_compose_disabled_packages_run_without_svg_generation(tmp_path: Path) -> None:
    config = _config(tmp_path, compose_enabled=False)

    summary = run_public_stage(config, "all")

    assert summary["status"] == "ok"
    root = Path(summary["output_dir"])
    assert not (root / "svg" / "semantic.svg").exists()
    assert (root / "elements" / "E001" / "asset_package.json").is_file()
    validation_report = json.loads(
        (root / "reports" / "svg_validation_report.json").read_text(encoding="utf-8")
    )
    assert validation_report["status"] == "skipped"
    assert validation_report["skip_reason"] == "v2.compose.disabled"
    assert validation_report["semantic_svg"] is None
    package = json.loads((root / "drawai_package.json").read_text(encoding="utf-8"))
    assert package["metadata"]["last_stage"] == "package_run"
    assert package["compose_outputs"] == {
        "status": "skipped",
        "enabled": False,
        "skip_reason": "v2.compose.disabled",
        "validation_report": "reports/svg_validation_report.json",
    }
    assert package["export_outputs"]["status"] == "skipped"
    assert package["export_outputs"]["skip_reason"] == "v2.compose.disabled"


def test_export_records_v2_export_outputs_on_success(tmp_path: Path) -> None:
    config = _config(tmp_path)
    compose_summary = run_drawai_pipeline_from_stage(
        config,
        "prepare",
        to_stage="compose_svg",
        svg_invoker=_fake_svg_invoker(),
    )
    assert compose_summary["status"] == "ok"

    export_summary = run_drawai_pipeline_from_stage(config, "export", to_stage="export")

    assert export_summary["status"] == "ok"
    root = Path(export_summary["output_dir"])
    package = json.loads((root / "drawai_package.json").read_text(encoding="utf-8"))
    assert package["metadata"]["last_stage"] == "export"
    assert package["compose_outputs"]["semantic_svg"] == "svg/semantic.svg"
    assert package["export_outputs"]["report"] == "reports/svg_to_ppt_export_report.json"

    package_summary = run_drawai_pipeline_from_stage(config, "package_run", to_stage="package_run")
    assert package_summary["status"] == "ok"
    package = json.loads((root / "drawai_package.json").read_text(encoding="utf-8"))
    assert package["compose_outputs"]["semantic_svg"] == "svg/semantic.svg"
    assert package["export_outputs"]["report"] == "reports/svg_to_ppt_export_report.json"
