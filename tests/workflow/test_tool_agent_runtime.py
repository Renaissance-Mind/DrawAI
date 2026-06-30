from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from drawai.tool_agent_runtime import invoke_drawai_tool_agent
from drawai.workflow.agent_execution import AgentExecutionRequest, execute_agent_prompt
from drawai.workflow.agents import agent_preset_by_id, render_agent_prompt


def test_drawai_tool_agent_loop_writes_file_through_tool(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    calls: list[dict[str, Any]] = []

    _install_fake_openai(
        monkeypatch,
        calls,
        [
            _tool_message(
                "write_file",
                {
                    "path": "output/result.json",
                    "content": '{"ok": true}\n',
                },
            ),
            _text_message("done"),
        ],
    )

    result = invoke_drawai_tool_agent(
        prompt="Write output/result.json.",
        task_name="unit.tool_agent",
        runtime_config={
            "provider": "drawai_tool_agent",
            "connection_id": "drawai_tool_agent",
            "model_name": "fake-model",
            "api_key": "fake-key",
            "wire_api": "chat_completions",
        },
        workspace_dir=tmp_path,
        repo_root=Path(__file__).resolve().parents[2],
        trace_path=tmp_path / "trace.jsonl",
    )

    assert result.final_text == "done"
    assert result.tool_calls == 1
    assert (tmp_path / "output" / "result.json").read_text(encoding="utf-8") == '{"ok": true}\n'
    assert calls[0]["tools"][0]["type"] == "function"
    assert any(message["role"] == "tool" for message in calls[1]["messages"])
    trace_text = (tmp_path / "trace.jsonl").read_text(encoding="utf-8")
    assert "tool_agent_tool_result" in trace_text
    assert "fake-key" not in trace_text


def test_agent_execution_uses_shared_agent_prompt_and_allows_manifest_image_href(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    calls: list[dict[str, Any]] = []
    run_root = tmp_path / "run"
    workdir = run_root / "nodes" / "svg_compose" / "runs" / "001"
    page_spec_path = run_root / "nodes" / "asset_prepare" / "runs" / "001" / "output" / "page_spec.json"
    crop_path = page_spec_path.parent / "assets" / "crops" / "plot.png"
    page_spec_path.parent.mkdir(parents=True, exist_ok=True)
    crop_path.parent.mkdir(parents=True, exist_ok=True)
    page_spec_path.write_text(
        json.dumps(
            {
                "schema": "drawai.page_spec.v1",
                "page_id": "p1",
                "source": {"width_px": 10, "height_px": 10},
                "canvas": {"width_px": 10, "height_px": 10},
                "elements": [
                    {
                        "id": "plot_1",
                        "type": "image",
                        "bbox": {"x": 1, "y": 1, "width": 8, "height": 8},
                        "build": {"processing_type": "crop"},
                        "materialization": {"path": "assets/crops/plot.png"},
                    }
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    crop_path.write_bytes(b"png")
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10">'
        '<image href="nodes/asset_prepare/runs/001/output/assets/crops/plot.png" x="1" y="1" width="8" height="8"/>'
        "</svg>\n"
    )
    output_path = "nodes/svg_compose/runs/001/output/semantic.svg"
    _install_fake_openai(
        monkeypatch,
        calls,
        [
            _tool_message("open_file", {"path": "nodes/asset_prepare/runs/001/output/page_spec.json"}),
            _tool_message("write_file", {"path": output_path, "content": svg}),
            _tool_message("finalize", {"summary": "wrote SVG with manifest-backed image href"}),
        ],
    )
    prompt = render_agent_prompt(
        agent_preset_by_id("svg_generation"),
        inputs=(
            {
                "path": "nodes/asset_prepare/runs/001/output/page_spec.json",
                "format_id": "drawai.page_spec.v1",
                "type": "page_spec",
                "source_node_id": "asset_prepare",
                "source_port_id": "page_spec",
                "description": "Materialized PageSpec with crop materialization paths.",
            },
        ),
        node_config={
            "node_id": "svg_compose",
            "provider_id": "drawai_tool_agent",
            "model": "fake-model",
            "api_key": "fake-key",
            "drawai_tools": ["format", "page-spec-assets", "page-spec-svg-draft", "svg-validate"],
        },
        runtime_context={"workflow_run_root": run_root, "node_workdir": workdir, "attempt_id": "001"},
    )

    result = execute_agent_prompt(
        AgentExecutionRequest(
            prompt=prompt,
            workdir=workdir,
            run_root=run_root,
            node_id="svg_compose",
            node_type="agent",
            runtime_config={"provider": "drawai_tool_agent", "model_name": "fake-model", "api_key": "fake-key"},
        ),
    )

    assert result.provider_id == "drawai_tool_agent"
    assert (workdir / "output" / "semantic.svg").read_text(encoding="utf-8") == svg
    assert (workdir / "output" / "build_semantic_svg.py").is_file()
    assert (
        'DECLARED_FINAL_SVG_RUN_ROOT_PATH = "nodes/svg_compose/runs/001/output/semantic.svg"'
        in (workdir / "output" / "build_semantic_svg.py").read_text(encoding="utf-8")
    )
    assert '<image href="nodes/asset_prepare/runs/001/output/assets/crops/plot.png"' in svg
    assert (workdir / "drawai_tool_agent_final_response.txt").read_text(encoding="utf-8") == "wrote SVG with manifest-backed image href"
    assert "你需要完成位图矢量化任务。" in prompt.text
    assert "SVG 生成脚本 run-root path：nodes/svg_compose/runs/001/output/build_semantic_svg.py" in prompt.text
    assert "ELEMENT_RENDERERS" in prompt.text
    assert "Materialized PageSpec with crop materialization paths." in prompt.text
    assert "run_drawai_tool" in prompt.text
    assert "copy_file" in prompt.text
    assert "append_file" in prompt.text
    assert "page-spec-svg-draft" not in prompt.text
    assert "do not hand-write a complete SVG" not in prompt.text
    assert "Exact command prefix" not in prompt.text
    assert "Tool Runtime Contract" not in prompt.text
    assert "fake-key" not in prompt.text
    assert "fake-key" not in calls[0]["messages"][1]["content"][0]["text"]
    request_manifest = (workdir / "agent_execution_request.json").read_text(encoding="utf-8")
    assert "fake-key" not in request_manifest


def test_drawai_tool_agent_stops_after_successful_finalize(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    calls: list[dict[str, Any]] = []
    _install_fake_openai(
        monkeypatch,
        calls,
        [
            _tool_message("write_file", {"path": "output/result.json", "content": '{"ok": true}\n'}),
            _tool_message("finalize", {"summary": "completed from finalize"}),
        ],
    )

    result = invoke_drawai_tool_agent(
        prompt="Write output/result.json and finalize.",
        task_name="unit.tool_agent.finalize",
        runtime_config={
            "provider": "drawai_tool_agent",
            "connection_id": "drawai_tool_agent",
            "model_name": "fake-model",
            "api_key": "fake-key",
            "wire_api": "chat_completions",
        },
        workspace_dir=tmp_path,
        repo_root=Path(__file__).resolve().parents[2],
        trace_path=tmp_path / "trace.jsonl",
        max_iterations=2,
    )

    assert result.final_text == "completed from finalize"
    assert result.iterations == 2
    assert len(calls) == 2


def test_drawai_tool_agent_appends_large_output_chunks(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    calls: list[dict[str, Any]] = []
    _install_fake_openai(
        monkeypatch,
        calls,
        [
            _tool_message("write_file", {"path": "output/page_spec.json", "content": ""}),
            _tool_message("append_file", {"path": "output/page_spec.json", "content": '{"schema":"drawai.page_spec.v1",'}),
            _tool_message("append_file", {"path": "output/page_spec.json", "content": '"elements":[]}\n'}),
            _tool_message("finalize", {"summary": "chunked page spec written"}),
        ],
    )

    result = invoke_drawai_tool_agent(
        prompt="Write a large output/page_spec.json in chunks.",
        task_name="unit.tool_agent.append_file",
        runtime_config={
            "provider": "drawai_tool_agent",
            "connection_id": "drawai_tool_agent",
            "model_name": "fake-model",
            "api_key": "fake-key",
            "wire_api": "chat_completions",
        },
        workspace_dir=tmp_path,
        repo_root=Path(__file__).resolve().parents[2],
        trace_path=tmp_path / "trace.jsonl",
        max_iterations=4,
    )

    assert result.final_text == "chunked page spec written"
    assert result.tool_calls == 4
    assert (
        tmp_path / "output" / "page_spec.json"
    ).read_text(encoding="utf-8") == '{"schema":"drawai.page_spec.v1","elements":[]}\n'
    tool_names = [tool["function"]["name"] for tool in calls[0]["tools"]]
    assert "append_file" in tool_names
    assert "append_file chunks" in calls[0]["messages"][0]["content"]


def test_drawai_tool_agent_copies_input_file_to_declared_output(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    calls: list[dict[str, Any]] = []
    source = tmp_path / "nodes" / "page_spec_fuse" / "runs" / "001" / "output" / "page_spec.json"
    source.parent.mkdir(parents=True)
    source.write_text('{"schema":"drawai.page_spec.v1","elements":[]}\n', encoding="utf-8")
    _install_fake_openai(
        monkeypatch,
        calls,
        [
            _tool_message(
                "copy_file",
                {
                    "source": "nodes/page_spec_fuse/runs/001/output/page_spec.json",
                    "path": "nodes/page_spec_refine/runs/001/output/page_spec.json",
                },
            ),
            _tool_message("finalize", {"summary": "copied and validated"}),
        ],
    )

    result = invoke_drawai_tool_agent(
        prompt="Copy the connected PageSpec to the declared output.",
        task_name="unit.tool_agent.copy_file",
        runtime_config={
            "provider": "drawai_tool_agent",
            "connection_id": "drawai_tool_agent",
            "model_name": "fake-model",
            "api_key": "fake-key",
            "wire_api": "chat_completions",
        },
        workspace_dir=tmp_path,
        repo_root=Path(__file__).resolve().parents[2],
        trace_path=tmp_path / "trace.jsonl",
        max_iterations=2,
    )

    copied = tmp_path / "nodes" / "page_spec_refine" / "runs" / "001" / "output" / "page_spec.json"
    assert result.final_text == "copied and validated"
    assert copied.read_text(encoding="utf-8") == source.read_text(encoding="utf-8")
    tool_names = [tool["function"]["name"] for tool in calls[0]["tools"]]
    assert "copy_file" in tool_names
    assert "prefer copy_file" in calls[0]["messages"][0]["content"]
    assert "For PageSpec refine tasks, copy the connected PageSpec" in calls[0]["messages"][0]["content"]
    trace_text = (tmp_path / "trace.jsonl").read_text(encoding="utf-8")
    assert "validate" in trace_text
    assert "Do not spend another turn rewriting the whole copied file." in trace_text


def test_page_spec_refine_auto_finalizes_after_successful_validation(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    calls: list[dict[str, Any]] = []
    source = tmp_path / "nodes" / "page_spec_fuse" / "runs" / "001" / "output" / "page_spec.json"
    output_path = "nodes/page_spec_refine/runs/001/output/page_spec.json"
    source.parent.mkdir(parents=True)
    source.write_text(
        json.dumps(
            {
                "schema": "drawai.page_spec.v1",
                "page_id": "p1",
                "source": {"width_px": 10, "height_px": 10},
                "canvas": {"width_px": 10, "height_px": 10},
                "elements": [],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    _install_fake_openai(
        monkeypatch,
        calls,
        [
            _tool_message(
                "copy_file",
                {
                    "source": "nodes/page_spec_fuse/runs/001/output/page_spec.json",
                    "path": output_path,
                },
            ),
        ],
    )

    result = invoke_drawai_tool_agent(
        prompt="Copy and validate the connected PageSpec.",
        task_name="drawai.workflow.agent.page_spec_refine.drawai_tool_agent",
        runtime_config={
            "provider": "drawai_tool_agent",
            "connection_id": "drawai_tool_agent",
            "model_name": "fake-model",
            "api_key": "fake-key",
            "wire_api": "chat_completions",
        },
        workspace_dir=tmp_path,
        repo_root=Path(__file__).resolve().parents[2],
        trace_path=tmp_path / "trace.jsonl",
        max_iterations=3,
    )

    assert result.final_text == "validated copied drawai.page_spec.v1 output"
    assert result.iterations == 1
    assert len(calls) == 1
    trace_text = (tmp_path / "trace.jsonl").read_text(encoding="utf-8")
    assert "auto_validation" in trace_text


def test_svg_agent_auto_finalizes_after_successful_page_spec_svg_draft(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    calls: list[dict[str, Any]] = []
    output_path = "nodes/svg_compose/runs/001/output/semantic.svg"
    _install_fake_openai(
        monkeypatch,
        calls,
        [
            _tool_message(
                "run_drawai_tool",
                {
                    "tool_id": "page-spec-svg-draft",
                    "args": [
                        "--page-spec",
                        "nodes/asset_prepare/runs/001/output/page_spec.json",
                        "--svg",
                        output_path,
                        "--href-base-dir",
                        "svg",
                        "--rendered",
                        "nodes/svg_compose/runs/001/output/rendered.png",
                        "--report",
                        "nodes/svg_compose/runs/001/output/validation_report_final.json",
                    ],
                },
            ),
        ],
    )

    def fake_run(*_args: Any, **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            _args[0],
            0,
            stdout=json.dumps({"ok": True, "validation": {"status": "ok"}}),
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = invoke_drawai_tool_agent(
        prompt="Draft and validate the final semantic SVG.",
        task_name="drawai.workflow.agent.svg_compose.drawai_tool_agent",
        runtime_config={
            "provider": "drawai_tool_agent",
            "connection_id": "drawai_tool_agent",
            "model_name": "fake-model",
            "api_key": "fake-key",
            "wire_api": "chat_completions",
        },
        workspace_dir=tmp_path,
        repo_root=Path(__file__).resolve().parents[2],
        trace_path=tmp_path / "trace.jsonl",
        max_iterations=3,
    )

    assert result.final_text == "validated page-spec semantic SVG draft output"
    assert result.iterations == 1
    assert len(calls) == 1


def test_svg_agent_auto_finalizes_after_page_spec_svg_draft_promotes_draft_path(
    tmp_path: Path, monkeypatch
) -> None:  # type: ignore[no-untyped-def]
    calls: list[dict[str, Any]] = []
    _install_fake_openai(
        monkeypatch,
        calls,
        [
            _tool_message(
                "run_drawai_tool",
                {
                    "tool_id": "page-spec-svg-draft",
                    "args": [
                        "--page-spec",
                        "nodes/asset_prepare/runs/001/output/page_spec.json",
                        "--svg",
                        "nodes/svg_compose/runs/001/output/semantic_0.svg",
                        "--href-base-dir",
                        "svg",
                        "--rendered",
                        "nodes/svg_compose/runs/001/output/rendered_0.png",
                        "--report",
                        "nodes/svg_compose/runs/001/output/validation_report_0.json",
                    ],
                },
            ),
        ],
    )

    def fake_run(*_args: Any, **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            _args[0],
            0,
            stdout=json.dumps(
                {
                    "ok": True,
                    "validation": {"status": "ok"},
                    "finalized_outputs": {
                        "semantic_svg": str(tmp_path / "nodes/svg_compose/runs/001/output/semantic.svg"),
                        "rendered_png": str(tmp_path / "nodes/svg_compose/runs/001/output/rendered.png"),
                        "validation_report": str(
                            tmp_path / "nodes/svg_compose/runs/001/output/validation_report_final.json"
                        ),
                    },
                }
            ),
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = invoke_drawai_tool_agent(
        prompt="Draft and validate the semantic SVG through a draft filename.",
        task_name="drawai.workflow.agent.svg_compose.drawai_tool_agent",
        runtime_config={
            "provider": "drawai_tool_agent",
            "connection_id": "drawai_tool_agent",
            "model_name": "fake-model",
            "api_key": "fake-key",
            "wire_api": "chat_completions",
        },
        workspace_dir=tmp_path,
        repo_root=Path(__file__).resolve().parents[2],
        trace_path=tmp_path / "trace.jsonl",
        max_iterations=3,
    )

    assert result.final_text == "validated page-spec semantic SVG draft output"
    assert result.iterations == 1
    assert len(calls) == 1


def test_svg_agent_auto_finalizes_after_page_spec_svg_draft_declared_output_path(
    tmp_path: Path, monkeypatch
) -> None:  # type: ignore[no-untyped-def]
    calls: list[dict[str, Any]] = []
    _install_fake_openai(
        monkeypatch,
        calls,
        [
            _tool_message(
                "run_drawai_tool",
                {
                    "tool_id": "page-spec-svg-draft",
                    "args": [
                        "--page-spec",
                        "nodes/asset_prepare/runs/001/output/page_spec.json",
                        "--svg",
                        "nodes/svg_compose/runs/001/output/semantic_svg.svg",
                        "--href-base-dir",
                        "svg",
                        "--rendered",
                        "nodes/svg_compose/runs/001/output/rendered.png",
                        "--report",
                        "nodes/svg_compose/runs/001/output/validation_report_final.json",
                    ],
                },
            ),
        ],
    )

    def fake_run(*_args: Any, **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            _args[0],
            0,
            stdout=json.dumps(
                {
                    "ok": True,
                    "validation": {"status": "ok"},
                    "finalized_outputs": {
                        "declared_semantic_svg": str(
                            tmp_path / "nodes/svg_compose/runs/001/output/semantic_svg.svg"
                        )
                    },
                }
            ),
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = invoke_drawai_tool_agent(
        prompt="Draft and validate the declared semantic SVG.",
        task_name="drawai.workflow.agent.svg_compose.drawai_tool_agent",
        runtime_config={
            "provider": "drawai_tool_agent",
            "connection_id": "drawai_tool_agent",
            "model_name": "fake-model",
            "api_key": "fake-key",
            "wire_api": "chat_completions",
        },
        workspace_dir=tmp_path,
        repo_root=Path(__file__).resolve().parents[2],
        trace_path=tmp_path / "trace.jsonl",
        max_iterations=3,
    )

    assert result.final_text == "validated page-spec semantic SVG draft output"
    assert result.iterations == 1
    assert len(calls) == 1


def _install_fake_openai(monkeypatch, calls: list[dict[str, Any]], messages: list[SimpleNamespace]) -> None:  # type: ignore[no-untyped-def]
    class FakeCompletions:
        def __init__(self) -> None:
            self.index = 0

        async def create(self, **payload: Any) -> SimpleNamespace:
            calls.append(payload)
            message = messages[self.index]
            self.index += 1
            return SimpleNamespace(choices=[SimpleNamespace(message=message)])

    class FakeAsyncOpenAI:
        def __init__(self, **_kwargs: Any) -> None:
            self.chat = SimpleNamespace(completions=FakeCompletions())

        async def close(self) -> None:
            return None

    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(AsyncOpenAI=FakeAsyncOpenAI))


def _tool_message(name: str, arguments: dict[str, Any]) -> SimpleNamespace:
    return SimpleNamespace(
        content="",
        tool_calls=[
            SimpleNamespace(
                id=f"call_{name}",
                function=SimpleNamespace(name=name, arguments=json.dumps(arguments)),
            )
        ],
    )


def _text_message(content: str) -> SimpleNamespace:
    return SimpleNamespace(content=content, tool_calls=[])
