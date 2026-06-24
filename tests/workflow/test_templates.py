from __future__ import annotations

import json
from pathlib import Path

import pytest

from drawai.workflow.schema import WorkflowNode, WorkflowPort, WorkflowTemplate
from drawai.workflow.agents import DEFAULT_AGENT_TIMEOUT_SECONDS, SVG_AGENT_TIMEOUT_SECONDS
from drawai.workflow.templates import (
    copy_builtin_template_to_workspace,
    copy_builtin_template,
    default_drawai_workflow_template,
    list_workflow_templates,
    load_workflow_template,
    load_workflow_template_by_id,
    save_workflow_template,
    user_workflow_template_path,
    workflow_templates_dir,
)
from drawai.workflow.validation import validate_workflow_template


def test_default_drawai_workflow_template_validates() -> None:
    template = default_drawai_workflow_template()

    result = validate_workflow_template(template)

    assert template.name == "Image-to-PPTX"
    assert result.ok
    assert result.errors == ()


def test_default_template_contains_pagespec_dag_nodes() -> None:
    template = default_drawai_workflow_template()
    node_ids = {node.node_id for node in template.nodes}

    assert node_ids == {
        "input",
        "sam_parse",
        "ocr_parse",
        "page_spec_fuse",
        "page_spec_refine",
        "asset_prepare",
        "svg_compose",
        "svg_to_ppt",
        "output",
    }


def test_builtin_processor_test_template_uses_asset_prepare_without_svg_compose() -> None:
    template = load_workflow_template_by_id(".", "processor_test_page_spec_assets")
    nodes = {node.node_id: node for node in template.nodes}

    assert "page_spec_refine" in nodes
    assert "asset_prepare" in nodes
    assert "svg_compose" not in nodes
    assert "svg_to_ppt" not in nodes
    assert nodes["page_spec_refine"].config["page_spec_processing_types"] == [
        "no_process",
        "crop",
        "crop_nobg",
        "image_generate",
        "image_edit",
    ]
    assert nodes["asset_prepare"].config["processor_id"] == "asset_prepare"
    assert nodes["asset_prepare"].config["stage"] == "process_assets"


def test_default_template_skips_human_review_node() -> None:
    template = default_drawai_workflow_template()

    assert "human_review" not in {node.node_type for node in template.nodes}


def test_default_template_exposes_sam_prompt_configuration_on_sam_parser() -> None:
    template = default_drawai_workflow_template()
    nodes = {node.node_id: node for node in template.nodes}

    prompts = nodes["sam_parse"].config["prompts"]

    assert prompts[0] == {
        "id": "arrow",
        "text": "arrow",
        "confidence_threshold": 0.3,
    }
    assert {prompt["id"] for prompt in prompts} >= {"content_box", "diagram", "icon", "picture"}


def test_default_template_uses_pagespec_processor_formats() -> None:
    template = default_drawai_workflow_template()
    nodes = {node.node_id: node for node in template.nodes}

    assert nodes["sam_parse"].node_type == "processor"
    assert nodes["sam_parse"].config["processor_id"] == "sam_parse"
    assert nodes["sam_parse"].outputs[0].types == ("page_spec",)
    assert nodes["sam_parse"].outputs[0].formats == ("drawai.page_spec.v1",)
    assert nodes["ocr_parse"].outputs[0].types == ("page_spec",)
    assert nodes["ocr_parse"].outputs[0].formats == ("drawai.page_spec.v1",)
    assert nodes["page_spec_fuse"].inputs[0].formats == ("drawai.page_spec.v1",)
    assert nodes["page_spec_fuse"].outputs[0].formats == ("drawai.page_spec.v1",)
    assert nodes["page_spec_refine"].node_type == "agent"
    assert nodes["page_spec_refine"].inputs[1].formats == ("drawai.page_spec.v1",)
    assert nodes["page_spec_refine"].outputs[0].formats == ("drawai.page_spec.v1",)
    assert nodes["page_spec_refine"].config["page_spec_processing_types"] == [
        "no_process",
        "crop",
        "crop_nobg",
        "image_edit",
    ]
    assert nodes["asset_prepare"].inputs[1].types == ("page_spec",)
    assert nodes["asset_prepare"].outputs[0].types == ("page_spec",)
    assert nodes["svg_compose"].node_type == "agent"
    assert nodes["svg_compose"].inputs[1].types == ("page_spec",)
    assert nodes["svg_compose"].outputs[0].formats == ("drawai.semantic_svg.v1",)
    assert nodes["svg_compose"].outputs[0].description.startswith("deliverable;")
    assert "Materialized PageSpec" in nodes["svg_compose"].inputs[1].description
    assert "crop_nobg" in nodes["page_spec_refine"].inputs[0].description


