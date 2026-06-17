import base64
import hashlib
import io
import json
import urllib.error
from email.message import Message
from pathlib import Path

import pytest
from PIL import Image

from drawai.artifacts import prepare_artifact_paths
from drawai.config import load_drawai_config
from drawai.sam3_client import (
    HttpJsonTransport,
    Sam3ResponseError,
    run_sam3_prompt_plan,
)


class FakeSam3Transport:
    def __init__(self):
        self.payloads = []

    def post_json(self, path, payload, timeout_s):
        self.payloads.append((path, payload, timeout_s))
        return {
            "regions": [
                {
                    "bbox": [1, 2, 10, 20],
                    "score": 0.9,
                    "label": payload["prompts"][0]["text"],
                }
            ],
            "raw_regions": [
                {
                    "bbox": [1, 2, 10, 20],
                    "score": 0.9,
                    "source_prompt": "service-origin",
                }
            ],
            "artifacts": {"overlay": "data:image/png;base64,AAAA"},
        }, 12.3


def test_run_sam3_prompt_plan_writes_each_prompt(tmp_path: Path):
    image = tmp_path / "input.png"
    Image.new("RGB", (32, 16), "white").save(image)
    config = tmp_path / "config.yaml"
    config.write_text(
        f"""
input:
  image: {image.name}
  output_dir: out
sam3:
  prompts:
    - id: arrow
      text: arrow
      confidence_threshold: 0.3
    - id: icon
      text: icon
      confidence_threshold: 0.3
""",
        encoding="utf-8",
    )
    cfg = load_drawai_config(config)
    paths = prepare_artifact_paths(cfg.input.output_dir)
    transport = FakeSam3Transport()

    result = run_sam3_prompt_plan(cfg.sam3, image, paths, transport=transport)

    assert [run.prompt_id for run in result.prompt_runs] == ["arrow", "icon"]
    assert (paths.prompt_runs_dir / "arrow.json").exists()
    assert (paths.prompt_runs_dir / "icon.json").exists()
    assert (paths.sam_prompt_overlays_dir / "arrow.png").exists()
    assert (paths.sam_prompt_overlays_dir / "icon.png").exists()
    assert len(result.raw_regions) == 2
    encoded = transport.payloads[0][1]["image_base64"]
    base64.b64decode(encoded)
    assert [path for path, _payload, _timeout in transport.payloads] == [
        "/v1/segment/proposals",
        "/v1/segment/proposals",
    ]
    assert all(len(payload["prompts"]) == 1 for _path, payload, _timeout in transport.payloads)
    assert all(payload["return_masks"] is False for _path, payload, _timeout in transport.payloads)

    raw_regions_payload = json.loads(paths.raw_regions_json.read_text(encoding="utf-8"))
    assert [region["source_prompt"] for region in raw_regions_payload["raw_regions"]] == [
        "arrow",
        "icon",
    ]
    assert [region["source_prompt_meta"]["text"] for region in raw_regions_payload["raw_regions"]] == [
        "arrow",
        "icon",
    ]
    assert [region["sam3_source_prompt"] for region in raw_regions_payload["raw_regions"]] == [
        "service-origin",
        "service-origin",
    ]
    assert raw_regions_payload["prompt_runs"][0]["review_overlay_path"].endswith("sam3/prompt_overlays/arrow.png")

    prompt_artifact = paths.prompt_runs_dir / "arrow.json"
    prompt_artifact_text = prompt_artifact.read_text(encoding="utf-8")
    prompt_payload = json.loads(prompt_artifact_text)
    assert prompt_payload["request"]["prompts"][0]["id"] == "arrow"
    assert "image_base64" not in prompt_payload["request"]
    assert '"image_base64":' not in prompt_artifact_text
    image_bytes = image.read_bytes()
    assert prompt_payload["request"]["image_path"] == str(image)
    assert prompt_payload["request"]["image_sha256"] == hashlib.sha256(image_bytes).hexdigest()
    assert prompt_payload["request"]["image_bytes"] == len(image_bytes)
    assert prompt_payload["request"]["image_base64_chars"] == len(transport.payloads[0][1]["image_base64"])
    assert "data:image" not in prompt_artifact_text
    assert prompt_payload["response"]["artifacts"]["overlay"]["redacted"] is True
    assert prompt_payload["artifacts"]["overlay"]["redacted"] is True
    assert prompt_payload["regions"][0]["label"] == "arrow"
    assert prompt_payload["raw_regions"][0]["source_prompt"] == "arrow"
    assert prompt_payload["raw_regions"][0]["source_prompt_meta"]["id"] == "arrow"
    assert prompt_payload["raw_regions"][0]["sam3_source_prompt"] == "service-origin"
    assert prompt_payload["review_overlay_path"].endswith("sam3/prompt_overlays/arrow.png")
    assert prompt_payload["elapsed_ms"] == 12.3


