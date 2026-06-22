import json
from pathlib import Path
import sqlite3
import sys
import threading
import time
from types import SimpleNamespace

import pytest

import drawai.codex_python_sdk_svg as codex_sdk_svg
from drawai.codex_python_sdk_svg import (
    CodexPythonSdkSvgError,
    _isolated_codex_home,
    _run_thread_with_timeout,
    build_codex_svg_output_schema,
    check_codex_python_sdk_connectivity,
    controlled_codex_config_overrides,
    invoke_codex_python_sdk_svg_text,
    parse_svg_from_final_response,
)


def test_codex_python_sdk_output_schema_requires_only_svg():
    schema = build_codex_svg_output_schema()

    assert schema["type"] == "object"
    assert schema["required"] == ["svg"]
    assert schema["additionalProperties"] is False
    assert schema["properties"]["svg"]["type"] == "string"


def test_controlled_codex_config_overrides_disable_agent_surfaces():
    overrides = controlled_codex_config_overrides()

    assert 'web_search="disabled"' in overrides
    assert "features.shell_tool=true" in overrides
    assert "features.rmcp_client=false" in overrides
    assert "features.multi_agent=false" in overrides
    assert "features.memories=false" in overrides
    assert "features.hooks=false" in overrides
    assert "project_doc_max_bytes=0" in overrides
    assert 'sandbox_mode="danger-full-access"' in overrides
    assert 'shell_environment_policy.ignore_default_excludes=false' in overrides
    assert 'shell_environment_policy.exclude=["CODEX_HOME","DRAWAI_HOST_HOME","DRAWAI_HOST_CODEX_HOME"]' in overrides


