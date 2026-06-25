from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
import sys

import pytest

from drawai.workflow.agent_execution import (
    AgentExecutionError,
    AgentExecutionRequest,
    execute_agent_prompt,
    _copy_codex_session_log_snapshot,
    _execute_codex_cli_agent,
    _execute_codex_sdk_agent,
    _execute_kimi_cli_agent,
    _execute_subprocess_agent,
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


def test_subprocess_agent_waits_for_process_exit_after_declared_outputs_are_valid(tmp_path: Path) -> None:
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
            "timeout_seconds": 5,
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
                "Path('nodes/svg_agent/runs/001/output').mkdir(parents=True, exist_ok=True); "
                "Path('nodes/svg_agent/runs/001/output/semantic.svg').write_text("
                "'<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"10\" height=\"10\"></svg>\\n', "
                "encoding='utf-8'); "
                "sys.stdin.read(); "
                "Path('nodes/svg_agent/runs/001/output/after_agent_exit.txt').write_text('done\\n', encoding='utf-8')"
        ),
    ]

    result = _execute_subprocess_agent(
        request,
        prompt_path=prompt_path,
        provider_id="kimi_cli",
        command=command,
        stdout_name="events.jsonl",
        stderr_name="stderr.txt",
    )

    assert result.exit_code == 0
    assert (workdir / "output" / "semantic.svg").is_file()
    assert (workdir / "output" / "after_agent_exit.txt").read_text(encoding="utf-8") == "done\n"
    trace_text = (workdir / "kimi_cli_trace.jsonl").read_text(encoding="utf-8")
    assert "agent_outputs_satisfied_before_process_finished" not in trace_text


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
        options={"reasoning_effort": "low", "fast": True},
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
    assert "-c" in captured["command"]
    assert 'service_tier="priority"' in captured["command"]
    env_overrides = captured["env_overrides"]
    assert isinstance(env_overrides, dict)
    assert env_overrides["CODEX_HOME"] == str(isolated_home)
    assert env_overrides["HOME"] == str(isolated_home.parent)
    assert env_overrides.get("CODEX_THREAD_ID") is None
    assert result.session_log_path == workdir / "codex_cli_session_log"


