from __future__ import annotations

import pytest

from drawai.workflow.agents import (
    agent_preset_by_id,
    custom_agent_preset,
    default_agent_provider_registry,
    render_agent_prompt,
    run0_agent_preset,
    svg_agent_preset,
)


def test_default_agent_provider_registry_keeps_provider_resource_limits_separate() -> None:
    registry = default_agent_provider_registry()

    assert registry["codex_sdk"].provider_id == "codex_sdk"
    assert registry["kimi_cli"].provider_id == "kimi_cli"
    assert registry["codex_sdk"].resource_key == "agent_provider:codex_sdk"
    assert registry["kimi_cli"].resource_key == "agent_provider:kimi_cli"
    assert registry["codex_sdk"].default_max_concurrent != registry["kimi_cli"].default_max_concurrent


def test_run0_agent_prompt_renders_inputs_and_output_contract() -> None:
    prompt = render_agent_prompt(
        run0_agent_preset(),
        inputs=(
            {
                "path": "nodes/fusion/runs/001/output/elements.json",
                "format_id": "drawai.element_plans.v1",
                "type": "element_plans",
                "source_node_id": "fusion",
                "source_port_id": "elements",
                "description": "Fused boxes from SAM and OCR.",
            },
        ),
        node_config={"provider_id": "codex_sdk", "reasoning_effort": "high"},
    )

    assert prompt.provider_id == "codex_sdk"
    assert prompt.preset_id == "run0_element_refine"
    assert "nodes/fusion/runs/001/output/elements.json" in prompt.text
    assert "Fused boxes from SAM and OCR." in prompt.text
    assert "output/elements.json" in prompt.text
    assert "drawai.element_plans.v1" in prompt.text
    assert "shell_command" not in prompt.text


def test_svg_agent_prompt_uses_same_agent_contract() -> None:
    prompt = render_agent_prompt(
        svg_agent_preset(),
        inputs=(
            {
                "path": "nodes/asset_planner/runs/001/output/elements.json",
                "format_id": "drawai.element_plans.v1",
                "type": "element_plans",
                "description": "Approved element plan.",
            },
            {
                "path": "nodes/asset_processors/runs/001/output/asset_packages.json",
                "format_id": "drawai.asset_packages.v1",
                "type": "asset_packages",
                "description": "Renderable crop and no-bg asset packages.",
            },
        ),
        node_config={"provider_id": "kimi_cli", "model": "kimi-k2"},
    )

    assert prompt.provider_id == "kimi_cli"
    assert prompt.outputs[0]["path"] == "output/semantic.svg"
    assert prompt.outputs[0]["format_id"] == "drawai.semantic_svg.v1"
    assert "nodes/asset_processors/runs/001/output/asset_packages.json" in prompt.text
    assert "output/semantic.svg" in prompt.text


def test_custom_agent_prompt_uses_configured_output_formats() -> None:
    preset = agent_preset_by_id("custom_agent")
    assert preset == custom_agent_preset()

    prompt = render_agent_prompt(
        preset,
        inputs=(
            {
                "path": "nodes/input/runs/latest/output/image.png",
                "format_id": "drawai.image.v1",
                "type": "image",
                "source_node_id": "input",
                "source_port_id": "image",
                "description": "Original uploaded image.",
            },
            {
                "path": "nodes/sam/runs/latest/output/candidates.json",
                "format_id": "drawai.element_candidates.v1",
                "type": "element_candidates",
                "source_node_id": "sam",
                "source_port_id": "candidates",
                "description": "SAM candidate boxes.",
            },
        ),
        node_config={
            "outputs": [
                {
                    "port_id": "asset_packages",
                    "path": "output/asset_packages.json",
                    "format_id": "drawai.asset_packages.v1",
                    "type": "asset_packages",
                    "description": "Custom generated assets.",
                }
            ],
            "prompt_fragments": "Use the image and candidates together.",
        },
    )

    assert prompt.preset_id == "custom_agent"
    assert prompt.outputs[0]["format_id"] == "drawai.asset_packages.v1"
    assert "nodes/input/runs/latest/output/image.png" in prompt.text
    assert "nodes/sam/runs/latest/output/candidates.json" in prompt.text
    assert "output/asset_packages.json" in prompt.text
    assert "Use the image and candidates together." in prompt.text


def test_agent_prompt_can_exclude_inputs_and_override_descriptions() -> None:
    prompt = render_agent_prompt(
        run0_agent_preset(),
        inputs=(
            {
                "path": "nodes/sam_parser/runs/001/output/candidates.json",
                "format_id": "drawai.element_candidates.v1",
                "type": "element_candidates",
                "description": "SAM parser candidates.",
            },
            {
                "path": "nodes/ocr_parser/runs/001/output/candidates.json",
                "format_id": "drawai.element_candidates.v1",
                "type": "element_candidates",
                "description": "OCR parser candidates.",
            },
        ),
        node_config={
            "input_overrides": {
                "nodes/sam_parser/runs/001/output/candidates.json": {
                    "description": "SAM candidates after an inserted Agent cleanup.",
                },
                "nodes/ocr_parser/runs/001/output/candidates.json": {
                    "include": False,
                },
            }
        },
    )

    assert "SAM candidates after an inserted Agent cleanup." in prompt.text
    assert "OCR parser candidates." not in prompt.text
    assert "nodes/ocr_parser/runs/001/output/candidates.json" not in prompt.text


def test_agent_prompt_uses_configured_outputs_and_task_prompt() -> None:
    prompt = render_agent_prompt(
        run0_agent_preset(),
        inputs=(
            {
                "path": "nodes/merge/runs/001/output/elements.json",
                "format_id": "drawai.element_plans.v1",
                "type": "element_plans",
                "description": "Merged boxes.",
            },
        ),
        node_config={
            "outputs": [
                {
                    "port_id": "elements",
                    "path": "output/refined_elements.json",
                    "format_id": "drawai.element_plans.v1",
                    "type": "element_plans",
                    "description": "UI-configured refined element plan file.",
                }
            ],
            "prompt_fragments": "Use the source image as visual truth and return JSON only.",
        },
    )

    assert "output/refined_elements.json" in prompt.text
    assert "UI-configured refined element plan file." in prompt.text
    assert "Use the source image as visual truth and return JSON only." in prompt.text


def test_agent_config_rejects_arbitrary_command_override() -> None:
    with pytest.raises(ValueError, match="shell_command"):
        render_agent_prompt(
            run0_agent_preset(),
            inputs=(),
            node_config={"shell_command": "rm -rf /"},
        )