def test_default_template_gives_svg_compose_longer_timeout() -> None:
    template = default_drawai_workflow_template()
    nodes = {node.node_id: node for node in template.nodes}

    assert nodes["page_spec_refine"].config["timeout_seconds"] == DEFAULT_AGENT_TIMEOUT_SECONDS
    assert nodes["svg_compose"].config["timeout_seconds"] == SVG_AGENT_TIMEOUT_SECONDS


def test_default_template_routes_svg_and_pptx_into_output() -> None:
    template = default_drawai_workflow_template()
    output_edges = {
        (edge.source_node_id, edge.source_port_id, edge.target_node_id, edge.target_port_id)
        for edge in template.edges
        if edge.target_node_id == "output"
    }

    assert ("svg_compose", "semantic_svg", "output", "deliverables") in output_edges
    assert ("svg_to_ppt", "pptx", "output", "deliverables") in output_edges


def test_default_template_routes_page_spec_through_assets_and_svg() -> None:
    template = default_drawai_workflow_template()
    nodes = {node.node_id: node for node in template.nodes}
    edges = {
        (edge.source_node_id, edge.source_port_id, edge.target_node_id, edge.target_port_id)
        for edge in template.edges
    }

    assert "page-spec-svg-draft" not in nodes["svg_compose"].config["drawai_tools"]
    assert "page-spec-assets" in nodes["svg_compose"].config["drawai_tools"]
    assert "svg-validate" in nodes["svg_compose"].config["drawai_tools"]
    assert ("input", "image", "sam_parse", "image") in edges
    assert ("input", "image", "ocr_parse", "image") in edges
    assert ("input", "image", "asset_prepare", "image") in edges
    assert ("sam_parse", "sam_page_spec", "page_spec_fuse", "sam_page_spec") in edges
    assert ("ocr_parse", "ocr_page_spec", "page_spec_fuse", "ocr_page_spec") in edges
    assert ("page_spec_fuse", "page_spec", "page_spec_refine", "page_spec") in edges
    assert ("page_spec_refine", "page_spec", "asset_prepare", "page_spec") in edges
    assert ("asset_prepare", "page_spec", "svg_compose", "page_spec") in edges
    assert ("asset_prepare", "page_spec", "svg_to_ppt", "page_spec") in edges


