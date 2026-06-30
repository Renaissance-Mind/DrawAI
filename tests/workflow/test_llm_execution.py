from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from PIL import Image

from drawai import model_runtime
from drawai.workflow.agents import agent_preset_by_id
from drawai.workflow.llm_execution import (
    LLMExecutionError,
    LLMExecutionRequest,
    execute_llm_prompt,
    render_llm_prompt,
)


def test_llm_prompt_embeds_json_inputs_and_attaches_image_content(tmp_path: Path) -> None:
    run_root = tmp_path / "run"
    image_path = run_root / "nodes" / "input" / "runs" / "001" / "output" / "image.png"
    page_spec_path = run_root / "nodes" / "fuse" / "runs" / "001" / "output" / "page_spec.json"
    image_path.parent.mkdir(parents=True)
    page_spec_path.parent.mkdir(parents=True)
    Image.new("RGB", (8, 8), "white").save(image_path)
    page_spec_path.write_text(
        json.dumps(
            {
                "schema": "drawai.page_spec.v1",
                "page_id": "p1",
                "source": {"width_px": 8, "height_px": 8},
                "canvas": {"width_px": 8, "height_px": 8},
                "elements": [],
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    prompt = render_llm_prompt(
        agent_preset_by_id("page_spec_refine"),
        inputs=(
            {
                "path": "nodes/input/runs/001/output/image.png",
                "format_id": "drawai.image.v1",
                "type": "image",
                "source_node_id": "input",
                "source_port_id": "image",
                "description": "Original page image.",
            },
            {
                "path": "nodes/fuse/runs/001/output/page_spec.json",
                "format_id": "drawai.page_spec.v1",
                "type": "page_spec",
                "source_node_id": "fuse",
                "source_port_id": "page_spec",
                "description": "Fused PageSpec evidence.",
            },
        ),
        node_config={
            "node_id": "page_spec_refine",
            "reasoning_effort": "high",
            "wire_api": "chat_completions",
            "extra_body": {"reasoning": {"enabled": True}},
        },
        runtime_context={
            "workflow_run_root": run_root,
            "node_workdir": run_root / "nodes" / "page_spec_refine" / "runs" / "001",
            "attempt_id": "001",
        },
    )

    assert prompt.image_paths == (image_path,)
    assert "## 已连接输入内容" in prompt.text
    assert "Image content 已附加到这个 LLM request" in prompt.text
    assert '"schema": "drawai.page_spec.v1"' in prompt.text
    assert "Fused PageSpec evidence." in prompt.text
    assert "不要从磁盘读取 workflow files" in prompt.text
    assert "以 JSON content 返回 page_spec output" in prompt.text
    assert "Write path from Agent cwd" not in prompt.text
    assert "## 直接输出运行模式" in prompt.text
    assert "忽略任何要求你自己运行命令或创建文件的措辞" in prompt.text
    assert "紧凑且有效的 JSON/SVG" in prompt.text
    assert "不要使用 raster image elements" in prompt.text
    assert '{"drawai_passthrough_input": true}' in prompt.text
    assert "大型结构化输入" in prompt.text
    assert "extra_body" not in prompt.text
    assert "reasoning" not in prompt.text


def test_execute_llm_prompt_extracts_fenced_json_and_writes_declared_output(tmp_path: Path) -> None:
    run_root = tmp_path / "run"
    workdir = run_root / "nodes" / "page_spec_refine" / "runs" / "001"
    page_spec = {
        "schema": "drawai.page_spec.v1",
        "page_id": "p1",
        "source": {"width_px": 10, "height_px": 10},
        "canvas": {"width_px": 10, "height_px": 10},
        "elements": [],
    }
    prompt = render_llm_prompt(
        agent_preset_by_id("page_spec_refine"),
        inputs=(),
        node_config={"node_id": "page_spec_refine"},
        runtime_context={"workflow_run_root": run_root, "node_workdir": workdir, "attempt_id": "001"},
    )

    captured: dict[str, Any] = {}

    def invoker(**kwargs: Any) -> str:
        captured["runtime_config"] = kwargs["runtime_config"]
        captured["max_output_tokens"] = kwargs["max_output_tokens"]
        return "```json\n" + json.dumps(page_spec) + "\n```"

    result = execute_llm_prompt(
        LLMExecutionRequest(
            prompt=prompt,
            workdir=workdir,
            run_root=run_root,
            node_id="page_spec_refine",
            node_type="llm",
            runtime_config={"provider": "fake", "model_name": "fake-model"},
        ),
        invoke_model=invoker,
    )

    saved = json.loads((workdir / "output" / "page_spec.json").read_text(encoding="utf-8"))
    assert saved == page_spec
    assert result.provider_id == "openai_responses"
    assert result.prompt_path == workdir / "llm_prompt.md"
    assert result.stdout_path == workdir / "llm_response.txt"
    assert result.execution_manifest_path == workdir / "llm_execution.json"
    assert captured["runtime_config"]["direct_output"] is True
    assert captured["max_output_tokens"] == 32768


def test_execute_llm_prompt_rejects_truncated_json_instead_of_nested_fragment(tmp_path: Path) -> None:
    run_root = tmp_path / "run"
    workdir = run_root / "nodes" / "page_spec_refine" / "runs" / "001"
    prompt = render_llm_prompt(
        agent_preset_by_id("page_spec_refine"),
        inputs=(),
        node_config={"node_id": "page_spec_refine"},
        runtime_context={"workflow_run_root": run_root, "node_workdir": workdir, "attempt_id": "001"},
    )

    def invoker(**kwargs: Any) -> str:
        return '```json\n{"schema":"drawai.page_spec.v1","source":{"width_px":10,"height_px":10},"elements":['

    with pytest.raises(LLMExecutionError, match="complete parseable JSON"):
        execute_llm_prompt(
            LLMExecutionRequest(
                prompt=prompt,
                workdir=workdir,
                run_root=run_root,
                node_id="page_spec_refine",
                node_type="llm",
                runtime_config={"provider": "fake", "model_name": "fake-model"},
            ),
            invoke_model=invoker,
        )


def test_execute_llm_prompt_falls_back_to_matching_input_on_empty_model_output(tmp_path: Path) -> None:
    run_root = tmp_path / "run"
    workdir = run_root / "nodes" / "page_spec_refine" / "runs" / "001"
    source_path = run_root / "nodes" / "page_spec_fuse" / "runs" / "001" / "output" / "page_spec.json"
    source_path.parent.mkdir(parents=True)
    page_spec = {
        "schema": "drawai.page_spec.v1",
        "page_id": "p1",
        "source": {"width_px": 10, "height_px": 10},
        "canvas": {"width_px": 10, "height_px": 10},
        "elements": [],
    }
    source_path.write_text(json.dumps(page_spec), encoding="utf-8")
    prompt = render_llm_prompt(
        agent_preset_by_id("page_spec_refine"),
        inputs=(
            {
                "path": "nodes/page_spec_fuse/runs/001/output/page_spec.json",
                "format_id": "drawai.page_spec.v1",
                "type": "page_spec",
                "source_node_id": "page_spec_fuse",
                "source_port_id": "page_spec",
                "description": "Fused PageSpec evidence.",
            },
        ),
        node_config={"node_id": "page_spec_refine"},
        runtime_context={"workflow_run_root": run_root, "node_workdir": workdir, "attempt_id": "001"},
    )

    def invoker(**kwargs: Any) -> str:
        raise model_runtime.ModelRuntimeError("model returned no text output")

    execute_llm_prompt(
        LLMExecutionRequest(
            prompt=prompt,
            workdir=workdir,
            run_root=run_root,
            node_id="page_spec_refine",
            node_type="llm",
            runtime_config={"provider": "fake", "model_name": "fake-model"},
        ),
        invoke_model=invoker,
    )

    saved = json.loads((workdir / "output" / "page_spec.json").read_text(encoding="utf-8"))
    trace = (workdir / "llm_trace.jsonl").read_text(encoding="utf-8")
    assert saved == page_spec
    assert '"type": "llm_fallback"' in trace


def test_execute_llm_prompt_honors_matching_input_passthrough_sentinel(tmp_path: Path) -> None:
    run_root = tmp_path / "run"
    workdir = run_root / "nodes" / "page_spec_refine" / "runs" / "001"
    source_path = run_root / "nodes" / "page_spec_fuse" / "runs" / "001" / "output" / "page_spec.json"
    source_path.parent.mkdir(parents=True)
    page_spec = {
        "schema": "drawai.page_spec.v1",
        "page_id": "p1",
        "source": {"width_px": 10, "height_px": 10},
        "canvas": {"width_px": 10, "height_px": 10},
        "elements": [],
    }
    source_path.write_text(json.dumps(page_spec), encoding="utf-8")
    prompt = render_llm_prompt(
        agent_preset_by_id("page_spec_refine"),
        inputs=(
            {
                "path": "nodes/page_spec_fuse/runs/001/output/page_spec.json",
                "format_id": "drawai.page_spec.v1",
                "type": "page_spec",
                "source_node_id": "page_spec_fuse",
                "source_port_id": "page_spec",
                "description": "Fused PageSpec evidence.",
            },
        ),
        node_config={"node_id": "page_spec_refine"},
        runtime_context={"workflow_run_root": run_root, "node_workdir": workdir, "attempt_id": "001"},
    )

    captured: dict[str, Any] = {}

    def invoker(**kwargs: Any) -> str:
        captured["max_output_tokens"] = kwargs["max_output_tokens"]
        return '{"drawai_passthrough_input": true}'

    execute_llm_prompt(
        LLMExecutionRequest(
            prompt=prompt,
            workdir=workdir,
            run_root=run_root,
            node_id="page_spec_refine",
            node_type="llm",
            runtime_config={"provider": "fake", "model_name": "fake-model"},
        ),
        invoke_model=invoker,
    )

    saved = json.loads((workdir / "output" / "page_spec.json").read_text(encoding="utf-8"))
    trace = (workdir / "llm_trace.jsonl").read_text(encoding="utf-8")
    assert saved == page_spec
    assert captured["max_output_tokens"] == 2048
    assert "model_requested_matching_input_passthrough" in trace


def test_execute_llm_prompt_extracts_json_wrapped_svg_and_writes_declared_output(tmp_path: Path) -> None:
    run_root = tmp_path / "run"
    workdir = run_root / "nodes" / "svg_compose" / "runs" / "001"
    svg = '<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"></svg>'
    prompt = render_llm_prompt(
        agent_preset_by_id("svg_generation"),
        inputs=(),
        node_config={"node_id": "svg_compose"},
        runtime_context={"workflow_run_root": run_root, "node_workdir": workdir, "attempt_id": "001"},
    )

    def invoker(**kwargs: Any) -> str:
        assert kwargs["image_paths"] == ()
        assert "以 SVG content 返回 semantic_svg output" in kwargs["prompt"]
        return json.dumps({"svg": svg})

    execute_llm_prompt(
        LLMExecutionRequest(
            prompt=prompt,
            workdir=workdir,
            run_root=run_root,
            node_id="svg_compose",
            node_type="llm",
            runtime_config={"provider": "fake", "model_name": "fake-model"},
        ),
        invoke_model=invoker,
    )

    assert (workdir / "output" / "semantic.svg").read_text(encoding="utf-8") == svg + "\n"


def test_execute_llm_prompt_removes_svg_raster_image_elements(
    tmp_path: Path,
) -> None:
    run_root = tmp_path / "run"
    workdir = run_root / "nodes" / "svg_compose" / "runs" / "001"
    prompt = render_llm_prompt(
        agent_preset_by_id("svg_generation"),
        inputs=(),
        node_config={"node_id": "svg_compose"},
        runtime_context={"workflow_run_root": run_root, "node_workdir": workdir, "attempt_id": "001"},
    )

    def invoker(**kwargs: Any) -> str:
        return (
            '<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10">'
            '<image href="assets/E001/crop.png" x="0" y="0" width="2" height="2"/>'
            '<image href="assets/MISSING/crop.png" x="2" y="2" width="2" height="2"/>'
            '<rect x="4" y="4" width="2" height="2"/>'
            "</svg>"
        )

    execute_llm_prompt(
        LLMExecutionRequest(
            prompt=prompt,
            workdir=workdir,
            run_root=run_root,
            node_id="svg_compose",
            node_type="llm",
            runtime_config={"provider": "fake", "model_name": "fake-model"},
        ),
        invoke_model=invoker,
    )

    saved = (workdir / "output" / "semantic.svg").read_text(encoding="utf-8")
    assert "assets/E001/crop.png" not in saved
    assert "assets/MISSING/crop.png" not in saved
    assert "<image" not in saved
    assert "<rect" in saved


def test_execute_llm_prompt_repairs_truncated_svg_at_last_complete_tag(tmp_path: Path) -> None:
    run_root = tmp_path / "run"
    workdir = run_root / "nodes" / "svg_compose" / "runs" / "001"
    prompt = render_llm_prompt(
        agent_preset_by_id("svg_generation"),
        inputs=(),
        node_config={"node_id": "svg_compose"},
        runtime_context={"workflow_run_root": run_root, "node_workdir": workdir, "attempt_id": "001"},
    )

    def invoker(**kwargs: Any) -> str:
        return (
            '<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10">'
            '<g id="kept"><rect x="1" y="1" width="2" height="2"/>'
            '<line x1="0" y1="0" x2='
        )

    execute_llm_prompt(
        LLMExecutionRequest(
            prompt=prompt,
            workdir=workdir,
            run_root=run_root,
            node_id="svg_compose",
            node_type="llm",
            runtime_config={"provider": "fake", "model_name": "fake-model"},
        ),
        invoke_model=invoker,
    )

    saved = (workdir / "output" / "semantic.svg").read_text(encoding="utf-8")
    assert '<g id="kept">' in saved
    assert "<rect" in saved
    assert saved.rstrip().endswith("</g></svg>")
