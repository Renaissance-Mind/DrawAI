from __future__ import annotations

import json
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image

from drawai.workflow.agent_execution import AgentExecutionRequest, AgentExecutionResult
from drawai.workbench.api import create_app
from drawai.workbench.models import WorkbenchSettings
from drawai.workbench.runner import WorkbenchRunner
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
    assert "input_manifest.json" in payload["text"]
    assert "From Agent cwd: ../../../nodes/fusion/runs/001/output/elements.json" in payload["text"]
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
