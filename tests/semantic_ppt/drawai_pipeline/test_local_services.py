from __future__ import annotations

import base64
import io
import os
import sys
import threading
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from drawai.local_services import (
    LocalServiceSettings,
    _maybe_reexec_into_runtime_venv,
    _parse_args,
    _runtime_venv_python,
    create_local_services_app,
)
from drawai.rmbg_client import RmbgResult


def test_local_services_health_reports_contract_ports(tmp_path: Path) -> None:
    app = create_local_services_app(
        settings=LocalServiceSettings(runtime_root=tmp_path, sam_port=18080, ocr_port=18080),
        sam3_transport=RecordingSam3Transport(),
        ocr_provider=RecordingOcrProvider(),
        rmbg_client=RecordingRmbgClient(),
    )
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["services"]["sam3"]["endpoint"] == "/v1/segment/proposals"
    assert payload["services"]["ocr"]["endpoint"] == "/v1/ocr/boxes"
    assert payload["services"]["rmbg"]["endpoint"] == "/v1/rmbg/remove-background"
    assert payload["services"]["sam3"]["port"] == 18080
    assert payload["services"]["ocr"]["port"] == 18080
    assert payload["services"]["rmbg"]["port"] == 18080


def test_local_services_can_enable_only_selected_models(tmp_path: Path) -> None:
    app = create_local_services_app(
        settings=LocalServiceSettings(runtime_root=tmp_path, models=("ocr",)),
        sam3_transport=RecordingSam3Transport(),
        ocr_provider=RecordingOcrProvider(),
        rmbg_client=RecordingRmbgClient(),
    )
    client = TestClient(app)

    health = client.get("/health").json()
    assert sorted(health["services"]) == ["ocr"]
    assert client.post("/v1/segment/proposals", json={}).status_code == 404


def test_local_services_reexecs_into_runtime_venv(monkeypatch, tmp_path: Path) -> None:
    runtime_root = tmp_path / "runtime"
    runtime_python = _runtime_venv_python(runtime_root)
    runtime_python.parent.mkdir(parents=True)
    runtime_python.write_text("#!/usr/bin/env python\n", encoding="utf-8")
    runtime_python.chmod(0o755)
    monkeypatch.setattr(sys, "prefix", str(tmp_path / "project_venv"))
    monkeypatch.delenv("DRAWAI_LOCAL_RUNTIME_REEXEC", raising=False)
    calls = []

    class ExecveCalled(Exception):
        pass

    def fake_execve(path, argv, env):
        calls.append((path, argv, env))
        raise ExecveCalled

    monkeypatch.setattr(os, "execve", fake_execve)
    args = _parse_args(["sam3", "--runtime-root", str(runtime_root)])

    with pytest.raises(ExecveCalled):
        _maybe_reexec_into_runtime_venv(args, ["sam3", "--runtime-root", str(runtime_root)])

    path, argv, env = calls[0]
    assert path == str(runtime_python)
    assert argv[:3] == [str(runtime_python), "-m", "drawai.local_services"]
    assert argv[3:] == ["sam3", "--runtime-root", str(runtime_root)]
    assert env["DRAWAI_LOCAL_RUNTIME_REEXEC"] == "1"
    assert env["DRAWAI_LOCAL_RUNTIME_ROOT"] == str(runtime_root.resolve(strict=False))


def test_local_services_reports_missing_runtime_venv(monkeypatch, tmp_path: Path) -> None:
    runtime_root = tmp_path / "runtime"
    args = _parse_args(["--runtime-root", str(runtime_root)])
    monkeypatch.delenv("DRAWAI_LOCAL_RUNTIME_REEXEC", raising=False)
    monkeypatch.delenv("DRAWAI_SKIP_LOCAL_RUNTIME_REEXEC", raising=False)

    message = _maybe_reexec_into_runtime_venv(args, ["--runtime-root", str(runtime_root)])

    assert "Local DrawAI runtime Python not found" in message
    assert "uv run drawai setup local --bootstrap-only" in message


