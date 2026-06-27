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
    assert registry["drawai_tool_agent"].provider_id == "drawai_tool_agent"
    assert registry["drawai_tool_agent"].label == "内置 Agent"
    assert registry["codex_sdk"].resource_key == "agent_provider:codex_sdk"
    assert registry["kimi_cli"].resource_key == "agent_provider:kimi_cli"
    assert registry["drawai_tool_agent"].resource_key == "agent_provider:drawai_tool_agent"
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
    assert "Absolute path: <workflow_run_root>/nodes/fusion/runs/001/output/elements.json" in prompt.text
    assert "From Agent cwd: nodes/fusion/runs/001/output/elements.json" in prompt.text
    assert "Fused boxes from SAM and OCR." in prompt.text
    assert "## Declared Output Files" in prompt.text
    assert "output/elements.json" in prompt.text
    assert "nodes/run0_agent/runs/<attempt_id>/output/elements.json" in prompt.text
    assert "Final absolute path: <workflow_run_root>/nodes/run0_agent/runs/<attempt_id>/output/elements.json" in prompt.text
    assert "## Built-in Script Files" in prompt.text
    assert "assets_visualization.py" in prompt.text
    assert "node_run.json" in prompt.text
    assert "## DrawAI Tools" in prompt.text
    assert "Tool `format`" in prompt.text
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
                "path": "nodes/input/runs/001/output/image.png",
                "format_id": "drawai.image.v1",
                "type": "image",
                "description": "Original page image.",
            },
            {
                "path": "nodes/asset_prepare/runs/001/output/page_spec.json",
                "format_id": "drawai.page_spec.v1",
                "type": "page_spec",
                "description": "Materialized PageSpec with raster materialization paths.",
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
    assert "nodes/asset_prepare/runs/001/output/page_spec.json" in prompt.text
    assert "output/semantic.svg" in prompt.text
    assert "semantic_0.svg, rendered_0.png, validation_report_0.json" in prompt.text
    assert "REFINE LOOP / DEFAULT 1 ROUND, MAX 2 ROUNDS" in prompt.text
    assert "Do not run a third refinement round" in prompt.text
    assert "A complete valid final SVG is better than an unfinished extra refinement" in prompt.text
    assert 'data-pb-formula-latex-b64' in prompt.text
    assert 'data-pb-formula-bbox="x y width height"' in prompt.text
    assert "Office Math" in prompt.text
    assert "Do not display raw LaTeX" in prompt.text
    assert "A formula includes standalone mathematical variables or symbols with subscripts, superscripts, accents, Greek letters, operators, or relation signs." in prompt.text
    assert "Do not flatten formula structure into plain text such as alphai, xi2, yhat, or theta0." in prompt.text
    assert "Formula SVG example" in prompt.text
    assert "label-formula-example" in prompt.text
    assert "\\alpha_i^2+\\beta_i=c_i" in prompt.text
    assert "baseline-shift=\"sub\"" in prompt.text
    assert "label-formula-delta-ae" not in prompt.text
    assert "\\Delta^\\phi_{AE}" not in prompt.text
    assert "semantic_3.svg" not in prompt.text
    assert "Do not look for unconnected OCR, template, layout, request, or parser files." in prompt.text
    assert "OCR boxes JSON" not in prompt.text
    assert "Template IR" not in prompt.text
    assert "Write each declared output exactly" in prompt.text


def test_svg_agent_prompt_filters_pagespec_tools_for_image_only_inputs() -> None:
    prompt = render_agent_prompt(
        svg_agent_preset(),
        inputs=(
            {
                "path": "nodes/input/runs/001/output/image.png",
                "format_id": "drawai.image.v1",
                "type": "image",
                "description": "Original page image.",
            },
        ),
        node_config={
            "node_id": "svg_agent",
            "drawai_tools": ["format", "page-spec-assets", "page-spec-svg-draft", "svg-validate"],
        },
    )

    assert "If the connected input list includes no PageSpec" in prompt.text
    assert "Tool `format`" in prompt.text
    assert "Tool `page-spec-assets`" not in prompt.text
    assert "Tool `page-spec-svg-draft`" not in prompt.text
    assert "Tool `svg-validate`" not in prompt.text
    assert "Rendered PNGs and per-round validation reports are optional in image-only runs" in prompt.text


def test_drawai_tool_agent_prompt_uses_same_agent_contract_with_tool_call_invocation() -> None:
    prompt = render_agent_prompt(
        svg_agent_preset(),
        inputs=(
            {
                "path": "nodes/input/runs/001/output/image.png",
                "format_id": "drawai.image.v1",
                "type": "image",
                "description": "Original page image.",
            },
            {
                "path": "nodes/asset_prepare/runs/001/output/page_spec.json",
                "format_id": "drawai.page_spec.v1",
                "type": "page_spec",
                "description": "Materialized PageSpec with crop/crop_nobg assets.",
            },
        ),
        node_config={
            "node_id": "svg_agent",
            "provider_id": "drawai_tool_agent",
            "model": "qwen3.7-plus",
            "drawai_tools": ["format", "page-spec-assets", "page-spec-svg-draft", "svg-validate"],
        },
    )

    assert prompt.provider_id == "drawai_tool_agent"
    assert "IMAGE VECTORIZATION TASK" in prompt.text
    assert "OVERALL SVG/PPT PROFILE" in prompt.text
    assert "Materialized PageSpec with crop/crop_nobg assets." in prompt.text
    assert "Use only the DrawAI tools listed here." in prompt.text
    assert "run_drawai_tool" in prompt.text
    assert 'run_drawai_tool({"tool_id": "page-spec-assets"' in prompt.text
    assert "page-spec-svg-draft" not in prompt.text
    assert "do not hand-write a complete SVG" not in prompt.text
    assert "Exact command prefix" not in prompt.text
    assert "Tool Runtime Contract" not in prompt.text
    assert "Direct Output Runtime Override" not in prompt.text


def test_page_spec_refine_prompt_defines_id_changes_and_validation() -> None:
    prompt = render_agent_prompt(
        agent_preset_by_id("page_spec_refine"),
        inputs=(
            {
                "path": "nodes/input/runs/001/output/image.png",
                "format_id": "drawai.image.v1",
                "type": "image",
                "description": "Original page image.",
            },
            {
                "path": "nodes/page_spec_fuse/runs/001/output/page_spec.json",
                "format_id": "drawai.page_spec.v1",
                "type": "page_spec",
                "description": "Fused PageSpec evidence.",
            },
        ),
        node_config={"node_id": "page_spec_refine"},
    )

    assert "The refined PageSpec elements array is the handoff" in prompt.text
    assert "no_process" in prompt.text
    assert "Use only the processing operations provided in this task prompt" in prompt.text
    assert "diagram" in prompt.text
    assert "Choose crop_nobg" not in prompt.text
    assert "Preserve stable ids" in prompt.text
    assert "\"adjusted\"" in prompt.text
    assert "format validate --format-id drawai.page_spec.v1" in prompt.text
    assert "Do not embed any other full schema" in prompt.text
    assert "kind=\"group\"" not in prompt.text
    assert "parent_id/children" not in prompt.text
    assert "element candidates" not in prompt.text
    assert "element plans" not in prompt.text


def test_page_spec_refine_prompt_uses_configured_processing_types() -> None:
    prompt = render_agent_prompt(
        agent_preset_by_id("page_spec_refine"),
        inputs=(),
        node_config={
            "node_id": "page_spec_refine",
            "page_spec_processing_types": ["no_process", "crop"],
        },
    )

    assert "### no_process" in prompt.text
    assert "### crop" in prompt.text
    assert "### crop_nobg" not in prompt.text
    assert "### chart_rebuild_reserved" not in prompt.text
    assert "### svg_self_draw" not in prompt.text


def test_page_spec_refine_prompt_uses_configured_operation_catalog() -> None:
    prompt = render_agent_prompt(
        agent_preset_by_id("page_spec_refine"),
        inputs=(),
        node_config={
            "node_id": "page_spec_refine",
            "page_spec_processing_types": ["no_process", "image_edit"],
            "page_spec_processing_operations": {
                "image_edit": {
                    "meaning": "Workspace edited image edit meaning.",
                    "choose_when": "Workspace edited image edit choose rule.",
                    "avoid_when": "Workspace edited image edit avoid rule.",
                }
            },
        },
    )

    assert "### image_edit" in prompt.text
    assert "Meaning: Workspace edited image edit meaning." in prompt.text
    assert "Choose when: Workspace edited image edit choose rule." in prompt.text
    assert "Do not choose when: Workspace edited image edit avoid rule." in prompt.text
    assert "Edit a source crop or existing image asset" not in prompt.text


def test_page_spec_refine_prompt_keeps_chart_rebuild_available_when_configured() -> None:
    prompt = render_agent_prompt(
        agent_preset_by_id("page_spec_refine"),
        inputs=(),
        node_config={
            "node_id": "page_spec_refine",
            "page_spec_processing_types": ["chart_rebuild_reserved"],
        },
    )

    assert "### chart_rebuild_reserved" in prompt.text
    assert "### no_process" not in prompt.text


def test_page_spec_refine_prompt_rejects_unknown_processing_type() -> None:
    with pytest.raises(ValueError, match="unsupported PageSpec processing type"):
        render_agent_prompt(
            agent_preset_by_id("page_spec_refine"),
            inputs=(),
            node_config={
                "node_id": "page_spec_refine",
                "page_spec_processing_types": ["no_process", "not_real"],
            },
        )


def test_page_spec_refine_drawai_tool_agent_prompt_requires_copy_file_first() -> None:
    prompt = render_agent_prompt(
        agent_preset_by_id("page_spec_refine"),
        inputs=(
            {
                "path": "nodes/input/runs/001/output/image.png",
                "format_id": "drawai.image.v1",
                "type": "image",
                "description": "Original page image.",
            },
            {
                "path": "nodes/page_spec_fuse/runs/001/output/page_spec.json",
                "format_id": "drawai.page_spec.v1",
                "type": "page_spec",
                "description": "Fused PageSpec evidence.",
            },
        ),
        node_config={
            "node_id": "page_spec_refine",
            "provider_id": "drawai_tool_agent",
        },
    )

    assert "the first file-producing action MUST be `copy_file`" in prompt.text
    assert "nodes/page_spec_fuse/runs/001/output/page_spec.json" in prompt.text
    assert "nodes/page_spec_refine/runs/<attempt_id>/output/page_spec.json" in prompt.text
    assert "Do not read the full connected PageSpec just to rewrite it" in prompt.text


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
