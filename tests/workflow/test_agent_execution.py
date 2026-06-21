from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import sys
import time

import pytest

from drawai.workflow.agent_execution import (
    AgentExecutionError,
    AgentExecutionRequest,
    execute_agent_prompt,
    _execute_codex_cli_agent,
    _execute_kimi_cli_agent,
    _execute_subprocess_agent,
    _run_codex_sdk_thread_until_done_or_outputs,
    _timeout_seconds,
    AgentExecutionResult,
)
from drawai.workflow.agents import DEFAULT_AGENT_TIMEOUT_SECONDS, AgentPrompt


def test_agent_execution_default_timeout_is_thirty_minutes() -> None:
    assert _timeout_seconds({}) == DEFAULT_AGENT_TIMEOUT_SECONDS


def test_agent_execution_requires_declared_input_files(tmp_path: Path) -> None:
    prompt = AgentPrompt(
        preset_id="custom_agent",
        provider_id="unsupported",
        text="Read the input and write output/result.json.",
        inputs=(
            {
                "path": "nodes/input/runs/001/output/missing.json",
                "format_id": "drawai.element_plans.v1",
                "type": "element_plans",
            },
        ),
        outputs=(
            {
                "port_id": "result",
                "path": "output/result.json",
                "format_id": "drawai.element_plans.v1",
                "type": "element_plans",
                "description": "Result.",
            },
        ),
        options={},
    )

    with pytest.raises(AgentExecutionError, match="Agent input files do not exist"):
        execute_agent_prompt(
            AgentExecutionRequest(
                prompt=prompt,
                workdir=tmp_path / "nodes" / "agent" / "runs" / "001",
                run_root=tmp_path,
                node_id="agent",
                node_type="agent",
            )
        )


def test_agent_execution_rejects_output_paths_outside_workdir(tmp_path: Path) -> None:
    input_path = tmp_path / "nodes" / "input" / "runs" / "001" / "output" / "input.json"
    input_path.parent.mkdir(parents=True)
    input_path.write_text("{}\n", encoding="utf-8")
    prompt = AgentPrompt(
        preset_id="custom_agent",
        provider_id="unsupported",
        text="Write outside the workdir.",
        inputs=(
            {
                "path": "nodes/input/runs/001/output/input.json",
                "format_id": "drawai.element_plans.v1",
                "type": "element_plans",
            },
        ),
        outputs=(
            {
                "port_id": "result",
                "path": "../result.json",
                "format_id": "drawai.element_plans.v1",
                "type": "element_plans",
                "description": "Result.",
            },
        ),
        options={},
    )

    with pytest.raises(AgentExecutionError, match="escapes node workdir"):
        execute_agent_prompt(
            AgentExecutionRequest(
                prompt=prompt,
                workdir=tmp_path / "nodes" / "agent" / "runs" / "001",
                run_root=tmp_path,
                node_id="agent",
                node_type="agent",
            )
        )


def test_codex_sdk_agent_completes_when_declared_outputs_are_valid(tmp_path: Path) -> None:
    run_root = tmp_path / "run"
    workdir = run_root / "nodes" / "svg_agent" / "runs" / "001"
    workdir.mkdir(parents=True)
    prompt = AgentPrompt(
        preset_id="svg_generation",
        provider_id="codex_sdk",
        text="Write output/semantic.svg.",
        inputs=(),
        outputs=(
            {
                "port_id": "semantic_svg",
                "path": "output/semantic.svg",
                "format_id": "drawai.semantic_svg.v1",
                "type": "semantic_svg",
                "description": "SVG output.",
            },
        ),
        options={
            "output_completion_poll_seconds": 0.02,
            "output_completion_stable_seconds": 0.05,
            "output_completion_close_wait_seconds": 0.02,
        },
    )
    request = AgentExecutionRequest(
        prompt=prompt,
        workdir=workdir,
        run_root=run_root,
        node_id="svg_agent",
        node_type="agent",
    )

    class HangingThread:
        def __init__(self) -> None:
            self.closed = False
            self._client = SimpleNamespace(close=self.close)

        def close(self) -> None:
            self.closed = True

        def run(self, _run_input: object, **_kwargs: object) -> SimpleNamespace:
            output_path = workdir / "output" / "semantic.svg"
            output_path.parent.mkdir(parents=True)
            output_path.write_text(
                '<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"></svg>\n',
                encoding="utf-8",
            )
            while not self.closed:
                time.sleep(0.01)
            return SimpleNamespace(final_response="")

    thread = HangingThread()
    started_at = time.monotonic()

    result = _run_codex_sdk_thread_until_done_or_outputs(
        thread,
        "prompt",
        request=request,
        trace_path=workdir / "codex_sdk_trace.jsonl",
        timeout_seconds=5,
    )

    assert result.completed_by_outputs is True
    assert thread.closed is True
    assert time.monotonic() - started_at < 1
    assert (workdir / "codex_sdk_trace.jsonl").read_text(encoding="utf-8").count(
        "agent_outputs_satisfied_before_sdk_turn_finished"
    ) == 1


