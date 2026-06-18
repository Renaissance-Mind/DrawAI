from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

from drawai.artifacts import DrawAiArtifactPaths, prepare_artifact_paths
from drawai.pipeline import run_drawai_pipeline_from_stage
from drawai.public_stages import PUBLIC_STAGE_ORDER, run_public_stage


def _config(tmp_path: Path, *, refine_enabled: bool | None = False) -> Path:
    image = tmp_path / "input.png"
    Image.new("RGB", (80, 40), "white").save(image)
    config = tmp_path / "config.yaml"
    v2_section = ""
    if refine_enabled is not None:
        v2_section = f"""
v2:
  refine:
    enabled: {str(refine_enabled).lower()}
"""
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
svg_to_ppt:
  enabled: true
  export_pptx: false
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
