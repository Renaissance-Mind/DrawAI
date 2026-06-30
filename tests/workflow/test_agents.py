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
from drawai.workflow.agent_prompt_defaults import PAGE_SPEC_REFINE_TASK_ZH


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
    assert "## Agent 运行上下文" in prompt.text
    assert "- Workflow run root：<workflow_run_root>" in prompt.text
    assert "- 当前 node workdir：<workflow_run_root>/nodes/run0_agent/runs/<attempt_id>" in prompt.text
    assert "DrawAI asset post-processing and element-plans task." in prompt.text
    assert "Task 1: refine the connected candidates into minimum independent assets." in prompt.text
    assert "## 已连接输入文件" in prompt.text
    assert "nodes/input/runs/001/output/image.png" in prompt.text
    assert "Original source image." in prompt.text
    assert "nodes/fusion/runs/001/output/elements.json" in prompt.text
    assert "Absolute path：<workflow_run_root>/nodes/fusion/runs/001/output/elements.json" in prompt.text
    assert "From Agent cwd：nodes/fusion/runs/001/output/elements.json" in prompt.text
    assert "Fused boxes from SAM and OCR." in prompt.text
    assert "## 声明输出文件" in prompt.text
    assert "output/elements.json" in prompt.text
    assert "nodes/run0_agent/runs/<attempt_id>/output/elements.json" in prompt.text
    assert "最终 absolute path：<workflow_run_root>/nodes/run0_agent/runs/<attempt_id>/output/elements.json" in prompt.text
    assert "## 内置脚本文件" in prompt.text
    assert "assets_visualization.py" in prompt.text
    assert "node_run.json" in prompt.text
    assert "## DrawAI 工具" in prompt.text
    assert "Tool `format`" in prompt.text
    assert "## 类型和格式契约" in prompt.text
    assert "Type `image`" in prompt.text
    assert "Type `element_plans`" in prompt.text
    assert "Format `drawai.image.v1`" in prompt.text
    assert "Format `drawai.element_plans.v1`" in prompt.text
    assert "## 约束" in prompt.text
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
    assert "- 当前 node workdir：<workflow_run_root>/nodes/svg_agent/runs/<attempt_id>" in prompt.text
    assert "你需要完成位图矢量化任务。" in prompt.text
    assert "SVG/PPT 结构约束" in prompt.text
    assert "SVG 生成脚本 run-root path：nodes/svg_agent/runs/<attempt_id>/output/build_semantic_svg.py" in prompt.text
    assert "SVG 生成脚本 absolute path：<workflow_run_root>/nodes/svg_agent/runs/<attempt_id>/output/build_semantic_svg.py" in prompt.text
    assert prompt.outputs[0]["path"] == "output/semantic.svg"
    assert prompt.outputs[0]["format_id"] == "drawai.semantic_svg.v1"
    assert "nodes/asset_prepare/runs/001/output/page_spec.json" in prompt.text
    assert "output/semantic.svg" in prompt.text
    assert "semantic_<ROUND_INDEX>.svg" in prompt.text
    assert "rendered_<ROUND_INDEX>.png" in prompt.text
    assert "validation_report_<ROUND_INDEX>.json" in prompt.text
    assert "总共最多进行 5 轮迭代" in prompt.text
    assert "以最后一轮生成并通过校验的 semantic_<ROUND_INDEX>.svg 作为 accepted SVG" in prompt.text
    assert "把这个文件复制到当前 DAG 声明的最终 SVG 路径" in prompt.text
    assert "ELEMENT_RENDERERS" in prompt.text
    assert "draw_svg_<element_id_lower>()" in prompt.text
    assert "不要直接手改 semantic_*.svg。" in prompt.text
    assert "后不回写脚本" not in prompt.text
    assert 'data-pb-role="formula"' in prompt.text
    assert "不要把公式变成不可编辑图片" in prompt.text
    assert "semantic_3.svg" not in prompt.text
    assert "OCR boxes JSON" not in prompt.text
    assert "Template IR" not in prompt.text
    assert "每个声明输出都会列在下面" in prompt.text


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

    assert "SVG 生成脚本 run-root path：" not in prompt.text
    assert "Tool `format`" in prompt.text
    assert "Tool `page-spec-assets`" not in prompt.text
    assert "Tool `page-spec-svg-draft`" not in prompt.text
    assert "Tool `svg-validate`" not in prompt.text
    assert "page-spec-assets 返回的 href" in prompt.text


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
    assert "你需要完成位图矢量化任务。" in prompt.text
    assert "SVG/PPT 结构约束" in prompt.text
    assert "Materialized PageSpec with crop/crop_nobg assets." in prompt.text
    assert "只能使用下面列出的 DrawAI tools。" in prompt.text
    assert "run_drawai_tool" in prompt.text
    assert 'run_drawai_tool({"tool_id": "page-spec-assets"' in prompt.text
    assert 'run_drawai_tool({"tool_id": "page-spec-svg-draft"' not in prompt.text
    assert "do not hand-write a complete SVG" not in prompt.text
    assert "Agent cwd 下的精确命令前缀" not in prompt.text
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


def test_page_spec_refine_zh_prompt_uses_configured_processing_types() -> None:
    prompt = render_agent_prompt(
        agent_preset_by_id("page_spec_refine"),
        inputs=(),
        node_config={
            "node_id": "page_spec_refine",
            "task": PAGE_SPEC_REFINE_TASK_ZH,
            "page_spec_processing_types": ["no_process", "crop"],
        },
    )

    assert "DrawAI PageSpec 精修任务" in prompt.text
    assert "### no_process" in prompt.text
    assert "### crop" in prompt.text
    assert "### crop_nobg" not in prompt.text
    assert "### image_edit" not in prompt.text


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

    assert "第一步产生文件的 action 必须是 用 `copy_file`" in prompt.text
    assert "nodes/page_spec_fuse/runs/001/output/page_spec.json" in prompt.text
    assert "nodes/page_spec_refine/runs/<attempt_id>/output/page_spec.json" in prompt.text
    assert "不要为了重写而读取完整 connected PageSpec" in prompt.text


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
