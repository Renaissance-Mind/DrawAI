import json
import subprocess
from pathlib import Path

from PIL import Image

from drawai.agent_cli_svg import invoke_agent_cli_svg_text


VALID_SVG = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 4 4"></svg>'


def test_agent_cli_svg_runner_calls_kimi_preset_and_reads_output(monkeypatch, tmp_path: Path):
    output_svg = tmp_path / "attempt" / "semantic.svg"
    output_response = tmp_path / "attempt" / "model_response.txt"
    output_svg.parent.mkdir(parents=True)
    output_svg.write_text("<svg>stale</svg>", encoding="utf-8")
    image_path = tmp_path / "input.png"
    Image.new("RGB", (2, 2), "white").save(image_path)
    trace_path = tmp_path / "trace.jsonl"
    calls = []

    def fake_run(command, *, input, cwd, text, capture_output, timeout, check):
        calls.append(
            {
                "command": list(command),
                "input": input,
                "cwd": str(cwd),
                "text": text,
                "capture_output": capture_output,
                "timeout": timeout,
                "check": check,
            }
        )
        assert not output_svg.exists()
        output_svg.write_text(VALID_SVG, encoding="utf-8")
        return subprocess.CompletedProcess(command, 0, stdout="wrote semantic.svg\n", stderr="")

    monkeypatch.setattr("drawai.agent_cli_svg.subprocess.run", fake_run)

    svg = invoke_agent_cli_svg_text(
        image_paths=image_path,
        prompt="Write the requested SVG.",
        task_name="unit_test_agent_cli_svg",
        runtime_config={
            "provider": "agent-cli",
            "model_name": "kimi-code/kimi-for-coding",
            "cli": {"agent": "kimi", "command": ["kimi"]},
            "timeout_seconds": 5,
        },
        trace_path=trace_path,
        isolated_cwd=tmp_path,
        output_svg_path=output_svg,
        output_response_path=output_response,
    )

    assert svg == VALID_SVG
    assert output_svg.read_text(encoding="utf-8") == VALID_SVG
    assert output_response.read_text(encoding="utf-8") == "wrote semantic.svg\n"
    assert calls[0]["command"] == [
        "kimi",
        "--model",
        "kimi-code/kimi-for-coding",
        "--output-format",
        "text",
        "--prompt",
        calls[0]["command"][-1],
    ]
    assert calls[0]["input"] is None
    assert calls[0]["cwd"] == str(tmp_path)
    assert calls[0]["timeout"] == 5
    assert "Internal DrawAI Kimi CLI SVG generation task" in calls[0]["command"][-1]
    assert str(image_path) in calls[0]["command"][-1]
    assert str(output_svg) in calls[0]["command"][-1]
    trace_events = [json.loads(line) for line in trace_path.read_text(encoding="utf-8").splitlines()]
    assert trace_events[0]["type"] == "agent_cli_request"
    assert trace_events[0]["agent"] == "kimi"
    assert trace_events[-1]["type"] == "agent_cli_response"
    assert trace_events[-1]["source"] == "output_svg_path"


def test_agent_cli_svg_runner_accepts_stdout_svg_when_file_is_missing(monkeypatch, tmp_path: Path):
    output_svg = tmp_path / "attempt" / "semantic.svg"
    image_path = tmp_path / "input.png"
    Image.new("RGB", (2, 2), "white").save(image_path)
    trace_path = tmp_path / "trace.jsonl"

    def fake_run(command, *, input, cwd, text, capture_output, timeout, check):
        return subprocess.CompletedProcess(command, 0, stdout=f"done\n{VALID_SVG}\n", stderr="")

    monkeypatch.setattr("drawai.agent_cli_svg.subprocess.run", fake_run)

    svg = invoke_agent_cli_svg_text(
        image_paths=image_path,
        prompt="Return the requested SVG.",
        task_name="unit_test_agent_cli_svg_stdout",
        runtime_config={
            "provider": "agent-cli",
            "cli": {"agent": "kimi", "command": ["kimi"]},
            "timeout_seconds": 5,
        },
        trace_path=trace_path,
        isolated_cwd=tmp_path,
        output_svg_path=output_svg,
    )

    assert svg == VALID_SVG
    assert output_svg.read_text(encoding="utf-8") == VALID_SVG
    trace_events = [json.loads(line) for line in trace_path.read_text(encoding="utf-8").splitlines()]
    assert trace_events[-1]["source"] == "stdout"


