from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from drawai.workbench.agent_settings import WorkbenchAgentSettings
from drawai.workbench.runner import _workflow_template_with_agent_settings
from drawai.workflow.templates import load_workflow_template_by_id


DEFAULT_AGENT_PROVIDER_ID = "default"
AGENT_RUNTIME_KEYS = ("model", "profile", "fast", "timeout_seconds", "reasoning_effort")


def test_builtin_agent_nodes_follow_workbench_settings_by_default(tmp_path: Path) -> None:
    template = load_workflow_template_by_id(tmp_path / "workspace", "default_drawai_dag")
    original_nodes = {node.node_id: node for node in template.nodes}

    for node_id in ("page_spec_refine", "svg_compose"):
        config = original_nodes[node_id].config
        assert config["provider_id"] == DEFAULT_AGENT_PROVIDER_ID
        for key in AGENT_RUNTIME_KEYS:
            assert key not in config

    effective = _workflow_template_with_agent_settings(
        template,
        WorkbenchAgentSettings(
            selected_provider_id="hermes_acp",
            model="hermes-model",
            reasoning_effort="medium",
            fast=True,
            timeout_seconds=900,
        ),
        execution_mode="agent",
    )

    effective_nodes = {node.node_id: node for node in effective.nodes}
    for node_id in ("page_spec_refine", "svg_compose"):
        config = effective_nodes[node_id].config
        assert config["provider_id"] == "hermes_acp"
        assert config["model"] == "hermes-model"
        assert config["reasoning_effort"] == "medium"
        assert config["fast"] is True
        assert config["timeout_seconds"] == 900


def test_builtin_agent_nodes_use_one_hour_workbench_default(tmp_path: Path) -> None:
    template = load_workflow_template_by_id(tmp_path / "workspace", "default_drawai_dag")

    effective = _workflow_template_with_agent_settings(
        template,
        WorkbenchAgentSettings(),
        execution_mode="agent",
    )

    effective_nodes = {node.node_id: node for node in effective.nodes}
    for node_id in ("page_spec_refine", "svg_compose"):
        assert effective_nodes[node_id].config["timeout_seconds"] == 3600


def test_explicit_dag_agent_runtime_settings_win_over_workbench_settings(tmp_path: Path) -> None:
    template = load_workflow_template_by_id(tmp_path / "workspace", "default_drawai_dag")
    nodes = []
    for node in template.nodes:
        if node.node_id == "page_spec_refine":
            nodes.append(
                replace(
                    node,
                    config={
                        **dict(node.config),
                        "provider_id": "kimi_cli",
                        "model": "kimi-model",
                        "reasoning_effort": "low",
                        "timeout_seconds": 120,
                    },
                )
            )
        else:
            nodes.append(node)
    template = replace(template, nodes=tuple(nodes))

    effective = _workflow_template_with_agent_settings(
        template,
        WorkbenchAgentSettings(
            selected_provider_id="hermes_acp",
            model="hermes-model",
            reasoning_effort="medium",
            fast=True,
            timeout_seconds=900,
        ),
        execution_mode="agent",
    )

    effective_nodes = {node.node_id: node for node in effective.nodes}
    explicit_config = effective_nodes["page_spec_refine"].config
    assert explicit_config["provider_id"] == "kimi_cli"
    assert explicit_config["model"] == "kimi-model"
    assert explicit_config["reasoning_effort"] == "low"
    assert "fast" not in explicit_config
    assert explicit_config["timeout_seconds"] == 120

    default_config = effective_nodes["svg_compose"].config
    assert default_config["provider_id"] == "hermes_acp"
    assert default_config["model"] == "hermes-model"
    assert default_config["reasoning_effort"] == "medium"
    assert default_config["fast"] is True
    assert default_config["timeout_seconds"] == 900
