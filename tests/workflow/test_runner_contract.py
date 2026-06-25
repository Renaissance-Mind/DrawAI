from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any, Mapping

from drawai.workflow.runner import NodeRunContext, WorkflowRunner
from drawai.workflow.schema import WorkflowEdge, WorkflowNode, WorkflowPort, WorkflowTemplate


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _port(
    port_id: str,
    types: tuple[str, ...],
    *,
    required: bool = True,
    cardinality: str = "single",
    formats: tuple[str, ...] = (),
    description: str = "",
) -> WorkflowPort:
    return WorkflowPort(
        port_id=port_id,
        label=port_id,
        types=types,
        required=required,
        cardinality=cardinality,  # type: ignore[arg-type]
        formats=formats,
        description=description,
    )


def _tiny_template() -> WorkflowTemplate:
    return WorkflowTemplate(
        template_id="tiny",
        name="Tiny",
        nodes=(
            WorkflowNode(
                node_id="input",
                node_type="input",
                title="Input",
                outputs=(
                    _port(
                        "source",
                        ("source",),
                        required=False,
                        description="Source artifact from input node.",
                    ),
                ),
            ),
            WorkflowNode(
                node_id="agent",
                node_type="agent",
                title="Agent",
                inputs=(
                    _port(
                        "source",
                        ("source",),
                        description="Connected source artifact for the agent.",
                    ),
                ),
                outputs=(
                    _port(
                        "semantic_svg",
                        ("semantic_svg",),
                        required=False,
                        formats=("drawai.semantic_svg.v1",),
                        description="deliverable",
                    ),
                ),
                config={
                    "provider_id": "codex_sdk",
                    "resource": "codex_sdk",
                    "outputs": [
                        {
                            "port_id": "semantic_svg",
                            "path": "output/semantic.svg",
                            "format_id": "drawai.semantic_svg.v1",
                            "type": "semantic_svg",
                            "description": "Semantic SVG output.",
                        },
                    ],
                },
            ),
            WorkflowNode(
                node_id="output",
                node_type="output",
                title="Output",
                inputs=(
                    _port(
                        "deliverables",
                        ("semantic_svg",),
                        cardinality="many",
                    ),
                ),
                outputs=(
                    _port(
                        "final_outputs",
                        ("final_outputs",),
                        required=False,
                        formats=("drawai.final_outputs.v1",),
                    ),
                ),
            ),
        ),
        edges=(
            WorkflowEdge("e1", "input", "source", "agent", "source"),
            WorkflowEdge("e2", "agent", "semantic_svg", "output", "deliverables"),
        ),
    )


def test_workflow_runner_executes_nodes_and_finalizes_output(tmp_path: Path) -> None:
    events: list[str] = []
    resource_events: list[str] = []

    def input_handler(
        context: NodeRunContext,
        _inputs: tuple[Mapping[str, Any], ...],
    ) -> tuple[Mapping[str, Any], ...]:
        events.append(context.node.node_id)
        source_path = context.output_dir / "source.txt"
        source_path.write_text("source", encoding="utf-8")
        return (
            {
                "port_id": "source",
                "path": context.relative_path(source_path),
                "type": "source",
            },
        )

    def agent_handler(
        context: NodeRunContext,
        inputs: tuple[Mapping[str, Any], ...],
    ) -> tuple[Mapping[str, Any], ...]:
        events.append(context.node.node_id)
        assert inputs[0]["source_node_id"] == "input"
        assert inputs[0]["description"] == "Connected source artifact for the agent."
        assert inputs[0]["source_port_label"] == "source"
        assert inputs[0]["target_port_label"] == "source"
        svg_path = context.output_dir / "semantic.svg"
        svg_path.write_text("<svg xmlns='http://www.w3.org/2000/svg'/>", encoding="utf-8")
        return (
            {
                "port_id": "semantic_svg",
                "path": context.relative_path(svg_path),
                "format_id": "drawai.semantic_svg.v1",
                "type": "semantic_svg",
                "deliverable": True,
            },
        )

    runner = WorkflowRunner(
        _tiny_template(),
        handlers={"input": input_handler, "agent": agent_handler},
        acquire_resource=lambda node: resource_events.append(node.node_id)
        or f"lease:{node.node_id}",
    )

    result = runner.run(tmp_path)

    assert result.ok
    assert events == ["input", "agent"]
    assert resource_events == ["agent"]
    assert [run.node_id for run in result.node_runs] == ["input", "agent", "output"]

    agent_manifest = _read_json(tmp_path / "nodes" / "agent" / "runs" / "001" / "node_run.json")
    assert agent_manifest["status"] == "ok"
    assert agent_manifest["provider_id"] == "codex_sdk"
    assert agent_manifest["resource_id"] == "lease:agent"
    assert agent_manifest["outputs"][0]["format_id"] == "drawai.semantic_svg.v1"

    final_manifest_path = tmp_path / "nodes" / "output" / "runs" / "001" / "output" / "final_outputs.json"
    final_manifest = _read_json(final_manifest_path)
    assert final_manifest["schema"] == "drawai.final_outputs.v1"
    assert final_manifest["outputs"][0]["path"] == "nodes/agent/runs/001/output/semantic.svg"
    assert final_manifest["outputs"][0]["mirror_path"] == "svg/semantic.svg"
    assert (tmp_path / "svg" / "semantic.svg").read_text(encoding="utf-8").startswith("<svg")