def test_codex_sdk_agent_uses_fast_service_tier(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    run_root = tmp_path / "run"
    workdir = run_root / "nodes" / "agent" / "runs" / "001"
    workdir.mkdir(parents=True)
    prompt_path = workdir / "prompt.md"
    prompt = AgentPrompt(
        preset_id="custom_agent",
        provider_id="codex_sdk",
        text="Return a concise response.",
        inputs=(),
        outputs=(),
        options={"reasoning_effort": "low", "fast": True, "timeout_seconds": 1},
    )
    request = AgentExecutionRequest(
        prompt=prompt,
        workdir=workdir,
        run_root=run_root,
        node_id="agent",
        node_type="agent",
    )
    isolated_home = tmp_path / "isolated_codex_home"
    seen: dict[str, object] = {}

    class IsolatedHome:
        def __enter__(self) -> SimpleNamespace:
            isolated_home.mkdir()
            return SimpleNamespace(codex_home=isolated_home)

        def __exit__(self, *args: object) -> None:
            return None

    class FakeCodex:
        def __init__(self, config: object) -> None:
            seen["config"] = config

        def __enter__(self) -> "FakeCodex":
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def thread_start(self, **kwargs: object) -> object:
            seen["thread_start_kwargs"] = kwargs
            return object()

    fake_sdk = SimpleNamespace(
        ApprovalMode=SimpleNamespace(deny_all="deny_all"),
        Sandbox=SimpleNamespace(full_access="full_access"),
        Codex=FakeCodex,
        CodexConfig=lambda **kwargs: kwargs,
        TextInput=lambda text: ("text", text),
        LocalImageInput=lambda path: ("image", path),
    )

    def fake_run_thread(_thread: object, run_input: object, **kwargs: object) -> SimpleNamespace:
        seen["run_input"] = run_input
        seen["run_kwargs"] = kwargs
        return SimpleNamespace(final_response="ok")

    monkeypatch.setattr("drawai.workflow.agent_execution._load_openai_codex_sdk", lambda: fake_sdk)
    monkeypatch.setattr("drawai.workflow.agent_execution._isolated_codex_home", lambda _workdir: IsolatedHome())
    monkeypatch.setattr("drawai.workflow.agent_execution._run_thread_with_timeout", fake_run_thread)
    monkeypatch.setattr(
        "drawai.workflow.agent_execution._start_codex_session_log_mirror",
        lambda *_args, **_kwargs: (SimpleNamespace(set=lambda: None), SimpleNamespace(join=lambda timeout=None: None)),
    )
    monkeypatch.setattr("drawai.workflow.agent_execution._stop_codex_session_log_mirror", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        "drawai.workflow.agent_execution._archive_codex_session_logs",
        lambda _codex_home, archive_dir, task_name, sdk_turn_result=None: {"archive_dir": str(archive_dir)},
    )

    result = _execute_codex_sdk_agent(request, prompt_path=prompt_path)

    assert result.provider_id == "codex_sdk"
    assert seen["thread_start_kwargs"]["service_tier"] == "priority"  # type: ignore[index]
    assert seen["run_kwargs"]["service_tier"] == "priority"  # type: ignore[index]


def test_codex_session_log_snapshot_copies_live_runtime_files(tmp_path: Path) -> None:
    codex_home = tmp_path / "codex_home"
    archive_dir = tmp_path / "workdir" / "codex_session_log"
    (codex_home / "shell_snapshots").mkdir(parents=True)
    (codex_home / "shell_snapshots" / "turn.sh").write_text("echo ok\n", encoding="utf-8")
    (codex_home / "history.jsonl").write_text('{"text":"ok"}\n', encoding="utf-8")

    _copy_codex_session_log_snapshot(codex_home, archive_dir, task_name="test.agent")

    assert (archive_dir / "shell_snapshots" / "turn.sh").read_text(encoding="utf-8") == "echo ok\n"
    assert (archive_dir / "history.jsonl").read_text(encoding="utf-8") == '{"text":"ok"}\n'
    live_manifest = (archive_dir / "live_manifest.json").read_text(encoding="utf-8")
    assert "test.agent" in live_manifest


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


def test_execute_agent_prompt_runs_generic_local_cli_provider(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    bin_dir = tmp_path / "bin"
    _write_executable(
        bin_dir / "claude",
            "\n".join(
                [
                    "/bin/mkdir -p nodes/agent/runs/001/output",
                    "/bin/cat >/dev/null",
                    "printf '{\"ok\": true}\\n' > nodes/agent/runs/001/output/result.json",
                    "echo 'claude done'",
                ]
            )
        + "\n",
    )
    monkeypatch.setenv("PATH", str(bin_dir))
    run_root = tmp_path / "run"
    workdir = run_root / "nodes" / "agent" / "runs" / "001"
    workdir.mkdir(parents=True)
    prompt = AgentPrompt(
        preset_id="custom_agent",
        provider_id="claude_cli",
        text="Write output/result.json.",
        inputs=(),
        outputs=(
            {
                "port_id": "result",
                "path": "output/result.json",
                "format_id": "drawai.element_plans.v1",
                "type": "element_plans",
                "description": "Result.",
            },
        ),
        options={"timeout_seconds": 5},
    )

    result = execute_agent_prompt(
        AgentExecutionRequest(
            prompt=prompt,
            workdir=workdir,
            run_root=run_root,
            node_id="agent",
            node_type="agent",
        )
    )

    assert result.provider_id == "claude_cli"
    assert (workdir / "output" / "result.json").read_text(encoding="utf-8") == '{"ok": true}\n'
    assert (workdir / "claude_cli_stdout.txt").read_text(encoding="utf-8") == "claude done\n"


@pytest.mark.parametrize(
    ("provider_id", "agent"),
    [
        ("kimi_acp", "kimi"),
        ("gemini_acp", "gemini"),
        ("qwen_acp", "qwen"),
        ("opencode_acp", "opencode"),
        ("goose_acp", "goose"),
        ("kiro_acp", "kiro"),
        ("qoder_acp", "qoder"),
        ("cursor_acp", "cursor"),
        ("cline_acp", "cline"),
        ("copilot_acp", "copilot"),
        ("hermes_acp", "hermes"),
    ],
)
def test_execute_agent_prompt_runs_acp_provider(
    tmp_path: Path,
    provider_id: str,
    agent: str,
) -> None:
    run_root = tmp_path / "run"
    workdir = run_root / "nodes" / "agent" / "runs" / "001"
    image_path = run_root / "input.png"
    output_path = workdir / "output" / "result.json"
    log_path = workdir / "fake_acp.jsonl"
    image_path.parent.mkdir(parents=True)
    image_path.write_bytes(
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    workdir.mkdir(parents=True)
    prompt = AgentPrompt(
        preset_id="custom_agent",
        provider_id=provider_id,
        text="Inspect input.png and write output/result.json.",
        inputs=(
            {
                "path": "input.png",
                "format_id": "image/png",
                "type": "image",
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
        options={
            "timeout_seconds": 5,
            "acp_agent_command": [
                sys.executable,
                "-c",
                _FAKE_WORKFLOW_ACP_SERVER,
                str(log_path),
                str(output_path),
            ],
        },
    )

    result = execute_agent_prompt(
        AgentExecutionRequest(
            prompt=prompt,
            workdir=workdir,
            run_root=run_root,
            node_id="agent",
            node_type="agent",
        )
    )

    assert result.provider_id == provider_id
    assert json.loads(output_path.read_text(encoding="utf-8")) == {"ok": True}
    assert result.stdout_path is not None
    assert result.stdout_path.name == f"{provider_id}_final_response.txt"
    assert result.stdout_path.read_text(encoding="utf-8") == "workflow acp complete\n"
    assert result.trace_path is not None and result.trace_path.is_file()
    trace_text = result.trace_path.read_text(encoding="utf-8")
    assert f'"agent": "{agent}"' in trace_text
    assert result.execution_manifest_path is not None and result.execution_manifest_path.is_file()


def _write_executable(path: Path, body: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/bin/sh\n" + body, encoding="utf-8")
    path.chmod(0o755)
    return path


_FAKE_WORKFLOW_ACP_SERVER = r"""
import json
import sys
from pathlib import Path

log_path = Path(sys.argv[1])
output_path = Path(sys.argv[2])


def write_log(payload):
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")


def emit(payload):
    print(json.dumps(payload, separators=(",", ":")), flush=True)


def read_response(expected_id):
    while True:
        line = sys.stdin.readline()
        if not line:
            raise SystemExit(1)
        message = json.loads(line)
        write_log({"from_client": message})
        if message.get("id") == expected_id:
            return message


for line in sys.stdin:
    message = json.loads(line)
    write_log({"from_client": message})
    method = message.get("method")
    request_id = message.get("id")
    if method == "initialize":
        emit(
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "protocolVersion": 1,
                    "agentCapabilities": {
                        "promptCapabilities": {
                            "image": True,
                            "audio": False,
                            "embeddedContext": False,
                        }
                    },
                    "authMethods": [],
                },
            }
        )
    elif method == "session/new":
        emit({"jsonrpc": "2.0", "id": request_id, "result": {"sessionId": "sess_workflow"}})
    elif method == "session/prompt":
        server_request_id = "srv-write-json"
        emit(
            {
                "jsonrpc": "2.0",
                "id": server_request_id,
                "method": "fs/write_text_file",
                "params": {
                    "sessionId": "sess_workflow",
                    "path": str(output_path),
                    "content": "{\"ok\": true}\n",
                },
            }
        )
        read_response(server_request_id)
        emit(
            {
                "jsonrpc": "2.0",
                "method": "session/update",
                "params": {
                    "sessionId": "sess_workflow",
                    "update": {
                        "sessionUpdate": "agent_message_chunk",
                        "messageId": "msg_workflow",
                        "content": {"type": "text", "text": "workflow acp complete\n"},
                    },
                },
            }
        )
        emit({"jsonrpc": "2.0", "id": request_id, "result": {"stopReason": "end_turn"}})
    elif method == "session/close":
        emit({"jsonrpc": "2.0", "id": request_id, "result": {}})
    elif request_id is not None:
        emit({"jsonrpc": "2.0", "id": request_id, "result": {}})
"""