def test_local_services_serves_sam3_proposals_contract(tmp_path: Path) -> None:
    transport = RecordingSam3Transport()
    app = create_local_services_app(
        settings=LocalServiceSettings(runtime_root=tmp_path),
        sam3_transport=transport,
        ocr_provider=RecordingOcrProvider(),
        rmbg_client=RecordingRmbgClient(),
    )
    client = TestClient(app)

    response = client.post(
        "/v1/segment/proposals",
        json={
            "image_base64": base64.b64encode(b"image").decode("ascii"),
            "prompts": [{"id": "arrow", "text": "arrow"}],
        },
    )

    assert response.status_code == 200
    assert response.json()["regions"][0]["bbox"] == [1, 2, 10, 12]
    assert transport.calls[0][0] == "/v1/segment/proposals"
    assert transport.calls[0][1]["prompts"][0]["id"] == "arrow"


def test_local_services_reports_sam3_busy_without_blocking_on_inference_queue(tmp_path: Path) -> None:
    transport = BlockingSam3Transport()
    app = create_local_services_app(
        settings=LocalServiceSettings(runtime_root=tmp_path),
        sam3_transport=transport,
        ocr_provider=RecordingOcrProvider(),
        rmbg_client=RecordingRmbgClient(),
    )
    client = TestClient(app)
    first_response = {}

    def run_first_request() -> None:
        first_response["response"] = client.post(
            "/v1/segment/proposals",
            json={
                "image_base64": base64.b64encode(b"image").decode("ascii"),
                "prompts": [{"id": "arrow", "text": "arrow"}],
            },
        )

    thread = threading.Thread(target=run_first_request)
    thread.start()
    assert transport.entered.wait(timeout=2)

    response = client.post(
        "/v1/segment/proposals",
        json={
            "image_base64": base64.b64encode(b"image").decode("ascii"),
            "prompts": [{"id": "arrow", "text": "arrow"}],
        },
    )

    assert response.status_code == 503
    assert response.headers["x-drawai-queue"] == "model-busy"
    assert response.headers["retry-after"] == "1"
    assert response.json()["detail"]["code"] == "model_busy"
    assert response.json()["detail"]["model"] == "sam3"
    transport.release.set()
    thread.join(timeout=2)
    assert first_response["response"].status_code == 200


def test_local_services_serves_ocr_boxes_contract(tmp_path: Path) -> None:
    provider = RecordingOcrProvider()
    app = create_local_services_app(
        settings=LocalServiceSettings(runtime_root=tmp_path),
        sam3_transport=RecordingSam3Transport(),
        ocr_provider=provider,
        rmbg_client=RecordingRmbgClient(),
    )
    client = TestClient(app)

    response = client.post(
        "/v1/ocr/boxes",
        json={
            "image_base64": base64.b64encode(b"png bytes").decode("ascii"),
            "filename": "figure.png",
        },
    )

    assert response.status_code == 200
    assert response.json()["ocr_text_boxes"][0]["text"] == "DrawAI"
    assert provider.images[0].read_bytes() == b"png bytes"
    assert provider.images[0].name.endswith("_figure.png")


def test_local_services_reports_ocr_busy_without_blocking_on_inference_queue(tmp_path: Path) -> None:
    provider = BlockingOcrProvider()
    app = create_local_services_app(
        settings=LocalServiceSettings(runtime_root=tmp_path),
        sam3_transport=RecordingSam3Transport(),
        ocr_provider=provider,
        rmbg_client=RecordingRmbgClient(),
    )
    client = TestClient(app)
    first_response = {}

    def run_first_request() -> None:
        first_response["response"] = client.post(
            "/v1/ocr/boxes",
            json={
                "image_base64": base64.b64encode(b"png bytes").decode("ascii"),
                "filename": "figure.png",
            },
        )

    thread = threading.Thread(target=run_first_request)
    thread.start()
    assert provider.entered.wait(timeout=2)

    response = client.post(
        "/v1/ocr/boxes",
        json={
            "image_base64": base64.b64encode(b"png bytes").decode("ascii"),
            "filename": "figure.png",
        },
    )

    assert response.status_code == 503
    assert response.headers["x-drawai-queue"] == "model-busy"
    assert response.headers["retry-after"] == "1"
    assert response.json()["detail"]["code"] == "model_busy"
    assert response.json()["detail"]["model"] == "ocr"
    provider.release.set()
    thread.join(timeout=2)
    assert first_response["response"].status_code == 200