def test_run_sam3_prompt_plan_localizes_mask_artifacts(tmp_path: Path):
    image = tmp_path / "input.png"
    Image.new("RGB", (32, 16), "white").save(image)
    runtime_dir = tmp_path / "runtime" / "sam3_job"
    mask_dir = runtime_dir / "masks"
    mask_dir.mkdir(parents=True)
    Image.new("L", (32, 16), 255).save(mask_dir / "icon.png")
    config = tmp_path / "config.yaml"
    config.write_text(
        f"""
input:
  image: {image.name}
  output_dir: out
sam3:
  return_masks: true
  prompts:
    - id: icon
      text: icon
      confidence_threshold: 0.3
""",
        encoding="utf-8",
    )

    class MaskTransport:
        def post_json(self, path, payload, timeout_s):
            assert payload["return_masks"] is True
            return {
                "regions": [{"bbox": [4, 3, 20, 12], "score": 0.9, "label": "icon"}],
                "raw_regions": [
                    {
                        "bbox": [4, 3, 20, 12],
                        "score": 0.9,
                        "mask_path": "masks/icon.png",
                        "geometry": {
                            "kind": "mask",
                            "mask_path": "masks/icon.png",
                            "bbox": [4, 3, 20, 12],
                        },
                    }
                ],
                "artifacts": {
                    "regions_json": str(runtime_dir / "regions.json"),
                    "mask_dir": str(mask_dir),
                },
            }, 5.0

    cfg = load_drawai_config(config)
    paths = prepare_artifact_paths(cfg.input.output_dir)
    result = run_sam3_prompt_plan(cfg.sam3, image, paths, transport=MaskTransport())

    mask_files = sorted(paths.sam_masks_dir.glob("*.png"))
    assert len(mask_files) == 1
    region = result.raw_regions[0]
    assert region["mask_path"] == mask_files[0].relative_to(paths.root).as_posix()
    assert region["geometry"]["kind"] == "mask"
    assert region["geometry"]["mask_path"] == region["mask_path"]
    raw_regions_payload = json.loads(paths.raw_regions_json.read_text(encoding="utf-8"))
    assert raw_regions_payload["raw_regions"][0]["geometry"]["mask_path"] == region["mask_path"]


def test_run_sam3_prompt_plan_normalizes_missing_optional_response_fields(tmp_path: Path):
    class MissingOptionalFieldsTransport:
        def post_json(self, path, payload, timeout_s):
            return {"regions": []}, 3.4

    image = tmp_path / "input.png"
    Image.new("RGB", (8, 8), "white").save(image)
    config = tmp_path / "config.yaml"
    config.write_text(
        f"""
input:
  image: {image.name}
  output_dir: out
sam3:
  prompts:
    - id: arrow
      text: arrow
      confidence_threshold: 0.3
""",
        encoding="utf-8",
    )
    cfg = load_drawai_config(config)
    paths = prepare_artifact_paths(cfg.input.output_dir)

    result = run_sam3_prompt_plan(
        cfg.sam3,
        image,
        paths,
        transport=MissingOptionalFieldsTransport(),
    )

    assert result.prompt_runs[0].raw_regions == []
    assert result.prompt_runs[0].artifacts == {}
    assert result.raw_regions == []


