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
                "path": "nodes/input/runs/001/output/image.png",
                "format_id": "drawai.image.v1",
                "type": "image",
                "source_node_id": "input",
                "source_port_id": "image",
                "description": "Original source image.",
            },
            {
                "path": "nodes/fusion/runs/001/output/elements.json",
                "format_id": "drawai.element_plans.v1",
                "type": "element_plans",
                "source_node_id": "fusion",
                "source_port_id": "elements",
                "description": "Fused boxes from SAM and OCR.",
            },
        ),
        node_config={
            "node_id": "run0_agent",
            "provider_id": "codex_sdk",
            "reasoning_effort": "high",
        },
    )

    assert prompt.provider_id == "codex_sdk"
    assert prompt.preset_id == "run0_element_refine"
    assert "# Run0 Element Refinement" not in prompt.text
    assert "## Agent Runtime Settings" in prompt.text
    assert "- Workflow run root: <workflow_run_root>" in prompt.text
    assert "- Current node workdir: <workflow_run_root>/nodes/run0_agent/runs/<attempt_id>" in prompt.text
    assert "DrawAI asset post-processing and element-plans task." in prompt.text
    assert "Task 1: refine the connected candidates into minimum independent assets." in prompt.text
    assert "## Connected Input Files" in prompt.text
    assert "nodes/input/runs/001/output/image.png" in prompt.text
    assert "Original source image." in prompt.text
    assert "nodes/fusion/runs/001/output/elements.json" in prompt.text
    assert "input_manifest.json" in prompt.text
    assert "Absolute path: <workflow_run_root>/nodes/fusion/runs/001/output/elements.json" in prompt.text
    assert "From Agent cwd: ../../../nodes/fusion/runs/001/output/elements.json" in prompt.text
    assert "Fused boxes from SAM and OCR." in prompt.text
    assert "## Declared Output Files" in prompt.text
    assert "output/elements.json" in prompt.text
    assert "nodes/run0_agent/runs/<attempt_id>/output/elements.json" in prompt.text
    assert "Final absolute path: <workflow_run_root>/nodes/run0_agent/runs/<attempt_id>/output/elements.json" in prompt.text
    assert "## Built-in Script Files" in prompt.text
    assert "assets_visualization.py" in prompt.text
    assert "node_run.json" in prompt.text
    assert "## Type And Format Contracts" in prompt.text
    assert "Type `image`" in prompt.text
    assert "Type `element_plans`" in prompt.text
    assert "Format `drawai.image.v1`" in prompt.text
    assert "Format `drawai.element_plans.v1`" in prompt.text
    assert "## Constraints" in prompt.text
    assert "Do not use MCP tools, apps, web search, memories, skills, hooks, or multi-agent delegation." in prompt.text
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
        node_config={"node_id": "svg_agent", "provider_id": "kimi_cli", "model": "kimi-k2"},
    )

    assert prompt.provider_id == "kimi_cli"
    assert "# SVG Generation" not in prompt.text
    assert "- Current node workdir: <workflow_run_root>/nodes/svg_agent/runs/<attempt_id>" in prompt.text
    assert "IMAGE VECTORIZATION TASK" in prompt.text
    assert "OVERALL SVG/PPT PROFILE" in prompt.text
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
                    "path": "custom/user_path.txt",
                    "format_id": "drawai.asset_packages.v1",
                    "type": "wrong_type",
                    "description": "Custom generated assets.",
                }
            ],
            "task": "Use the image and candidates together.",
            "constraints": [
                "Keep the output schema stable.",
                "Write only the configured output file.",
            ],
        },
    )

    assert prompt.preset_id == "custom_agent"
    assert prompt.outputs[0]["path"] == "output/asset_packages.json"
    assert prompt.outputs[0]["type"] == "asset_packages"
    assert prompt.outputs[0]["format_id"] == "drawai.asset_packages.v1"
    assert "nodes/input/runs/latest/output/image.png" in prompt.text
    assert "nodes/sam/runs/latest/output/candidates.json" in prompt.text
    assert "output/asset_packages.json" in prompt.text
    assert "Use the image and candidates together." in prompt.text
    assert "Keep the output schema stable." in prompt.text


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
            "task": "Use the source image as visual truth and return JSON only.",
            "constraints": "Return one JSON document.\nDo not add markdown fences.",
        },
    )

    assert "output/elements.json" in prompt.text
    assert "UI-configured refined element plan file." in prompt.text
    assert "Use the source image as visual truth and return JSON only." in prompt.text
    assert "- Return one JSON document." in prompt.text
    assert "- Do not add markdown fences." in prompt.text


def test_agent_prompt_keeps_legacy_prompt_fragments_as_task() -> None:
    prompt = render_agent_prompt(
        custom_agent_preset(),
        inputs=(),
        node_config={"prompt_fragments": "Legacy task text stays visible."},
    )

    assert "Legacy task text stays visible." in prompt.text
    assert "Treat every connected input file as explicit node context." in prompt.text


def test_agent_config_rejects_arbitrary_command_override() -> None:
    with pytest.raises(ValueError, match="shell_command"):
        render_agent_prompt(
            run0_agent_preset(),
            inputs=(),
            node_config={"shell_command": "rm -rf /"},
        )


def test_agent_output_paths_are_generated_from_port_and_format() -> None:
    prompt = render_agent_prompt(
        custom_agent_preset(),
        inputs=(),
        node_config={
            "outputs": [
                {
                    "port_id": "semantic_svg",
                    "path": "../user_supplied.svg",
                    "format_id": "drawai.semantic_svg.v1",
                    "type": "wrong_type",
                    "description": "SVG output.",
                },
                {
                    "port_id": "slide deck",
                    "path": "/tmp/user_supplied.pptx",
                    "format_id": "drawai.pptx.v1",
                    "type": "wrong_type",
                    "description": "PPTX output.",
                },
            ]
        },
    )

    assert prompt.outputs[0]["path"] == "output/semantic_svg.svg"
    assert prompt.outputs[0]["type"] == "semantic_svg"
    assert prompt.outputs[1]["path"] == "output/slide_deck.pptx"
    assert prompt.outputs[1]["type"] == "pptx"