def test_subprocess_agent_completes_when_declared_outputs_are_valid(tmp_path: Path) -> None:
    run_root = tmp_path / "run"
    workdir = run_root / "nodes" / "svg_agent" / "runs" / "001"
    workdir.mkdir(parents=True)
    prompt_path = workdir / "prompt.md"
    prompt_path.write_text("Write output/semantic.svg.", encoding="utf-8")
    prompt = AgentPrompt(
        preset_id="svg_generation",
        provider_id="kimi_cli",
        text="Write output/semantic.svg.",
        inputs=(),
        outputs=(
            {
                "port_id": "semantic_svg",
                "path": "output/semantic.svg",
                "format_id": "drawai.semantic_svg.v1",
                "type": "semantic_svg",
                "description": "SVG output.",
            },
        ),
        options={
            "output_completion_poll_seconds": 0.02,
            "output_completion_stable_seconds": 0.05,
            "output_completion_close_wait_seconds": 0.02,
        },
    )
    request = AgentExecutionRequest(
        prompt=prompt,
        workdir=workdir,
        run_root=run_root,
        node_id="svg_agent",
        node_type="agent",
    )
    command = [
        sys.executable,
        "-c",
        (
            "from pathlib import Path; import sys, time; "
            "Path('output').mkdir(exist_ok=True); "
            "Path('output/semantic.svg').write_text("
            "'<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"10\" height=\"10\"></svg>\\n', "
            "encoding='utf-8'); "
            "sys.stdin.read(); "
            "time.sleep(30)"
        ),
    ]
    started_at = time.monotonic()

    result = _execute_subprocess_agent(
        request,
        prompt_path=prompt_path,
        provider_id="kimi_cli",
        command=command,
        stdout_name="events.jsonl",
        stderr_name="stderr.txt",
    )

    assert result.exit_code == 0
    assert time.monotonic() - started_at < 1
    assert (workdir / "output" / "semantic.svg").is_file()
    assert "agent_outputs_satisfied_before_process_finished" in (
        workdir / "kimi_cli_trace.jsonl"
    ).read_text(encoding="utf-8")