def test_workflow_runner_marks_downstream_nodes_blocked(tmp_path: Path) -> None:
    events: list[str] = []

    def input_handler(
        context: NodeRunContext,
        _inputs: tuple[Mapping[str, Any], ...],
    ) -> tuple[Mapping[str, Any], ...]:
        events.append(context.node.node_id)
        source_path = context.output_dir / "source.txt"
        source_path.write_text("source", encoding="utf-8")
        return (
            {
                "port_id": "source",
                "path": context.relative_path(source_path),
                "type": "source",
            },
        )

    def failing_agent_handler(
        context: NodeRunContext,
        _inputs: tuple[Mapping[str, Any], ...],
    ) -> tuple[Mapping[str, Any], ...]:
        events.append(context.node.node_id)
        raise RuntimeError("agent failed")

    runner = WorkflowRunner(
        _tiny_template(),
        handlers={"input": input_handler, "agent": failing_agent_handler},
    )

    result = runner.run(tmp_path)

    assert not result.ok
    assert result.failed_node_ids == ("agent",)
    assert result.blocked_node_ids == ("output",)
    assert events == ["input", "agent"]

    agent_manifest = _read_json(tmp_path / "nodes" / "agent" / "runs" / "001" / "node_run.json")
    output_manifest = _read_json(tmp_path / "nodes" / "output" / "runs" / "001" / "node_run.json")
    assert agent_manifest["status"] == "failed"
    assert "agent failed" in agent_manifest["error"]
    assert output_manifest["status"] == "blocked"
    assert output_manifest["error"] == "blocked by upstream node failure"


def test_workflow_runner_pauses_after_breakpoint_node(tmp_path: Path) -> None:
    events: list[str] = []

    def input_handler(
        context: NodeRunContext,
        _inputs: tuple[Mapping[str, Any], ...],
    ) -> tuple[Mapping[str, Any], ...]:
        events.append(context.node.node_id)
        source_path = context.output_dir / "source.txt"
        source_path.write_text("source", encoding="utf-8")
        return ({"port_id": "source", "path": context.relative_path(source_path), "type": "source"},)

    def agent_handler(
        context: NodeRunContext,
        _inputs: tuple[Mapping[str, Any], ...],
    ) -> tuple[Mapping[str, Any], ...]:
        events.append(context.node.node_id)
        svg_path = context.output_dir / "semantic.svg"
        svg_path.write_text("<svg xmlns='http://www.w3.org/2000/svg'/>", encoding="utf-8")
        return (
            {
                "port_id": "semantic_svg",
                "path": context.relative_path(svg_path),
                "format_id": "drawai.semantic_svg.v1",
                "type": "semantic_svg",
                "deliverable": True,
            },
        )

    runner = WorkflowRunner(
        _tiny_template(),
        handlers={"input": input_handler, "agent": agent_handler},
    )

    result = runner.run(tmp_path, break_after_node_ids=("agent",))

    assert result.ok
    assert result.paused_node_ids == ("agent",)
    assert events == ["input", "agent"]
    assert [run.node_id for run in result.node_runs] == ["input", "agent"]
    assert not (tmp_path / "nodes" / "output" / "runs" / "001" / "node_run.json").exists()


def test_workflow_runner_executes_ready_sibling_nodes_concurrently(tmp_path: Path) -> None:
    template = WorkflowTemplate(
        template_id="parallel_siblings",
        name="Parallel Siblings",
        nodes=(
            WorkflowNode(
                node_id="input",
                node_type="input",
                title="Input",
                outputs=(_port("source", ("source",), required=False),),
            ),
            WorkflowNode(
                node_id="branch_a",
                node_type="branch",
                title="Branch A",
                inputs=(_port("source", ("source",)),),
                outputs=(_port("artifact", ("artifact",), required=False),),
            ),
            WorkflowNode(
                node_id="branch_b",
                node_type="branch",
                title="Branch B",
                inputs=(_port("source", ("source",)),),
                outputs=(_port("artifact", ("artifact",), required=False),),
            ),
        ),
        edges=(
            WorkflowEdge("e1", "input", "source", "branch_a", "source"),
            WorkflowEdge("e2", "input", "source", "branch_b", "source"),
        ),
    )
    started = {
        "branch_a": threading.Event(),
        "branch_b": threading.Event(),
    }
    release = threading.Event()
    result_holder: dict[str, Any] = {}
    errors: list[BaseException] = []

    def input_handler(
        context: NodeRunContext,
        _inputs: tuple[Mapping[str, Any], ...],
    ) -> tuple[Mapping[str, Any], ...]:
        source_path = context.output_dir / "source.txt"
        source_path.write_text("source", encoding="utf-8")
        return ({"port_id": "source", "path": context.relative_path(source_path), "type": "source"},)

    def branch_handler(
        context: NodeRunContext,
        _inputs: tuple[Mapping[str, Any], ...],
    ) -> tuple[Mapping[str, Any], ...]:
        started[context.node.node_id].set()
        release.wait(timeout=5)
        output_path = context.output_dir / f"{context.node.node_id}.txt"
        output_path.write_text(context.node.node_id, encoding="utf-8")
        return (
            {
                "port_id": "artifact",
                "path": context.relative_path(output_path),
                "type": "artifact",
            },
        )

    runner = WorkflowRunner(
        template,
        handlers={"input": input_handler, "branch": branch_handler},
    )

    def run_workflow() -> None:
        try:
            result_holder["result"] = runner.run(tmp_path)
        except BaseException as exc:  # Thread boundary for surfacing runner failures in the test.
            errors.append(exc)

    thread = threading.Thread(target=run_workflow)
    thread.start()
    try:
        assert started["branch_a"].wait(timeout=2)
        assert started["branch_b"].wait(timeout=0.5)
    finally:
        release.set()
        thread.join(timeout=5)

    assert not thread.is_alive()
    assert not errors
    result = result_holder["result"]
    assert result.ok
    assert [run.node_id for run in result.node_runs] == ["input", "branch_a", "branch_b"]
