"""Actual shared settings, tool transports and native files; no model mocks."""
import json
import os
from pathlib import Path
import subprocess
import sys

from drawai.cli import main
from drawai.runtime_paths import initialize_home, workspace_path, read_preferences
from drawai.shared_tools import plan_session
from drawai.session_install import install_session


def test_setup_reuses_existing_workspace_without_overwriting_settings(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("DRAWAI_HOME", str(tmp_path / "home"))
    monkeypatch.delenv("DRAWAI_WORKBENCH_WORKSPACE", raising=False)
    old = tmp_path / "existing"
    old.mkdir()
    sentinel = old / "user-file.txt"
    sentinel.write_text("keep")
    assert main(["setup", "--workspace", str(old)]) == 0
    assert workspace_path() == old
    assert sentinel.read_text() == "keep"
    config = tmp_path / "home/config.yaml"
    initial = config.read_bytes()
    assert main(["setup"]) == 0
    assert config.read_bytes() == initial
    capsys.readouterr()


def test_session_and_cli_share_api_connections_and_image_preferences(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("DRAWAI_HOME", str(tmp_path / "home"))
    monkeypatch.delenv("DRAWAI_WORKBENCH_WORKSPACE", raising=False)
    monkeypatch.setenv("DRAWAI_TEST_IMAGE_KEY", "test-credential")
    presets = tmp_path / "connections.json"
    presets.write_text(json.dumps({"presets": [{"id": "visuals", "type": "images_api", "label": "Personal visuals", "base_url": "https://example.invalid/v1", "model": "user-image-model", "api_key_env": "DRAWAI_TEST_IMAGE_KEY"}]}))
    assert main(["config", "connections", "--import", str(presets)]) == 0
    assert main(["config", "image", "--source", "api", "--connection", "visuals"]) == 0
    output = capsys.readouterr().out
    assert "test-credential" not in output
    from drawai.workbench.api_presets import read_workbench_api_presets
    assert read_workbench_api_presets(workspace_path())[0].id == "visuals"
    plan = plan_session({"environment": {"agent": "claude", "model": "claude-user-model", "image_viewing_available": True, "local_execution_available": True, "image_generation_available": True}, "preferences": {"skip_questions": True}})
    assert plan["design"]["connection"] == "visuals"
    assert plan["design"]["method"] == "image_generation_api"
    assert plan["implementation"]["agent"] == "claude"
    assert plan["implementation"]["configuration_source"] == "caller_session"


def test_generic_adapter_contains_thin_skills_and_points_to_installed_core(tmp_path, monkeypatch):
    monkeypatch.setenv("DRAWAI_HOME", str(tmp_path / "home"))
    result = install_session("generic", output_dir=tmp_path / "adapter")
    mcp = json.loads((Path(result["directory"]) / ".mcp.json").read_text())
    server = mcp["mcpServers"]["drawai"]
    assert server["command"] == sys.executable
    assert server["args"] == ["-m", "drawai.mcp_server"]
    assert not (tmp_path / "adapter/skills/drawai-image2ppt/scripts/pptx_skill/document").exists()
    assert server["env"]["DRAWAI_HOME"] == str(tmp_path / "home")


def test_real_stdio_mcp_and_cli_use_the_same_session_plan(tmp_path):
    request = {"environment": {"agent": "codex", "model": "caller-model", "model_source": "session_metadata", "image_viewing_available": True, "local_execution_available": True}, "preferences": {"skip_questions": True}, "inputs": {"visual_page_count": 1, "visual_aspect_ratio": "16:9"}}
    payload = "\n".join(json.dumps(message) for message in [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "integration", "version": "1"}}},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "drawai_plan", "arguments": {"request": request}}},
    ]) + "\n"
    env = {**os.environ, "DRAWAI_HOME": str(tmp_path / "home"), "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src")}
    server = subprocess.run([sys.executable, "-m", "drawai.mcp_server"], input=payload, text=True, capture_output=True, env=env, cwd=tmp_path, check=True, timeout=20)
    responses = [json.loads(line) for line in server.stdout.splitlines()]
    assert responses[0]["result"]["protocolVersion"] == "2025-06-18"
    assert "drawai_image" in {tool["name"] for tool in responses[1]["result"]["tools"]}
    path = tmp_path / "request.json"
    path.write_text(json.dumps(request))
    cli = subprocess.run([sys.executable, "-m", "drawai.cli", "plan", str(path)], text=True, capture_output=True, env=env, cwd=tmp_path, check=True)
    assert json.loads(cli.stdout) == responses[2]["result"]["structuredContent"]
    assert responses[2]["result"]["structuredContent"]["implementation"]["model"] == "caller-model"


def test_dry_run_does_not_install_or_write_configuration(tmp_path, monkeypatch, capsys):
    home = tmp_path / "not-created"
    monkeypatch.setenv("DRAWAI_HOME", str(home))
    assert main(["setup", "--dry-run", "--enable", "models", "--agent", "generic"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert "local" in result["commands"][0]
    assert not home.exists()


def test_workbench_uses_connection_references_without_a_browser_supplied_key(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from drawai.workbench.api import create_app
    from drawai.workbench.models import WorkbenchSettings
    monkeypatch.setenv("DRAWAI_HOME", str(tmp_path / "home"))
    monkeypatch.delenv("DRAWAI_WORKBENCH_WORKSPACE", raising=False)
    monkeypatch.delenv("DRAWAI_MISSING_TEST_KEY", raising=False)
    initialize_home()
    from drawai.workbench.api_presets import write_workbench_api_presets
    write_workbench_api_presets(workspace_path(), {"presets": [{"id": "shared-images", "type": "images_api", "base_url": "https://example.invalid/v1", "model": "configured-image-model", "api_key_env": "DRAWAI_MISSING_TEST_KEY"}]})
    settings = WorkbenchSettings(workspace=workspace_path(), default_config=tmp_path / "home/config.yaml")
    with TestClient(create_app(settings)) as client:
        response = client.post("/api/imagegen/generations", json={"api_preset_id": "shared-images", "prompt": "page"})
        assert response.status_code == 503
        assert "DRAWAI_MISSING_TEST_KEY" in response.json()["detail"]
        response = client.post("/api/imagegen/generations", json={"api_preset_id": "unknown", "prompt": "page"})
        assert response.status_code == 400