def test_codex_cli_agent_uses_isolated_codex_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    run_root = tmp_path / "run"
    workdir = run_root / "nodes" / "agent" / "runs" / "001"
    workdir.mkdir(parents=True)
    prompt_path = workdir / "prompt.md"
    prompt = AgentPrompt(
        preset_id="custom_agent",
        provider_id="codex_cli",
        text="Copy the connected input to output/elements.json.",
        inputs=(),
        outputs=(
            {
                "port_id": "elements",
                "path": "output/elements.json",
                "format_id": "drawai.element_plans.v1",
                "type": "element_plans",
                "description": "Result.",
            },
        ),
        options={"reasoning_effort": "low"},
    )
    request = AgentExecutionRequest(
        prompt=prompt,
        workdir=workdir,
        run_root=run_root,
        node_id="agent",
        node_type="agent",
    )
    isolated_home = tmp_path / "isolated_codex_home"
    captured: dict[str, object] = {}

    class IsolatedHome:
        def __enter__(self) -> SimpleNamespace:
            isolated_home.mkdir()
            return SimpleNamespace(codex_home=isolated_home)

        def __exit__(self, *args: object) -> None:
            return None

    def fake_subprocess_agent(*args: object, **kwargs: object) -> AgentExecutionResult:
        captured["command"] = kwargs["command"]
        captured["env_overrides"] = kwargs["env_overrides"]
        trace_path = workdir / "codex_cli_trace.jsonl"
        trace_path.write_text("", encoding="utf-8")
        return AgentExecutionResult(
            provider_id="codex_cli",
            prompt_path=prompt_path,
            stdout_path=workdir / "codex_cli_events.jsonl",
            stderr_path=workdir / "codex_cli_stderr.txt",
            trace_path=trace_path,
        )

    monkeypatch.setattr("drawai.workflow.agent_execution.resolve_codex_executable", lambda: Path("/bin/codex"))
    monkeypatch.setattr("drawai.workflow.agent_execution._isolated_codex_home", lambda _workdir: IsolatedHome())
    monkeypatch.setattr("drawai.workflow.agent_execution._execute_subprocess_agent", fake_subprocess_agent)
    monkeypatch.setattr(
        "drawai.workflow.agent_execution._archive_codex_session_logs",
        lambda _codex_home, archive_dir, task_name, sdk_turn_result=None: {"archive_dir": str(archive_dir)},
    )

    result = _execute_codex_cli_agent(request, prompt_path=prompt_path)

    assert "--ignore-rules" in captured["command"]
    env_overrides = captured["env_overrides"]
    assert isinstance(env_overrides, dict)
    assert env_overrides["CODEX_HOME"] == str(isolated_home)
    assert env_overrides["HOME"] == str(isolated_home.parent)
    assert env_overrides.get("CODEX_THREAD_ID") is None
    assert result.session_log_path == workdir / "codex_cli_session_log"


def test_kimi_cli_agent_uses_isolated_skills_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    run_root = tmp_path / "run"
    workdir = run_root / "nodes" / "agent" / "runs" / "001"
    workdir.mkdir(parents=True)
    prompt_path = workdir / "prompt.md"
    prompt = AgentPrompt(
        preset_id="custom_agent",
        provider_id="kimi_cli",
        text="Copy the connected input to output/elements.json.",
        inputs=(),
        outputs=(
            {
                "port_id": "elements",
                "path": "output/elements.json",
                "format_id": "drawai.element_plans.v1",
                "type": "element_plans",
                "description": "Result.",
            },
        ),
        options={},
    )
    request = AgentExecutionRequest(
        prompt=prompt,
        workdir=workdir,
        run_root=run_root,
        node_id="agent",
        node_type="agent",
    )
    captured: dict[str, object] = {}

    def fake_subprocess_agent(*args: object, **kwargs: object) -> AgentExecutionResult:
        captured["command"] = kwargs["command"]
        return AgentExecutionResult(
            provider_id="kimi_cli",
            prompt_path=prompt_path,
            stdout_path=workdir / "kimi_events.jsonl",
            stderr_path=workdir / "kimi_stderr.txt",
            trace_path=workdir / "kimi_cli_trace.jsonl",
        )

    def fake_run(command: list[str], **kwargs: object) -> SimpleNamespace:
        captured["export_command"] = command
        export_path = workdir / "kimi_session.zip"
        export_path.write_bytes(b"zip")
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr("drawai.workflow.agent_execution.shutil.which", lambda name: "/bin/kimi")
    monkeypatch.setattr("drawai.workflow.agent_execution._execute_subprocess_agent", fake_subprocess_agent)
    monkeypatch.setattr("drawai.workflow.agent_execution.subprocess.run", fake_run)

    result = _execute_kimi_cli_agent(request, prompt_path=prompt_path)

    command = captured["command"]
    assert isinstance(command, list)
    assert "--skills-dir" in command
    skills_dir = Path(command[command.index("--skills-dir") + 1])
    assert skills_dir == workdir / "_isolated_kimi_skills"
    assert skills_dir.is_dir()
    assert result.session_log_path == workdir / "kimi_session.zip"
