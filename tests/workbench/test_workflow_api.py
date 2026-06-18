from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image

from drawai.workbench.api import create_app
from drawai.workbench.models import WorkbenchSettings
from drawai.workbench.runner import WorkbenchRunner
from drawai.workbench.store import WorkbenchStore
from drawai.workflow.templates import load_workflow_template_by_id


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
            "node_config": {"provider_id": "kimi_cli"},
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
    assert "Fused element plans." in payload["text"]


def test_workbench_workflow_provider_api_lists_provider_scoped_limits(tmp_path: Path) -> None:
    client = _client(tmp_path)

    response = client.get("/api/workflow/providers")

    assert response.status_code == 200
    providers = {item["provider_id"]: item for item in response.json()["providers"]}
    assert providers["codex_sdk"]["resource_key"] == "agent_provider:codex_sdk"
    assert providers["kimi_cli"]["resource_key"] == "agent_provider:kimi_cli"


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