def test_run_sam3_prompt_plan_rejects_non_list_regions(tmp_path: Path):
    class BadRegionsTransport:
        def post_json(self, path, payload, timeout_s):
            return {"regions": {"bbox": [1, 2, 3, 4]}}, 1.0

    image = tmp_path / "input.png"
    Image.new("RGB", (8, 8), "white").save(image)
    config = tmp_path / "config.yaml"
    config.write_text(
        f"""
input:
  image: {image.name}
  output_dir: out
sam3:
  prompts:
    - id: arrow
      text: arrow
      confidence_threshold: 0.3
""",
        encoding="utf-8",
    )
    cfg = load_drawai_config(config)
    paths = prepare_artifact_paths(cfg.input.output_dir)

    with pytest.raises(ValueError, match="SAM3 response.*regions.*list"):
        run_sam3_prompt_plan(cfg.sam3, image, paths, transport=BadRegionsTransport())


def test_run_sam3_prompt_plan_adds_prompt_context_to_transport_errors(tmp_path: Path):
    class FailingTransport:
        def post_json(self, path, payload, timeout_s):
            raise Sam3ResponseError("connection refused")

    image = tmp_path / "input.png"
    Image.new("RGB", (8, 8), "white").save(image)
    config = tmp_path / "config.yaml"
    config.write_text(
        f"""
input:
  image: {image.name}
  output_dir: out
sam3:
  base_url: http://sam3.test
  timeout_seconds: 9
  prompts:
    - id: arrow
      text: arrow
      confidence_threshold: 0.3
""",
        encoding="utf-8",
    )
    cfg = load_drawai_config(config)
    paths = prepare_artifact_paths(cfg.input.output_dir)

    with pytest.raises(Sam3ResponseError) as exc_info:
        run_sam3_prompt_plan(cfg.sam3, image, paths, transport=FailingTransport())

    message = str(exc_info.value)
    assert "connection refused" in message
    assert "prompt_id='arrow'" in message
    assert "endpoint='/v1/segment/proposals'" in message
    assert "base_url='http://sam3.test'" in message
    assert "timeout_s=9.0" in message
    assert isinstance(exc_info.value.__cause__, Sam3ResponseError)


def test_http_json_transport_reports_malformed_json_context(monkeypatch):
    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def read(self):
            return b"{not-json"

    def fake_urlopen(request, timeout):
        return FakeResponse()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    transport = HttpJsonTransport("http://sam3.test")

    with pytest.raises(Sam3ResponseError) as exc_info:
        transport.post_json("/v1/segment/proposals", {"x": 1}, 7)

    message = str(exc_info.value)
    assert "malformed JSON" in message
    assert "base_url='http://sam3.test'" in message
    assert "endpoint='/v1/segment/proposals'" in message
    assert "timeout_s=7" in message
    assert "{not-json" in message
    assert isinstance(exc_info.value.__cause__, json.JSONDecodeError)


def test_http_json_transport_retries_model_busy_without_counting_queue_as_inference_timeout(monkeypatch):
    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def read(self):
            return b'{"regions":[],"raw_regions":[],"artifacts":{}}'

    calls = []
    sleeps = []

    def fake_urlopen(request, timeout):
        calls.append((request.full_url, timeout))
        if len(calls) == 1:
            headers = Message()
            headers.add_header("Retry-After", "0")
            headers.add_header("X-DrawAI-Queue", "model-busy")
            raise urllib.error.HTTPError(
                request.full_url,
                503,
                "Service Unavailable",
                headers,
                io.BytesIO(b'{"detail":{"code":"model_busy","retry_after_seconds":0}}'),
            )
        return FakeResponse()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    monkeypatch.setattr("drawai.sam3_client.time.sleep", sleeps.append)
    transport = HttpJsonTransport("http://sam3.test")

    payload, _elapsed_ms = transport.post_json("/v1/segment/proposals", {"x": 1}, 7)

    assert payload["regions"] == []
    assert calls == [
        ("http://sam3.test/v1/segment/proposals", 7),
        ("http://sam3.test/v1/segment/proposals", 7),
    ]
    assert sleeps == [0.0]