def test_agent_cli_svg_runner_builds_claude_preset(monkeypatch, tmp_path: Path):
    image_path = tmp_path / "input.png"
    output_svg = tmp_path / "semantic.svg"
    Image.new("RGB", (2, 2), "white").save(image_path)
    calls = []

    def fake_run(command, *, input, cwd, text, capture_output, timeout, check):
        calls.append({"command": list(command), "input": input, "cwd": str(cwd)})
        output_svg.write_text(VALID_SVG, encoding="utf-8")
        return subprocess.CompletedProcess(command, 0, stdout="done\n", stderr="")

    monkeypatch.setattr("drawai.agent_cli_svg.subprocess.run", fake_run)

    svg = invoke_agent_cli_svg_text(
        image_paths=image_path,
        prompt="Write the requested SVG.",
        task_name="unit_test_agent_cli_claude",
        runtime_config={
            "provider": "agent-cli",
            "model_name": "sonnet",
            "fast": True,
            "cli": {"agent": "claude", "command": ["claude"]},
            "timeout_seconds": 5,
        },
        isolated_cwd=tmp_path,
        output_svg_path=output_svg,
    )

    assert svg == VALID_SVG
    assert calls[0]["command"] == [
        "claude",
        "--model",
        "sonnet",
        "--bare",
        "--print",
        "--permission-mode",
        "bypassPermissions",
        "--output-format",
        "text",
        "--input-format",
        "text",
    ]
    assert "Internal DrawAI Claude CLI SVG generation task" in calls[0]["input"]


def test_agent_cli_svg_runner_builds_codex_preset_with_images(monkeypatch, tmp_path: Path):
    image_path = tmp_path / "input.png"
    output_svg = tmp_path / "semantic.svg"
    Image.new("RGB", (2, 2), "white").save(image_path)
    calls = []

    def fake_run(command, *, input, cwd, text, capture_output, timeout, check):
        calls.append({"command": list(command), "input": input, "cwd": str(cwd)})
        output_svg.write_text(VALID_SVG, encoding="utf-8")
        return subprocess.CompletedProcess(command, 0, stdout="done\n", stderr="")

    monkeypatch.setattr("drawai.agent_cli_svg.subprocess.run", fake_run)

    svg = invoke_agent_cli_svg_text(
        image_paths=image_path,
        prompt="Write the requested SVG.",
        task_name="unit_test_agent_cli_codex",
        runtime_config={
            "provider": "agent-cli",
            "model_name": "gpt-5.1-codex-max",
            "fast": True,
            "cli": {"agent": "codex", "command": ["codex", "exec"]},
            "timeout_seconds": 5,
        },
        isolated_cwd=tmp_path,
        output_svg_path=output_svg,
    )

    assert svg == VALID_SVG
    assert calls[0]["command"] == [
        "codex",
        "exec",
        "--model",
        "gpt-5.1-codex-max",
        "--cd",
        str(tmp_path),
        "--skip-git-repo-check",
        "--dangerously-bypass-approvals-and-sandbox",
        "--color",
        "never",
        "-c",
        'service_tier="priority"',
        "-i",
        str(image_path),
        "-",
    ]
    assert "Internal DrawAI Codex CLI SVG generation task" in calls[0]["input"]