def test_controlled_codex_config_overrides_can_inherit_host_model_provider(monkeypatch, tmp_path):
    host_codex_home = tmp_path / "host_codex"
    host_codex_home.mkdir()
    (host_codex_home / "config.toml").write_text(
        """
model_provider = "custom"
model = "gpt-5.5"

[model_providers.custom]
name = "custom"
wire_api = "responses"
requires_openai_auth = true
base_url = "http://127.0.0.1:15721/v1"
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("DRAWAI_HOST_CODEX_HOME", str(host_codex_home))
    monkeypatch.setenv("DRAWAI_CODEX_INHERIT_HOST_CONFIG", "1")

    overrides = controlled_codex_config_overrides()

    assert 'model_provider="custom"' in overrides
    assert 'model="gpt-5.5"' in overrides
    assert 'model_providers.custom.name="custom"' in overrides
    assert 'model_providers.custom.wire_api="responses"' in overrides
    assert "model_providers.custom.requires_openai_auth=true" in overrides
    assert 'model_providers.custom.base_url="http://127.0.0.1:15721/v1"' in overrides


def test_controlled_codex_config_overrides_quotes_provider_key(monkeypatch, tmp_path):
    host_codex_home = tmp_path / "host_codex"
    host_codex_home.mkdir()
    (host_codex_home / "config.toml").write_text(
        """
model_provider = "custom.proxy"
model = "gpt-5.5"

[model_providers."custom.proxy"]
name = "custom.proxy"
wire_api = "responses"
base_url = "http://127.0.0.1:15721/v1"
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("DRAWAI_HOST_CODEX_HOME", str(host_codex_home))
    monkeypatch.setenv("DRAWAI_CODEX_INHERIT_HOST_CONFIG", "1")

    overrides = controlled_codex_config_overrides()

    assert 'model_provider="custom.proxy"' in overrides
    assert 'model_providers."custom.proxy".base_url="http://127.0.0.1:15721/v1"' in overrides


def test_controlled_codex_config_overrides_rejects_invalid_host_config(monkeypatch, tmp_path):
    host_codex_home = tmp_path / "host_codex"
    host_codex_home.mkdir()
    (host_codex_home / "config.toml").write_text('model_provider = "custom', encoding="utf-8")
    monkeypatch.setenv("DRAWAI_HOST_CODEX_HOME", str(host_codex_home))
    monkeypatch.setenv("DRAWAI_CODEX_INHERIT_HOST_CONFIG", "1")

    with pytest.raises(CodexPythonSdkSvgError, match="invalid TOML"):
        controlled_codex_config_overrides()


def test_controlled_codex_config_overrides_allows_model_env_override(monkeypatch, tmp_path):
    host_codex_home = tmp_path / "host_codex"
    host_codex_home.mkdir()
    (host_codex_home / "config.toml").write_text(
        """
model_provider = "custom"
model = "gpt-5.4"

[model_providers.custom]
name = "custom"
wire_api = "responses"
base_url = "http://127.0.0.1:15721/v1"
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("DRAWAI_HOST_CODEX_HOME", str(host_codex_home))
    monkeypatch.setenv("DRAWAI_CODEX_INHERIT_HOST_CONFIG", "1")
    monkeypatch.setenv("DRAWAI_CODEX_MODEL", "gpt-5.5")

    overrides = controlled_codex_config_overrides()

    assert 'model="gpt-5.5"' in overrides
    assert 'model="gpt-5.4"' not in overrides


def test_isolated_codex_home_copies_auth_without_global_agents(monkeypatch, tmp_path):
    host_codex_home = tmp_path / "host_codex"
    host_codex_home.mkdir()
    (host_codex_home / "auth.json").write_text('{"OPENAI_API_KEY":"sk-test"}', encoding="utf-8")
    (host_codex_home / "AGENTS.md").write_text("global instruction", encoding="utf-8")
    monkeypatch.setenv("DRAWAI_HOST_CODEX_HOME", str(host_codex_home))

    with _isolated_codex_home(tmp_path / "workspace") as prepared:
        assert prepared.codex_home != host_codex_home
        assert prepared.auth_copied is True
        assert (prepared.codex_home / "auth.json").read_text(encoding="utf-8") == '{"OPENAI_API_KEY":"sk-test"}'
        assert not (prepared.codex_home / "AGENTS.md").exists()
        assert not (prepared.codex_home / "AGENTS.override.md").exists()

    assert not prepared.codex_home.exists()


def test_invoke_codex_python_sdk_lets_codex_write_svg_in_workspace(monkeypatch, tmp_path):
    seen = {}
    output_svg_path = tmp_path / "attempt" / "semantic.svg"
    output_response_path = tmp_path / "attempt" / "model_response.txt"

    class FakeResult:
        final_response = "wrote semantic.svg"
        duration_ms = 1

    class FakeThread:
        def run(self, run_input, **kwargs):
            seen["run_input"] = run_input
            seen["run_kwargs"] = kwargs
            output_svg_path.parent.mkdir(parents=True, exist_ok=True)
            output_svg_path.write_text(
                '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1"></svg>',
                encoding="utf-8",
            )
            output_response_path.write_text("wrote semantic.svg\n", encoding="utf-8")
            codex_home = Path(seen["config"]["env"]["CODEX_HOME"])
            session_log = (
                codex_home / "sessions" / "2026" / "06" / "08" / "rollout-test.jsonl"
            )
            session_log.parent.mkdir(parents=True, exist_ok=True)
            session_log.write_text('{"event":"tool"}\n', encoding="utf-8")
            runtime_log = codex_home / "log" / "codex-tui.log"
            runtime_log.parent.mkdir(parents=True, exist_ok=True)
            runtime_log.write_text("tool log\n", encoding="utf-8")
            (codex_home / "history.jsonl").write_text(
                '{"session":"unit"}\n',
                encoding="utf-8",
            )
            (codex_home / "auth.json").write_text("secret", encoding="utf-8")
            return FakeResult()

    class FakeCodex:
        def __init__(self, config):
            seen["config"] = config

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def thread_start(self, **kwargs):
            seen["thread_start_kwargs"] = kwargs
            return FakeThread()

    fake_openai_codex = SimpleNamespace(
        ApprovalMode=SimpleNamespace(deny_all="deny_all"),
        Sandbox=SimpleNamespace(read_only="read_only", workspace_write="workspace_write", full_access="full_access"),
        Codex=FakeCodex,
        CodexConfig=lambda **kwargs: kwargs,
        TextInput=lambda text: ("text", text),
        LocalImageInput=lambda path: ("image", path),
    )
    monkeypatch.setitem(sys.modules, "openai_codex", fake_openai_codex)
    image_path = tmp_path / "input.png"
    image_path.write_bytes(b"fake image bytes")
    trace_path = tmp_path / "trace.jsonl"

    svg = invoke_codex_python_sdk_svg_text(
        image_paths=image_path,
        prompt="Use the files in this workspace.",
        task_name="unit_test_workspace_writer",
        runtime_config={"model_name": "fake-model", "timeout_seconds": 1},
        trace_path=trace_path,
        isolated_cwd=tmp_path,
        output_svg_path=output_svg_path,
        output_response_path=output_response_path,
    )

    assert svg == '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1"></svg>'
    assert seen["config"]["env"]["CODEX_HOME"] != str(tmp_path)
    assert seen["thread_start_kwargs"]["config"] == {"model_reasoning_effort": "xhigh"}
    assert seen["thread_start_kwargs"]["sandbox"] == "full_access"
    assert seen["run_kwargs"]["effort"] == "xhigh"
    assert seen["run_kwargs"]["sandbox"] == "full_access"
    assert "Write the SVG file yourself" in seen["run_input"][0][1]
    assert str(output_svg_path) in seen["run_input"][0][1]
    assert output_response_path.read_text(encoding="utf-8") == "wrote semantic.svg\n"
    archive_dir = output_response_path.parent / "codex_session_log"
    assert (
        archive_dir / "sessions" / "2026" / "06" / "08" / "rollout-test.jsonl"
    ).read_text(encoding="utf-8") == '{"event":"tool"}\n'
    assert (
        archive_dir / "log" / "codex-tui.log"
    ).read_text(encoding="utf-8") == "tool log\n"
    assert (
        archive_dir / "history.jsonl"
    ).read_text(encoding="utf-8") == '{"session":"unit"}\n'
    assert not (archive_dir / "auth.json").exists()
    manifest = json.loads(
        (archive_dir / "manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["schema"] == "drawai.codex_session_log_archive.v1"
    assert manifest["archive_dir"] == str(archive_dir)
    assert manifest["auth_json_copied"] is False
    assert "sessions" in manifest["copied"]
    assert "log" in manifest["copied"]
    assert "history.jsonl" in manifest["copied"]
    events = [
        json.loads(line) for line in trace_path.read_text(encoding="utf-8").splitlines()
    ]
    assert events[0]["sandbox"] == "danger-full-access"
    assert events[0]["session_log_archive_path"] == str(archive_dir)
    assert events[0]["reasoning_effort"] == "xhigh"
    assert events[0]["codex_home"]["isolated"] is True
    assert events[0]["codex_home"]["auth_copied"] in {True, False}
    assert events[0]["codex_home"]["agents_md_present"] is False
    archive_events = [
        event for event in events if event["type"] == "codex_python_sdk_session_log_archive"
    ]
    assert len(archive_events) == 1
    assert archive_events[0]["archive"]["archive_dir"] == str(archive_dir)
    assert events[-1]["source"] == "output_svg_path"


def test_archive_codex_session_logs_preserves_live_runtime_tail_without_sqlite(tmp_path):
    codex_home = tmp_path / "codex_home"
    codex_home.mkdir()
    archive_dir = tmp_path / "archive"
    archive_dir.mkdir()
    live_tail = archive_dir / "codex_runtime_events.jsonl"
    live_tail.write_text('{"event_type":"response.output_text.delta"}\n', encoding="utf-8")

    manifest = codex_sdk_svg._archive_codex_session_logs(
        codex_home,
        archive_dir,
        task_name="unit_test",
        sdk_turn_result=None,
    )

    assert live_tail.read_text(encoding="utf-8") == '{"event_type":"response.output_text.delta"}\n'
    assert "codex_runtime_events.jsonl" in manifest["copied"]
    assert manifest["runtime_event_tail"]["status"] == "missing"
    assert manifest["runtime_event_tail"]["preserved_live_path"] == str(live_tail)


def test_archive_codex_session_logs_merges_existing_live_snapshot_dirs(tmp_path):
    codex_home = tmp_path / "codex_home"
    (codex_home / "shell_snapshots").mkdir(parents=True)
    (codex_home / "shell_snapshots" / "final.sh").write_text("echo final\n", encoding="utf-8")
    archive_dir = tmp_path / "archive"
    (archive_dir / "shell_snapshots").mkdir(parents=True)
    (archive_dir / "shell_snapshots" / "live.sh").write_text("echo live\n", encoding="utf-8")

    manifest = codex_sdk_svg._archive_codex_session_logs(
        codex_home,
        archive_dir,
        task_name="unit_test",
        sdk_turn_result=None,
    )

    assert "shell_snapshots" in manifest["copied"]
    assert (archive_dir / "shell_snapshots" / "live.sh").read_text(encoding="utf-8") == "echo live\n"
    assert (archive_dir / "shell_snapshots" / "final.sh").read_text(encoding="utf-8") == "echo final\n"


def test_archive_codex_session_logs_extracts_websocket_runtime_tail(tmp_path):
    codex_home = tmp_path / "codex_home"
    codex_home.mkdir()
    db_path = codex_home / "logs_2.sqlite"
    connection = sqlite3.connect(db_path)
    try:
        connection.execute(
            "create table logs (id integer primary key, ts integer, ts_nanos integer, level text, target text, feedback_log_body text)"
        )
        connection.execute(
            "insert into logs values (1, 1, 2, 'TRACE', 'codex_api::endpoint::responses_websocket', ?)",
            ('websocket event: {"type":"response.output_text.delta","delta":"hello"}',),
        )
        connection.commit()
    finally:
        connection.close()

    archive_dir = tmp_path / "archive"
    manifest = codex_sdk_svg._archive_codex_session_logs(
        codex_home,
        archive_dir,
        task_name="unit_test",
        sdk_turn_result=None,
    )

    assert manifest["runtime_event_tail"]["status"] == "ok"
    event = json.loads((archive_dir / "codex_runtime_events.jsonl").read_text(encoding="utf-8"))
    assert event["event_type"] == "response.output_text.delta"
    assert event["event"]["delta"] == "hello"


def test_archive_codex_runtime_tail_summarizes_large_websocket_payloads(tmp_path):
    codex_home = tmp_path / "codex_home"
    codex_home.mkdir()
    db_path = codex_home / "logs_2.sqlite"
    connection = sqlite3.connect(db_path)
    try:
        connection.execute(
            "create table logs (id integer primary key, ts integer, ts_nanos integer, level text, target text, feedback_log_body text)"
        )
        connection.execute(
            "insert into logs values (1, 1, 2, 'TRACE', 'codex_api::endpoint::responses_websocket', ?)",
            (
                'websocket event: {"type":"response.in_progress",'
                '"response":{"id":"resp_1","status":"in_progress","instructions":"secret instructions"},'
                '"item":{"id":"rs_1","type":"reasoning","encrypted_content":"ciphertext"}}',
            ),
        )
        connection.commit()
    finally:
        connection.close()

    archive_dir = tmp_path / "archive"
    codex_sdk_svg._archive_codex_session_logs(
        codex_home,
        archive_dir,
        task_name="unit_test",
        sdk_turn_result=None,
    )

    text = (archive_dir / "codex_runtime_events.jsonl").read_text(encoding="utf-8")
    assert "secret instructions" not in text
    assert "ciphertext" not in text
    event = json.loads(text)
    assert event["event_type"] == "response.in_progress"
    assert event["message"] == "reasoning"
    assert event["event"]["item"]["encrypted_content"] == "[redacted]"
    assert event["event"]["response"]["status"] == "in_progress"


def test_codex_python_sdk_session_reuses_one_thread_for_multiple_turns(
    monkeypatch, tmp_path
):
    seen = {
        "configs": [],
        "thread_start_kwargs": [],
        "run_inputs": [],
        "run_kwargs": [],
    }
    outputs = [
        tmp_path / "attempt_1" / "semantic.svg",
        tmp_path / "attempt_2" / "semantic.svg",
    ]
    responses = [
        tmp_path / "attempt_1" / "model_response.txt",
        tmp_path / "attempt_2" / "model_response.txt",
    ]

    class FakeResult:
        status = SimpleNamespace(value="completed")
        started_at = 1
        completed_at = 2
        duration_ms = 1
        final_response = "wrote semantic.svg"
        usage = {"total": {"totalTokens": 3}}

        def __init__(self, turn_index):
            self.id = f"turn-{turn_index + 1}"
            self.items = [
                {
                    "type": "agentMessage",
                    "turn": turn_index + 1,
                    "text": "done",
                }
            ]

    class FakeThread:
        id = "thread-reused"

        def run(self, run_input, **kwargs):
            turn_index = len(seen["run_inputs"])
            seen["run_inputs"].append(run_input)
            seen["run_kwargs"].append(kwargs)
            outputs[turn_index].parent.mkdir(parents=True, exist_ok=True)
            outputs[turn_index].write_text(
                '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1"></svg>',
                encoding="utf-8",
            )
            responses[turn_index].write_text(
                f"turn {turn_index + 1}\n",
                encoding="utf-8",
            )
            codex_home = Path(seen["configs"][0]["env"]["CODEX_HOME"])
            session_log = codex_home / "sessions" / f"turn-{turn_index + 1}.jsonl"
            session_log.parent.mkdir(parents=True, exist_ok=True)
            session_log.write_text(
                json.dumps({"turn": turn_index + 1}) + "\n",
                encoding="utf-8",
            )
            return FakeResult(turn_index)

    class FakeCodex:
        def __init__(self, config):
            seen["configs"].append(config)

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            seen["closed"] = True
            return False

        def thread_start(self, **kwargs):
            seen["thread_start_kwargs"].append(kwargs)
            return FakeThread()

    fake_openai_codex = SimpleNamespace(
        ApprovalMode=SimpleNamespace(deny_all="deny_all"),
        Sandbox=SimpleNamespace(read_only="read_only", workspace_write="workspace_write", full_access="full_access"),
        Codex=FakeCodex,
        CodexConfig=lambda **kwargs: kwargs,
        TextInput=lambda text: ("text", text),
        LocalImageInput=lambda path: ("image", path),
    )
    monkeypatch.setitem(sys.modules, "openai_codex", fake_openai_codex)
    image_path = tmp_path / "input.png"
    image_path.write_bytes(b"fake image bytes")
    trace_path = tmp_path / "trace.jsonl"
    shared_prompt = "SHARED DRAWAI THREAD CONTEXT"

    with codex_sdk_svg.CodexPythonSdkSvgSession(
        runtime_config={"model_name": "fake-model", "timeout_seconds": 1},
        trace_path=trace_path,
        isolated_cwd=tmp_path,
        shared_prompt=shared_prompt,
    ) as session:
        first_svg = session.invoke(
            image_paths=image_path,
            prompt="TURN ONE ONLY",
            task_name="unit.thread.turn_one",
            output_svg_path=outputs[0],
            output_response_path=responses[0],
        )
        second_svg = session.invoke(
            image_paths=image_path,
            prompt="TURN TWO ONLY",
            task_name="unit.thread.turn_two",
            output_svg_path=outputs[1],
            output_response_path=responses[1],
        )

    assert first_svg.startswith("<svg")
    assert second_svg.startswith("<svg")
    assert len(seen["configs"]) == 1
    assert len(seen["thread_start_kwargs"]) == 1
    assert shared_prompt in json.dumps(seen["thread_start_kwargs"][0], default=str)
    assert len(seen["run_inputs"]) == 2
    assert "TURN ONE ONLY" in seen["run_inputs"][0][0][1]
    assert "TURN TWO ONLY" in seen["run_inputs"][1][0][1]
    assert shared_prompt not in seen["run_inputs"][0][0][1]
    assert shared_prompt not in seen["run_inputs"][1][0][1]
    assert seen["run_kwargs"][0]["model"] == "fake-model"
    assert seen["run_kwargs"][1]["model"] == "fake-model"
    assert seen["closed"] is True

    for response_path, task_name in zip(
        responses,
        ["unit.thread.turn_one", "unit.thread.turn_two"],
        strict=True,
    ):
        archive_dir = response_path.parent / "codex_session_log"
        summary = json.loads(
            (archive_dir / "turn_result_summary.json").read_text(encoding="utf-8")
        )
        assert summary["task_name"] == task_name
        assert (archive_dir / "codex_session_events.jsonl").is_file()

    events = [
        json.loads(line) for line in trace_path.read_text(encoding="utf-8").splitlines()
    ]
    thread_events = [
        event
        for event in events
        if event["type"] == "codex_python_sdk_thread_start"
    ]
    request_events = [
        event for event in events if event["type"] == "codex_python_sdk_request"
    ]
    assert len(thread_events) == 1
    assert [event["thread_id"] for event in request_events] == [
        "thread-reused",
        "thread-reused",
    ]
    assert request_events[0]["turn_index"] == 1
    assert request_events[1]["turn_index"] == 2


def test_invoke_codex_python_sdk_archives_sdk_turn_items_without_cli_logs(
    monkeypatch, tmp_path
):
    output_svg_path = tmp_path / "attempt" / "semantic.svg"
    output_response_path = tmp_path / "attempt" / "model_response.txt"

    class FakeSdkModel:
        def __init__(self, payload):
            self.payload = payload

        def model_dump(self, **_kwargs):
            return self.payload

    class FakeResult:
        id = "turn-test"
        status = SimpleNamespace(value="completed")
        started_at = 10
        completed_at = 20
        duration_ms = 10
        final_response = "wrote semantic.svg"
        items = [
            FakeSdkModel(
                {
                    "type": "commandExecution",
                    "command": "printf svg > semantic.svg",
                    "status": "completed",
                }
            ),
            FakeSdkModel(
                {
                    "type": "agentMessage",
                    "phase": "final_answer",
                    "text": "done",
                }
            ),
        ]
        usage = FakeSdkModel({"total": {"totalTokens": 7}})

    class FakeThread:
        def run(self, *_args, **_kwargs):
            output_svg_path.parent.mkdir(parents=True, exist_ok=True)
            output_svg_path.write_text(
                '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1"></svg>',
                encoding="utf-8",
            )
            output_response_path.write_text("wrote semantic.svg\n", encoding="utf-8")
            return FakeResult()

    class FakeCodex:
        def __init__(self, _config):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def thread_start(self, **_kwargs):
            return FakeThread()

    fake_openai_codex = SimpleNamespace(
        ApprovalMode=SimpleNamespace(deny_all="deny_all"),
        Sandbox=SimpleNamespace(read_only="read_only", workspace_write="workspace_write", full_access="full_access"),
        Codex=FakeCodex,
        CodexConfig=lambda **kwargs: kwargs,
        TextInput=lambda text: ("text", text),
        LocalImageInput=lambda path: ("image", path),
    )
    monkeypatch.setitem(sys.modules, "openai_codex", fake_openai_codex)
    image_path = tmp_path / "input.png"
    image_path.write_bytes(b"fake image bytes")

    invoke_codex_python_sdk_svg_text(
        image_paths=image_path,
        prompt="Use the files in this workspace.",
        task_name="unit_test_sdk_items_archive",
        runtime_config={"model_name": "fake-model", "timeout_seconds": 1},
        trace_path=tmp_path / "trace.jsonl",
        isolated_cwd=tmp_path,
        output_svg_path=output_svg_path,
        output_response_path=output_response_path,
    )

    archive_dir = output_response_path.parent / "codex_session_log"
    summary = json.loads(
        (archive_dir / "turn_result_summary.json").read_text(encoding="utf-8")
    )
    assert summary["schema"] == "drawai.codex_sdk_turn_result.v1"
    assert summary["task_name"] == "unit_test_sdk_items_archive"
    assert summary["turn_id"] == "turn-test"
    assert summary["status"] == "completed"
    assert summary["item_count"] == 2
    assert summary["usage"] == {"total": {"totalTokens": 7}}

    event_lines = (archive_dir / "codex_session_events.jsonl").read_text(
        encoding="utf-8"
    ).splitlines()
    events = [json.loads(line) for line in event_lines]
    assert [event["item"]["type"] for event in events] == [
        "commandExecution",
        "agentMessage",
    ]
    assert events[0]["turn_id"] == "turn-test"
    assert events[0]["index"] == 1

    manifest = json.loads(
        (archive_dir / "manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["sdk_turn_result"]["event_count"] == 2
    assert manifest["sdk_turn_result"]["events_file"] == "codex_session_events.jsonl"
    assert manifest["sdk_turn_result"]["summary_file"] == "turn_result_summary.json"


def test_parse_svg_from_final_response_json_object():
    svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"></svg>'

    parsed, metadata = parse_svg_from_final_response(json.dumps({"svg": svg, "notes": "ignored"}))

    assert parsed == svg
    assert metadata == {"source": "json_object", "field": "svg"}


def test_parse_svg_from_final_response_rejects_missing_svg():
    with pytest.raises(CodexPythonSdkSvgError, match="svg"):
        parse_svg_from_final_response(json.dumps({"notes": "no svg"}))


def test_run_thread_with_timeout_interrupts_slow_sdk_call():
    class SlowThread:
        def run(self, *_args, **_kwargs):
            time.sleep(1)

    with pytest.raises(CodexPythonSdkSvgError, match="exceeded timeout_seconds=0.01"):
        _run_thread_with_timeout(SlowThread(), [], timeout_seconds=0.01)


def test_run_thread_with_timeout_interrupts_slow_sdk_call_from_worker_thread():
    class SlowThread:
        def run(self, *_args, **_kwargs):
            time.sleep(0.2)
            return "late"

    results = []
    errors = []

    def run_in_worker():
        try:
            results.append(_run_thread_with_timeout(SlowThread(), [], timeout_seconds=0.01))
        except BaseException as exc:  # noqa: BLE001 - test captures worker-thread exception.
            errors.append(exc)

    worker = threading.Thread(target=run_in_worker)
    worker.start()
    worker.join(timeout=1)

    assert not worker.is_alive()
    assert results == []
    assert len(errors) == 1
    assert isinstance(errors[0], CodexPythonSdkSvgError)
    assert "exceeded timeout_seconds=0.01" in str(errors[0])


def test_run_thread_with_timeout_closes_sdk_client_after_worker_timeout():
    class FakeClient:
        def __init__(self):
            self.closed = False

        def close(self):
            self.closed = True

    class SlowThread:
        def __init__(self):
            self._client = FakeClient()

        def run(self, *_args, **_kwargs):
            time.sleep(0.2)
            return "late"

    thread = SlowThread()
    errors = []

    def run_in_worker():
        try:
            _run_thread_with_timeout(thread, [], timeout_seconds=0.01)
        except BaseException as exc:  # noqa: BLE001 - test captures worker-thread exception.
            errors.append(exc)

    worker = threading.Thread(target=run_in_worker)
    worker.start()
    worker.join(timeout=1)

    assert not worker.is_alive()
    assert len(errors) == 1
    assert thread._client.closed is True


def test_run_thread_with_timeout_forwards_run_arguments():
    expected = object()

    class FakeThread:
        def run(self, run_input, **kwargs):
            self.run_input = run_input
            self.kwargs = kwargs
            return expected

    thread = FakeThread()

    result = _run_thread_with_timeout(
        thread,
        ["input"],
        timeout_seconds=1,
        approval_mode="deny",
        cwd="/tmp/cwd",
        model="fake-model",
        output_schema={"type": "object"},
        sandbox="read-only",
    )

    assert result is expected
    assert thread.run_input == ["input"]
    assert thread.kwargs == {
        "approval_mode": "deny",
        "cwd": "/tmp/cwd",
        "model": "fake-model",
        "output_schema": {"type": "object"},
        "sandbox": "read-only",
    }


def test_invoke_codex_python_sdk_records_generic_sdk_errors(monkeypatch, tmp_path):
    seen_config = {}

    class FakeThread:
        def run(self, *_args, **_kwargs):
            codex_home = Path(seen_config["env"]["CODEX_HOME"])
            session_log = (
                codex_home / "sessions" / "2026" / "06" / "08" / "error.jsonl"
            )
            session_log.parent.mkdir(parents=True, exist_ok=True)
            session_log.write_text('{"event":"error"}\n', encoding="utf-8")
            raise RuntimeError("401 Unauthorized: Missing bearer authentication")

    class FakeCodex:
        def __init__(self, config):
            seen_config.update(config)

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def thread_start(self, **_kwargs):
            return FakeThread()

    fake_openai_codex = SimpleNamespace(
        ApprovalMode=SimpleNamespace(deny_all="deny_all"),
        Sandbox=SimpleNamespace(read_only="read_only", workspace_write="workspace_write", full_access="full_access"),
        Codex=FakeCodex,
        CodexConfig=lambda **kwargs: kwargs,
        TextInput=lambda text: ("text", text),
        LocalImageInput=lambda path: ("image", path),
    )
    monkeypatch.setitem(sys.modules, "openai_codex", fake_openai_codex)
    image_path = tmp_path / "input.png"
    image_path.write_bytes(b"fake image bytes")
    trace_path = tmp_path / "trace.jsonl"

    with pytest.raises(CodexPythonSdkSvgError, match="invocation failed"):
        invoke_codex_python_sdk_svg_text(
            image_paths=image_path,
            prompt="Draw the image as SVG.",
            task_name="unit_test_sdk_error",
            runtime_config={"model_name": "fake-model", "timeout_seconds": 1},
            trace_path=trace_path,
            isolated_cwd=tmp_path / "isolated",
        )

    events = [json.loads(line) for line in trace_path.read_text(encoding="utf-8").splitlines()]
    error_events = [event for event in events if event["type"] == "codex_python_sdk_error"]
    assert len(error_events) == 1
    assert error_events[0]["error_type"] == "RuntimeError"
    assert "Missing bearer authentication" in error_events[0]["error"]
    archive_dir = tmp_path / "isolated" / "codex_session_log"
    assert (
        archive_dir / "sessions" / "2026" / "06" / "08" / "error.jsonl"
    ).read_text(encoding="utf-8") == '{"event":"error"}\n'
    archive_events = [
        event for event in events if event["type"] == "codex_python_sdk_session_log_archive"
    ]
    assert len(archive_events) == 1
    assert archive_events[0]["archive"]["archive_dir"] == str(archive_dir)


def test_invoke_codex_python_sdk_copies_auth_to_isolated_home(monkeypatch, tmp_path):
    seen_config = {}

    class FakeResult:
        final_response = json.dumps(
            {"svg": '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1"></svg>'}
        )
        duration_ms = 1

    class FakeThread:
        def run(self, *_args, **_kwargs):
            return FakeResult()

    class FakeCodex:
        def __init__(self, config):
            seen_config.update(config)
            codex_home = Path(config["env"]["CODEX_HOME"])
            seen_config["auth_text"] = (codex_home / "auth.json").read_text(encoding="utf-8")

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def thread_start(self, **_kwargs):
            return FakeThread()

    fake_openai_codex = SimpleNamespace(
        ApprovalMode=SimpleNamespace(deny_all="deny_all"),
        Sandbox=SimpleNamespace(read_only="read_only", workspace_write="workspace_write", full_access="full_access"),
        Codex=FakeCodex,
        CodexConfig=lambda **kwargs: kwargs,
        TextInput=lambda text: ("text", text),
        LocalImageInput=lambda path: ("image", path),
    )
    monkeypatch.setitem(sys.modules, "openai_codex", fake_openai_codex)
    host_home = tmp_path / "real_home"
    host_codex_home = host_home / ".codex"
    host_codex_home.mkdir(parents=True)
    (host_codex_home / "auth.json").write_text('{"auth_mode":"test"}', encoding="utf-8")
    monkeypatch.setenv("DRAWAI_HOST_HOME", str(host_home))
    image_path = tmp_path / "input.png"
    image_path.write_bytes(b"fake image bytes")

    invoke_codex_python_sdk_svg_text(
        image_paths=image_path,
        prompt="Draw the image as SVG.",
        task_name="unit_test_host_home",
        runtime_config={"model_name": "fake-model", "timeout_seconds": 1},
        trace_path=tmp_path / "trace.jsonl",
        isolated_cwd=tmp_path / "isolated",
    )

    assert seen_config["auth_text"] == '{"auth_mode":"test"}'
    assert seen_config["env"]["HOME"] != str(host_home)
    assert seen_config["env"]["CODEX_HOME"] != str(host_codex_home)
    assert seen_config["env"]["HOME"] == str(Path(seen_config["env"]["CODEX_HOME"]).parent)


def test_codex_python_sdk_connectivity_probe_runs_low_effort_turn(monkeypatch, tmp_path):
    seen = {}

    class FakeResult:
        final_response = "OK"

    class FakeThread:
        def run(self, run_input, **kwargs):
            seen["run_input"] = run_input
            seen["run_kwargs"] = kwargs
            return FakeResult()

    class FakeCodex:
        def __init__(self, config):
            seen["config"] = config

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def thread_start(self, **kwargs):
            seen["thread_start_kwargs"] = kwargs
            return FakeThread()

    fake_openai_codex = SimpleNamespace(
        ApprovalMode=SimpleNamespace(deny_all="deny_all"),
        Sandbox=SimpleNamespace(read_only="read_only", workspace_write="workspace_write", full_access="full_access"),
        Codex=FakeCodex,
        CodexConfig=lambda **kwargs: kwargs,
        TextInput=lambda text: ("text", text),
    )
    monkeypatch.setitem(sys.modules, "openai_codex", fake_openai_codex)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("DRAWAI_HOST_HOME", str(tmp_path / "home"))

    detail = check_codex_python_sdk_connectivity(timeout_seconds=1, model_name="fake-model")

    assert detail == "Codex SDK responded with 2 chars"
    assert seen["config"]["env"]["OPENAI_API_KEY"] == "sk-test"
    assert seen["config"]["env"]["HOME"] == str(Path(seen["config"]["env"]["CODEX_HOME"]).parent)
    assert seen["config"]["env"]["HOME"] != str(tmp_path / "home")
    assert seen["thread_start_kwargs"]["config"] == {"model_reasoning_effort": "low"}
    assert seen["thread_start_kwargs"]["model"] == "fake-model"
    assert seen["thread_start_kwargs"]["sandbox"] == "full_access"
    assert seen["run_input"] == [("text", "Reply exactly: OK")]
    assert seen["run_kwargs"]["effort"] == "low"
    assert seen["run_kwargs"]["model"] == "fake-model"
    assert seen["run_kwargs"]["sandbox"] == "full_access"


def test_invoke_codex_python_sdk_uses_codex_default_model_when_unset(monkeypatch, tmp_path):
    seen = {}

    class FakeResult:
        final_response = json.dumps(
            {"svg": '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1"></svg>'}
        )
        duration_ms = 1

    class FakeThread:
        def run(self, _run_input, **kwargs):
            seen["run_kwargs"] = kwargs
            return FakeResult()

    class FakeCodex:
        def __init__(self, _config):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def thread_start(self, **kwargs):
            seen["thread_start_kwargs"] = kwargs
            return FakeThread()

    fake_openai_codex = SimpleNamespace(
        ApprovalMode=SimpleNamespace(deny_all="deny_all"),
        Sandbox=SimpleNamespace(read_only="read_only", workspace_write="workspace_write", full_access="full_access"),
        Codex=FakeCodex,
        CodexConfig=lambda **kwargs: kwargs,
        TextInput=lambda text: ("text", text),
        LocalImageInput=lambda path: ("image", path),
    )
    monkeypatch.setitem(sys.modules, "openai_codex", fake_openai_codex)
    image_path = tmp_path / "input.png"
    image_path.write_bytes(b"fake image bytes")

    invoke_codex_python_sdk_svg_text(
        image_paths=image_path,
        prompt="Draw the image as SVG.",
        task_name="unit_test_default_model",
        runtime_config={"timeout_seconds": 1},
        trace_path=tmp_path / "trace.jsonl",
        isolated_cwd=tmp_path / "isolated",
    )

    assert seen["thread_start_kwargs"]["model"] is None
    assert seen["run_kwargs"]["model"] is None


def test_invoke_codex_python_sdk_accepts_configured_reasoning_effort(monkeypatch, tmp_path):
    seen = {}

    class FakeResult:
        final_response = json.dumps(
            {"svg": '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1"></svg>'}
        )
        duration_ms = 1

    class FakeThread:
        def run(self, _run_input, **kwargs):
            seen["run_kwargs"] = kwargs
            return FakeResult()

    class FakeCodex:
        def __init__(self, _config):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def thread_start(self, **kwargs):
            seen["thread_start_kwargs"] = kwargs
            return FakeThread()

    fake_openai_codex = SimpleNamespace(
        ApprovalMode=SimpleNamespace(deny_all="deny_all"),
        Sandbox=SimpleNamespace(read_only="read_only", workspace_write="workspace_write", full_access="full_access"),
        Codex=FakeCodex,
        CodexConfig=lambda **kwargs: kwargs,
        TextInput=lambda text: ("text", text),
        LocalImageInput=lambda path: ("image", path),
    )
    monkeypatch.setitem(sys.modules, "openai_codex", fake_openai_codex)
    image_path = tmp_path / "input.png"
    image_path.write_bytes(b"fake image bytes")

    invoke_codex_python_sdk_svg_text(
        image_paths=image_path,
        prompt="Draw the image as SVG.",
        task_name="unit_test_reasoning_effort",
        runtime_config={"model_name": "fake-model", "reasoning_effort": "high", "timeout_seconds": 1},
        trace_path=tmp_path / "trace.jsonl",
        isolated_cwd=tmp_path / "isolated",
    )

    assert seen["thread_start_kwargs"]["config"] == {"model_reasoning_effort": "high"}
    assert seen["run_kwargs"]["effort"] == "high"
