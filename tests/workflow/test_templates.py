from __future__ import annotations

from pathlib import Path

import pytest

from drawai.workflow.schema import WorkflowNode, WorkflowTemplate
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

    assert result.ok
    assert result.errors == ()


def test_default_template_contains_current_v2_nodes() -> None:
    template = default_drawai_workflow_template()
    node_ids = {node.node_id for node in template.nodes}

    assert {
        "input",
        "sam_parser",
        "ocr_parser",
        "fusion",
        "run0_agent",
        "asset_planner",
        "asset_processors",
        "svg_agent",
        "svg_to_ppt",
        "output",
    }.issubset(node_ids)


def test_run0_and_svg_are_agent_node_presets() -> None:
    template = default_drawai_workflow_template()
    nodes = {node.node_id: node for node in template.nodes}

    assert nodes["run0_agent"].node_type == "agent"
    assert nodes["svg_agent"].node_type == "agent"
    assert nodes["run0_agent"].config["provider_id"] == "codex_sdk"
    assert nodes["svg_agent"].config["provider_id"] == "codex_sdk"
    assert nodes["run0_agent"].config["preset_id"] == "run0_element_refine"
    assert nodes["svg_agent"].config["preset_id"] == "svg_generation"


def test_default_template_routes_svg_and_pptx_into_output() -> None:
    template = default_drawai_workflow_template()
    output_edges = {
        (edge.source_node_id, edge.source_port_id, edge.target_node_id, edge.target_port_id)
        for edge in template.edges
        if edge.target_node_id == "output"
    }

    assert ("svg_agent", "semantic_svg", "output", "deliverables") in output_edges
    assert ("svg_to_ppt", "pptx", "output", "deliverables") in output_edges


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


def test_save_workflow_template_rejects_invalid_template(tmp_path: Path) -> None:
    invalid = WorkflowTemplate(
        template_id="invalid",
        name="Invalid",
        nodes=(
            WorkflowNode(
                node_id="fusion",
                node_type="fusion",
                title="Fusion",
                inputs=default_drawai_workflow_template().nodes[3].inputs,
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
