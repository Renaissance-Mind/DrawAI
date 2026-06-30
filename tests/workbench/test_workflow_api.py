from __future__ import annotations

import base64
import io
import json
import threading
import urllib.error
import zipfile
from pathlib import Path
from typing import Mapping

import pytest
import yaml
from fastapi.testclient import TestClient
from PIL import Image

from drawai.workflow.agent_execution import AgentExecutionRequest, AgentExecutionResult
from drawai.workflow.node_runs import begin_node_run
from drawai.workflow.runner import NodeRunContext
from drawai.workflow.schema import WorkflowNode, WorkflowPort, WorkflowTemplate
from drawai.workbench.agent_settings import WorkbenchAgentSettings
from drawai.workbench import api as api_module
from drawai.workbench.api import create_app
from drawai.workbench.api_presets import (
    api_preset_logo_page_urls,
    api_preset_logo_url_from_html,
)
from drawai.workbench.models import WorkbenchSettings
from drawai.workbench.processor_settings import require_processor_configured
from drawai.workbench.runner import WorkbenchRunner, _workflow_template_with_agent_settings
from drawai.workbench.store import WorkbenchStore
from drawai.workflow.templates import load_workflow_template_by_id, user_workflow_template_path


def test_workbench_workflow_template_api_lists_and_copies_templates(tmp_path: Path) -> None:
    client = _client(tmp_path)

    list_response = client.get("/api/workflow/templates")
    assert list_response.status_code == 200
    assert list_response.json()["templates"][0]["template_id"] == "default_drawai_dag"

    copy_response = client.post(
        "/api/workflow/templates/copy",
        json={"template_id": "default_drawai_dag", "name": "Workbench Copy"},
    )
    assert copy_response.status_code == 200
    copied = copy_response.json()["template"]
    assert copied["template_id"] == "custom_workbench_copy"
    assert copied["defaults"]["read_only"] is False

    loaded = load_workflow_template_by_id(tmp_path / "workspace", copied["template_id"])
    assert loaded.name == "Workbench Copy"