def test_agent_cli_svg_runner_builds_openclaw_preset_with_prompt_argument(monkeypatch, tmp_path: Path):
    image_path = tmp_path / "input.png"
    output_svg = tmp_path / "semantic.svg"
    Image.new("RGB", (2, 2), "white").save(image_path)
    trace_path = tmp_path / "trace.jsonl"
    calls = []

    def fake_run(command, *, input, cwd, text, capture_output, timeout, check):
        calls.append({"command": list(command), "input": input, "cwd": str(cwd)})
        output_svg.write_text(VALID_SVG, encoding="utf-8")
        return subprocess.CompletedProcess(command, 0, stdout='{"status":"ok"}\n', stderr="")

    monkeypatch.setattr("drawai.agent_cli_svg.subprocess.run", fake_run)

    svg = invoke_agent_cli_svg_text(
        image_paths=image_path,
        prompt="Write the requested SVG.",
        task_name="unit_test_agent_cli_openclaw",
        runtime_config={
            "provider": "agent-cli",
            "reasoning_effort": "high",
            "cli": {"agent": "openclaw", "command": ["openclaw"]},
            "timeout_seconds": 5,
        },
        trace_path=trace_path,
        isolated_cwd=tmp_path,
        output_svg_path=output_svg,
    )

    assert svg == VALID_SVG
    command = calls[0]["command"]
    assert calls[0]["input"] is None
    assert command[:2] == ["openclaw", "agent"]
    assert "--local" in command
    assert "--json" in command
    assert command[command.index("--agent") + 1] == "main"
    assert command[command.index("--timeout") + 1] == "5"
    assert command[command.index("--thinking") + 1] == "high"
    message = command[command.index("--message") + 1]
    assert "Internal DrawAI OpenClaw CLI SVG generation task" in message
    assert str(output_svg) in message
    trace_events = [json.loads(line) for line in trace_path.read_text(encoding="utf-8").splitlines()]
    assert "<prompt:" in " ".join(trace_events[0]["command"])
    assert message not in trace_events[0]["command"]


def test_agent_cli_svg_runner_builds_hermes_preset_with_prompt_argument(monkeypatch, tmp_path: Path):
    image_path = tmp_path / "input.png"
    output_svg = tmp_path / "semantic.svg"
    Image.new("RGB", (2, 2), "white").save(image_path)
    trace_path = tmp_path / "trace.jsonl"
    calls = []

    def fake_run(command, *, input, cwd, text, capture_output, timeout, check):
        calls.append({"command": list(command), "input": input, "cwd": str(cwd)})
        output_svg.write_text(VALID_SVG, encoding="utf-8")
        return subprocess.CompletedProcess(command, 0, stdout="done\n", stderr="")

    monkeypatch.setattr("drawai.agent_cli_svg.subprocess.run", fake_run)

    svg = invoke_agent_cli_svg_text(
        image_paths=image_path,
        prompt="Write the requested SVG.",
        task_name="unit_test_agent_cli_hermes",
        runtime_config={
            "provider": "agent-cli",
            "model_name": "moonshot/kimi-k2-thinking",
            "cli": {"agent": "hermes", "command": ["hermes"]},
            "timeout_seconds": 5,
        },
        trace_path=trace_path,
        isolated_cwd=tmp_path,
        output_svg_path=output_svg,
    )

    assert svg == VALID_SVG
    command = calls[0]["command"]
    assert calls[0]["input"] is None
    assert command[:2] == ["hermes", "chat"]
    assert command[command.index("--model") + 1] == "moonshot/kimi-k2-thinking"
    assert "--quiet" in command
    assert "--yolo" in command
    assert command[command.index("--source") + 1] == "drawai"
    assert command[command.index("--image") + 1] == str(image_path)
    query = command[command.index("--query") + 1]
    assert "Internal DrawAI Hermes CLI SVG generation task" in query
    assert str(output_svg) in query
    trace_events = [json.loads(line) for line in trace_path.read_text(encoding="utf-8").splitlines()]
    assert "<prompt:" in " ".join(trace_events[0]["command"])
    assert query not in trace_events[0]["command"]