def test_workflow_template_paths_are_under_ignored_workbench_dir(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"

    assert workflow_templates_dir(workspace) == workspace / ".drawai" / "workflows"
    assert (
        user_workflow_template_path(workspace, "custom")
        == workspace / ".drawai" / "workflows" / "custom.json"
    )


def test_workflow_template_local_dir_is_gitignored() -> None:
    repo_root = Path(__file__).parents[2]

    gitignore = (repo_root / ".gitignore").read_text(encoding="utf-8")

    assert ".drawai/" in gitignore.splitlines()


def test_copy_builtin_template_returns_editable_custom_template() -> None:
    copied = copy_builtin_template("default_drawai_dag", name="My DAG")

    assert copied.template_id.startswith("custom_")
    assert copied.name == "My DAG"
    assert copied.defaults["source_template_id"] == "default_drawai_dag"
    assert validate_workflow_template(copied).ok


def test_save_and_load_workflow_template_round_trip(tmp_path: Path) -> None:
    copied = copy_builtin_template("default_drawai_dag", name="My Editable DAG")

    path = save_workflow_template(tmp_path, copied)
    loaded = load_workflow_template(path)

    assert path == user_workflow_template_path(tmp_path, copied.template_id)
    assert loaded.to_dict() == copied.to_dict()


def test_load_workflow_template_normalizes_legacy_asset_refine_title(tmp_path: Path) -> None:
    payload = _legacy_agent_template_payload()
    payload["nodes"][0]["title"] = "Run0 Agent"
    path = user_workflow_template_path(tmp_path, payload["template_id"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")

    loaded = load_workflow_template(path)
    nodes = {node.node_id: node for node in loaded.nodes}

    assert nodes["run0_agent"].title == "Asset Refine Agent"


def test_load_workflow_template_upgrades_legacy_agent_default_prompts(tmp_path: Path) -> None:
    payload = _legacy_agent_template_payload()
    for node in payload["nodes"]:
        if node["node_id"] == "run0_agent":
            node["config"]["task"] = "Refine element bbox, size, and type. Preserve IDs unless merge/delete is declared."
            node["config"]["constraints"] = []
        if node["node_id"] == "svg_agent":
            node["config"]["prompt_fragments"] = "Generate an editable SVG using connected element plans and confirmed assets."
            node["config"].pop("task", None)
            node["config"].pop("constraints", None)
    path = user_workflow_template_path(tmp_path, payload["template_id"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")

    loaded = load_workflow_template(path)
    nodes = {node.node_id: node for node in loaded.nodes}

    assert "DrawAI asset post-processing and element-plans task." in nodes["run0_agent"].config["task"]
    assert nodes["run0_agent"].config["constraints"]
    assert "IMAGE VECTORIZATION TASK" in nodes["svg_agent"].config["task"]
    assert "prompt_fragments" not in nodes["svg_agent"].config
    assert nodes["svg_agent"].config["constraints"]


def test_save_workflow_template_rejects_invalid_template(tmp_path: Path) -> None:
    invalid = WorkflowTemplate(
        template_id="invalid",
        name="Invalid",
        nodes=(
            WorkflowNode(
                node_id="fusion",
                node_type="fusion",
                title="Fusion",
                inputs=(
                    WorkflowPort(
                        port_id="candidates",
                        label="Candidates",
                        types=("element_candidates",),
                    ),
                ),
            ),
        ),
        edges=(),
    )

    with pytest.raises(ValueError, match="required_input_unconnected"):
        save_workflow_template(tmp_path, invalid)

    assert not user_workflow_template_path(tmp_path, "invalid").exists()


def test_list_workflow_templates_includes_builtin_and_local_templates(tmp_path: Path) -> None:
    copied = copy_builtin_template("default_drawai_dag", name="Listed DAG")
    save_workflow_template(tmp_path, copied)

    templates = list_workflow_templates(tmp_path)
    ids = [template.template_id for template in templates]

    assert ids[0] == "default_drawai_dag"
    assert copied.template_id in ids


def test_load_workflow_template_by_id_loads_builtin_or_local_template(tmp_path: Path) -> None:
    copied = copy_builtin_template_to_workspace(
        tmp_path,
        "default_drawai_dag",
        name="Workspace Copy",
    )

    builtin = load_workflow_template_by_id(tmp_path, "default_drawai_dag")
    local = load_workflow_template_by_id(tmp_path, copied.template_id)

    assert builtin.defaults["builtin"] is True
    assert local.template_id == copied.template_id
    assert local.defaults["read_only"] is False


def _legacy_agent_template_payload() -> dict[str, object]:
    return {
        "schema": "drawai.workflow_template.v1",
        "template_id": "legacy_agent_template",
        "name": "Legacy Agent Template",
        "version": 1,
        "nodes": [
            {
                "node_id": "run0_agent",
                "node_type": "agent",
                "title": "Asset Refine Agent",
                "inputs": [],
                "outputs": [
                    {
                        "port_id": "analysis",
                        "label": "Element Analysis",
                        "types": ["element_analysis"],
                        "formats": ["drawai.codex_element_analysis.v1"],
                        "required": False,
                        "cardinality": "single",
                    }
                ],
                "config": {
                    "preset_id": "run0_element_refine",
                    "provider_id": "codex_sdk",
                    "outputs": [
                        {
                            "port_id": "analysis",
                            "path": "output/element_analysis.json",
                            "format_id": "drawai.codex_element_analysis.v1",
                            "type": "element_analysis",
                            "description": "Run0 refined asset/source analysis.",
                        }
                    ],
                },
            },
            {
                "node_id": "svg_agent",
                "node_type": "agent",
                "title": "SVG Agent",
                "inputs": [],
                "outputs": [
                    {
                        "port_id": "semantic_svg",
                        "label": "Semantic SVG",
                        "types": ["semantic_svg"],
                        "formats": ["drawai.semantic_svg.v1"],
                        "required": False,
                        "cardinality": "single",
                    }
                ],
                "config": {
                    "preset_id": "svg_generation",
                    "provider_id": "codex_sdk",
                    "outputs": [
                        {
                            "port_id": "semantic_svg",
                            "path": "output/semantic.svg",
                            "format_id": "drawai.semantic_svg.v1",
                            "type": "semantic_svg",
                            "description": "Editable semantic SVG rooted at an svg element.",
                        }
                    ],
                },
            },
        ],
        "edges": [],
        "defaults": {},
    }