def test_workbench_api_allows_local_vite_fallback_ports(tmp_path: Path) -> None:
    client = _client(tmp_path)

    response = client.options(
        "/api/workflow/templates",
        headers={
            "Origin": "http://127.0.0.1:5178",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:5178"


def test_workbench_workflow_template_api_saves_and_validates_templates(tmp_path: Path) -> None:
    client = _client(tmp_path)
    copied = client.post(
        "/api/workflow/templates/copy",
        json={"template_id": "default_drawai_dag", "name": "Editable"},
    ).json()["template"]
    copied["name"] = "Edited In Workbench"

    save_response = client.put(f"/api/workflow/templates/{copied['template_id']}", json=copied)
    assert save_response.status_code == 200
    assert save_response.json()["template"]["name"] == "Edited In Workbench"

    validate_response = client.post("/api/workflow/templates/validate", json=copied)
    assert validate_response.status_code == 200
    assert validate_response.json()["validation"]["ok"] is True


def test_workbench_workflow_agent_prompt_preview_uses_connected_inputs(tmp_path: Path) -> None:
    client = _client(tmp_path)

    response = client.post(
        "/api/workflow/agent-prompt-preview",
        json={
            "preset_id": "run0_element_refine",
            "node_config": {
                "node_id": "run0_agent",
                "provider_id": "kimi_cli",
                "task": "Refine the connected element plans from the current node settings.",
                "constraints": ["Return the declared JSON output only."],
            },
            "inputs": [
                {
                    "path": "nodes/fusion/runs/001/output/elements.json",
                    "format_id": "drawai.element_plans.v1",
                    "type": "element_plans",
                    "description": "Fused element plans.",
                }
            ],
        },
    )

    assert response.status_code == 200
    payload = response.json()["prompt"]
    assert payload["provider_id"] == "kimi_cli"
    assert "# Run0 Element Refinement" not in payload["text"]
    assert "<workflow_run_root>/nodes/run0_agent/runs/<attempt_id>" in payload["text"]
    assert "input_manifest.json" not in payload["text"]
    assert "From Agent cwd：nodes/fusion/runs/001/output/elements.json" in payload["text"]
    assert "## DrawAI 工具" in payload["text"]
    assert "Type `element_plans`" in payload["text"]
    assert "Refine the connected element plans from the current node settings." in payload["text"]
    assert "Return the declared JSON output only." in payload["text"]
    assert "Fused element plans." in payload["text"]


def test_workbench_workflow_provider_api_lists_provider_scoped_limits(tmp_path: Path) -> None:
    client = _client(tmp_path)

    response = client.get("/api/workflow/providers")

    assert response.status_code == 200
    providers = {item["provider_id"]: item for item in response.json()["providers"]}
    assert providers["codex_sdk"]["resource_key"] == "agent_provider:codex_sdk"
    assert providers["kimi_cli"]["resource_key"] == "agent_provider:kimi_cli"
    for provider_id in (
        "kimi_acp",
        "gemini_acp",
        "qwen_acp",
        "opencode_acp",
        "goose_acp",
        "kiro_acp",
        "qoder_acp",
        "cursor_acp",
        "cline_acp",
        "copilot_acp",
        "hermes_acp",
    ):
        assert providers[provider_id]["resource_key"] == f"agent_provider:{provider_id}"
    assert providers["drawai_tool_agent"]["label"] == "内置 Agent"
    assert providers["drawai_tool_agent"]["kind"] == "api"


def test_workbench_agent_settings_api_discovers_validates_and_saves_cli_provider(
    tmp_path: Path,
    monkeypatch,
) -> None:
    bin_dir = tmp_path / "bin"
    kimi = _write_executable(bin_dir / "kimi", "echo 'kimi 1.2.3'\n")
    gemini = _write_executable(bin_dir / "gemini", "echo 'gemini 1.2.3'\n")
    qwen = _write_executable(bin_dir / "qwen", "echo 'qwen 1.2.3'\n")
    opencode = _write_executable(bin_dir / "opencode", "echo 'opencode 1.2.3'\n")
    goose = _write_executable(bin_dir / "goose", "echo 'goose 1.2.3'\n")
    kiro = _write_executable(bin_dir / "kiro-cli", "echo 'kiro 1.2.3'\n")
    qoder = _write_executable(bin_dir / "qodercli", "echo 'qoder 1.2.3'\n")
    cursor = _write_executable(bin_dir / "agent", "echo 'cursor 1.2.3'\n")
    cline = _write_executable(bin_dir / "cline", "echo 'cline 1.2.3'\n")
    copilot = _write_executable(bin_dir / "copilot", "echo 'copilot 1.2.3'\n")
    hermes = _write_executable(bin_dir / "hermes", "echo 'hermes 1.2.3'\n")
    monkeypatch.setenv("PATH", str(bin_dir))
    client = _client(tmp_path)

    response = client.get("/api/workbench/agent-settings")

    assert response.status_code == 200
    agents = {item["provider_id"]: item for item in response.json()["agents"]}
    assert agents["kimi_cli"]["available"] is True
    assert agents["kimi_cli"]["status"] == "ok"
    assert agents["kimi_cli"]["executable_path"] == str(kimi)
    assert agents["kimi_cli"]["version"] == "kimi 1.2.3"
    assert agents["kimi_acp"]["available"] is True
    assert agents["kimi_acp"]["command"] == [str(kimi), "acp"]
    assert agents["gemini_acp"]["command"] == [str(gemini), "--experimental-acp"]
    assert agents["qwen_acp"]["command"] == [str(qwen), "--acp"]
    assert agents["opencode_acp"]["command"] == [str(opencode), "acp"]
    assert agents["goose_acp"]["command"] == [str(goose), "acp"]
    assert agents["kiro_acp"]["command"] == [str(kiro), "acp"]
    assert agents["qoder_acp"]["command"] == [str(qoder), "--acp"]
    assert agents["cursor_acp"]["command"] == [str(cursor), "acp"]
    assert agents["cline_acp"]["command"] == [str(cline), "--acp"]
    assert agents["copilot_acp"]["command"] == [str(copilot), "--acp", "--stdio"]
    assert agents["hermes_acp"]["command"] == [str(hermes), "acp"]
    assert agents["drawai_tool_agent"]["available"] is True
    assert agents["drawai_tool_agent"]["label"] == "内置 Agent"
    assert agents["drawai_tool_agent"]["kind"] == "api"

    save_response = client.put(
        "/api/workbench/agent-settings",
        json={
            "selected_provider_id": "kimi_cli",
            "model": "kimi-code/kimi-for-coding",
            "reasoning_effort": "high",
            "fast": True,
            "timeout_seconds": 3600,
            "llm_model": "minimax/minimax-m3",
            "llm_base_url": "https://openrouter.ai/api/v1",
            "llm_api_key_env": "OPENROUTER_API_KEY",
            "llm_wire_api": "chat_completions",
            "llm_extra_body": {"reasoning": {"enabled": True}},
        },
    )

    assert save_response.status_code == 200
    settings = save_response.json()["settings"]
    assert settings["selected_provider_id"] == "kimi_cli"
    assert settings["fast"] is True
    assert settings["model"] == "kimi-code/kimi-for-coding"
    assert settings["reasoning_effort"] == "high"
    assert settings["timeout_seconds"] == 3600
    assert "execution_mode" not in settings
    assert settings["llm_model"] == "minimax/minimax-m3"
    assert settings["llm_base_url"] == "https://openrouter.ai/api/v1"
    assert settings["llm_api_key_env"] == "OPENROUTER_API_KEY"
    assert settings["llm_wire_api"] == "chat_completions"
    assert settings["llm_extra_body"] == {"reasoning": {"enabled": True}}


def test_workbench_agent_settings_api_can_skip_agent_discovery(tmp_path: Path) -> None:
    client = _client(tmp_path)

    response = client.get("/api/workbench/agent-settings?include_agents=false")

    assert response.status_code == 200
    payload = response.json()
    assert payload["settings"]["selected_provider_id"] == "codex_sdk"
    assert payload["agents"] == []

    save_response = client.put(
        "/api/workbench/agent-settings?include_agents=false",
        json={"selected_provider_id": "codex_cli", "model": "gpt-5"},
    )

    assert save_response.status_code == 200
    save_payload = save_response.json()
    assert save_payload["settings"]["selected_provider_id"] == "codex_cli"
    assert save_payload["settings"]["model"] == "gpt-5"
    assert save_payload["agents"] == []


def test_workbench_agent_settings_api_uses_startup_agent_snapshot_until_refresh(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first_bin = tmp_path / "first-bin"
    second_bin = tmp_path / "second-bin"
    first_kimi = _write_executable(first_bin / "kimi", "echo 'kimi first'\n")
    second_kimi = _write_executable(second_bin / "kimi", "echo 'kimi second'\n")
    monkeypatch.setenv("PATH", str(first_bin))
    client = _client(tmp_path)

    first_response = client.get("/api/workbench/agent-settings")

    assert first_response.status_code == 200
    first_agents = {item["provider_id"]: item for item in first_response.json()["agents"]}
    assert first_agents["kimi_cli"]["executable_path"] == str(first_kimi)
    assert first_agents["kimi_cli"]["version"] == "kimi first"

    monkeypatch.setenv("PATH", str(second_bin))
    cached_response = client.get("/api/workbench/agent-settings")

    assert cached_response.status_code == 200
    cached_agents = {item["provider_id"]: item for item in cached_response.json()["agents"]}
    assert cached_agents["kimi_cli"]["executable_path"] == str(first_kimi)
    assert cached_agents["kimi_cli"]["version"] == "kimi first"

    refreshed_response = client.get("/api/workbench/agent-settings?refresh_agents=true")

    assert refreshed_response.status_code == 200
    refreshed_agents = {item["provider_id"]: item for item in refreshed_response.json()["agents"]}
    assert refreshed_agents["kimi_cli"]["executable_path"] == str(second_kimi)
    assert refreshed_agents["kimi_cli"]["version"] == "kimi second"


def test_workbench_agent_settings_api_preserves_explicit_empty_llm_key_env(tmp_path: Path) -> None:
    client = _client(tmp_path)

    save_response = client.put(
        "/api/workbench/agent-settings?include_agents=false",
        json={
            "selected_provider_id": "codex_cli",
            "model": "gpt-5",
            "llm_model": "llama3.1",
            "llm_base_url": "http://localhost:11434/v1",
            "llm_api_key_env": "",
            "llm_wire_api": "chat_completions",
        },
    )

    assert save_response.status_code == 200
    assert save_response.json()["settings"]["llm_api_key_env"] == ""

    read_response = client.get("/api/workbench/agent-settings?include_agents=false")
    assert read_response.status_code == 200
    assert read_response.json()["settings"]["llm_api_key_env"] == ""


def test_workbench_agent_settings_api_requires_api_preset_for_builtin_agent(tmp_path: Path) -> None:
    client = _client(tmp_path)

    response = client.put(
        "/api/workbench/agent-settings",
        json={"selected_provider_id": "drawai_tool_agent"},
    )

    assert response.status_code == 400
    assert "需要选择 API 预设" in response.json()["detail"]


def test_workbench_agent_settings_api_reads_saved_builtin_agent(tmp_path: Path) -> None:
    settings_path = tmp_path / "workspace" / "settings" / "agent.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text(
        json.dumps(
            {
                "selected_provider_id": "drawai_tool_agent",
                "llm_api_preset_id": "openrouter",
                "llm_model": "qwen3.7-plus",
                "llm_base_url": "https://openrouter.ai/api/v1",
            }
        ),
        encoding="utf-8",
    )
    client = _client(tmp_path)

    response = client.get("/api/workbench/agent-settings")

    assert response.status_code == 200
    settings = response.json()["settings"]
    assert settings["selected_provider_id"] == "drawai_tool_agent"
    assert settings["llm_api_preset_id"] == "openrouter"


def test_workbench_api_presets_api_saves_and_validates_presets(tmp_path: Path) -> None:
    client = _client(tmp_path)

    response = client.get("/api/workbench/api-presets")

    assert response.status_code == 200
    assert response.json()["schema"] == "drawai.workbench.api_presets.v1"
    assert response.json()["presets"] == []
    assert "images_api" in response.json()["preset_types"]

    save_response = client.put(
        "/api/workbench/api-presets",
        json={
            "presets": [
                {
                    "id": "openai_images",
                    "label": "OpenAI Images",
                    "type": "images_api",
                    "base_url": "https://api.openai.com",
                    "model": "gpt-image-2",
                    "api_key_env": "OPENAI_API_KEY",
                    "api_key": "sk-local",
                    "logo_url": "https://example.invalid/icon.svg",
                }
            ]
        },
    )

    assert save_response.status_code == 200
    saved = save_response.json()["presets"][0]
    assert saved["id"] == "openai_images"
    assert saved["type"] == "images_api"
    assert saved["api_key"] == "sk-local"
    assert "logo_url" not in saved
    saved_document = json.loads((tmp_path / "workspace" / "settings" / "api_presets.json").read_text(encoding="utf-8"))
    assert "logo_url" not in saved_document["presets"][0]
    assert (tmp_path / "workspace" / "settings" / "api_presets.json").is_file()


def test_workbench_api_presets_api_saves_keyless_local_presets(tmp_path: Path) -> None:
    client = _client(tmp_path)

    save_response = client.put(
        "/api/workbench/api-presets",
        json={
            "presets": [
                {
                    "id": "ollama",
                    "label": "Ollama",
                    "type": "llm_chat_completions",
                    "base_url": "http://localhost:11434/v1",
                    "model": "llama3.1",
                    "api_key_env": "",
                    "api_key": "",
                }
            ]
        },
    )

    assert save_response.status_code == 200
    saved = save_response.json()["presets"][0]
    assert saved["id"] == "ollama"
    assert saved["api_key_env"] == ""
    assert saved["api_key"] == ""
    assert "logo_url" not in saved


def test_workbench_api_preset_logo_parser_uses_site_logo_for_api_subdomains() -> None:
    page_urls = api_preset_logo_page_urls("https://api.apimart.ai/v1/images/generations")

    assert page_urls[:3] == (
        "https://api.apimart.ai/",
        "https://apimart.ai/",
        "https://www.apimart.ai/",
    )

    html = """
    <!doctype html>
    <html>
      <head>
        <script type="application/ld+json">
          {"@context":"https://schema.org","@type":"Organization","logo":{"@type":"ImageObject","url":"https://apimart.ai/supplier/apimart.svg"}}
        </script>
      </head>
    </html>
    """

    assert api_preset_logo_url_from_html("https://www.apimart.ai/", html) == "https://apimart.ai/supplier/apimart.svg"


def test_workbench_api_presets_api_rejects_invalid_payloads(tmp_path: Path) -> None:
    client = _client(tmp_path)

    duplicate_response = client.put(
        "/api/workbench/api-presets",
        json={
            "presets": [
                {
                    "id": "openai",
                    "label": "OpenAI",
                    "type": "images_api",
                    "base_url": "https://api.openai.com",
                    "model": "gpt-image-2",
                    "api_key_env": "OPENAI_API_KEY",
                },
                {
                    "id": "openai",
                    "label": "OpenAI Again",
                    "type": "images_api",
                    "base_url": "https://api.openai.com",
                    "model": "gpt-image-2",
                    "api_key_env": "OPENAI_API_KEY",
                },
            ]
        },
    )
    assert duplicate_response.status_code == 400
    assert "duplicate API preset id" in duplicate_response.json()["detail"]

    unknown_type_response = client.put(
        "/api/workbench/api-presets",
        json={
            "presets": [
                {
                    "id": "bad",
                    "label": "Bad",
                    "type": "not_real",
                    "base_url": "https://api.example.com",
                    "model": "model",
                    "api_key_env": "OPENAI_API_KEY",
                }
            ]
        },
    )
    assert unknown_type_response.status_code == 400
    assert "unsupported API preset type" in unknown_type_response.json()["detail"]


def test_workbench_processor_settings_api_lists_registered_processors(tmp_path: Path) -> None:
    client = _client(tmp_path)

    response = client.get("/api/workbench/processor-settings")

    assert response.status_code == 200
    payload = response.json()
    assert payload["schema"] == "drawai.workbench.processor_settings.v1"
    assert "crop" in payload["definitions"]["processors"]
    assert "image_generate" in payload["definitions"]["processors"]
    assert "openai_images_api" in payload["definitions"]["drivers"]
    assert "openai_images_api" in payload["definitions"]["processors"]["image_edit"]["supported_driver_ids"]
    assert payload["settings"]["processors"]["crop"]["enabled"] is True
    assert payload["validation"]["processors"]["crop"]["configured"] is True
    assert payload["settings"]["processors"]["image_generate"]["enabled"] is False


def test_workbench_processor_settings_api_saves_driver_and_operation_overrides(tmp_path: Path) -> None:
    client = _client(tmp_path)
    preset_response = client.put(
        "/api/workbench/api-presets",
        json={
            "presets": [
                {
                    "id": "openai_images",
                    "label": "OpenAI Images",
                    "type": "images_api",
                    "base_url": "https://api.openai.com",
                    "model": "gpt-image-2",
                    "api_key_env": "OPENAI_API_KEY",
                }
            ]
        },
    )
    assert preset_response.status_code == 200

    save_response = client.put(
        "/api/workbench/processor-settings",
        json={
            "processors": {
                "image_generate": {
                    "enabled": True,
                    "driver_id": "openai_images_api",
                    "api_preset_id": "openai_images",
                    "operation": {
                        "meaning": "Workspace image generation meaning.",
                        "choose_when": "Workspace choose image generation.",
                        "avoid_when": "Workspace avoid image generation.",
                    },
                }
            }
        },
    )

    assert save_response.status_code == 200
    image_generate = save_response.json()["settings"]["processors"]["image_generate"]
    assert image_generate["enabled"] is True
    assert image_generate["driver_id"] == "openai_images_api"
    assert image_generate["api_preset_id"] == "openai_images"
    assert image_generate["operation"]["meaning"] == "Workspace image generation meaning."


def test_asset_processor_providers_routes_images_api_generation_driver(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _client(tmp_path)
    preset_response = client.put(
        "/api/workbench/api-presets",
        json={
            "presets": [
                {
                    "id": "openai_images",
                    "label": "OpenAI Images",
                    "type": "images_api",
                    "base_url": "https://api.openai.com",
                    "model": "gpt-image-2",
                    "api_key": "plain-test-key",
                }
            ]
        },
    )
    assert preset_response.status_code == 200
    settings_response = client.put(
        "/api/workbench/processor-settings",
        json={
            "processors": {
                "image_generate": {
                    "enabled": True,
                    "driver_id": "openai_images_api",
                    "api_preset_id": "openai_images",
                }
            }
        },
    )
    assert settings_response.status_code == 200

    captured: dict[str, object] = {}

    def fake_generation_upstream(
        payload: Mapping[str, object],
        *,
        api_url: str,
        api_key: str | None = None,
    ) -> dict[str, object]:
        captured["payload"] = dict(payload)
        captured["api_url"] = api_url
        captured["api_key"] = api_key
        buffer = io.BytesIO()
        Image.new("RGB", (3, 2), "#1f77b4").save(buffer, format="PNG")
        encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
        return {"data": [{"id": "img_1", "b64_json": encoded, "revised_prompt": "Draw it clearly."}]}

    monkeypatch.setattr(api_module, "_call_image_generation_upstream", fake_generation_upstream)
    processor_setting = require_processor_configured(tmp_path / "workspace", "image_generate")

    providers = api_module._asset_processor_providers(
        None,  # type: ignore[arg-type]
        "image_generate",
        _settings(tmp_path, tmp_path / "base.yaml"),
        None,
        processor_setting=processor_setting,
    )
    provider_result = providers["image_generate"](
        prompt="Draw it",
        output_dir=tmp_path / "provider-output",
        task_name="drawai.test.image_generate",
        output_stem="image_generate",
        runtime_config={"size": "1024x1024"},
    )

    assert captured["api_url"] == "https://api.openai.com/v1/images/generations"
    assert captured["api_key"] == "plain-test-key"
    assert captured["payload"] == {
        "model": "gpt-image-2",
        "prompt": "Draw it",
        "n": 1,
        "size": "1024x1024",
    }
    image_payload = provider_result["images"][0]
    assert Path(image_payload["path"]).is_file()
    assert image_payload["width"] == 3
    assert image_payload["height"] == 2
    assert provider_result["provider"] == "openai_images"


def test_asset_prepare_receives_images_api_generate_and_edit_providers(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _client(tmp_path)
    preset_response = client.put(
        "/api/workbench/api-presets",
        json={
            "presets": [
                {
                    "id": "apimart_images",
                    "label": "Apimart Images",
                    "type": "images_api",
                    "base_url": "https://api.apimart.ai/v1/images/generations",
                    "model": "gpt-image-2",
                    "api_key": "plain-test-key",
                }
            ]
        },
    )
    assert preset_response.status_code == 200
    settings_response = client.put(
        "/api/workbench/processor-settings",
        json={
            "processors": {
                "image_generate": {
                    "enabled": True,
                    "driver_id": "openai_images_api",
                    "api_preset_id": "apimart_images",
                },
                "image_edit": {
                    "enabled": True,
                    "driver_id": "openai_images_api",
                    "api_preset_id": "apimart_images",
                },
            }
        },
    )
    assert settings_response.status_code == 200

    source = tmp_path / "source.png"
    Image.new("RGBA", (64, 48), (255, 255, 255, 255)).save(source)
    page_spec = {
        "schema": "drawai.page_spec.v1",
        "page_id": "provider-routing",
        "source": {"image": str(source), "width_px": 64, "height_px": 48},
        "canvas": {"width_px": 64, "height_px": 48},
        "background": {},
        "elements": [
            {
                "id": "E001",
                "kind": "image",
                "role": "representation",
                "box_px": [2, 2, 18, 12],
                "z_index": 1,
                "build": {"mode": "asset_ref", "processing_type": "image_generate"},
            },
            {
                "id": "E002",
                "kind": "image",
                "role": "representation",
                "box_px": [24, 2, 18, 12],
                "z_index": 2,
                "build": {"mode": "asset_ref", "processing_type": "image_edit"},
            },
        ],
        "metadata": {},
    }
    upstream_calls: list[tuple[str, str]] = []
    upstream_lock = threading.Lock()

    def image_response(image_id: str) -> dict[str, object]:
        buffer = io.BytesIO()
        Image.new("RGB", (4, 3), "#1f77b4").save(buffer, format="PNG")
        encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
        return {"data": [{"id": image_id, "b64_json": encoded}]}

    def fake_upstream(
        payload: Mapping[str, object],
        *,
        api_url: str,
        api_key: str | None = None,
    ) -> dict[str, object]:
        with upstream_lock:
            operation = "edit_reference" if "image_urls" in payload else "generate"
            upstream_calls.append((operation, api_url))
        assert api_key == "plain-test-key"
        assert payload["model"] == "gpt-image-2"
        if "image_urls" in payload:
            image_urls = payload["image_urls"]
            assert isinstance(image_urls, list)
            assert str(image_urls[0]).startswith("data:image/png;base64,")
        return image_response("img_generate")

    def fake_edit_upstream(
        payload: Mapping[str, object],
        *,
        source_image_path: str | Path,
        api_url: str,
        api_key: str | None = None,
    ) -> dict[str, object]:
        with upstream_lock:
            upstream_calls.append(("edit", api_url))
        assert api_key == "plain-test-key"
        assert payload["model"] == "gpt-image-2"
        assert Path(source_image_path).is_file()
        return image_response("img_edit")

    from drawai.page_spec_assets import materialize_page_spec_assets
    from drawai.workbench import image_processor_providers as provider_module

    monkeypatch.setattr(provider_module, "call_image_generation_upstream", fake_upstream)
    monkeypatch.setattr(provider_module, "call_image_edit_upstream", fake_edit_upstream)
    materialized = materialize_page_spec_assets(
        page_spec,
        source_image_path=source,
        output_dir=tmp_path / "bundle",
        **provider_module.asset_prepare_image_providers(tmp_path / "workspace"),
    )

    assert sorted(upstream_calls) == [
        ("edit_reference", "https://api.apimart.ai/v1/images/generations"),
        ("generate", "https://api.apimart.ai/v1/images/generations"),
    ]
    assert materialized["elements"][0]["materialization"]["processing_type"] == "image_generate"
    assert materialized["elements"][1]["materialization"]["processing_type"] == "image_edit"


def test_images_api_urls_replace_specific_endpoint_base_urls() -> None:
    from drawai.workbench.image_processor_providers import image_edit_api_url, image_generation_api_url

    assert image_generation_api_url("https://api.apimart.ai/v1/images/generations") == (
        "https://api.apimart.ai/v1/images/generations"
    )
    assert image_edit_api_url("https://api.apimart.ai/v1/images/generations") == (
        "https://api.apimart.ai/v1/images/edits"
    )
    assert image_generation_api_url("https://api.apimart.ai/v1/images/edits") == (
        "https://api.apimart.ai/v1/images/generations"
    )


def test_images_api_generation_retries_transient_http_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from drawai.workbench import image_processor_providers as provider_module

    calls = 0
    buffer = io.BytesIO()
    Image.new("RGB", (3, 2), "#1f77b4").save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    payload = json.dumps({"data": [{"id": "img_1", "b64_json": encoded}]}).encode("utf-8")

    class Response:
        def __enter__(self) -> "Response":
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def read(self) -> bytes:
            return payload

    def fake_urlopen(request: object, timeout: float) -> Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise urllib.error.HTTPError(
                "https://api.example/v1/images/generations",
                504,
                "Gateway Timeout",
                {},
                io.BytesIO(b'{"detail":"origin timeout"}'),
            )
        return Response()

    monkeypatch.setattr(provider_module, "urlopen_external", fake_urlopen)
    monkeypatch.setenv("DRAWAI_IMAGEGEN_RETRY_DELAY_SECONDS", "0.001")
    response = provider_module.call_image_generation_upstream(
        {"model": "gpt-image-2", "prompt": "Draw it", "n": 1},
        api_url="https://api.example/v1/images/generations",
        api_key="plain-test-key",
    )

    assert calls == 2
    assert response["data"][0]["id"] == "img_1"


def test_images_api_provider_materializes_apimart_task_result_urls(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from drawai.workbench.api_presets import ApiPreset
    from drawai.workbench import image_processor_providers as provider_module

    buffer = io.BytesIO()
    Image.new("RGB", (3, 2), "#1f77b4").save(buffer, format="PNG")
    data_url = "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")

    def fake_upstream(
        payload: Mapping[str, object],
        *,
        api_url: str,
        api_key: str | None = None,
    ) -> dict[str, object]:
        assert api_url == "https://api.apimart.ai/v1/images/generations"
        assert api_key == "plain-test-key"
        return {
            "data": {
                "id": "task_1",
                "status": "completed",
                "result": {"images": [{"url": [data_url]}]},
            }
        }

    monkeypatch.setattr(provider_module, "call_image_generation_upstream", fake_upstream)
    provider = provider_module.images_api_generate_provider(
        ApiPreset(
            id="apimart_images",
            label="Apimart Images",
            type="images_api",
            base_url="https://api.apimart.ai/v1/images/generations",
            model="gpt-image-2",
            api_key="plain-test-key",
        )
    )

    result = provider(
        prompt="Draw it",
        output_dir=tmp_path / "images",
        task_name="drawai.test.image_generate",
        output_stem="image_generate",
    )

    image_payload = result["images"][0]
    assert Path(image_payload["path"]).is_file()
    assert image_payload["width"] == 3
    assert image_payload["height"] == 2


def test_images_api_provider_retries_protected_result_url_with_api_key(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from drawai.workbench.api_presets import ApiPreset
    from drawai.workbench import image_processor_providers as provider_module

    buffer = io.BytesIO()
    Image.new("RGB", (3, 2), "#1f77b4").save(buffer, format="PNG")
    image_bytes = buffer.getvalue()
    requested_authorization: list[str | None] = []

    class Response:
        headers = {"content-type": "image/png"}

        def __enter__(self) -> "Response":
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def read(self, *_args: object) -> bytes:
            return image_bytes

    def fake_upstream(
        payload: Mapping[str, object],
        *,
        api_url: str,
        api_key: str | None = None,
    ) -> dict[str, object]:
        return {"data": {"result": {"images": [{"url": "https://api.apimart.ai/v1/files/generated.png"}]}}}

    def fake_urlopen(request: object, timeout: float) -> Response:
        assert isinstance(request, urllib.request.Request)
        authorization = request.headers.get("Authorization")
        requested_authorization.append(authorization)
        if authorization is None:
            raise urllib.error.HTTPError(
                request.full_url,
                403,
                "Forbidden",
                {},
                io.BytesIO(b"forbidden"),
            )
        assert authorization == "Bearer plain-test-key"
        return Response()

    monkeypatch.setattr(provider_module, "call_image_generation_upstream", fake_upstream)
    monkeypatch.setattr(provider_module, "urlopen_external", fake_urlopen)
    provider = provider_module.images_api_generate_provider(
        ApiPreset(
            id="apimart_images",
            label="Apimart Images",
            type="images_api",
            base_url="https://api.apimart.ai/v1/images/generations",
            model="gpt-image-2",
            api_key="plain-test-key",
        )
    )

    result = provider(
        prompt="Draw it",
        output_dir=tmp_path / "images",
        task_name="drawai.test.image_generate",
        output_stem="image_generate",
    )

    assert requested_authorization == [None, "Bearer plain-test-key"]
    assert Path(result["images"][0]["path"]).is_file()


def test_workbench_processor_settings_api_rejects_invalid_processor_settings(tmp_path: Path) -> None:
    client = _client(tmp_path)

    unknown_processor = client.put(
        "/api/workbench/processor-settings",
        json={"processors": {"not_real": {"enabled": True}}},
    )
    assert unknown_processor.status_code == 400
    assert "unsupported processor" in unknown_processor.json()["detail"]

    bad_driver = client.put(
        "/api/workbench/processor-settings",
        json={"processors": {"crop": {"enabled": True, "driver_id": "openai_images_api"}}},
    )
    assert bad_driver.status_code == 400
    assert "unsupported driver" in bad_driver.json()["detail"]

    missing_preset = client.put(
        "/api/workbench/processor-settings",
        json={
            "processors": {
                "image_generate": {
                    "enabled": True,
                    "driver_id": "openai_images_api",
                    "api_preset_id": "missing",
                }
            }
        },
    )
    assert missing_preset.status_code == 400
    assert "API preset not found" in missing_preset.json()["detail"]


def test_workbench_processor_settings_allows_disabled_incomplete_api_driver(tmp_path: Path) -> None:
    client = _client(tmp_path)

    save_response = client.put(
        "/api/workbench/processor-settings",
        json={
            "processors": {
                "image_generate": {
                    "enabled": False,
                    "driver_id": "openai_images_api",
                    "api_preset_id": "",
                }
            }
        },
    )

    assert save_response.status_code == 200
    image_generate = save_response.json()["settings"]["processors"]["image_generate"]
    assert image_generate["enabled"] is False
    assert image_generate["driver_id"] == "openai_images_api"
    assert save_response.json()["validation"]["processors"]["image_generate"]["configured"] is False


def test_workbench_processor_settings_guard_rejects_disabled_processor(tmp_path: Path) -> None:
    client = _client(tmp_path)

    with pytest.raises(ValueError, match="processor is disabled: image_generate"):
        require_processor_configured(tmp_path / "workspace", "image_generate")

    save_response = client.put(
        "/api/workbench/processor-settings",
        json={"processors": {"image_generate": {"enabled": True, "driver_id": "codex_imagegen_builtin"}}},
    )
    assert save_response.status_code == 200
    setting = require_processor_configured(tmp_path / "workspace", "image_generate")
    assert setting.driver_id == "codex_imagegen_builtin"


def test_create_batch_applies_saved_workbench_agent_to_case_config(
    tmp_path: Path,
    monkeypatch,
) -> None:
    bin_dir = tmp_path / "bin"
    _write_executable(bin_dir / "kimi", "echo 'kimi 1.2.3'\n")
    monkeypatch.setenv("PATH", str(bin_dir))
    client = _client(tmp_path)
    source = tmp_path / "single.png"
    Image.new("RGB", (24, 24), "white").save(source)
    save_response = client.put(
        "/api/workbench/agent-settings",
        json={
            "selected_provider_id": "kimi_cli",
            "model": "kimi-code/kimi-for-coding",
            "reasoning_effort": "medium",
            "fast": True,
            "timeout_seconds": 240,
        },
    )
    assert save_response.status_code == 200

    response = client.post(
        "/api/batches",
        json={
            "name": "agent config batch",
            "input_mode": "local_dir",
            "local_dir": str(source),
            "auto_run_svg_after_analysis": False,
            "max_concurrent_cases": 1,
            "base_config_path": str(_base_config(tmp_path)),
            "execution_mode": "agent",
        },
    )

    assert response.status_code == 200
    assert response.json()["batch"]["execution_mode"] == "agent"
    config_path = Path(response.json()["cases"][0]["config_path"])
    payload = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert payload["svg"]["generation_backend"] == "agent_cli"
    assert payload["model_runtime"]["provider"] == "agent-cli"
    assert payload["model_runtime"]["connection_id"] == "kimi"
    assert payload["model_runtime"]["model_name"] == "kimi-code/kimi-for-coding"
    assert payload["model_runtime"]["reasoning_effort"] == "medium"
    assert payload["model_runtime"]["fast"] is True
    assert payload["model_runtime"]["timeout_seconds"] == 240
    assert payload["model_runtime"]["cli"]["agent"] == "kimi"
    assert payload["model_runtime"]["cli"]["command"][0] == str(bin_dir / "kimi")


def test_create_batch_can_use_task_scoped_agent_settings(
    tmp_path: Path,
    monkeypatch,
) -> None:
    bin_dir = tmp_path / "bin"
    _write_executable(bin_dir / "kimi", "echo 'kimi 1.2.3'\n")
    monkeypatch.setenv("PATH", str(bin_dir))
    client = _client(tmp_path)
    source = tmp_path / "single.png"
    Image.new("RGB", (24, 24), "white").save(source)

    response = client.post(
        "/api/batches",
        json={
            "name": "task scoped settings",
            "input_mode": "local_dir",
            "local_dir": str(source),
            "auto_run_svg_after_analysis": True,
            "max_concurrent_cases": 1,
            "base_config_path": str(_base_config(tmp_path)),
            "execution_mode": "agent",
            "agent_settings": {
                "selected_provider_id": "kimi_cli",
                "model": "kimi-code/kimi-for-coding",
                "reasoning_effort": "high",
                "fast": True,
                "timeout_seconds": 300,
            },
        },
    )

    assert response.status_code == 200
    config_path = Path(response.json()["cases"][0]["config_path"])
    payload = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert payload["model_runtime"]["connection_id"] == "kimi"
    assert payload["model_runtime"]["model_name"] == "kimi-code/kimi-for-coding"
    assert payload["model_runtime"]["reasoning_effort"] == "high"
    assert payload["model_runtime"]["fast"] is True
    snapshot_path = Path(response.json()["cases"][0]["run_root"]) / "reports" / "workbench" / "settings_snapshot.json"
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    assert snapshot["agent_settings"]["selected_provider_id"] == "kimi_cli"
    assert snapshot["agent_settings"]["model"] == "kimi-code/kimi-for-coding"


def test_submitted_case_keeps_agent_and_processor_settings_snapshot(
    tmp_path: Path,
    monkeypatch,
) -> None:
    bin_dir = tmp_path / "bin"
    _write_executable(bin_dir / "kimi", "echo 'kimi 1.2.3'\n")
    monkeypatch.setenv("PATH", str(bin_dir))
    store = WorkbenchStore(tmp_path / "workspace")
    base_config = _base_config(tmp_path)
    settings = _settings(tmp_path, base_config)
    runner = WorkbenchRunner(store, settings, stage_executor=lambda _case, _stage: None)
    app = create_app(settings, store=store, runner=runner)
    client = TestClient(app)
    source = tmp_path / "single.png"
    Image.new("RGB", (24, 24), "white").save(source)
    preset_response = client.put(
        "/api/workbench/api-presets",
        json={
            "presets": [
                {
                    "id": "apimart_images",
                    "label": "Apimart Images",
                    "type": "images_api",
                    "base_url": "https://api.apimart.ai/v1/images/generations",
                    "model": "gpt-image-2",
                    "api_key_env": "APIMART_API_KEY",
                }
            ]
        },
    )
    assert preset_response.status_code == 200
    processor_response = client.put(
        "/api/workbench/processor-settings",
        json={
            "processors": {
                "image_generate": {
                    "enabled": True,
                    "driver_id": "openai_images_api",
                    "api_preset_id": "apimart_images",
                }
            }
        },
    )
    assert processor_response.status_code == 200
    agent_response = client.put(
        "/api/workbench/agent-settings",
        json={
            "selected_provider_id": "kimi_cli",
            "model": "kimi-code/kimi-for-coding",
            "reasoning_effort": "medium",
            "fast": True,
            "timeout_seconds": 240,
        },
    )
    assert agent_response.status_code == 200
    batch_response = client.post(
        "/api/batches",
        json={
            "name": "settings snapshot batch",
            "input_mode": "local_dir",
            "local_dir": str(source),
            "auto_run_svg_after_analysis": False,
            "max_concurrent_cases": 1,
            "base_config_path": str(base_config),
            "execution_mode": "agent",
        },
    )
    assert batch_response.status_code == 200
    case = store.get_case(batch_response.json()["cases"][0]["case_id"])
    snapshot_path = Path(case.run_root) / "reports" / "workbench" / "settings_snapshot.json"
    assert snapshot_path.is_file()
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    assert snapshot["agent_settings"]["selected_provider_id"] == "kimi_cli"
    assert snapshot["api_presets"]["presets"][0]["id"] == "apimart_images"
    assert snapshot["processor_settings"]["processors"]["image_generate"]["api_preset_id"] == "apimart_images"

    changed_presets = client.put(
        "/api/workbench/api-presets",
        json={
            "presets": [
                {
                    "id": "other_images",
                    "label": "Other Images",
                    "type": "images_api",
                    "base_url": "https://api.example.test/v1/images/generations",
                    "model": "other-image-model",
                    "api_key_env": "OTHER_IMAGE_KEY",
                }
            ]
        },
    )
    assert changed_presets.status_code == 200
    changed_processor = client.put(
        "/api/workbench/processor-settings",
        json={
            "processors": {
                "image_generate": {
                    "enabled": True,
                    "driver_id": "openai_images_api",
                    "api_preset_id": "other_images",
                }
            }
        },
    )
    assert changed_processor.status_code == 200
    changed_agent = client.put(
        "/api/workbench/agent-settings",
        json={
            "selected_provider_id": "codex_sdk",
            "model": "codex-after-submit",
            "reasoning_effort": "low",
        },
    )
    assert changed_agent.status_code == 200

    refreshed = runner._refresh_case_runtime_config(store.get_case(case.case_id))
    config_payload = yaml.safe_load(Path(refreshed.config_path).read_text(encoding="utf-8"))
    assert config_payload["model_runtime"]["connection_id"] == "kimi"
    assert config_payload["model_runtime"]["model_name"] == "kimi-code/kimi-for-coding"
    assert config_payload["model_runtime"]["fast"] is True

    progress_response = client.get(f"/api/cases/{case.case_id}/progress")
    assert progress_response.status_code == 200
    nodes = {item["node_id"]: item for item in progress_response.json()["workflow_nodes"]}
    assert nodes["page_spec_refine"]["provider_id"] == "kimi_cli"
    assert nodes["page_spec_refine"]["provider_label"] == "Kimi CLI"
    assert nodes["page_spec_refine"]["model"] == "kimi-code/kimi-for-coding"
    assert nodes["page_spec_refine"]["processor_types"] == [
        "no_process",
        "crop",
        "crop_nobg",
        "image_generate",
    ]
    assert nodes["asset_prepare"]["api_presets"] == [
        {
            "processing_type": "image_generate",
            "api_preset_id": "apimart_images",
            "api_preset_label": "Apimart Images",
        }
    ]


@pytest.mark.parametrize(
    ("provider_id", "agent", "command"),
    [
        ("kimi_acp", "kimi", ("kimi", "acp")),
        ("gemini_acp", "gemini", ("gemini", "--experimental-acp")),
        ("qwen_acp", "qwen", ("qwen", "--acp")),
        ("opencode_acp", "opencode", ("opencode", "acp")),
        ("goose_acp", "goose", ("goose", "acp")),
        ("kiro_acp", "kiro", ("kiro-cli", "acp")),
        ("qoder_acp", "qoder", ("qodercli", "--acp")),
        ("cursor_acp", "cursor", ("agent", "acp")),
        ("cline_acp", "cline", ("cline", "--acp")),
        ("copilot_acp", "copilot", ("copilot", "--acp", "--stdio")),
        ("hermes_acp", "hermes", ("hermes", "acp")),
    ],
)
def test_create_batch_applies_saved_workbench_acp_agent_to_case_config(
    tmp_path: Path,
    monkeypatch,
    provider_id: str,
    agent: str,
    command: tuple[str, ...],
) -> None:
    bin_dir = tmp_path / "bin"
    executable = _write_executable(bin_dir / command[0], f"echo '{agent} 1.2.3'\n")
    monkeypatch.setenv("PATH", str(bin_dir))
    client = _client(tmp_path)
    source = tmp_path / "single.png"
    Image.new("RGB", (24, 24), "white").save(source)
    save_response = client.put(
        "/api/workbench/agent-settings",
        json={
            "selected_provider_id": provider_id,
            "model": "kimi-code/kimi-for-coding",
            "reasoning_effort": "medium",
            "timeout_seconds": 240,
        },
    )
    assert save_response.status_code == 200

    response = client.post(
        "/api/batches",
        json={
            "name": "acp agent config batch",
            "input_mode": "local_dir",
            "local_dir": str(source),
            "auto_run_svg_after_analysis": False,
            "max_concurrent_cases": 1,
            "base_config_path": str(_base_config(tmp_path)),
            "execution_mode": "agent",
        },
    )

    assert response.status_code == 200
    assert response.json()["batch"]["execution_mode"] == "agent"
    config_path = Path(response.json()["cases"][0]["config_path"])
    payload = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert payload["svg"]["generation_backend"] == "acp_agent"
    assert payload["model_runtime"]["provider"] == "acp-agent"
    assert payload["model_runtime"]["connection_id"] == agent
    assert payload["model_runtime"]["model_name"] == "kimi-code/kimi-for-coding"
    assert payload["model_runtime"]["reasoning_effort"] == "medium"
    assert payload["model_runtime"]["timeout_seconds"] == 240
    assert payload["model_runtime"]["acp"]["agent"] == agent
    assert payload["model_runtime"]["acp"]["command"] == [str(executable), *command[1:]]


def test_create_batch_applies_saved_workbench_llm_runtime_to_case_config(tmp_path: Path) -> None:
    client = _client(tmp_path)
    source = tmp_path / "single.png"
    Image.new("RGB", (24, 24), "white").save(source)
    save_response = client.put(
        "/api/workbench/agent-settings",
        json={
            "llm_model": "minimax/minimax-m3",
            "llm_base_url": "https://openrouter.ai/api/v1",
            "llm_api_key_env": "OPENROUTER_API_KEY",
            "llm_wire_api": "chat_completions",
            "reasoning_effort": "xhigh",
            "timeout_seconds": 900,
        },
    )
    assert save_response.status_code == 200

    response = client.post(
        "/api/batches",
        json={
            "name": "llm config batch",
            "input_mode": "local_dir",
            "local_dir": str(source),
            "auto_run_svg_after_analysis": False,
            "max_concurrent_cases": 1,
            "base_config_path": str(_base_config(tmp_path)),
            "execution_mode": "llm",
        },
    )

    assert response.status_code == 200
    assert response.json()["batch"]["execution_mode"] == "llm"
    config_path = Path(response.json()["cases"][0]["config_path"])
    payload = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert payload["svg"]["generation_backend"] == "responses"
    assert payload["model_runtime"]["provider"] == "openai_compatible"
    assert payload["model_runtime"]["connection_id"] == "openai_compatible"
    assert payload["model_runtime"]["model_name"] == "minimax/minimax-m3"
    assert payload["model_runtime"]["reasoning_effort"] == "xhigh"
    assert payload["model_runtime"]["timeout_seconds"] == 900
    assert payload["model_runtime"]["base_url"] == "https://openrouter.ai/api/v1"
    assert payload["model_runtime"]["api_provider"]["mode"] == "thirdparty"
    thirdparty = payload["model_runtime"]["api_provider"]["thirdparty"]
    assert thirdparty["base_url"] == "https://openrouter.ai/api/v1"
    assert thirdparty["api_key_env"] == "OPENROUTER_API_KEY"
    assert thirdparty["wire_api"] == "chat_completions"


def test_create_batch_applies_saved_builtin_agent_api_preset_to_case_config(tmp_path: Path) -> None:
    client = _client(tmp_path)
    source = tmp_path / "single.png"
    Image.new("RGB", (24, 24), "white").save(source)
    save_response = client.put(
        "/api/workbench/agent-settings",
        json={
            "selected_provider_id": "drawai_tool_agent",
            "llm_api_preset_id": "openrouter",
            "llm_model": "minimax/minimax-m3",
            "llm_base_url": "https://openrouter.ai/api/v1",
            "llm_api_key_env": "OPENROUTER_API_KEY",
            "llm_wire_api": "chat_completions",
            "llm_extra_body": {"reasoning": {"enabled": True}},
            "timeout_seconds": 900,
        },
    )
    assert save_response.status_code == 200
    settings = save_response.json()["settings"]
    assert settings["selected_provider_id"] == "drawai_tool_agent"
    assert settings["llm_api_preset_id"] == "openrouter"

    response = client.post(
        "/api/batches",
        json={
            "name": "builtin agent config batch",
            "input_mode": "local_dir",
            "local_dir": str(source),
            "auto_run_svg_after_analysis": False,
            "max_concurrent_cases": 1,
            "base_config_path": str(_base_config(tmp_path)),
            "execution_mode": "agent",
        },
    )

    assert response.status_code == 200
    assert response.json()["batch"]["execution_mode"] == "agent"
    config_path = Path(response.json()["cases"][0]["config_path"])
    payload = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert payload["svg"]["generation_backend"] == "tool_agent"
    assert payload["model_runtime"]["provider"] == "drawai_tool_agent"
    assert payload["model_runtime"]["connection_id"] == "drawai_tool_agent"
    assert payload["model_runtime"]["api_preset_id"] == "openrouter"
    assert payload["model_runtime"]["model_name"] == "minimax/minimax-m3"
    assert payload["model_runtime"]["base_url"] == "https://openrouter.ai/api/v1"
    assert payload["model_runtime"]["api_key_env"] == "OPENROUTER_API_KEY"
    assert payload["model_runtime"]["wire_api"] == "chat_completions"
    assert payload["model_runtime"]["timeout_seconds"] == 900


def test_workbench_agent_mode_keeps_default_agent_nodes(tmp_path: Path) -> None:
    template = load_workflow_template_by_id(tmp_path / "workspace", "default_drawai_dag")

    effective = _workflow_template_with_agent_settings(
        template,
        WorkbenchAgentSettings(
            selected_provider_id="kimi_cli",
            reasoning_effort="medium",
            timeout_seconds=900,
        ),
        execution_mode="agent",
    )

    original_nodes = {node.node_id: node for node in template.nodes}
    effective_nodes = {node.node_id: node for node in effective.nodes}
    assert original_nodes["page_spec_refine"].node_type == "agent"
    assert original_nodes["svg_compose"].node_type == "agent"
    assert effective_nodes["page_spec_refine"].node_type == "agent"
    assert effective_nodes["svg_compose"].node_type == "agent"
    assert effective_nodes["page_spec_refine"].config["provider_id"] == "kimi_cli"
    assert effective_nodes["svg_compose"].config["provider_id"] == "kimi_cli"
    assert effective_nodes["page_spec_refine"].config["reasoning_effort"] == "medium"
    assert effective_nodes["svg_compose"].config["timeout_seconds"] == 900


def test_workbench_llm_mode_projects_default_agent_nodes_to_llm(tmp_path: Path) -> None:
    template = load_workflow_template_by_id(tmp_path / "workspace", "default_drawai_dag")

    effective = _workflow_template_with_agent_settings(
        template,
        WorkbenchAgentSettings(
            llm_model="minimax/minimax-m3",
            llm_base_url="https://openrouter.ai/api/v1",
            llm_api_key_env="OPENROUTER_API_KEY",
            llm_wire_api="chat_completions",
            llm_extra_body={"reasoning": {"enabled": True}},
            reasoning_effort="high",
            timeout_seconds=900,
        ),
        execution_mode="llm",
    )

    original_nodes = {node.node_id: node for node in template.nodes}
    effective_nodes = {node.node_id: node for node in effective.nodes}
    assert original_nodes["page_spec_refine"].node_type == "agent"
    assert original_nodes["svg_compose"].node_type == "agent"
    assert effective_nodes["page_spec_refine"].node_type == "llm"
    assert effective_nodes["svg_compose"].node_type == "llm"
    assert effective_nodes["page_spec_refine"].inputs == original_nodes["page_spec_refine"].inputs
    assert effective_nodes["svg_compose"].outputs == original_nodes["svg_compose"].outputs
    assert effective_nodes["page_spec_refine"].config["provider_id"] == "openai_compatible"
    assert effective_nodes["svg_compose"].config["provider_id"] == "openai_compatible"
    assert effective_nodes["page_spec_refine"].config["model"] == "minimax/minimax-m3"
    assert effective_nodes["svg_compose"].config["model"] == "minimax/minimax-m3"
    assert effective_nodes["page_spec_refine"].config["base_url"] == "https://openrouter.ai/api/v1"
    assert effective_nodes["page_spec_refine"].config["api_key_env"] == "OPENROUTER_API_KEY"
    assert effective_nodes["page_spec_refine"].config["wire_api"] == "chat_completions"
    assert effective_nodes["page_spec_refine"].config["extra_body"] == {"reasoning": {"enabled": True}}
    assert effective_nodes["page_spec_refine"].config["reasoning_effort"] == "high"
    assert effective_nodes["svg_compose"].config["timeout_seconds"] == 900


def test_workbench_default_mode_preserves_dag_prompt_node_types(tmp_path: Path) -> None:
    template = load_workflow_template_by_id(tmp_path / "workspace", "default_drawai_dag")

    effective = _workflow_template_with_agent_settings(
        template,
        WorkbenchAgentSettings(
            selected_provider_id="kimi_cli",
            llm_model="minimax/minimax-m3",
            llm_base_url="https://openrouter.ai/api/v1",
        ),
        execution_mode="default",
    )

    effective_nodes = {node.node_id: node for node in effective.nodes}
    assert effective_nodes["page_spec_refine"].node_type == "agent"
    assert effective_nodes["svg_compose"].node_type == "agent"
    assert effective_nodes["page_spec_refine"].config["provider_id"] == "kimi_cli"


def test_workbench_workflow_template_injects_processor_operation_config(tmp_path: Path) -> None:
    template = load_workflow_template_by_id(tmp_path / "workspace", "default_drawai_dag")

    effective = _workflow_template_with_agent_settings(
        template,
        WorkbenchAgentSettings(),
        processor_operation_config={
            "page_spec_processing_types": ["no_process", "image_edit"],
            "page_spec_processing_operations": {
                "image_edit": {
                    "meaning": "Workspace image edit meaning.",
                    "choose_when": "Workspace image edit choose.",
                    "avoid_when": "Workspace image edit avoid.",
                }
            },
        },
    )

    node = {item.node_id: item for item in effective.nodes}["page_spec_refine"]
    assert node.config["page_spec_processing_types"] == ["no_process", "image_edit"]
    assert node.config["page_spec_processing_operations"]["image_edit"]["meaning"] == "Workspace image edit meaning."


def test_case_progress_exposes_effective_workflow_node_runtime_metadata(tmp_path: Path) -> None:
    store = WorkbenchStore(tmp_path / "workspace")
    base_config = _base_config(tmp_path)
    source = tmp_path / "single.png"
    Image.new("RGB", (24, 24), "white").save(source)
    settings = _settings(tmp_path, base_config)
    runner = WorkbenchRunner(store, settings, stage_executor=lambda _case, _stage: None)
    app = create_app(settings, store=store, runner=runner)
    client = TestClient(app)
    preset_response = client.put(
        "/api/workbench/api-presets",
        json={
            "presets": [
                {
                    "id": "apimart_images",
                    "label": "Apimart Images",
                    "type": "images_api",
                    "base_url": "https://api.apimart.ai/v1/images/generations",
                    "model": "gpt-image-2",
                    "api_key_env": "APIMART_API_KEY",
                }
            ]
        },
    )
    assert preset_response.status_code == 200
    processor_response = client.put(
        "/api/workbench/processor-settings",
        json={
            "processors": {
                "image_generate": {
                    "enabled": True,
                    "driver_id": "openai_images_api",
                    "api_preset_id": "apimart_images",
                }
            }
        },
    )
    assert processor_response.status_code == 200
    agent_response = client.put(
        "/api/workbench/agent-settings",
        json={
            "selected_provider_id": "hermes_acp",
            "model": "hermes-model",
        },
    )
    assert agent_response.status_code == 200
    batch = store.create_batch(
        name="metadata batch",
        input_mode="local_dir",
        max_concurrent_cases=1,
        auto_run_svg_after_analysis=False,
        config_path=base_config,
        execution_mode="agent",
    )
    case = store.create_case(
        batch_id=batch.batch_id,
        name=source.name,
        source_image_path=source,
        config_path=base_config,
    )
    _write_workflow_node_run_fixture(
        Path(case.run_root),
        "page_spec_refine",
        output_type="element_plans",
        format_id="drawai.element_plans.v1",
        output_payload={"elements": []},
        output_name="elements.json",
        provider_id="kimi_acp",
        resource_id="agent_provider:kimi_acp",
    )

    response = client.get(f"/api/cases/{case.case_id}/progress")

    assert response.status_code == 200
    payload = response.json()
    runs = {item["node_id"]: item for item in payload["workflow_node_runs"]}
    assert runs["page_spec_refine"]["provider_id"] == "kimi_acp"
    assert runs["page_spec_refine"]["provider_label"] == "Kimi ACP"
    assert runs["page_spec_refine"]["resource_id"] == "agent_provider:kimi_acp"
    nodes = {item["node_id"]: item for item in payload["workflow_nodes"]}
    assert nodes["page_spec_refine"]["provider_id"] == "hermes_acp"
    assert nodes["page_spec_refine"]["provider_label"] == "Hermes ACP"
    assert nodes["page_spec_refine"]["model"] == "hermes-model"
    assert nodes["page_spec_refine"]["api_presets"] == []
    assert nodes["page_spec_refine"]["processor_types"] == [
        "no_process",
        "crop",
        "crop_nobg",
        "image_generate",
    ]
    assert nodes["asset_prepare"]["api_presets"] == [
        {
            "processing_type": "image_generate",
            "api_preset_id": "apimart_images",
            "api_preset_label": "Apimart Images",
        }
    ]
    assert nodes["asset_prepare"]["processor_types"] == []


def test_create_batch_binds_selected_workflow_template(tmp_path: Path) -> None:
    store = WorkbenchStore(tmp_path / "workspace")
    base_config = _base_config(tmp_path)
    source = tmp_path / "single.png"
    Image.new("RGB", (24, 24), "white").save(source)
    settings = _settings(tmp_path, base_config)
    runner = WorkbenchRunner(store, settings, stage_executor=lambda _case, _stage: None)
    app = create_app(settings, store=store, runner=runner)
    client = TestClient(app)

    copy_response = client.post(
        "/api/workflow/templates/copy",
        json={"template_id": "default_drawai_dag", "name": "Batch Template"},
    )
    template_id = copy_response.json()["template"]["template_id"]
    response = client.post(
        "/api/batches",
        json={
            "name": "workflow batch",
            "input_mode": "local_dir",
            "local_dir": str(source),
            "auto_run_svg_after_analysis": False,
            "max_concurrent_cases": 1,
            "base_config_path": str(base_config),
            "workflow_template_id": template_id,
        },
    )

    assert response.status_code == 200
    assert response.json()["batch"]["workflow_template_id"] == template_id
    assert store.get_batch(response.json()["batch"]["batch_id"]).workflow_template_id == template_id


def test_workbench_workflow_export_node_converts_connected_svg_without_run_package(tmp_path: Path) -> None:
    store = WorkbenchStore(tmp_path / "workspace")
    base_config = _base_config(tmp_path)
    source = tmp_path / "single.png"
    Image.new("RGB", (24, 24), "white").save(source)
    template_id = "custom_direct_svg_export"
    _write_direct_svg_export_template(store.workspace, template_id)

    def agent_executor(request: AgentExecutionRequest) -> AgentExecutionResult:
        output_path = request.workdir / str(request.prompt.outputs[0]["path"])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 360">
  <rect x="0" y="0" width="640" height="360" fill="#ffffff"/>
  <rect x="48" y="64" width="220" height="120" fill="#dceeff" stroke="#2563eb"/>
  <text x="72" y="132" font-size="28" fill="#111827">DrawAI</text>
</svg>""",
            encoding="utf-8",
        )
        prompt_path = request.workdir / "prompt.md"
        prompt_path.write_text(request.prompt.text, encoding="utf-8")
        return AgentExecutionResult(
            provider_id=request.prompt.provider_id,
            prompt_path=prompt_path,
            exit_code=0,
        )

    batch = store.create_batch(
        name="workflow svg export",
        input_mode="local_dir",
        max_concurrent_cases=1,
        auto_run_svg_after_analysis=True,
        config_path=base_config,
        workflow_template_id=template_id,
    )
    case = store.create_case(
        batch_id=batch.batch_id,
        name=source.name,
        source_image_path=source,
        config_path=base_config,
    )
    runner = WorkbenchRunner(
        store,
        _settings(tmp_path, base_config),
        stage_executor=lambda _case, _stage: None,
        agent_executor=agent_executor,
    )

    runner._run_workflow_case(case.case_id)

    run_root = Path(store.get_case(case.case_id).run_root)
    assert not (run_root / "drawai_package.json").exists()
    pptx_path = run_root / "svg_to_ppt" / "semantic.svg_to_ppt.pptx"
    assert pptx_path.is_file()
    with zipfile.ZipFile(pptx_path) as archive:
        assert "[Content_Types].xml" in archive.namelist()
        assert "ppt/presentation.xml" in archive.namelist()
    report = json.loads((run_root / "reports" / "svg_to_ppt_export_report.json").read_text(encoding="utf-8"))
    assert report["status"] == "ok"
    final_outputs = json.loads(
        (run_root / "nodes" / "output" / "runs" / "001" / "output" / "final_outputs.json").read_text(encoding="utf-8")
    )
    assert final_outputs["outputs"][0]["format_id"] == "drawai.pptx.v1"


def test_workflow_export_node_uses_canonical_svg_dir_for_page_spec_assets(tmp_path: Path) -> None:
    store = WorkbenchStore(tmp_path / "workspace")
    base_config = _base_config(tmp_path)
    source = tmp_path / "single.png"
    Image.new("RGB", (32, 32), "white").save(source)
    batch = store.create_batch(
        name="workflow asset href export",
        input_mode="local_dir",
        max_concurrent_cases=1,
        auto_run_svg_after_analysis=True,
        config_path=base_config,
        workflow_template_id="default_drawai_dag",
    )
    case = store.create_case(
        batch_id=batch.batch_id,
        name=source.name,
        source_image_path=source,
        config_path=base_config,
    )
    run_root = Path(case.run_root)
    page_spec_dir = run_root / "nodes" / "asset_prepare" / "runs" / "001" / "output"
    asset_dir = page_spec_dir / "assets" / "E001"
    asset_dir.mkdir(parents=True)
    Image.new("RGBA", (8, 8), (40, 120, 220, 255)).save(asset_dir / "active.png")
    page_spec_path = page_spec_dir / "page_spec.json"
    page_spec_path.write_text(
        json.dumps(
            {
                "schema": "drawai.page_spec.v1",
                "page_id": case.case_id,
                "source": {"image": "inputs/figure.png", "width_px": 32, "height_px": 32},
                "canvas": {"width_px": 32, "height_px": 32},
                "background": {},
                "elements": [
                    {
                        "id": "E001",
                        "kind": "image",
                        "role": "picture",
                        "box_px": [4, 4, 8, 8],
                        "build": {"mode": "asset_ref", "processing_type": "crop"},
                        "materialization": {
                            "status": "ok",
                            "outputs": {
                                "active": {
                                    "path": "assets/E001/active.png",
                                    "media_type": "image/png",
                                    "width_px": 8,
                                    "height_px": 8,
                                }
                            },
                        },
                    }
                ],
                "metadata": {},
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    svg_dir = run_root / "nodes" / "svg_compose" / "runs" / "001" / "output"
    svg_dir.mkdir(parents=True)
    svg_path = svg_dir / "semantic.svg"
    svg_path.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" width="32" height="32">
  <rect x="0" y="0" width="32" height="32" fill="#ffffff"/>
  <rect x="17" y="6" width="10" height="8" fill="#dceeff" stroke="#2563eb"/>
  <text x="17" y="24" font-size="5" fill="#111827">DrawAI</text>
  <image id="image-E001" href="../nodes/asset_prepare/runs/001/output/assets/E001/active.png" x="4" y="4" width="8" height="8"/>
</svg>
""",
        encoding="utf-8",
    )
    node = WorkflowNode(
        node_id="svg_to_ppt",
        node_type="export",
        title="SVG to PPT",
        inputs=(
            WorkflowPort("semantic_svg", "Semantic SVG", ("semantic_svg",), formats=("drawai.semantic_svg.v1",)),
            WorkflowPort("page_spec", "PageSpec", ("page_spec",), formats=("drawai.page_spec.v1",), required=False),
        ),
        outputs=(WorkflowPort("pptx", "PPTX", ("pptx",), formats=("drawai.pptx.v1",)),),
        config={"exporter_id": "svg_to_ppt"},
    )
    template = WorkflowTemplate(
        template_id="direct_export",
        name="Direct Export",
        nodes=(node,),
        edges=(),
    )
    record = begin_node_run(run_root, "svg_to_ppt", node_type="export")
    context = NodeRunContext(template=template, node=node, run_root=run_root, record=record)
    runner = WorkbenchRunner(store, _settings(tmp_path, base_config), stage_executor=lambda _case, _stage: None)

    outputs = runner._run_workflow_export_node(
        case,
        context,
        (
            {
                "port_id": "semantic_svg",
                "path": str(svg_path.relative_to(run_root)),
                "type": "semantic_svg",
                "format_id": "drawai.semantic_svg.v1",
            },
            {
                "port_id": "page_spec",
                "path": str(page_spec_path.relative_to(run_root)),
                "type": "page_spec",
                "format_id": "drawai.page_spec.v1",
            },
        ),
        {},
    )

    assert outputs[0]["format_id"] == "drawai.pptx.v1"
    assert (run_root / "svg" / "semantic.svg").is_file()
    assert (run_root / "svg_to_ppt" / "semantic.svg_to_ppt.pptx").is_file()
    report = json.loads((run_root / "reports" / "svg_to_ppt_export_report.json").read_text(encoding="utf-8"))
    assert report["status"] == "ok"
    manifest = json.loads((run_root / "svg_to_ppt" / "assets" / "asset_manifest.json").read_text(encoding="utf-8"))
    assert manifest["assets"][0]["svg_href"] == "../nodes/asset_prepare/runs/001/output/assets/E001/active.png"


def _client(tmp_path: Path) -> TestClient:
    store = WorkbenchStore(tmp_path / "workspace")
    base_config = _base_config(tmp_path)
    settings = _settings(tmp_path, base_config)
    runner = WorkbenchRunner(store, settings, stage_executor=lambda _case, _stage: None)
    return TestClient(create_app(settings, store=store, runner=runner))


def _settings(tmp_path: Path, base_config: Path) -> WorkbenchSettings:
    return WorkbenchSettings(
        workspace=tmp_path / "workspace",
        default_config=base_config,
        max_concurrent_cases=2,
    )


def _base_config(tmp_path: Path) -> Path:
    path = tmp_path / "base.yaml"
    path.write_text(
        "\n".join(
            [
                "input:",
                f"  image: {tmp_path / 'missing.png'}",
                f"  output_dir: {tmp_path / 'out'}",
                "svg_to_ppt:",
                "  enabled: true",
                "  export_pptx: true",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def _write_executable(path: Path, body: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/bin/sh\n" + body, encoding="utf-8")
    path.chmod(0o755)
    return path


def _write_workflow_node_run_fixture(
    root: Path,
    node_id: str,
    *,
    output_type: str,
    format_id: str,
    output_payload: object,
    output_name: str,
    provider_id: str = "",
    resource_id: str = "",
) -> None:
    run_dir = root / "nodes" / node_id / "runs" / "001"
    output_relative_path = Path("nodes") / node_id / "runs" / "001" / "output" / output_name
    output_path = root / output_relative_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "node_run.json").write_text(
        json.dumps(
            {
                "schema": "drawai.workflow_node_run.v1",
                "node_id": node_id,
                "node_type": "agent",
                "attempt_id": "001",
                "status": "ok",
                "workdir": f"nodes/{node_id}/runs/001",
                "provider_id": provider_id,
                "resource_id": resource_id,
                "inputs": [],
                "outputs": [
                    {
                        "port_id": "output",
                        "path": output_relative_path.as_posix(),
                        "format_id": format_id,
                        "type": output_type,
                        "exit_code": 0,
                        "source_node_id": node_id,
                        "source_port_id": "output",
                    }
                ],
                "started_at": "2026-06-18T00:00:00Z",
                "ended_at": "2026-06-18T00:00:01Z",
                "duration_ms": 1000,
                "exit_code": 0,
                "error": None,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def _write_direct_svg_export_template(workspace: Path, template_id: str) -> None:
    template_path = user_workflow_template_path(workspace, template_id)
    template_path.parent.mkdir(parents=True, exist_ok=True)
    template_path.write_text(
        json.dumps(
            {
                "schema": "drawai.workflow_template.v1",
                "template_id": template_id,
                "name": "Direct SVG Export",
                "version": 1,
                "nodes": [
                    {
                        "node_id": "input",
                        "node_type": "input",
                        "title": "Input",
                        "outputs": [
                            {
                                "port_id": "image",
                                "label": "Image",
                                "types": ["image"],
                                "required": False,
                                "cardinality": "single",
                                "formats": ["drawai.image.v1"],
                            }
                        ],
                    },
                    {
                        "node_id": "svg_agent",
                        "node_type": "agent",
                        "title": "SVG Agent",
                        "inputs": [
                            {
                                "port_id": "image",
                                "label": "Image",
                                "types": ["image"],
                                "required": True,
                                "cardinality": "single",
                                "formats": ["drawai.image.v1"],
                            }
                        ],
                        "outputs": [
                            {
                                "port_id": "semantic_svg",
                                "label": "Semantic SVG",
                                "types": ["semantic_svg"],
                                "required": False,
                                "cardinality": "single",
                                "formats": ["drawai.semantic_svg.v1"],
                            }
                        ],
                        "config": {
                            "preset_id": "custom_agent",
                            "provider_id": "codex_sdk",
                            "task": "Write a semantic SVG.",
                            "outputs": [
                                {
                                    "port_id": "semantic_svg",
                                    "path": "output/semantic.svg",
                                    "format_id": "drawai.semantic_svg.v1",
                                    "type": "semantic_svg",
                                    "description": "Semantic SVG.",
                                }
                            ],
                        },
                    },
                    {
                        "node_id": "svg_to_ppt",
                        "node_type": "export",
                        "title": "SVG to PPT",
                        "inputs": [
                            {
                                "port_id": "semantic_svg",
                                "label": "Semantic SVG",
                                "types": ["semantic_svg"],
                                "required": True,
                                "cardinality": "single",
                            }
                        ],
                        "outputs": [
                            {
                                "port_id": "pptx",
                                "label": "PPTX",
                                "types": ["pptx"],
                                "required": False,
                                "cardinality": "single",
                                "formats": ["drawai.pptx.v1"],
                                "description": "deliverable",
                            }
                        ],
                        "config": {"exporter_id": "svg_to_ppt"},
                    },
                    {
                        "node_id": "output",
                        "node_type": "output",
                        "title": "Output",
                        "inputs": [
                            {
                                "port_id": "deliverables",
                                "label": "Deliverables",
                                "types": ["pptx"],
                                "required": True,
                                "cardinality": "many",
                            }
                        ],
                        "outputs": [
                            {
                                "port_id": "final_outputs",
                                "label": "Final Outputs",
                                "types": ["final_outputs"],
                                "required": False,
                                "cardinality": "single",
                                "formats": ["drawai.final_outputs.v1"],
                            }
                        ],
                    },
                ],
                "edges": [
                    {
                        "edge_id": "e1",
                        "source_node_id": "input",
                        "source_port_id": "image",
                        "target_node_id": "svg_agent",
                        "target_port_id": "image",
                    },
                    {
                        "edge_id": "e2",
                        "source_node_id": "svg_agent",
                        "source_port_id": "semantic_svg",
                        "target_node_id": "svg_to_ppt",
                        "target_port_id": "semantic_svg",
                    },
                    {
                        "edge_id": "e3",
                        "source_node_id": "svg_to_ppt",
                        "source_port_id": "pptx",
                        "target_node_id": "output",
                        "target_port_id": "deliverables",
                    },
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