def test_local_services_rejects_missing_ocr_image_base64(tmp_path: Path) -> None:
    app = create_local_services_app(
        settings=LocalServiceSettings(runtime_root=tmp_path),
        sam3_transport=RecordingSam3Transport(),
        ocr_provider=RecordingOcrProvider(),
        rmbg_client=RecordingRmbgClient(),
    )
    client = TestClient(app)

    response = client.post("/v1/ocr/boxes", json={})

    assert response.status_code == 400
    assert "image_base64" in response.json()["detail"]


def test_local_services_serves_rmbg_remove_background_contract(tmp_path: Path) -> None:
    rmbg = RecordingRmbgClient()
    app = create_local_services_app(
        settings=LocalServiceSettings(runtime_root=tmp_path),
        sam3_transport=RecordingSam3Transport(),
        ocr_provider=RecordingOcrProvider(),
        rmbg_client=rmbg,
    )
    client = TestClient(app)
    image = Image.new("RGB", (3, 2), "white")

    response = client.post(
        "/v1/rmbg/remove-background",
        json={
            "image_base64": _image_to_base64(image),
            "output_name": "asset.png",
            "artifact_prefix": "asset_001",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    output = _image_from_base64(payload["image_base64"])
    assert output.mode == "RGBA"
    assert output.size == (3, 2)
    assert payload["artifacts"]["runtime"] == "test_rmbg"
    assert rmbg.calls[0]["output_name"] == "asset.png"


class RecordingSam3Transport:
    def __init__(self) -> None:
        self.calls = []

    def post_json(self, path: str, payload: dict, timeout_s: float):
        self.calls.append((path, payload, timeout_s))
        return {
            "regions": [{"id": "region_001", "bbox": [1, 2, 10, 12], "score": 0.9}],
            "raw_regions": [{"id": "arrow_001", "bbox": [1, 2, 10, 12], "score": 0.9}],
            "artifacts": {},
        }, 12.5


class BlockingSam3Transport:
    def __init__(self) -> None:
        self.entered = threading.Event()
        self.release = threading.Event()

    def post_json(self, path: str, payload: dict, timeout_s: float):
        del path, payload, timeout_s
        self.entered.set()
        assert self.release.wait(timeout=2)
        return {
            "regions": [{"id": "region_001", "bbox": [1, 2, 10, 12], "score": 0.9}],
            "raw_regions": [],
            "artifacts": {},
        }, 12.5


class RecordingOcrProvider:
    def __init__(self) -> None:
        self.images: list[Path] = []

    def extract_boxes(self, image_path: Path):
        self.images.append(image_path)
        return {
            "ocr_text_boxes": [
                {
                    "id": "T001",
                    "bbox": [1, 2, 20, 10],
                    "confidence": 0.95,
                    "source": "local_paddleocr",
                    "text": "DrawAI",
                }
            ],
            "provider": "local_paddleocr",
        }


class BlockingOcrProvider:
    def __init__(self) -> None:
        self.entered = threading.Event()
        self.release = threading.Event()

    def extract_boxes(self, image_path: Path):
        del image_path
        self.entered.set()
        assert self.release.wait(timeout=2)
        return {
            "ocr_text_boxes": [
                {
                    "id": "T001",
                    "bbox": [1, 2, 20, 10],
                    "confidence": 0.95,
                    "source": "local_paddleocr",
                    "text": "DrawAI",
                }
            ],
            "provider": "local_paddleocr",
        }


class RecordingRmbgClient:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def remove_background(self, image, output_name: str, *, timeout_s: float, model_path: str = "", artifact_prefix=None):
        self.calls.append(
            {
                "image": image,
                "output_name": output_name,
                "timeout_s": timeout_s,
                "model_path": model_path,
                "artifact_prefix": artifact_prefix,
            }
        )
        output = image.convert("RGBA")
        output.putalpha(128)
        return RmbgResult(image=output, artifacts={"runtime": "test_rmbg"}, elapsed_ms=7.5)


def _image_to_base64(image: Image.Image) -> str:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def _image_from_base64(value: str) -> Image.Image:
    return Image.open(io.BytesIO(base64.b64decode(value))).convert("RGBA")
