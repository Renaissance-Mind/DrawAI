from __future__ import annotations

import json
from pathlib import Path

import pytest

from drawai.workflow.node_runs import (
    begin_node_run,
    finish_node_run_failed,
    finish_node_run_ok,
    mark_node_run_stale,
    node_run_dir,
    write_input_manifest,
)


def _read_json(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def test_begin_node_run_creates_runner_owned_manifest(tmp_path: Path) -> None:
    record = begin_node_run(
        tmp_path,
        "svg_agent",
        node_type="agent",
        provider_id="codex_sdk",
    )

    assert record.attempt_id == "001"
    assert record.workdir == tmp_path / "nodes" / "svg_agent" / "runs" / "001"
    assert (record.workdir / "output").is_dir()

    payload = _read_json(record.workdir / "node_run.json")
    assert payload["schema"] == "drawai.workflow_node_run.v1"
    assert payload["node_id"] == "svg_agent"
    assert payload["node_type"] == "agent"
    assert payload["attempt_id"] == "001"
    assert payload["status"] == "running"
    assert payload["provider_id"] == "codex_sdk"
    assert payload["workdir"] == "nodes/svg_agent/runs/001"
    assert payload["started_at"]
    assert payload["ended_at"] == ""


def test_begin_node_run_increments_attempt_id(tmp_path: Path) -> None:
    first = begin_node_run(tmp_path, "run0_agent", node_type="agent")
    second = begin_node_run(tmp_path, "run0_agent", node_type="agent")

    assert first.attempt_id == "001"
    assert second.attempt_id == "002"
    assert second.workdir == tmp_path / "nodes" / "run0_agent" / "runs" / "002"


def test_node_run_paths_reject_unsafe_node_ids(tmp_path: Path) -> None:
    unsafe_node_ids = ("../escape", "nested/node", "", ".", "..", str(tmp_path / "abs"))

    for node_id in unsafe_node_ids:
        with pytest.raises(ValueError, match="node_id"):
            begin_node_run(tmp_path, node_id, node_type="agent")
        with pytest.raises(ValueError, match="node_id"):
            node_run_dir(tmp_path, node_id, "001")

    assert not (tmp_path.parent / "escape").exists()
    assert not (tmp_path / "nodes" / "nested").exists()


def test_write_input_manifest_records_connected_files(tmp_path: Path) -> None:
    record = begin_node_run(tmp_path, "run0_agent", node_type="agent")

    manifest_path = write_input_manifest(
        record.workdir,
        inputs=(
            {
                "source_node_id": "fusion",
                "source_port_id": "elements",
                "path": "nodes/fusion/runs/001/output/elements.json",
                "format_id": "drawai.element_plans.v1",
                "description": "Fused element plans.",
            },
        ),
    )

    payload = _read_json(manifest_path)
    assert payload["schema"] == "drawai.workflow_input_manifest.v1"
    assert payload["inputs"][0]["source_node_id"] == "fusion"
    assert payload["inputs"][0]["format_id"] == "drawai.element_plans.v1"


def test_finish_node_run_ok_records_outputs(tmp_path: Path) -> None:
    record = begin_node_run(tmp_path, "svg_agent", node_type="agent")
    output_path = record.workdir / "output" / "semantic.svg"
    output_path.write_text("<svg xmlns='http://www.w3.org/2000/svg'/>", encoding="utf-8")

    finish_node_run_ok(
        record,
        outputs=(
            {
                "path": "nodes/svg_agent/runs/001/output/semantic.svg",
                "format_id": "drawai.semantic_svg.v1",
                "type": "semantic_svg",
                "deliverable": True,
            },
        ),
        prompt_path="prompt.md",
        stdout_path="stdout.log",
        stderr_path="stderr.log",
        trace_path="trace.jsonl",
        session_log_path="codex_session_log",
        execution_manifest_path="agent_execution.json",
    )

    payload = _read_json(record.workdir / "node_run.json")
    assert payload["status"] == "ok"
    assert payload["outputs"][0]["format_id"] == "drawai.semantic_svg.v1"
    assert payload["prompt_path"] == "prompt.md"
    assert payload["trace_path"] == "trace.jsonl"
    assert payload["session_log_path"] == "codex_session_log"
    assert payload["execution_manifest_path"] == "agent_execution.json"
    assert payload["ended_at"]
    assert payload["duration_ms"] >= 0


def test_finish_node_run_failed_records_error(tmp_path: Path) -> None:
    record = begin_node_run(tmp_path, "svg_agent", node_type="agent")

    finish_node_run_failed(record, error="SVG generation failed", exit_code=2)

    payload = _read_json(record.workdir / "node_run.json")
    assert payload["status"] == "failed"
    assert payload["error"] == "SVG generation failed"
    assert payload["exit_code"] == 2
    assert payload["ended_at"]


def test_mark_node_run_stale_preserves_attempt_and_reason(tmp_path: Path) -> None:
    record = begin_node_run(tmp_path, "svg_agent", node_type="agent")
    finish_node_run_ok(record)

    mark_node_run_stale(record.workdir, stale_reason="upstream run0_agent reran")

    payload = _read_json(record.workdir / "node_run.json")
    assert payload["attempt_id"] == "001"
    assert payload["status"] == "stale"
    assert payload["stale_reason"] == "upstream run0_agent reran"
